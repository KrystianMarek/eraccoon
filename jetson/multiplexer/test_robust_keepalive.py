#!/usr/bin/env python3

import serial
import time
import threading
import sys
import glob

def find_arduino_port():
    """Find available Arduino port"""
    ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
    for port in sorted(ports):
        try:
            ser = serial.Serial(port, 115200, timeout=1)
            ser.close()
            return port
        except:
            continue
    return None

def keepalive_sender(ser, stop_event):
    """Send keep-alive messages every 3 seconds"""
    while not stop_event.is_set():
        try:
            if ser.is_open:
                ser.write(b"KEEPALIVE:0\n")
                print("📡 Sent keep-alive")
            time.sleep(3)
        except Exception as e:
            print(f"📡 Keep-alive stopped: {e}")
            break

def safe_write(ser, data):
    """Safely write to serial, handling disconnection"""
    try:
        ser.write(data)
        return True
    except Exception as e:
        print(f"⚠️  Write failed (Arduino may have rebooted): {e}")
        return False

def test_robust_keepalive():
    # Find Arduino port
    initial_port = find_arduino_port()
    if not initial_port:
        print("❌ Could not find Arduino")
        return

    print(f"🔍 Found Arduino at: {initial_port}")

    try:
        ser = serial.Serial(initial_port, 115200, timeout=1)
        print(f"✅ Connected to {initial_port} at 115200 baud")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    try:
        # Wait for Arduino to be ready
        time.sleep(2)

        # Send test commands with error handling
        print("📤 Sending test command: FORWARD:30")
        if not safe_write(ser, b"FORWARD:30\n"):
            return
        time.sleep(1)

        print("📤 Sending: STOP:0")
        if not safe_write(ser, b"STOP:0\n"):
            return
        time.sleep(1)

        # Start keep-alive thread
        stop_keepalive = threading.Event()
        keepalive_thread = threading.Thread(target=keepalive_sender, args=(ser, stop_keepalive))
        keepalive_thread.daemon = True
        keepalive_thread.start()

        # Read responses for 8 seconds while keep-alive is running
        print("⏰ Running with keep-alive for 8 seconds...")
        start_time = time.time()
        while time.time() - start_time < 8:
            try:
                if ser.in_waiting > 0:
                    response = ser.readline().decode().strip()
                    if response:
                        print(f"📥 Arduino: {response}")
            except Exception as e:
                print(f"📥 Read error (Arduino may have rebooted): {e}")
                break
            time.sleep(0.1)

        print("🛑 Stopping keep-alive - Arduino should reboot soon...")

        # Stop keep-alive thread cleanly
        stop_keepalive.set()
        keepalive_thread.join(timeout=1)

        print("⏰ Waiting for Arduino reboot...")

        # Monitor for reboot by checking port availability
        reboot_detected = False
        for i in range(15):  # Wait up to 15 seconds
            try:
                # Try to read from the port
                if ser.in_waiting > 0:
                    ser.read()
            except:
                print(f"🔄 Arduino disconnected after {i+1} seconds")
                reboot_detected = True
                break
            time.sleep(1)

        if not reboot_detected:
            print("⚠️  No reboot detected within 15 seconds")

    except Exception as e:
        print(f"❌ Test error: {e}")
    finally:
        try:
            if ser and ser.is_open:
                ser.close()
        except:
            pass
        print("🔌 Serial connection closed")

        # Check for new port after reboot
        time.sleep(2)
        final_port = find_arduino_port()
        if final_port and final_port != initial_port:
            print(f"✅ REBOOT CONFIRMED: {initial_port} → {final_port}")
        elif final_port == initial_port:
            print(f"⚠️  Same port detected: {final_port} (reboot may not have occurred)")
        else:
            print("❌ No Arduino port found after test")

if __name__ == "__main__":
    test_robust_keepalive()
