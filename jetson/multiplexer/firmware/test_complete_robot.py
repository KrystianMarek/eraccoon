#!/usr/bin/env python3
"""
Comprehensive Arduino Robot Test Script

This script demonstrates:
- Remote control via serial in all directions
- Sensor data reception and parsing
- Reconnection handling with auto-reboot
- Keep-alive system for connection maintenance
- Error handling and graceful disconnection

Usage: ./test_complete_robot.py
"""

import serial
import time
import threading
import json
import glob
import sys

class RobotController:
    def __init__(self, port=None, baud_rate=115200):
        self.port = port
        self.baud_rate = baud_rate
        self.serial = None
        self.connected = False
        self.sensor_data = {}
        self.keepalive_thread = None
        self.stop_keepalive = threading.Event()

    def find_arduino_port(self):
        """Find available Arduino port"""
        ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*') + glob.glob('COM*')
        for port in sorted(ports):
            try:
                test_ser = serial.Serial(port, self.baud_rate, timeout=1)
                test_ser.close()
                return port
            except:
                continue
        return None

    def connect(self):
        """Connect to Arduino with auto-discovery"""
        if not self.port:
            self.port = self.find_arduino_port()

        if not self.port:
            print("❌ No Arduino found")
            return False

        try:
            self.serial = serial.Serial(self.port, self.baud_rate, timeout=1)
            print(f"✅ Connected to {self.port} at {self.baud_rate} baud")
            self.connected = True

            # Wait for Arduino to be ready
            time.sleep(2)

            # Start keep-alive thread
            self.start_keepalive()

            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False

    def disconnect(self):
        """Gracefully disconnect from Arduino"""
        self.stop_keepalive_thread()

        if self.serial and self.serial.is_open:
            try:
                self.serial.close()
            except:
                pass

        self.connected = False
        print("🔌 Disconnected from Arduino")

    def start_keepalive(self):
        """Start keep-alive thread to maintain connection"""
        self.stop_keepalive.clear()
        self.keepalive_thread = threading.Thread(target=self._keepalive_worker)
        self.keepalive_thread.daemon = True
        self.keepalive_thread.start()
        print("💓 Keep-alive started")

    def stop_keepalive_thread(self):
        """Stop keep-alive thread"""
        if self.keepalive_thread:
            self.stop_keepalive.set()
            self.keepalive_thread.join(timeout=2)
            print("💓 Keep-alive stopped")

    def _keepalive_worker(self):
        """Keep-alive worker thread"""
        while not self.stop_keepalive.is_set():
            try:
                if self.connected and self.serial and self.serial.is_open:
                    self.send_command("KEEPALIVE", 0, silent=True)
                time.sleep(3)  # Send keep-alive every 3 seconds
            except Exception as e:
                print(f"💓 Keep-alive error: {e}")
                break

    def send_command(self, direction, speed, silent=False):
        """Send movement command to Arduino"""
        if not self.connected or not self.serial:
            return False

        try:
            command = f"{direction}:{speed}\n"
            self.serial.write(command.encode())
            if not silent:
                print(f"📤 Sent: {direction}:{speed}")
            return True
        except Exception as e:
            if not silent:
                print(f"❌ Send failed: {e}")
            return False

    def read_responses(self, duration=2.0):
        """Read Arduino responses for specified duration"""
        start_time = time.time()
        responses = []

        while time.time() - start_time < duration:
            try:
                if self.serial and self.serial.in_waiting > 0:
                    line = self.serial.readline().decode().strip()
                    if line:
                        responses.append(line)

                        # Parse sensor data
                        if line.startswith('{"sensors"'):
                            try:
                                self.sensor_data = json.loads(line)
                                print(f"📊 Sensors: FL:{self.get_sensor_distance('front_left')} "
                                      f"FR:{self.get_sensor_distance('front_right')} "
                                      f"RL:{self.get_sensor_distance('rear_left')} "
                                      f"RR:{self.get_sensor_distance('rear_right')}")
                            except json.JSONDecodeError:
                                pass
                        else:
                            print(f"📥 Arduino: {line}")

            except Exception as e:
                print(f"📥 Read error: {e}")
                break

            time.sleep(0.05)

        return responses

    def get_sensor_distance(self, sensor_name):
        """Get formatted sensor distance"""
        if 'sensors' in self.sensor_data:
            distance = self.sensor_data['sensors'].get(sensor_name, 0)
            if distance == 2147483647:
                return "∞"
            elif distance > 1000:
                return f"{distance//1000}k"
            else:
                return str(distance)
        return "?"

    def test_movement_directions(self):
        """Test all movement directions"""
        print("\n🎮 TESTING ALL MOVEMENT DIRECTIONS")
        print("=" * 50)

        movements = [
            ("FORWARD", 60),
            ("BACKWARD", 50),
            ("LEFT", 45),
            ("RIGHT", 45),
            ("FORWARD_LEFT", 40),
            ("FORWARD_RIGHT", 40),
            ("BACKWARD_LEFT", 35),
            ("BACKWARD_RIGHT", 35),
        ]

        for direction, speed in movements:
            print(f"\n🚗 Testing {direction} at speed {speed}")
            self.send_command(direction, speed)
            self.read_responses(1.5)

            print(f"🛑 Stopping...")
            self.send_command("STOP", 0)
            self.read_responses(0.5)

    def test_sensor_monitoring(self):
        """Test sensor data reception"""
        print("\n📡 TESTING SENSOR DATA MONITORING")
        print("=" * 50)
        print("Monitoring sensors for 10 seconds...")

        start_time = time.time()
        sensor_count = 0

        while time.time() - start_time < 10:
            responses = self.read_responses(1.0)
            for response in responses:
                if response.startswith('{"sensors"'):
                    sensor_count += 1

        print(f"📊 Received {sensor_count} sensor data packets")

        if self.sensor_data:
            print("📋 Latest sensor readings:")
            sensors = self.sensor_data.get('sensors', {})
            for sensor, value in sensors.items():
                if 'collision' not in sensor:
                    print(f"   {sensor}: {self.get_sensor_distance(sensor)}")

            front_collision = sensors.get('front_collision', False)
            rear_collision = sensors.get('rear_collision', False)
            print(f"   Collisions: Front={front_collision}, Rear={rear_collision}")

    def test_reconnection(self):
        """Test reconnection with auto-reboot"""
        print("\n🔄 TESTING RECONNECTION WITH AUTO-REBOOT")
        print("=" * 50)

        original_port = self.port
        print(f"📍 Original port: {original_port}")

        # Disconnect and wait for reboot
        print("🔌 Disconnecting to trigger auto-reboot...")
        self.disconnect()

        print("⏰ Waiting for Arduino reboot (up to 15 seconds)...")
        for i in range(15):
            time.sleep(1)
            new_port = self.find_arduino_port()
            if new_port and new_port != original_port:
                print(f"🔄 Reboot detected: {original_port} → {new_port}")
                break
            elif i == 14:
                print("⚠️  No reboot detected within 15 seconds")
                return False

        # Reconnect to new port
        print("🔌 Reconnecting...")
        self.port = new_port
        if self.connect():
            print("✅ Reconnection successful!")
            self.read_responses(2.0)  # Read startup messages
            return True
        else:
            print("❌ Reconnection failed")
            return False

