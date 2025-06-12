#!/usr/bin/env python3
import serial
import time

SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 115200

def simple_reconnect_test():
    """Very simple test to check if Arduino responds after reconnection"""

    for attempt in range(5):
        print(f"\n{'='*50}")
        print(f"ATTEMPT {attempt + 1}/5")
        print(f"{'='*50}")

        try:
            # Connect
            print("📡 Connecting...")
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=5)
            time.sleep(1)  # Give connection time to establish

            # Send a simple command and wait for ANY response
            print("📤 Sending RESET command...")
            ser.write(b'RESET:0\n')
            ser.flush()  # Ensure data is sent

            # Wait longer for response
            print("⏰ Waiting for response (up to 10 seconds)...")
            response_received = False
            start_time = time.time()

            while time.time() - start_time < 10:
                if ser.in_waiting > 0:
                    try:
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            print(f"📨 RESPONSE: {line}")
                            response_received = True
                            if "RESET" in line:
                                print("✅ Arduino responded to RESET command!")
                                break
                    except:
                        pass
                time.sleep(0.1)

            if response_received:
                print(f"✅ ATTEMPT {attempt + 1}: Arduino is RESPONSIVE")
            else:
                print(f"❌ ATTEMPT {attempt + 1}: Arduino is NOT RESPONDING")

            # Close connection
            print("🔌 Closing connection...")
            ser.close()

            # Wait before next attempt
            if attempt < 4:
                print("⏸️  Waiting 5 seconds before next attempt...")
                time.sleep(5)

        except Exception as e:
            print(f"❌ ATTEMPT {attempt + 1}: Connection failed - {e}")
            time.sleep(3)

    print(f"\n{'='*50}")
    print("🎯 TEST COMPLETE")
    print("📋 If Arduino stops responding after first attempt:")
    print("   - The issue is confirmed")
    print("   - Arduino gets stuck during disconnection")
    print("   - Need to investigate serial handling further")
    print("📋 If Arduino responds to all attempts:")
    print("   - Reconnection fix is working!")
    print("   - Robot should work reliably with scripts")

if __name__ == "__main__":
    simple_reconnect_test()