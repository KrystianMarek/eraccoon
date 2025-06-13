#!/usr/bin/env python3
import serial
import time

SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 115200

def recover_robot():
    """Try to recover an unresponsive robot"""
    print("🚑 ROBOT RECOVERY TOOL")
    print("=" * 30)

    try:
        print("1. 📡 Attempting connection...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=3)
        print("   ✅ Serial connected")

        # Try multiple recovery methods
        recovery_methods = [
            ("RESET:0\n", "Basic reset"),
            ("STOP:0\n", "Emergency stop"),
            ("\n", "Newline wake-up"),
            ("RESET:0\n", "Second reset attempt")
        ]

        for i, (cmd, desc) in enumerate(recovery_methods, 1):
            print(f"\n{i+1}. 🔧 Trying: {desc}")
            ser.write(cmd.encode('utf-8'))
            time.sleep(2)

            # Check for response
            response_seen = False
            start_time = time.time()
            while time.time() - start_time < 3:
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        print(f"   📨 {line}")
                        response_seen = True
                        if "RESET" in line or "SYSTEM READY" in line:
                            print("   ✅ Recovery successful!")
                            break
                time.sleep(0.1)

            if response_seen:
                break

        if not response_seen:
            print("\n❌ Robot not responding to recovery attempts")
            print("💡 Try:")
            print("   - Power cycle the Arduino")
            print("   - Check USB connection")
            print("   - Re-upload firmware")
        else:
            print("\n✅ Robot appears to be responding")
            print("🎮 Try using joystick or running test scripts")

        ser.close()

    except Exception as e:
        print(f"❌ Recovery failed: {e}")
        print("💡 Arduino may need physical reset")

if __name__ == "__main__":
    recover_robot()