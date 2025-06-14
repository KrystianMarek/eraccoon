#!/usr/bin/env python3
"""
Arduino Robot Serial Control Test

Tests JSON-based motor commands:
- Tank JSON format: {"type": "tank", "command": "FORWARD", "value": 60}
- Mecanum JSON format: {"type": "mecanum", "motors": {"left_front": 100, ...}}
"""

import serial
import time
import glob
import json

def find_arduino_port():
    """Find available Arduino port"""
    ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*') + glob.glob('COM*')
    for port in sorted(ports):
        try:
            test_ser = serial.Serial(port, 115200, timeout=1)
            test_ser.close()
            return port
        except:
            continue
    return None

def test_serial_control():
    """Test serial control with JSON formats"""
    port = find_arduino_port()
    if not port:
        print("❌ No Arduino found")
        return

    try:
        # Connect to Arduino
        ser = serial.Serial(port, 115200, timeout=1)
        print(f"✅ Connected to {port}")

        # Wait for Arduino to initialize
        time.sleep(2)
        print("🚀 Starting motor control tests\n")

        # Test movements with JSON formats only
        movements = [
            # Tank JSON format tests
            ("TANK_JSON", {"type": "tank", "command": "FORWARD", "value": 60}, "Forward movement (tank JSON)"),
            ("TANK_JSON", {"type": "tank", "command": "BACKWARD", "value": 50}, "Backward movement (tank JSON)"),
            ("TANK_JSON", {"type": "tank", "command": "LEFT", "value": 45}, "Left turn (tank JSON)"),
            ("TANK_JSON", {"type": "tank", "command": "RIGHT", "value": 45}, "Right turn (tank JSON)"),
            ("TANK_JSON", {"type": "tank", "command": "FORWARD_LEFT", "value": 40}, "Forward-left diagonal (tank JSON)"),
            ("TANK_JSON", {"type": "tank", "command": "FORWARD_RIGHT", "value": 40}, "Forward-right diagonal (tank JSON)"),
            ("TANK_JSON", {"type": "tank", "command": "BACKWARD_LEFT", "value": 35}, "Backward-left diagonal (tank JSON)"),
            ("TANK_JSON", {"type": "tank", "command": "BACKWARD_RIGHT", "value": 35}, "Backward-right diagonal (tank JSON)"),
            ("TANK_JSON", {"type": "tank", "command": "KEEPALIVE", "value": 0}, "Keep-alive command (tank JSON)"),
            ("TANK_JSON", {"type": "tank", "command": "STOP", "value": 0}, "Stop command (tank JSON)"),
        ]

        for cmd_type, command, description in movements:
            print(f"\n   🎯 Testing {description}")
            print(f"   📤 Sending command...")

            # Send JSON command
            cmd_str = f"{json.dumps(command)}\n"
            ser.write(cmd_str.encode('utf-8'))
            print(f"   📝 Sent: {json.dumps(command)}")

            # Monitor for 2 seconds to see command execution
            start_time = time.time()
            command_seen = False
            motor_action_seen = False

            while time.time() - start_time < 2.0:  # Watch for 2 seconds
                while ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line and not line.startswith('{"sensors"'):
                        if 'NEW TANK CMD' in line:
                            print(f"   ✅ Command received: {line}")
                            command_seen = True
                        elif 'MOTOR: Executing' in line:
                            print(f"   🚗 Motor action: {line}")
                            motor_action_seen = True
                        elif 'KEEPALIVE processed' in line:
                            print(f"   💓 Keep-alive processed: {line}")
                            motor_action_seen = True  # Count keepalive as successful action
                        elif 'CONTINUING' in line:
                            print(f"   ⏳ Continuing: {line}")
                        elif 'EXPIRED' in line:
                            print(f"   ⏰ Expired: {line}")
                        else:
                            print(f"   📝 {line}")
                time.sleep(0.1)

            # Send explicit STOP (unless this is already a STOP or KEEPALIVE command)
            if command.get("command") not in ["STOP", "KEEPALIVE"]:
                print(f"   🛑 Sending STOP command...")
                stop_cmd = json.dumps({"type": "tank", "command": "STOP", "value": 0})
                ser.write(f"{stop_cmd}\n".encode('utf-8'))
                time.sleep(0.5)  # Brief pause after stop

            # Check results
            if command_seen and motor_action_seen:
                print(f"   ✅ {description}: SUCCESS")
            elif command_seen:
                print(f"   ⚠️  {description}: RECEIVED but no motor action seen")
            else:
                print(f"   ❌ {description}: FAILED - not received")

        print(f"\n🎉 All movement tests completed!")
        ser.close()

    except Exception as e:
        print(f"❌ Test failed: {e}")
        if 'ser' in locals() and ser.is_open:
            ser.close()

