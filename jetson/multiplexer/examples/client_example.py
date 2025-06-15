#!/usr/bin/env python3
"""
Example client for Motor Controller Proxy/Multiplexer

This script demonstrates how to connect to the Unix socket server
and control the Arduino robot via the proxy service.
"""

import socket
import json
import time
import threading
import sys
from typing import Dict, Any, Optional


class MotorProxyClient:
    """Client for connecting to the Motor Controller Proxy via Unix socket"""

    def __init__(self, socket_path: str = '/tmp/motor-proxy/motor_controller.sock'):
        self.socket_path = socket_path
        self.sock: Optional[socket.socket] = None
        self.connected = False
        self.client_id: Optional[str] = None
        self._stop_event = threading.Event()

    def connect(self) -> bool:
        """Connect to the proxy server"""
        try:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.connect(self.socket_path)
            self.connected = True

            # Start message receiving thread
            self._receiver_thread = threading.Thread(target=self._receive_messages, daemon=True)
            self._receiver_thread.start()

            print(f"✅ Connected to motor proxy at {self.socket_path}")
            return True

        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False

    def disconnect(self):
        """Disconnect from the proxy server"""
        self.connected = False
        self._stop_event.set()

        if self.sock:
            try:
                self.sock.close()
            except:
                pass

        print("👋 Disconnected from motor proxy")

    def send_message(self, message: Dict[str, Any]) -> bool:
        """Send a message to the proxy server"""
        if not self.connected or not self.sock:
            print("❌ Not connected to proxy server")
            return False

        try:
            msg_str = json.dumps(message) + '\n'
            self.sock.send(msg_str.encode('utf-8'))
            return True
        except Exception as e:
            print(f"❌ Failed to send message: {e}")
            return False

    def _receive_messages(self):
        """Background thread to receive messages from server"""
        buffer = ""

        while self.connected and not self._stop_event.is_set():
            try:
                data = self.sock.recv(4096).decode('utf-8')
                if not data:
                    break

                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line:
                        self._process_message(line)

            except Exception as e:
                if self.connected:
                    print(f"❌ Error receiving message: {e}")
                break

    def _process_message(self, message: str):
        """Process a received message"""
        try:
            data = json.loads(message)
            msg_type = data.get('type', '')

            if msg_type == 'welcome':
                self.client_id = data.get('client_id')
                print(f"✅ Connected as {self.client_id}")

            elif msg_type == 'status':
                arduino_state = data.get('arduino_state', 'unknown')
                arduino_connected = data.get('arduino_connected', False)
                if arduino_connected:
                    print(f"📊 Arduino: {arduino_state}")
                else:
                    print(f"⚠️  Arduino: {arduino_state} (disconnected)")

            elif msg_type == 'tank_command_response':
                command = data.get('command', '')
                value = data.get('value', 0)
                success = data.get('success', False)
                status = "✅" if success else "❌"
                print(f"🎮 {status} {command}:{value}")

            elif msg_type == 'sensor_data':
                # Don't print sensor data - too noisy for command interface
                pass

            elif msg_type == 'arduino_message':
                message_text = data.get('message', '')
                # Only show important Arduino messages, skip routine ones
                if any(keyword in message_text.upper() for keyword in ['ERROR', 'WARNING', 'TIMEOUT', 'DISCONNECTED', 'CONNECTED', 'READY']):
                    print(f"🤖 Arduino: {message_text}")

            elif msg_type == 'error':
                error_msg = data.get('message', 'Unknown error')
                print(f"❌ Error: {error_msg}")

            elif msg_type == 'arduino_connection':
                state = data.get('state', 'unknown')
                if state in ['connected', 'disconnected']:
                    print(f"🔄 Arduino: {state}")

            elif msg_type == 'pong':
                print("🏓 Pong")

        except json.JSONDecodeError:
            print(f"❌ Invalid JSON received: {message}")
        except Exception as e:
            print(f"❌ Error processing message: {e}")

    # Convenience methods for robot control
    def move_forward(self, speed: int = 60):
        """Move robot forward"""
        return self.send_message({'type': 'tank_command', 'command': 'FORWARD', 'value': speed})

    def move_backward(self, speed: int = 60):
        """Move robot backward"""
        return self.send_message({'type': 'tank_command', 'command': 'BACKWARD', 'value': speed})

    def turn_left(self, speed: int = 40):
        """Turn robot left"""
        return self.send_message({'type': 'tank_command', 'command': 'LEFT', 'value': speed})

    def turn_right(self, speed: int = 40):
        """Turn robot right"""
        return self.send_message({'type': 'tank_command', 'command': 'RIGHT', 'value': speed})

    def stop(self):
        """Stop robot movement"""
        return self.send_message({'type': 'tank_command', 'command': 'STOP', 'value': 0})

    def reset(self):
        """Reset robot to joystick control"""
        return self.send_message({'type': 'tank_command', 'command': 'RESET', 'value': 0})

    def ping(self):
        """Send ping to server"""
        return self.send_message({'type': 'ping'})

    def get_status(self):
        """Get server status"""
        return self.send_message({'type': 'get_status'})

    def get_sensor_data(self):
        """Get current sensor data"""
        return self.send_message({'type': 'get_sensor_data'})

    def set_priority(self, priority: int):
        """Set client priority (lower number = higher priority)"""
        return self.send_message({'type': 'set_priority', 'priority': priority})


