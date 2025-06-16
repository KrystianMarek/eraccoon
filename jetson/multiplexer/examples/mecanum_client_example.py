#!/usr/bin/env python3
"""
Mecanum Client Example

Demonstrates the new mecanum wheel control capabilities of the motor controller
proxy service. Shows both tank-style and direct mecanum motor control.

Features:
- Tank-style commands (traditional robot control)
- Mecanum-specific commands (strafing, diagonal movement, rotation)
- Intelligent keepalive management (motor commands act as implicit keepalives)
- Real-time sensor data monitoring
- Interactive control mode

Intelligent Keepalive System:
- Motor commands automatically act as keepalives
- Explicit keepalives are ignored during active control
- Connection maintained as long as either keepalives OR motor commands are sent
"""

import socket
import json
import time
import sys
import threading
from typing import Optional, Dict, Any

class MecanumClient:
    """Client for controlling robot with mecanum wheels"""

    def __init__(self, socket_path: str = '/var/eraccoon/multiplexer/socket/motor_proxy_service.sock'):
        self.socket_path = socket_path
        self.sock: Optional[socket.socket] = None
        self.connected = False
        self.running = False
        self.listen_thread: Optional[threading.Thread] = None
        self.keepalive_thread: Optional[threading.Thread] = None

        # Keepalive management
        self.keepalive_interval = 2.5  # Send keepalive every 2.5 seconds
        self.last_keepalive_response = time.time()

    def connect(self) -> bool:
        """Connect to the motor proxy service"""
        try:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.connect(self.socket_path)
            self.connected = True

            # Start listening thread
            self.running = True
            self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.listen_thread.start()

            # Send identification
            self.send_command({
                'type': 'identify',
                'name': 'MecanumClient'
            })

            # Start keepalive thread
            self.keepalive_thread = threading.Thread(target=self._keepalive_loop, daemon=True)
            self.keepalive_thread.start()

            print(f"✅ Connected to motor proxy at {self.socket_path}")
            return True

        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False

    def disconnect(self):
        """Disconnect from the service"""
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        self.connected = False
        print("👋 Disconnected from motor proxy")

    def _listen_loop(self):
        """Listen for responses from the service"""
        while self.running and self.sock:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break

                # Process each line
                for line in data.decode('utf-8').strip().split('\n'):
                    if line:
                        try:
                            response = json.loads(line)
                            self._handle_response(response)
                        except json.JSONDecodeError:
                            print(f"📝 Raw: {line}")

            except Exception as e:
                if self.running:
                    print(f"❌ Listen error: {e}")
                break

    def _handle_response(self, response: Dict[str, Any]):
        """Handle responses from the service"""
        msg_type = response.get('type', '')

        if msg_type == 'sensor_data':
            # Only show sensor data occasionally to avoid spam
            if hasattr(self, '_last_sensor_print'):
                if time.time() - self._last_sensor_print < 2.0:
                    return
            self._last_sensor_print = time.time()

            data = response.get('data')
            if data:
                print(f"📊 Sensors: FL:{data['front_left']} FR:{data['front_right']} "
                      f"RL:{data['rear_left']} RR:{data['rear_right']}")

        elif msg_type in ['tank_command_response', 'mecanum_command_response']:
            success = response.get('success', False)
            status = "✅" if success else "❌"

            if msg_type == 'tank_command_response':
                cmd = response.get('command', '')
                val = response.get('value', 0)
                print(f"{status} Tank: {cmd}:{val}")
            else:
                motors = response.get('motors', {})
                print(f"{status} Mecanum: LF:{motors.get('left_front', 0)} "
                      f"LR:{motors.get('left_rear', 0)} RF:{motors.get('right_front', 0)} "
                      f"RR:{motors.get('right_rear', 0)}")

        elif msg_type == 'error':
            print(f"❌ Error: {response.get('message', 'Unknown error')}")

        elif msg_type == 'status':
            arduino_connected = response.get('arduino_connected', False)
            port = response.get('arduino_current_port', 'unknown')
            clients = response.get('total_clients', 0)
            print(f"📊 Status: Arduino {'✅' if arduino_connected else '❌'} "
                  f"on {port}, {clients} clients")

        elif msg_type == 'welcome':
            client_id = response.get('client_id')
            print(f"🎉 Welcome! Client ID: {client_id}")

        elif msg_type == 'identify_response':
            unique_name = response.get('unique_name')
            claimed_name = response.get('claimed_name')
            print(f"🏷️  Identified as {unique_name} (claimed: {claimed_name})")

        elif msg_type == 'keepalive_response':
            self.last_keepalive_response = time.time()
            print("💓 Keepalive acknowledged")

        elif msg_type == 'keepalive_ignored':
            self.last_keepalive_response = time.time()
            reason = response.get('reason', 'unknown')
            print(f"💓 Keepalive ignored ({reason}) - client is active")

    def send_command(self, command: Dict[str, Any]) -> bool:
        """Send a command to the service"""
        if not self.connected or not self.sock:
            print("❌ Not connected")
            return False

        try:
            message = json.dumps(command) + '\n'
            self.sock.send(message.encode('utf-8'))
            return True
        except Exception as e:
            print(f"❌ Send error: {e}")
            return False

    # Tank-style commands (traditional)
    def tank_forward(self, speed: int = 60):
        """Move forward using tank controls"""
        return self.send_command({
            'type': 'tank_command',
            'command': 'FORWARD',
            'value': speed
        })

    def tank_backward(self, speed: int = 60):
        """Move backward using tank controls"""
        return self.send_command({
            'type': 'tank_command',
            'command': 'BACKWARD',
            'value': speed
        })

    def tank_left(self, speed: int = 50):
        """Turn left using tank controls"""
        return self.send_command({
            'type': 'tank_command',
            'command': 'LEFT',
            'value': speed
        })

    def tank_right(self, speed: int = 50):
        """Turn right using tank controls"""
        return self.send_command({
            'type': 'tank_command',
            'command': 'RIGHT',
            'value': speed
        })

    def tank_stop(self):
        """Stop using tank controls"""
        return self.send_command({
            'type': 'tank_command',
            'command': 'STOP',
            'value': 0
        })

    # Mecanum-style commands (advanced)
    def mecanum_forward(self, speed: int = 100):
        """Move forward using mecanum wheels"""
        return self.send_command({
            'type': 'mecanum_command',
            'motors': {
                'left_front': speed,
                'left_rear': speed,
                'right_front': speed,
                'right_rear': speed
            }
        })

    def mecanum_backward(self, speed: int = 100):
        """Move backward using mecanum wheels"""
        return self.send_command({
            'type': 'mecanum_command',
            'motors': {
                'left_front': -speed,
                'left_rear': -speed,
                'right_front': -speed,
                'right_rear': -speed
            }
        })

    def mecanum_strafe_left(self, speed: int = 100):
        """Strafe left (sideways movement)"""
        return self.send_command({
            'type': 'mecanum_command',
            'motors': {
                'left_front': speed,
                'left_rear': -speed,
                'right_front': -speed,
                'right_rear': speed
            }
        })

    def mecanum_strafe_right(self, speed: int = 100):
        """Strafe right (sideways movement)"""
        return self.send_command({
            'type': 'mecanum_command',
            'motors': {
                'left_front': -speed,
                'left_rear': speed,
                'right_front': speed,
                'right_rear': -speed
            }
        })

    def mecanum_rotate_clockwise(self, speed: int = 80):
        """Rotate clockwise in place"""
        return self.send_command({
            'type': 'mecanum_command',
            'motors': {
                'left_front': -speed,
                'left_rear': -speed,
                'right_front': speed,
                'right_rear': speed
            }
        })

    def mecanum_rotate_counterclockwise(self, speed: int = 80):
        """Rotate counter-clockwise in place"""
        return self.send_command({
            'type': 'mecanum_command',
            'motors': {
                'left_front': speed,
                'left_rear': speed,
                'right_front': -speed,
                'right_rear': -speed
            }
        })

    def mecanum_diagonal_forward_right(self, speed: int = 100):
        """Move diagonally forward-right"""
        return self.send_command({
            'type': 'mecanum_command',
            'motors': {
                'left_front': speed,
                'left_rear': 0,
                'right_front': 0,
                'right_rear': speed
            }
        })

    def mecanum_diagonal_forward_left(self, speed: int = 100):
        """Move diagonally forward-left"""
        return self.send_command({
            'type': 'mecanum_command',
            'motors': {
                'left_front': 0,
                'left_rear': speed,
                'right_front': speed,
                'right_rear': 0
            }
        })

    def mecanum_stop(self):
        """Stop all mecanum motors"""
        return self.send_command({
            'type': 'mecanum_command',
            'motors': {
                'left_front': 0,
                'left_rear': 0,
                'right_front': 0,
                'right_rear': 0
            }
        })

    def get_status(self):
        """Get service status"""
        return self.send_command({'type': 'get_status'})

    def _keepalive_loop(self):
        """Send periodic keepalive messages"""
        while self.running:
            try:
                self.send_command({'type': 'keepalive'})
                time.sleep(self.keepalive_interval)

                # Check if we're getting keepalive responses
                if time.time() - self.last_keepalive_response > 10:
                    print("⚠️  Warning: No keepalive response for 10 seconds")

            except Exception as e:
                if self.running:
                    print(f"❌ Keepalive error: {e}")
                break


