#!/usr/bin/env python3
import serial
import time

SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 115200

def simple_lcd_test():
    """Simple test for LCD and basic functionality"""
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud")

        # Wait for Arduino to initialize
        time.sleep(3)

        print("\n=== STARTING SIMPLE TEST ===")
        print("1. Sending RESET command...")
        ser.write(b'RESET:0\n')
        time.sleep(2)

        print("2. Testing movement commands (1 second each)...")
        commands = [
            "FORWARD:40",
            "STOP:0",
            "BACKWARD:40",
            "STOP:0",
            "LEFT:30",
            "STOP:0"
        ]

        for cmd in commands:
            print(f"   Sending: {cmd}")
            ser.write((cmd + '\n').encode('utf-8'))
            time.sleep(1)  # 1 second per command

        print("3. Final RESET...")
        ser.write(b'RESET:0\n')
        time.sleep(1)

        print("4. Monitoring for 5 seconds (test joystick now)...")
        start_time = time.time()
        while time.time() - start_time < 5:
            while ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line and not line.startswith('{"sensors"'):
                    if 'LCD' in line:
                        print(f"📺 {line}")
                    elif 'JOYSTICK' in line:
                        print(f"🕹️  {line}")
                    elif 'RESET' in line:
                        print(f"🔄 {line}")
                    else:
                        print(f"🤖 {line}")
            time.sleep(0.1)

        print("\n=== TEST COMPLETED ===")
        print("Expected results:")
        print("- LCD should show different states")
        print("- Robot should move for each command")
        print("- Joystick should work after reset")
        print("- No stuck states")

        ser.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    simple_lcd_test()