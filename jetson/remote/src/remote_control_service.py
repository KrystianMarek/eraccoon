#!/usr/bin/env python3
"""
Remote Control Service

Main service that coordinates controller input, Mecanum wheel calculations,
and either robot simulation (development mode) or socket communication (production mode).
"""

import logging
import time
import threading
import platform
from typing import Optional

from .controller_handler import ControllerHandler, ControllerButton
from .mecanum_calculator import MecanumCalculator, MotorSpeeds
from .robot_simulator import RobotSimulator
from .socket_client import SocketClient
from enum import Enum

logger = logging.getLogger(__name__)


class DriveMode(Enum):
    """Robot drive modes"""
    TANK = "tank"
    MECANUM = "mecanum"


class ConnectionState(Enum):
    """Connection states for client-server architecture"""
    DISCONNECTED = "disconnected"
    CONTROLLER_CONNECTED = "controller_connected"
    FULLY_CONNECTED = "fully_connected"


class RemoteControlService:
    """
    Remote Control Service for Mecanum Wheel Robot

    Coordinates all components to provide seamless remote control functionality.
    Supports both development mode (with simulation) and production mode (with socket communication).
    """

    def __init__(self, mode: str = 'development',
                 controller_device: str = '/dev/input/js0',
                 socket_path: str = '/tmp/motor-proxy/motor_controller.sock',
                 simulation_width: int = 800,
                 simulation_height: int = 600):
        """
        Initialize the remote control service

        Args:
            mode: Operation mode ('development' or 'production')
            controller_device: Path to controller device
            socket_path: Unix socket path for production mode
            simulation_width: Simulation window width for development mode
            simulation_height: Simulation window height for development mode
        """
        self.mode = mode
        self.running = False
        self.controller_device = controller_device
        self.socket_path = socket_path

        # Detect platform for threading considerations
        self.is_macos = platform.system() == "Darwin"

        # Initialize core components
        self.controller: Optional[ControllerHandler] = None
        self.mecanum_calc = MecanumCalculator(max_speed=1.0)

        # Mode-specific components
        if mode == 'development':
            self.simulator = RobotSimulator(simulation_width, simulation_height)
            self.socket_client = None
            logger.info("🛠️  Initialized for development mode with simulation")
        else:  # production
            self.simulator = None
            self.socket_client = None  # Will be created when controller connects
            logger.info("🏭 Initialized for production mode with socket communication")

        # Control state
        self.current_motor_speeds = MotorSpeeds()
        self.previous_motor_speeds = MotorSpeeds()  # Track previous speeds for change detection
        self.emergency_stop = False
        self.precision_mode = False
        self.boost_mode = False

        # Drive mode
        self.drive_mode = DriveMode.MECANUM  # Start in mecanum mode

        # Connection state management
        self.connection_state = ConnectionState.DISCONNECTED
        self.last_controller_check = 0
        self.controller_check_interval = 15.0  # Check for controller every 15 seconds

        # Socket communication rate limiting
        self.last_socket_send_time = 0
        self.socket_send_interval = 0.1  # Send to socket at most every 100ms (10 Hz)
        self.pending_socket_send = False  # Flag to indicate data needs to be sent

        # Periodic status checks to prevent Arduino timeout
        self.last_status_check_time = 0
        self.status_check_interval = 2.0  # Check status every 2 seconds to prevent 3-second timeout

        if mode == 'production':
            logger.info(f"🕐 Socket rate limiting enabled: max {1/self.socket_send_interval:.0f} Hz ({self.socket_send_interval*1000:.0f}ms intervals)")
            logger.info(f"💓 Status checks enabled: every {self.status_check_interval:.1f}s to prevent Arduino timeout")

        # Threading
        self.update_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        logger.info(f"🖥️  Remote control server initialized in {mode} mode")
        logger.info("⏳ Waiting for controller (client) connection...")

    def _setup_controller_callbacks(self):
        """Setup controller event callbacks"""
        if self.controller:
            self.controller.on_button_press = self._on_button_press
            self.controller.on_button_release = self._on_button_release

    def _setup_socket_callbacks(self):
        """Setup socket client callbacks"""
        if self.socket_client:
            self.socket_client.on_status_update = self._on_socket_status_update
            self.socket_client.on_arduino_message = self._on_arduino_message
            self.socket_client.on_connection_change = self._on_socket_connection_change

    def _try_connect_controller(self) -> bool:
        """Try to connect to controller"""
        try:
            if self.controller:
                # Already have a controller, check if it's still connected
                if self.controller.is_connected():
                    return True
                else:
                    logger.info("🎮 Controller disconnected, cleaning up...")
                    self._disconnect_controller()

            # Try to create and connect new controller
            logger.debug("🔍 Looking for controller...")
            self.controller = ControllerHandler(self.controller_device)

            if self.controller.connect():
                logger.info("✅ Controller (client) connected!")
                self._setup_controller_callbacks()
                self.connection_state = ConnectionState.CONTROLLER_CONNECTED

                # Connect to socket in production mode
                if self.mode == 'production':
                    self._connect_socket()

                return True
            else:
                # Clean up failed connection attempt
                self.controller = None
                return False

        except Exception as e:
            logger.debug(f"Controller connection failed: {e}")
            self.controller = None
            return False

    def _disconnect_controller(self):
        """Disconnect controller and associated services"""
        if self.controller:
            logger.info("🎮 Disconnecting controller...")
            try:
                self.controller.disconnect()
            except:
                pass
            self.controller = None

        # Disconnect socket if connected
        if self.mode == 'production':
            self._disconnect_socket()

        self.connection_state = ConnectionState.DISCONNECTED
        self.current_motor_speeds = MotorSpeeds()  # Reset motor speeds
        logger.info("⏳ Waiting for controller (client) reconnection...")

    def _connect_socket(self):
        """Connect to socket server"""
        if self.mode != 'production':
            return

        try:
            if not self.socket_client:
                self.socket_client = SocketClient(self.socket_path)
                self._setup_socket_callbacks()

            if self.socket_client.connect():
                logger.info("🔌 Connected to motor controller socket")
                self.socket_client.set_priority(1)
                self.connection_state = ConnectionState.FULLY_CONNECTED
            else:
                logger.warning("⚠️  Failed to connect to motor controller socket")

        except Exception as e:
            logger.warning(f"Socket connection failed: {e}")

    def _disconnect_socket(self):
        """Disconnect from socket server"""
        if self.socket_client:
            logger.info("🔌 Disconnecting from motor controller socket")
            try:
                self.socket_client.disconnect()
            except:
                pass
            self.socket_client = None

    def run(self):
        """Run the remote control service (server)"""
        try:
            if not self._initialize():
                return False

            self.running = True
            logger.info("🖥️  Remote control server started")

            # Choose main loop based on mode and platform
            if self.mode == 'development':
                self._run_development_server_loop()
            else:
                if self.is_macos:
                    # On macOS, keep everything on main thread
                    self._run_production_server_loop_main_thread()
                else:
                    # On Linux, can use background thread for controller updates
                    self._run_production_server_loop_threaded()

        except KeyboardInterrupt:
            logger.info("🛑 Received interrupt signal")
        except Exception as e:
            logger.error(f"💥 Service error: {e}")
        finally:
            self._cleanup()

    def _initialize(self) -> bool:
        """Initialize server components"""
        logger.info("🚀 Initializing remote control server...")

        # Initialize mode-specific components
        if self.mode == 'development':
            if not self.simulator.start():
                logger.error("❌ Failed to start simulator")
                return False

        # Note: Controller and socket connections are handled in the main loop
        # based on client connection state

        logger.info("✅ Server components initialized successfully")
        return True

    def _run_development_server_loop(self):
        """Main server loop for development mode - handles client connections"""
        logger.info("🛠️  Starting development server loop...")

        while self.running and self.simulator.is_running():
            current_time = time.time()

            # Check for controller (client) connection periodically
            if (self.connection_state == ConnectionState.DISCONNECTED and
                current_time - self.last_controller_check >= self.controller_check_interval):

                if self._try_connect_controller():
                    logger.info("🎮 Controller client connected to development server")

                self.last_controller_check = current_time

            # If controller is connected, update it
            if self.controller and self.controller.is_connected():
                if not self.controller.update():
                    logger.info("🎮 Controller client disconnected")
                    self._disconnect_controller()
                else:
                    # Calculate motor speeds based on controller input
                    self._update_motor_speeds()

            # Always update simulator (even without controller)
            if not self.simulator.update(self.current_motor_speeds):
                break

            # Small delay to prevent excessive CPU usage
            time.sleep(0.001)

        logger.info("Development server loop ended")

    def _run_production_server_loop_main_thread(self):
        """Main server loop for production mode on macOS - everything on main thread"""
        logger.info("🏭 Starting production server loop (main thread)...")

        last_status_check = 0
        status_check_interval = 5.0  # Check status every 5 seconds

        while self.running:
            current_time = time.time()

            # Check for controller (client) connection periodically
            if (self.connection_state == ConnectionState.DISCONNECTED and
                current_time - self.last_controller_check >= self.controller_check_interval):

                if self._try_connect_controller():
                    logger.info("🎮 Controller client connected to production server")

                self.last_controller_check = current_time

            # If controller is connected, update it
            if self.controller and self.controller.is_connected():
                if not self.controller.update():
                    logger.info("🎮 Controller client disconnected")
                    self._disconnect_controller()
                else:
                    # Calculate motor speeds based on controller input
                    self._update_motor_speeds()

                    # Send commands if socket is connected
                    if (self.socket_client and self.socket_client.is_connected()
                        and self.connection_state == ConnectionState.FULLY_CONNECTED):
                        self._send_motor_commands()

            # Periodically check socket connection status
            if current_time - last_status_check > status_check_interval:
                if self.socket_client and self.socket_client.is_connected():
                    self.socket_client.get_status()
                last_status_check = current_time

            # Sleep to prevent excessive CPU usage
            time.sleep(0.02)  # 50 Hz update rate

        logger.info("Production server loop ended")

    def _run_production_server_loop_threaded(self):
        """Main server loop for production mode with background thread (Linux)"""
        logger.info("🏭 Starting production server loop (threaded)...")

        # Start update thread for controller
        self.update_thread = threading.Thread(target=self._update_loop_threaded, daemon=True)
        self.update_thread.start()

        last_status_check = 0
        status_check_interval = 5.0  # Check status every 5 seconds

        while self.running:
            current_time = time.time()

            # Check for controller (client) connection periodically
            if (self.connection_state == ConnectionState.DISCONNECTED and
                current_time - self.last_controller_check >= self.controller_check_interval):

                if self._try_connect_controller():
                    logger.info("🎮 Controller client connected to production server")

                self.last_controller_check = current_time

            # Periodically check socket connection status
            if current_time - last_status_check > status_check_interval:
                if self.socket_client and self.socket_client.is_connected():
                    self.socket_client.get_status()
                last_status_check = current_time

            # Sleep to prevent excessive CPU usage
            time.sleep(0.1)

        logger.info("Production server loop ended")

    def _update_loop_threaded(self):
        """Background update loop for controller and motor calculations (Linux only)"""
        logger.debug("Update loop started (threaded)")

        while self.running and not self.stop_event.is_set():
            try:
                # Only process if controller is connected
                if self.controller and self.controller.is_connected():
                    # Update controller state
                    if not self.controller.update():
                        logger.info("🎮 Controller client disconnected (threaded)")
                        self._disconnect_controller()
                    else:
                        # Calculate motor speeds based on controller input
                        self._update_motor_speeds()

                        # Send commands if socket is connected
                        if (self.socket_client and self.socket_client.is_connected()
                            and self.connection_state == ConnectionState.FULLY_CONNECTED):
                            self._send_motor_commands()

                # Periodic status check to prevent Arduino timeout
                current_time = time.time()
                if (self.socket_client and self.socket_client.is_connected() and
                    current_time - self.last_status_check_time >= self.status_check_interval):
                    try:
                        self.socket_client.get_status()
                        self.last_status_check_time = current_time
                    except Exception as e:
                        logger.debug(f"Status check failed: {e}")

                # Small delay for update loop
                time.sleep(0.02)  # 50 Hz update rate

            except Exception as e:
                logger.error(f"Error in update loop: {e}")
                break

        logger.debug("Update loop ended (threaded)")

    def _update_motor_speeds(self):
        """Update motor speeds based on controller input"""
        if not self.controller or not self.controller.is_connected():
            self.current_motor_speeds = MotorSpeeds()
            return

        # Get movement vector from controller
        forward, strafe, rotation = self.controller.get_movement_vector()

        # Apply drive mode restrictions
        if self.drive_mode == DriveMode.TANK:
            # Tank mode: only use left stick (forward/backward), ignore strafe and right stick rotation
            # Use left stick X for rotation instead of right stick
            left_stick_x = self.controller.get_state().left_stick_x
            forward = forward  # Keep forward/backward from left stick Y
            strafe = 0.0      # No strafing in tank mode
            rotation = left_stick_x  # Use left stick X for rotation

        # Apply speed modifier
        speed_modifier = self.controller.get_speed_modifier()

        # Apply emergency stop
        if self.emergency_stop:
            forward = strafe = rotation = 0.0

        # Calculate motor speeds
        motor_speeds = self.mecanum_calc.calculate_motor_speeds(forward, strafe, rotation)

        # Apply speed modifier
        new_motor_speeds = motor_speeds.scale(speed_modifier)

        # Log significant changes at DATA level
        if self._motor_speeds_changed(new_motor_speeds):
            mode_indicator = "🚗" if self.drive_mode == DriveMode.TANK else "🤖"
            logger.data(f"{mode_indicator} Motor speeds [{self.drive_mode.value.upper()}]: "
                       f"F={forward:.2f}, S={strafe:.2f}, R={rotation:.2f}, "
                       f"Speed={speed_modifier:.2f} -> LF={new_motor_speeds.left_front:.2f}, "
                       f"LR={new_motor_speeds.left_rear:.2f}, "
                       f"RF={new_motor_speeds.right_front:.2f}, "
                       f"RR={new_motor_speeds.right_rear:.2f}")
            logger.debug(f"Motor speeds updated [{self.drive_mode.value}]: "
                        f"F={forward:.2f}, S={strafe:.2f}, R={rotation:.2f}, "
                        f"Speed={speed_modifier:.2f}")

        # Update motor speeds
        self.previous_motor_speeds = self.current_motor_speeds
        self.current_motor_speeds = new_motor_speeds

        # Mark that we have new data to send (rate-limited sending)
        if self.mode == 'production':
            # Only mark pending if we actually need to send a command
            if self._should_send_command(new_motor_speeds):
                self.pending_socket_send = True

    def _send_motor_commands(self):
        """Send motor commands via socket client with rate limiting"""
        if not self.socket_client or not self.socket_client.is_connected():
            return

        # Check if we have pending data and enough time has passed
        current_time = time.time()
        if not self.pending_socket_send:
            return

        if current_time - self.last_socket_send_time < self.socket_send_interval:
            return  # Too soon, wait for next cycle

        # Send the command
        if self.drive_mode == DriveMode.MECANUM:
            # Send mecanum command with individual motor speeds
            # Convert from -1.0..1.0 to -255..255 range
            left_front = int(self.current_motor_speeds.left_front * 255)
            left_rear = int(self.current_motor_speeds.left_rear * 255)
            right_front = int(self.current_motor_speeds.right_front * 255)
            right_rear = int(self.current_motor_speeds.right_rear * 255)

            # Log the mecanum command being sent at DATA level
            logger.data(f"🤖 Mecanum command: LF={left_front}, LR={left_rear}, RF={right_front}, RR={right_rear}")

            # Send mecanum command
            self.socket_client.send_mecanum_command(left_front, left_rear, right_front, right_rear)

        else:  # TANK mode
            # Convert motor speeds to tank command
            command, value = self.mecanum_calc.convert_to_multiplexer_command(self.current_motor_speeds)

            # Log the tank command being sent at DATA level
            logger.data(f"🚗 Tank command: {command}:{value}")

            # Send tank command
            self.socket_client.send_tank_command(command, value)

        # Update timing and clear pending flag
        self.last_socket_send_time = current_time
        self.pending_socket_send = False

    def _motor_speeds_changed(self, new_speeds: MotorSpeeds) -> bool:
        """Check if motor speeds have changed significantly"""
        threshold = 0.01  # Only log changes greater than 1%

        # Check if any motor speed changed significantly
        return (abs(new_speeds.left_front - self.current_motor_speeds.left_front) > threshold or
                abs(new_speeds.left_rear - self.current_motor_speeds.left_rear) > threshold or
                abs(new_speeds.right_front - self.current_motor_speeds.right_front) > threshold or
                abs(new_speeds.right_rear - self.current_motor_speeds.right_rear) > threshold)

    def _should_send_command(self, new_speeds: MotorSpeeds) -> bool:
        """Check if we should send a command (non-zero or significant change)"""
        # Always send if any motor speed is non-zero (robot is moving)
        if (abs(new_speeds.left_front) > 0.01 or abs(new_speeds.left_rear) > 0.01 or
            abs(new_speeds.right_front) > 0.01 or abs(new_speeds.right_rear) > 0.01):
            return True

        # Send stop command only if we were previously moving
        if (abs(self.current_motor_speeds.left_front) > 0.01 or abs(self.current_motor_speeds.left_rear) > 0.01 or
            abs(self.current_motor_speeds.right_front) > 0.01 or abs(self.current_motor_speeds.right_rear) > 0.01):
            return True

        # Don't send if already stopped
        return False

    def _on_button_press(self, button: ControllerButton):
        """Handle controller button press events"""
        logger.debug(f"Button pressed: {button.name}")

        if button == ControllerButton.CIRCLE:
            # Emergency stop
            self.emergency_stop = True
            logger.warning("🚨 Emergency stop activated!")

        elif button == ControllerButton.SQUARE:
            # Reset/resume
            self.emergency_stop = False
            logger.info("✅ Emergency stop deactivated")

        elif button == ControllerButton.TRIANGLE:
            # Test movement patterns (development mode only)
            if self.mode == 'development':
                self._test_movement_patterns()

        elif button == ControllerButton.OPTIONS:
            # Switch drive mode (button physically labeled L1 on your controller)
            if self.drive_mode == DriveMode.MECANUM:
                self.drive_mode = DriveMode.TANK
                logger.info("🚗 Switched to TANK drive mode")
            else:
                self.drive_mode = DriveMode.MECANUM
                logger.info("🤖 Switched to MECANUM drive mode")

        elif button == ControllerButton.L1:
            # Precision mode (restored to L1)
            self.precision_mode = True
            logger.info("🎯 Precision mode activated")

        elif button == ControllerButton.R1:
            # Boost mode
            self.boost_mode = True
            logger.info("🚀 Boost mode activated")

    def _on_button_release(self, button: ControllerButton):
        """Handle controller button release events"""
        logger.debug(f"Button released: {button.name}")

        if button == ControllerButton.L1:
            self.precision_mode = False
            logger.info("🎯 Precision mode deactivated")

        elif button == ControllerButton.R1:
            self.boost_mode = False
            logger.info("🚀 Boost mode deactivated")

    def _test_movement_patterns(self):
        """Test predefined movement patterns (development mode)"""
        if self.mode != 'development':
            return

        logger.info("🧪 Testing movement patterns...")
        test_patterns = [
            'forward', 'backward', 'left', 'right',
            'forward_left', 'forward_right',
            'rotate_left', 'rotate_right'
        ]

        for pattern in test_patterns:
            logger.info(f"Testing: {pattern}")
            speeds = self.mecanum_calc.calculate_predefined_movement(pattern, 0.3)
            self.current_motor_speeds = speeds
            time.sleep(0.5)

        # Stop after test
        self.current_motor_speeds = MotorSpeeds()
        logger.info("🧪 Movement pattern test completed")

    def _on_socket_status_update(self, status_data: dict):
        """Handle status updates from socket client"""
        arduino_connected = status_data.get('arduino_connected', False)
        arduino_state = status_data.get('arduino_state', 'unknown')

        logger.debug(f"📊 Arduino status: {arduino_state} (connected: {arduino_connected})")

        if not arduino_connected:
            logger.warning("⚠️  Arduino not connected - commands may not be executed")

    def _on_arduino_message(self, message: str):
        """Handle Arduino messages from socket client"""
        logger.info(f"🤖 Arduino: {message}")

    def _on_socket_connection_change(self, connected: bool):
        """Handle socket connection changes"""
        if connected:
            logger.info("✅ Connected to motor controller")
        else:
            logger.warning("❌ Disconnected from motor controller")
            if self.running:
                logger.info("🔄 Attempting to reconnect...")
                # Could implement reconnection logic here

    def stop(self):
        """Stop the remote control service"""
        logger.info("🛑 Stopping remote control service...")
        self.running = False
        self.stop_event.set()

        # Wait for update thread to finish
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=2.0)

    def _cleanup(self):
        """Clean up all server resources"""
        logger.info("🧹 Cleaning up server resources...")

        # Stop all motors first
        if self.socket_client and self.socket_client.is_connected():
            try:
                self.socket_client.stop_robot()
            except:
                pass

        # Clean up components
        if self.controller:
            try:
                self.controller.cleanup()
            except:
                pass

        if self.simulator:
            try:
                self.simulator.cleanup()
            except:
                pass

        if self.socket_client:
            try:
                self.socket_client.cleanup()
            except:
                pass

        logger.info("👋 Remote control server stopped")

    def is_running(self) -> bool:
        """Check if service is running"""
        return self.running

    def get_current_motor_speeds(self) -> MotorSpeeds:
        """Get current motor speeds"""
        return self.current_motor_speeds

    def is_emergency_stopped(self) -> bool:
        """Check if emergency stop is active"""
        return self.emergency_stop