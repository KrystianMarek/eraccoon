#!/usr/bin/env python3

import serial
import time
import threading
import sys

def keepalive_sender(ser, stop_event):
    """Send keep-alive messages every 3 seconds"""
    while not stop_event.is_set():
        try:
            if ser.is_open:
                ser.write(b"KEEPALIVE:0\n")
                print("📡 Sent keep-alive")
            time.sleep(3)
        except Exception as e:
            print(f"❌ Keep-alive error: {e}")
            break

def test_simple_keepalive():
    # Find Arduino port
    ports = ['/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyUSB0', '/dev/ttyUSB1']
    ser = None

    for port in ports:
        try:
            ser = serial.Serial(port, 115200, timeout=1)
            print(f"✅ Connected to {port} at 115200 baud")
            break
        except:
            continue

    if not ser:
        print("❌ Could not connect to Arduino")
        return

    try:
        # Wait for Arduino to be ready
        time.sleep(2)

        # Send one test command to establish connection
        print("📤 Sending test command: FORWARD:30")
        ser.write(b"FORWARD:30\n")
        time.sleep(1)

        print("📤 Sending: STOP:0")
        ser.write(b"STOP:0\n")
        time.sleep(1)

        # Start keep-alive thread
        stop_keepalive = threading.Event()
        keepalive_thread = threading.Thread(target=keepalive_sender, args=(ser, stop_keepalive))
        keepalive_thread.daemon = True
        keepalive_thread.start()

        # Read responses for 10 seconds while keep-alive is running
        print("⏰ Running with keep-alive for 10 seconds...")
        start_time = time.time()
        while time.time() - start_time < 10:
            if ser.in_waiting > 0:
                response = ser.readline().decode().strip()
                if response:
                    print(f"📥 Arduino: {response}")
            time.sleep(0.1)

        print("🛑 Stopping keep-alive - Arduino should reboot in ~5 seconds")

        # Stop keep-alive thread cleanly
        stop_keepalive.set()
        keepalive_thread.join(timeout=1)

        # Clear any remaining serial buffer
        while ser.in_waiting > 0:
            ser.read()

        print("🔌 Closing serial connection...")

    finally:
        if ser and ser.is_open:
            ser.close()
        print("✅ Serial connection closed")
        print("⏰ Wait 10 seconds and check if device changed (e.g., /dev/ttyACM0 → /dev/ttyACM1)")

if __name__ == "__main__":
    test_simple_keepalive()