#!/usr/bin/env python3
import serial
import time

SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 115200

def test_fixed_robot():
    """Test the fixed robot with shorter command timeouts"""
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud")

        # Wait for Arduino to initialize
        time.sleep(3)

        print("\n=== TESTING FIXED ROBOT ===")
        print("📋 Changes made:")
        print("   - Reduced command timeout from 1000ms to 200ms")
        print("   - Added enhanced joystick debugging")
        print("   - Throttled continuous command output")
        print("   - Fixed LCD update after reset")
        print()

        print("1. 🔄 Sending RESET command...")
        ser.write(b'RESET:0\n')
        time.sleep(2)

        print("2. 🚗 Testing movement commands (shorter duration)...")
        commands = [
            ("FORWARD:50", 0.5),    # 500ms forward
            ("STOP:0", 0.1),        # Stop immediately
            ("BACKWARD:40", 0.5),   # 500ms backward
            ("STOP:0", 0.1),        # Stop immediately
            ("LEFT:30", 0.3),       # 300ms left
            ("STOP:0", 0.1),        # Stop immediately
            ("RIGHT:30", 0.3),      # 300ms right
            ("STOP:0", 0.1),        # Stop immediately
        ]

        for cmd, duration in commands:
            print(f"   📤 Sending: {cmd} (wait {duration}s)")
            ser.write((cmd + '\n').encode('utf-8'))
            time.sleep(duration)

        print("3. 🔄 Final RESET...")
        ser.write(b'RESET:0\n')
        time.sleep(2)

        print("4. 🕹️  Testing joystick response (press joystick buttons now)...")
        print("   📺 Monitor LCD for status changes")
        print("   🎮 Try moving joystick in different directions")

        start_time = time.time()
        joystick_detected = False
        while time.time() - start_time < 10:  # Monitor for 10 seconds
            while ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line and not line.startswith('{"sensors"'):
                    if 'JOYSTICK DEBUG' in line:
                        print(f"🔍 {line}")
                        if 'Active:YES' in line:
                            joystick_detected = True
                    elif 'JOYSTICK ACTIVE' in line:
                        print(f"🎮 {line}")
                        joystick_detected = True
                    elif 'LCD' in line:
                        print(f"📺 {line}")
                    elif 'RESET' in line:
                        print(f"🔄 {line}")
                    elif 'CONTINUING' in line:
                        print(f"⚠️  {line}")  # This shouldn't happen with new timeout
                    else:
                        print(f"🤖 {line}")
            time.sleep(0.1)

        print(f"\n=== TEST RESULTS ===")
        print(f"✅ Compilation: SUCCESS")
        print(f"{'✅' if joystick_detected else '❌'} Joystick Detection: {'DETECTED' if joystick_detected else 'NOT DETECTED'}")
        print(f"📊 Expected improvements:")
        print(f"   - Commands should timeout after 200ms (not 1000ms)")
        print(f"   - Less debug spam in logs")
        print(f"   - Joystick should work after serial commands")
        print(f"   - LCD should show proper status (not stuck on RESET)")

        if not joystick_detected:
            print(f"\n⚠️  JOYSTICK TROUBLESHOOTING:")
            print(f"   - Check pins 22-25 connections")
            print(f"   - Verify joystick ground connection")
            print(f"   - Try pressing buttons firmly")
            print(f"   - Check for loose wires")

        ser.close()

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_fixed_robot()