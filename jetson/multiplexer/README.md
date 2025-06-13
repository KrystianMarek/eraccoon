# Motor Controller Proxy/Multiplexer

A robust proxy/multiplexer service that exposes Arduino motor control via Unix socket interface. Designed for deployment on Nvidia Jetson Nano with support for multiple concurrent clients, command arbitration, and real-time sensor data streaming.

## 🏗️ Architecture

```
┌─────────────────┐    Unix Socket    ┌─────────────────┐    Serial    ┌─────────────┐
│   Client Apps   │◄─────────────────►│ Proxy/Multiplexer│◄────────────►│  Arduino    │
│                 │    JSON Protocol  │     Service     │   Commands   │  Robot      │
└─────────────────┘                   └─────────────────┘              └─────────────┘
        ▲                                       │
        │                              ┌───────▼───────┐
        │                              │ • Connection  │
        └──────────────────────────────┤   Management  │
                                       │ • Priority    │
                                       │   Control     │
                                       │ • Status      │
                                       │   Broadcasting│
                                       │ • Auto-Reboot │
                                       │   Handling    │
                                       └───────────────┘
```

## 🚀 Features

- **Unix Socket Interface**: Clean IPC mechanism for local applications
- **Multi-Client Support**: Handle multiple concurrent connections with priority-based arbitration
- **Real-time Sensor Data**: Live streaming of Arduino sensor readings (100ms intervals)
- **Robust Connection Management**: Auto-reconnection, dynamic port detection, and Arduino reboot handling
- **Non-blocking Socket Operations**: Prevents client issues from affecting Arduino communication
- **Docker Support**: Multi-architecture builds for ARM64/AMD64 with comprehensive deployment options
- **Comprehensive Logging**: Detailed logging with configurable levels (DEBUG, INFO, WARNING, ERROR)
- **Health Monitoring**: Built-in health checks, statistics, and connection status
- **Arduino Watchdog Integration**: Handles Arduino's 5-second watchdog system with automatic keepalive

## 📋 Requirements

### Hardware
- Arduino with motor controller firmware (see `firmware/` directory)
- USB connection between host and Arduino
- Target deployment: Nvidia Jetson Nano (ARM64)
- **Note**: Arduino auto-reboots when connections are made, causing device re-enumeration (e.g., `/dev/ttyACM0` → `/dev/ttyACM1`)

### Software
- Python 3.7+
- Docker (for containerized deployment)
- Linux/Unix environment
- Required Python packages: `pyserial`, `dataclasses` (Python 3.6)

## 🛠️ Installation

### Development Setup

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd multiplexer
   pip install -r requirements.txt
   ```

2. **Run locally**:
   ```bash
   python main.py  # Auto-detects Arduino port
   # Or specify a port:
   # python main.py --serial-port /dev/ttyACM0 --log-level DEBUG
   ```

### Docker Deployment

#### Quick Start (Local Development)

```bash
# Build for your architecture
./docker_build.sh

# Run with auto-detection (recommended)
docker run -d \
  --name motor-proxy \
  --privileged \
  -v /dev:/dev \
  -v /tmp/motor-proxy:/tmp/motor-proxy \
  motor-controller-proxy:latest
