# Remote Control Service for Mecanum Wheel Robot

A comprehensive remote control application for a 4-wheel Mecanum robot using PlayStation 5 DualSense controller. Features advanced motor smoothing, intelligent keepalive protocol, and dual-mode operation with 2D simulation and real robot control.

## 🎮 Features

- **PlayStation 5 DualSense Controller Support**: Full support for PS5 controller input with proper button mapping
- **Advanced Mecanum Wheel Kinematics**: Fixed rotation calculations for accurate omnidirectional movement
- **Dual Mode Operation**:
  - **Development Mode**: 2D pygame simulation for testing and development
  - **Production Mode**: Real robot control via Unix socket communication
- **Intelligent Motor Control**:
  - **Motor Speed Smoothing**: Reduces vibrations and jerky movements
  - **Motor Deadzone**: Eliminates ineffective low motor values
  - **Rate-Limited Communication**: 10Hz socket communication for optimal performance
  - **Intelligent Keepalive**: Protocol-compliant idle state management
- **Advanced Movement Patterns**:
  - Forward/backward movement
  - Strafe left/right movement (corrected direction mapping)
  - Rotation in place (fixed rotation direction)
  - Diagonal movement patterns
  - Drift movements
- **Safety Features**: Emergency stop, precision mode, speed boost
- **Drive Mode Switching**: Tank vs Mecanum mode toggle
- **Dockerized Deployment**: Production-ready containerized deployment with multiple configurations

## 🏗️ Architecture

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   PS5 Controller   │────│  Controller Handler │────│  Movement Calculator │
│    (pygame)        │    │   Fixed Mapping     │    │   Corrected Math    │
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
                           │ │ Rate Limited    │ │
                           │ │ + Keepalive     │ │
                           │ └─────────────────┘ │
                           └─────────────────────┘
                                       │
                           ┌─────────────────────┐
                           │  Motor Controller   │
                           │    Multiplexer      │
                           │ (Updated Protocol)  │
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

| Control | Function | Notes |
|---------|----------|-------|
| **Left Stick** | Robot movement | • **Mecanum**: Forward/back + strafe left/right<br/>• **Tank**: Forward/back only |
| **Right Stick X** | Robot rotation | • **Mecanum**: Left/right rotation<br/>• **Tank**: Controls rotation instead of left stick |
| **L1 Button** | **Drive Mode Switch** | Toggle between Tank ↔ Mecanum modes |
| **OPTIONS Button** | Precision mode toggle | Slower, more precise movement |
| **R1 Button** | Boost mode toggle | Faster movement |
| **L2 Trigger** | Precision mode (hold) | Variable precision based on trigger pressure |
| **R2 Trigger** | Speed boost (hold) | Variable speed boost based on trigger pressure |
| **Circle Button** | Emergency stop | Immediately stops all motors |
| **Square Button** | Resume from emergency stop | Restores normal operation |
| **Triangle Button** | Test movement patterns | Development mode only |
| **CREATE Button** | Toggle motor smoothing | Enable/disable vibration reduction |
| **TOUCHPAD Button** | Cycle motor deadzone | Adjust threshold: 0→10→15→20→25 |

**Note**: To quit the application, use **Ctrl+C** in the terminal.

### 🚗 Drive Modes

The remote control supports two driving modes that can be switched with the **L1 button**:

#### 🤖 Mecanum Mode (Default)
- **Full omnidirectional movement** - Move in any direction while independently rotating
- **Left stick**: Forward/backward + strafe left/right
- **Right stick X**: Rotation around robot center
- **Perfect for**: Complex maneuvers, precise positioning, sideways movement

#### 🚗 Tank Mode
- **Traditional tank-style driving** - Simplified control for familiar driving feel
- **Left stick Y**: Forward/backward movement
- **Right stick X**: Rotation (turn left/right)
- **Left stick X**: Ignored in tank mode
- **Perfect for**: Simple navigation, familiar driving feel

**Current mode is displayed in log messages when switching.**

## ⚡ Advanced Motor Control Features

### 🎛️ Motor Speed Smoothing
- **Purpose**: Eliminates violent movements and structural vibrations
- **Method**: Exponential smoothing (low-pass filter) with configurable factor
- **Default**: 30% smoothing factor for optimal balance of responsiveness and smoothness
- **Control**: Toggle with **CREATE button**

### 🚫 Motor Deadzone
- **Purpose**: Prevents sending ineffective low motor values that cause stalling
- **Threshold**: Values below ±15 (out of 255) are automatically set to 0
- **Control**: Cycle threshold with **TOUCHPAD button** (0→10→15→20→25)
- **Benefit**: Cleaner movement, reduced mechanical stress

