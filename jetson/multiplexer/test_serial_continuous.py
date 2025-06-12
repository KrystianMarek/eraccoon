#!/usr/bin/env python3
import serial
import json
import time
import threading

# Adjust the port as needed
SERIAL_PORT = '/dev/ttyACM0'  # or 'COM3' on Windows
BAUD_RATE = 115200

def continuous_movement_test():
    try:
        # Open serial connection
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud")

        # Wait for Arduino to initialize
        time.sleep(2)

        # Test continuous movement
        movements = [
            ("FORWARD", 60, 3),    # Forward for 3 seconds
            ("STOP", 0, 1),        # Stop for 1 second
            ("BACKWARD", 50, 2),   # Backward for 2 seconds
            ("STOP", 0, 1),        # Stop for 1 second
            ("LEFT", 40, 2),       # Left for 2 seconds
            ("STOP", 0, 1),        # Stop for 1 second
            ("RIGHT", 40, 2),      # Right for 2 seconds
            ("STOP", 0, 1),        # Stop for 1 second
        ]

        for direction, speed, duration in movements:
            print(f"\n=== {direction} at speed {speed} for {duration}s ===")

            # Send command continuously during the duration
            start_time = time.time()
            while time.time() - start_time < duration:
                command = f"{direction}:{speed}"
                ser.write((command + '\n').encode('utf-8'))
                time.sleep(0.05)  # Send every 50ms (faster than 100ms timeout)

                # Read any debug messages
                while ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line and not line.startswith('{"sensors"'):
                        print(f"Arduino: {line}")

        print("\nSending final STOP command...")
        ser.write(b'STOP:0\n')
        time.sleep(1)

        print("Test completed")
        ser.close()

    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except KeyboardInterrupt:
        print("\nTest interrupted")
        if 'ser' in locals() and ser.is_open:
            ser.write(b'STOP:0\n')  # Emergency stop
            ser.close()

def single_command_test():
    """Test with single commands (should work with new persistence system)"""
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud")
        time.sleep(2)

        commands = [
            ("FORWARD:60", 2),
            ("STOP:0", 1),
            ("BACKWARD:50", 2),
            ("STOP:0", 1),
        ]

        for cmd, wait_time in commands:
            print(f"Sending: {cmd}")
            ser.write((cmd + '\n').encode('utf-8'))
            time.sleep(wait_time)

            # Read responses
            while ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line and not line.startswith('{"sensors"'):
                    print(f"Arduino: {line}")

        ser.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Choose test mode:")
    print("1. Continuous commands (recommended)")
    print("2. Single commands (test persistence)")

    choice = input("Enter choice (1 or 2): ").strip()

    if choice == "1":
        continuous_movement_test()
    elif choice == "2":
        single_command_test()
    else:
        print("Invalid choice")