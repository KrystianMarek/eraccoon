#!/usr/bin/env python3
"""
Remote Control Service for Mecanum Wheel Robot

Handles PlayStation 5 DualSense controller input and translates it to robot movement commands.
Supports both development mode (with 2D simulation) and production mode (with socket communication).
"""

import argparse
import logging
import sys
import os
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.controller_handler import ControllerHandler
from src.mecanum_calculator import MecanumCalculator
from src.robot_simulator import RobotSimulator
from src.socket_client import SocketClient
from src.remote_control_service import RemoteControlService


# Add custom DATA log level between INFO (20) and DEBUG (10)
DATA_LOG_LEVEL = 15
logging.addLevelName(DATA_LOG_LEVEL, 'DATA')

def data_log(self, message, *args, **kwargs):
    """Log at DATA level (15) - between INFO and DEBUG"""
    if self.isEnabledFor(DATA_LOG_LEVEL):
        self._log(DATA_LOG_LEVEL, message, args, **kwargs)

# Add the DATA logging method to the Logger class
logging.Logger.data = data_log


def setup_logging(log_level: str = 'INFO'):
    """Configure logging"""
    # Handle custom DATA level
    if log_level.upper() == 'DATA':
        level = DATA_LOG_LEVEL
    else:
        level = getattr(logging, log_level.upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    return root_logger


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Remote Control Service for Mecanum Wheel Robot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Development mode (with 2D simulation)
  python main.py --mode development

  # Production mode (with socket communication)
  python main.py --mode production --socket-path /tmp/motor-proxy/motor_controller.sock

  # Specify custom controller device
  python main.py --mode development --controller-device /dev/input/js1

  # Enable debug logging
  python main.py --mode development --log-level DEBUG
        """
    )

    parser.add_argument(
        '--mode',
        choices=['development', 'production'],
        default='development',
        help='Operation mode (default: development)'
    )

    parser.add_argument(
        '--controller-device',
        default='/dev/input/js0',
        help='Controller device path (default: /dev/input/js0)'
    )

    parser.add_argument(
        '--socket-path',
        default='/tmp/motor-proxy/motor_controller.sock',
        help='Unix socket path for production mode (default: /tmp/motor-proxy/motor_controller.sock)'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'DATA', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO). DATA level shows socket data frames.'
    )

    parser.add_argument(
        '--simulation-width',
        type=int,
        default=800,
        help='Simulation window width in development mode (default: 800)'
    )

    parser.add_argument(
        '--simulation-height',
        type=int,
        default=600,
        help='Simulation window height in development mode (default: 600)'
    )

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(args.log_level)

    # Print startup banner
    print("=" * 60)
    print("🎮 Remote Control Service for Mecanum Wheel Robot")
    print("=" * 60)
    print(f"🔧 Mode: {args.mode}")
    print(f"🎮 Controller: {args.controller_device}")
    if args.mode == 'production':
        print(f"🔌 Socket: {args.socket_path}")
    else:
        print(f"📺 Simulation: {args.simulation_width}x{args.simulation_height}")
    print(f"📝 Log Level: {args.log_level}")
    print("=" * 60)

    try:
        # Create the remote control service
        service = RemoteControlService(
            mode=args.mode,
            controller_device=args.controller_device,
            socket_path=args.socket_path,
            simulation_width=args.simulation_width,
            simulation_height=args.simulation_height
        )

        # Start the service
        logger.info("🚀 Starting Remote Control Service...")
        service.run()

    except KeyboardInterrupt:
        logger.info("🛑 Received interrupt signal")
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        return 1
    finally:
        logger.info("👋 Remote Control Service stopped")

    return 0


if __name__ == "__main__":
    sys.exit(main())