```

#### Production Deployment (Jetson Nano)

1. **Build for ARM64 architecture**:
   ```bash
   # Build, save, and test for ARM64
   ./docker_build.sh -a arm64 -s -t
   ```

2. **Deploy to Jetson Nano**:
   ```bash
   # Quick deployment
   ./deploy_arm64.sh $ER_JETSON_IP $ER_SSH_USER deploy quick

   # Production deployment with logging
   ./deploy_arm64.sh $ER_JETSON_IP $ER_SSH_USER deploy production

   # Debug deployment with verbose logging
   ./deploy_arm64.sh $ER_JETSON_IP $ER_SSH_USER deploy debug

   # Secure deployment with specific device access
   ./deploy_arm64.sh $ER_JETSON_IP $ER_SSH_USER deploy secure
   ```

3. **Monitor deployment**:
   ```bash
   # Check status
   ./deploy_arm64.sh $ER_JETSON_IP $ER_SSH_USER status

   # View logs
   ./deploy_arm64.sh $ER_JETSON_IP $ER_SSH_USER logs

   # Stop service
   ./deploy_arm64.sh $ER_JETSON_IP $ER_SSH_USER stop
   ```

## 🎮 Usage

### Example Clients

The project includes two example clients optimized for different use cases:

#### 1. Monitor Sensors (`examples/monitor_sensors.py`)
**Purpose**: Full data monitoring - shows ALL socket data
```bash
# Shows real-time sensor data, Arduino messages, command responses
python examples/monitor_sensors.py
```
**Output**: Real-time sensor readings, Arduino status, command responses, connection events

#### 2. Client Example (`examples/client_example.py`)
**Purpose**: Clean command interface - focused on motor control
```bash
# Interactive motor control with minimal logging
python examples/client_example.py

# Automated demo
python examples/client_example.py auto
```
**Output**: Only command responses and important status messages (no sensor spam)

### Basic Control

```python
from examples.client_example import MotorProxyClient

# Connect to proxy
client = MotorProxyClient('/tmp/motor-proxy/motor_controller.sock')
client.connect()

# Control robot
client.move_forward(60)    # Move forward at speed 60
client.turn_left(40)       # Turn left at speed 40
client.stop()              # Stop all movement
client.reset()             # Return to joystick control

# Get status and sensor data
client.get_status()        # Server and Arduino status
client.get_sensor_data()   # Current sensor readings

client.disconnect()
```

### Command Line Options

```bash
python main.py --help

Options:
  --serial-port PORT    Arduino serial port (default: auto-detect)
  --baud-rate RATE      Serial baud rate (default: 115200)
  --socket-path PATH    Unix socket path (default: /tmp/motor-proxy/motor_controller.sock)
  --log-level LEVEL     Logging level (DEBUG, INFO, WARNING, ERROR)
  --log-file FILE       Log to file (optional)
  --daemon              Run as daemon
```

### Environment Variables (Docker)

| Variable | Default | Description |
|----------|---------|-------------|
| `SERIAL_PORT` | `""` (auto-detect) | Arduino serial port |
| `BAUD_RATE` | `115200` | Serial communication baud rate |
| `SOCKET_PATH` | `/tmp/motor-proxy/motor_controller.sock` | Unix socket path |
| `LOG_LEVEL` | `INFO` | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FILE` | | Optional log file path |
| `DAEMON_MODE` | `false` | Run as daemon |

## 📡 Socket Protocol Specification

### Connection Process

1. **Client connects** to Unix socket at `/tmp/motor-proxy/motor_controller.sock`
2. **Server sends welcome message** with client ID and server version
3. **Server sends initial status** with Arduino state and connection info
4. **Client can send commands** and receives responses
5. **Server broadcasts** sensor data and Arduino messages to all connected clients

### Message Format

All messages are JSON objects terminated with `\n`:
```
{"type": "command", "data": {...}}\n
```

### Client → Server Messages

#### Motor Commands
```json
{
  "type": "motor_command",
  "command": "FORWARD|BACKWARD|LEFT|RIGHT|STOP|RESET|FORWARD_LEFT|FORWARD_RIGHT|BACKWARD_LEFT|BACKWARD_RIGHT",
  "value": 0-255
}
```

**Command Types:**
- `FORWARD` / `BACKWARD`: Linear movement
- `LEFT` / `RIGHT`: Turning movement
- `FORWARD_LEFT` / `FORWARD_RIGHT`: Diagonal movement
- `BACKWARD_LEFT` / `BACKWARD_RIGHT`: Reverse diagonal movement
- `STOP`: Stop all motors
- `RESET`: Return control to Arduino joystick

**Value Range**: 0-255 (motor speed/power)

#### System Commands
```json
{
  "type": "ping"
}
```
```json
{
  "type": "get_status"
}
```
```json
{
  "type": "get_sensor_data"
}
```
```json
{
  "type": "set_priority",
  "priority": 1-100
}
```

