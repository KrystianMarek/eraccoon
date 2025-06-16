#!/usr/bin/env python3
"""
PlayStation 5 DualSense Controller Handler

Handles input from PlayStation 5 DualSense controller connected via USB or Bluetooth.
Uses pygame to read joystick events and provides a clean interface for accessing controller state.
Supports both macOS (auto-detection) and Linux (device path) environments.
"""

import pygame
import logging
import time
import platform
from typing import Dict, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ControllerButton(Enum):
    """PlayStation 5 DualSense button mapping - based on actual PS5 controller"""
    X = 0           # Bottom button (Cross)
    CIRCLE = 1      # Right button
    SQUARE = 2      # Left button
    TRIANGLE = 3    # Top button
    L1 = 4          # Left shoulder button
    R1 = 5          # Right shoulder button
    L2 = 6          # Left trigger button
    R2 = 7          # Right trigger button
    CREATE = 8      # Share/Create button (left of touchpad)
    OPTIONS = 9     # Options button (right of touchpad)
    L3 = 10         # Left stick press
    R3 = 11         # Right stick press
    PS = 12         # PlayStation button
    TOUCHPAD = 13   # Touchpad press


@dataclass
class ControllerState:
    """Current state of the controller"""
    # Analog sticks (-1.0 to 1.0)
    left_stick_x: float = 0.0
    left_stick_y: float = 0.0
    right_stick_x: float = 0.0
    right_stick_y: float = 0.0

    # Triggers (0.0 to 1.0)
    left_trigger: float = 0.0
    right_trigger: float = 0.0

    # Buttons (True/False)
    buttons: Dict[ControllerButton, bool] = None

    # D-pad (hat) - returns (-1, 0, 1) for each axis
    dpad_x: int = 0
    dpad_y: int = 0

    # Connection status
    connected: bool = False

    def __post_init__(self):
        if self.buttons is None:
            self.buttons = {button: False for button in ControllerButton}


