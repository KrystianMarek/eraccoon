#!/usr/bin/env python3
"""
2D Robot Simulator for Development Mode

Provides a pygame-based 2D visualization of the Mecanum wheel robot.
Simulates robot movement based on calculated motor speeds and visualizes
the unique movement patterns possible with Mecanum wheels.
"""

import pygame
import math
import logging
import time
from typing import Tuple, Optional
from dataclasses import dataclass

from .mecanum_calculator import MotorSpeeds

logger = logging.getLogger(__name__)


@dataclass
class RobotState:
    """Current state of the simulated robot"""
    x: float = 0.0          # X position (pixels)
    y: float = 0.0          # Y position (pixels)
    angle: float = 0.0      # Rotation angle (radians)
    velocity_x: float = 0.0 # X velocity (pixels/second)
    velocity_y: float = 0.0 # Y velocity (pixels/second)
    angular_velocity: float = 0.0  # Angular velocity (radians/second)


class RobotSimulator:
    """
    2D Mecanum Wheel Robot Simulator

    Simulates a robot with Mecanum wheels in a 2D environment.
    Visualizes movement patterns and provides feedback for development.
    """

    def __init__(self, width: int = 800, height: int = 600):
        """
        Initialize the robot simulator

        Args:
            width: Window width in pixels
            height: Window height in pixels
        """
        self.width = width
        self.height = height
        self.running = False

        # Robot physical properties
        self.robot_width = 60    # Robot width in pixels
        self.robot_height = 80   # Robot height in pixels
        self.wheel_size = 12     # Wheel size in pixels

        # Physics parameters
        self.max_speed = 200.0   # Max speed in pixels/second
        self.max_angular_speed = 3.0  # Max angular speed in radians/second
        self.friction = 0.95     # Friction coefficient (0-1)

        # Robot state
        self.robot_state = RobotState(
            x=width // 2,
            y=height // 2
        )

        # Current motor speeds
        self.current_motor_speeds = MotorSpeeds()

        # Pygame initialization
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Mecanum Wheel Robot Simulator")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)

        # Colors
        self.colors = {
            'background': (20, 20, 30),
            'robot_body': (100, 150, 200),
            'robot_outline': (150, 200, 255),
            'wheel_active': (255, 100, 100),
            'wheel_inactive': (100, 100, 100),
            'trail': (255, 255, 100),
            'text': (255, 255, 255),
            'grid': (50, 50, 60),
            'center': (100, 255, 100)
        }

        # Trail for visualization
        self.trail_points = []
        self.max_trail_points = 200

        # Last update time for physics
        self.last_update_time = time.time()

        logger.info(f"Initialized robot simulator: {width}x{height}")

    def start(self) -> bool:
        """
        Start the simulator

        Returns:
            bool: True if started successfully, False otherwise
        """
        try:
            self.running = True
            self.last_update_time = time.time()
            logger.info("✅ Robot simulator started")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to start simulator: {e}")
            return False

    def stop(self):
        """Stop the simulator"""
        self.running = False
        pygame.quit()
        logger.info("👋 Robot simulator stopped")

    def update(self, motor_speeds: MotorSpeeds) -> bool:
        """
        Update the simulator with new motor speeds

        Args:
            motor_speeds: Current motor speeds for the robot

        Returns:
            bool: True if update successful, False if simulator should close
        """
        if not self.running:
            return False

        # Handle pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.stop()
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.stop()
                    return False
                elif event.key == pygame.K_SPACE:
                    self._reset_robot_position()
                elif event.key == pygame.K_c:
                    self._clear_trail()

        # Update motor speeds
        self.current_motor_speeds = motor_speeds

        # Update physics
        self._update_physics()

        # Render the scene
        self._render()

        # Control frame rate
        self.clock.tick(60)  # 60 FPS

        return True

    def _update_physics(self):
        """Update robot physics based on motor speeds"""
        current_time = time.time()
        dt = current_time - self.last_update_time
        self.last_update_time = current_time

        # Convert motor speeds to movement vectors
        # Mecanum wheel kinematics simulation
        lf = self.current_motor_speeds.left_front
        lr = self.current_motor_speeds.left_rear
        rf = self.current_motor_speeds.right_front
        rr = self.current_motor_speeds.right_rear

        # Calculate robot movement from wheel speeds
        # Forward/backward component
        forward_vel = (lf + lr + rf + rr) * 0.25 * self.max_speed

        # Strafe component (unique to Mecanum wheels)
        strafe_vel = (-lf + lr + rf - rr) * 0.25 * self.max_speed

        # Rotation component
        angular_vel = (-lf - lr + rf + rr) * 0.25 * self.max_angular_speed

        # Apply movement in robot's local coordinate system
        cos_angle = math.cos(self.robot_state.angle)
        sin_angle = math.sin(self.robot_state.angle)

        # Transform to world coordinates
        world_vel_x = forward_vel * cos_angle - strafe_vel * sin_angle
        world_vel_y = forward_vel * sin_angle + strafe_vel * cos_angle

        # Update robot state
        self.robot_state.velocity_x = world_vel_x
        self.robot_state.velocity_y = world_vel_y
        self.robot_state.angular_velocity = angular_vel

        # Update position and rotation
        self.robot_state.x += self.robot_state.velocity_x * dt
        self.robot_state.y += self.robot_state.velocity_y * dt
        self.robot_state.angle += self.robot_state.angular_velocity * dt

        # Apply friction
        self.robot_state.velocity_x *= self.friction
        self.robot_state.velocity_y *= self.friction
        self.robot_state.angular_velocity *= self.friction

        # Keep robot on screen (wrap around)
        if self.robot_state.x < 0:
            self.robot_state.x = self.width
        elif self.robot_state.x > self.width:
            self.robot_state.x = 0

        if self.robot_state.y < 0:
            self.robot_state.y = self.height
        elif self.robot_state.y > self.height:
            self.robot_state.y = 0

        # Add to trail if moving
        if abs(self.robot_state.velocity_x) > 1 or abs(self.robot_state.velocity_y) > 1:
            self.trail_points.append((int(self.robot_state.x), int(self.robot_state.y)))
            if len(self.trail_points) > self.max_trail_points:
                self.trail_points.pop(0)

    def _render(self):
        """Render the simulation"""
        # Clear screen
        self.screen.fill(self.colors['background'])

        # Draw grid
        self._draw_grid()

        # Draw trail
        self._draw_trail()

        # Draw robot
        self._draw_robot()

        # Draw UI
        self._draw_ui()

        # Update display
        pygame.display.flip()

    def _draw_grid(self):
        """Draw grid lines for reference"""
        grid_size = 50

        # Vertical lines
        for x in range(0, self.width, grid_size):
            pygame.draw.line(self.screen, self.colors['grid'],
                           (x, 0), (x, self.height), 1)

        # Horizontal lines
        for y in range(0, self.height, grid_size):
            pygame.draw.line(self.screen, self.colors['grid'],
                           (0, y), (self.width, y), 1)

        # Center cross
        center_x, center_y = self.width // 2, self.height // 2
        pygame.draw.line(self.screen, self.colors['center'],
                        (center_x - 20, center_y), (center_x + 20, center_y), 2)
        pygame.draw.line(self.screen, self.colors['center'],
                        (center_x, center_y - 20), (center_x, center_y + 20), 2)

    def _draw_trail(self):
        """Draw robot movement trail"""
        if len(self.trail_points) > 1:
            for i, point in enumerate(self.trail_points):
                alpha = int(255 * (i / len(self.trail_points)))
                color = (*self.colors['trail'], alpha)

                # Create a surface with per-pixel alpha
                trail_surf = pygame.Surface((4, 4), pygame.SRCALPHA)
                trail_surf.fill((*self.colors['trail'], alpha))
                self.screen.blit(trail_surf, (point[0] - 2, point[1] - 2))

    def _draw_robot(self):
        """Draw the robot with Mecanum wheels"""
        x, y = int(self.robot_state.x), int(self.robot_state.y)
        angle = self.robot_state.angle

        # Calculate robot corners
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        half_w, half_h = self.robot_width // 2, self.robot_height // 2

        # Robot corners in local coordinates
        corners = [
            (-half_w, -half_h),  # Top-left
            (half_w, -half_h),   # Top-right
            (half_w, half_h),    # Bottom-right
            (-half_w, half_h)    # Bottom-left
        ]

        # Transform to world coordinates
        world_corners = []
        for lx, ly in corners:
            wx = x + lx * cos_a - ly * sin_a
            wy = y + lx * sin_a + ly * cos_a
            world_corners.append((int(wx), int(wy)))

        # Draw robot body
        pygame.draw.polygon(self.screen, self.colors['robot_body'], world_corners)
        pygame.draw.polygon(self.screen, self.colors['robot_outline'], world_corners, 2)

        # Draw Mecanum wheels
        self._draw_mecanum_wheels(x, y, angle)

        # Draw direction indicator
        front_x = x + (half_h + 15) * cos_a
        front_y = y + (half_h + 15) * sin_a
        pygame.draw.line(self.screen, self.colors['robot_outline'],
                        (x, y), (int(front_x), int(front_y)), 3)

        # Draw center point
        pygame.draw.circle(self.screen, self.colors['center'], (x, y), 3)

    def _draw_mecanum_wheels(self, x: int, y: int, angle: float):
        """Draw Mecanum wheels with speed indicators"""
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        wheel_offset = 25  # Distance from center to wheel

        # Wheel positions (relative to robot center)
        wheel_positions = [
            (-wheel_offset, -wheel_offset),  # Left Front
            (-wheel_offset, wheel_offset),   # Left Rear
            (wheel_offset, -wheel_offset),   # Right Front
            (wheel_offset, wheel_offset)     # Right Rear
        ]

        # Motor speeds
        motor_speeds = [
            self.current_motor_speeds.left_front,
            self.current_motor_speeds.left_rear,
            self.current_motor_speeds.right_front,
            self.current_motor_speeds.right_rear
        ]

        wheel_labels = ['LF', 'LR', 'RF', 'RR']

        for i, ((wx, wy), speed, label) in enumerate(zip(wheel_positions, motor_speeds, wheel_labels)):
            # Transform wheel position
            world_x = x + wx * cos_a - wy * sin_a
            world_y = y + wx * sin_a + wy * cos_a

            # Choose color based on speed
            if abs(speed) > 0.05:
                intensity = min(int(abs(speed) * 255), 255)
                if speed > 0:
                    color = (intensity, 0, 0)  # Red for positive
                else:
                    color = (0, 0, intensity)  # Blue for negative
            else:
                color = self.colors['wheel_inactive']

            # Draw wheel
            pygame.draw.circle(self.screen, color, (int(world_x), int(world_y)), self.wheel_size)
            pygame.draw.circle(self.screen, self.colors['robot_outline'],
                             (int(world_x), int(world_y)), self.wheel_size, 2)

            # Draw wheel label
            text = self.small_font.render(label, True, self.colors['text'])
            text_rect = text.get_rect(center=(int(world_x), int(world_y)))
            self.screen.blit(text, text_rect)

    def _draw_ui(self):
        """Draw user interface elements"""
        ui_y = 10
        line_height = 25

        # Motor speeds
        motor_info = [
            f"LF: {self.current_motor_speeds.left_front:6.2f}",
            f"LR: {self.current_motor_speeds.left_rear:6.2f}",
            f"RF: {self.current_motor_speeds.right_front:6.2f}",
            f"RR: {self.current_motor_speeds.right_rear:6.2f}"
        ]

        for info in motor_info:
            text = self.font.render(info, True, self.colors['text'])
            self.screen.blit(text, (10, ui_y))
            ui_y += line_height

        ui_y += 10

        # Robot state
        state_info = [
            f"Position: ({self.robot_state.x:.0f}, {self.robot_state.y:.0f})",
            f"Angle: {math.degrees(self.robot_state.angle):.1f}°",
            f"Velocity: ({self.robot_state.velocity_x:.1f}, {self.robot_state.velocity_y:.1f})",
            f"Angular Vel: {math.degrees(self.robot_state.angular_velocity):.1f}°/s"
        ]

        for info in state_info:
            text = self.font.render(info, True, self.colors['text'])
            self.screen.blit(text, (10, ui_y))
            ui_y += line_height

        # Controls help
        help_y = self.height - 80
        help_text = [
            "Controls:",
            "SPACE - Reset position",
            "C - Clear trail",
            "ESC - Exit"
        ]

        for text_line in help_text:
            text = self.small_font.render(text_line, True, self.colors['text'])
            self.screen.blit(text, (10, help_y))
            help_y += 20

    def _reset_robot_position(self):
        """Reset robot to center position"""
        self.robot_state.x = self.width // 2
        self.robot_state.y = self.height // 2
        self.robot_state.angle = 0.0
        self.robot_state.velocity_x = 0.0
        self.robot_state.velocity_y = 0.0
        self.robot_state.angular_velocity = 0.0
        self._clear_trail()
        logger.info("🔄 Robot position reset")

    def _clear_trail(self):
        """Clear the movement trail"""
        self.trail_points.clear()
        logger.debug("🧹 Trail cleared")

    def is_running(self) -> bool:
        """Check if simulator is running"""
        return self.running

    def get_robot_position(self) -> Tuple[float, float, float]:
        """
        Get current robot position and angle

        Returns:
            Tuple[float, float, float]: (x, y, angle_degrees)
        """
        return (self.robot_state.x, self.robot_state.y,
                math.degrees(self.robot_state.angle))

    def cleanup(self):
        """Clean up resources"""
        self.stop()