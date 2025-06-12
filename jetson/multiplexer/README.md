# Motor Controller Proxy/Multiplexer

A robust proxy/multiplexer service that exposes Arduino motor control via Unix socket interface. Designed for deployment on Nvidia Jetson Nano with support for multiple concurrent clients and command arbitration.

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
                                       └───────────────┘
```

## 🚀 Features

- **Unix Socket Interface**: Clean IPC mechanism for local applications
- **Multi-Client Support**: Handle multiple concurrent connections
- **Priority-Based Control**: Client prioritization for command arbitration
- **Real-time Sensor Data**: Live streaming of Arduino sensor readings
- **Robust Connection Management**: Auto-reconnection and dynamic port detection
- **Docker Support**: Multi-architecture builds for ARM64/AMD64
- **Comprehensive Logging**: Detailed logging with configurable levels
- **Health Monitoring**: Built-in health checks and statistics

## 📋 Requirements

### Hardware
- Arduino with motor controller firmware (see `firmware/` directory)
- USB connection between host and Arduino
- Target deployment: Nvidia Jetson Nano (ARM64)
- **Note**: Arduino may auto-reboot and change USB device path (e.g., `/dev/ttyACM0` → `/dev/ttyACM1`)

### Software
- Python 3.7+
- Docker (for containerized deployment)
- Linux/Unix environment

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
   # python main.py --serial-port /dev/ttyACM0
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
   # On development machine (AMD64/ARM64)
   ./docker_build.sh -a arm64 -s -t
   ```

2. **Transfer to Jetson Nano**:
   ```bash
   # Manual transfer (shows deployment options)
   ./transfer_arm64.sh <jetson-ip> <username>
   # Example: ./transfer_arm64.sh 192.168.1.100 jetson

   # OR: Automated deployment with testing
   ./deploy_arm64.sh <jetson-ip> <username> <deployment-type>
   # Examples:
   ./deploy_arm64.sh 192.168.1.100 jetson quick      # Quick start
   ./deploy_arm64.sh 192.168.1.100 jetson production # Full production
   ./deploy_arm64.sh 192.168.1.100 jetson secure     # Secure setup
   ```

3. **Run on Jetson Nano**:
   ```bash
   # Method 1: Full device access (recommended for auto-detection)
   docker run -d \
     --name motor-proxy \
     --restart unless-stopped \
     --privileged \
     -v /dev:/dev \
     -v /tmp/motor-proxy:/tmp/motor-proxy \
     -e LOG_LEVEL=INFO \
     motor-controller-proxy:latest-arm64

   # Method 2: Specific device access (if you know the port)
   docker run -d \
     --name motor-proxy \
     --restart unless-stopped \
     --device=/dev/ttyACM0:/dev/ttyACM0 \
     --device=/dev/ttyACM1:/dev/ttyACM1 \
     --device=/dev/ttyUSB0:/dev/ttyUSB0 \
     -v /tmp/motor-proxy:/tmp/motor-proxy \
     -e SERIAL_PORT=/dev/ttyACM0 \
     motor-controller-proxy:latest-arm64
   ```

## 🎮 Usage

### Basic Control

```python
from examples.client_example import MotorProxyClient

# Connect to proxy
client = MotorProxyClient('/tmp/motor_controller.sock')
client.connect()

# Control robot
client.move_forward(60)    # Move forward at speed 60
client.turn_left(40)       # Turn left at speed 40
client.stop()              # Stop all movement
client.reset()             # Return to joystick control

client.disconnect()
```

### Command Line Options

