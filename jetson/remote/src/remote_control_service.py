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

logger = logging.getLogger(__name__)


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

        # Detect platform for threading considerations
        self.is_macos = platform.system() == "Darwin"

        # Initialize components
        self.controller = ControllerHandler(controller_device)
        self.mecanum_calc = MecanumCalculator(max_speed=1.0)

        # Mode-specific components
        if mode == 'development':
            self.simulator = RobotSimulator(simulation_width, simulation_height)
            self.socket_client = None
            logger.info("🛠️  Initialized for development mode with simulation")
        else:  # production
            self.simulator = None
            self.socket_client = SocketClient(socket_path)
            logger.info("🏭 Initialized for production mode with socket communication")

        # Control state
        self.current_motor_speeds = MotorSpeeds()
        self.emergency_stop = False
        self.precision_mode = False
        self.boost_mode = False

        # Update thread (only for production mode on non-macOS)
        self.update_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        # Setup controller callbacks
        self._setup_controller_callbacks()

        logger.info(f"Remote control service initialized in {mode} mode")

    def _setup_controller_callbacks(self):
        """Setup controller event callbacks"""
        self.controller.on_button_press = self._on_button_press
        self.controller.on_button_release = self._on_button_release

        if self.socket_client:
            # Setup socket client callbacks for production mode
            self.socket_client.on_status_update = self._on_socket_status_update
            self.socket_client.on_arduino_message = self._on_arduino_message
            self.socket_client.on_connection_change = self._on_socket_connection_change

    def run(self):
        """Run the remote control service"""
        try:
            if not self._initialize():
                return False

            self.running = True

            # Choose main loop based on mode and platform
            if self.mode == 'development':
                self._run_development_loop()
            else:
                if self.is_macos:
                    # On macOS, keep everything on main thread
                    self._run_production_loop_main_thread()
                else:
                    # On Linux, can use background thread for controller updates
                    self._run_production_loop_threaded()

        except KeyboardInterrupt:
            logger.info("🛑 Received interrupt signal")
        except Exception as e:
            logger.error(f"💥 Service error: {e}")
        finally:
            self._cleanup()

    def _initialize(self) -> bool:
        """Initialize all components"""
        logger.info("🚀 Initializing remote control service...")

        # Connect controller
        if not self.controller.connect():
            logger.error("❌ Failed to connect to controller")
            return False

        # Initialize mode-specific components
        if self.mode == 'development':
            if not self.simulator.start():
                logger.error("❌ Failed to start simulator")
                return False
        else:  # production
            if not self.socket_client.connect():
                logger.error("❌ Failed to connect to motor controller")
                return False

            # Set high priority for real-time control
            self.socket_client.set_priority(1)

        logger.info("✅ All components initialized successfully")
        return True

    def _run_development_loop(self):
        """Main loop for development mode - everything on main thread for macOS compatibility"""
        logger.info("🛠️  Starting development mode loop...")

        while self.running and self.simulator.is_running():
            # Update controller state on main thread (required for macOS)
            if not self.controller.update():
                logger.warning("Controller disconnected")
                break

            # Calculate motor speeds based on controller input
            self._update_motor_speeds()

            # Update simulator
            if not self.simulator.update(self.current_motor_speeds):
                break

            # Small delay to prevent excessive CPU usage
            time.sleep(0.001)

        logger.info("Development mode loop ended")

    def _run_production_loop_main_thread(self):
        """Main loop for production mode on macOS - everything on main thread"""
        logger.info("🏭 Starting production mode loop (main thread)...")

        last_status_check = 0
        status_check_interval = 5.0  # Check status every 5 seconds

        while self.running:
            # Update controller state on main thread (required for macOS)
            if not self.controller.update():
                logger.warning("Controller disconnected")
                break

            # Calculate motor speeds based on controller input
            self._update_motor_speeds()

            # Send commands
            if self.socket_client:
                self._send_motor_commands()

            # Periodically check connection status
            current_time = time.time()
            if current_time - last_status_check > status_check_interval:
                if self.socket_client and self.socket_client.is_connected():
                    self.socket_client.get_status()
                last_status_check = current_time

            # Sleep to prevent excessive CPU usage
            time.sleep(0.02)  # 50 Hz update rate

        logger.info("Production mode loop ended")

    def _run_production_loop_threaded(self):
        """Main loop for production mode with background thread (Linux)"""
        logger.info("🏭 Starting production mode loop (threaded)...")

        # Start update thread for controller
        self.update_thread = threading.Thread(target=self._update_loop_threaded, daemon=True)
        self.update_thread.start()

        last_status_check = 0
        status_check_interval = 5.0  # Check status every 5 seconds

        while self.running:
            # Periodically check connection status
            current_time = time.time()
            if current_time - last_status_check > status_check_interval:
                if self.socket_client and self.socket_client.is_connected():
                    self.socket_client.get_status()
                last_status_check = current_time

            # Sleep to prevent excessive CPU usage
            time.sleep(0.1)

        logger.info("Production mode loop ended")

    def _update_loop_threaded(self):
        """Background update loop for controller and motor calculations (Linux only)"""
        logger.debug("Update loop started (threaded)")

        while self.running and not self.stop_event.is_set():
            try:
                # Update controller state
                if not self.controller.update():
                    logger.warning("Controller disconnected")
                    break

                # Calculate motor speeds based on controller input
                self._update_motor_speeds()

                # Send commands if in production mode
                if self.socket_client:
                    self._send_motor_commands()

                # Small delay for update loop
                time.sleep(0.02)  # 50 Hz update rate

            except Exception as e:
                logger.error(f"Error in update loop: {e}")
                break

        logger.debug("Update loop ended (threaded)")

    def _update_motor_speeds(self):
        """Update motor speeds based on controller input"""
        if not self.controller.is_connected():
            self.current_motor_speeds = MotorSpeeds()
            return

        # Get movement vector from controller
        forward, strafe, rotation = self.controller.get_movement_vector()

        # Apply speed modifier
        speed_modifier = self.controller.get_speed_modifier()

        # Apply emergency stop
        if self.emergency_stop:
            forward = strafe = rotation = 0.0

        # Calculate motor speeds
        motor_speeds = self.mecanum_calc.calculate_motor_speeds(forward, strafe, rotation)

        # Apply speed modifier
        self.current_motor_speeds = motor_speeds.scale(speed_modifier)

        # Log significant changes at DATA level
        if self._motor_speeds_changed():
            logger.data(f"🎯 Motor speeds: F={forward:.2f}, S={strafe:.2f}, R={rotation:.2f}, "
                       f"Speed={speed_modifier:.2f} -> LF={self.current_motor_speeds.left_front:.2f}, "
                       f"LR={self.current_motor_speeds.left_rear:.2f}, "
                       f"RF={self.current_motor_speeds.right_front:.2f}, "
                       f"RR={self.current_motor_speeds.right_rear:.2f}")
            logger.debug(f"Motor speeds updated: "
                        f"F={forward:.2f}, S={strafe:.2f}, R={rotation:.2f}, "
                        f"Speed={speed_modifier:.2f}")

    def _send_motor_commands(self):
        """Send motor commands via socket client"""
        if not self.socket_client or not self.socket_client.is_connected():
            return

        # Convert motor speeds to multiplexer command
        command, value = self.mecanum_calc.convert_to_multiplexer_command(self.current_motor_speeds)

        # Log the actual multiplexer command being sent at DATA level
        logger.data(f"🚀 Multiplexer command: {command}:{value}")

        # Send command
        self.socket_client.send_motor_command(command, value)

    def _motor_speeds_changed(self) -> bool:
        """Check if motor speeds have changed significantly"""
        # This is a simple implementation - could be more sophisticated
        return True  # For now, always return True for logging

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
            # Quit application
            logger.info("🛑 Options button pressed - stopping service")
            self.stop()

        elif button == ControllerButton.L1:
            # Precision mode
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
        """Clean up all resources"""
        logger.info("🧹 Cleaning up resources...")

        # Stop all motors first
        if self.socket_client and self.socket_client.is_connected():
            self.socket_client.stop_robot()

        # Clean up components
        if self.controller:
            self.controller.cleanup()

        if self.simulator:
            self.simulator.cleanup()

        if self.socket_client:
            self.socket_client.cleanup()

        logger.info("👋 Remote control service stopped")

    def is_running(self) -> bool:
        """Check if service is running"""
        return self.running

    def get_current_motor_speeds(self) -> MotorSpeeds:
        """Get current motor speeds"""
        return self.current_motor_speeds

    def is_emergency_stopped(self) -> bool:
        """Check if emergency stop is active"""
        return self.emergency_stop