# Arduino Robot Serial Protocol

## Overview
This document describes the serial communication protocol for the 4-wheel Arduino robot with modular architecture. The robot supports dual control modes: onboard joystick and external JSON commands via PC.

## Connection Parameters
- **Baud Rate**: 115200
- **Data Bits**: 8
- **Parity**: None
- **Stop Bits**: 1
- **Flow Control**: None
- **Port**: `/dev/ttyACM*` (Linux/Mac) or `COM*` (Windows)

## Control Priority
1. **Serial Commands** (highest priority) - PC control overrides joystick
2. **Onboard Joystick** (fallback) - Active when no serial commands present
3. **Safety System** - Can block unsafe movements regardless of control source

## Command Protocol

### Command Format
All commands must be in JSON format and end with newline character (`\n`):

```json
{"type": "tank", "command": "FORWARD", "value": 60}
{"type": "mecanum", "motors": {"left_front": 100, "left_rear": -100, "right_front": -100, "right_rear": 100}}
```

### Tank Movement Commands
| Command | Value Range | Description | Example |
|---------|-------------|-------------|---------|
| `FORWARD` | 0-255 | Move forward at specified speed | `{"type": "tank", "command": "FORWARD", "value": 60}` |
| `BACKWARD` | 0-255 | Move backward at specified speed | `{"type": "tank", "command": "BACKWARD", "value": 50}` |
| `LEFT` | 0-255 | Turn left at specified speed | `{"type": "tank", "command": "LEFT", "value": 40}` |
| `RIGHT` | 0-255 | Turn right at specified speed | `{"type": "tank", "command": "RIGHT", "value": 40}` |
| `FORWARD_LEFT` | 0-255 | Move forward-left diagonal | `{"type": "tank", "command": "FORWARD_LEFT", "value": 45}` |
| `FORWARD_RIGHT` | 0-255 | Move forward-right diagonal | `{"type": "tank", "command": "FORWARD_RIGHT", "value": 45}` |
| `BACKWARD_LEFT` | 0-255 | Move backward-left diagonal | `{"type": "tank", "command": "BACKWARD_LEFT", "value": 35}` |
| `BACKWARD_RIGHT` | 0-255 | Move backward-right diagonal | `{"type": "tank", "command": "BACKWARD_RIGHT", "value": 35}` |
| `STOP` | 0 | Stop all motors immediately | `{"type": "tank", "command": "STOP", "value": 0}` |

### Mecanum Movement Commands
Direct motor control for advanced movements:

```json
{
  "type": "mecanum",
  "motors": {
    "left_front": -100,
    "left_rear": 100,
    "right_front": 100,
    "right_rear": -100
  }
}
```

**Motor Speed Range**: -255 to 255 (negative values = reverse)

**Basic Movement Patterns**:
- **Forward**: `LF:100, LR:100, RF:100, RR:100`
- **Backward**: `LF:-100, LR:-100, RF:-100, RR:-100`
- **Strafe Right**: `LF:-100, LR:100, RF:100, RR:-100`
- **Strafe Left**: `LF:100, LR:-100, RF:-100, RR:100`
- **Rotate Clockwise**: `LF:-100, LR:-100, RF:100, RR:100`
- **Rotate Counter-Clockwise**: `LF:100, LR:100, RF:-100, RR:-100`

### System Commands
| Command | Description | Example | Behavior |
|---------|-------------|---------|----------|
| `RESET` | Reset robot state and return to joystick control | `{"type": "tank", "command": "RESET", "value": 0}` | Resets all states, activates joystick control |
| `KEEPALIVE` | Prevent auto-reboot (for connection maintenance) | `{"type": "tank", "command": "KEEPALIVE", "value": 0}` | **No motor action** - only kicks watchdog timer |

**Note**: KEEPALIVE commands are processed as tank commands but do not trigger any motor movement. They serve solely to maintain the connection and prevent the auto-reboot system from activating during idle periods.

### Speed Values
- **Tank Commands**: 0-255 (8-bit PWM values)
- **Mecanum Commands**: -255 to 255 (signed for direction)
- **Recommended**: 30-80 for normal operation
- **0**: Stop/No movement
- **255/-255**: Maximum speed (use with caution)

## Response Protocol

### Command Acknowledgment
Arduino sends debug messages for received commands:
```
PARSED TANK JSON: FORWARD:60 -> 1
🤖 NEW TANK CMD: FORWARD at speed 60
🚗 MOTOR: Executing FORWARD at speed 60

PARSED MECANUM JSON: LF:100 LR:-100 RF:-100 RR:100
🤖 NEW MECANUM CMD: LF:100 LR:-100 RF:-100 RR:100
🚗 MECANUM MOTORS: LF:100 LR:-100 RF:-100 RR:100
```

### Error Messages
```
INVALID COMMAND FORMAT: Expected JSON, got: 'FORWARD:60'
JSON PARSE ERROR: Invalid JSON syntax
MISSING TYPE FIELD IN JSON
INVALID MOTOR SPEEDS IN MECANUM JSON (must be -255 to 255)
```

### Sensor Data (JSON Format)
Sent automatically every 500ms during operation:
```json
{
  "sensors": {
    "front_left": 2147483647,
    "front_right": 1331,
    "rear_left": 242,
    "rear_right": 380,
    "front_collision": false,
    "rear_collision": false
  }
}
```

