# Eraccoon Robot Platform 🤖

![Robot Platform](doc/img/IMG_1099.jpg)

[Vibe coded](https://en.wikipedia.org/wiki/Vibe_coding) with [cursor](https://www.cursor.com/) and [claude-4-sonnet](https://chat.chatbot.app/claude)

A sophisticated DIY robotics platform featuring omnidirectional movement with Mecanum wheels, Arduino-based motor control, and Nvidia Jetson Nano onboard computer. This multi-repository project demonstrates modern robotics software architecture with robust communication protocols, remote control capabilities, and production-ready deployment.

## 🏗️ System Architecture

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   Remote Control    │    │   Jetson Nano       │    │   Arduino Giga      │
│  (PS5 Controller)   │────│   Multiplexer       │────│  Motor Controller   │
│  JSON Protocol      │    │  Unix Socket API    │    │  JSON Protocol      │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
                                       │                          │
                           ┌─────────────────────┐    ┌─────────────────────┐
                           │  Multiple Clients   │    │   4x Mecanum        │
                           │  Priority Control   │    │   Wheels + Motors   │
                           │  Sensor Streaming   │    │   Ultrasonic        │
                           │  Rate Limiting      │    │   Sensors           │
                           └─────────────────────┘    └─────────────────────┘
```

## 🎯 Key Features

### 🚗 Advanced Movement System
- **Mecanum Wheels**: True omnidirectional movement - move in any direction while independently rotating
- **Dual Control Modes**: Tank-style (traditional) and Mecanum (advanced) driving modes
- **Precision Control**: Variable speed control, deadzone filtering, and motor smoothing
- **Complex Maneuvers**: Strafing, rotation in place, diagonal movement, and drift patterns

### 🎮 Remote Control
- **PlayStation 5 DualSense Controller**: Full wireless control with intelligent button mapping
- **Multi-mode Operation**: Development simulation and production robot control
- **Real-time Response**: Low-latency control optimized for robotics applications
- **Safety Features**: Emergency stop, precision mode, and speed boost controls

### 🔌 Robust Communication
- **JSON-based Protocol**: Modern, structured communication between all components
- **Auto-reconnection**: Handles device disconnections and Arduino reboots gracefully
- **Multi-client Support**: Multiple applications can connect simultaneously with priority arbitration
- **Intelligent Keepalive**: Protocol-compliant idle state management

### 🛡️ Production Ready
- **Docker Deployment**: Multi-architecture containers for ARM64/AMD64
- **Comprehensive Logging**: Detailed system monitoring and diagnostics
- **Error Recovery**: Automatic reboot handling and connection management
- **Safety Systems**: Obstacle detection with 4 ultrasonic sensors

## 📦 Hardware Components

### Core Platform
- **Arduino Giga R1 WiFi**: Main motor controller and sensor interface
- **Nvidia Jetson Nano**: Onboard computer for advanced processing and connectivity
- **4x Cytron MD Motors**: PWM-controlled motors with individual speed control
- **140mm Mecanum Wheels (70A durometer)**: Omnidirectional movement capability

### Sensors & Interface
- **4x Ultrasonic Sensors**: 360-degree obstacle detection (front-left, front-right, rear-left, rear-right)
- **I2C LCD Display**: Real-time status and diagnostics
- **Onboard Joystick**: Fallback control when no external controller connected
- **PlayStation 5 DualSense Controller**: Primary remote control interface

### Power & Safety
- Battery capacity monitoring (planned)
- Safety shutdown system (planned)
- Emergency stop functionality

## 🚀 Getting Started

### 1. Arduino Firmware Setup
Navigate to `arduino/firmware/` for complete setup instructions:
- Flash the JSON-based motor control firmware
- Configure mecanum wheel kinematics
- Test basic movement and sensor functionality

**Quick Test**:
```bash
cd arduino/firmware
python3 test_complete_robot.py
```

### 2. Jetson Multiplexer Service
Deploy the motor controller proxy on the Jetson Nano:
```bash
cd jetson/multiplexer
./docker_build.sh arm64
./deploy_arm64.sh <JETSON_IP> jetson deploy production
```

### 3. Remote Control Setup
Set up PS5 controller remote control:
```bash
cd jetson/remote
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py --mode development  # For simulation
python main.py --mode production   # For real robot
```

## 🎮 Operation Modes

### Development Mode
- **2D Simulation**: Test control algorithms without hardware
- **Real-time Visualization**: See robot movement patterns and sensor data
- **Safe Testing**: Develop and debug control logic in simulation

### Production Mode
- **Full Robot Control**: Direct control of physical robot
- **Real-time Sensor Feedback**: Live obstacle detection and avoidance
- **Multi-client Architecture**: Support for simultaneous control applications

## 🔧 Control Interface

### PS5 Controller Mapping
| Control | Function | Notes |
|---------|----------|-------|
| **Left Stick** | Movement | Forward/back + strafe (Mecanum mode) |
| **Right Stick X** | Rotation | Independent rotation control |
| **L1** | Mode Switch | Toggle Tank ↔ Mecanum modes |
| **L2/R2** | Precision/Boost | Variable speed control |
| **Circle** | Emergency Stop | Immediate motor shutdown |
| **Options** | Precision Mode | Toggle fine control |

### Movement Capabilities
- **Forward/Backward**: Traditional movement
- **Strafe Left/Right**: Sideways movement without rotation
- **Rotate in Place**: Spin without translation
- **Diagonal Movement**: 45-degree movement patterns
- **Complex Maneuvers**: Simultaneous rotation and translation

## 📊 Technical Specifications

### Performance
- **Motor Speed Range**: -255 to +255 (full bidirectional control)
- **Communication Rate**: 10Hz optimal for real-time control
- **Memory Usage**: 9.6% RAM, 7.4% Flash on Arduino
- **Response Latency**: <100ms end-to-end control

### Protocol Details
- **Command Format**: JSON with structured parameter validation
- **Sensor Data**: Real-time JSON streaming at 500ms intervals
- **Connection Management**: Auto-reboot detection and reconnection
- **Error Handling**: Comprehensive validation and recovery

## 🧪 Testing & Development

### Comprehensive Test Suite
Each component includes specialized test scripts:

**Arduino Firmware**:
- `test_serial_control.py` - Basic JSON protocol testing
- `test_mecanum_protocol.py` - Advanced movement validation
- `test_complete_robot.py` - Full system integration

**Multiplexer Service**:
- Multi-client connection testing
- Rate limiting and priority validation
- Keepalive and reconnection testing

**Remote Control**:
- Controller input mapping validation
- Simulation vs production mode testing
- Movement pattern verification

### Client Examples
- Basic motor control with keepalive management
- Real-time sensor monitoring
- Advanced mecanum movement demonstrations
- Rate limiting and performance testing

## 📁 Repository Structure

```
eraccoon/
├── arduino/
│   └── firmware/           # Arduino motor controller firmware
├── jetson/
│   ├── multiplexer/        # Motor controller proxy service
│   └── remote/             # PS5 controller remote control
├── doc/
│   └── img/                # Documentation images
└── README.md               # This file
```

## 🔮 Future Enhancements

### Planned Features
- **Intel RealSense Integration**: 3D depth sensing and computer vision
- **Battery Management**: Capacity monitoring and safety shutdown
- **Advanced Sensors**: Additional distance sensors for enhanced navigation
- **Machine Learning**: AI-powered autonomous navigation
- **Kubernetes Deployment**: GPU-enabled cluster support for ML workloads

### Development Roadmap
- Autonomous navigation capabilities
- Computer vision integration
- Advanced sensor fusion
- Mobile app control interface
- Voice command integration

## 📚 Documentation

Each component includes comprehensive documentation:
- **Arduino Firmware**: Complete protocol specification and implementation details
- **Multiplexer Service**: Architecture documentation and deployment guides
- **Remote Control**: Controller mapping and movement pattern documentation

## 🤝 Contributing

This is a hobby robotics project demonstrating modern software architecture in robotics. The modular design allows for easy component replacement and enhancement.

## 📄 License

This project is a personal DIY robotics platform created for educational and hobbyist purposes.

---

**Status**: ✅ Production Ready - All core systems operational and tested