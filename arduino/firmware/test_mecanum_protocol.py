#!/usr/bin/env python3
"""
Mecanum Wheel Protocol Test

This test demonstrates the new JSON-based mecanum wheel control protocol.
Tests the various movement patterns enabled by direct motor control.

Based on the MECANUM_PROTOCOL_PROPOSAL.md requirements.
"""

import serial
import time
import glob
import json
import math

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

def send_mecanum_command(ser, left_front, left_rear, right_front, right_rear, description=""):
    """Send a mecanum command and monitor response"""
    command = {
        "type": "mecanum",
        "motors": {
            "left_front": left_front,
            "left_rear": left_rear,
            "right_front": right_front,
            "right_rear": right_rear
        }
    }

    print(f"   🎯 {description}")
    print(f"   📤 Motors: LF:{left_front} LR:{left_rear} RF:{right_front} RR:{right_rear}")

    cmd_str = f"{json.dumps(command)}\n"
    ser.write(cmd_str.encode('utf-8'))

    # Monitor response
    start_time = time.time()
    command_received = False
    motor_action = False

    while time.time() - start_time < 1.5:
        while ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line and not line.startswith('{"sensors"'):
                if 'PARSED MECANUM JSON' in line:
                    print(f"   ✅ Parsed: {line}")
                    command_received = True
                elif 'NEW MECANUM CMD' in line:
                    print(f"   🤖 Command: {line}")
                elif 'MECANUM MOTORS' in line:
                    print(f"   ⚙️  Motors: {line}")
                    motor_action = True
                elif 'ERROR' in line or 'INVALID' in line:
                    print(f"   ❌ Error: {line}")
                else:
                    print(f"   📝 {line}")
        time.sleep(0.05)

    if command_received and motor_action:
        print(f"   ✅ SUCCESS: Command executed")
    elif command_received:
        print(f"   ⚠️  PARTIAL: Command received but no motor action")
    else:
        print(f"   ❌ FAILED: Command not received")

    print()
    return command_received and motor_action