#### Sensor Data Fields
- **Distance values**: Measured in arbitrary units (higher = farther)
- **2147483647**: Maximum sensor reading (no obstacle detected)
- **Low values (< 100)**: Close obstacles detected
- **front_collision/rear_collision**: Boolean safety flags

### Status Messages
Arduino sends various status messages with emoji prefixes:
- `🚀 SYSTEM READY` - Arduino ready for commands
- `💓 ALIVE` - Periodic heartbeat (every 30 seconds)
- `🔌 SERIAL CONNECTED` - External controller detected
- `🕹️ USING JOYSTICK CONTROL` - Fallback to joystick mode
- `🛑 STOP CMD - EXECUTED` - Stop command processed
- `⚠️ OBSTACLE DETECTED` - Safety system active

## Auto-Reboot System

### Purpose
Ensures clean state between different control sessions by automatically rebooting Arduino when external controller disconnects.

### Behavior
1. **Connection Detection**: Arduino detects when external controller connects
2. **Grace Period**: 5-second grace period after connection to prevent premature reboot
3. **Disconnection Detection**:
   - Port closure detection (immediate)
   - Activity timeout (5 seconds of no commands)
4. **Auto-Reboot**: Arduino resets itself using `NVIC_SystemReset()`
5. **Device Re-enumeration**: USB device changes (e.g., `/dev/ttyACM0` → `/dev/ttyACM1`)

### Keep-Alive Support
- **Format**: `{"type": "tank", "command": "KEEPALIVE", "value": 0}` (JSON tank command)
- **Behavior**: No motor action - only kicks watchdog timer to prevent auto-reboot
- **Parsing**: Processed as tank command, converted to `KEEPALIVE_CMD` enum internally
- **Usage**: Send periodically (every 3-5 seconds) to maintain connection during idle periods
- **Important**: KEEPALIVE commands do NOT reset the activity timer for command persistence

## Safety System

### Obstacle Detection
- **4 ultrasonic sensors**: Front-left, front-right, rear-left, rear-right
- **Collision thresholds**: Configurable distance limits
- **Movement blocking**: Prevents unsafe movements when obstacles detected

### Safety Behavior
- **Forward movement**: Blocked if front sensors detect obstacles
- **Backward movement**: Blocked if rear sensors detect obstacles
- **Turning**: Generally allowed (robot can turn in place)
- **Override**: No manual override - safety is always enforced

## Error Handling

### Invalid Commands
- Non-JSON commands are rejected
- Unknown command types default to invalid
- Invalid speed values (outside valid ranges) are rejected
- Malformed JSON is ignored with error message

### Connection Issues
- **Timeout**: Commands expire after 1000ms if not refreshed
- **Buffer overflow**: Serial buffer cleared periodically
- **Port errors**: Trigger immediate auto-reboot

## Example Communication Session

```
# Connection established
Arduino: 🚀 SYSTEM READY - Accepting connections

# Send tank movement command
PC: {"type": "tank", "command": "FORWARD", "value": 60}
Arduino: PARSED TANK JSON: FORWARD:60 -> 1
Arduino: 🤖 NEW TANK CMD: FORWARD at speed 60
Arduino: 🚗 MOTOR: Executing FORWARD at speed 60

# Send mecanum movement command
PC: {"type": "mecanum", "motors": {"left_front": -100, "left_rear": 100, "right_front": 100, "right_rear": -100}}
Arduino: PARSED MECANUM JSON: LF:-100 LR:100 RF:100 RR:-100
Arduino: 🤖 NEW MECANUM CMD: LF:-100 LR:100 RF:100 RR:-100
Arduino: 🚗 MECANUM MOTORS: LF:-100 LR:100 RF:100 RR:-100

# Sensor data (automatic)
Arduino: {"sensors":{"front_left":2147483647,"front_right":1331,...}}

# Stop command
PC: {"type": "tank", "command": "STOP", "value": 0}
Arduino: 🛑 STOP CMD - EXECUTED, NOT PERSISTING

# Connection closed by PC
Arduino: 🔌 SERIAL TIMEOUT: No activity for 5 seconds
Arduino: 🔄 AUTO-REBOOT: Restarting Arduino for clean state...
# Arduino resets, device re-enumerates
```

## Integration Notes

### For Control Applications
1. **Connect** to Arduino at 115200 baud
2. **Wait** for `SYSTEM READY` message
3. **Send JSON commands** with proper formatting
4. **Parse JSON** sensor data for obstacle avoidance

### Python Example
```python
import serial
import json

ser = serial.Serial('/dev/ttyACM0', 115200)

# Tank movement
tank_cmd = json.dumps({"type": "tank", "command": "FORWARD", "value": 60})
ser.write(f"{tank_cmd}\n".encode())

# Mecanum strafing
mecanum_cmd = json.dumps({
    "type": "mecanum",
    "motors": {
        "left_front": -100,
        "left_rear": 100,
        "right_front": 100,
        "right_rear": -100
    }
})
ser.write(f"{mecanum_cmd}\n".encode())
```

This protocol provides a consistent, structured approach to robot control with support for both simple tank-style movements and advanced mecanum wheel capabilities.