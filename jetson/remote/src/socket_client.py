#!/usr/bin/env python3
"""
Socket Client for Motor Controller Multiplexer

Handles communication with the motor controller multiplexer service via Unix socket.
Sends movement commands and receives status updates.
"""

import socket
import json
import logging
import threading
import time
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)


class SocketClient:
    """
    Unix Socket Client for Motor Controller Communication

    Connects to the motor controller multiplexer and provides an interface
    for sending movement commands and receiving status updates.
    """

    def __init__(self, socket_path: str = '/tmp/motor-proxy/motor_controller.sock'):
        self.socket_path = socket_path
        self.sock: Optional[socket.socket] = None
        self.connected = False
        self.client_id: Optional[str] = None
        self.unique_name: Optional[str] = None
        self._stop_event = threading.Event()
        self._receiver_thread: Optional[threading.Thread] = None
        self._keepalive_thread: Optional[threading.Thread] = None

        # Status tracking
        self.arduino_connected = False
        self.arduino_state = "unknown"
        self.last_command_success = True

        # Keepalive management
        self.keepalive_interval = 2.5  # Send keepalive every 2.5 seconds (server expects every 3s)
        self.last_keepalive_response = time.time()
        self.last_command_time = 0  # Track when we last sent a motor command
        self.command_activity_threshold = 2.0  # Consider client idle after 2 seconds without commands

        # Callbacks
        self.on_status_update: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_arduino_message: Optional[Callable[[str], None]] = None
        self.on_connection_change: Optional[Callable[[bool], None]] = None

        logger.info(f"Initialized socket client for: {socket_path}")

    def connect(self) -> bool:
        """
        Connect to the motor controller multiplexer

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.connect(self.socket_path)
            self.connected = True

            # Start message receiving thread
            self._receiver_thread = threading.Thread(target=self._receive_messages, daemon=True)
            self._receiver_thread.start()

            logger.info(f"✅ Connected to motor controller at {self.socket_path}")

            # Send client identification
            self.send_message({
                'type': 'identify',
                'name': 'RemoteControlService'
            })

            # Initialize command activity tracking
            self.last_command_time = time.time()

            # Wait a moment for welcome and identification response
            time.sleep(0.5)

            # Start keepalive thread
            self._keepalive_thread = threading.Thread(target=self._keepalive_loop, daemon=True)
            self._keepalive_thread.start()

            # Request initial status
            self.get_status()

            if self.on_connection_change:
                self.on_connection_change(True)

            return True

        except Exception as e:
            logger.error(f"❌ Failed to connect to motor controller: {e}")
            return False

    def disconnect(self):
        """Disconnect from the motor controller"""
        self.connected = False
        self._stop_event.set()

        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None

        # Wait for threads to finish
        if self._receiver_thread and self._receiver_thread.is_alive():
            self._receiver_thread.join(timeout=1.0)

        if self._keepalive_thread and self._keepalive_thread.is_alive():
            self._keepalive_thread.join(timeout=1.0)

        if self.on_connection_change:
            self.on_connection_change(False)

        logger.info("👋 Disconnected from motor controller")

    def send_message(self, message: Dict[str, Any]) -> bool:
        """
        Send a message to the motor controller

        Args:
            message: Message dictionary to send

        Returns:
            bool: True if message sent successfully, False otherwise
        """
        if not self.connected or not self.sock:
            logger.error("❌ Not connected to motor controller")
            return False

        try:
            msg_str = json.dumps(message) + '\n'
            self.sock.send(msg_str.encode('utf-8'))

            # Log at DATA level to show socket data frames
            logger.data(f"📤 Sent: {message}")
            logger.debug(f"Sent message: {message}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send message: {e}")
            self.disconnect()
            return False

    def send_tank_command(self, command: str, value: int) -> bool:
        """
        Send a tank-style motor command to the robot

        Args:
            command: Motor command (FORWARD, BACKWARD, LEFT, RIGHT, etc.)
            value: Speed value (0-255)

        Returns:
            bool: True if command sent successfully, False otherwise
        """
        message = {
            'type': 'tank_command',
            'command': command.upper(),
            'value': max(0, min(255, value))  # Clamp to valid range
        }

        success = self.send_message(message)
        if success:
            # Track command activity for intelligent keepalive management
            self.last_command_time = time.time()

            # Log motor commands at DATA level for visibility
            logger.data(f"🚗 Tank command: {command}:{value}")
            logger.debug(f"🚗 Sent tank command: {command}:{value}")

        return success

    def send_mecanum_command(self, left_front: int, left_rear: int, right_front: int, right_rear: int) -> bool:
        """
        Send a mecanum-style motor command to the robot

        Args:
            left_front: Left front motor speed (-255 to 255)
            left_rear: Left rear motor speed (-255 to 255)
            right_front: Right front motor speed (-255 to 255)
            right_rear: Right rear motor speed (-255 to 255)

        Returns:
            bool: True if command sent successfully, False otherwise
        """
        # Clamp values to valid range
        def clamp(value):
            return max(-255, min(255, int(value)))

        message = {
            'type': 'mecanum_command',
            'motors': {
                'left_front': clamp(left_front),
                'left_rear': clamp(left_rear),
                'right_front': clamp(right_front),
                'right_rear': clamp(right_rear)
            }
        }

        success = self.send_message(message)
        if success:
            # Track command activity for intelligent keepalive management
            self.last_command_time = time.time()

            # Log motor commands at DATA level for visibility
            logger.data(f"🤖 Mecanum command: LF={left_front}, LR={left_rear}, RF={right_front}, RR={right_rear}")
            logger.debug(f"🤖 Sent mecanum command: LF={left_front}, LR={left_rear}, RF={right_front}, RR={right_rear}")

        return success

    def send_motor_command(self, command: str, value: int) -> bool:
        """
        Send a motor command to the robot (legacy method - uses tank commands)

        Args:
            command: Motor command (FORWARD, BACKWARD, LEFT, RIGHT, etc.)
            value: Speed value (0-255)

        Returns:
            bool: True if command sent successfully, False otherwise
        """
        return self.send_tank_command(command, value)

    def stop_robot(self) -> bool:
        """
        Send stop command to the robot

        Returns:
            bool: True if command sent successfully, False otherwise
        """
        return self.send_motor_command("STOP", 0)

    def reset_robot(self) -> bool:
        """
        Send reset command to the robot

        Returns:
            bool: True if command sent successfully, False otherwise
        """
        return self.send_motor_command("RESET", 0)

    def get_status(self) -> bool:
        """
        Request status from the motor controller

        Returns:
            bool: True if request sent successfully, False otherwise
        """
        return self.send_message({'type': 'get_status'})

    def get_sensor_data(self) -> bool:
        """
        Request sensor data from the motor controller

        Returns:
            bool: True if request sent successfully, False otherwise
        """
        return self.send_message({'type': 'get_sensor_data'})

    def set_priority(self, priority: int) -> bool:
        """
        Set client priority for motor control

        Args:
            priority: Priority value (lower = higher priority)

        Returns:
            bool: True if message sent successfully, False otherwise
        """
        return self.send_message({'type': 'set_priority', 'priority': priority})

    def ping(self) -> bool:
        """
        Send ping to the motor controller

        Returns:
            bool: True if ping sent successfully, False otherwise
        """
        return self.send_message({'type': 'ping'})

    def send_keepalive(self) -> bool:
        """
        Send keepalive message to maintain connection

        Returns:
            bool: True if keepalive sent successfully, False otherwise
        """
        return self.send_message({'type': 'keepalive'})

    def _keepalive_loop(self):
        """Background thread to send keepalive messages (intelligent management)"""
        while self.connected and not self._stop_event.is_set():
            try:
                # Wait for keepalive interval or stop event
                if self._stop_event.wait(self.keepalive_interval):
                    break  # Stop event was set

                if self.connected:
                    current_time = time.time()
                    time_since_last_command = current_time - self.last_command_time

                    # Only send keepalive if client has been idle for more than threshold
                    if time_since_last_command > self.command_activity_threshold:
                        if self.send_keepalive():
                            logger.debug("💓 Keepalive sent (client idle)")
                        else:
                            logger.warning("❌ Failed to send keepalive")
                            break
                    else:
                        # Client is active, motor commands act as keepalives
                        logger.debug(f"💓 Keepalive skipped (client active, last command {time_since_last_command:.1f}s ago)")

            except Exception as e:
                logger.error(f"❌ Keepalive error: {e}")
                break

        logger.debug("Keepalive loop ended")

    def _receive_messages(self):
        """Background thread to receive messages from the motor controller"""
        buffer = ""

        while self.connected and not self._stop_event.is_set():
            try:
                if not self.sock:
                    break

                # Set a short timeout to allow checking stop event
                self.sock.settimeout(0.5)

                try:
                    data = self.sock.recv(4096).decode('utf-8')
                except socket.timeout:
                    continue  # Check stop event and try again

                if not data:
                    logger.warning("Socket closed by remote host")
                    break

                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        self._process_message(line.strip())

            except Exception as e:
                if self.connected:
                    logger.error(f"❌ Error receiving message: {e}")
                break

        # Connection lost
        if self.connected:
            logger.warning("Connection lost, disconnecting...")
            self.disconnect()

    def _process_message(self, message: str):
        """Process a received message from the motor controller"""
        try:
            data = json.loads(message)
            msg_type = data.get('type', '')

            # Log at DATA level to show received socket data frames
            logger.data(f"📥 Received: {data}")
            logger.debug(f"Received message: {msg_type}")

            if msg_type == 'welcome':
                self.client_id = data.get('client_id')
                logger.info(f"✅ Connected as {self.client_id}")

            elif msg_type == 'identify_response':
                self.unique_name = data.get('unique_name')
                claimed_name = data.get('claimed_name')
                logger.info(f"🏷️  Identified as {self.unique_name} (claimed: {claimed_name})")

            elif msg_type == 'keepalive_response':
                self.last_keepalive_response = time.time()
                logger.debug("💓 Keepalive acknowledged")

            elif msg_type == 'keepalive_ignored':
                self.last_keepalive_response = time.time()
                reason = data.get('reason', 'unknown')
                logger.debug(f"💓 Keepalive ignored ({reason}) - client is active")

            elif msg_type == 'status':
                self._handle_status_message(data)

            elif msg_type in ['command_response', 'tank_command_response', 'mecanum_command_response']:
                self._handle_command_response(data)

            elif msg_type == 'sensor_data':
                self._handle_sensor_data(data)

            elif msg_type == 'arduino_message':
                self._handle_arduino_message(data)

            elif msg_type == 'arduino_connection':
                self._handle_arduino_connection(data)

            elif msg_type == 'error':
                self._handle_error_message(data)

            elif msg_type == 'pong':
                logger.debug("🏓 Received pong")

        except json.JSONDecodeError:
            logger.error(f"❌ Invalid JSON received: {message}")
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")

    def _handle_status_message(self, data: Dict[str, Any]):
        """Handle status message from motor controller"""
        self.arduino_connected = data.get('arduino_connected', False)
        self.arduino_state = data.get('arduino_state', 'unknown')

        logger.debug(f"📊 Arduino status: {self.arduino_state} "
                    f"(connected: {self.arduino_connected})")

        if self.on_status_update:
            self.on_status_update(data)

    def _handle_command_response(self, data: Dict[str, Any]):
        """Handle command response from motor controller"""
        msg_type = data.get('type', '')
        success = data.get('success', False)
        self.last_command_success = success

        status = "✅" if success else "❌"

        if msg_type == 'tank_command_response':
            command = data.get('command', '')
            value = data.get('value', 0)
            logger.debug(f"🚗 {status} Tank command {command}:{value}")
            if not success:
                logger.warning(f"Tank command failed: {command}:{value}")

        elif msg_type == 'mecanum_command_response':
            motors = data.get('motors', {})
            logger.debug(f"🤖 {status} Mecanum command LF:{motors.get('left_front')} "
                        f"LR:{motors.get('left_rear')} RF:{motors.get('right_front')} RR:{motors.get('right_rear')}")
            if not success:
                logger.warning(f"Mecanum command failed")

        else:  # Legacy command_response
            command = data.get('command', '')
            value = data.get('value', 0)
            logger.debug(f"🎮 {status} Command {command}:{value}")
            if not success:
                logger.warning(f"Command failed: {command}:{value}")

    def _handle_sensor_data(self, data: Dict[str, Any]):
        """Handle sensor data from motor controller"""
        sensor_data = data.get('data')
        if sensor_data:
            # Log sensor data occasionally to avoid spam
            front_left = sensor_data.get('front_left', 'N/A')
            front_right = sensor_data.get('front_right', 'N/A')
            rear_left = sensor_data.get('rear_left', 'N/A')
            rear_right = sensor_data.get('rear_right', 'N/A')
            front_collision = sensor_data.get('front_collision', False)
            rear_collision = sensor_data.get('rear_collision', False)

            logger.debug(f"📡 Sensors: FL:{front_left} FR:{front_right} RL:{rear_left} RR:{rear_right} "
                        f"Collisions: F:{front_collision} R:{rear_collision}")
        else:
            logger.debug(f"📡 No sensor data available")

    def _handle_arduino_message(self, data: Dict[str, Any]):
        """Handle Arduino message from motor controller"""
        message_text = data.get('message', '')

        # Filter important messages
        if any(keyword in message_text.upper() for keyword in
               ['ERROR', 'WARNING', 'TIMEOUT', 'DISCONNECTED', 'CONNECTED', 'READY']):
            logger.info(f"🤖 Arduino: {message_text}")

            if self.on_arduino_message:
                self.on_arduino_message(message_text)

    def _handle_arduino_connection(self, data: Dict[str, Any]):
        """Handle Arduino connection state change"""
        state = data.get('state', 'unknown')
        self.arduino_connected = (state == 'connected')

        logger.info(f"🔄 Arduino connection: {state}")

    def _handle_error_message(self, data: Dict[str, Any]):
        """Handle error message from motor controller"""
        error_msg = data.get('message', 'Unknown error')
        logger.error(f"❌ Motor controller error: {error_msg}")

    def is_connected(self) -> bool:
        """Check if connected to motor controller"""
        return self.connected

    def is_arduino_connected(self) -> bool:
        """Check if Arduino is connected to motor controller"""
        return self.arduino_connected

    def get_arduino_state(self) -> str:
        """Get current Arduino state"""
        return self.arduino_state

    def get_unique_name(self) -> Optional[str]:
        """Get unique client name assigned by server"""
        return self.unique_name

    def was_last_command_successful(self) -> bool:
        """Check if last command was successful"""
        return self.last_command_success

    def cleanup(self):
        """Clean up resources"""
        self.disconnect()