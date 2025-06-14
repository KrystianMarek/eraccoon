# Mecanum Protocol Implementation

## Overview

This document describes the implementation of the new JSON-based mecanum wheel control protocol for the Arduino robot firmware. The implementation supports both legacy commands and new JSON-based commands for tank-style and direct mecanum motor control.

## Protocol Formats

### 1. Legacy Commands (Backward Compatible)
```
FORWARD:60
BACKWARD:50
LEFT:45
RIGHT:45
FORWARD_LEFT:40
FORWARD_RIGHT:40
BACKWARD_LEFT:35
BACKWARD_RIGHT:35
STOP:0
RESET:0
KEEPALIVE:0
```

### 2. Tank JSON Commands
```json
{
  "type": "tank",
  "command": "FORWARD",
  "value": 60
}
```

Supported commands: `FORWARD`, `BACKWARD`, `LEFT`, `RIGHT`, `FORWARD_LEFT`, `FORWARD_RIGHT`, `BACKWARD_LEFT`, `BACKWARD_RIGHT`, `STOP`, `RESET`, `KEEPALIVE`

### 3. Mecanum JSON Commands (New)
```json
{
  "type": "mecanum",
  "motors": {
    "left_front": 100,
    "left_rear": -100,
    "right_front": -100,
    "right_rear": 100
  }
}
```

Motor speeds: `-255` to `255` (negative = reverse)

## Mecanum Movement Patterns

### Basic Movements
- **Forward**: `LF:100, LR:100, RF:100, RR:100`
- **Backward**: `LF:-100, LR:-100, RF:-100, RR:-100`
- **Strafe Right**: `LF:-100, LR:100, RF:100, RR:-100`
- **Strafe Left**: `LF:100, LR:-100, RF:-100, RR:100`
- **Rotate Clockwise**: `LF:-100, LR:-100, RF:100, RR:100`
- **Rotate Counter-Clockwise**: `LF:100, LR:100, RF:-100, RR:-100`

### Advanced Movements
- **Forward + Strafe Right**: `LF:50, LR:150, RF:150, RR:50`
- **Forward + Strafe Left**: `LF:150, LR:50, RF:50, RR:150`
- **Forward + Rotate**: `LF:80, LR:80, RF:40, RR:40`

## Implementation Details

### Files Modified

1. **platformio.ini**
   - Added ArduinoJson library dependency

2. **include/SerialController.h**
   - Added CommandType enum (TANK_COMMAND, MECANUM_COMMAND, LEGACY_COMMAND, INVALID_COMMAND)
   - Extended SerialCommand struct with motor_speeds array and command type
   - Added parseJsonCommand() and parseLegacyCommand() methods

3. **src/SerialController.cpp**
   - Implemented JSON parsing using ArduinoJson library
   - Added support for tank and mecanum command types
   - Maintained backward compatibility with legacy commands
   - Added comprehensive error handling and validation

4. **include/MotorController.h**
   - Added moveWithDirectControl() method for direct motor control

5. **src/MotorController.cpp**
   - Implemented moveWithDirectControl() with debug logging
   - Added motor speed validation and status reporting

6. **src/RobotController.cpp**
   - Updated command processing to handle different command types
   - Added separate execution paths for tank/legacy vs mecanum commands
   - Implemented command continuation for all command types

### Memory Usage
- RAM: 9.6% (50,360 bytes used)
- Flash: 7.3% (143,112 bytes used)
- ArduinoJson library adds minimal overhead

## Testing

### Test Files Created/Updated

1. **test_serial_control.py** - Updated to test both legacy and JSON formats
2. **test_mecanum_protocol.py** - New comprehensive mecanum testing suite
3. **test_complete_robot.py** - Added JSON command format testing

### Running Tests

```bash
# Test basic legacy and JSON tank commands
python3 test_serial_control.py

# Test comprehensive mecanum capabilities
python3 test_mecanum_protocol.py

# Test complete robot functionality including JSON commands
python3 test_complete_robot.py
```

## Command Processing Flow

```
Serial Input → parseCommand()
    ├─ Starts with '{'? → parseJsonCommand()
    │   ├─ type: "tank" → Tank JSON Command
    │   └─ type: "mecanum" → Mecanum Command
    └─ Legacy format → parseLegacyCommand()

RobotController.update()
    ├─ TANK_COMMAND/LEGACY_COMMAND → motorController->move()
    └─ MECANUM_COMMAND → motorController->moveWithDirectControl()
```

## Error Handling

### JSON Parsing Errors
- Invalid JSON syntax
- Missing required fields
- Invalid motor speeds (outside -255 to 255 range)
- Unknown command types

### Debug Output Examples
```
PARSED TANK JSON: FORWARD:60 -> 1
PARSED MECANUM JSON: LF:100 LR:-100 RF:-100 RR:100
🤖 NEW MECANUM CMD: LF:100 LR:-100 RF:-100 RR:100
🚗 MECANUM MOTORS: LF:100 LR:-100 RF:-100 RR:100
```

## Benefits

1. **Backward Compatibility**: All existing legacy commands continue to work
2. **Direct Motor Control**: Enables full mecanum wheel capabilities
3. **Precise Movement**: Individual motor speed control allows complex maneuvers
4. **Extensible**: JSON format allows easy addition of new command types
5. **Error Handling**: Comprehensive validation and error reporting
6. **Debug Support**: Detailed logging for troubleshooting

## Usage Examples

### Python Integration
```python
import serial
import json

ser = serial.Serial('/dev/ttyACM0', 115200)

# Legacy command
ser.write(b'FORWARD:60\n')

# Tank JSON command
tank_cmd = json.dumps({"type": "tank", "command": "FORWARD", "value": 60})
ser.write(f"{tank_cmd}\n".encode())

# Mecanum command for strafing right
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

### Multiplexer Integration
The new protocol allows the multiplexer to:
- Accept complex movement commands from remote control applications
- Pass through direct motor commands without lossy conversion
- Support both simple and advanced client applications
- Maintain compatibility with existing testing tools

## Future Enhancements

1. **Speed Limiting**: Add configurable maximum speeds per motor
2. **Acceleration Control**: Implement smooth acceleration/deceleration
3. **Movement Validation**: Safety checks for impossible movements
4. **Batch Commands**: Support multiple commands in single JSON payload
5. **Status Reporting**: Enhanced feedback on command execution status

## Troubleshooting

### Common Issues
1. **JSON Parse Errors**: Check JSON syntax and required fields
2. **Motor Speed Validation**: Ensure speeds are within -255 to 255 range
3. **Command Not Executed**: Check for safety system blocks or sensor obstacles
4. **Legacy Commands Not Working**: Verify colon-separated format

### Debug Steps
1. Monitor serial debug output
2. Check command parsing messages
3. Verify motor execution logs
4. Test with simple movements first
5. Use test scripts to validate functionality

This implementation successfully bridges the gap between simple tank-style controls and advanced mecanum wheel capabilities while maintaining full backward compatibility.