# Remote Control Service for Mecanum Wheel Robot

A comprehensive remote control application for a 4-wheel Mecanum robot using PlayStation 5 DualSense controller. Supports both development mode with 2D simulation and production mode with real robot control via socket communication.

## 🎮 Features

- **PlayStation 5 DualSense Controller Support**: Full support for PS5 controller input via pygame
- **Mecanum Wheel Kinematics**: Advanced movement calculations supporting omnidirectional movement
- **Dual Mode Operation**:
  - **Development Mode**: 2D pygame simulation for testing and development
  - **Production Mode**: Real robot control via Unix socket communication
- **Advanced Movement Patterns**:
  - Forward/backward movement
  - Strafe left/right movement
  - Rotation in place
  - Diagonal movement patterns
  - Drift movements
- **Safety Features**: Emergency stop, precision mode, speed boost
- **Dockerized Deployment**: Production-ready containerized deployment

## 🏗️ Architecture

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   PS5 Controller   │────│  Controller Handler │────│  Movement Calculator │
│    (pygame)        │    │                     │    │   (Mecanum Math)    │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
                                                                │
                           ┌─────────────────────┐              │
                           │    Development      │              │
                           │      Mode           │              │
                           │ ┌─────────────────┐ │              │
                           │ │ 2D Robot        │ │◄─────────────┘
                           │ │ Simulator       │ │
                           │ │ (pygame)        │ │
                           │ └─────────────────┘ │
                           └─────────────────────┘
                                                                │
                           ┌─────────────────────┐              │
                           │   Production Mode   │              │
                           │ ┌─────────────────┐ │              │
                           │ │ Socket Client   │ │◄─────────────┘
                           │ │ (Unix Socket)   │ │
                           │ └─────────────────┘ │
                           └─────────────────────┘
                                       │
                           ┌─────────────────────┐
                           │  Motor Controller   │
                           │    Multiplexer      │
                           │                     │
                           └─────────────────────┘
                                       │
                           ┌─────────────────────┐
                           │   Mecanum Robot     │
                           │  (4 Motor Wheels)   │
                           └─────────────────────┘
```

## 🛠️ Requirements

### Development Mode (macOS)
- Python 3.8+
- pygame (for controller input and simulation)
- PS5 DualSense controller (USB or Bluetooth)

### Production Mode (Robot/Linux)
- Docker and Docker Buildx
- PS5 DualSense controller connected as `/dev/input/js0`
- Motor Controller Multiplexer service running

## 🚀 Quick Start

### Development Mode Setup

1. **Clone and setup the project:**
```bash
cd /Users/kmarek/Development/eraccoon/jetson/remote
python -m venv .venv
source .venv/bin/activate  # On macOS/Linux
pip install -r requirements.txt
```

2. **Connect PS5 Controller:**
   - USB: Connect via USB cable
   - Bluetooth: Pair controller with your macOS system

3. **Run in development mode:**
```bash
python main.py --mode development
```

4. **Optional parameters:**
```bash
# Custom simulation window size
python main.py --mode development --simulation-width 1024 --simulation-height 768

# Enable debug logging
python main.py --mode development --log-level DEBUG

# Custom controller device (if not detected automatically)
python main.py --mode development --controller-device /dev/input/js1
```

### Production Mode Setup

1. **Build Docker image:**
```bash
./docker_build.sh arm64
```

2. **Deploy to robot:**
```bash
./deploy_arm64.sh <ROBOT_IP> jetson deploy quick
```

3. **Alternative deployment types:**
```bash
# Production deployment with logging
./deploy_arm64.sh <ROBOT_IP> jetson deploy production

# Debug deployment with verbose logging
./deploy_arm64.sh <ROBOT_IP> jetson deploy debug

# Secure deployment with limited privileges
./deploy_arm64.sh <ROBOT_IP> jetson deploy secure
```

## 🎮 Controller Mapping

| Control | Function |
|---------|----------|
| **Left Stick** | Robot movement (forward/back, strafe left/right in Mecanum mode; forward/back + rotation in Tank mode) |
| **Right Stick X** | Robot rotation (left/right, Mecanum mode only) |
| **R2 Trigger** | Speed boost mode |
| **L2 Trigger** | Precision mode (slower, more precise) |
| **Circle Button** | Emergency stop |
| **Square Button** | Resume from emergency stop |
| **Triangle Button** | Test movement patterns (development mode only) |
| **L1** | Precision mode toggle |
| **R1** | Boost mode toggle |
| **Options Button** | **Drive Mode Switch** - Toggle between Tank and Mecanum modes |

**Note**: To quit the application, use **Ctrl+C** in the terminal.

### 🚗 Drive Modes

The remote control supports two driving modes:

#### 🤖 Mecanum Mode (Default)
- **Full omnidirectional movement** - Move in any direction while independently rotating
- **Left stick**: Forward/backward + strafe left/right
- **Right stick X**: Rotation around robot center
- **Perfect for**: Complex maneuvers, precise positioning, sideways movement

#### 🚗 Tank Mode
- **Traditional tank-style driving** - Simplified control using only left stick
- **Left stick Y**: Forward/backward movement
- **Left stick X**: Rotation (turn left/right)
- **Right stick**: Ignored
- **Perfect for**: Simple navigation, familiar driving feel

**Switch modes**: Press **L1** button to toggle between modes. Current mode is displayed in log messages.

## 🔧 Configuration

### Command Line Options

```bash
python main.py [OPTIONS]

