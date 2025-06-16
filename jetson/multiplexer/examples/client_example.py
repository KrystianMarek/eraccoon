#!/usr/bin/env python3
"""
Example client for the Motor Controller Proxy Service

This example demonstrates:
- Connecting to the multiplexer service
- Client identification and keepalive management
- Sending tank and mecanum commands
- Receiving sensor data
- Proper cleanup and error handling
"""

import json
import socket
import threading
import time
import sys
from typing import Optional


class MotorControllerClient:
    """Client for communicating with the Motor Controller Proxy Service"""

    def __init__(self, socket_path: str = '/tmp/motor-proxy/motor_controller.sock',
                 client_name: str = 'ExampleClient'):
        self.socket_path = socket_path
        self.client_name = client_name
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.receive_thread: Optional[threading.Thread] = None
        self.keepalive_thread: Optional[threading.Thread] = None

        # Client info received from server
        self.unique_name = None
        self.client_id = None

        # Keepalive management
        self.keepalive_interval = 2.5  # Send keepalive every 2.5 seconds (server expects every 3s)
        self.last_keepalive_response = time.time()

    def connect(self) -> bool:
        """Connect to the motor controller service"""
        try:
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.socket.connect(self.socket_path)
            self.running = True

            # Start receive thread
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()

            # Send identification
            self.send_message({
                'type': 'identify',
                'name': self.client_name
            })

            # Wait a moment for welcome and identification response
            time.sleep(0.5)

            # Start keepalive thread
            self.keepalive_thread = threading.Thread(target=self._keepalive_loop, daemon=True)
            self.keepalive_thread.start()

            print(f"✅ Connected to motor controller service as {self.unique_name or 'Unknown'}")
            return True

        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False

    def disconnect(self):
        """Disconnect from the service"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        print("👋 Disconnected from motor controller service")

    def send_message(self, message: dict) -> bool:
        """Send a message to the service"""
        try:
            if self.socket:
                json_msg = json.dumps(message) + '\n'
                self.socket.send(json_msg.encode('utf-8'))
                return True
        except Exception as e:
            print(f"❌ Failed to send message: {e}")
            return False
        return False

    def send_tank_command(self, command: str, value: int = 0) -> bool:
        """Send a tank-style motor command"""
        return self.send_message({
            'type': 'tank_command',
            'command': command.upper(),
            'value': value
        })

    def send_mecanum_command(self, left_front: int, left_rear: int,
                           right_front: int, right_rear: int) -> bool:
        """Send a mecanum-style motor command"""
        return self.send_message({
            'type': 'mecanum_command',
            'motors': {
                'left_front': left_front,
                'left_rear': left_rear,
                'right_front': right_front,
                'right_rear': right_rear
            }
        })

    def send_keepalive(self) -> bool:
        """Send a keepalive message"""
        return self.send_message({
            'type': 'keepalive'
        })

    def get_status(self) -> bool:
        """Request server status"""
        return self.send_message({
            'type': 'get_status'
        })

    def _receive_loop(self):
        """Receive messages from the service"""
        buffer = ""

        while self.running:
            try:
                if self.socket:
                    data = self.socket.recv(1024).decode('utf-8')
                    if not data:
                        break

                    buffer += data
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if line.strip():
                            self._handle_message(line.strip())

            except Exception as e:
                if self.running:
                    print(f"❌ Receive error: {e}")
                break

    def _handle_message(self, message: str):
        """Handle a message from the service"""
        try:
            data = json.loads(message)
            msg_type = data.get('type', '')

            if msg_type == 'welcome':
                self.client_id = data.get('client_id')
                print(f"🎉 Welcome! Client ID: {self.client_id}")

            elif msg_type == 'identify_response':
                self.unique_name = data.get('unique_name')
                claimed_name = data.get('claimed_name')
                print(f"🏷️  Identified as {self.unique_name} (claimed: {claimed_name})")

            elif msg_type == 'keepalive_response':
                self.last_keepalive_response = time.time()
                print("💓 Keepalive acknowledged")

            elif msg_type == 'sensor_data':
                # Print sensor data (abbreviated for readability)
                sensors = data.get('sensors', {})
                print(f"📊 Sensors: Temp={sensors.get('temperature', 'N/A')}°C, "
                      f"Humidity={sensors.get('humidity', 'N/A')}%, "
                      f"Distance={sensors.get('distance', 'N/A')}cm")

            elif msg_type == 'tank_command_response':
                success = "✅" if data.get('success') else "❌"
                print(f"{success} Tank command: {data.get('command')} = {data.get('value')}")

            elif msg_type == 'mecanum_command_response':
                success = "✅" if data.get('success') else "❌"
                motors = data.get('motors', {})
                print(f"{success} Mecanum: LF={motors.get('left_front')}, "
                      f"LR={motors.get('left_rear')}, RF={motors.get('right_front')}, "
                      f"RR={motors.get('right_rear')}")

            elif msg_type == 'error':
                print(f"❌ Error: {data.get('message')}")

            elif msg_type == 'status':
                print(f"📊 Status: Arduino={data.get('arduino_state')}, "
                      f"Clients={len(data.get('clients', []))}")

            else:
                print(f"📨 Received: {msg_type}")

        except json.JSONDecodeError:
            print(f"❌ Invalid JSON received: {message}")
        except Exception as e:
            print(f"❌ Error handling message: {e}")

    def _keepalive_loop(self):
        """Send periodic keepalive messages"""
        while self.running:
            try:
                self.send_keepalive()
                time.sleep(self.keepalive_interval)

                # Check if we're getting keepalive responses
                if time.time() - self.last_keepalive_response > 10:
                    print("⚠️  Warning: No keepalive response for 10 seconds")

            except Exception as e:
                if self.running:
                    print(f"❌ Keepalive error: {e}")
                break


def demo_tank_commands(client: MotorControllerClient):
    """Demonstrate tank-style commands"""
    print("\n🚗 Tank Command Demo")
    print("=" * 40)

    commands = [
        ('FORWARD', 100),
        ('BACKWARD', 80),
        ('LEFT', 60),
        ('RIGHT', 60),
        ('STOP', 0)
    ]

    for command, value in commands:
        print(f"Sending: {command} {value}")
        client.send_tank_command(command, value)
        time.sleep(1)


def demo_mecanum_commands(client: MotorControllerClient):
    """Demonstrate mecanum-style commands"""
    print("\n🕹️  Mecanum Command Demo")
    print("=" * 40)

    movements = [
        ("Forward", 100, 100, 100, 100),
        ("Backward", -100, -100, -100, -100),
        ("Strafe Left", -100, 100, 100, -100),
        ("Strafe Right", 100, -100, -100, 100),
        ("Rotate Left", -100, -100, 100, 100),
        ("Rotate Right", 100, 100, -100, -100),
        ("Stop", 0, 0, 0, 0)
    ]

    for name, lf, lr, rf, rr in movements:
        print(f"Sending: {name} (LF={lf}, LR={lr}, RF={rf}, RR={rr})")
        client.send_mecanum_command(lf, lr, rf, rr)
        time.sleep(1.5)


def interactive_mode(client: MotorControllerClient):
    """Interactive command mode"""
    print("\n🎮 Interactive Mode")
    print("=" * 40)
    print("Commands:")
    print("  tank <command> <value>  - Send tank command")
    print("  mecanum <lf> <lr> <rf> <rr> - Send mecanum command")
    print("  status                  - Get server status")
    print("  keepalive              - Send keepalive")
    print("  quit                   - Exit")
    print()

    while client.running:
        try:
            cmd = input("🎮 > ").strip().split()
            if not cmd:
                continue

            if cmd[0] == 'quit':
                break
            elif cmd[0] == 'tank' and len(cmd) >= 3:
                client.send_tank_command(cmd[1], int(cmd[2]))
            elif cmd[0] == 'mecanum' and len(cmd) >= 5:
                client.send_mecanum_command(int(cmd[1]), int(cmd[2]), int(cmd[3]), int(cmd[4]))
            elif cmd[0] == 'status':
                client.get_status()
            elif cmd[0] == 'keepalive':
                client.send_keepalive()
            else:
                print("❌ Invalid command")

        except KeyboardInterrupt:
            break
        except ValueError:
            print("❌ Invalid number format")
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='Motor Controller Client Example')
    parser.add_argument('--socket-path', default='/tmp/motor-proxy/motor_controller.sock',
                       help='Unix socket path')
    parser.add_argument('--name', default='ExampleClient',
                       help='Client name to identify as')
    parser.add_argument('--mode', choices=['demo', 'interactive'], default='demo',
                       help='Run mode: demo or interactive')

    args = parser.parse_args()

    print("🤖 Motor Controller Client Example")
    print("=" * 50)

    # Create and connect client
    client = MotorControllerClient(args.socket_path, args.name)

    if not client.connect():
        return 1

    try:
        if args.mode == 'demo':
            # Run demonstrations
            demo_tank_commands(client)
            demo_mecanum_commands(client)

            print("\n📊 Getting final status...")
            client.get_status()
            time.sleep(2)

        else:
            # Interactive mode
            interactive_mode(client)

    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        client.disconnect()

    return 0


if __name__ == "__main__":
    sys.exit(main())