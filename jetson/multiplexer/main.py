#!/usr/bin/env python3
"""
Motor Controller Proxy/Multiplexer Service

Main entry point for the proxy service that exposes Arduino motor control
via Unix socket interface while managing serial communication.
"""

import argparse
import logging
import signal
import sys
import time
import os
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.unix_socket_server import MotorProxyServer


def setup_logging(log_level: str = 'INFO', log_file: str = None):
    """Configure logging"""
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

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    return root_logger


def signal_handler(signum, frame, server: MotorProxyServer):
    """Handle shutdown signals"""
    logging.info(f"Received signal {signum}, shutting down gracefully...")
    server.stop()
    sys.exit(0)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Motor Controller Proxy/Multiplexer Service',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start with auto-detection
  python main.py

  # Specify custom serial port and socket path
  python main.py --serial-port /dev/ttyACM1 --socket-path /tmp/robot.sock

  # Enable debug logging
  python main.py --log-level DEBUG

  # Log to file
  python main.py --log-file /var/log/motor-proxy.log
        """
    )

    parser.add_argument(
        '--serial-port',
        default=None,
        help='Arduino serial port (default: auto-detect)'
    )

    parser.add_argument(
        '--baud-rate',
        type=int,
        default=115200,
        help='Serial baud rate (default: 115200)'
    )

    parser.add_argument(
        '--socket-path',
        default='/tmp/motor_controller.sock',
        help='Unix socket path (default: /tmp/motor_controller.sock)'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )

    parser.add_argument(
        '--log-file',
        help='Log file path (optional, logs to console by default)'
    )

    parser.add_argument(
        '--daemon',
        action='store_true',
        help='Run as daemon (detach from terminal)'
    )

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(args.log_level, args.log_file)

    # Print startup banner
    print("=" * 60)
    print("🤖 Motor Controller Proxy/Multiplexer Service")
    print("=" * 60)
    print(f"📡 Serial Port: {args.serial_port or 'Auto-detect'}")
    print(f"⚡ Baud Rate: {args.baud_rate}")
    print(f"🔌 Socket Path: {args.socket_path}")
    print(f"📝 Log Level: {args.log_level}")
    if args.log_file:
        print(f"📁 Log File: {args.log_file}")
    print("=" * 60)

    # Daemonize if requested
    if args.daemon:
        logger.info("Daemonizing process...")
        pid = os.fork()
        if pid > 0:
            print(f"🚀 Service started as daemon with PID: {pid}")
            sys.exit(0)

        # Detach from terminal
        os.setsid()
        os.chdir('/')

        # Redirect standard file descriptors
        with open('/dev/null', 'r') as dev_null:
            os.dup2(dev_null.fileno(), sys.stdin.fileno())
        if not args.log_file:
            with open('/dev/null', 'w') as dev_null:
                os.dup2(dev_null.fileno(), sys.stdout.fileno())
                os.dup2(dev_null.fileno(), sys.stderr.fileno())

    # Create and start server
    server = MotorProxyServer(
        socket_path=args.socket_path,
        serial_port=args.serial_port,
        baud_rate=args.baud_rate
    )

    # Setup signal handlers
    signal.signal(signal.SIGINT, lambda s, f: signal_handler(s, f, server))
    signal.signal(signal.SIGTERM, lambda s, f: signal_handler(s, f, server))

    try:
        # Start the server
        logger.info("🚀 Starting Motor Controller Proxy Service...")
        if args.serial_port:
            logger.info(f"📡 Using specified Arduino port: {args.serial_port}")
        else:
            logger.info("📡 Auto-detecting Arduino port...")
        logger.info(f"🔌 Creating Unix socket at {args.socket_path}")

        if not server.start():
            logger.error("❌ Failed to start server")
            return 1

        logger.info("✅ Server started successfully!")
        logger.info("📊 Server Statistics:")
        logger.info("   - Serial connection: Active")
        logger.info("   - Unix socket: Listening")
        logger.info("   - Client connections: 0")
        logger.info("")
        logger.info("🎮 Ready to accept client connections!")
        logger.info("💡 Use Ctrl+C to stop the service")

        # Keep the main thread alive
        while True:
            time.sleep(1)

            # Periodically log statistics (every 5 minutes)
            if int(time.time()) % 300 == 0:
                stats = server.stats
                uptime = time.time() - stats['start_time']
                current_port = server.serial_controller.get_current_port()
                logger.info(f"📊 Uptime: {uptime:.0f}s, "
                           f"Port: {current_port}, "
                           f"Connections: {stats['total_connections']}, "
                           f"Commands: {stats['commands_processed']}, "
                           f"Errors: {stats['errors']}")

    except KeyboardInterrupt:
        logger.info("🛑 Received interrupt signal")
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        return 1
    finally:
        logger.info("🧹 Cleaning up...")
        server.stop()
        logger.info("👋 Motor Controller Proxy Service stopped")

    return 0


if __name__ == "__main__":
    sys.exit(main())