**Priority System**: Lower numbers = higher priority. Only the highest priority client can control motors.

### Server → Client Messages

#### Welcome Message
```json
{
  "type": "welcome",
  "client_id": "client_12345",
  "server_version": "1.0.0",
  "timestamp": 1640995200.0
}
```

#### Status Updates
```json
{
  "type": "status",
  "arduino_state": "connected|disconnected|error",
  "arduino_connected": true,
  "arduino_current_port": "/dev/ttyACM0",
  "arduino_preferred_port": null,
  "active_client": "client_12345",
  "total_clients": 2,
  "clients": [
    {
      "client_id": "client_12345",
      "address": "",
      "state": "connected",
      "last_activity": 1640995200.0,
      "priority": 10
    }
  ],
  "stats": {
    "start_time": 1640995000.0,
    "total_connections": 5,
    "commands_processed": 42,
    "errors": 0
  },
  "timestamp": 1640995200.0
}
```

#### Sensor Data (Broadcast every 100ms)
```json
{
  "type": "sensor_data",
  "data": {
    "front_left": 2147483647,
    "front_right": 1331,
    "rear_left": 242,
    "rear_right": 380,
    "front_collision": false,
    "rear_collision": false
  },
  "timestamp": 1640995200.0
}
```

**Sensor Values**:
- Distance readings in sensor units (higher = closer for some sensors)
- `2147483647` typically indicates "no obstacle detected"
- Collision flags indicate immediate obstacle detection

#### Command Responses
```json
{
  "type": "command_response",
  "command": "FORWARD",
  "value": 60,
  "success": true,
  "timestamp": 1640995200.0
}
```

#### Arduino Messages
```json
{
  "type": "arduino_message",
  "message": "💓 KEEPALIVE processed - no motor action",
  "timestamp": 1640995200.0
}
```

#### Connection Events
```json
{
  "type": "arduino_connection",
  "state": "connected|disconnected",
  "current_port": "/dev/ttyACM0",
  "timestamp": 1640995200.0
}
```

#### Error Messages
```json
{
  "type": "error",
  "message": "Invalid command: INVALID_CMD",
  "timestamp": 1640995200.0
}
```

### Socket Connection Details

#### Connection Management
- **Socket Type**: `AF_UNIX`, `SOCK_STREAM`
- **Socket Path**: `/tmp/motor-proxy/motor_controller.sock`
- **Permissions**: `0666` (configurable)
- **Timeout**: 1 second for client recv operations
- **Send Timeout**: 100ms to prevent blocking on slow clients

#### Error Handling
- **Connection Errors**: Automatic client disconnection
- **Send Timeouts**: Warning logged, message skipped (client not disconnected)
- **Malformed JSON**: Error response sent to client
- **Arduino Disconnection**: Broadcast to all clients

#### Performance Characteristics
- **Sensor Data Rate**: 10 messages/second (100ms intervals)
- **Command Response**: Immediate (< 10ms typical)
- **Client Capacity**: Tested with 10+ concurrent clients
- **Memory Usage**: ~50MB typical, ~100MB with debug logging

## 🐳 Docker Deployment Options

### Build Options

```bash
# Build for host architecture
./docker_build.sh

# Build for ARM64 (Jetson Nano)
./docker_build.sh -a arm64

# Build, test, and save for transfer
./docker_build.sh -a arm64 -s -t

# Build multi-architecture (requires registry)
./docker_build.sh -m -r your-registry.com
```

### Deployment Types

#### 1. Quick Deployment
```bash
./deploy_arm64.sh $ER_JETSON_IP $ER_SSH_USER deploy quick
```
- Basic setup with auto-detection
- Privileged mode for device access
- Suitable for development and testing

#### 2. Production Deployment
```bash
./deploy_arm64.sh $ER_JETSON_IP $ER_SSH_USER deploy production
```
- Health checks enabled
- Log file creation
- Restart policies
- Suitable for long-running production use