### 📡 Intelligent Communication
- **Rate Limiting**: Commands sent at maximum 10Hz (100ms intervals) for optimal performance
- **Intelligent Keepalive**: When idle, sends keepalive packets instead of zero commands
- **Protocol Compliance**: Follows updated multiplexer protocol requirements
- **Benefit**: Reduced network traffic, cleaner multiplexer logs

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
  --log-level {DEBUG,DATA,INFO,WARNING,ERROR}  Logging level
```

### Special Log Levels

- **DATA**: Shows only socket communication frames (clean protocol debugging)
- **DEBUG**: Full verbose logging including controller events and calculations

### Environment Variables

```bash
# Production mode configuration
export MODE=production
export CONTROLLER_DEVICE=/dev/input/js0
export SOCKET_PATH=/var/eraccoon/multiplexer/socket/motor_proxy_service.sock
export LOG_LEVEL=INFO
```

## 🔌 Communication Protocol

The remote control communicates with the updated multiplexer using different protocols based on the drive mode:

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

### Tank Mode Protocol
```json
{
  "type": "tank_command",
  "command": "FORWARD|BACKWARD|LEFT|RIGHT|STOP",
  "value": 0-255
}
```

### Intelligent Keepalive Protocol
- **Active State**: When robot is moving, motor commands act as keepalives
- **Idle State**: When robot is stopped, explicit keepalive packets sent every 2.5 seconds
- **No Spam**: Zero motor commands are never sent - keepalive handles connection maintenance

## 🤖 Mecanum Wheel Movement (Fixed Calculations)

The robot supports various movement patterns with **corrected rotation mathematics**:

### Fixed Movement Calculations

```
Motor Layout:        Corrected Formulas:
LF ---- RF          LF = forward - strafe + rotation
|  \  /  |          LR = forward + strafe + rotation
|   \/   |          RF = forward + strafe - rotation
|   /\   |          RR = forward - strafe - rotation
|  /  \  |
LR ---- RR
```

### Movement Patterns
- **Forward/Backward**: All wheels rotate in same direction
- **Strafe Left/Right**: Diagonal wheels work together (fixed direction mapping)
- **Rotation**: Left and right sides rotate in opposite directions (fixed rotation direction)
- **Diagonal Movement**: Complex combinations for omnidirectional movement

## 🐳 Docker Deployment

### Building Images

```bash
# Build for ARM64 (Jetson Nano)
./docker_build.sh -a arm64 -t

# Build and save image locally
./docker_build.sh -a arm64 -s

# Build multi-architecture image
./docker_build.sh -m

# Build with custom registry and tag
./docker_build.sh -a arm64 -r myregistry.com -n my-robot --tag v2.0.0
```

### Deployment Types

```bash
# Quick deployment (production mode)
./deploy_arm64.sh <ROBOT_IP> jetson deploy quick

# Production deployment with full logging
./deploy_arm64.sh <ROBOT_IP> jetson deploy production

# Debug deployment with verbose logging
./deploy_arm64.sh <ROBOT_IP> jetson deploy debug

# Data deployment with socket communication logging only
./deploy_arm64.sh <ROBOT_IP> jetson deploy data

# Secure deployment with limited privileges
./deploy_arm64.sh <ROBOT_IP> jetson deploy secure
```

### Management Commands

```bash
# Check deployment status
./deploy_arm64.sh <ROBOT_IP> jetson status

# View container logs
./deploy_arm64.sh <ROBOT_IP> jetson logs

# Stop service
./deploy_arm64.sh <ROBOT_IP> jetson stop

# Remove container
./deploy_arm64.sh <ROBOT_IP> jetson delete

# Complete cleanup
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

**Wrong movement directions:**
- ✅ **Fixed**: Controller mapping has been corrected
- **Left stick left** → Robot strafes left
- **Right stick left** → Robot rotates counterclockwise
- If still incorrect, try adjusting controller deadzone with **TOUCHPAD button**

**Robot movements too violent/jerky:**
- ✅ **Fixed**: Motor smoothing implemented
- Press **CREATE button** to toggle smoothing on/off
- Adjust deadzone with **TOUCHPAD button** (try values 15-25)
- Use **L2 trigger** for precision mode

### Socket Connection Issues

**Cannot connect to multiplexer:**
```bash
# Check if multiplexer is running
docker ps | grep multiplexer

# Check socket exists
ls -la /var/eraccoon/multiplexer/socket/motor_proxy_service.sock

# Check multiplexer logs
docker logs -f multiplexer
```

