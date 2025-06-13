#!/usr/bin/env python3
"""
Simple sensor data monitor for the motor controller proxy
"""

import socket
import json
import sys

def monitor_sensors():
    socket_path = '/tmp/motor-proxy/motor_controller.sock'

    try:
        # Connect to Unix socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(socket_path)
        print(f"✅ Connected to {socket_path}")
        print("📡 Monitoring sensor data... (Ctrl+C to exit)")
        print("-" * 50)

        buffer = ""
        while True:
            # Receive data
            data = sock.recv(4096).decode('utf-8')
            if not data:
                break

            buffer += data

            # Process complete JSON messages
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if line:
                    try:
                        msg = json.loads(line)
                        if msg.get('type') == 'sensor_data':
                            sensor_data = msg.get('data', {})
                            if sensor_data:
                                print(f"🔍 FL:{sensor_data.get('front_left', '?'):>4} "
                                      f"FR:{sensor_data.get('front_right', '?'):>4} "
                                      f"RL:{sensor_data.get('rear_left', '?'):>4} "
                                      f"RR:{sensor_data.get('rear_right', '?'):>4} "
                                      f"| FC:{sensor_data.get('front_collision', False)} "
                                      f"RC:{sensor_data.get('rear_collision', False)}")
                        elif msg.get('type') == 'welcome':
                            print(f"🎉 {msg}")
                        elif msg.get('type') == 'arduino_message':
                            print(f"🤖 Arduino: {msg.get('message', '')}")
                        else:
                            print(f"📨 {msg.get('type', 'unknown')}: {line}")
                    except json.JSONDecodeError:
                        print(f"📝 Raw: {line}")

    except FileNotFoundError:
        print(f"❌ Socket not found: {socket_path}")
        print("   Make sure the motor proxy server is running")
    except ConnectionRefusedError:
        print(f"❌ Connection refused: {socket_path}")
        print("   Make sure the motor proxy server is running")
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        try:
            sock.close()
        except:
            pass

if __name__ == "__main__":
    monitor_sensors()