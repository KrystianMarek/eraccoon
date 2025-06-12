#!/usr/bin/env python3
import serial
import time

SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 115200

def monitor_robot():
    """Monitor robot debug output and allow manual commands"""
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud")
        print("\nRobot Debug Monitor")
        print("Commands: f=forward, b=backward, l=left, r=right, s=stop, reset=reset, q=quit")
        print("Or type full command like 'FORWARD:60'")
        print("-" * 50)

        # Non-blocking input setup
        import sys
        import select

        while True:
            # Check for user input (non-blocking)
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                user_input = input().strip().lower()

                if user_input == 'q':
                    print("Sending STOP and exiting...")
                    ser.write(b'STOP:0\n')
                    break
                elif user_input == 'f':
                    ser.write(b'FORWARD:60\n')
                    print("Sent: FORWARD:60")
                elif user_input == 'b':
                    ser.write(b'BACKWARD:60\n')
                    print("Sent: BACKWARD:60")
                elif user_input == 'l':
                    ser.write(b'LEFT:60\n')
                    print("Sent: LEFT:60")
                elif user_input == 'r':
                    ser.write(b'RIGHT:60\n')
                    print("Sent: RIGHT:60")
                elif user_input == 's':
                    ser.write(b'STOP:0\n')
                    print("Sent: STOP:0")
                elif user_input == 'reset':
                    ser.write(b'RESET:0\n')
                    print("Sent: RESET:0")
                elif ':' in user_input:
                    command = user_input.upper()
                    ser.write((command + '\n').encode())
                    print(f"Sent: {command}")
                else:
                    print("Unknown command")

            # Read Arduino output
            while ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    if line.startswith('{"sensors"'):
                        # Sensor data - only show collision status
                        if 'true' in line:
                            print(f"COLLISION: {line}")
                    else:
                        # Debug messages
                        print(f"Arduino: {line}")

            time.sleep(0.05)  # Small delay

        ser.close()

    except KeyboardInterrupt:
        print("\nInterrupted - sending STOP")
        if 'ser' in locals() and ser.is_open:
            ser.write(b'STOP:0\n')
            ser.close()
    except Exception as e:
        print(f"Error: {e}")

def simple_test():
    """Simple test to reproduce the issue"""
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print("Testing robot state issue...")

        print("1. Sending FORWARD:60...")
        ser.write(b'FORWARD:60\n')
        time.sleep(2)

        print("2. Sending STOP:0...")
        ser.write(b'STOP:0\n')
        time.sleep(2)

        print("3. Test complete. Check joystick now.")
        print("4. Monitor output for 10 seconds...")

        start_time = time.time()
        while time.time() - start_time < 10:
            while ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line and not line.startswith('{"sensors"'):
                    print(f"Arduino: {line}")
            time.sleep(0.1)

        ser.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Choose mode:")
    print("1. Interactive monitor")
    print("2. Simple test")

    choice = input("Enter choice (1 or 2): ").strip()

    if choice == "1":
        monitor_robot()
    elif choice == "2":
        simple_test()
    else:
        print("Invalid choice")