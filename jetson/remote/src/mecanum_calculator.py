#!/usr/bin/env python3
"""
Mecanum Wheel Movement Calculator

Calculates individual motor speeds for Mecanum wheel robot based on movement vectors.
Implements the movement patterns described in the SunFounder Zeus Car documentation.

Based on: https://docs.sunfounder.com/projects/zeus-car-dev/en/latest/scratch/sc4_move_wheels.html
"""

import logging
import math
from typing import Tuple, Dict, NamedTuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MotorSpeeds:
    """Motor speeds for the four Mecanum wheels"""
    left_front: float = 0.0      # LF motor
    left_rear: float = 0.0       # LR motor
    right_front: float = 0.0     # RF motor
    right_rear: float = 0.0      # RR motor

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary format"""
        return {
            'left_front': self.left_front,
            'left_rear': self.left_rear,
            'right_front': self.right_front,
            'right_rear': self.right_rear
        }

    def scale(self, factor: float) -> 'MotorSpeeds':
        """Scale all motor speeds by a factor"""
        return MotorSpeeds(
            left_front=self.left_front * factor,
            left_rear=self.left_rear * factor,
            right_front=self.right_front * factor,
            right_rear=self.right_rear * factor
        )

    def normalize(self, max_speed: float = 1.0) -> 'MotorSpeeds':
        """Normalize motor speeds to ensure none exceed max_speed while maintaining ratios"""
        max_current = max(abs(self.left_front), abs(self.left_rear),
                         abs(self.right_front), abs(self.right_rear))

        if max_current == 0 or max_current <= max_speed:
            return self

        scale_factor = max_speed / max_current
        return self.scale(scale_factor)


class MecanumCalculator:
    """
    Mecanum Wheel Movement Calculator

    Converts movement vectors (forward/backward, strafe, rotation) into individual motor speeds
    for a four-wheel Mecanum drive robot.

    Motor Layout:
    LF ---- RF
    |  \  /  |
    |   \/   |
    |   /\   |
    |  /  \  |
    LR ---- RR

    Based on SunFounder Zeus Car Mecanum wheel principles.
    """

    def __init__(self, max_speed: float = 1.0):
        """
        Initialize the Mecanum calculator

        Args:
            max_speed: Maximum motor speed (0.0 to 1.0)
        """
        self.max_speed = max_speed
        logger.info(f"Initialized Mecanum calculator with max speed: {max_speed}")

    def calculate_motor_speeds(self, forward: float, strafe: float, rotation: float) -> MotorSpeeds:
        """
        Calculate motor speeds for Mecanum wheel movement

        Args:
            forward: Forward/backward movement (-1.0 to 1.0, positive = forward)
            strafe: Left/right strafe movement (-1.0 to 1.0, positive = right)
            rotation: Rotation (-1.0 to 1.0, positive = clockwise)

        Returns:
            MotorSpeeds: Individual motor speeds for each wheel
        """
        # Mecanum wheel kinematics
        # Based on the movement patterns from SunFounder documentation:

        # Forward/Backward: All wheels same direction
        # Left/Right strafe: Diagonal wheels together
        # Rotation: Left side opposite to right side

        left_front = forward - strafe - rotation
        left_rear = forward + strafe - rotation
        right_front = forward + strafe + rotation
        right_rear = forward - strafe + rotation

        motor_speeds = MotorSpeeds(
            left_front=left_front,
            left_rear=left_rear,
            right_front=right_front,
            right_rear=right_rear
        )

        # Normalize to ensure no motor exceeds max speed
        normalized_speeds = motor_speeds.normalize(self.max_speed)

        logger.debug(f"Movement: F={forward:.2f}, S={strafe:.2f}, R={rotation:.2f} -> "
                    f"Motors: LF={normalized_speeds.left_front:.2f}, "
                    f"LR={normalized_speeds.left_rear:.2f}, "
                    f"RF={normalized_speeds.right_front:.2f}, "
                    f"RR={normalized_speeds.right_rear:.2f}")

        return normalized_speeds

    def calculate_predefined_movement(self, movement_type: str, speed: float = 0.5) -> MotorSpeeds:
        """
        Calculate motor speeds for predefined movement patterns

        Args:
            movement_type: Type of movement (forward, backward, left, right, etc.)
            speed: Movement speed (0.0 to 1.0)

        Returns:
            MotorSpeeds: Motor speeds for the specified movement
        """
        speed = max(0.0, min(speed, self.max_speed))

        # Predefined movement patterns based on SunFounder documentation
        patterns = {
            # Basic movements
            'forward': MotorSpeeds(speed, speed, speed, speed),
            'backward': MotorSpeeds(-speed, -speed, -speed, -speed),

            # Strafe movements
            'left': MotorSpeeds(-speed, speed, speed, -speed),
            'right': MotorSpeeds(speed, -speed, -speed, speed),

            # Rotation
            'rotate_left': MotorSpeeds(-speed, -speed, speed, speed),
            'rotate_right': MotorSpeeds(speed, speed, -speed, -speed),
            'rotate_clockwise': MotorSpeeds(speed, speed, -speed, -speed),
            'rotate_counterclockwise': MotorSpeeds(-speed, -speed, speed, speed),

            # Diagonal movements
            'forward_left': MotorSpeeds(0, speed, speed, 0),
            'forward_right': MotorSpeeds(speed, 0, 0, speed),
            'backward_left': MotorSpeeds(0, -speed, -speed, 0),
            'backward_right': MotorSpeeds(-speed, 0, 0, -speed),

            # Drift movements
            'drift_left': MotorSpeeds(0, speed, 0, -speed),
            'drift_right': MotorSpeeds(0, -speed, 0, speed),

            # Stop
            'stop': MotorSpeeds(0, 0, 0, 0),
        }

        if movement_type not in patterns:
            logger.warning(f"Unknown movement type: {movement_type}")
            return MotorSpeeds(0, 0, 0, 0)

        result = patterns[movement_type]
        logger.debug(f"Predefined movement '{movement_type}' at speed {speed}: {result}")

        return result

    def convert_to_multiplexer_command(self, motor_speeds: MotorSpeeds) -> Tuple[str, int]:
        """
        Convert motor speeds to multiplexer command format

        The multiplexer expects commands like FORWARD, BACKWARD, LEFT, RIGHT with speed 0-255
        We need to determine the dominant movement pattern and convert to this format.

        Args:
            motor_speeds: Motor speeds to convert

        Returns:
            Tuple[str, int]: (command, speed) for the multiplexer
        """
        # Convert from -1.0..1.0 range to 0-255 range
        def to_byte_value(speed: float) -> int:
            return int(abs(speed) * 255)

        # Determine dominant movement pattern
        lf, lr, rf, rr = motor_speeds.left_front, motor_speeds.left_rear, motor_speeds.right_front, motor_speeds.right_rear

        # Check for stop condition
        if abs(lf) < 0.05 and abs(lr) < 0.05 and abs(rf) < 0.05 and abs(rr) < 0.05:
            return ("STOP", 0)

        # Check for pure forward/backward
        if abs(lf - lr) < 0.1 and abs(rf - rr) < 0.1 and abs(lf - rf) < 0.1:
            if lf > 0:
                return ("FORWARD", to_byte_value(lf))
            else:
                return ("BACKWARD", to_byte_value(abs(lf)))

        # Check for pure left/right strafe
        if abs(lf + rf) < 0.1 and abs(lr + rr) < 0.1 and abs(lf - lr) > 0.3:
            if lf < 0:  # Moving left
                return ("LEFT", to_byte_value(abs(lf)))
            else:  # Moving right
                return ("RIGHT", to_byte_value(lf))

        # Check for rotation
        if abs(lf - lr) < 0.1 and abs(rf - rr) < 0.1 and abs(lf + rf) < 0.1:
            if lf > 0:  # Clockwise
                return ("RIGHT", to_byte_value(lf))  # Use RIGHT for clockwise rotation
            else:  # Counterclockwise
                return ("LEFT", to_byte_value(abs(lf)))  # Use LEFT for counterclockwise

        # Check for diagonal movements
        if abs(lf) < 0.05 and abs(rr) < 0.05:  # Forward-left or backward-right
            if lr > 0:
                return ("FORWARD_LEFT", to_byte_value(lr))
            else:
                return ("BACKWARD_RIGHT", to_byte_value(abs(lr)))

        if abs(lr) < 0.05 and abs(rf) < 0.05:  # Forward-right or backward-left
            if lf > 0:
                return ("FORWARD_RIGHT", to_byte_value(lf))
            else:
                return ("BACKWARD_LEFT", to_byte_value(abs(lf)))

        # Default to forward/backward based on average
        avg_speed = (lf + lr + rf + rr) / 4
        if avg_speed > 0.05:
            return ("FORWARD", to_byte_value(avg_speed))
        elif avg_speed < -0.05:
            return ("BACKWARD", to_byte_value(abs(avg_speed)))
        else:
            return ("STOP", 0)

    def get_circular_path_speeds(self, radius: float, speed: float = 0.5, clockwise: bool = True) -> MotorSpeeds:
        """
        Calculate motor speeds for circular movement

        Args:
            radius: Turn radius (smaller = tighter turn, 0 = spin in place)
            speed: Movement speed (0.0 to 1.0)
            clockwise: Direction of turn

        Returns:
            MotorSpeeds: Motor speeds for circular movement
        """
        if radius <= 0:
            # Spin in place
            rotation_speed = speed if clockwise else -speed
            return self.calculate_motor_speeds(0, 0, rotation_speed)

        # Calculate differential speeds for circular path
        # Inner wheels slower, outer wheels faster
        speed_diff = speed / (radius + 1)

        if clockwise:
            # Right turn - left wheels faster
            left_speed = speed
            right_speed = speed - speed_diff
        else:
            # Left turn - right wheels faster
            left_speed = speed - speed_diff
            right_speed = speed

        return MotorSpeeds(
            left_front=left_speed,
            left_rear=left_speed,
            right_front=right_speed,
            right_rear=right_speed
        ).normalize(self.max_speed)

    def test_movement_patterns(self):
        """Test all predefined movement patterns (for debugging)"""
        logger.info("Testing Mecanum movement patterns:")

        patterns = [
            'forward', 'backward', 'left', 'right',
            'rotate_left', 'rotate_right',
            'forward_left', 'forward_right', 'backward_left', 'backward_right',
            'drift_left', 'drift_right', 'stop'
        ]

        for pattern in patterns:
            speeds = self.calculate_predefined_movement(pattern, 0.5)
            command, value = self.convert_to_multiplexer_command(speeds)
            logger.info(f"{pattern:15} -> LF:{speeds.left_front:6.2f} LR:{speeds.left_rear:6.2f} "
                       f"RF:{speeds.right_front:6.2f} RR:{speeds.right_rear:6.2f} "
                       f"-> {command}:{value}")