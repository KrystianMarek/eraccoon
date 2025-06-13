#!/usr/bin/env python3
import serial
import time
import sys
import json

def test_arduino_commands():
    try:
        print('🔍 Testing Arduino command activation...')
        ser = serial.Serial('/dev/ttyACM1', 115200, timeout=2)
        print('✅ Serial port opened successfully')

        # Wait for Arduino to initialize
        time.sleep(3)

        # Test commands that might activate serial mode
        commands = [
            'FORWARD:0',    # Basic movement command
            'STOP:0',       # Stop command
            'RESET:0',      # Reset command
            'KEEPALIVE:0',  # Keepalive
        ]

        for cmd in commands:
            print(f'\n📤 Sending: {cmd}')
            ser.write(f'{cmd}\n'.encode('utf-8'))
            ser.flush()

            # Read responses for 2 seconds
            start_time = time.time()
            responses = []
            while time.time() - start_time < 2:
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        responses.append(line)
                        # Check for important status changes
                        if '🚀 SYSTEM READY' in line:
                            print(f'   ✅ SYSTEM READY: {line}')
                        elif '🤖 NEW SERIAL CMD' in line:
                            print(f'   ✅ COMMAND RECEIVED: {line}')
                        elif 'SERIAL CONNECTED' in line:
                            print(f'   ✅ SERIAL ACTIVATED: {line}')
                        elif line.startswith('{'):
                            # JSON sensor data
                            try:
                                data = json.loads(line)
                                if 'sensors' in data:
                                    print(f'   ✅ SENSOR DATA: {line[:100]}...')
                            except:
                                pass
                        elif not ('LCD:' in line or 'JOYSTICK' in line):
                            # Other interesting messages
                            print(f'   📥 {line}')
                time.sleep(0.1)

            if responses:
                print(f'   📊 Got {len(responses)} responses')
            else:
                print('   ❌ No responses')

        # Final check - monitor for sensor data
        print(f'\n🔍 Monitoring for sensor data (10 seconds)...')
        start_time = time.time()
        sensor_count = 0
        while time.time() - start_time < 10:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line.startswith('{'):
                    try:
                        data = json.loads(line)
                        if 'sensors' in data:
                            sensor_count += 1
                            sensors = data['sensors']
                            print(f'📡 Sensor #{sensor_count}: FL:{sensors.get("front_left", "?")} FR:{sensors.get("front_right", "?")} RL:{sensors.get("rear_left", "?")} RR:{sensors.get("rear_right", "?")}')
                    except:
                        pass
                elif '🚀' in line or '🤖' in line or 'SERIAL' in line:
                    print(f'📥 Status: {line}')
            time.sleep(0.1)

        if sensor_count > 0:
            print(f'✅ Received {sensor_count} sensor data packets!')
        else:
            print('❌ No sensor data received')

        ser.close()
        print('✅ Test completed')

    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    test_arduino_commands()