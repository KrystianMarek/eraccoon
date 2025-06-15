#!/usr/bin/env python3
"""
Test New Command Format

Quick test script to verify the new JSON command format works correctly
with both tank and mecanum commands.
"""

import socket
import json
import time
import sys

def test_commands():
    """Test both tank and mecanum commands"""
    socket_path = '/tmp/motor-proxy/motor_controller.sock'

    try:
        # Connect to the service
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(socket_path)
        print(f"✅ Connected to {socket_path}")

        # Test tank commands
        print("\n🚗 Testing Tank Commands")
        print("-" * 30)

        tank_commands = [
            {"type": "tank_command", "command": "FORWARD", "value": 60},
            {"type": "tank_command", "command": "BACKWARD", "value": 60},
            {"type": "tank_command", "command": "LEFT", "value": 50},
            {"type": "tank_command", "command": "RIGHT", "value": 50},
            {"type": "tank_command", "command": "STOP", "value": 0},
        ]

        for cmd in tank_commands:
            print(f"📤 Sending: {cmd}")
            message = json.dumps(cmd) + '\n'
            sock.send(message.encode('utf-8'))

            # Wait for response
            try:
                sock.settimeout(2.0)
                response = sock.recv(1024).decode('utf-8').strip()
                if response:
                    for line in response.split('\n'):
                        if line:
                            try:
                                resp_data = json.loads(line)
                                if resp_data.get('type') == 'tank_command_response':
                                    success = resp_data.get('success', False)
                                    print(f"📥 Response: {'✅' if success else '❌'} {resp_data.get('command')}:{resp_data.get('value')}")
                            except json.JSONDecodeError:
                                print(f"📥 Raw response: {line}")
            except socket.timeout:
                print("⏰ No response received")

            time.sleep(1)

        # Test mecanum commands
        print("\n🤖 Testing Mecanum Commands")
        print("-" * 30)

        mecanum_commands = [
            {
                "type": "mecanum_command",
                "motors": {"left_front": 100, "left_rear": 100, "right_front": 100, "right_rear": 100}
            },
            {
                "type": "mecanum_command",
                "motors": {"left_front": -100, "left_rear": 100, "right_front": 100, "right_rear": -100}
            },
            {
                "type": "mecanum_command",
                "motors": {"left_front": 100, "left_rear": -100, "right_front": -100, "right_rear": 100}
            },
            {
                "type": "mecanum_command",
                "motors": {"left_front": 0, "left_rear": 0, "right_front": 0, "right_rear": 0}
            },
        ]

        descriptions = ["Forward", "Strafe Right", "Strafe Left", "Stop"]

        for cmd, desc in zip(mecanum_commands, descriptions):
            print(f"📤 Sending {desc}: {cmd}")
            message = json.dumps(cmd) + '\n'
            sock.send(message.encode('utf-8'))

            # Wait for response
            try:
                sock.settimeout(2.0)
                response = sock.recv(1024).decode('utf-8').strip()
                if response:
                    for line in response.split('\n'):
                        if line:
                            try:
                                resp_data = json.loads(line)
                                if resp_data.get('type') == 'mecanum_command_response':
                                    success = resp_data.get('success', False)
                                    motors = resp_data.get('motors', {})
                                    print(f"📥 Response: {'✅' if success else '❌'} "
                                          f"LF:{motors.get('left_front')} LR:{motors.get('left_rear')} "
                                          f"RF:{motors.get('right_front')} RR:{motors.get('right_rear')}")
                            except json.JSONDecodeError:
                                print(f"📥 Raw response: {line}")
            except socket.timeout:
                print("⏰ No response received")

            time.sleep(1.5)



        # Final stop
        stop_cmd = {"type": "tank_command", "command": "STOP", "value": 0}
        message = json.dumps(stop_cmd) + '\n'
        sock.send(message.encode('utf-8'))
        time.sleep(0.5)

        sock.close()
        print("\n✅ Test completed successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    print("🧪 Testing New Command Format")
    print("=" * 50)
    sys.exit(test_commands())