def demo_tank_commands(client: MecanumClient):
    """Demonstrate tank-style commands"""
    print("\n🚗 Tank Command Demo")
    print("=" * 40)

    commands = [
        ("Forward", lambda: client.tank_forward(60)),
        ("Backward", lambda: client.tank_backward(60)),
        ("Turn Left", lambda: client.tank_left(50)),
        ("Turn Right", lambda: client.tank_right(50)),
        ("Stop", lambda: client.tank_stop()),
    ]

    for name, cmd_func in commands:
        print(f"🎯 {name}")
        cmd_func()
        time.sleep(1.5)


def demo_mecanum_commands(client: MecanumClient):
    """Demonstrate mecanum-specific commands"""
    print("\n🤖 Mecanum Command Demo")
    print("=" * 40)

    commands = [
        ("Forward", lambda: client.mecanum_forward(100)),
        ("Backward", lambda: client.mecanum_backward(100)),
        ("Strafe Left", lambda: client.mecanum_strafe_left(100)),
        ("Strafe Right", lambda: client.mecanum_strafe_right(100)),
        ("Rotate Clockwise", lambda: client.mecanum_rotate_clockwise(80)),
        ("Rotate Counter-Clockwise", lambda: client.mecanum_rotate_counterclockwise(80)),
        ("Diagonal Forward-Right", lambda: client.mecanum_diagonal_forward_right(100)),
        ("Diagonal Forward-Left", lambda: client.mecanum_diagonal_forward_left(100)),
        ("Stop", lambda: client.mecanum_stop()),
    ]

    for name, cmd_func in commands:
        print(f"🎯 {name}")
        cmd_func()
        time.sleep(2.0)


