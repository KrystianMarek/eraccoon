#!/usr/bin/env python3
import serial
import time
import sys

try:
    print('🔍 Testing direct Arduino communication...')
    ser = serial.Serial('/dev/ttyACM1', 115200, timeout=2)
    print('✅ Serial port opened successfully')

    # Wait for Arduino to initialize
    time.sleep(3)

    # Try to send a command
    print('📤 Sending test command: KEEPALIVE:0')
    ser.write(b'KEEPALIVE:0\n')
    ser.flush()

    # Try to read response
    print('📥 Waiting for response...')
    start_time = time.time()
    while time.time() - start_time < 5:  # Wait up to 5 seconds
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                print(f'✅ Arduino responded: {line}')
                break
        time.sleep(0.1)
    else:
        print('❌ No response from Arduino within 5 seconds')

    # Check if more data is available
    print('📨 Checking for additional data...')
    additional_responses = 0
    while ser.in_waiting > 0 and additional_responses < 10:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line:
            print(f'   {line}')
            additional_responses += 1
        if additional_responses >= 10:
            print('   ... (truncated, more data available)')

    ser.close()
    print('✅ Test completed')

except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)