def test_mecanum_control():
    """Test mecanum wheel direct motor control"""
    port = find_arduino_port()
    if not port:
        print("❌ No Arduino found")
        return

    try:
        # Connect to Arduino
        ser = serial.Serial(port, 115200, timeout=1)
        print(f"✅ Connected to {port}")

        # Wait for Arduino to initialize
        time.sleep(2)
        print("🚀 Starting mecanum control tests\n")

        # Test mecanum movements based on the protocol proposal
        mecanum_movements = [
            # Pure movements
            ({"type": "mecanum", "motors": {"left_front": 100, "left_rear": 100, "right_front": 100, "right_rear": 100}}, "Forward movement"),
            ({"type": "mecanum", "motors": {"left_front": -100, "left_rear": -100, "right_front": -100, "right_rear": -100}}, "Backward movement"),
            ({"type": "mecanum", "motors": {"left_front": -100, "left_rear": 100, "right_front": 100, "right_rear": -100}}, "Strafe right"),
            ({"type": "mecanum", "motors": {"left_front": 100, "left_rear": -100, "right_front": -100, "right_rear": 100}}, "Strafe left"),
            ({"type": "mecanum", "motors": {"left_front": -100, "left_rear": -100, "right_front": 100, "right_rear": 100}}, "Rotate clockwise"),
            ({"type": "mecanum", "motors": {"left_front": 100, "left_rear": 100, "right_front": -100, "right_rear": -100}}, "Rotate counter-clockwise"),

            # Complex movements
            ({"type": "mecanum", "motors": {"left_front": 50, "left_rear": 150, "right_front": 150, "right_rear": 50}}, "Forward + strafe right"),
            ({"type": "mecanum", "motors": {"left_front": 150, "left_rear": 50, "right_front": 50, "right_rear": 150}}, "Forward + strafe left"),
            ({"type": "mecanum", "motors": {"left_front": 80, "left_rear": 80, "right_front": -40, "right_rear": -40}}, "Forward + rotate"),

            # Stop command
            ({"type": "mecanum", "motors": {"left_front": 0, "left_rear": 0, "right_front": 0, "right_rear": 0}}, "Stop all motors"),
        ]

        for command, description in mecanum_movements:
            print(f"\n   🎯 Testing {description}")
            cmd_str = f"{json.dumps(command)}\n"
            ser.write(cmd_str.encode('utf-8'))
            print(f"   📝 Sent: {json.dumps(command)}")

            # Monitor for 2 seconds to see command execution
            start_time = time.time()
            command_seen = False
            motor_action_seen = False

            while time.time() - start_time < 2.0:  # Watch for 2 seconds
                while ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line and not line.startswith('{"sensors"'):
                        if 'NEW MECANUM CMD' in line:
                            print(f"   ✅ Command received: {line}")
                            command_seen = True
                        elif 'MECANUM MOTORS' in line:
                            print(f"   🚗 Motor action: {line}")
                            motor_action_seen = True
                        elif 'CONTINUING MECANUM' in line:
                            print(f"   ⏳ Continuing: {line}")
                        elif 'EXPIRED' in line:
                            print(f"   ⏰ Expired: {line}")
                        else:
                            print(f"   📝 {line}")
                time.sleep(0.1)

            # Brief pause between movements
            time.sleep(0.5)

            # Check results
            if command_seen and motor_action_seen:
                print(f"   ✅ {description}: SUCCESS")
            elif command_seen:
                print(f"   ⚠️  {description}: RECEIVED but no motor action seen")
            else:
                print(f"   ❌ {description}: FAILED - not received")

        print(f"\n🎉 All mecanum tests completed!")
        ser.close()

    except Exception as e:
        print(f"❌ Test failed: {e}")
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    print("🤖 Arduino Robot Serial Control Test")
    print("=" * 50)

    print("\n1️⃣  Testing tank JSON commands...")
    test_serial_control()

    print("\n" + "=" * 50)
    print("\n2️⃣  Testing mecanum wheel control...")
    test_mecanum_control()

    print("\n" + "=" * 50)
    print("✅ All tests completed!")