```bash
python main.py --help

Options:
  --serial-port PORT    Arduino serial port (default: auto-detect)
  --baud-rate RATE      Serial baud rate (default: 115200)
  --socket-path PATH    Unix socket path (default: /tmp/motor_controller.sock)
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
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `LOG_FILE` | | Optional log file path |
| `DAEMON_MODE` | `false` | Run as daemon |

## 📡 Protocol Specification

### Client → Server Messages

#### Motor Commands
```json
{
  "type": "motor_command",
  "command": "FORWARD|BACKWARD|LEFT|RIGHT|STOP|RESET",
  "value": 0-255
}
```

#### System Commands
```json
{
  "type": "ping"
}
{
  "type": "get_status"
}
{
  "type": "get_sensor_data"
}
{
  "type": "set_priority",
  "priority": 1-100
}
```

### Server → Client Messages

#### Status Updates
```json
{
  "type": "status",
  "arduino_state": "connected|disconnected|error",
  "arduino_connected": true,
  "active_client": "client_12345",
  "total_clients": 2,
  "clients": [...],
  "stats": {...}
}
```

#### Sensor Data
```json
{
  "type": "sensor_data",
  "data": {
    "front_left": 2147483647,
    "front_right": 1331,
    "rear_left": 242,
    "rear_right": 380,
    "front_collision": false,
    "rear_collision": false,
    "timestamp": 1640995200.0
  }
}
```

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

## 🐳 Docker Multi-Architecture Build

The service supports multi-architecture builds for both development (AMD64) and deployment (ARM64) environments.

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

#### Docker Configuration Options

**Environment Variables:**
```bash
-e SERIAL_PORT=""              # Auto-detect (default) or specific port
-e BAUD_RATE=115200           # Serial communication speed
-e SOCKET_PATH=/tmp/motor-proxy/motor_controller.sock
-e LOG_LEVEL=INFO             # DEBUG, INFO, WARNING, ERROR
-e LOG_FILE=""                # Optional log file path
-e DAEMON_MODE=false          # Run as daemon
```

**Volume Mounts:**
```bash
-v /tmp/motor-proxy:/tmp/motor-proxy    # Socket directory (required)
-v /var/log:/var/log                    # Optional: for log files
```

**Device Access Options:**

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

#### Complete Production Example

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

#### Docker Compose Example

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  motor-proxy:
    image: motor-controller-proxy:latest-arm64
    container_name: motor-proxy
    restart: unless-stopped
    privileged: true
    environment:
      - LOG_LEVEL=INFO
      - LOG_FILE=/var/log/motor-proxy/motor-proxy.log
      - SERIAL_PORT=  # Auto-detect
    volumes:
      - /dev:/dev
      - /tmp/motor-proxy:/tmp/motor-proxy
      - /var/log/motor-proxy:/var/log/motor-proxy
    healthcheck:
      test: ["CMD", "test", "-S", "/tmp/motor-proxy/motor_controller.sock"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # Optional: Example client service
  motor-client:
    image: motor-controller-proxy:latest-arm64
    container_name: motor-client
    depends_on:
      - motor-proxy
    volumes:
      - /tmp/motor-proxy:/tmp/motor-proxy
    command: python examples/client_example.py auto
    restart: "no"
```

Deploy with Docker Compose:

```bash
# Deploy
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs motor-proxy

# Stop
docker-compose down
```

#### Systemd Service (Production)

For production deployments, create a systemd service:

Create `/etc/systemd/system/motor-proxy.service`:

```ini
[Unit]
Description=Motor Controller Proxy Service
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStartPre=-/usr/bin/docker stop motor-proxy
ExecStartPre=-/usr/bin/docker rm motor-proxy
ExecStart=/usr/bin/docker run -d \
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
ExecStop=/usr/bin/docker stop motor-proxy

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
# Enable service
sudo systemctl enable motor-proxy.service

# Start service
sudo systemctl start motor-proxy.service

# Check status
sudo systemctl status motor-proxy.service

# View logs
sudo journalctl -u motor-proxy.service -f
```

## 🧪 Testing

### Run Example Client

```bash
# Interactive demo
python examples/client_example.py interactive

# Automated demo
python examples/client_example.py auto
```

### Test with Multiple Clients

```bash
# Terminal 1: Start proxy
python main.py --log-level DEBUG

# Terminal 2: Client 1 (high priority)
python -c "
from examples.client_example import MotorProxyClient
c = MotorProxyClient()
c.connect()
c.set_priority(1)
c.move_forward(60)
"

# Terminal 3: Client 2 (low priority)
python -c "
from examples.client_example import MotorProxyClient
c = MotorProxyClient()
c.connect()
c.set_priority(10)
c.turn_left(40)  # Should be rejected due to lower priority
"
```

## 📁 Project Structure

```
multiplexer/
├── src/                          # Core modules
│   ├── __init__.py
│   ├── serial_controller.py      # Arduino communication
│   └── unix_socket_server.py     # Unix socket server
├── examples/                     # Example clients
│   └── client_example.py
├── firmware/                     # Arduino firmware docs
│   ├── SERIAL_PROTOCOL.md
│   └── test_*.py
├── main.py                       # Entry point
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Multi-arch container
├── docker_build.sh              # Build script
└── README.md                     # This file
```

## 🔧 Configuration

### Arduino Auto-Detection

