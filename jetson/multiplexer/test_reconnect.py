#!/usr/bin/env python3
import socket
import json
import time

def test_reconnection():
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect('/tmp/motor-proxy/motor_controller.sock')
        print("✅ Connected to motor proxy")

        # Send a motor command to trigger reconnection
        cmd = {'type': 'motor_command', 'command': 'FORWARD', 'value': 0}
        print("📤 Sending FORWARD command to trigger reconnection...")
        sock.send((json.dumps(cmd) + '\n').encode())

        # Read response
        print("📥 Waiting for response...")
        response = sock.recv(1024).decode()
        print(f"📨 Response: {response}")

        sock.close()
        print("✅ Test completed")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_reconnection()