#!/usr/bin/env python3
import serial
import time
import glob

BAUD_RATE = 115200

def find_arduino_port():
    """Find available Arduino port"""
    ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*') + glob.glob('COM*')
    for port in sorted(ports):
        try:
            test_ser = serial.Serial(port, BAUD_RATE, timeout=1)
            test_ser.close()
            return port
        except:
            continue
    return None

def test_serial_control():
    """Test serial control with proper timing to avoid command conflicts"""
    try:
        # Find Arduino port
        port = find_arduino_port()
        if not port:
            print("❌ No Arduino found")
            return

        # Open serial connection
        ser = serial.Serial(port, BAUD_RATE, timeout=1)
        print(f"Connected to {port} at {BAUD_RATE} baud")

        # Wait for Arduino to initialize
        time.sleep(3)

        print("\n=== SERIAL CONTROL TEST ===")
        print("🎯 Testing individual movement commands with proper timing")
        print("📝 Each command will run for 2 seconds with 1 second pause between")
        print()

        # Clear any initial state
        print("1. 🔄 Initial RESET...")
        ser.write(b'RESET:0\n')
        time.sleep(2)

        # Monitor for 3 seconds to see initial state
        print("2. 📊 Checking initial state...")
        start_time = time.time()
        while time.time() - start_time < 3:
            while ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line and not line.startswith('{"sensors"'):
                    print(f"   {line}")
            time.sleep(0.1)

        print("\n3. 🚗 Testing individual movements...")

        # Test each direction individually with longer duration
        movements = [
            ("FORWARD", 40, "Should move forward"),
            ("BACKWARD", 40, "Should move backward"),
            ("LEFT", 35, "Should turn left"),
            ("RIGHT", 35, "Should turn right")
        ]

        for direction, speed, description in movements:
            print(f"\n   🎯 Testing {direction}:{speed} - {description}")
            print(f"   📤 Sending command...")

            # Send command
            cmd = f"{direction}:{speed}\n"
            ser.write(cmd.encode('utf-8'))

            # Monitor for 2 seconds to see command execution
            start_time = time.time()
            command_seen = False
            motor_action_seen = False

            while time.time() - start_time < 2.0:  # Watch for 2 seconds
                while ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line and not line.startswith('{"sensors"'):
                        if 'NEW SERIAL CMD' in line:
                            print(f"   ✅ Command received: {line}")
                            command_seen = True
                        elif 'MOTOR: Executing' in line:
                            print(f"   🚗 Motor action: {line}")
                            motor_action_seen = True
                        elif 'CONTINUING' in line:
                            print(f"   ⏳ Continuing: {line}")
                        elif 'EXPIRED' in line:
                            print(f"   ⏰ Expired: {line}")
                        else:
                            print(f"   📝 {line}")
                time.sleep(0.1)

            # Send explicit STOP
            print(f"   🛑 Sending STOP command...")
            ser.write(b'STOP:0\n')
            time.sleep(0.5)  # Brief pause after stop

            # Check results
            if command_seen and motor_action_seen:
                print(f"   ✅ {direction} command: SUCCESS")
            elif command_seen:
                print(f"   ⚠️  {direction} command: RECEIVED but no motor action seen")
            else:
                print(f"   ❌ {direction} command: FAILED - not received")

            print(f"   ⏸️  Pausing 1 second before next command...")
            time.sleep(1)

        print(f"\n4. 🔄 Final RESET and joystick test...")
        ser.write(b'RESET:0\n')
        time.sleep(2)

        print(f"5. 🕹️  Testing joystick recovery (try joystick now)...")
        start_time = time.time()
        joystick_working = False

        while time.time() - start_time < 5:  # 5 seconds to test joystick
            while ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line and not line.startswith('{"sensors"'):
                    if 'JOYSTICK ACTIVE' in line or 'Active:YES' in line:
                        print(f"   🎮 {line}")
                        joystick_working = True
                    elif 'JOYSTICK DEBUG' in line:
                        print(f"   🔍 {line}")
                    else:
                        print(f"   📝 {line}")
            time.sleep(0.1)

        print(f"\n=== TEST RESULTS ===")
        print(f"📊 Movement Commands:")
        for direction, _, _ in movements:
            print(f"   {direction}: Check console output above")

        print(f"\n🕹️  Joystick Recovery: {'✅ WORKING' if joystick_working else '❌ NOT WORKING'}")

        if not joystick_working:
            print(f"\n🔧 TROUBLESHOOTING NEXT STEPS:")
            print(f"   1. Check if motor debug output shows different directions")
            print(f"   2. Verify that RESET clears all serial state")
            print(f"   3. Test joystick independently (disconnect serial)")
            print(f"   4. Check for hardware conflicts between serial and joystick pins")

        ser.close()

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_serial_control()