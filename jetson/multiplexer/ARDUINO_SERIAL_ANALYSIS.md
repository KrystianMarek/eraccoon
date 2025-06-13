# Arduino Serial Communication Analysis

**Date**: 2025-06-13
**Purpose**: Help diagnose multiplexer connection issues with Arduino firmware
**Status**: Critical - Arduino resets but multiplexer can't establish proper communication

## Executive Summary

The Arduino firmware has a **sophisticated watchdog system** that automatically reboots when serial communication fails. The multiplexer is successfully triggering the reboot (as designed), but **failing to establish proper bidirectional communication** after reconnection. The Arduino remains in joystick mode instead of switching to serial mode.

## Arduino Serial Communication Requirements

### 1. Connection Detection Logic

The Arduino detects serial connections through **ANY** of these conditions:
```cpp
// From RobotController.cpp:67-77
if (cmd.valid || Serial.available() > 0) {
    if (!serialWasActive) {
        Serial.println("🔌 SERIAL CONNECTED: External controller detected");
        serialWasActive = true;
    }
    // Always activate watchdog when we have serial activity
    if (!watchdogActive) {
        activateWatchdog();
    }
}
```

**Key Points:**
- **ANY** data in serial buffer triggers connection detection
- **ANY** valid command triggers connection detection
- No special handshake or initialization required
- Connection is detected **immediately** on first data

### 2. Watchdog System Behavior

#### Activation Triggers:
- **Immediate**: Any serial data or valid command
- **Timeout**: 5 seconds (WATCHDOG_TIMEOUT_MS)
- **Kick Frequency**: Every 100ms (sensor data) + every command received

#### Watchdog States:
```cpp
// From RobotController.cpp:456-485
void RobotController::activateWatchdog() {
    if (!watchdogHardwareStarted) {
        if (mbed::Watchdog::get_instance().start(WATCHDOG_TIMEOUT_MS)) {
            watchdogHardwareStarted = true;
            watchdogActive = true;
            Serial.println("🐕 WATCHDOG: STARTED - Serial communication mode");
        }
    }
}
```

#### Deactivation Logic:
- **Timeout**: 3 seconds without serial activity
- **Result**: Arduino returns to joystick mode
- **Warning**: "Will reboot in 5s if no serial activity"

### 3. Serial Protocol Requirements

#### Command Format:
```
DIRECTION:SPEED\n
```

**Examples:**
- `FORWARD:60\n`
- `BACKWARD:50\n`
- `KEEPALIVE:0\n`
- `STOP:0\n`

#### Keepalive Requirements:
- **Command**: `KEEPALIVE:0\n`
- **Frequency**: Every 3 seconds (must be < 5 second watchdog timeout)
- **Purpose**: Prevents watchdog reboot
- **Response**: `💓 KEEPALIVE processed - no motor action`

#### Sensor Data Output:
```json
{"sensors":{"front_left":123,"front_right":456,"rear_left":789,"rear_right":101,"front_collision":false,"rear_collision":false}}
```
- **Frequency**: Every 100ms when watchdog active
- **Trigger**: Automatic when in serial mode

## Working Test Script Analysis

From `test_complete_robot.py`, the successful connection sequence is:

### 1. Connection Sequence:
```python
# 1. Open serial port
self.serial = serial.Serial(self.port, self.baud_rate, timeout=1)

# 2. Wait for Arduino startup
time.sleep(2)

# 3. Start keepalive immediately
self.start_keepalive()
```

### 2. Keepalive Implementation:
```python
def _keepalive_worker(self):
    while not self.stop_keepalive.is_set():
        if self.connected and self.serial and self.serial.is_open:
            self.send_command("KEEPALIVE", 0, silent=True)
        time.sleep(3)  # Every 3 seconds
```

### 3. Expected Arduino Responses:
```
🔌 SERIAL CONNECTED: External controller detected
🐕 WATCHDOG: STARTED - Serial communication mode
💓 KEEPALIVE processed - no motor action
{"sensors":{"front_left":...}}  # Every 100ms
```

## Multiplexer Diagnosis

### Problem Symptoms:
1. ✅ Arduino reboot detected (port changes)
2. ✅ Service reconnects to new port
3. ❌ No sensor data received
4. ❌ Arduino stays in joystick mode
5. ❌ No "SERIAL CONNECTED" messages

### Root Cause Analysis:

#### Theory 1: Read Thread Not Processing Data
The Arduino **immediately** sends data when serial connection is detected:
- Alive messages every 30 seconds
- Joystick debug every 1-2 seconds
- Sensor data every 100ms (when watchdog active)

If the multiplexer read thread is dead/broken:
- Arduino data accumulates in buffer
- No keepalive commands sent
- Arduino times out and returns to joystick mode

#### Theory 2: Keepalive Not Starting
Without keepalive commands:
- Arduino watchdog never activates
- No sensor data transmission starts
- Arduino remains in joystick mode
- Connection appears successful but no data flows

#### Theory 3: Port Detection Issues
If reconnection finds wrong port or stale connection:
- Serial.open() succeeds but no actual communication
- Arduino never sees incoming data
- Watchdog never activates

## Debugging Recommendations

### 1. Enable Arduino Serial Monitoring
Connect to Arduino directly and monitor output during multiplexer connection:
```bash
# Monitor Arduino output
screen /dev/ttyACM0 115200
# or
minicom -D /dev/ttyACM0 -b 115200
```

**Expected on successful connection:**
```
🔌 SERIAL CONNECTED: External controller detected
🐕 WATCHDOG: STARTED - Serial communication mode
💓 KEEPALIVE processed - no motor action
```

**If stuck in joystick mode:**
```
🕹️ JOYSTICK DEBUG - Active:NO Pins F:0 B:0 L:0 R:0
🕹️ USING JOYSTICK CONTROL
```

### 2. Test Minimal Connection
Create a minimal test to verify basic communication:
```python
import serial
import time

# Connect to Arduino
ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
time.sleep(2)

# Send keepalive
ser.write(b'KEEPALIVE:0\n')
time.sleep(0.1)

# Read response
while ser.in_waiting:
    print(ser.readline().decode().strip())
```

### 3. Check Thread Status
Verify multiplexer threads are actually running:
- Read thread processing incoming data
- Keepalive thread sending commands
- Both threads restarted after reconnection

### 4. Timing Analysis
The Arduino has strict timing requirements:
- **Connection detection**: Immediate on first data
- **Watchdog activation**: Immediate on connection
- **Keepalive requirement**: < 5 seconds
- **Sensor data**: Starts immediately when watchdog active

## Critical Implementation Notes

### 1. No Special Handshake Required
Unlike complex protocols, Arduino serial is **dead simple**:
- Send any data → Arduino detects connection
- Send `KEEPALIVE:0\n` → Watchdog stays active
- Receive JSON sensor data → Communication working

### 2. Watchdog is Aggressive
- 5-second timeout is **hard limit**
- Missing keepalive = guaranteed reboot
- No grace period or retry logic

### 3. Port Changes are Normal
- Every reboot changes `/dev/ttyACM*` port
- Must re-scan ports after reboot
- Old port handles become invalid

## Recommended Fix Strategy

1. **Verify Thread Restart**: Ensure read/keepalive threads restart after reconnection
2. **Add Connection Verification**: Send test command after reconnection and verify response
3. **Implement Immediate Keepalive**: Start keepalive within 2 seconds of connection
4. **Add Arduino Output Monitoring**: Log Arduino responses to verify communication state
5. **Fix Port Detection**: Ensure reconnection finds the correct new port

The Arduino firmware is working correctly - the issue is in the multiplexer's post-reconnection communication handling.