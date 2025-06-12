#!/usr/bin/env python3
import serial
import time

SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 115200

def test_reconnection_fix():
    """Test the reconnection fixes"""
    print("🔄 RECONNECTION FIX TEST")
    print("=" * 40)

    for attempt in range(3):
        print(f"\n🔢 ATTEMPT {attempt + 1}/3")
        print("-" * 20)

        try:
            # Connect
            print("1. 📡 Connecting...")
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=3)
            print("   ✅ Connected")

            # Wait for startup or ready messages
            print("2. 🚀 Waiting for ready messages...")
            ready_seen = False
            start_time = time.time()

            while time.time() - start_time < 10:
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        if ('SYSTEM READY' in line or 'SERIAL CONNECTED' in line or
                            'STARTUP COMPLETE' in line or 'AUTO-RESET' in line):
                            print(f"   📨 {line}")
                            ready_seen = True
                            break
                        elif not line.startswith('{"sensors"'):
                            print(f"   📝 {line}")
                time.sleep(0.1)

            if ready_seen:
                print("   ✅ Arduino ready")
            else:
                print("   ⚠️  No ready message")

            # Test basic command
            print("3. 📤 Testing command...")
            ser.write(b'RESET:0\n')
            time.sleep(1)

            response_seen = False
            start_time = time.time()
            while time.time() - start_time < 3:
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line and 'RESET' in line:
                        print(f"   📨 {line}")
                        response_seen = True
                        break
                time.sleep(0.1)

            if response_seen:
                print("   ✅ Command response OK")
            else:
                print("   ❌ No command response")

            # Disconnect
            print("4. 🔌 Disconnecting...")
            ser.close()
            print("   ✅ Disconnected")

            # Wait before reconnection
            print("5. ⏰ Waiting 3 seconds...")
            time.sleep(3)

            # Results for this attempt
            if ready_seen and response_seen:
                print(f"   ✅ Attempt {attempt + 1}: SUCCESS")
            else:
                print(f"   ❌ Attempt {attempt + 1}: FAILED")

        except Exception as e:
            print(f"   ❌ Attempt {attempt + 1}: ERROR - {e}")

        if attempt < 2:  # Not the last attempt
            print("   ⏸️  Pausing before next attempt...")
            time.sleep(2)

    print(f"\n" + "=" * 40)
    print("🎯 RECONNECTION TEST COMPLETE")
    print("📋 If all attempts succeeded:")
    print("   - Arduino properly detects disconnection")
    print("   - Arduino resets state on reconnection")
    print("   - Arduino responds to commands after reconnection")
    print("   - Robot should remain responsive between script runs")

if __name__ == "__main__":
    test_reconnection_fix()