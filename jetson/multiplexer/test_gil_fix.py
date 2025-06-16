#!/usr/bin/env python3
"""
Test script to verify GIL contention fix

This script simulates the remote service connection pattern that was causing
the Arduino connection to drop.
"""

import json
import socket
import threading
import time
import sys


class TestClient:
    """Test client that simulates the remote service behavior"""

    def __init__(self, socket_path: str, client_name: str):
        self.socket_path = socket_path
        self.client_name = client_name
        self.socket = None
        self.running = False

    def connect(self) -> bool:
        """Connect and send rapid messages like the remote service"""
        try:
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.socket.connect(self.socket_path)
            self.running = True

            print(f"✅ {self.client_name} connected")

            # Simulate the rapid message sequence from remote service
            messages = [
                {'type': 'identify', 'name': self.client_name},
                {'type': 'get_status'},
                {'type': 'set_priority', 'priority': 1},
                {'type': 'get_status'},
            ]

            # Send messages rapidly (like remote service does)
            for msg in messages:
                self.send_message(msg)
                time.sleep(0.01)  # Very short delay between messages

            # Start keepalive loop
            keepalive_thread = threading.Thread(target=self._keepalive_loop, daemon=True)
            keepalive_thread.start()

            # Start receive loop
            receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            receive_thread.start()

            return True

        except Exception as e:
            print(f"❌ {self.client_name} failed to connect: {e}")
            return False

    def send_message(self, message: dict) -> bool:
        """Send a message to the service"""
        try:
            if self.socket and self.running:
                json_msg = json.dumps(message) + '\n'
                self.socket.send(json_msg.encode('utf-8'))
                print(f"📤 {self.client_name} sent: {message['type']}")
                return True
        except Exception as e:
            print(f"❌ {self.client_name} send error: {e}")
            return False
        return False

    def _keepalive_loop(self):
        """Send periodic keepalive messages"""
        while self.running:
            try:
                self.send_message({'type': 'keepalive'})
                time.sleep(2.5)  # Send every 2.5 seconds
            except Exception:
                break

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
                    print(f"❌ {self.client_name} receive error: {e}")
                break

    def _handle_message(self, message: str):
        """Handle a message from the service"""
        try:
            data = json.loads(message)
            msg_type = data.get('type', '')

            if msg_type == 'welcome':
                client_id = data.get('client_id')
                print(f"🎉 {self.client_name} welcomed as {client_id}")

            elif msg_type == 'identify_response':
                unique_name = data.get('unique_name')
                print(f"🏷️  {self.client_name} identified as {unique_name}")

            elif msg_type == 'sensor_data':
                # Don't print sensor data to avoid spam
                pass

            elif msg_type == 'error':
                print(f"❌ {self.client_name} error: {data.get('message')}")

        except json.JSONDecodeError:
            pass
        except Exception:
            pass

    def disconnect(self):
        """Disconnect from the service"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass


def main():
    """Main test function"""
    socket_path = '/tmp/motor-proxy/motor_controller.sock'

    print("🧪 GIL Contention Fix Test")
    print("=" * 50)
    print("This test simulates the remote service connection pattern")
    print("that was causing Arduino connection drops.")
    print("")

    # Create test client
    client = TestClient(socket_path, 'GIL_Test_Client')

    if not client.connect():
        print("❌ Failed to connect to multiplexer service")
        print("💡 Make sure the multiplexer service is running")
        return 1

    try:
        print("⏱️  Monitoring for 30 seconds...")
        print("📊 Watch the multiplexer logs for:")
        print("   - No 'No sensor data for X.Xs' warnings")
        print("   - Continued sensor data flow")
        print("   - No Arduino connection drops")
        print("")

        # Monitor for 30 seconds
        for i in range(30):
            time.sleep(1)
            if i % 5 == 0:
                print(f"⏱️  {i}s elapsed - sending status request...")
                client.send_message({'type': 'get_status'})

        print("✅ Test completed successfully!")
        print("📊 Check multiplexer logs to verify:")
        print("   - Arduino connection remained stable")
        print("   - Sensor data continued flowing")
        print("   - No GIL contention warnings")

    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"❌ Test error: {e}")
    finally:
        client.disconnect()
        print("👋 Test client disconnected")

    return 0


if __name__ == "__main__":
    sys.exit(main())