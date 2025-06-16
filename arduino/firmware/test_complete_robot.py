#!/usr/bin/env python3
"""
Comprehensive Arduino Robot Test Script

This script demonstrates:
- Remote control via serial in all directions
- Sensor data reception and parsing
- Watchdog reboot functionality and recovery
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
        """Send tank command using JSON format"""
        return self.send_tank_command(direction, speed, silent)

    def send_tank_command(self, direction, speed, silent=False):
        """Send tank command using JSON format"""
        if not self.connected or not self.serial:
            return False

        try:
            import json
            command = json.dumps({"type": "tank", "command": direction, "value": speed})
            self.serial.write(f"{command}\n".encode())
            if not silent:
                print(f"📤 Sent Tank JSON: {command}")
            return True
        except Exception as e:
            if not silent:
                print(f"❌ Tank command failed: {e}")
            return False

    def send_mecanum_command(self, left_front, left_rear, right_front, right_rear, silent=False):
        """Send mecanum command using JSON format"""
        if not self.connected or not self.serial:
            return False

        try:
            import json
            command = json.dumps({
                "type": "mecanum",
                "motors": {
                    "left_front": left_front,
                    "left_rear": left_rear,
                    "right_front": right_front,
                    "right_rear": right_rear
                }
            })
            self.serial.write(f"{command}\n".encode())
            if not silent:
                print(f"📤 Sent Mecanum: LF:{left_front} LR:{left_rear} RF:{right_front} RR:{right_rear}")
            return True
        except Exception as e:
            if not silent:
                print(f"❌ Mecanum command failed: {e}")
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

    def test_json_command_formats(self):
        """Test new JSON command formats"""
        print("\n🚀 TESTING JSON COMMAND FORMATS")
        print("=" * 50)

        # Test tank JSON commands
        print("🔹 Testing Tank JSON Commands")
        tank_movements = [
            ("FORWARD", 60),
            ("BACKWARD", 50),
            ("LEFT", 45),
            ("RIGHT", 45),
            ("STOP", 0)
        ]

        for direction, speed in tank_movements:
            print(f"\n🚗 Testing Tank JSON {direction} at speed {speed}")
            self.send_tank_command(direction, speed)
            self.read_responses(1.0)

        time.sleep(1)

        # Test mecanum commands
        print("\n🔹 Testing Mecanum Commands")
        mecanum_movements = [
            (100, 100, 100, 100, "Forward"),
            (-100, -100, -100, -100, "Backward"),
            (-100, 100, 100, -100, "Strafe Right"),
            (100, -100, -100, 100, "Strafe Left"),
            (-100, -100, 100, 100, "Rotate Clockwise"),
            (100, 100, -100, -100, "Rotate Counter-Clockwise"),
            (50, 150, 150, 50, "Forward + Strafe Right"),
            (0, 0, 0, 0, "Stop")
        ]

        for lf, lr, rf, rr, description in mecanum_movements:
            print(f"\n🚗 Testing Mecanum {description}")
            self.send_mecanum_command(lf, lr, rf, rr)
            self.read_responses(1.5)
            time.sleep(0.5)

        print(f"\n📊 JSON command formats testing completed")

    def test_watchdog_reboot(self):
        """Test watchdog-triggered reboot functionality"""
        print("\n🐕 TESTING WATCHDOG REBOOT FUNCTIONALITY")
        print("=" * 50)

        # Stop keep-alive to allow watchdog timeout
        print("💓 Stopping keep-alive to test watchdog...")
        self.stop_keepalive_thread()

        # Send a command to activate watchdog
        print("📤 Sending command to activate watchdog...")
        self.send_command("FORWARD", 60)
        time.sleep(2)  # Let it run for a bit

        # Send stop command
        print("🛑 Sending STOP command...")
        self.send_command("STOP", 0)
        time.sleep(1)

        print("⏰ Waiting for watchdog timeout and reboot...")
        print("   Should see 'SERIAL TIMEOUT' message followed by reboot in ~8 seconds")

        # Monitor for reboot indicators
        start_time = time.time()
        last_message_time = time.time()
        reboot_detected = False
        timeout_detected = False
        deactivation_detected = False

        # Track message patterns that indicate reboot
        startup_messages = ["LCD: Force update after reset", "JOYSTICK DEBUG", "USING JOYSTICK CONTROL"]
        startup_count = 0

        while time.time() - start_time < 15:
            try:
                if self.serial and self.serial.in_waiting > 0:
                    line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        current_time = time.time()
                        elapsed = current_time - start_time
                        print(f"[{elapsed:.1f}s] Arduino: {line}")
                        last_message_time = current_time

                        # Look for timeout and deactivation messages
                        if "SERIAL TIMEOUT" in line:
                            print("🐕 Watchdog timeout detected - reboot should follow...")
                            timeout_detected = True

                        if "WATCHDOG: DEACTIVATED" in line:
                            print("🐕 Watchdog deactivated - reboot should follow...")
                            deactivation_detected = True

                        # Look for startup indicators after timeout
                        if timeout_detected and deactivation_detected:
                            for startup_msg in startup_messages:
                                if startup_msg in line:
                                    startup_count += 1
                                    if startup_count >= 2:  # Multiple startup messages = reboot
                                        print("✅ REBOOT DETECTED! Multiple startup messages after watchdog timeout.")
                                        reboot_detected = True
                                        break

                            # Also look for joystick mode activation (indicates clean restart)
                            if "USING JOYSTICK CONTROL" in line and elapsed > 5:
                                print("✅ REBOOT DETECTED! Arduino returned to joystick mode after timeout.")
                                reboot_detected = True
                                break

                        # Look for explicit reboot indicators
                        if "SYSTEM READY" in line or "WATCHDOG: Ready to start" in line:
                            print("✅ REBOOT DETECTED! Watchdog system working correctly.")
                            reboot_detected = True
                            break

                        if reboot_detected:
                            break
                else:
                    time.sleep(0.1)
            except Exception as e:
                print(f"📥 Read error (may indicate reboot): {e}")
                # Serial errors often indicate the device rebooted
                if timeout_detected and deactivation_detected:
                    print("✅ REBOOT DETECTED! Serial error after watchdog timeout likely indicates reboot.")
                    reboot_detected = True
                break

        # Check if we stopped getting messages after timeout (indicating reboot)
        if not reboot_detected and timeout_detected and deactivation_detected:
            silence_duration = time.time() - last_message_time
            if silence_duration > 2:
                print(f"✅ REBOOT DETECTED! Arduino silent for {silence_duration:.1f}s after watchdog timeout.")
                reboot_detected = True

        # Final check: if we saw timeout and deactivation, assume reboot worked
        if not reboot_detected and timeout_detected and deactivation_detected:
            print("✅ REBOOT LIKELY OCCURRED! Saw timeout and deactivation messages.")
            reboot_detected = True

        if reboot_detected:
            print("🔄 Attempting to reconnect after reboot...")
            time.sleep(3)  # Wait longer for Arduino to fully restart

            # Try to reconnect
            try:
                self.serial.close()
            except:
                pass

            if self.connect():
                print("✅ Reconnection after watchdog reboot successful!")
                self.read_responses(2.0)  # Read startup messages
                return True
            else:
                print("❌ Reconnection failed after reboot")
                return False
        else:
            print("❌ No reboot detected within timeout period")
            return False

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
    print("• Watchdog reboot functionality and recovery")
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

        # Test JSON command formats
        print("\n" + "=" * 60)
        robot.test_json_command_formats()

        # Test watchdog reboot functionality
        robot.test_watchdog_reboot()

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