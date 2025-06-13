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
from typing import Optional, Dict, Any, Callable
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
        self.keepalive_interval = 3  # Set to 3 as in test_complete_robot.py
        self.grace_period = 6.0  # Wait 6 seconds after connection before starting keepalive
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5.0  # Seconds between reconnect attempts (wait for Arduino reboot + startup)
        self._keepalive_thread: Optional[threading.Thread] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_keepalive = threading.Event()

    def find_arduino_port(self) -> Optional[str]:
        """
        Find available Arduino port.
        Returns the preferred port if available, otherwise scans for Arduino devices.
        """
        # If user specified a port and it exists, try it first
        if self.preferred_port:
            if os.path.exists(self.preferred_port):
                try:
                    test_ser = serial.Serial(self.preferred_port, self.baud_rate, timeout=1)
                    test_ser.close()
                    logger.debug(f"Preferred port {self.preferred_port} is available")
                    return self.preferred_port
                except Exception as e:
                    logger.debug(f"Preferred port {self.preferred_port} test failed: {e}")

        # Scan for available Arduino ports
        # Arduino devices typically appear as /dev/ttyACM* or /dev/ttyUSB*
        patterns = ['/dev/ttyACM*', '/dev/ttyUSB*']

        # On Windows, check COM ports
        if os.name == 'nt':
            patterns.append('COM*')

        available_ports = []
        for pattern in patterns:
            available_ports.extend(glob.glob(pattern))

        # Sort ports to ensure consistent ordering
        available_ports = sorted(available_ports)

        logger.debug(f"Scanning ports: {available_ports}")

        for port in available_ports:
            try:
                # Test if port is accessible
                test_ser = serial.Serial(port, self.baud_rate, timeout=1)
                test_ser.close()
                logger.debug(f"Found working Arduino port: {port}")
                return port
            except Exception as e:
                logger.debug(f"Port {port} test failed: {e}")
                continue

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

            # Wait for Arduino to initialize
            time.sleep(3)

            # Start reading thread
            self._running = True
            self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._read_thread.start()

            # Start simple keepalive thread immediately (essential to prevent Arduino auto-reboot)
            self._stop_keepalive.clear()
            self._keepalive_thread = threading.Thread(target=self._simple_keepalive_loop, daemon=True)
            self._keepalive_thread.start()

            # Start reconnection monitor
            self._monitor_thread = threading.Thread(target=self._connection_monitor, daemon=True)
            self._monitor_thread.start()

            self.state = ConnectionState.CONNECTED
            self.connection_time = time.time()  # Record connection time
            self.reconnect_attempts = 0  # Reset reconnect counter
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
            new_port = self.find_arduino_port()
            if not new_port:
                logger.warning("No Arduino found during reconnection attempt")
                self.reconnect_attempts += 1
                self.state = ConnectionState.ERROR
                self._notify_connection_change()
                return False

            # Check if port changed (Arduino rebooted)
            if new_port != self.current_port:
                logger.info(f"Arduino rebooted: {self.current_port} -> {new_port}")
                self.current_port = new_port

            # Attempt connection
            self.serial_conn = serial.Serial(
                port=new_port,
                baudrate=self.baud_rate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )

            # Wait for Arduino startup
            time.sleep(3)

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
        """Send a command to Arduino"""
        if not self._is_connected():
            logger.warning(f"Cannot send command {command}:{value} - not connected")
            return False

        try:
            with self._write_lock:
                cmd_str = f"{command.upper()}:{value}\n"
                self.serial_conn.write(cmd_str.encode('utf-8'))
                self.last_activity = time.time()
                logger.debug(f"Sent command: {cmd_str.strip()}")
                return True
        except Exception as e:
            logger.error(f"Failed to send command {command}:{value} - {e}")
            self._handle_connection_error()
            return False

    def _read_loop(self):
        """Background thread for reading Arduino responses"""
        logger.debug("Starting serial read loop")

        while self._running and self._is_connected():
            try:
                if self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        self._process_response(line)
                else:
                    time.sleep(0.01)  # Small delay to prevent busy waiting

            except Exception as e:
                logger.error(f"Error in read loop: {e}")
                self._handle_connection_error()
                break

        logger.debug("Serial read loop stopped")

    def _process_response(self, line: str):
        """Process a response line from Arduino"""
        try:
            # Try to parse as JSON (sensor data)
            if line.startswith('{'):
                data = json.loads(line)
                if 'sensors' in data:
                    sensor_data = SensorData.from_json(data)
                    self.last_sensor_data = sensor_data
                    if self.on_sensor_data:
                        self.on_sensor_data(sensor_data)
                    return

            # Handle status messages
            if self.on_status_message:
                self.on_status_message(line)

            # Log important status messages
            if any(indicator in line for indicator in ['🚀', '💓', '🔌', '🕹️', '🛑', '⚠️']):
                logger.info(f"Arduino status: {line}")
            else:
                logger.debug(f"Arduino: {line}")

        except json.JSONDecodeError:
            # Not JSON, treat as status message
            if self.on_status_message:
                self.on_status_message(line)
            logger.debug(f"Arduino: {line}")
        except Exception as e:
            logger.error(f"Error processing response '{line}': {e}")

    def _is_connected(self) -> bool:
        """Check if serial connection is active"""
        return (self.serial_conn is not None and
                self.serial_conn.is_open and
                self.state == ConnectionState.CONNECTED)

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

    def _simple_keepalive_loop(self):
        """Simple keepalive to prevent Arduino 5-second auto-reboot timeout"""
        logger.info("Starting simple keepalive thread")

        while not self._stop_keepalive.is_set():
            try:
                # Wait 3 seconds (Arduino watchdog expects communication every 3 seconds)
                if self._stop_keepalive.wait(3.0):
                    break  # Stop event was set

                # Send keepalive if still connected
                if self._running and self.state == ConnectionState.CONNECTED:
                    if self._is_connected():
                        try:
                            with self._write_lock:
                                if self.serial_conn and self.serial_conn.is_open:
                                    cmd_str = "KEEPALIVE:0\n"
                                    self.serial_conn.write(cmd_str.encode('utf-8'))
                                    logger.debug("Sent keepalive command")
                        except Exception as e:
                            logger.warning(f"Keepalive failed: {e}")
                            break
                    else:
                        logger.debug("Skipping keepalive - not connected")
                else:
                    logger.debug(f"Skipping keepalive - running:{self._running}, state:{self.state}")
            except Exception as e:
                logger.error(f"Keepalive loop error: {e}")
                break

        logger.info("Simple keepalive thread stopped")