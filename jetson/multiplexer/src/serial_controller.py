#!/usr/bin/env python3
"""
Serial Controller Module

Manages serial communication with Arduino motor controller.
Handles command sending, response parsing, and connection management with
dynamic port detection and auto-reconnection capabilities.
"""

import serial
import time
import json
import threading
import logging
import glob
import os
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


@dataclass
class SensorData:
    front_left: int
    front_right: int
    rear_left: int
    rear_right: int
    front_collision: bool
    rear_collision: bool
    timestamp: float

    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> 'SensorData':
        sensors = json_data.get('sensors', {})
        return cls(
            front_left=sensors.get('front_left', 0),
            front_right=sensors.get('front_right', 0),
            rear_left=sensors.get('rear_left', 0),
            rear_right=sensors.get('rear_right', 0),
            front_collision=sensors.get('front_collision', False),
            rear_collision=sensors.get('rear_collision', False),
            timestamp=time.time()
        )


class SerialController:
    """
    Manages serial communication with Arduino motor controller.
    Provides thread-safe command sending and response monitoring with
    dynamic port detection and auto-reconnection capabilities.
    """

    def __init__(self, port: Optional[str] = None, baud_rate: int = 115200, timeout: float = 1.0):
        self.preferred_port = port  # User-specified port (optional)
        self.current_port: Optional[str] = None  # Actually connected port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.serial_conn: Optional[serial.Serial] = None
        self.state = ConnectionState.DISCONNECTED
        self._running = False
        self._read_thread: Optional[threading.Thread] = None
        self._write_lock = threading.Lock()

        # Callbacks for events
        self.on_sensor_data: Optional[Callable[[SensorData], None]] = None
        self.on_status_message: Optional[Callable[[str], None]] = None
        self.on_connection_change: Optional[Callable[[ConnectionState], None]] = None

        # Last known sensor data
        self.last_sensor_data: Optional[SensorData] = None

        # Connection monitoring and recovery
        self.last_activity = time.time()
        self.connection_time: Optional[float] = None  # Track when connection was established
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 2.0  # Seconds between reconnect attempts (Arduino full reboot cycle ~12s)
        self._keepalive_thread: Optional[threading.Thread] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_keepalive = threading.Event()

        # Connection health tracking
        self.last_sensor_time = 0.0
        self.sensor_count = 0
        self.expected_sensor_interval = 0.1  # Arduino sends every 100ms

    def _scan_arduino_ports(self) -> List[str]:
        """Scan for available Arduino ports without opening them"""
        import glob
        patterns = ['/dev/ttyACM*', '/dev/ttyUSB*']

        # On Windows, check COM ports
        if os.name == 'nt':
            patterns.append('COM*')

        available_ports = []
        for pattern in patterns:
            available_ports.extend(glob.glob(pattern))

        return sorted(available_ports)

    def find_arduino_port(self) -> Optional[str]:
        """
        Find available Arduino port.
        Returns the preferred port if available, otherwise scans for Arduino devices.
        """
        # If user specified a port and it exists, try it first
        if self.preferred_port:
            if os.path.exists(self.preferred_port):
                logger.debug(f"Preferred port {self.preferred_port} is available")
                return self.preferred_port

        # Scan for available Arduino ports
        available_ports = self._scan_arduino_ports()

        if self.state == ConnectionState.RECONNECTING:
            logger.info(f"Reconnection port scan - Available ports: {available_ports}")
        else:
            logger.debug(f"Scanning ports: {available_ports}")

        for port in available_ports:
            # Just check if port exists - don't open it (would trigger Arduino reboot)
            if os.path.exists(port):
                logger.debug(f"Found Arduino port: {port}")
                return port

        logger.warning("No Arduino ports found")
        return None

    def connect(self) -> bool:
        """Establish connection to Arduino with auto-discovery"""
        if self.state == ConnectionState.CONNECTED:
            return True

        try:
            self.state = ConnectionState.CONNECTING
            self._notify_connection_change()

            # Find Arduino port
            port = self.find_arduino_port()
            if not port:
                logger.error("No Arduino found on any port")
                self.state = ConnectionState.ERROR
                self._notify_connection_change()
                return False

            # Update current port
            if self.current_port != port:
                logger.info(f"Arduino port changed: {self.current_port} -> {port}")
                self.current_port = port

            logger.info(f"Connecting to Arduino on {port} at {self.baud_rate} baud")

            self.serial_conn = serial.Serial(
                port=port,
                baudrate=self.baud_rate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )

            # Start reading thread first
            self._running = True
            self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._read_thread.start()

            # Start keepalive thread immediately (critical for Arduino watchdog activation)
            self._stop_keepalive.clear()
            self._keepalive_thread = threading.Thread(target=self._simple_keepalive_loop, daemon=True)
            self._keepalive_thread.start()

            # Start reconnection monitor
            self._monitor_thread = threading.Thread(target=self._connection_monitor, daemon=True)
            self._monitor_thread.start()

            self.state = ConnectionState.CONNECTED
            self.connection_time = time.time()  # Record connection time
            self.reconnect_attempts = 0  # Reset reconnect counter

            # Reset sensor tracking for new connection
            self.sensor_count = 0
            self.last_sensor_time = 0.0

            self._notify_connection_change()
            logger.info(f"Successfully connected to Arduino on {port}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Arduino: {e}")
            self.state = ConnectionState.ERROR
            self._notify_connection_change()
            return False

    def disconnect(self):
        """Close connection to Arduino"""
        logger.info("Disconnecting from Arduino")
        self._running = False
        # Stop keepalive thread
        self._stop_keepalive.set()

        if self._read_thread and self._read_thread.is_alive():
            self._read_thread.join(timeout=2.0)

        if self.serial_conn and self.serial_conn.is_open:
            try:
                # Send reset command before disconnecting
                self.send_command("RESET", 0)
                time.sleep(0.5)
                self.serial_conn.close()
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")

        self.serial_conn = None
        self.current_port = None
        self.state = ConnectionState.DISCONNECTED
        self._notify_connection_change()
        logger.info("Disconnected from Arduino")

    def _connection_monitor(self):
        """Monitor connection health and handle auto-reconnection"""
        while self._running:
            try:
                time.sleep(5.0)  # Check every 5 seconds

                if not self._running:
                    break

                # Check if connection is still valid
                if self.state == ConnectionState.CONNECTED:
                    if not self._is_connected():
                        logger.warning("Connection lost, attempting to reconnect...")
                        self._attempt_reconnection()
                elif self.state == ConnectionState.ERROR:
                    # Try to reconnect after error
                    if self.reconnect_attempts < self.max_reconnect_attempts:
                        logger.info(f"Attempting reconnection {self.reconnect_attempts + 1}/{self.max_reconnect_attempts}")
                        self._attempt_reconnection()
                    else:
                        logger.error("Max reconnection attempts reached, giving up")
                        break
            except Exception as e:
                logger.error(f"Error in connection monitor: {e}")

    def _attempt_reconnection(self):
        """Attempt to reconnect to Arduino, possibly on a different port"""
        try:
            self.state = ConnectionState.RECONNECTING
            self._notify_connection_change()

            # Close existing connection
            if self.serial_conn:
                try:
                    self.serial_conn.close()
                except:
                    pass
                self.serial_conn = None

            # Wait before reconnecting
            time.sleep(self.reconnect_delay)

            # Find Arduino (may be on different port after reboot)
            logger.info("Scanning for Arduino ports during reconnection...")
            new_port = self.find_arduino_port()
            if not new_port:
                logger.warning("No Arduino found during reconnection attempt")
                # Log available ports for debugging
                available_ports = self._scan_arduino_ports()
                logger.warning(f"Available ports during reconnection: {available_ports}")

                self.reconnect_attempts += 1
                self.state = ConnectionState.ERROR
                self._notify_connection_change()
                return False

            # Check if port changed (Arduino rebooted)
            if new_port != self.current_port:
                logger.info(f"Arduino rebooted: {self.current_port} -> {new_port}")
                self.current_port = new_port
                # Give Arduino extra time to complete initialization after reboot
                logger.info("Waiting for Arduino to complete reboot initialization...")
                time.sleep(1)

            # Attempt connection
            self.serial_conn = serial.Serial(
                port=new_port,
                baudrate=self.baud_rate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )

            # Restart reading thread if it died
            if not self._read_thread or not self._read_thread.is_alive():
                self._running = True
                self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
                self._read_thread.start()
                logger.info("Restarted read thread after reconnection")

            # Restart keepalive thread if it died
            if not self._keepalive_thread or not self._keepalive_thread.is_alive():
                self._stop_keepalive.clear()
                self._keepalive_thread = threading.Thread(target=self._simple_keepalive_loop, daemon=True)
                self._keepalive_thread.start()
                logger.info("Restarted keepalive thread after reconnection")

            self.state = ConnectionState.CONNECTED
            self.connection_time = time.time()  # Record reconnection time
            self.reconnect_attempts = 0

            # Reset sensor tracking for new connection
            self.sensor_count = 0
            self.last_sensor_time = 0.0

            self._notify_connection_change()
            logger.info(f"Successfully reconnected to Arduino on {new_port}")
            return True

        except Exception as e:
            logger.error(f"Reconnection attempt failed: {e}")
            self.reconnect_attempts += 1
            self.state = ConnectionState.ERROR
            self._notify_connection_change()
            return False

    def send_command(self, command: str, value: int) -> bool:
        """Send a tank command to Arduino (legacy format, converted to JSON)"""
        return self.send_tank_command(command, value)

    def send_tank_command(self, command: str, value: int) -> bool:
        """Send a tank-style JSON command to Arduino"""
        if not self._is_connected():
            logger.warning(f"Cannot send tank command {command}:{value} - not connected")
            return False

        try:
            with self._write_lock:
                # Create JSON command for tank movement
                json_cmd = {
                    "type": "tank",
                    "command": command.upper(),
                    "value": max(0, min(255, value))
                }
                cmd_str = f"{json.dumps(json_cmd)}\n"
                self.serial_conn.write(cmd_str.encode('utf-8'))
                self.last_activity = time.time()
                logger.debug(f"Sent tank command: {cmd_str.strip()}")
                return True
        except Exception as e:
            logger.error(f"Failed to send tank command {command}:{value} - {e}")
            self._handle_connection_error()
            return False

    def send_mecanum_command(self, left_front: int, left_rear: int, right_front: int, right_rear: int) -> bool:
        """Send a mecanum-style JSON command to Arduino"""
        logger.debug(f"🔍 SERIAL: send_mecanum_command called with LF:{left_front} LR:{left_rear} RF:{right_front} RR:{right_rear}")

        if not self._is_connected():
            logger.warning(f"Cannot send mecanum command - not connected")
            return False

        # Validate motor speeds
        def clamp_speed(speed):
            return max(-255, min(255, speed))

        try:
            logger.debug(f"🔍 SERIAL: About to acquire _write_lock")
            with self._write_lock:
                logger.debug(f"🔍 SERIAL: _write_lock acquired, creating JSON command")
                # Create JSON command for mecanum movement
                json_cmd = {
                    "type": "mecanum",
                    "motors": {
                        "left_front": clamp_speed(left_front),
                        "left_rear": clamp_speed(left_rear),
                        "right_front": clamp_speed(right_front),
                        "right_rear": clamp_speed(right_rear)
                    }
                }
                cmd_str = f"{json.dumps(json_cmd)}\n"
                logger.debug(f"🔍 SERIAL: About to write to serial: {cmd_str.strip()}")
                self.serial_conn.write(cmd_str.encode('utf-8'))
                self.last_activity = time.time()
                logger.debug(f"🔍 SERIAL: Serial write completed")
                logger.debug(f"Sent mecanum command: LF:{left_front} LR:{left_rear} RF:{right_front} RR:{right_rear}")
                logger.debug(f"🔍 SERIAL: About to release _write_lock and return True")
                return True
        except Exception as e:
            logger.error(f"Failed to send mecanum command - {e}")
            logger.error(f"🔍 SERIAL: Exception in send_mecanum_command: {type(e).__name__}: {e}")
            self._handle_connection_error()
            return False

    def send_raw_json_command(self, json_command: Dict[str, Any]) -> bool:
        """Send a raw JSON command to Arduino"""
        if not self._is_connected():
            logger.warning(f"Cannot send raw JSON command - not connected")
            return False

        try:
            with self._write_lock:
                cmd_str = f"{json.dumps(json_command)}\n"
                self.serial_conn.write(cmd_str.encode('utf-8'))
                self.last_activity = time.time()
                logger.debug(f"Sent raw JSON command: {cmd_str.strip()}")
                return True
        except Exception as e:
            logger.error(f"Failed to send raw JSON command - {e}")
            self._handle_connection_error()
            return False

    def _read_loop(self):
        """Background thread for reading Arduino responses"""
        logger.debug("Starting serial read loop")

        while self._running:
            try:
                # Check if we have a valid serial connection
                if not self.serial_conn or not self.serial_conn.is_open:
                    logger.debug("Serial connection not available, stopping read loop")
                    break

                # Read data if available (like your working example)
                if self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        self._process_response(line)
                else:
                    time.sleep(0.05)  # Match your working example timing

            except Exception as e:
                logger.error(f"Error in read loop: {e}")
                self._handle_connection_error()
                break

        logger.debug("Serial read loop stopped")

    def _process_response(self, line: str):
        """Process a response line from Arduino"""
        try:
            # Log all Arduino output for debugging
            logger.debug(f"Arduino raw: {repr(line)}")

            # Try to parse as JSON (sensor data)
            if line.startswith('{'):
                data = json.loads(line)
                if 'sensors' in data:
                    sensor_data = SensorData.from_json(data)
                    self.last_sensor_data = sensor_data

                    # Track sensor reception for connection health
                    self.last_sensor_time = time.time()
                    self.sensor_count += 1

                    # Log milestone sensor counts
                    if self.sensor_count in [1, 10, 50, 100, 500] or self.sensor_count % 1000 == 0:
                        logger.info(f"📊 Received {self.sensor_count} sensor readings - connection healthy")

                    # Log first few sensor readings for debugging
                    if self.sensor_count <= 5:
                        logger.info(f"📊 Sensor #{self.sensor_count}: FL:{data['sensors'].get('front_left')} FR:{data['sensors'].get('front_right')} RL:{data['sensors'].get('rear_left')} RR:{data['sensors'].get('rear_right')}")

                    if self.on_sensor_data:
                        self.on_sensor_data(sensor_data)
                    return

            # Handle status messages - log ALL of them for debugging
            if self.on_status_message:
                self.on_status_message(line)

            # Log ALL Arduino messages during initial connection for debugging
            if self.sensor_count < 10:
                logger.info(f"Arduino: {line}")
            elif any(indicator in line for indicator in ['🚀', '💓', '🔌', '🛑', '⚠️']):
                logger.info(f"Arduino status: {line}")
            elif '🕹️' in line and 'DEBUG' in line:
                # Reduce noise from repetitive joystick debug messages
                logger.debug(f"Arduino: {line}")
            elif '🕹️' in line:
                logger.info(f"Arduino status: {line}")
            else:
                logger.debug(f"Arduino: {line}")

        except json.JSONDecodeError:
            # Not JSON, treat as status message
            if self.on_status_message:
                self.on_status_message(line)

            # Log non-JSON messages during initial connection
            if self.sensor_count < 10:
                logger.info(f"Arduino: {line}")
            else:
                logger.debug(f"Arduino: {line}")
        except Exception as e:
            logger.error(f"Error processing response '{line}': {e}")

    def _is_connected(self) -> bool:
        """Check if Arduino connection is healthy based on sensor data and port existence"""
        if not self.serial_conn or not self.serial_conn.is_open:
            return False

        if self.state != ConnectionState.CONNECTED:
            return False

        # Check if the device file still exists (Arduino hasn't rebooted)
        if self.current_port and not os.path.exists(self.current_port):
            logger.warning(f"Arduino port {self.current_port} disappeared - Arduino rebooted")
            return False

        # During initial connection (first 30 seconds), be very patient
        # Arduino needs time to activate watchdog and start sending sensors
        if self.connection_time and (time.time() - self.connection_time) < 30.0:
            return True

        # After initial period, check if we're receiving sensor data (Arduino sends every 100ms)
        if self.last_sensor_time > 0:
            time_since_sensor = time.time() - self.last_sensor_time
            if time_since_sensor > 5.0:  # No sensor data for 5 seconds = problem
                logger.warning(f"No sensor data for {time_since_sensor:.1f}s - connection may be dead")
                return False
        else:
            # No sensor data received yet after initial period = problem
            logger.warning("No sensor data received after 30s - Arduino may not be responding to keepalive")
            return False

        return True

    def _handle_connection_error(self):
        """Handle connection errors"""
        logger.warning("Connection error detected")
        if self.state == ConnectionState.CONNECTED:
            self.state = ConnectionState.ERROR
            self._notify_connection_change()

    def _notify_connection_change(self):
        """Notify listeners of connection state change"""
        if self.on_connection_change:
            self.on_connection_change(self.state)

    def get_sensor_data(self) -> Optional[SensorData]:
        """Get last known sensor data"""
        return self.last_sensor_data

    def is_connected(self) -> bool:
        """Check if controller is connected"""
        return self.state == ConnectionState.CONNECTED

    def get_state(self) -> ConnectionState:
        """Get current connection state"""
        return self.state

    def get_current_port(self) -> Optional[str]:
        """Get currently connected port"""
        return self.current_port

    # Movement command helpers
    def move_forward(self, speed: int) -> bool:
        """Move robot forward"""
        return self.send_command("FORWARD", max(0, min(255, speed)))

    def move_backward(self, speed: int) -> bool:
        """Move robot backward"""
        return self.send_command("BACKWARD", max(0, min(255, speed)))

    def turn_left(self, speed: int) -> bool:
        """Turn robot left"""
        return self.send_command("LEFT", max(0, min(255, speed)))

    def turn_right(self, speed: int) -> bool:
        """Turn robot right"""
        return self.send_command("RIGHT", max(0, min(255, speed)))

    def stop(self) -> bool:
        """Stop robot movement"""
        return self.send_command("STOP", 0)

    def reset(self) -> bool:
        """Reset robot to joystick control"""
        return self.send_command("RESET", 0)

    # Mecanum movement helpers
    def mecanum_forward(self, speed: int) -> bool:
        """Move robot forward using mecanum wheels"""
        speed = max(-255, min(255, speed))
        return self.send_mecanum_command(speed, speed, speed, speed)

    def mecanum_backward(self, speed: int) -> bool:
        """Move robot backward using mecanum wheels"""
        speed = max(-255, min(255, speed))
        return self.send_mecanum_command(-speed, -speed, -speed, -speed)

    def mecanum_strafe_left(self, speed: int) -> bool:
        """Strafe left using mecanum wheels"""
        speed = max(-255, min(255, speed))
        return self.send_mecanum_command(speed, -speed, -speed, speed)

    def mecanum_strafe_right(self, speed: int) -> bool:
        """Strafe right using mecanum wheels"""
        speed = max(-255, min(255, speed))
        return self.send_mecanum_command(-speed, speed, speed, -speed)

    def mecanum_rotate_clockwise(self, speed: int) -> bool:
        """Rotate clockwise using mecanum wheels"""
        speed = max(-255, min(255, speed))
        return self.send_mecanum_command(-speed, -speed, speed, speed)

    def mecanum_rotate_counterclockwise(self, speed: int) -> bool:
        """Rotate counter-clockwise using mecanum wheels"""
        speed = max(-255, min(255, speed))
        return self.send_mecanum_command(speed, speed, -speed, -speed)

    def mecanum_stop(self) -> bool:
        """Stop all mecanum motors"""
        return self.send_mecanum_command(0, 0, 0, 0)

    def _simple_keepalive_loop(self):
        """Simple keepalive to prevent Arduino 5-second auto-reboot timeout"""
        logger.info("Starting simple keepalive thread")

        while not self._stop_keepalive.is_set():
            try:
                # Wait 2.5 seconds (faster than Arduino's 3-second timeout to prevent race condition)
                if self._stop_keepalive.wait(2.5):
                    break  # Stop event was set

                # Send keepalive if we have a serial connection (simpler check)
                if self._running and self.serial_conn and self.serial_conn.is_open:
                    try:
                        # Use timeout on lock acquisition to prevent deadlock with motor commands
                        if self._write_lock.acquire(timeout=0.5):  # 500ms timeout
                            try:
                                # Send keepalive as JSON command
                                keepalive_cmd = {
                                    "type": "tank",
                                    "command": "KEEPALIVE",
                                    "value": 0
                                }
                                cmd_str = f"{json.dumps(keepalive_cmd)}\n"
                                self.serial_conn.write(cmd_str.encode('utf-8'))
                                logger.debug("Sent keepalive command")
                            finally:
                                self._write_lock.release()
                        else:
                            logger.debug("Keepalive skipped - write lock busy (motor command in progress)")
                    except Exception as e:
                        logger.warning(f"Keepalive failed: {e}")
                        self._handle_connection_error()
                        break
                else:
                    logger.debug(f"Skipping keepalive - running:{self._running}, serial_open:{self.serial_conn and self.serial_conn.is_open}")

            except Exception as e:
                logger.error(f"Keepalive loop error: {e}")
                break

        logger.info("Simple keepalive thread stopped")