#### 3. Debug Deployment
```bash
./deploy_arm64.sh $ER_JETSON_IP $ER_SSH_USER deploy debug
```
- `LOG_LEVEL=DEBUG` for verbose logging
- Detailed socket operation logs
- Arduino communication debugging
- Suitable for troubleshooting

#### 4. Secure Deployment
```bash
./deploy_arm64.sh $ER_JETSON_IP $ER_SSH_USER deploy secure
```
- Specific device access only
- No privileged mode
- Predefined serial ports
- Suitable for security-conscious environments

### Docker Configuration

#### Environment Variables
```bash
-e SERIAL_PORT=""              # Auto-detect (default) or specific port
-e BAUD_RATE=115200           # Serial communication speed
-e SOCKET_PATH=/tmp/motor-proxy/motor_controller.sock
-e LOG_LEVEL=INFO             # DEBUG, INFO, WARNING, ERROR
-e LOG_FILE=""                # Optional log file path
-e DAEMON_MODE=false          # Run as daemon
```

#### Volume Mounts
```bash
-v /tmp/motor-proxy:/tmp/motor-proxy    # Socket directory (required)
-v /var/log/motor-proxy:/var/log/motor-proxy  # Log files (optional)
-v /dev:/dev                            # Device access (for auto-detection)
```

#### Device Access Options

1. **Full Device Access (Recommended)**:
   ```bash
   --privileged -v /dev:/dev
   # Allows auto-detection and handles Arduino reboots
   ```

2. **Specific Device Access**:
   ```bash
   --device=/dev/ttyACM0:/dev/ttyACM0 --device=/dev/ttyACM1:/dev/ttyACM1
   # More secure but requires known device paths
   ```

3. **Group-based Access** (Most Secure):
   ```bash
   # Add user to dialout group on host
   sudo usermod -a -G dialout $USER

   # Run container with group access
   docker run --group-add $(getent group dialout | cut -d: -f3) \
     --device=/dev/ttyACM0 ...
   ```

### Complete Production Example

```bash
# Full production deployment on Jetson Nano
docker run -d \
  --name motor-proxy \
  --restart unless-stopped \
  --privileged \
  --health-cmd="test -S /tmp/motor-proxy/motor_controller.sock" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  -v /dev:/dev \
  -v /tmp/motor-proxy:/tmp/motor-proxy \
  -v /var/log/motor-proxy:/var/log/motor-proxy \
  -e LOG_LEVEL=INFO \
  -e LOG_FILE=/var/log/motor-proxy/motor-proxy.log \
  motor-controller-proxy:latest-arm64

# Check status
docker ps
docker logs motor-proxy
docker exec motor-proxy ls -la /tmp/motor-proxy/
```

## 🧪 Testing

### Example Client Usage

```bash
# In container (recommended)
docker exec -it motor-proxy python examples/monitor_sensors.py
docker exec -it motor-proxy python examples/client_example.py

# On host (if socket is accessible)
python examples/monitor_sensors.py
python examples/client_example.py auto
```

### Multi-Client Testing

```bash
# Terminal 1: Monitor all data
docker exec -it motor-proxy python examples/monitor_sensors.py

# Terminal 2: Control robot
docker exec -it motor-proxy python examples/client_example.py

# Terminal 3: Check status
docker exec motor-proxy python -c "
from examples.client_example import MotorProxyClient
c = MotorProxyClient()
c.connect()
c.get_status()
c.disconnect()
"
```

### Priority Testing

```bash
# High priority client (can control)
docker exec motor-proxy python -c "
from examples.client_example import MotorProxyClient
c = MotorProxyClient()
c.connect()
c.set_priority(1)
c.move_forward(60)
"

# Low priority client (commands rejected)
docker exec motor-proxy python -c "
from examples.client_example import MotorProxyClient
c = MotorProxyClient()
c.connect()
c.set_priority(10)
c.turn_left(40)  # Should be rejected
"
```

## 📁 Project Structure