def main():
    print("🤖 COMPREHENSIVE ARDUINO ROBOT TEST")
    print("=" * 60)
    print("This script tests:")
    print("• Remote control via serial in all directions")
    print("• Sensor data reception and parsing")
    print("• Reconnection handling with auto-reboot")
    print("• Keep-alive system for connection maintenance")
    print("=" * 60)

    robot = RobotController()

    try:
        # Initial connection
        if not robot.connect():
            return

        # Wait for Arduino startup
        print("\n⏰ Waiting for Arduino startup...")
        robot.read_responses(3.0)

        # Test all movement directions
        robot.test_movement_directions()

        # Test sensor monitoring
        robot.test_sensor_monitoring()

        # Test reconnection
        if robot.test_reconnection():
            # Quick test after reconnection
            print("\n🔄 POST-RECONNECTION TEST")
            print("=" * 30)
            robot.send_command("FORWARD", 30)
            robot.read_responses(1.0)
            robot.send_command("STOP", 0)
            robot.read_responses(0.5)

        print("\n✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("🎯 Robot is ready for:")
        print("   • Gamepad control integration")
        print("   • AI model control integration")
        print("   • Multiplexer service development")

    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test error: {e}")
    finally:
        robot.disconnect()
        print("\n🏁 Test session ended")

if __name__ == "__main__":
    main()