Options:
  --mode {development,production}   Operation mode (default: development)
  --controller-device PATH          Controller device path (default: /dev/input/js0)
  --socket-path PATH               Unix socket path for production mode
  --simulation-width INT           Simulation window width (development mode)
  --simulation-height INT          Simulation window height (development mode)
  --log-level {DEBUG,INFO,WARNING,ERROR}  Logging level
```

### Environment Variables

```bash
# Production mode configuration
export MODE=production
export CONTROLLER_DEVICE=/dev/input/js0
export SOCKET_PATH=/tmp/motor-proxy/motor_controller.sock
export LOG_LEVEL=INFO
```

## 🔌 Communication Protocol

The remote control communicates with the updated multiplexer using different protocols based on the drive mode:

### Tank Mode Protocol
```json
{
  "type": "tank_command",
  "command": "FORWARD|BACKWARD|LEFT|RIGHT|STOP",
  "value": 0-255
}
```

### Mecanum Mode Protocol
```json
{
  "type": "mecanum_command",
  "motors": {
    "left_front": -255,   // Individual motor speeds
    "left_rear": 127,     // Range: -255 to 255
    "right_front": 200,   // Negative = reverse
    "right_rear": -100    // Positive = forward
  }
}
```

This allows the robot to utilize either simple tank-style movements or complex omnidirectional Mecanum capabilities based on the selected drive mode.

## 🤖 Mecanum Wheel Movement Patterns

The robot supports various movement patterns unique to Mecanum wheels:

### Basic Movements
- **Forward/Backward**: All wheels rotate in same direction
- **Strafe Left/Right**: Diagonal wheels work together
- **Rotation**: Left and right sides rotate in opposite directions

### Advanced Movements
- **Diagonal Movement**: Only two wheels active (forward-left, forward-right, etc.)
- **Drift Movement**: Rear wheels only for sideways sliding
- **Circular Paths**: Differential speeds for curved movement

### Movement Calculations

Based on [SunFounder Zeus Car documentation](https://docs.sunfounder.com/projects/zeus-car-dev/en/latest/scratch/sc4_move_wheels.html):

```
Motor Layout:
LF ---- RF
|  \  /  |
|   \/   |
|   /\   |
|  /  \  |
LR ---- RR

Calculations:
LF = forward - strafe - rotation
LR = forward + strafe - rotation
RF = forward + strafe + rotation
RR = forward - strafe + rotation
```

## 🐳 Docker Deployment

### Building Images

```bash
# Build for ARM64 (Jetson Nano)
./docker_build.sh arm64

# Build for x86_64 (testing)
./docker_build.sh amd64

# Build for both architectures
./docker_build.sh both

# Build with custom version
./docker_build.sh arm64 --version 1.1.0

# Build debug version
./docker_build.sh arm64 --debug
```

### Deployment Management

```bash
# Deploy service
./deploy_arm64.sh <ROBOT_IP> jetson deploy quick

# Check status
./deploy_arm64.sh <ROBOT_IP> jetson status

# View logs
./deploy_arm64.sh <ROBOT_IP> jetson logs

# Stop service
./deploy_arm64.sh <ROBOT_IP> jetson stop

# Clean up completely
./deploy_arm64.sh <ROBOT_IP> jetson clean
```

## 🔍 Troubleshooting

### Controller Issues

**Controller not detected:**
```bash
# Check available controllers
ls -la /dev/input/js*

# Test controller manually
jstest /dev/input/js0

# Use specific device
python main.py --controller-device /dev/input/js1
```

**Bluetooth connection issues:**
```bash
# On macOS, check Bluetooth settings
# Make sure controller is properly paired
# Try USB connection first
```

### Socket Connection Issues

**Cannot connect to multiplexer:**
```bash
# Check if multiplexer is running
docker ps | grep motor-proxy

# Check socket exists
ls -la /tmp/motor-proxy/motor_controller.sock

# Check logs
docker logs motor-proxy
```

### Development Mode Issues

**Pygame display issues on macOS:**
```bash
# Install pygame with proper dependencies
pip install pygame>=2.5.0

# For headless testing, set SDL driver
export SDL_VIDEODRIVER=dummy
```

### Production Mode Issues

**Permission denied accessing controller:**
```bash
# Add user to input group
sudo usermod -a -G input $USER

# Or run with appropriate permissions
sudo docker run ...
```

## 📁 Project Structure

```
remote/
├── main.py                 # Main application entry point
├── requirements.txt        # Python dependencies
├── Dockerfile             # Production container definition
├── docker_build.sh        # Docker build script
├── deploy_arm64.sh         # Deployment script
├── README.md              # This file
├── .gitignore             # Git ignore patterns
└── src/                   # Source code modules
    ├── __init__.py
    ├── controller_handler.py      # PS5 controller interface
    ├── mecanum_calculator.py      # Movement calculations
    ├── robot_simulator.py         # 2D simulation (development)
    ├── socket_client.py           # Unix socket communication
    └── remote_control_service.py  # Main service coordinator
```

## 🔗 Dependencies

This project integrates with:
- **Motor Controller Multiplexer**: `/Users/kmarek/Development/eraccoon/jetson/multiplexer`
- **SunFounder Zeus Car**: Movement patterns and kinematics
- **PlayStation 5 DualSense**: Controller input handling

## 📜 License

This project is part of the Eraccoon Jetson robotics framework.

## 🤝 Contributing

1. Test changes in development mode first
2. Ensure compatibility with existing multiplexer service
3. Update documentation for new features
4. Test deployment on target hardware

## 📞 Support

For issues and questions:
1. Check troubleshooting section above
2. Review logs in development/production mode
3. Test with multiplexer service examples
4. Verify hardware connections and permissions