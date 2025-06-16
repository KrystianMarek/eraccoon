#!/usr/bin/env python3
"""
Intelligent Keepalive System Demo

This example demonstrates the intelligent keepalive system implemented in the
motor controller proxy service. It shows how:

1. Motor commands automatically act as keepalives
2. Explicit keepalives are ignored during active control periods
3. The server responds differently based on client activity
4. Connection is maintained through either keepalives OR motor commands

The demo runs through different scenarios to showcase the system behavior.
"""

import json
import socket
import threading
import time
import sys
from typing import Optional


class IntelligentKeepaliveDemo:
    """Demo client showcasing intelligent keepalive behavior"""

    def __init__(self, socket_path: str = '/tmp/motor-proxy/motor_controller.sock'):
        self.socket_path = socket_path
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.receive_thread: Optional[threading.Thread] = None

        # Track responses for demo purposes
        self.keepalive_responses = []
        self.keepalive_ignored_count = 0
        self.keepalive_acknowledged_count = 0

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
                'name': 'IntelligentKeepaliveDemo'
            })

            time.sleep(0.5)  # Wait for identification
            print("✅ Connected to motor controller service")
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

    def send_keepalive(self) -> bool:
        """Send a keepalive message"""
        print("💓 Sending explicit keepalive...")
        return self.send_message({'type': 'keepalive'})

    def send_motor_command(self, command: str = "FORWARD", value: int = 50) -> bool:
        """Send a motor command"""
        print(f"🚗 Sending motor command: {command} {value}")
        return self.send_message({
            'type': 'tank_command',
            'command': command,
            'value': value
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
                client_id = data.get('client_id')
                print(f"🎉 Welcome! Client ID: {client_id}")

            elif msg_type == 'identify_response':
                unique_name = data.get('unique_name')
                print(f"🏷️  Identified as {unique_name}")

            elif msg_type == 'keepalive_response':
                self.keepalive_acknowledged_count += 1
                print(f"✅ Keepalive ACKNOWLEDGED (idle client)")
                self.keepalive_responses.append(('acknowledged', time.time()))

            elif msg_type == 'keepalive_ignored':
                self.keepalive_ignored_count += 1
                reason = data.get('reason', 'unknown')
                print(f"🚫 Keepalive IGNORED ({reason}) - client is active")
                self.keepalive_responses.append(('ignored', time.time()))

            elif msg_type == 'tank_command_response':
                success = "✅" if data.get('success') else "❌"
                command = data.get('command')
                value = data.get('value')
                print(f"{success} Motor command executed: {command} {value}")

            elif msg_type == 'error':
                print(f"❌ Error: {data.get('message')}")

        except json.JSONDecodeError:
            print(f"❌ Invalid JSON received: {message}")
        except Exception as e:
            print(f"❌ Error handling message: {e}")

    def demo_idle_keepalives(self):
        """Demo 1: Keepalives when client is idle"""
        print("\n" + "="*60)
        print("📋 DEMO 1: Keepalives when client is IDLE")
        print("="*60)
        print("When no motor commands are sent, explicit keepalives are acknowledged.")
        print()

        for i in range(3):
            self.send_keepalive()
            time.sleep(1.5)

        print(f"\n📊 Result: {self.keepalive_acknowledged_count} keepalives acknowledged")

    def demo_active_keepalives(self):
        """Demo 2: Keepalives when client is active"""
        print("\n" + "="*60)
        print("📋 DEMO 2: Keepalives when client is ACTIVE")
        print("="*60)
        print("When motor commands are being sent, explicit keepalives are ignored.")
        print()

        # Send a motor command to make client "active"
        self.send_motor_command("FORWARD", 30)
        time.sleep(0.5)

        # Now try sending keepalives - they should be ignored
        for i in range(3):
            self.send_keepalive()
            time.sleep(1)

        print(f"\n📊 Result: {self.keepalive_ignored_count} keepalives ignored")

    def demo_mixed_activity(self):
        """Demo 3: Mixed motor commands and keepalives"""
        print("\n" + "="*60)
        print("📋 DEMO 3: Mixed motor commands and keepalives")
        print("="*60)
        print("Showing how the system transitions between active and idle states.")
        print()

        # Start with motor commands (active period)
        print("🔄 Phase 1: Active period with motor commands")
        self.send_motor_command("FORWARD", 40)
        time.sleep(0.5)
        self.send_keepalive()  # Should be ignored
        time.sleep(1)
        self.send_motor_command("LEFT", 30)
        time.sleep(0.5)
        self.send_keepalive()  # Should be ignored
        time.sleep(1)

        # Wait for idle period (>2 seconds since last motor command)
        print("\n⏳ Phase 2: Waiting for idle period (3 seconds)...")
        time.sleep(3)

        # Now send keepalives - should be acknowledged
        print("\n💤 Phase 3: Idle period - keepalives should be acknowledged")
        self.send_keepalive()  # Should be acknowledged
        time.sleep(1)
        self.send_keepalive()  # Should be acknowledged
        time.sleep(1)

        print(f"\n📊 Final Results:")
        print(f"   Keepalives acknowledged: {self.keepalive_acknowledged_count}")
        print(f"   Keepalives ignored: {self.keepalive_ignored_count}")

    def demo_motor_commands_as_keepalives(self):
        """Demo 4: Motor commands acting as implicit keepalives"""
        print("\n" + "="*60)
        print("📋 DEMO 4: Motor commands as implicit keepalives")
        print("="*60)
        print("Motor commands automatically act as keepalives - no explicit keepalives needed!")
        print()

        print("🚗 Sending motor commands every 2 seconds for 10 seconds...")
        print("   (No explicit keepalives needed - connection stays alive)")

        commands = [
            ("FORWARD", 50),
            ("RIGHT", 40),
            ("BACKWARD", 50),
            ("LEFT", 40),
            ("STOP", 0)
        ]

        for command, value in commands:
            self.send_motor_command(command, value)
            time.sleep(2)

        print("\n✅ Connection maintained through motor commands alone!")

    def run_demo(self):
        """Run the complete intelligent keepalive demo"""
        print("🤖 Intelligent Keepalive System Demo")
        print("=" * 60)
        print("This demo showcases the intelligent keepalive system behavior:")
        print("• Motor commands automatically act as keepalives")
        print("• Explicit keepalives are ignored during active control")
        print("• Server responds differently based on client activity")
        print("• Connection maintained through either keepalives OR motor commands")
        print()

        try:
            self.demo_idle_keepalives()
            time.sleep(2)

            self.demo_active_keepalives()
            time.sleep(2)

            self.demo_mixed_activity()
            time.sleep(2)

            self.demo_motor_commands_as_keepalives()

            print("\n" + "="*60)
            print("🎉 DEMO COMPLETE!")
            print("="*60)
            print("Key Takeaways:")
            print("• Idle clients: Explicit keepalives are acknowledged")
            print("• Active clients: Explicit keepalives are ignored (motor commands suffice)")
            print("• Motor commands act as implicit keepalives")
            print("• Connection stays alive with either approach")
            print(f"\nTotal keepalive responses: {len(self.keepalive_responses)}")
            print(f"  - Acknowledged: {self.keepalive_acknowledged_count}")
            print(f"  - Ignored: {self.keepalive_ignored_count}")

        except KeyboardInterrupt:
            print("\n🛑 Demo interrupted by user")


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='Intelligent Keepalive System Demo')
    parser.add_argument('--socket-path', default='/tmp/motor-proxy/motor_controller.sock',
                       help='Unix socket path')

    args = parser.parse_args()

    # Create and connect demo client
    demo = IntelligentKeepaliveDemo(args.socket_path)

    if not demo.connect():
        return 1

    try:
        demo.run_demo()
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        demo.disconnect()

    return 0


if __name__ == "__main__":
    sys.exit(main())