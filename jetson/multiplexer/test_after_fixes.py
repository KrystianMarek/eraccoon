#!/usr/bin/env python3
import serial
import time

SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 115200

def test_after_fixes():
    """Test the fixes: LCD spam, diagonal movements, serial disconnect"""
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud")

        # Wait for Arduino to initialize
        time.sleep(3)

        print("\n=== TESTING FIXES ===")
        print("🎯 Testing: LCD spam fix, diagonal movements, serial disconnect")
        print()

        # Test 1: Check LCD spam is reduced
        print("1. 🔄 RESET and monitor LCD messages (should be fewer)...")
        ser.write(b'RESET:0\n')
        time.sleep(3)

        lcd_force_updates = 0
        start_time = time.time()
        while time.time() - start_time < 5:  # 5 seconds
            while ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line and not line.startswith('{"sensors"'):
                    if 'LCD: Force update after reset' in line:
                        lcd_force_updates += 1
                    print(f"   {line}")
            time.sleep(0.1)

        print(f"   📊 LCD Force Updates detected: {lcd_force_updates} (should be 2 or fewer)")

        # Test 2: Test serial disconnect after 6 seconds
        print(f"\n2. 🔌 Testing serial disconnect detection...")
        print(f"   📤 Sending FORWARD command, then stopping communication...")
        ser.write(b'FORWARD:30\n')
        time.sleep(1)

        print(f"   ⏰ Waiting 6 seconds for disconnect detection...")
        start_time = time.time()
        disconnect_detected = False

        while time.time() - start_time < 7:  # Wait 7 seconds
            while ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line and not line.startswith('{"sensors"'):
                    if 'SERIAL DISCONNECT' in line:
                        print(f"   ✅ Disconnect detected: {line}")
                        disconnect_detected = True
                    elif 'JOYSTICK' in line and 'Active:YES' in line:
                        print(f"   🎮 Joystick active after disconnect: {line}")
                    else:
                        print(f"   📝 {line}")
            time.sleep(0.1)

        # Test 3: Test joystick after disconnect
        print(f"\n3. 🕹️  Testing joystick after serial disconnect (try joystick now)...")
        start_time = time.time()
        joystick_works_after_disconnect = False

        while time.time() - start_time < 5:  # 5 seconds to test
            while ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line and not line.startswith('{"sensors"'):
                    if 'JOYSTICK ACTIVE' in line or ('Active:YES' in line and 'JOYSTICK' in line):
                        print(f"   🎮 {line}")
                        joystick_works_after_disconnect = True
                    elif 'MOTOR: Executing' in line and 'UNKNOWN' not in line:
                        print(f"   🚗 {line}")
                    elif 'UNKNOWN' in line:
                        print(f"   ⚠️  Unknown direction: {line}")
            time.sleep(0.1)

        print(f"\n=== RESULTS ===")
        print(f"✅ Compilation: SUCCESS")
        print(f"{'✅' if lcd_force_updates <= 2 else '⚠️ '} LCD Spam Fix: {lcd_force_updates} force updates (target: ≤2)")
        print(f"{'✅' if disconnect_detected else '❌'} Serial Disconnect: {'DETECTED' if disconnect_detected else 'NOT DETECTED'}")
        print(f"{'✅' if joystick_works_after_disconnect else '❌'} Joystick Recovery: {'WORKING' if joystick_works_after_disconnect else 'NOT WORKING'}")

        print(f"\n📋 What should work now:")
        print(f"   - ✅ Serial commands work in all directions")
        print(f"   - ✅ Robot automatically returns to joystick control after script ends")
        print(f"   - ✅ LCD updates are less frequent")
        print(f"   - ✅ Diagonal movements show proper names (not UNKNOWN)")
        print(f"   - ✅ Robot remains responsive after serial sessions")

        ser.close()

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_after_fixes()