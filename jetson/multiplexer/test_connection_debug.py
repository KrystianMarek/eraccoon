#!/usr/bin/env python3
import serial
import time
import sys

SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 115200

def test_connection():
    """Test Arduino connection and diagnose hanging issues"""
    print("🔍 ARDUINO CONNECTION DIAGNOSTIC")
    print("=" * 50)

    try:
        print("1. 📡 Opening serial connection...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
        print(f"   ✅ Connected to {SERIAL_PORT} at {BAUD_RATE} baud")

        # Test 1: Wait for startup messages
        print("\n2. 🚀 Waiting for Arduino startup messages (10 seconds)...")
        startup_seen = False
        start_time = time.time()

        while time.time() - start_time < 10:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    print(f"   📨 {line}")
                    if "STARTUP COMPLETE" in line or "SYSTEM READY" in line:
                        startup_seen = True
                        break
            time.sleep(0.1)

        if startup_seen:
            print("   ✅ Arduino startup detected")
        else:
            print("   ⚠️  No startup messages - Arduino might be already running")

        # Test 2: Send a simple command
        print("\n3. 📤 Testing basic command response...")
        ser.write(b'RESET:0\n')
        time.sleep(1)

        response_seen = False
        start_time = time.time()
        while time.time() - start_time < 5:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    print(f"   📨 {line}")
                    if "RESET" in line:
                        response_seen = True
                        break
            time.sleep(0.1)

        if response_seen:
            print("   ✅ Arduino responds to commands")
        else:
            print("   ❌ No response to RESET command")
            return False

        # Test 3: Monitor alive messages
        print("\n4. 💓 Monitoring for alive messages (30 seconds)...")
        alive_seen = False
        start_time = time.time()

        while time.time() - start_time < 35:  # Wait a bit longer than 30s alive interval
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    if "ALIVE" in line:
                        print(f"   💓 {line}")
                        alive_seen = True
                    elif not line.startswith('{"sensors"'):
                        print(f"   📨 {line}")
            time.sleep(0.1)

        if alive_seen:
            print("   ✅ Arduino sending alive messages")
        else:
            print("   ⚠️  No alive messages detected")

        # Test 4: Test graceful disconnect
        print("\n5. 🔌 Testing graceful disconnect...")
        ser.close()
        print("   ✅ Serial connection closed")

        # Test 5: Immediate reconnection
        print("\n6. 🔄 Testing immediate reconnection...")
        time.sleep(2)  # Brief pause

        try:
            ser2 = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
            print("   ✅ Reconnection successful")

            # Check if Arduino responds after reconnection
            response_after_reconnect = False
            start_time = time.time()

            # Send test command
            ser2.write(b'RESET:0\n')

            while time.time() - start_time < 5:
                if ser2.in_waiting > 0:
                    line = ser2.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        print(f"   📨 {line}")
                        response_after_reconnect = True
                        break
                time.sleep(0.1)

            if response_after_reconnect:
                print("   ✅ Arduino responds after reconnection")
            else:
                print("   ❌ Arduino not responding after reconnection")

            ser2.close()

        except Exception as e:
            print(f"   ❌ Reconnection failed: {e}")
            return False

        print("\n" + "=" * 50)
        print("🎯 DIAGNOSTIC COMPLETE")
        print("✅ Arduino connection appears to be working normally")
        print("📋 If robot becomes unresponsive after scripts:")
        print("   - Check for 💓 ALIVE messages every 30 seconds")
        print("   - Try RESET:0 command to recover")
        print("   - Look for 🧹 CLEANING messages if buffer issues")
        return True

    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    test_connection()