def interactive_demo():
    """Interactive demo of robot control"""
    print("🤖 Motor Controller Proxy - Interactive Demo")
    print("=" * 50)

    # Create client and connect
    client = MotorProxyClient()
    if not client.connect():
        return

    # Wait for welcome message
    time.sleep(1)

    try:
        print("\n🎮 Commands: w/s=forward/back, a/d=left/right, x=stop, r=reset, i=status, q=quit")

        while True:
            choice = input("\n> ").lower().strip()

            if choice == 'w':
                client.move_forward(60)
            elif choice == 's':
                client.move_backward(60)
            elif choice == 'a':
                client.turn_left(40)
            elif choice == 'd':
                client.turn_right(40)
            elif choice == 'x':
                client.stop()
            elif choice == 'r':
                client.reset()
            elif choice == 'i':
                client.get_status()
            elif choice == 'p':
                client.ping()
            elif choice == 't':
                client.get_sensor_data()
            elif choice == 'q':
                break
            elif choice == '':
                continue
            else:
                print("❌ Invalid command")

            # Small delay to see responses
            time.sleep(0.3)

    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    finally:
        client.disconnect()


def automated_demo():
    """Automated demo showing basic robot movements"""
    print("🤖 Motor Controller Proxy - Automated Demo")
    print("=" * 50)

    # Create client and connect
    client = MotorProxyClient()
    if not client.connect():
        return

    # Wait for welcome message
    time.sleep(2)

    try:
        # Get initial status
        print("📊 Getting initial status...")
        client.get_status()
        time.sleep(1)

        # Perform sequence of movements
        movements = [
            ("Moving forward", lambda: client.move_forward(50)),
            ("Stopping", lambda: client.stop()),
            ("Moving backward", lambda: client.move_backward(50)),
            ("Stopping", lambda: client.stop()),
            ("Turning left", lambda: client.turn_left(40)),
            ("Stopping", lambda: client.stop()),
            ("Turning right", lambda: client.turn_right(40)),
            ("Stopping", lambda: client.stop()),
        ]

        for description, action in movements:
            print(f"🎮 {description}...")
            action()
            time.sleep(2)  # Wait between movements

        # Reset to joystick control
        print("🔄 Resetting to joystick control...")
        client.reset()
        time.sleep(1)

        print("✅ Automated demo completed!")

    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
    finally:
        client.disconnect()


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        if sys.argv[1] == 'auto':
            automated_demo()
        elif sys.argv[1] == 'interactive':
            interactive_demo()
        else:
            print("Usage: python client_example.py [auto|interactive]")
            print("  auto       - Run automated demo")
            print("  interactive - Run interactive demo (default)")
    else:
        interactive_demo()


if __name__ == "__main__":
    main()