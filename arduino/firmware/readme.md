# Arduino Robot Firmware - Mecanum Protocol Implementation ✅

## 🎉 Project Status: READY FOR PRODUCTION

The Arduino robot firmware features a **modern JSON-based protocol** with full mecanum wheel support, robust serial communication, and comprehensive testing. Ready for multiplexer integration and advanced robotic control!

## 🏗️ Architecture Overview

### Modular Firmware Design
- **MotorController**: 4-wheel mecanum control with direct motor control and tank-style movements
- **JoystickController**: Onboard joystick with diagonal movement support
- **SerialController**: JSON-based PC communication with ArduinoJson parsing
- **RobotController**: Orchestrates all components with priority system
- **Safety System**: Obstacle detection with 4 ultrasonic sensors

### Control Priority System
1. **JSON Serial Commands** (highest) - PC control overrides everything
2. **Onboard Joystick** (fallback) - Active when no serial commands
3. **Safety System** (always active) - Blocks unsafe movements

## 🔄 Auto-Reboot System ⭐

**Key Innovation**: Arduino automatically reboots when external controller disconnects, ensuring clean state for next connection.

### How It Works
- **Connection Detection**: Tracks when external controller connects
- **Disconnection Detection**: Dual method (port closure + timeout)
- **Auto-Reboot**: `NVIC_SystemReset()` triggers clean restart
- **Device Re-enumeration**: `/dev/ttyACM0` → `/dev/ttyACM1` (expected)

### Benefits
- ✅ **No manual resets** required between script runs
- ✅ **Clean state** guaranteed for each new connection
- ✅ **Eliminates stuck states** that plagued earlier versions
- ✅ **Robust reconnection** handling

## 📡 JSON-Based Serial Protocol

### Connection Parameters
- **Baud Rate**: 115200
- **Format**: JSON commands ending with `\n`
- **Port**: Auto-discovered `/dev/ttyACM*`

### Tank Movement Commands
All commands use structured JSON format:
```json
{"type": "tank", "command": "FORWARD", "value": 60}
```

| Command | Range | Description | Example JSON |
|---------|-------|-------------|--------------|
| `FORWARD` | 0-255 | Move forward | `{"type": "tank", "command": "FORWARD", "value": 60}` |
| `BACKWARD` | 0-255 | Move backward | `{"type": "tank", "command": "BACKWARD", "value": 50}` |
| `LEFT` | 0-255 | Turn left | `{"type": "tank", "command": "LEFT", "value": 45}` |
| `RIGHT` | 0-255 | Turn right | `{"type": "tank", "command": "RIGHT", "value": 45}` |
| `FORWARD_LEFT` | 0-255 | Diagonal movement | `{"type": "tank", "command": "FORWARD_LEFT", "value": 40}` |
| `FORWARD_RIGHT` | 0-255 | Diagonal movement | `{"type": "tank", "command": "FORWARD_RIGHT", "value": 40}` |
| `BACKWARD_LEFT` | 0-255 | Diagonal movement | `{"type": "tank", "command": "BACKWARD_LEFT", "value": 35}` |
| `BACKWARD_RIGHT` | 0-255 | Diagonal movement | `{"type": "tank", "command": "BACKWARD_RIGHT", "value": 35}` |
| `STOP` | 0 | Stop immediately | `{"type": "tank", "command": "STOP", "value": 0}` |
| `RESET` | 0 | Reset to joystick mode | `{"type": "tank", "command": "RESET", "value": 0}` |
| `KEEPALIVE` | 0 | Maintain connection (prevents auto-reboot) | `{"type": "tank", "command": "KEEPALIVE", "value": 0}` |

### Mecanum Movement Commands (NEW)
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

**Motor Speed Range**: -255 to 255 (negative = reverse)

**Advanced Capabilities**:
- ✅ **Pure Strafing**: Sideways movement while maintaining orientation
- ✅ **Omnidirectional Movement**: Any direction without rotation
- ✅ **Rotation + Translation**: Complex maneuvers like rotating while moving
- ✅ **Drift Movements**: Smooth curved paths with differential speeds

### Sensor Data (JSON)
Real-time sensor data automatically sent using ArduinoJson:
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

## 🧪 Test Scripts

### Primary Test Suite
**`test_serial_control.py`** - Tank and Mecanum JSON testing
- ✅ Tank JSON movement commands
- ✅ Mecanum wheel direct control
- ✅ All movement patterns validated

**`test_mecanum_protocol.py`** - Comprehensive mecanum testing
- ✅ Basic movements (forward, backward, strafe, rotate)
- ✅ Advanced movements (diagonal, complex maneuvers)
- ✅ Protocol compatibility testing
- ✅ Error handling validation

