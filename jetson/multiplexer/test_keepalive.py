#!/usr/bin/env python3

import serial
import time
import threading
import sys

def keepalive_sender(ser, stop_event):
    """Send keep-alive messages every 2 seconds"""
    while not stop_event.is_set():
        try:
            if ser.is_open:
                ser.write(b"KEEPALIVE:0\n")
                print("📡 Sent keep-alive")
            time.sleep(2)
        except Exception as e:
            print(f"❌ Keep-alive error: {e}")
            break

def test_robot_with_keepalive():
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

    # Start keep-alive thread
    stop_keepalive = threading.Event()
    keepalive_thread = threading.Thread(target=keepalive_sender, args=(ser, stop_keepalive))
    keepalive_thread.daemon = True
    keepalive_thread.start()

    try:
        # Wait for Arduino to be ready
        time.sleep(2)

        # Test commands with keep-alive running in background
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
            print(f"📤 Sending: {cmd}")
            ser.write(f"{cmd}\n".encode())

            # Read responses for 2 seconds
            start_time = time.time()
            while time.time() - start_time < 2:
                if ser.in_waiting > 0:
                    response = ser.readline().decode().strip()
                    if response:
                        print(f"📥 Arduino: {response}")
                time.sleep(0.1)

        print("✅ Test completed - keep-alive still running")
        print("⏰ Waiting 5 seconds before stopping keep-alive...")
        time.sleep(5)

        print("🛑 Stopping keep-alive - Arduino should reboot in ~8 seconds")

    finally:
        # Stop keep-alive thread
        stop_keepalive.set()
        keepalive_thread.join(timeout=1)
        ser.close()
        print("🔌 Serial connection closed")

if __name__ == "__main__":
    test_robot_with_keepalive()