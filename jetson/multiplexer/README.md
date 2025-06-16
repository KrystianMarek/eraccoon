# Motor Controller Proxy/Multiplexer

A robust proxy/multiplexer service that exposes Arduino motor control via Unix socket interface. Designed for deployment on Nvidia Jetson Nano with support for multiple concurrent clients, command arbitration, real-time sensor data streaming, rate limiting, and client keepalive management.

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
                                       │ • Rate Limiting│
                                       │ • Keepalive   │
                                       │   Monitoring  │
                                       │ • Status      │
                                       │   Broadcasting│
                                       │ • Auto-Reboot │
                                       │   Handling    │
                                       └───────────────┘
```

## 🚀 Features

- **Unix Socket Interface**: Clean IPC mechanism for local applications
- **Multi-Client Support**: Handle multiple concurrent connections with priority-based arbitration
- **Rate Limiting**: Adaptive rate limiting per client based on number of connected clients
- **Client Keepalive Management**: Automatic disconnection of inactive clients (3-second timeout)
- **Unique Client Naming**: Server-assigned unique names independent of client claims
- **Real-time Sensor Data**: Live streaming of Arduino sensor readings (100ms intervals) to all clients
- **Robust Connection Management**: Auto-reconnection, dynamic port detection, and Arduino reboot handling
- **Non-blocking Socket Operations**: Prevents client issues from affecting Arduino communication
- **Docker Support**: Multi-architecture builds for ARM64/AMD64 with comprehensive deployment options
- **Comprehensive Logging**: Detailed logging with configurable levels and rate limiting statistics
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

The project includes several example clients optimized for different use cases:

#### 1. Basic Client Example (`examples/client_example.py`)
**Purpose**: Demonstrates basic motor control with keepalive management
```bash
# Interactive motor control with keepalive
python examples/client_example.py --mode interactive

# Automated demo showing tank and mecanum commands
python examples/client_example.py --mode demo

# Custom client name
python examples/client_example.py --name "MyController"
```
**Features**:
- Automatic client identification and unique naming
- Built-in keepalive management (every 2.5 seconds)
- Tank and mecanum command demonstrations
- Interactive command mode
- Proper error handling and cleanup

#### 2. Monitor Sensors (`examples/monitor_sensors.py`)
**Purpose**: Full data monitoring - shows ALL socket data
```bash
# Shows real-time sensor data, Arduino messages, command responses
python examples/monitor_sensors.py
```
**Output**: Real-time sensor readings, Arduino status, command responses, connection events

#### 3. Mecanum Client Example (`examples/mecanum_client_example.py`)
**Purpose**: Demonstrates advanced mecanum wheel control capabilities
```bash
# Run both tank and mecanum demos, then interactive mode
python examples/mecanum_client_example.py

# Run specific demo mode
python examples/mecanum_client_example.py tank      # Tank commands only
python examples/mecanum_client_example.py mecanum   # Mecanum commands only
python examples/mecanum_client_example.py interactive  # Interactive control
```
**Features**:
- Tank-style movement commands (traditional)
- Mecanum-specific movements (strafing, rotation, diagonal)
- Interactive control with keyboard commands
- Demonstrates all movement patterns possible with mecanum wheels

#### 4. Rate Limiting Test (`examples/rate_limit_test.py`)
**Purpose**: Test rate limiting and keepalive functionality with multiple clients
```bash
# Test rate limiting with 3 clients for 30 seconds at 5 commands/sec each
python examples/rate_limit_test.py --clients 3 --duration 30 --rate 5.0

# Test keepalive functionality
python examples/rate_limit_test.py --test keepalive --clients 4