**`test_complete_robot.py`** - Full system integration testing
- ✅ JSON command format testing
- ✅ Sensor data reception and parsing
- ✅ Watchdog and auto-reboot verification
- ✅ Keep-alive system demonstration
- ✅ Error handling and graceful disconnection

### Usage
```bash
python3 test_serial_control.py      # Basic JSON protocol testing
python3 test_mecanum_protocol.py    # Advanced mecanum capabilities
python3 test_complete_robot.py      # Complete system validation
```

## 📋 Documentation

### Complete Protocol Documentation
**`SERIAL_PROTOCOL.md`** - Comprehensive JSON protocol specification
- JSON command format and examples
- Tank and mecanum movement patterns
- Response format documentation
- Auto-reboot system explanation
- Integration guidelines for multiplexer services
- Error handling and troubleshooting

**`MECANUM_PROTOCOL_IMPLEMENTATION.md`** - Implementation details
- Technical implementation specifics
- Memory usage and performance metrics
- Code architecture and design decisions
- Testing methodology and results

## 🎯 Ready for Integration

### For Multiplexer Service
- **JSON Protocol**: Structured, extensible command format
- **Mecanum Support**: Full omnidirectional movement capabilities
- **Direct Motor Control**: No lossy command conversion
- **Consistent Format**: All commands and responses use JSON
- **Error Handling**: Comprehensive validation and clear error messages

### For Remote Control Applications
- **Advanced Movements**: Pure strafing, rotation, complex maneuvers
- **Precise Control**: Individual motor speed control (-255 to +255)
- **Real-time Feedback**: JSON sensor data for obstacle avoidance
- **Flexible Commands**: Support both simple and complex movement patterns

### For AI Model Control
- **Structured Data**: JSON sensor input for AI decision making
- **Command Interface**: Clean JSON-based control
- **Safety System**: Built-in obstacle avoidance
- **State Management**: Clean resets between sessions

## 🔧 Hardware Configuration

### Arduino Giga R1 WiFi
- **Memory Usage**: 9.6% RAM, 7.4% Flash (optimized)
- **Performance**: Stable operation with ArduinoJson library

### Mecanum Wheels & Motors
- **4 Cytron MD motors**: PWM pins 2-3, 6-7, 4-5, 8-9
- **Mecanum wheels**: Enable omnidirectional movement
- **Movement patterns**: Both tank-style and direct motor control

### Sensors
- **4 ultrasonic sensors**: Front-left, front-right, rear-left, rear-right
- **Update rate**: 500ms automatic JSON transmission
- **Safety integration**: Real-time collision detection

### Joystick
- **4-direction control**: Pins 22-25 with INPUT_PULLUP
- **Diagonal support**: 8 total movement directions
- **Fallback mode**: Active when no serial commands

## 🚀 Success Metrics

- ✅ **100% reliable JSON protocol** - No legacy command support needed
- ✅ **Full mecanum capabilities** - Strafing, rotation, complex movements
- ✅ **ArduinoJson integration** - Robust parsing and generation
- ✅ **Advanced movement patterns** - 10+ movement types tested
- ✅ **Comprehensive test suite** - 3 specialized test scripts
- ✅ **Memory optimized** - 9.6% RAM, 7.4% Flash usage
- ✅ **Production ready** - Robust error handling and validation

## 📁 File Structure

```
firmware/
├── src/                              # Arduino source code
│   ├── main.cpp                      # Main setup and loop
│   ├── RobotController.cpp           # Main orchestration with JSON support
│   ├── MotorController.cpp           # Motor control with direct mecanum support
│   ├── SerialController.cpp          # JSON parsing with ArduinoJson
│   └── [other components]
├── include/                          # Header files
├── platformio.ini                    # PlatformIO config with ArduinoJson
├── SERIAL_PROTOCOL.md               # Complete JSON protocol docs
├── MECANUM_PROTOCOL_IMPLEMENTATION.md # Technical implementation guide
├── test_serial_control.py           # Basic JSON protocol testing
├── test_mecanum_protocol.py         # Advanced mecanum testing
└── test_complete_robot.py           # Complete system validation
```

## 🎊 MISSION ACCOMPLISHED!

The Arduino robot firmware development is **complete and production-ready**. The system now provides:

- **Modern JSON-based protocol** with ArduinoJson library
- **Full mecanum wheel capabilities** with direct motor control
- **Advanced movement patterns** including strafing and complex maneuvers
- **Robust error handling** with comprehensive validation
- **Optimized performance** with minimal memory footprint
- **Comprehensive testing** with specialized test suites
- **Production-ready documentation** for integration

**Ready for the next stage**: Multiplexer service integration with full mecanum wheel support! 🚀