The service automatically detects Arduino devices and handles port changes due to auto-reboot:

```bash
# The service scans for Arduino devices on:
# - /dev/ttyACM* (Linux/Mac)
# - /dev/ttyUSB* (Linux/Mac)
# - COM* (Windows)

# If Arduino reboots and changes ports, the service automatically reconnects
# Example: /dev/ttyACM0 → /dev/ttyACM1
```

### Serial Port Detection

The service automatically detects available serial ports:

```bash
# List available ports
ls /dev/ttyACM* /dev/ttyUSB*

# Check port permissions
ls -la /dev/ttyACM0

# Add user to dialout group (if needed)
sudo usermod -a -G dialout $USER
```

### Socket Permissions

Unix socket permissions are set to `0666` by default. For production deployments, consider:

```bash
# Restrict to specific group
chgrp motor-users /tmp/motor_controller.sock
chmod 660 /tmp/motor_controller.sock
```

## 🔍 Monitoring & Debugging

### Health Check

```bash
# Check if socket exists
test -S /tmp/motor_controller.sock && echo "Socket OK" || echo "Socket Missing"

# Check container health (Docker)
docker inspect motor-proxy --format='{{.State.Health.Status}}'
```

### Log Analysis

```bash
# Follow live logs
docker logs -f motor-proxy

# Debug serial communication
python main.py --log-level DEBUG --serial-port /dev/ttyACM0

# Test Arduino connection
python firmware/test_serial_control.py
```

### Performance Metrics

The service provides built-in statistics:

```python
client.get_status()  # Returns stats including:
# - uptime
# - total_connections
# - commands_processed
# - errors
```

## 🐛 Troubleshooting

### Common Issues

1. **Permission Denied on Serial Port**
   ```bash
   sudo usermod -a -G dialout $USER
   # Log out and back in
   ```

2. **Socket Already in Use**
   ```bash
   rm /tmp/motor_controller.sock
   # Or use different socket path
   ```

3. **Arduino Not Responding**
   ```bash
   # Check connection
   dmesg | grep tty

   # Test manually
   python firmware/test_serial_control.py
   ```

4. **Docker Container Exits**
   ```bash
   # Check logs
   docker logs motor-proxy

   # Verify device access
   docker run --rm --privileged -v /dev:/dev motor-controller-proxy:latest ls -la /dev/tty*

   # Check if Arduino is detected
   docker run --rm --privileged -v /dev:/dev motor-controller-proxy:latest \
     python -c "import glob; print('Arduino ports:', glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*'))"
   ```

5. **Container Can't Access Arduino**
   ```bash
   # Method 1: Check host permissions
   ls -la /dev/ttyACM*
   sudo chmod 666 /dev/ttyACM*

   # Method 2: Run with privileged access
   docker run --privileged -v /dev:/dev ...

   # Method 3: Add dialout group
   docker run --group-add $(getent group dialout | cut -d: -f3) ...
   ```

6. **Socket Permission Issues**
   ```bash
   # Ensure socket directory exists and is writable
   sudo mkdir -p /tmp/motor-proxy
   sudo chmod 777 /tmp/motor-proxy

   # Check socket creation
   docker exec motor-proxy ls -la /tmp/motor-proxy/
   ```

7. **Arduino Not Auto-Detected**
   ```bash
   # Check available devices in container
   docker exec motor-proxy ls -la /dev/tty*

   # Force specific port
   docker run -e SERIAL_PORT=/dev/ttyACM0 ...

   # Debug mode
   docker run -e LOG_LEVEL=DEBUG ...
   ```

8. **Cross-Architecture Issues (ARM64 on AMD64)**
   ```bash
   # Enable multiarch support
   docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

   # Verify platform
   docker run --rm motor-controller-proxy:latest-arm64 uname -m
   # Should output: aarch64
   ```

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
# Local debugging
python main.py --log-level DEBUG --log-file debug.log

# Docker debugging
docker run -e LOG_LEVEL=DEBUG motor-controller-proxy:latest
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure Docker builds work for both architectures
5. Submit a pull request

## 📄 License

[Add your license information here]

## 🙋 Support

For issues and questions:

1. Check the troubleshooting section
2. Review Arduino firmware documentation in `firmware/`
3. Enable debug logging to diagnose issues
4. Check Docker container logs for deployment issues

---

**Note**: This service is designed specifically for the Arduino motor controller firmware documented in the `firmware/` directory. Ensure your Arduino is running compatible firmware before deployment.