**Connection keeps dropping:**
- ✅ **Fixed**: Intelligent keepalive implemented
- Check multiplexer logs for client disconnection messages
- Verify socket path matches multiplexer configuration
- Try **data** deployment mode for clean protocol debugging:
  ```bash
  ./deploy_arm64.sh <ROBOT_IP> jetson deploy data
  ```

**Zero command spam in multiplexer logs:**
- ✅ **Fixed**: Keepalive protocol implemented
- Old issue: Robot sent zero motor commands continuously
- New behavior: Only sends commands when moving, keepalive when idle

### Motor Control Issues

**Motors not responding to small movements:**
- ✅ **Fixed**: Motor deadzone implemented
- Press **TOUCHPAD button** to cycle deadzone threshold
- Try lower values (0-10) for more sensitive motors
- Higher values (20-25) for motors that need more power to start

**Robot doesn't stop smoothly:**
- ✅ **Fixed**: Motor smoothing handles transitions
- Press **CREATE button** to ensure smoothing is enabled
- Check that emergency stop (**Circle button**) works immediately
- Resume with **Square button**

### Drive Mode Issues

**Drive mode not switching:**
- ✅ **Fixed**: Button mapping corrected
- Press **L1 button** (not OPTIONS) to switch modes
- Current mode displayed in logs when switching
- **Tank mode**: Left stick Y + Right stick X for rotation
- **Mecanum mode**: Left stick XY + Right stick X for rotation

### Debugging and Logging

**Enable clean protocol debugging:**
```bash
# Use DATA log level to see only socket communication
python main.py --mode production --log-level DATA

# Or deploy in data mode
./deploy_arm64.sh <ROBOT_IP> jetson deploy data
```

**Enable verbose debugging:**
```bash
# Full debug logging
python main.py --mode development --log-level DEBUG

# Or deploy in debug mode
./deploy_arm64.sh <ROBOT_IP> jetson deploy debug
```

**Check motor smoothing status:**
- Look for log messages: `🎛️ Motor smoothing enabled/disabled`
- Toggle with **CREATE button** to test difference
- Look for: `⚡ Motor deadzone threshold: ±X`

### Bluetooth Connection Issues (macOS)

**PS5 Controller connection problems:**
```bash
# Reset Bluetooth connection
# 1. Unpair controller from System Preferences
# 2. Hold PS + Create buttons for 5 seconds to reset controller
# 3. Re-pair via Bluetooth settings
# 4. Test with USB cable first

# Check controller battery
# Low battery can cause connection drops
```

### Performance Issues

**High CPU usage:**
- ✅ **Optimized**: Rate limiting and intelligent communication implemented
- Commands limited to 10Hz (100ms intervals)
- No unnecessary zero-command spam
- Smoothing reduces calculation overhead

**Network congestion:**
- ✅ **Fixed**: Intelligent keepalive reduces traffic
- Use **data** deployment mode to monitor actual traffic:
  ```bash
  ./deploy_arm64.sh <ROBOT_IP> jetson logs | grep "DATA"
  ```

## 📊 Current System Status

### ✅ **Implemented & Working:**
- ✅ **Controller Input**: Fixed direction mapping for strafe and rotation
- ✅ **Motor Smoothing**: Eliminates violent movements and vibrations
- ✅ **Motor Deadzone**: Prevents ineffective low motor values
- ✅ **Intelligent Keepalive**: Protocol-compliant communication
- ✅ **Rate Limiting**: 10Hz socket communication
- ✅ **Drive Mode Switching**: Tank ↔ Mecanum with L1 button
- ✅ **Multi-Platform Support**: macOS development, Linux production
- ✅ **Docker Deployment**: Multiple deployment configurations
- ✅ **Logging Levels**: DATA level for clean protocol debugging

### 🎮 **Controller Features:**
- ✅ **All buttons mapped** with proper functionality
- ✅ **Variable triggers** for speed and precision control
- ✅ **Emergency stop** with immediate response
- ✅ **Mode switching** with visual feedback in logs
- ✅ **Real-time configuration** of smoothing and deadzone

### 🔌 **Protocol Compliance:**
- ✅ **Multiplexer Integration**: Updated socket path structure
- ✅ **Intelligent Communication**: No zero-command spam
- ✅ **Proper Keepalive**: Maintains connection without overhead
- ✅ **Rate Limiting**: Optimal 10Hz communication frequency

The system is now production-ready with robust motor control, smooth movement, and efficient communication protocols!