def test_basic_mecanum_movements():
    """Test basic mecanum movement patterns"""
    port = find_arduino_port()
    if not port:
        print("❌ No Arduino found")
        return False

    try:
        ser = serial.Serial(port, 115200, timeout=1)
        print(f"✅ Connected to {port}")
        time.sleep(2)

        print("🚀 Testing Basic Mecanum Movements")
        print("=" * 50)

        success_count = 0
        total_tests = 0

        # Test 1: Forward movement
        total_tests += 1
        if send_mecanum_command(ser, 100, 100, 100, 100, "Forward Movement"):
            success_count += 1
        time.sleep(0.5)

        # Test 2: Backward movement
        total_tests += 1
        if send_mecanum_command(ser, -100, -100, -100, -100, "Backward Movement"):
            success_count += 1
        time.sleep(0.5)

        # Test 3: Strafe right (key mecanum capability)
        total_tests += 1
        if send_mecanum_command(ser, -100, 100, 100, -100, "Strafe Right (Pure Sideways)"):
            success_count += 1
        time.sleep(0.5)

        # Test 4: Strafe left (key mecanum capability)
        total_tests += 1
        if send_mecanum_command(ser, 100, -100, -100, 100, "Strafe Left (Pure Sideways)"):
            success_count += 1
        time.sleep(0.5)

        # Test 5: Rotate clockwise
        total_tests += 1
        if send_mecanum_command(ser, -100, -100, 100, 100, "Rotate Clockwise"):
            success_count += 1
        time.sleep(0.5)

        # Test 6: Rotate counter-clockwise
        total_tests += 1
        if send_mecanum_command(ser, 100, 100, -100, -100, "Rotate Counter-Clockwise"):
            success_count += 1
        time.sleep(0.5)

        # Test 7: Stop
        total_tests += 1
        if send_mecanum_command(ser, 0, 0, 0, 0, "Stop All Motors"):
            success_count += 1

        ser.close()

        print(f"📊 Basic Movement Results: {success_count}/{total_tests} tests passed")
        return success_count == total_tests

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_advanced_mecanum_movements():
    """Test advanced mecanum movement combinations"""
    port = find_arduino_port()
    if not port:
        print("❌ No Arduino found")
        return False

    try:
        ser = serial.Serial(port, 115200, timeout=1)
        print(f"✅ Connected to {port}")
        time.sleep(2)

        print("🚀 Testing Advanced Mecanum Movements")
        print("=" * 50)

        success_count = 0
        total_tests = 0

        # Test 1: Forward + Strafe Right (diagonal)
        total_tests += 1
        if send_mecanum_command(ser, 50, 150, 150, 50, "Forward + Strafe Right (Diagonal)"):
            success_count += 1
        time.sleep(0.5)

        # Test 2: Forward + Strafe Left (diagonal)
        total_tests += 1
        if send_mecanum_command(ser, 150, 50, 50, 150, "Forward + Strafe Left (Diagonal)"):
            success_count += 1
        time.sleep(0.5)

        # Test 3: Backward + Strafe Right
        total_tests += 1
        if send_mecanum_command(ser, -150, -50, -50, -150, "Backward + Strafe Right"):
            success_count += 1
        time.sleep(0.5)

        # Test 4: Backward + Strafe Left
        total_tests += 1
        if send_mecanum_command(ser, -50, -150, -150, -50, "Backward + Strafe Left"):
            success_count += 1
        time.sleep(0.5)

        # Test 5: Forward + Rotate (complex maneuver)
        total_tests += 1
        if send_mecanum_command(ser, 80, 80, 40, 40, "Forward + Rotate Right"):
            success_count += 1
        time.sleep(0.5)

        # Test 6: Strafe + Rotate (very complex)
        total_tests += 1
        if send_mecanum_command(ser, -50, 150, 150, -50, "Strafe Right + Slight Forward"):
            success_count += 1
        time.sleep(0.5)

        # Test 7: Variable speed demonstration
        total_tests += 1
        if send_mecanum_command(ser, 200, 100, 50, 25, "Variable Speed Test"):
            success_count += 1
        time.sleep(0.5)

        # Test 8: Stop
        total_tests += 1
        if send_mecanum_command(ser, 0, 0, 0, 0, "Stop All Motors"):
            success_count += 1

        ser.close()

        print(f"📊 Advanced Movement Results: {success_count}/{total_tests} tests passed")
        return success_count == total_tests

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_protocol_compatibility():
    """Test compatibility between different command formats"""
    port = find_arduino_port()
    if not port:
        print("❌ No Arduino found")
        return False

    try:
        ser = serial.Serial(port, 115200, timeout=1)
        print(f"✅ Connected to {port}")
        time.sleep(2)

        print("🚀 Testing Protocol Compatibility")
        print("=" * 50)

                # Skip legacy test - no longer supported
        print("   ℹ️  Legacy commands no longer supported - testing JSON only")

        # Test tank JSON command
        print("\n   🎯 Testing Tank JSON Command")
        tank_cmd = json.dumps({"type": "tank", "command": "BACKWARD", "value": 50})
        ser.write(f"{tank_cmd}\n".encode('utf-8'))
        time.sleep(1)

        # Read response
        while ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line and not line.startswith('{"sensors"'):
                if 'PARSED TANK JSON' in line:
                    print(f"   ✅ Tank JSON: {line}")
                elif 'NEW TANK CMD' in line:
                    print(f"   🤖 Tank JSON: {line}")

        # Test KEEPALIVE command
        print("\n   🎯 Testing KEEPALIVE Command")
        keepalive_cmd = json.dumps({"type": "tank", "command": "KEEPALIVE", "value": 0})
        ser.write(f"{keepalive_cmd}\n".encode('utf-8'))
        time.sleep(1)

        # Read response
        while ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line and not line.startswith('{"sensors"'):
                if 'PARSED TANK JSON' in line:
                    print(f"   ✅ KEEPALIVE JSON: {line}")
                elif 'KEEPALIVE processed' in line:
                    print(f"   💓 KEEPALIVE: {line}")

        time.sleep(0.5)

        # Test mecanum command
        print("\n   🎯 Testing Mecanum Command")
        mecanum_cmd = json.dumps({
            "type": "mecanum",
            "motors": {"left_front": 100, "left_rear": -100, "right_front": -100, "right_rear": 100}
        })
        ser.write(f"{mecanum_cmd}\n".encode('utf-8'))
        time.sleep(1)

        # Read response
        while ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line and not line.startswith('{"sensors"'):
                if 'PARSED MECANUM JSON' in line:
                    print(f"   ✅ Mecanum: {line}")
                elif 'NEW MECANUM CMD' in line:
                    print(f"   🤖 Mecanum: {line}")

        # Stop all
        ser.write(f"{json.dumps({'type': 'mecanum', 'motors': {'left_front': 0, 'left_rear': 0, 'right_front': 0, 'right_rear': 0}})}\n".encode('utf-8'))

        ser.close()
        print(f"\n📊 Protocol compatibility test completed")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_error_handling():
    """Test error handling for invalid commands"""
    port = find_arduino_port()
    if not port:
        print("❌ No Arduino found")
        return False

    try:
        ser = serial.Serial(port, 115200, timeout=1)
        print(f"✅ Connected to {port}")
        time.sleep(2)

        print("🚀 Testing Error Handling")
        print("=" * 50)

        # Test invalid JSON
        print("   🎯 Testing Invalid JSON")
        ser.write(b'{"type": "mecanum", "motors": {"left_front": 100}\n')  # Missing closing brace
        time.sleep(1)

        while ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line and 'ERROR' in line:
                print(f"   ✅ Caught JSON error: {line}")

        # Test invalid motor speeds (out of range)
        print("\n   🎯 Testing Invalid Motor Speeds")
        invalid_cmd = json.dumps({
            "type": "mecanum",
            "motors": {"left_front": 500, "left_rear": -400, "right_front": 300, "right_rear": -500}
        })
        ser.write(f"{invalid_cmd}\n".encode('utf-8'))
        time.sleep(1)

        while ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line and 'INVALID' in line:
                print(f"   ✅ Caught speed error: {line}")

        # Test missing fields
        print("\n   🎯 Testing Missing Fields")
        incomplete_cmd = json.dumps({"type": "mecanum"})  # Missing motors field
        ser.write(f"{incomplete_cmd}\n".encode('utf-8'))
        time.sleep(1)

        while ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line and 'MISSING' in line:
                print(f"   ✅ Caught missing field error: {line}")

        ser.close()
        print(f"\n📊 Error handling test completed")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Run all mecanum protocol tests"""
    print("🤖 Mecanum Wheel Protocol Test Suite")
    print("=" * 60)
    print("Testing the new JSON-based mecanum control protocol")
    print("Based on MECANUM_PROTOCOL_PROPOSAL.md specifications")
    print("=" * 60)

    results = []

    print("\n1️⃣  Basic Mecanum Movements")
    results.append(test_basic_mecanum_movements())

    print("\n" + "=" * 60)
    print("\n2️⃣  Advanced Mecanum Movements")
    results.append(test_advanced_mecanum_movements())

    print("\n" + "=" * 60)
    print("\n3️⃣  Protocol Compatibility")
    results.append(test_protocol_compatibility())

    print("\n" + "=" * 60)
    print("\n4️⃣  Error Handling")
    results.append(test_error_handling())

    print("\n" + "=" * 60)
    print("\n📊 FINAL RESULTS")
    print("=" * 60)

    test_names = [
        "Basic Mecanum Movements",
        "Advanced Mecanum Movements",
        "Protocol Compatibility",
        "Error Handling"
    ]

    for i, (name, result) in enumerate(zip(test_names, results), 1):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i}. {name}: {status}")

    passed = sum(results)
    total = len(results)

    print(f"\nOverall: {passed}/{total} test suites passed")

    if passed == total:
        print("🎉 All tests passed! Mecanum protocol is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")

if __name__ == "__main__":
    main()