#!/usr/bin/env python3
import serial
import json
import time

# Adjust the port as needed (check with ls /dev/tty* or Device Manager on Windows)
SERIAL_PORT = '/dev/ttyACM0'  # or 'COM3' on Windows
BAUD_RATE = 115200

def test_robot_control():
    try:
        # Open serial connection
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud")

        # Wait for Arduino to initialize
        time.sleep(2)

        # Test commands
        commands = [
            "FORWARD:60",
            "STOP:0",
            "BACKWARD:50",
            "STOP:0",
            "LEFT:40",
            "STOP:0",
            "RIGHT:40",
            "STOP:0"
        ]

        for cmd in commands:
            print(f"Sending: {cmd}")
            ser.write((cmd + '\n').encode('utf-8'))  # Make sure to add \n
            time.sleep(1)  # Wait between commands

            # Read any responses/debug output
            while ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    print(f"Arduino: {line}")

        print("Test completed")
        ser.close()

    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except KeyboardInterrupt:
        print("Test interrupted")
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    test_robot_control()