```
multiplexer/
├── src/                          # Core modules
│   ├── __init__.py              # Version and build info
│   ├── serial_controller.py     # Arduino communication & auto-reconnection
│   ├── unix_socket_server.py    # Unix socket server & client management
│   └── build_info.json         # Build metadata (generated)
├── examples/                     # Example clients
│   ├── monitor_sensors.py       # Full data monitoring client
│   └── client_example.py        # Clean command interface client
├── firmware/                     # Arduino firmware documentation
│   ├── ARDUINO_SERIAL_ANALYSIS.md
│   └── readme.md
├── main.py                       # Entry point
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Multi-arch container definition
├── docker_build.sh              # Build script with multi-arch support
├── deploy_arm64.sh              # Deployment script (generated by docker_build.sh)
└── README.md                     # This file
```

## 🔧 Configuration

### Arduino Integration

The service integrates with Arduino firmware that includes:
- **Watchdog System**: 5-second timeout requiring keepalive every 3 seconds
- **Auto-Reboot**: Arduino reboots on connection, causing device re-enumeration
- **Sensor Broadcasting**: Sends sensor data every 100ms when watchdog is active
- **Command Protocol**: `COMMAND:VALUE\n` format (e.g., `FORWARD:60\n`)

### Serial Port Management

```bash
# Auto-detection scans for:
# - /dev/ttyACM* (Arduino Uno, Nano, etc.)
# - /dev/ttyUSB* (USB-to-serial adapters)

# Service handles Arduino reboots:
# /dev/ttyACM0 → /dev/ttyACM1 (automatic reconnection)

# Check available ports:
ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null || echo "No Arduino ports found"
```

### Socket Configuration

```bash
# Default socket path
/tmp/motor-proxy/motor_controller.sock

# Socket permissions (configurable)
chmod 666 /tmp/motor-proxy/motor_controller.sock

# For production, consider restricted access:
chgrp motor-users /tmp/motor-proxy/motor_controller.sock
chmod 660 /tmp/motor-proxy/motor_controller.sock
```

## 🔍 Monitoring & Debugging

### Health Checks

```bash
# Check socket existence
test -S /tmp/motor-proxy/motor_controller.sock && echo "Socket OK" || echo "Socket Missing"

# Check container health (Docker)
docker inspect motor-proxy --format='{{.State.Health.Status}}'

# Check Arduino connection
docker exec motor-proxy python -c "
from src.serial_controller import SerialController
sc = SerialController()
print('Arduino detected:', sc.find_arduino_port())
"
```

### Log Analysis

```bash
# Live logs
docker logs -f motor-proxy

# Debug mode
docker run -e LOG_LEVEL=DEBUG motor-controller-proxy:latest

# Specific log patterns
docker logs motor-proxy 2>&1 | grep -E "(sensor|command|connection)"
```

### Performance Monitoring

```bash
# Container resource usage
docker stats motor-proxy

# Socket connection count
docker exec motor-proxy ss -x | grep motor_controller.sock

# Arduino communication status
docker exec motor-proxy python -c "
from examples.client_example import MotorProxyClient
c = MotorProxyClient()
c.connect()
c.get_status()
"
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Permission Denied on Serial Port
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER
# Log out and back in

# Or set permissions directly
sudo chmod 666 /dev/ttyACM*
```

#### 2. Socket Already in Use
```bash
# Remove existing socket
rm /tmp/motor-proxy/motor_controller.sock

# Or use different socket path
python main.py --socket-path /tmp/motor-proxy-alt/motor_controller.sock
```

#### 3. Arduino Not Responding
```bash
# Check connection
dmesg | grep -i tty | tail -5

# List available ports
ls -la /dev/ttyACM* /dev/ttyUSB*

# Test direct connection
python -c "
import serial
ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
print('Connected to:', ser.name)
ser.close()
"
```

#### 4. Container Can't Access Arduino
```bash
# Check device access in container
docker exec motor-proxy ls -la /dev/ttyACM*

# Verify privileged mode
docker inspect motor-proxy | grep -i privileged

# Check group membership
docker exec motor-proxy groups
```

