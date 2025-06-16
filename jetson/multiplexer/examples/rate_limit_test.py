#!/usr/bin/env python3
"""
Rate Limiting Test for Motor Controller Proxy Service

This example demonstrates:
- Multiple clients connecting simultaneously
- Rate limiting behavior under high command load
- Keepalive management with multiple clients
- Observing dropped command logging
"""

import json
import socket
import threading
import time
import sys
import random
from typing import Optional, List


class TestClient:
    """Test client for rate limiting demonstration"""

    def __init__(self, socket_path: str, client_name: str, client_id: int):
        self.socket_path = socket_path
        self.client_name = f"{client_name}-{client_id:02d}"
        self.client_id = client_id
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.receive_thread: Optional[threading.Thread] = None
        self.keepalive_thread: Optional[threading.Thread] = None

        # Stats
        self.commands_sent = 0
        self.responses_received = 0
        self.errors_received = 0

        # Unique name from server
        self.unique_name = None

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

            # Wait for identification
            time.sleep(0.2)

            # Start keepalive thread
            self.keepalive_thread = threading.Thread(target=self._keepalive_loop, daemon=True)
            self.keepalive_thread.start()

            print(f"✅ {self.unique_name or self.client_name} connected")
            return True

        except Exception as e:
            print(f"❌ {self.client_name} failed to connect: {e}")
            return False

    def disconnect(self):
        """Disconnect from the service"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass

    def send_message(self, message: dict) -> bool:
        """Send a message to the service"""
        try:
            if self.socket and self.running:
                json_msg = json.dumps(message) + '\n'
                self.socket.send(json_msg.encode('utf-8'))
                return True
        except Exception as e:
            if self.running:
                print(f"❌ {self.client_name} send error: {e}")
            return False
        return False

    def send_random_tank_command(self) -> bool:
        """Send a random tank command"""
        commands = ['FORWARD', 'BACKWARD', 'LEFT', 'RIGHT', 'STOP']
        command = random.choice(commands)
        value = random.randint(0, 255) if command != 'STOP' else 0

        success = self.send_message({
            'type': 'tank_command',
            'command': command,
            'value': value
        })

        if success:
            self.commands_sent += 1

        return success

    def send_random_mecanum_command(self) -> bool:
        """Send a random mecanum command"""
        motors = {
            'left_front': random.randint(-255, 255),
            'left_rear': random.randint(-255, 255),
            'right_front': random.randint(-255, 255),
            'right_rear': random.randint(-255, 255)
        }

        success = self.send_message({
            'type': 'mecanum_command',
            'motors': motors
        })

        if success:
            self.commands_sent += 1

        return success

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

            if msg_type == 'identify_response':
                self.unique_name = data.get('unique_name')

            elif msg_type in ['tank_command_response', 'mecanum_command_response']:
                self.responses_received += 1

            elif msg_type == 'error':
                self.errors_received += 1

            elif msg_type in ['keepalive_response', 'keepalive_ignored']:
                # Track keepalive responses for connection health
                pass

        except json.JSONDecodeError:
            pass
        except Exception:
            pass

    def _keepalive_loop(self):
        """Send periodic keepalive messages"""
        while self.running:
            try:
                self.send_message({'type': 'keepalive'})
                time.sleep(2.5)  # Send every 2.5 seconds
            except Exception:
                break

    def get_stats(self) -> dict:
        """Get client statistics"""
        return {
            'name': self.unique_name or self.client_name,
            'commands_sent': self.commands_sent,
            'responses_received': self.responses_received,
            'errors_received': self.errors_received
        }


def run_rate_limit_test(socket_path: str, num_clients: int, test_duration: int,
                       commands_per_second: float):
    """Run rate limiting test with multiple clients"""
    print(f"🧪 Rate Limiting Test")
    print(f"   Clients: {num_clients}")
    print(f"   Duration: {test_duration} seconds")
    print(f"   Commands per client per second: {commands_per_second}")
    print(f"   Total expected commands/sec: {num_clients * commands_per_second}")
    print("=" * 60)

    # Create and connect clients
    clients: List[TestClient] = []
    for i in range(num_clients):
        client = TestClient(socket_path, "RateTestClient", i + 1)
        if client.connect():
            clients.append(client)
        else:
            print(f"❌ Failed to connect client {i + 1}")

    if not clients:
        print("❌ No clients connected, aborting test")
        return

    print(f"✅ Connected {len(clients)} clients")
    time.sleep(1)  # Let clients settle

    # Start command sending threads
    def send_commands(client: TestClient):
        """Send commands at specified rate"""
        interval = 1.0 / commands_per_second
        end_time = time.time() + test_duration

        while time.time() < end_time and client.running:
            # Randomly choose between tank and mecanum commands
            if random.choice([True, False]):
                client.send_random_tank_command()
            else:
                client.send_random_mecanum_command()

            time.sleep(interval)

    # Start sending threads
    threads = []
    start_time = time.time()

    for client in clients:
        thread = threading.Thread(target=send_commands, args=(client,), daemon=True)
        thread.start()
        threads.append(thread)

    print(f"🚀 Started command sending for {test_duration} seconds...")

    # Monitor progress
    for i in range(test_duration):
        time.sleep(1)
        total_sent = sum(c.commands_sent for c in clients)
        total_responses = sum(c.responses_received for c in clients)
        total_errors = sum(c.errors_received for c in clients)

        print(f"⏱️  {i+1:2d}s: Sent={total_sent:4d}, Responses={total_responses:4d}, "
              f"Errors={total_errors:3d}, Rate={total_sent/(i+1):.1f}/s")

    # Wait for threads to finish
    for thread in threads:
        thread.join(timeout=1)

    # Final statistics
    print("\n📊 Final Statistics:")
    print("-" * 60)

    total_sent = 0
    total_responses = 0
    total_errors = 0

    for client in clients:
        stats = client.get_stats()
        print(f"  {stats['name']:15s}: Sent={stats['commands_sent']:4d}, "
              f"Resp={stats['responses_received']:4d}, Err={stats['errors_received']:3d}")

        total_sent += stats['commands_sent']
        total_responses += stats['responses_received']
        total_errors += stats['errors_received']

    print("-" * 60)
    actual_duration = time.time() - start_time
    print(f"  {'TOTAL':15s}: Sent={total_sent:4d}, Resp={total_responses:4d}, Err={total_errors:3d}")
    print(f"  Actual rate: {total_sent/actual_duration:.1f} commands/second")
    print(f"  Success rate: {(total_responses/total_sent*100) if total_sent > 0 else 0:.1f}%")
    print(f"  Drop rate: {((total_sent-total_responses)/total_sent*100) if total_sent > 0 else 0:.1f}%")

    # Disconnect clients
    print("\n🧹 Disconnecting clients...")
    for client in clients:
        client.disconnect()

    print("✅ Rate limiting test completed!")


def run_keepalive_test(socket_path: str, num_clients: int):
    """Test keepalive functionality with multiple clients"""
    print(f"💓 Keepalive Test")
    print(f"   Clients: {num_clients}")
    print(f"   Will stop sending keepalives after 10 seconds")
    print("=" * 60)

    # Create and connect clients
    clients: List[TestClient] = []
    for i in range(num_clients):
        client = TestClient(socket_path, "KeepAliveTest", i + 1)
        if client.connect():
            clients.append(client)

    if not clients:
        print("❌ No clients connected, aborting test")
        return

    print(f"✅ Connected {len(clients)} clients")
    print("⏱️  Waiting 10 seconds with normal keepalives...")
    time.sleep(10)

    # Stop keepalives for half the clients
    stopped_clients = clients[:len(clients)//2]
    active_clients = clients[len(clients)//2:]

    print(f"🛑 Stopping keepalives for {len(stopped_clients)} clients...")
    for client in stopped_clients:
        client.running = False  # This will stop their keepalive threads

    print("⏱️  Waiting 15 seconds to see disconnections...")
    for i in range(15):
        time.sleep(1)
        print(f"   {i+1:2d}s elapsed...")

    print(f"✅ Keepalive test completed!")
    print(f"   Expected: {len(stopped_clients)} clients disconnected by server")
    print(f"   Expected: {len(active_clients)} clients still connected")

    # Clean up remaining clients
    for client in active_clients:
        client.disconnect()


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='Rate Limiting Test for Motor Controller')
    parser.add_argument('--socket-path', default='/var/eraccoon/multiplexer/socket/motor_proxy_service.sock',
                       help='Unix socket path')
    parser.add_argument('--test', choices=['rate', 'keepalive', 'both'], default='both',
                       help='Test type to run')
    parser.add_argument('--clients', type=int, default=3,
                       help='Number of test clients')
    parser.add_argument('--duration', type=int, default=30,
                       help='Test duration in seconds')
    parser.add_argument('--rate', type=float, default=5.0,
                       help='Commands per second per client')

    args = parser.parse_args()

    print("🧪 Motor Controller Rate Limiting Test Suite")
    print("=" * 60)

    try:
        if args.test in ['rate', 'both']:
            run_rate_limit_test(args.socket_path, args.clients, args.duration, args.rate)

            if args.test == 'both':
                print("\n" + "="*60 + "\n")
                time.sleep(2)

        if args.test in ['keepalive', 'both']:
            run_keepalive_test(args.socket_path, args.clients)

    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"❌ Test error: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())