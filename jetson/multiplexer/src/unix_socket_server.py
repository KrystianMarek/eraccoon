#!/usr/bin/env python3
"""
Unix Socket Server Module

Provides Unix socket interface for robot control.
Handles multiple client connections and command multiplexing.
"""

import socket
import threading
import logging
import json
import time
import os
import errno
import select
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

from .serial_controller import SerialController, SensorData, ConnectionState

logger = logging.getLogger(__name__)


class ClientState(Enum):
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    ACTIVE = "active"
    DISCONNECTED = "disconnected"


@dataclass
class ClientInfo:
    client_id: str
    socket: socket.socket
    address: str
    state: ClientState
    last_activity: float
    priority: int = 10  # Lower number = higher priority

    # Rate limiting
    command_count: int = 0
    last_command_time: float = 0.0
    dropped_commands: int = 0
    last_drop_log_time: float = 0.0

    # Keepalive tracking
    last_keepalive: float = 0.0
    missed_keepalives: int = 0

    # Unique naming
    unique_name: str = ""
    claimed_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'client_id': self.client_id,
            'unique_name': self.unique_name,
            'claimed_name': self.claimed_name,
            'address': self.address,
            'state': self.state.value,
            'last_activity': self.last_activity,
            'priority': self.priority,
            'command_count': self.command_count,
            'dropped_commands': self.dropped_commands,
            'last_keepalive': self.last_keepalive,
            'missed_keepalives': self.missed_keepalives
        }


