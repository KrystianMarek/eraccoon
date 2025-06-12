#!/usr/bin/env python3
import serial
import time

SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 115200

def test_safety_system():
    """Test the improved safety system and LCD display"""
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud")
        print("\nSafety System Test")
        print("=" * 50)
        print("Instructions:")
        print("1. Watch the LCD display for obstacle information")
        print("2. Try moving joystick when obstacles are detected")
        print("3. Remove obstacles and verify safety clears")
        print("4. Test serial commands with obstacles present")
        print("-" * 50)

        # Wait for Arduino to initialize
        time.sleep(2)

        print("\nPhase 1: Testing serial commands")
        commands = [
            ("FORWARD:40", "Test forward movement"),
            ("STOP:0", "Stop robot"),
            ("BACKWARD:40", "Test backward movement"),
            ("STOP:0", "Stop robot"),
            ("LEFT:30", "Test left turn"),
            ("STOP:0", "Stop robot"),
            ("RIGHT:30", "Test right turn"),
            ("STOP:0", "Stop robot"),
        ]

        for cmd, description in commands:
            print(f"\n{description}: Sending {cmd}")
            ser.write((cmd + '\n').encode('utf-8'))
            time.sleep(1.5)  # Give time to see LCD changes

            # Read Arduino output
            start_time = time.time()
            while time.time() - start_time < 0.5:
                while ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line and not line.startswith('{"sensors"'):
                        print(f"  Arduino: {line}")

        print("\nPhase 2: Testing reset command")
        print("Sending RESET command to clear any stuck states...")
        ser.write(b'RESET:0\n')
        time.sleep(1)

        print("\nPhase 3: Monitor for 10 seconds")
        print("Try using the joystick now and watch the LCD...")
        print("Place obstacles in front/back and observe LCD changes")

        start_time = time.time()
        while time.time() - start_time < 10:
            while ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    if line.startswith('LCD:'):
                        print(f"📺 {line}")
                    elif line.startswith('SENSOR DEBUG'):
                        print(f"🔍 {line}")
                    elif line.startswith('JOYSTICK'):
                        print(f"🕹️  {line}")
                    elif line.startswith('MOVEMENT BLOCKED'):
                        print(f"🚫 {line}")
                    elif line.startswith('CLEARING STUCK'):
                        print(f"✅ {line}")
                    elif not line.startswith('{"sensors"'):
                        print(f"🤖 {line}")
            time.sleep(0.1)

        print("\nTest completed!")
        print("Expected behavior:")
        print("- LCD shows 'ALL CLEAR' (green) when no obstacles")
        print("- LCD shows 'OBSTACLE: FRONT/REAR BLOCKED' (red) when blocked")
        print("- Safety blocks movement when obstacles detected")
        print("- Safety automatically clears when obstacles removed")
        print("- Joystick works normally when path is clear")

        ser.close()

    except KeyboardInterrupt:
        print("\nTest interrupted")
        if 'ser' in locals() and ser.is_open:
            ser.write(b'STOP:0\n')
            ser.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_safety_system()