def interactive_mode(client: MecanumClient):
    """Interactive control mode"""
    print("\n🎮 Interactive Control Mode")
    print("=" * 40)
    print("Tank Commands:")
    print("  w/s - forward/backward    a/d - left/right    x - stop")
    print("Mecanum Commands:")
    print("  i/k - forward/backward    j/l - strafe left/right")
    print("  u/o - rotate left/right   n/m - diagonal movements")
    print("  space - mecanum stop      q - quit")
    print()

    while True:
        try:
            key = input("Command: ").lower().strip()

            if key == 'q':
                break
            elif key == 'w':
                client.tank_forward(60)
            elif key == 's':
                client.tank_backward(60)
            elif key == 'a':
                client.tank_left(50)
            elif key == 'd':
                client.tank_right(50)
            elif key == 'x':
                client.tank_stop()
            elif key == 'i':
                client.mecanum_forward(100)
            elif key == 'k':
                client.mecanum_backward(100)
            elif key == 'j':
                client.mecanum_strafe_left(100)
            elif key == 'l':
                client.mecanum_strafe_right(100)
            elif key == 'u':
                client.mecanum_rotate_counterclockwise(80)
            elif key == 'o':
                client.mecanum_rotate_clockwise(80)
            elif key == 'n':
                client.mecanum_diagonal_forward_left(100)
            elif key == 'm':
                client.mecanum_diagonal_forward_right(100)
            elif key == ' ':
                client.mecanum_stop()
            elif key == 'status':
                client.get_status()
            else:
                print("❓ Unknown command")

        except KeyboardInterrupt:
            break
        except EOFError:
            break


def main():
    """Main function"""
    print("🤖 Mecanum Wheel Control Client")
    print("=" * 50)

    client = MecanumClient()

    if not client.connect():
        return 1

    try:
        # Get initial status
        client.get_status()
        time.sleep(1)

        if len(sys.argv) > 1:
            mode = sys.argv[1].lower()

            if mode == 'tank':
                demo_tank_commands(client)
            elif mode == 'mecanum':
                demo_mecanum_commands(client)
            elif mode == 'interactive':
                interactive_mode(client)
            else:
                print(f"❓ Unknown mode: {mode}")
                print("Available modes: tank, mecanum, interactive")
        else:
            # Default: run both demos
            demo_tank_commands(client)
            time.sleep(2)
            demo_mecanum_commands(client)

            print("\n🎮 Starting interactive mode...")
            time.sleep(1)
            interactive_mode(client)

    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")

    finally:
        client.disconnect()

    return 0


if __name__ == "__main__":
    sys.exit(main())