class MotorProxyServer:
    """
    Unix socket server that provides multiplexed access to Arduino motor controller.
    Handles client connections, command queuing, and status broadcasting.
    """

    def __init__(self, socket_path: str = '/var/eraccoon/multiplexer/socket/motor_proxy_service.sock',
                 serial_port: Optional[str] = None, baud_rate: int = 115200):
        self.socket_path = socket_path
        self.server_socket: Optional[socket.socket] = None
        self.serial_controller = SerialController(serial_port, baud_rate)

        # Client management
        self.clients: Dict[str, ClientInfo] = {}
        self.clients_lock = threading.Lock()
        self.active_client_id: Optional[str] = None
        self.client_counter = 0  # For unique client naming

        # Rate limiting configuration
        self.base_rate_limit = 10.0  # Base commands per second per client
        self.min_rate_limit = 1.0   # Minimum rate limit per client

        # Keepalive configuration
        self.keepalive_timeout = 3.0  # Seconds between required keepalives
        self.max_missed_keepalives = 3  # Max consecutive missed keepalives before disconnect

        # Server state
        self.running = False
        self.server_thread: Optional[threading.Thread] = None
        self.keepalive_thread: Optional[threading.Thread] = None

        # Command queuing
        self.command_queue: List[Dict[str, Any]] = []
        self.queue_lock = threading.Lock()

        # Statistics
        self.stats = {
            'start_time': time.time(),
            'total_connections': 0,
            'commands_processed': 0,
            'commands_dropped': 0,
            'errors': 0
        }

        # Set up serial controller callbacks
        self.serial_controller.on_sensor_data = self._on_sensor_data
        self.serial_controller.on_status_message = self._on_status_message
        self.serial_controller.on_connection_change = self._on_connection_change

    def start(self) -> bool:
        """Start the proxy server"""
        try:
            # Remove existing socket file
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)

            # Create socket directory if needed
            Path(self.socket_path).parent.mkdir(parents=True, exist_ok=True)

            # Connect to Arduino
            logger.info("Connecting to Arduino...")
            if not self.serial_controller.connect():
                logger.error("Failed to connect to Arduino")
                return False

            # Create and bind Unix socket
            self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.server_socket.bind(self.socket_path)
            self.server_socket.listen(5)

            # Set permissions for socket file
            os.chmod(self.socket_path, 0o666)

            self.running = True
            self.stats['start_time'] = time.time()

            # Start server thread
            self.server_thread = threading.Thread(target=self._server_loop, daemon=True)
            self.server_thread.start()

            # Start keepalive monitoring thread
            self.keepalive_thread = threading.Thread(target=self._keepalive_monitor, daemon=True)
            self.keepalive_thread.start()

            current_port = self.serial_controller.get_current_port()
            logger.info(f"Motor proxy server started on {self.socket_path}")
            logger.info(f"Connected to Arduino on port: {current_port}")
            return True

        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            return False

    def stop(self):
        """Stop the proxy server"""
        logger.info("Stopping motor proxy server...")
        self.running = False

        # Disconnect all clients
        with self.clients_lock:
            for client in list(self.clients.values()):
                self._disconnect_client(client.client_id)

        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception as e:
                logger.warning(f"Error closing server socket: {e}")

        # Remove socket file
        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except Exception as e:
                logger.warning(f"Error removing socket file: {e}")

        # Disconnect from Arduino
        self.serial_controller.disconnect()

        logger.info("Motor proxy server stopped")

    def _server_loop(self):
        """Main server loop for accepting connections"""
        logger.debug("Starting server loop")

        while self.running:
            try:
                if self.server_socket:
                    client_socket, address = self.server_socket.accept()

                    # Generate unique client ID and name
                    self.client_counter += 1
                    client_id = f"client_{int(time.time() * 1000) % 100000}"
                    unique_name = f"Client-{self.client_counter:03d}"

                    logger.info(f"New client connected: {client_id} ({unique_name})")
                    self.stats['total_connections'] += 1

                    # Log current sensor data flow status for debugging
                    sensor_data = self.serial_controller.get_sensor_data()
                    sensor_count = getattr(self.serial_controller, 'sensor_count', 0)
                    logger.info(f"Client connection - Current sensor count: {sensor_count}, Last sensor: {sensor_data is not None}")

                    # Log timing for GIL contention debugging
                    connection_start = time.time()
                    logger.debug(f"Client {unique_name} connection processing started at {connection_start}")

                    # Create client info
                    current_time = time.time()
                    client_info = ClientInfo(
                        client_id=client_id,
                        socket=client_socket,
                        address=str(address),
                        state=ClientState.CONNECTED,
                        last_activity=current_time,
                        unique_name=unique_name,
                        last_keepalive=current_time  # Initialize keepalive timer
                    )

                    with self.clients_lock:
                        self.clients[client_id] = client_info

                    # Start client handler thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_id,),
                        daemon=True
                    )
                    client_thread.start()

                    # Log completion timing
                    connection_end = time.time()
                    logger.debug(f"Client {unique_name} connection processing completed in {(connection_end - connection_start)*1000:.1f}ms")

            except Exception as e:
                if self.running:
                    logger.error(f"Error in server loop: {e}")
                    self.stats['errors'] += 1
                break

        logger.debug("Server loop stopped")

    def _handle_client(self, client_id: str):
        """Handle individual client connection"""
        logger.debug(f"Starting client handler for {client_id}")

        try:
            with self.clients_lock:
                if client_id not in self.clients:
                    logger.warning(f"🔍 CLIENT {client_id} NO LONGER IN CLIENTS DICT, exiting handler")
                    return
                client = self.clients[client_id]

            # Set socket to non-blocking mode for select()
            client.socket.setblocking(False)

            # Optimize socket buffer sizes to prevent write buffer overflow
            try:
                # Increase send buffer size to handle burst traffic
                client.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)  # 64KB send buffer
                # Increase receive buffer size for incoming commands
                client.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 32768)  # 32KB receive buffer
                logger.debug(f"🔧 Socket buffers optimized for {client_id}")
            except Exception as e:
                logger.warning(f"⚠️  Failed to optimize socket buffers for {client_id}: {e}")

            # Send welcome message
            welcome_msg = {
                'type': 'welcome',
                'client_id': client_id,
                'server_version': '1.0.0',
                'timestamp': time.time()
            }
            self._send_to_client(client_id, welcome_msg)

            # Send current status
            self._send_status_to_client(client_id)

            # Buffer for incomplete messages
            message_buffer = ""
            loop_count = 0

            while self.running:
                loop_count += 1
                if loop_count % 100 == 0:  # Log every 100 iterations
                    logger.debug(f"🔍 SOCKET LOOP for {client_id}: iteration {loop_count}")

                try:
                    # Check if client is still valid
                    with self.clients_lock:
                        if client_id not in self.clients:
                            logger.warning(f"🔍 CLIENT {client_id} NO LONGER IN CLIENTS DICT, exiting handler")
                            break
                        client = self.clients[client_id]

                    # Use select to check if data is available (with timeout)
                    logger.debug(f"🔍 SELECT: Checking for data on {client_id}")
                    ready, _, error = select.select([client.socket], [], [client.socket], 0.1)

                    logger.debug(f"🔍 SELECT RESULT for {client_id}: ready={len(ready)}, error={len(error)}")

                    if error:
                        logger.error(f"🔌 Socket error detected for {client_id}")
                        break

                    if ready:
                        logger.debug(f"🔍 SOCKET READY for {client_id}, attempting recv()")
                        # Data is available, read it
                        try:
                            data = client.socket.recv(4096)
                            if not data:
                                logger.info(f"🔌 Client {client_id} closed connection (no data)")
                                break

                            # Log raw data received
                            logger.debug(f"📥 RAW SOCKET DATA from {client_id}: {data[:200]}{'...' if len(data) > 200 else ''}")

                            # Update last activity
                            client.last_activity = time.time()

                            # Add to buffer
                            message_buffer += data.decode('utf-8')
                            logger.debug(f"📝 MESSAGE BUFFER for {client_id}: {len(message_buffer)} chars")

                        except socket.error as e:
                            if e.errno == errno.EAGAIN or e.errno == errno.EWOULDBLOCK:
                                # This shouldn't happen with select, but handle it
                                logger.debug(f"🔍 EAGAIN/EWOULDBLOCK for {client_id} (unexpected with select)")
                                continue
                            else:
                                logger.error(f"🔌 Socket error for {client_id}: {e}")
                                break

                        # Process complete messages from buffer
                        messages_processed = 0
                        start_time = time.time()
                        while '\n' in message_buffer:
                            line, message_buffer = message_buffer.split('\n', 1)
                            if line.strip():
                                messages_processed += 1
                                logger.debug(f"📨 PROCESSING MESSAGE #{messages_processed} from {client_id}: {line.strip()[:100]}{'...' if len(line.strip()) > 100 else ''}")

                                try:
                                    logger.debug(f"🔍 CALLING _process_client_message for {client_id}")
                                    self._process_client_message(client_id, line.strip())
                                    logger.debug(f"🔍 RETURNED from _process_client_message for {client_id}")
                                except Exception as e:
                                    logger.error(f"❌ EXCEPTION in _process_client_message for {client_id}: {e}")
                                    logger.error(f"❌ Message processing exception type: {type(e).__name__}")
                                    import traceback
                                    logger.error(f"❌ Message processing traceback: {traceback.format_exc()}")
                                    # Don't break the loop, just log the error

                                # Yield GIL after each message to prevent monopolization
                                time.sleep(0.0001)  # 0.1ms yield

                        if messages_processed > 0:
                            processing_time = (time.time() - start_time) * 1000  # Convert to ms
                            logger.debug(f"✅ PROCESSED {messages_processed} messages from {client_id} in {processing_time:.1f}ms")

                            # Warn if client is sending too many messages at once
                            if messages_processed > 5:
                                with self.clients_lock:
                                    client = self.clients.get(client_id)
                                    client_name = client.unique_name if client else client_id
                                logger.warning(f"⚠️  HIGH MESSAGE BURST from {client_name}: {messages_processed} messages in one batch")

                        logger.debug(f"🔍 CONTINUING SOCKET LOOP for {client_id} after processing {messages_processed} messages")

                    else:
                        # No data available, yield to other threads
                        logger.debug(f"🔍 NO DATA AVAILABLE for {client_id}, yielding")
                        time.sleep(0.001)  # 1ms yield

                except Exception as e:
                    logger.error(f"❌ Error handling client {client_id}: {e}")
                    logger.error(f"❌ Exception type: {type(e).__name__}")
                    logger.error(f"❌ Exception args: {e.args}")
                    import traceback
                    logger.error(f"❌ Traceback: {traceback.format_exc()}")
                    break

        except Exception as e:
            logger.error(f"Client handler error for {client_id}: {e}")
            logger.error(f"Handler exception type: {type(e).__name__}")
            logger.error(f"Handler exception args: {e.args}")
            import traceback
            logger.error(f"Handler traceback: {traceback.format_exc()}")
        finally:
            logger.info(f"🔍 CLIENT HANDLER EXITING for {client_id}")
            self._disconnect_client(client_id)

    def _process_client_message(self, client_id: str, message: str):
        """Process a message from a client"""
        try:
            data = json.loads(message)
            msg_type = data.get('type', '')

            # Get client info for detailed logging
            with self.clients_lock:
                client = self.clients.get(client_id)
                client_name = client.unique_name if client else client_id
                client_claimed_name = client.claimed_name if client else "unknown"

            # Log ALL incoming messages with client details
            logger.info(f"📨 COMMAND RECEIVED: {msg_type} from {client_name} ({client_claimed_name}) - Data: {data}")

            # Update client activity
            with self.clients_lock:
                if client_id in self.clients:
                    self.clients[client_id].last_activity = time.time()

            # Yield GIL briefly to prevent monopolization
            time.sleep(0.0001)  # 0.1ms yield

            if msg_type == 'ping':
                logger.debug(f"🏓 Processing PING from {client_name}")
                self._send_to_client(client_id, {'type': 'pong', 'timestamp': time.time()})

            elif msg_type == 'get_status':
                logger.debug(f"📊 Processing GET_STATUS from {client_name}")
                self._send_status_to_client(client_id)

            elif msg_type == 'keepalive':
                logger.info(f"💓 Processing KEEPALIVE from {client_name}")
                self._handle_keepalive(client_id, data)

            elif msg_type == 'tank_command':
                command = data.get('command', '').upper()
                value = data.get('value', 0)
                logger.info(f"🚗 Processing TANK_COMMAND from {client_name}: {command}={value}")
                # Apply rate limiting for motor commands
                if self._should_rate_limit_client(client_id):
                    logger.warning(f"⚠️  TANK_COMMAND DROPPED due to rate limiting: {client_name} - {command}={value}")
                    return  # Command dropped due to rate limiting
                self._handle_tank_command(client_id, data)

            elif msg_type == 'mecanum_command':
                motors = data.get('motors', {})
                logger.info(f"🎮 Processing MECANUM_COMMAND from {client_name}: {motors}")
                # Apply rate limiting for motor commands
                if self._should_rate_limit_client(client_id):
                    logger.warning(f"⚠️  MECANUM_COMMAND DROPPED due to rate limiting: {client_name} - {motors}")
                    return  # Command dropped due to rate limiting
                self._handle_mecanum_command(client_id, data)

            elif msg_type == 'set_priority':
                priority = data.get('priority', 10)
                logger.info(f"🔢 Processing SET_PRIORITY from {client_name}: priority={priority}")
                self._handle_set_priority(client_id, priority)

            elif msg_type == 'get_sensor_data':
                logger.debug(f"📡 Processing GET_SENSOR_DATA from {client_name}")
                self._send_sensor_data_to_client(client_id)

            elif msg_type == 'identify':
                name = data.get('name', 'Unknown')
                logger.info(f"🏷️  Processing IDENTIFY from {client_name}: name='{name}'")
                self._handle_client_identify(client_id, data)

            else:
                logger.warning(f"❓ UNKNOWN MESSAGE TYPE from {client_name}: {msg_type} - Data: {data}")
                self._send_to_client(client_id, {
                    'type': 'error',
                    'message': f'Unknown message type: {msg_type}'
                })

        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON DECODE ERROR from {client_id}: {e} - Raw message: '{message}'")
            self._send_to_client(client_id, {
                'type': 'error',
                'message': 'Invalid JSON format'
            })
        except Exception as e:
            logger.error(f"❌ MESSAGE PROCESSING ERROR from {client_id}: {e} - Message: '{message}'")
            self._send_to_client(client_id, {
                'type': 'error',
                'message': str(e)
            })

    def _handle_tank_command(self, client_id: str, data: Dict[str, Any]):
        """Handle tank-style motor command from client"""
        command = data.get('command', '').upper()
        value = data.get('value', 0)

        # Get client info for logging WITHOUT holding lock during method calls
        client_name = client_id
        with self.clients_lock:
            client = self.clients.get(client_id)
            if client:
                client_name = client.unique_name

        logger.info(f"🔧 HANDLING TANK_COMMAND: {command}={value} from {client_name}")

        # Handle KEEPALIVE command specially
        if command == 'KEEPALIVE':
            logger.info(f"💓 Sending KEEPALIVE to Arduino from {client_name}")

            # Update keepalive timestamp
            with self.clients_lock:
                if client_id in self.clients:
                    self.clients[client_id].last_keepalive = time.time()
                    self.clients[client_id].missed_keepalives = 0

            # Send keepalive to Arduino
            success = self.serial_controller.send_tank_command(command, value)

            logger.info(f"💓 KEEPALIVE result from {client_name}: {'✅ SUCCESS' if success else '❌ FAILED'}")

            # Send response to client
            response = {
                'type': 'tank_command_response',
                'command': command,
                'value': value,
                'success': success,
                'timestamp': time.time()
            }
            self._send_to_client(client_id, response)

            # Update stats
            self.stats['commands_processed'] += 1
            if not success:
                self.stats['errors'] += 1

            return

        # Check if client has control priority for non-keepalive commands (called WITHOUT holding lock)
        if not self._can_client_control(client_id):
            logger.warning(f"🚫 ACCESS DENIED for {client_name}: another client has higher priority")
            self._send_to_client(client_id, {
                'type': 'error',
                'message': f'Access denied - another client has higher priority (from {client_name})'
            })
            return

        # Validate command
        valid_commands = {'FORWARD', 'BACKWARD', 'LEFT', 'RIGHT', 'STOP', 'RESET',
                         'FORWARD_LEFT', 'FORWARD_RIGHT', 'BACKWARD_LEFT', 'BACKWARD_RIGHT'}

        if command not in valid_commands:
            logger.error(f"❌ INVALID TANK COMMAND from {client_name}: {command}")
            self._send_to_client(client_id, {
                'type': 'error',
                'message': f'Invalid tank command: {command} (from {client_name})'
            })
            return

        # Validate value range
        if not (0 <= value <= 255):
            logger.error(f"❌ INVALID VALUE from {client_name}: {value} (must be 0-255)")
            self._send_to_client(client_id, {
                'type': 'error',
                'message': f'Invalid value: {value}. Must be 0-255 (from {client_name})'
            })
            return

        # Send command to Arduino
        logger.info(f"📡 SENDING TO ARDUINO from {client_name}: {command}={value}")
        success = self.serial_controller.send_tank_command(command, value)
        logger.info(f"📡 ARDUINO RESPONSE for {client_name}: {'✅ SUCCESS' if success else '❌ FAILED'}")

        # Motor commands act as implicit keepalives - update keepalive timestamp
        with self.clients_lock:
            if client_id in self.clients:
                self.clients[client_id].last_keepalive = time.time()
                self.clients[client_id].missed_keepalives = 0
                logger.debug(f"💓 Tank command acts as keepalive for {client_name}")

        # Update stats
        self.stats['commands_processed'] += 1
        if not success:
            self.stats['errors'] += 1

        # Send response to client
        response = {
            'type': 'tank_command_response',
            'command': command,
            'value': value,
            'success': success,
            'timestamp': time.time()
        }
        self._send_to_client(client_id, response)

        # Set active client
        if success:
            self.active_client_id = client_id
            logger.debug(f"🎯 Active client set to: {client_name}")

    def _handle_mecanum_command(self, client_id: str, data: Dict[str, Any]):
        """Handle mecanum-style motor command from client"""
        # Get client info for logging WITHOUT holding lock during method calls
        client_name = client_id
        with self.clients_lock:
            client = self.clients.get(client_id)
            if client:
                client_name = client.unique_name

        logger.info(f"🎮 HANDLING MECANUM_COMMAND from {client_name}: {data}")

        # Check for KEEPALIVE command in mecanum format
        if data.get('command') == 'KEEPALIVE':
            logger.info(f"💓 Sending MECANUM KEEPALIVE to Arduino from {client_name}")

            # Update keepalive timestamp
            with self.clients_lock:
                if client_id in self.clients:
                    self.clients[client_id].last_keepalive = time.time()
                    self.clients[client_id].missed_keepalives = 0

            # Send keepalive to Arduino (using tank format for keepalive)
            success = self.serial_controller.send_tank_command('KEEPALIVE', 0)

            logger.info(f"💓 MECANUM KEEPALIVE result from {client_name}: {'✅ SUCCESS' if success else '❌ FAILED'}")

            # Send response to client
            response = {
                'type': 'mecanum_command_response',
                'command': 'KEEPALIVE',
                'success': success,
                'timestamp': time.time()
            }
            self._send_to_client(client_id, response)

            # Update stats
            self.stats['commands_processed'] += 1
            if not success:
                self.stats['errors'] += 1

            return

        # Check if client has control priority for motor commands (called WITHOUT holding lock)
        if not self._can_client_control(client_id):
            logger.warning(f"🚫 MECANUM ACCESS DENIED for {client_name}: another client has higher priority")
            self._send_to_client(client_id, {
                'type': 'error',
                'message': f'Access denied - another client has higher priority (from {client_name})'
            })
            return

        # Extract motor speeds
        motors = data.get('motors', {})
        left_front = motors.get('left_front', 0)
        left_rear = motors.get('left_rear', 0)
        right_front = motors.get('right_front', 0)
        right_rear = motors.get('right_rear', 0)

        logger.info(f"🎮 MECANUM MOTORS from {client_name}: LF={left_front}, LR={left_rear}, RF={right_front}, RR={right_rear}")

        # Validate motor speed ranges
        def validate_speed(speed, motor_name):
            if not isinstance(speed, (int, float)):
                return False, f'{motor_name} speed must be a number (from {client_name})'
            if not (-255 <= speed <= 255):
                return False, f'{motor_name} speed must be between -255 and 255 (from {client_name})'
            return True, None

        for speed, name in [(left_front, 'left_front'), (left_rear, 'left_rear'),
                           (right_front, 'right_front'), (right_rear, 'right_rear')]:
            valid, error_msg = validate_speed(speed, name)
            if not valid:
                logger.error(f"❌ INVALID MECANUM SPEED from {client_name}: {error_msg}")
                self._send_to_client(client_id, {
                    'type': 'error',
                    'message': error_msg
                })
                return

                # Send command to Arduino
        logger.info(f"📡 SENDING MECANUM TO ARDUINO from {client_name}: LF={int(left_front)}, LR={int(left_rear)}, RF={int(right_front)}, RR={int(right_rear)}")
        logger.debug(f"🔍 MECANUM: About to call serial_controller.send_mecanum_command")

        success = self.serial_controller.send_mecanum_command(
            int(left_front), int(left_rear), int(right_front), int(right_rear)
        )

        logger.debug(f"🔍 MECANUM: serial_controller.send_mecanum_command returned: {success}")
        logger.info(f"📡 MECANUM ARDUINO RESPONSE for {client_name}: {'✅ SUCCESS' if success else '❌ FAILED'}")

        # Motor commands act as implicit keepalives - update keepalive timestamp
        with self.clients_lock:
            if client_id in self.clients:
                self.clients[client_id].last_keepalive = time.time()
                self.clients[client_id].missed_keepalives = 0
                logger.debug(f"💓 Mecanum command acts as keepalive for {client_name}")

        # Update stats
        logger.debug(f"🔍 MECANUM: Updating stats")
        self.stats['commands_processed'] += 1
        if not success:
            self.stats['errors'] += 1

        # Send response to client
        logger.debug(f"🔍 MECANUM: Preparing response to client")
        response = {
            'type': 'mecanum_command_response',
            'motors': {
                'left_front': int(left_front),
                'left_rear': int(left_rear),
                'right_front': int(right_front),
                'right_rear': int(right_rear)
            },
            'success': success,
            'timestamp': time.time()
        }

        logger.debug(f"🔍 MECANUM: About to send response to client")
        self._send_to_client(client_id, response)
        logger.debug(f"🔍 MECANUM: Response sent to client")

        # Set active client
        if success:
            self.active_client_id = client_id
            logger.debug(f"🎯 Active client set to: {client_name}")

        logger.debug(f"🔍 MECANUM: _handle_mecanum_command COMPLETED for {client_name}")

    def _handle_keepalive(self, client_id: str, data: Dict[str, Any]):
        """Handle keepalive message from client"""
        # Check if client is actively sending motor commands
        should_process_keepalive = False
        client_name = client_id

        with self.clients_lock:
            if client_id in self.clients:
                client = self.clients[client_id]
                client_name = client.unique_name
                current_time = time.time()

                # Only process explicit keepalives if no recent motor commands
                # Motor commands act as implicit keepalives
                time_since_last_command = current_time - client.last_activity

                if time_since_last_command > 2.0:  # No motor commands in last 2 seconds
                    client.last_keepalive = current_time
                    client.missed_keepalives = 0  # Reset missed count
                    should_process_keepalive = True
                    logger.debug(f"💓 Keepalive processed for idle client {client.unique_name}")
                else:
                    # Client is actively sending commands, ignore explicit keepalive
                    logger.debug(f"💓 Keepalive ignored for active client {client.unique_name} (last command {time_since_last_command:.1f}s ago)")

        # Send keepalive response OUTSIDE the lock to prevent deadlock
        if should_process_keepalive:
            self._send_to_client(client_id, {
                'type': 'keepalive_response',
                'timestamp': time.time()
            })
        else:
            # Send a brief acknowledgment that keepalive was ignored due to activity
            self._send_to_client(client_id, {
                'type': 'keepalive_ignored',
                'reason': 'client_active',
                'timestamp': time.time()
            })

    def _handle_client_identify(self, client_id: str, data: Dict[str, Any]):
        """Handle client identification message"""
        claimed_name = data.get('name', 'Unknown')

        # Get client info and update claimed name
        unique_name = None
        with self.clients_lock:
            if client_id in self.clients:
                client = self.clients[client_id]
                client.claimed_name = claimed_name
                unique_name = client.unique_name

                logger.info(f"Client {client.unique_name} identifies as '{claimed_name}'")

        # Send identification response OUTSIDE the lock to prevent deadlock
        if unique_name:
            self._send_to_client(client_id, {
                'type': 'identify_response',
                'unique_name': unique_name,
                'claimed_name': claimed_name,
                'timestamp': time.time()
            })

    def _handle_set_priority(self, client_id: str, priority: int):
        """Handle client priority change"""
        # Update priority while holding lock
        priority_updated = False
        with self.clients_lock:
            if client_id in self.clients:
                self.clients[client_id].priority = max(0, min(100, priority))
                priority_updated = True

        # Send response OUTSIDE the lock to prevent deadlock
        if priority_updated:
            self._send_to_client(client_id, {
                'type': 'priority_updated',
                'priority': priority
            })

    def _can_client_control(self, client_id: str) -> bool:
        """Check if client can control the robot based on priority"""
        with self.clients_lock:
            if client_id not in self.clients:
                return False

            client_priority = self.clients[client_id].priority

            # Check if any other client has higher priority and is active
            for other_id, other_client in self.clients.items():
                if (other_id != client_id and
                    other_client.priority < client_priority and
                    time.time() - other_client.last_activity < 30):  # Active within 30 seconds
                    return False

            return True

    def _send_status_to_client(self, client_id: str):
        """Send server status to client"""
        with self.clients_lock:
            clients_info = [client.to_dict() for client in self.clients.values()]

        # Get current Arduino port information
        current_port = self.serial_controller.get_current_port()
        preferred_port = self.serial_controller.preferred_port

        status = {
            'type': 'status',
            'arduino_state': self.serial_controller.get_state().value,
            'arduino_connected': self.serial_controller.is_connected(),
            'arduino_current_port': current_port,
            'arduino_preferred_port': preferred_port,
            'active_client': self.active_client_id,
            'total_clients': len(self.clients),
            'clients': clients_info,
            'stats': self.stats.copy(),
            'timestamp': time.time()
        }
        self._send_to_client(client_id, status)

    def _send_sensor_data_to_client(self, client_id: str):
        """Send current sensor data to client"""
        sensor_data = self.serial_controller.get_sensor_data()
        if sensor_data:
            self._send_to_client(client_id, {
                'type': 'sensor_data',
                'data': asdict(sensor_data),
                'timestamp': time.time()
            })
        else:
            self._send_to_client(client_id, {
                'type': 'sensor_data',
                'data': None,
                'message': 'No sensor data available',
                'timestamp': time.time()
            })

    def _send_to_client(self, client_id: str, data: Dict[str, Any]):
        """Send data to a specific client"""
        logger.debug(f"🔍 _send_to_client CALLED for {client_id}")

        # Get client info without holding lock during socket operations
        client_socket = None
        client_name = client_id

        try:
            with self.clients_lock:
                if client_id in self.clients:
                    client = self.clients[client_id]
                    client_socket = client.socket
                    client_name = client.unique_name if client else client_id
                else:
                    logger.warning(f"🔍 _send_to_client: client {client_id} not found in clients dict")
                    return

            if client_socket is None:
                logger.warning(f"🔍 _send_to_client: no socket for {client_id}")
                return

            message = json.dumps(data) + '\n'
            message_bytes = message.encode('utf-8')

            # Log outgoing message
            logger.debug(f"📤 SENDING TO {client_name}: {data.get('type', 'unknown')} - {message[:200]}{'...' if len(message) > 200 else ''}")

            # Use select to check if socket is ready for writing (without holding lock)
            try:
                logger.debug(f"🔍 _send_to_client: calling select for write on {client_id}")
                _, ready, error = select.select([], [client_socket], [client_socket], 0.1)  # 100ms timeout

                logger.debug(f"🔍 _send_to_client: select result for {client_id}: ready={len(ready)}, error={len(error)}")

                if error:
                    logger.warning(f"🔌 Socket error during send to {client_name}")
                    self._disconnect_client(client_id)
                    return

                if ready:
                    # Socket is ready for writing
                    logger.debug(f"🔍 _send_to_client: socket ready, sending {len(message_bytes)} bytes to {client_id}")
                    bytes_sent = client_socket.send(message_bytes)
                    if bytes_sent < len(message_bytes):
                        logger.warning(f"⚠️  Partial send to {client_name}: {bytes_sent}/{len(message_bytes)} bytes")
                        # Handle partial sends by attempting to send the remaining data
                        remaining_data = message_bytes[bytes_sent:]
                        try:
                            # Try to send remaining data with a shorter timeout
                            _, ready2, error2 = select.select([], [client_socket], [client_socket], 0.05)
                            if ready2 and not error2:
                                bytes_sent2 = client_socket.send(remaining_data)
                                if bytes_sent + bytes_sent2 == len(message_bytes):
                                    logger.debug(f"✅ SENT TO {client_name}: {bytes_sent + bytes_sent2} bytes (partial send recovered)")
                                else:
                                    logger.error(f"❌ Failed to send complete message to {client_name}: {bytes_sent + bytes_sent2}/{len(message_bytes)} bytes")
                                    self._disconnect_client(client_id)
                                    return
                            else:
                                logger.error(f"❌ Failed to recover from partial send to {client_name}")
                                self._disconnect_client(client_id)
                                return
                        except Exception as e:
                            logger.error(f"❌ Error recovering from partial send to {client_name}: {e}")
                            self._disconnect_client(client_id)
                            return
                    else:
                        logger.debug(f"✅ SENT TO {client_name}: {bytes_sent} bytes")
                else:
                    logger.warning(f"⏰ Send timeout to {client_name} - socket not ready for write after 100ms")
                    # Disconnect client on persistent write timeout as it indicates a problem
                    logger.error(f"❌ Disconnecting {client_name} due to persistent write timeout")
                    self._disconnect_client(client_id)
                    return

            except socket.error as e:
                if e.errno == errno.EAGAIN or e.errno == errno.EWOULDBLOCK:
                    logger.warning(f"⚠️  Socket would block for {client_name}")
                else:
                    logger.error(f"❌ Socket error sending to {client_name}: {e}")
                    self._disconnect_client(client_id)

        except Exception as e:
            logger.error(f"❌ Error in _send_to_client for {client_id}: {e}")
            logger.error(f"❌ _send_to_client exception type: {type(e).__name__}")
            logger.error(f"❌ Message type: {data.get('type', 'unknown')}")
            logger.error(f"❌ Message size: {len(message_bytes) if 'message_bytes' in locals() else 'unknown'} bytes")
            import traceback
            logger.error(f"❌ _send_to_client traceback: {traceback.format_exc()}")
            self._disconnect_client(client_id)

        logger.debug(f"🔍 _send_to_client COMPLETED for {client_id}")

    def _broadcast_to_clients(self, data: Dict[str, Any], exclude_client: Optional[str] = None):
        """Broadcast data to all connected clients"""
        with self.clients_lock:
            client_ids = list(self.clients.keys())

        # Send to clients outside the lock to prevent blocking
        for client_id in client_ids:
            if client_id != exclude_client:
                self._send_to_client(client_id, data)

    def _disconnect_client(self, client_id: str):
        """Disconnect and remove a client"""
        logger.warning(f"🔍 _disconnect_client CALLED for {client_id}")
        import traceback
        logger.warning(f"🔍 _disconnect_client called from: {traceback.format_stack()[-2].strip()}")

        with self.clients_lock:
            if client_id in self.clients:
                client = self.clients[client_id]
                client_name = client.unique_name if client else client_id
                client_claimed_name = client.claimed_name if client else "unknown"
                connection_duration = time.time() - client.last_activity

                logger.info(f"🔌 DISCONNECTING CLIENT: {client_name} ({client_claimed_name}) - Connected for {connection_duration:.1f}s")
                logger.info(f"📊 Client stats: Commands={client.command_count}, Dropped={client.dropped_commands}, Missed keepalives={client.missed_keepalives}")

                try:
                    # Try to send a graceful disconnect message before closing
                    try:
                        disconnect_msg = json.dumps({'type': 'disconnect', 'reason': 'server_initiated', 'timestamp': time.time()}) + '\n'
                        client.socket.send(disconnect_msg.encode('utf-8'))
                        logger.debug(f"📤 Sent disconnect message to {client_name}")
                    except:
                        pass  # Ignore errors when sending disconnect message

                    client.socket.close()
                    logger.debug(f"✅ Socket closed for {client_name}")
                except Exception as e:
                    logger.warning(f"⚠️  Error closing socket for {client_name}: {e}")

                del self.clients[client_id]

                # Clear active client if this was it
                if self.active_client_id == client_id:
                    self.active_client_id = None
                    logger.info(f"🎯 Active client cleared (was {client_name})")

                logger.info(f"👋 Client {client_name} ({client_claimed_name}) disconnected")
            else:
                logger.warning(f"🔍 _disconnect_client: client {client_id} not found in clients dict")

    # Serial controller event handlers
    def _on_sensor_data(self, sensor_data: SensorData):
        """Handle new sensor data from Arduino"""
        # Debug: Log sensor data broadcasting
        with self.clients_lock:
            client_count = len(self.clients)

        if client_count > 0:
            # Temporarily disable rate limiting to debug deadlock issue
            logger.debug(f"Broadcasting sensor data to {client_count} clients")

            # Broadcast sensor data
            self._broadcast_to_clients({
                'type': 'sensor_data',
                'data': asdict(sensor_data),
                'timestamp': time.time()
            })
        else:
            # No clients connected, no need to broadcast
            pass

    def _on_status_message(self, message: str):
        """Handle status message from Arduino"""
        self._broadcast_to_clients({
            'type': 'arduino_message',
            'message': message,
            'timestamp': time.time()
        })

    def _on_connection_change(self, state: ConnectionState):
        """Handle Arduino connection state change"""
        current_port = self.serial_controller.get_current_port()

        self._broadcast_to_clients({
            'type': 'arduino_connection',
            'state': state.value,
            'current_port': current_port,
            'timestamp': time.time()
        })

        logger.info(f"Arduino connection state changed to: {state.value} (port: {current_port})")

    def _keepalive_monitor(self):
        """Monitor client keepalives and disconnect inactive clients"""
        logger.debug("Starting keepalive monitor")

        while self.running:
            try:
                current_time = time.time()
                clients_to_disconnect = []

                with self.clients_lock:
                    for client_id, client in self.clients.items():
                        # Check client activity - consider both explicit keepalives and motor commands
                        time_since_keepalive = current_time - client.last_keepalive
                        time_since_activity = current_time - client.last_activity

                        # Use the more recent of keepalive or activity as the "alive" indicator
                        time_since_alive = min(time_since_keepalive, time_since_activity)

                        if time_since_alive > self.keepalive_timeout:
                            client.missed_keepalives += 1
                            logger.debug(f"Client {client.unique_name} inactive for {time_since_alive:.1f}s (keepalive: {time_since_keepalive:.1f}s, activity: {time_since_activity:.1f}s) - missed #{client.missed_keepalives}")

                            if client.missed_keepalives >= self.max_missed_keepalives:
                                logger.warning(f"Client {client.unique_name} ({client_id}) inactive for {time_since_alive:.1f}s, missed {client.missed_keepalives} keepalives, disconnecting")
                                clients_to_disconnect.append(client_id)
                            else:
                                # Don't reset timer - let the client send keepalive or activity
                                pass
                        else:
                            # Client is active, reset missed keepalives counter
                            if client.missed_keepalives > 0:
                                logger.debug(f"Client {client.unique_name} is active (alive {time_since_alive:.1f}s ago), resetting missed keepalives")
                                client.missed_keepalives = 0

                # Disconnect clients outside the lock
                for client_id in clients_to_disconnect:
                    self._disconnect_client(client_id)

                time.sleep(1.0)  # Check every second

            except Exception as e:
                if self.running:
                    logger.error(f"Error in keepalive monitor: {e}")

        logger.debug("Keepalive monitor stopped")

    def _get_rate_limit_for_client(self, client_id: str) -> float:
        """Calculate rate limit for a client based on number of connected clients"""
        with self.clients_lock:
            num_clients = len(self.clients)

        if num_clients <= 1:
            return self.base_rate_limit

        # Distribute available bandwidth among clients
        rate_per_client = self.base_rate_limit / num_clients
        return max(rate_per_client, self.min_rate_limit)

    def _should_rate_limit_client(self, client_id: str) -> bool:
        """Check if client should be rate limited"""
        with self.clients_lock:
            client = self.clients.get(client_id)
            if not client:
                return True

            current_time = time.time()
            # Calculate rate limit inline to avoid nested lock acquisition
            num_clients = len(self.clients)
            if num_clients <= 1:
                rate_limit = self.base_rate_limit
            else:
                # Distribute available bandwidth among clients
                rate_per_client = self.base_rate_limit / num_clients
                rate_limit = max(rate_per_client, self.min_rate_limit)

            # Reset counter if enough time has passed
            if current_time - client.last_command_time >= 1.0:
                client.command_count = 0
                client.last_command_time = current_time

            # Check if client exceeds rate limit
            if client.command_count >= rate_limit:
                client.dropped_commands += 1
                self.stats['commands_dropped'] += 1

                # Log rate limiting (max once per second per client)
                if current_time - client.last_drop_log_time >= 1.0:
                    parsed_commands = client.command_count
                    total_received = parsed_commands + client.dropped_commands
                    logger.warning(f"Rate limiting {client.unique_name}: received {total_received} commands, parsed {parsed_commands}, dropped {client.dropped_commands}")
                    client.last_drop_log_time = current_time
                    # Reset dropped counter after logging
                    client.dropped_commands = 0

                return True

            # Allow command
            client.command_count += 1
            return False