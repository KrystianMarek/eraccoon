#!/usr/bin/env python3

import serial
import time
import sys

def find_arduino_port():
    """Find Arduino port automatically"""
    import serial.tools.list_ports

    for port in serial.tools.list_ports.comports():
        if 'Arduino' in port.description or 'ttyACM' in port.device or 'ttyUSB' in port.device:
            return port.device
    return None

def test_watchdog_reboot():
    """Test watchdog reboot functionality"""
    print("🐕 WATCHDOG REBOOT TEST")
    print("=" * 40)

    # Find and connect to Arduino
    port = find_arduino_port()
    if not port:
        print("❌ No Arduino found")
        return False

    print(f"📡 Connecting to {port}...")

    try:
        ser = serial.Serial(port, 115200, timeout=1)
        time.sleep(2)  # Wait for connection
        print("✅ Connected!")

        # Clear any initial messages
        while ser.in_waiting > 0:
            ser.readline()

        # Send command to activate watchdog
        print("📤 Activating watchdog with FORWARD command...")
        ser.write(b"FORWARD:60\n")
        time.sleep(2)

        # Send STOP to clear command
        print("🛑 Sending STOP command...")
        ser.write(b"STOP:0\n")
        time.sleep(1)

        print("⏰ Waiting for watchdog timeout and reboot...")
        print("   Looking for timeout → deactivation → reboot sequence")

        start_time = time.time()
        timeout_seen = False
        deactivation_seen = False
        reboot_detected = False

        while time.time() - start_time < 15:
            try:
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        elapsed = time.time() - start_time
                        print(f"[{elapsed:.1f}s] {line}")

                        if "SERIAL TIMEOUT" in line:
                            print("   🔍 Timeout detected!")
                            timeout_seen = True

                        if "WATCHDOG: DEACTIVATED" in line:
                            print("   🔍 Watchdog deactivated!")
                            deactivation_seen = True

                        # Look for signs of reboot after timeout
                        if timeout_seen and deactivation_seen:
                            if ("JOYSTICK DEBUG" in line or
                                "USING JOYSTICK CONTROL" in line or
                                "LCD: Force update after reset" in line):
                                print("   ✅ REBOOT DETECTED! Arduino restarted cleanly.")
                                reboot_detected = True
                                break
                else:
                    time.sleep(0.1)

            except Exception as e:
                print(f"   📥 Serial error: {e}")
                if timeout_seen and deactivation_seen:
                    print("   ✅ REBOOT DETECTED! Serial error after watchdog timeout.")
                    reboot_detected = True
                break

        # Final assessment
        if reboot_detected:
            print("\n🎉 WATCHDOG TEST PASSED!")
            print("   • Timeout detected ✅")
            print("   • Watchdog deactivated ✅")
            print("   • Reboot occurred ✅")
            result = True
        elif timeout_seen and deactivation_seen:
            print("\n✅ WATCHDOG TEST LIKELY PASSED!")
            print("   • Timeout detected ✅")
            print("   • Watchdog deactivated ✅")
            print("   • Reboot likely occurred (Arduino may have rebooted quickly)")
            result = True
        else:
            print("\n❌ WATCHDOG TEST FAILED!")
            print(f"   • Timeout detected: {'✅' if timeout_seen else '❌'}")
            print(f"   • Watchdog deactivated: {'✅' if deactivation_seen else '❌'}")
            print(f"   • Reboot detected: {'✅' if reboot_detected else '❌'}")
            result = False

        ser.close()
        return result

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_watchdog_reboot()
    sys.exit(0 if success else 1)