#### 5. Client Connection Issues
```bash
# Check socket permissions
ls -la /tmp/motor-proxy/motor_controller.sock

# Test socket connectivity
docker exec motor-proxy python -c "
import socket
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect('/tmp/motor-proxy/motor_controller.sock')
print('Socket connection successful')
s.close()
"
```

#### 6. Sensor Data Not Flowing
```bash
# Check Arduino watchdog status
docker logs motor-proxy | grep -i keepalive

# Verify sensor data reception
docker exec motor-proxy python examples/monitor_sensors.py

# Debug Arduino communication
docker run -e LOG_LEVEL=DEBUG motor-controller-proxy:latest
```

#### 7. High CPU Usage
```bash
# Check for excessive logging
docker logs motor-proxy | wc -l

# Reduce log level
docker run -e LOG_LEVEL=WARNING motor-controller-proxy:latest

# Monitor socket connections
docker exec motor-proxy ss -x | grep motor_controller
```

### Debug Mode

Enable comprehensive debugging:

```bash
# Local debugging
python main.py --log-level DEBUG --log-file debug.log

# Docker debugging with debug deployment
./deploy_arm64.sh $ER_JETSON_IP $ER_SSH_USER deploy debug

# Monitor debug logs
ssh $ER_SSH_USER@$ER_JETSON_IP "tail -f /var/log/motor-proxy/motor-proxy-debug.log"
```

### Arduino Communication Analysis

The service includes detailed Arduino communication logging:

```bash
# Enable Arduino debug logging
docker run -e LOG_LEVEL=DEBUG motor-controller-proxy:latest

# Look for these log patterns:
# - "📊 Received X sensor readings" (sensor data flow)
# - "💓 KEEPALIVE processed" (watchdog system)
# - "🔌 SERIAL CONNECTED/TIMEOUT" (connection status)
# - "📡 Arduino: ..." (Arduino status messages)
```

## 🚀 Recent Improvements

### Version 2.1.0 Features

- **Non-blocking Socket Operations**: Prevents slow clients from affecting Arduino communication
- **Enhanced Error Handling**: Improved client disconnection and timeout management
- **Arduino Reboot Handling**: Robust handling of Arduino auto-reboot cycles
- **Optimized Port Detection**: Faster Arduino detection without triggering reboots
- **Client Priority System**: Multiple clients with priority-based command arbitration
- **Comprehensive Logging**: Detailed debugging with configurable log levels
- **Build Info Integration**: Version tracking and build metadata
- **Multi-deployment Types**: Quick, production, debug, and secure deployment options

### Socket Communication Improvements

- **Send Timeouts**: 100ms timeout prevents blocking on slow clients
- **Connection Monitoring**: Real-time client connection status
- **Broadcast Optimization**: Efficient sensor data distribution to multiple clients
- **Error Isolation**: Client errors don't affect other clients or Arduino communication

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure Docker builds work for both architectures
5. Test with real Arduino hardware
6. Submit a pull request

### Development Guidelines

- Follow existing code style and logging patterns
- Test with multiple concurrent clients
- Verify Arduino auto-reboot handling
- Ensure cross-platform compatibility (AMD64/ARM64)
- Document any new socket protocol messages

## 📄 License

[Add your license information here]

## 🙋 Support

For issues and questions:

1. Check the troubleshooting section above
2. Review Arduino firmware documentation in `firmware/`
3. Enable debug logging: `LOG_LEVEL=DEBUG`
4. Check Docker container logs: `docker logs motor-proxy`
5. Test Arduino connection directly with firmware tools
6. Verify socket permissions and accessibility

### Getting Help

- **Arduino Issues**: Check `firmware/ARDUINO_SERIAL_ANALYSIS.md`
- **Socket Issues**: Enable debug logging and check client examples
- **Docker Issues**: Verify device access and container permissions
- **Performance Issues**: Monitor with `docker stats` and check log levels

---

**Note**: This service is designed specifically for the Arduino motor controller firmware documented in the `firmware/` directory. Ensure your Arduino is running compatible firmware with the watchdog system and sensor broadcasting capabilities before deployment.