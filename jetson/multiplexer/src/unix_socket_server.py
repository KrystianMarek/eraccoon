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

    def to_dict(self) -> Dict[str, Any]:
        return {
            'client_id': self.client_id,
            'address': self.address,
            'state': self.state.value,
            'last_activity': self.last_activity,
            'priority': self.priority
        }


class MotorProxyServer:
    """
    Unix socket server that provides multiplexed access to Arduino motor controller.
    Handles client connections, command queuing, and status broadcasting.
    """

    def __init__(self, socket_path: str = '/tmp/motor_controller.sock',
                 serial_port: Optional[str] = None, baud_rate: int = 115200):
        self.socket_path = socket_path
        self.server_socket: Optional[socket.socket] = None
        self.serial_controller = SerialController(serial_port, baud_rate)

        # Client management
        self.clients: Dict[str, ClientInfo] = {}
        self.clients_lock = threading.Lock()
        self.active_client_id: Optional[str] = None

        # Server state
        self.running = False
        self.server_thread: Optional[threading.Thread] = None

        # Command queuing
        self.command_queue: List[Dict[str, Any]] = []
        self.queue_lock = threading.Lock()

        # Statistics
        self.stats = {
            'start_time': time.time(),
            'total_connections': 0,
            'commands_processed': 0,
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
                    client_id = f"client_{int(time.time() * 1000) % 100000}"

                    logger.info(f"New client connected: {client_id}")
                    self.stats['total_connections'] += 1

                    # Create client info
                    client_info = ClientInfo(
                        client_id=client_id,
                        socket=client_socket,
                        address=str(address),
                        state=ClientState.CONNECTED,
                        last_activity=time.time()
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
                client = self.clients.get(client_id)

            if not client:
                return

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

            while self.running:
                try:
                    # Receive data from client
                    data = client.socket.recv(4096)
                    if not data:
                        break

                    # Update last activity
                    client.last_activity = time.time()

                    # Process received messages
                    messages = data.decode('utf-8').strip().split('\n')
                    for msg_str in messages:
                        if msg_str:
                            self._process_client_message(client_id, msg_str)

                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Error handling client {client_id}: {e}")
                    break

        except Exception as e:
            logger.error(f"Client handler error for {client_id}: {e}")
        finally:
            self._disconnect_client(client_id)

    def _process_client_message(self, client_id: str, message: str):
        """Process a message from a client"""
        try:
            data = json.loads(message)
            msg_type = data.get('type', '')

            logger.debug(f"Client {client_id} sent: {msg_type}")

            if msg_type == 'ping':
                self._send_to_client(client_id, {'type': 'pong', 'timestamp': time.time()})

            elif msg_type == 'get_status':
                self._send_status_to_client(client_id)

            elif msg_type == 'motor_command':
                self._handle_motor_command(client_id, data)

            elif msg_type == 'set_priority':
                self._handle_set_priority(client_id, data.get('priority', 10))

            elif msg_type == 'get_sensor_data':
                self._send_sensor_data_to_client(client_id)

            else:
                self._send_to_client(client_id, {
                    'type': 'error',
                    'message': f'Unknown message type: {msg_type}'
                })

        except json.JSONDecodeError:
            self._send_to_client(client_id, {
                'type': 'error',
                'message': 'Invalid JSON format'
            })
        except Exception as e:
            logger.error(f"Error processing message from {client_id}: {e}")
            self._send_to_client(client_id, {
                'type': 'error',
                'message': str(e)
            })

    def _handle_motor_command(self, client_id: str, data: Dict[str, Any]):
        """Handle motor command from client"""
        command = data.get('command', '').upper()
        value = data.get('value', 0)

        # Check if client has control priority
        if not self._can_client_control(client_id):
            self._send_to_client(client_id, {
                'type': 'error',
                'message': 'Access denied - another client has higher priority'
            })
            return

        # Validate command
        valid_commands = {'FORWARD', 'BACKWARD', 'LEFT', 'RIGHT', 'STOP', 'RESET',
                         'FORWARD_LEFT', 'FORWARD_RIGHT', 'BACKWARD_LEFT', 'BACKWARD_RIGHT'}

        if command not in valid_commands:
            self._send_to_client(client_id, {
                'type': 'error',
                'message': f'Invalid command: {command}'
            })
            return

        # Validate value range
        if not (0 <= value <= 255):
            self._send_to_client(client_id, {
                'type': 'error',
                'message': f'Invalid value: {value}. Must be 0-255'
            })
            return

        # Send command to Arduino
        success = self.serial_controller.send_command(command, value)

        # Update stats
        self.stats['commands_processed'] += 1
        if not success:
            self.stats['errors'] += 1

        # Send response to client
        response = {
            'type': 'command_response',
            'command': command,
            'value': value,
            'success': success,
            'timestamp': time.time()
        }
        self._send_to_client(client_id, response)

        # Set active client
        if success:
            self.active_client_id = client_id

    def _handle_set_priority(self, client_id: str, priority: int):
        """Handle client priority change"""
        with self.clients_lock:
            if client_id in self.clients:
                self.clients[client_id].priority = max(0, min(100, priority))
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
        try:
            with self.clients_lock:
                if client_id in self.clients:
                    client = self.clients[client_id]
                    message = json.dumps(data) + '\n'
                    client.socket.send(message.encode('utf-8'))
        except Exception as e:
            logger.error(f"Error sending to client {client_id}: {e}")
            self._disconnect_client(client_id)

    def _broadcast_to_clients(self, data: Dict[str, Any], exclude_client: Optional[str] = None):
        """Broadcast data to all connected clients"""
        with self.clients_lock:
            for client_id in list(self.clients.keys()):
                if client_id != exclude_client:
                    self._send_to_client(client_id, data)

    def _disconnect_client(self, client_id: str):
        """Disconnect and remove a client"""
        with self.clients_lock:
            if client_id in self.clients:
                client = self.clients[client_id]
                try:
                    client.socket.close()
                except:
                    pass
                del self.clients[client_id]

                # Clear active client if this was it
                if self.active_client_id == client_id:
                    self.active_client_id = None

                logger.info(f"Client {client_id} disconnected")

    # Serial controller event handlers
    def _on_sensor_data(self, sensor_data: SensorData):
        """Handle new sensor data from Arduino"""
        self._broadcast_to_clients({
            'type': 'sensor_data',
            'data': asdict(sensor_data),
            'timestamp': time.time()
        })

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