# Test both rate limiting and keepalive
python examples/rate_limit_test.py --test both --clients 5
```
**Features**:
- Multiple simultaneous client connections
- Rate limiting behavior observation
- Keepalive timeout testing
- Command drop statistics
- Client disconnection testing

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

### Testing New Command Format

A test script is provided to verify the new JSON command format:

```bash
# Test both tank and mecanum commands
python test_new_commands.py
```

This script tests:
- Tank command format and responses
- Mecanum command format and responses
- Error handling and validation

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
3. **Client should send identification** with claimed name (optional but recommended)
4. **Server assigns unique name** independent of client claims
5. **Server sends initial status** with Arduino state and connection info
6. **Client must send keepalive** messages every 3 seconds to maintain connection
7. **Client can send commands** and receives responses (subject to rate limiting)
8. **Server broadcasts** sensor data and Arduino messages to all connected clients

### Message Format

All messages are JSON objects terminated with `\n`:
```
{"type": "command", "data": {...}}\n
```

### Client → Server Messages

#### Client Identification (Recommended)
```json
{
  "type": "identify",
  "name": "MyRobotController"
}
```

#### Keepalive (Required every 3 seconds)
```json
{
  "type": "keepalive"
}
```

#### Motor Commands

The service supports two types of motor commands with built-in rate limiting:

##### 1. Tank Commands
```json
{
  "type": "tank_command",
  "command": "FORWARD|BACKWARD|LEFT|RIGHT|STOP|RESET|KEEPALIVE|FORWARD_LEFT|FORWARD_RIGHT|BACKWARD_LEFT|BACKWARD_RIGHT",
  "value": 0-255
}
```

##### 2. Mecanum Commands (Advanced)
```json
{
  "type": "mecanum_command",
  "motors": {
    "left_front": -255 to 255,
    "left_rear": -255 to 255,
    "right_front": -255 to 255,
    "right_rear": -255 to 255
  }
}
```

##### 3. Mecanum Keepalive
```json
{
  "type": "mecanum_command",
  "command": "KEEPALIVE"
}
```

**Tank Command Types:**
- `FORWARD` / `BACKWARD`: Linear movement
- `LEFT` / `RIGHT`: Turning movement
- `FORWARD_LEFT` / `FORWARD_RIGHT`: Diagonal movement
- `BACKWARD_LEFT` / `BACKWARD_RIGHT`: Reverse diagonal movement
- `STOP`: Stop all motors
- `RESET`: Return control to Arduino joystick
- `KEEPALIVE`: Maintain connection (system use)

**Tank Value Range**: 0-255 (motor speed/power)

**Mecanum Motor Control:**
- **Individual Motor Control**: Direct control of each wheel motor
- **Speed Range**: -255 to 255 (negative = reverse direction)
- **Advanced Movements**: Enables strafing, diagonal movement, rotation in place
- **Movement Patterns**:
  - Forward: `LF:100, LR:100, RF:100, RR:100`
  - Strafe Right: `LF:-100, LR:100, RF:100, RR:-100`
  - Strafe Left: `LF:100, LR:-100, RF:-100, RR:100`
  - Rotate Clockwise: `LF:-100, LR:-100, RF:100, RR:100`

**Rate Limiting:**
- Base rate: 10 commands/second per client (single client)
- Adaptive rate: Distributed among connected clients
- Minimum rate: 1 command/second per client
- Dropped commands are logged with statistics

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

#### Client Identification Response
```json
{
  "type": "identify_response",
  "unique_name": "Client-001",
  "claimed_name": "MyRobotController",
  "timestamp": 1640995200.0
}
```

#### Keepalive Response
```json
{
  "type": "keepalive_response",
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
      "unique_name": "Client-001",
      "claimed_name": "MyRobotController",
      "address": "",
      "state": "connected",
      "last_activity": 1640995200.0,
      "priority": 10,
      "command_count": 42,
      "dropped_commands": 3,
      "last_keepalive": 1640995200.0,
      "missed_keepalives": 0
    }
  ],
  "stats": {
    "start_time": 1640995000.0,
    "total_connections": 5,
    "commands_processed": 42,
    "commands_dropped": 8,
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

##### Tank Command Response
```json
{
  "type": "tank_command_response",
  "command": "FORWARD",
  "value": 60,
  "success": true,
  "timestamp": 1640995200.0
}
```

##### Mecanum Command Response
```json
{
  "type": "mecanum_command_response",
  "motors": {
    "left_front": 100,
    "left_rear": -100,
    "right_front": -100,
    "right_rear": 100
  },
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

#### Client Management
- **Unique Naming**: Server assigns unique names (Client-001, Client-002, etc.)
- **Client Identification**: Clients can provide claimed names for logging
- **Keepalive Requirement**: Clients must send keepalive every 3 seconds
- **Automatic Disconnection**: Clients disconnected after 3 missed keepalives
- **Connection Logging**: All client connections/disconnections logged with unique names

#### Rate Limiting
- **Adaptive Rate Limiting**: Rate limit adjusts based on number of connected clients
- **Base Rate**: 10 commands/second for single client
- **Minimum Rate**: 1 command/second per client (guaranteed minimum)
- **Distribution**: Available bandwidth distributed equally among clients
- **Drop Logging**: Rate limit violations logged max once per second per client
- **Statistics**: Command counts, drop counts, and rates tracked per client

**Rate Limiting Examples**:
- 1 client: 10 commands/second
- 2 clients: 5 commands/second each
- 5 clients: 2 commands/second each
- 10 clients: 1 command/second each (minimum)

#### Error Handling
- **Connection Errors**: Automatic client disconnection
- **Send Timeouts**: Warning logged, message skipped (client not disconnected)
- **Malformed JSON**: Error response sent to client
- **Arduino Disconnection**: Broadcast to all clients
- **Rate Limit Violations**: Commands dropped, statistics logged

#### Performance Characteristics
- **Sensor Data Rate**: 10 messages/second (100ms intervals) - broadcast to ALL clients
- **Command Response**: Immediate (< 10ms typical)
- **Rate Limiting**: 10 commands/second base rate, adaptive per client count
- **Keepalive Monitoring**: 1-second intervals, 3-second timeout
- **Client Capacity**: Tested with 10+ concurrent clients
- **Memory Usage**: ~50MB typical, ~100MB with debug logging
- **Command Processing**: ~1000 commands/second aggregate throughput

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

```