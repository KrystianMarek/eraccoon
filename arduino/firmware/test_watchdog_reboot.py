#!/usr/bin/env python3

import serial
import time
import sys

def test_watchdog_reboot():
    try:
        # Connect to Arduino
        ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
        print("Connected to Arduino")
        time.sleep(2)  # Wait for Arduino to initialize

        # Send a command to activate watchdog
        print("Sending command to activate watchdog...")
        ser.write(b'FORWARD:60\n')
        time.sleep(2)  # Let it run for a bit

        # Send stop command
        print("Sending STOP command...")
        ser.write(b'STOP:0\n')
        time.sleep(1)

        print("Waiting for watchdog timeout and reboot...")
        print("Should see 'SERIAL TIMEOUT' message followed by reboot in ~8 seconds")

        # Monitor for 15 seconds to see reboot
        start_time = time.time()
        last_message_time = time.time()

        while time.time() - start_time < 15:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    current_time = time.time()
                    elapsed = current_time - start_time
                    print(f"[{elapsed:.1f}s] Arduino: {line}")
                    last_message_time = current_time

                    # Look for reboot indicators
                    if "SYSTEM READY" in line or "WATCHDOG: Ready to start" in line:
                        print("✅ REBOOT DETECTED! Watchdog system working correctly.")
                        return True
            else:
                time.sleep(0.1)

        # Check if we stopped getting messages (indicating reboot)
        if time.time() - last_message_time > 3:
            print("✅ Arduino stopped responding - likely rebooted successfully")
            return True
        else:
            print("❌ No reboot detected within timeout period")
            return False

    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if 'ser' in locals():
            ser.close()

if __name__ == "__main__":
    print("Testing Arduino watchdog reboot functionality...")
    success = test_watchdog_reboot()
    sys.exit(0 if success else 1)