class ControllerHandler:
    """
    PlayStation 5 DualSense Controller Handler

    Manages connection to PS5 controller and provides real-time state updates.
    Automatically detects controllers on macOS, uses device paths on Linux.
    """

    def __init__(self, device_path: str = "/dev/input/js0"):
        self.device_path = device_path
        self.joystick: Optional[pygame.joystick.Joystick] = None
        self.controller_state = ControllerState()
        self.last_update_time = 0.0

        # Detect platform
        self.is_macos = platform.system() == "Darwin"
        self.is_linux = platform.system() == "Linux"

        # Deadzone for analog sticks (to handle controller drift)
        self.deadzone = 0.1

        # Callbacks
        self.on_button_press: Optional[Callable[[ControllerButton], None]] = None
        self.on_button_release: Optional[Callable[[ControllerButton], None]] = None
        self.on_stick_move: Optional[Callable[[str, float, float], None]] = None

        # Initialize pygame
        pygame.init()

        # Set SDL environment variables for better joystick detection in containers
        import os
        os.environ.setdefault('SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS', '1')
        if not self.is_macos and os.path.exists(device_path):
            os.environ.setdefault('SDL_JOYSTICK_DEVICE', device_path)

        pygame.joystick.init()

        # Log SDL environment for debugging
        sdl_vars = ['SDL_VIDEODRIVER', 'SDL_JOYSTICK_DEVICE', 'SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS']
        for var in sdl_vars:
            value = os.environ.get(var, 'Not set')
            logger.debug(f"SDL Environment: {var}={value}")

        if self.is_macos:
            logger.info(f"Initialized controller handler for macOS (auto-detection)")
        else:
            logger.info(f"Initialized controller handler for device: {device_path}")
            # Check if device file exists and is readable
            if os.path.exists(device_path):
                logger.debug(f"Device file {device_path} exists")
                try:
                    with open(device_path, 'rb') as f:
                        logger.debug(f"Device file {device_path} is readable")
                except Exception as e:
                    logger.warning(f"Device file {device_path} exists but not readable: {e}")
            else:
                logger.warning(f"Device file {device_path} does not exist")

            # List all input devices for debugging
            try:
                input_devices = os.listdir("/dev/input/")
                js_devices = [d for d in input_devices if d.startswith('js')]
                event_devices = [d for d in input_devices if d.startswith('event')]
                logger.debug(f"Available input devices - JS: {js_devices}, Event: {event_devices}")
            except Exception as e:
                logger.debug(f"Could not list /dev/input/ devices: {e}")

    def connect(self) -> bool:
        """
        Connect to the PlayStation 5 controller

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Force refresh joystick detection (important for containers)
            pygame.joystick.quit()
            pygame.joystick.init()

            # Check for available joysticks
            joystick_count = pygame.joystick.get_count()
            logger.info(f"Found {joystick_count} joystick(s)")

            if joystick_count == 0:
                logger.warning("No joysticks found. Please connect a PS5 DualSense controller.")
                if self.is_macos:
                    logger.info("💡 On macOS: Connect via USB or make sure Bluetooth pairing is complete")
                else:
                    logger.info(f"💡 On Linux: Check if controller is available at {self.device_path}")
                    # Additional debugging for Linux
                    import os
                    if os.path.exists(self.device_path):
                        logger.info(f"🔍 Device file exists but pygame can't detect it - this may be a permissions or SDL issue")
                        logger.info(f"🔍 Try: sudo chmod 666 {self.device_path}")
                return False

            # Try to find and connect to a suitable controller
            for i in range(joystick_count):
                joystick = pygame.joystick.Joystick(i)
                joystick.init()

                controller_name = joystick.get_name()
                logger.info(f"Joystick {i}: {controller_name}")

                # Check if this is a PS5 controller (DualSense) or any suitable controller
                if self._is_suitable_controller(controller_name):
                    self.joystick = joystick
                    self.controller_state.connected = True
                    logger.info(f"✅ Connected to PS5 DualSense controller: {controller_name}")

                    # Log controller capabilities
                    self._log_controller_info(joystick)
                    return True
                elif i == 0:  # Fallback to first controller if no PS5 found
                    self.joystick = joystick
                    self.controller_state.connected = True
                    logger.info(f"✅ Connected to controller: {controller_name} (fallback)")
                    logger.warning("⚠️  This may not be a PS5 DualSense controller - button mapping might be different")

                    # Log controller capabilities
                    self._log_controller_info(joystick)
                    return True

            logger.error("No suitable controller found")
            return False

        except Exception as e:
            logger.error(f"Failed to connect to controller: {e}")
            return False

    def _is_suitable_controller(self, controller_name: str) -> bool:
        """Check if the controller is suitable (preferably PS5 DualSense)"""
        controller_name_lower = controller_name.lower()

        # PS5 DualSense identifiers
        ps5_identifiers = [
            "dualsense",
            "ps5",
            "playstation 5",
            "wireless controller"  # Generic PS5 name on some systems
        ]

        for identifier in ps5_identifiers:
            if identifier in controller_name_lower:
                return True

        return False

    def _log_controller_info(self, joystick: pygame.joystick.Joystick):
        """Log detailed controller information for debugging"""
        logger.debug(f"Controller details:")
        logger.debug(f"  - Name: {joystick.get_name()}")
        logger.debug(f"  - Axes: {joystick.get_numaxes()}")
        logger.debug(f"  - Buttons: {joystick.get_numbuttons()}")
        logger.debug(f"  - Hats: {joystick.get_numhats()}")
        if hasattr(joystick, 'get_guid'):
            logger.debug(f"  - GUID: {joystick.get_guid()}")

    def disconnect(self):
        """Disconnect from the controller"""
        if self.joystick:
            try:
                self.joystick.quit()
            except:
                pass
            self.joystick = None

        self.controller_state.connected = False
        logger.info("Controller disconnected")

    def update(self) -> bool:
        """
        Update controller state by processing pygame events

        Returns:
            bool: True if update successful, False if disconnected
        """
        if not self.controller_state.connected or not self.joystick:
            return False

        try:
            # Process pygame events
            for event in pygame.event.get():
                if event.type == pygame.JOYBUTTONDOWN:
                    self._handle_button_press(event.button)
                elif event.type == pygame.JOYBUTTONUP:
                    self._handle_button_release(event.button)
                elif event.type == pygame.JOYAXISMOTION:
                    self._handle_axis_motion(event.axis, event.value)
                elif event.type == pygame.JOYHATMOTION:
                    self._handle_hat_motion(event.hat, event.value)
                elif event.type == pygame.JOYDEVICEREMOVED:
                    logger.warning("Controller disconnected")
                    self.disconnect()
                    return False

            # Update state timestamp
            self.last_update_time = time.time()
            return True

        except Exception as e:
            logger.error(f"Error updating controller state: {e}")
            self.disconnect()
            return False

    def _handle_button_press(self, button_id: int):
        """Handle button press event"""
        try:
            # Handle button mapping differences between controllers
            if button_id < len(ControllerButton):
                button = ControllerButton(button_id)
                self.controller_state.buttons[button] = True

                if self.on_button_press:
                    self.on_button_press(button)

                logger.debug(f"Button pressed: {button.name} (ID: {button_id})")
            else:
                logger.debug(f"Unknown button pressed: {button_id}")
        except ValueError:
            logger.debug(f"Unmapped button pressed: {button_id}")

    def _handle_button_release(self, button_id: int):
        """Handle button release event"""
        try:
            # Handle button mapping differences between controllers
            if button_id < len(ControllerButton):
                button = ControllerButton(button_id)
                self.controller_state.buttons[button] = False

                if self.on_button_release:
                    self.on_button_release(button)

                logger.debug(f"Button released: {button.name} (ID: {button_id})")
            else:
                logger.debug(f"Unknown button released: {button_id}")
        except ValueError:
            logger.debug(f"Unmapped button released: {button_id}")

    def _handle_axis_motion(self, axis_id: int, value: float):
        """Handle analog stick/trigger motion"""
        # Apply deadzone
        if abs(value) < self.deadzone:
            value = 0.0

        # Map axis to controller state
        if axis_id == 0:  # Left stick X
            self.controller_state.left_stick_x = value
        elif axis_id == 1:  # Left stick Y
            self.controller_state.left_stick_y = value
        elif axis_id == 2:  # Right stick X (or sometimes left trigger)
            # On some controllers, axis 2 might be left trigger instead of right stick
            if hasattr(self.joystick, 'get_numaxes') and self.joystick.get_numaxes() > 4:
                self.controller_state.right_stick_x = value
            else:
                self.controller_state.left_trigger = (value + 1.0) / 2.0
        elif axis_id == 3:  # Right stick Y (or sometimes right trigger)
            if hasattr(self.joystick, 'get_numaxes') and self.joystick.get_numaxes() > 4:
                self.controller_state.right_stick_y = value
            else:
                self.controller_state.right_trigger = (value + 1.0) / 2.0
        elif axis_id == 4:  # Left trigger (on controllers with 6+ axes)
            self.controller_state.left_trigger = (value + 1.0) / 2.0
        elif axis_id == 5:  # Right trigger (on controllers with 6+ axes)
            self.controller_state.right_trigger = (value + 1.0) / 2.0

        # Trigger stick move callback
        if self.on_stick_move:
            if axis_id in [0, 1]:  # Left stick
                self.on_stick_move("left", self.controller_state.left_stick_x, self.controller_state.left_stick_y)
            elif axis_id in [2, 3] and hasattr(self.joystick, 'get_numaxes') and self.joystick.get_numaxes() > 4:  # Right stick
                self.on_stick_move("right", self.controller_state.right_stick_x, self.controller_state.right_stick_y)

        # Only log significant axis movements to reduce noise
        if abs(value) > 0.1:  # Only log if movement is above deadzone
            logger.debug(f"Axis {axis_id} motion: {value:.3f}")

    def _handle_hat_motion(self, hat_id: int, value: Tuple[int, int]):
        """Handle D-pad (hat) motion"""
        if hat_id == 0:  # Main D-pad
            self.controller_state.dpad_x = value[0]
            self.controller_state.dpad_y = value[1]

            logger.debug(f"D-pad motion: {value}")

    def get_state(self) -> ControllerState:
        """Get current controller state"""
        return self.controller_state

    def is_connected(self) -> bool:
        """Check if controller is connected"""
        return self.controller_state.connected

    def get_movement_vector(self) -> Tuple[float, float, float]:
        """
        Get movement vector from controller input

        Returns:
            Tuple[float, float, float]: (forward/backward, strafe left/right, rotation)
                All values are in range -1.0 to 1.0
        """
        if not self.controller_state.connected:
            return (0.0, 0.0, 0.0)

        # Use left stick for movement (forward/backward, strafe)
        forward_backward = -self.controller_state.left_stick_y  # Invert Y axis (up = forward)
        strafe_left_right = -self.controller_state.left_stick_x  # Invert X axis (left = negative)

        # Use right stick X for rotation (no inversion needed - mecanum formula handles it correctly)
        rotation = self.controller_state.right_stick_x  # Right = positive (clockwise), Left = negative (counterclockwise)

        return (forward_backward, strafe_left_right, rotation)

    def get_speed_modifier(self) -> float:
        """
        Get speed modifier from triggers

        Returns:
            float: Speed modifier in range 0.0 to 1.0
        """
        if not self.controller_state.connected:
            return 0.5  # Default moderate speed

        # Use right trigger for speed boost, left trigger for precision mode
        speed_boost = self.controller_state.right_trigger
        precision_mode = self.controller_state.left_trigger

        # Base speed is 0.5, can be boosted up to 1.0 or reduced to 0.1 for precision
        base_speed = 0.5
        if speed_boost > 0.1:
            return base_speed + (speed_boost * 0.5)  # Boost to max 1.0
        elif precision_mode > 0.1:
            return base_speed * (1.0 - precision_mode * 0.8)  # Reduce to min 0.1
        else:
            return base_speed

    def cleanup(self):
        """Clean up resources"""
        self.disconnect()
        try:
            pygame.joystick.quit()
            pygame.quit()
        except:
            pass

        logger.info("Controller handler cleaned up")