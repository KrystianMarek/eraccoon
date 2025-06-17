# RealSense D435i Web Streaming Application

A simple web application for streaming live RGB and depth camera feeds from an Intel RealSense D435i camera using Python Flask backend.

## Features

- 📷 **RGB Camera Stream**: Live color video feed at 640x480 @ 30fps
- 🌊 **Depth Camera Stream**: Real-time depth visualization with color mapping
- 🌐 **Web Interface**: Modern, responsive UI accessible from any device
- 📱 **Mobile Friendly**: Works on phones, tablets, and desktops
- 🎯 **Real-time Status**: Live camera status monitoring
- 🔄 **Stream Controls**: Refresh, status check, and fullscreen options

## Prerequisites

- Jetson Nano (or compatible ARM64 device)
- Intel RealSense D435i camera
- librealsense2 installed (see installation links below)
- Python 3.6+ with virtual environment support
- USB 3.0 connection for optimal performance

### RealSense Installation
- https://github.com/JetsonHacksNano/installLibrealsense

## Quick Start

### Option 1: Docker Deployment (Recommended for Jetson Nano)

Perfect for legacy systems with older Python versions:

1. **Build the Docker image and generate deployment scripts:**
   ```bash
   ./docker_build.sh -a arm64 -s
   ```

2. **Deploy to remote Jetson:**
   ```bash
   ./deploy_arm64.sh <jetson-ip> jetson deploy
   ```

3. **Access the web interface:**
   - Local: http://localhost:5000
   - Network: http://[YOUR_JETSON_IP]:5000

### Option 2: Native Python (Requires Python 3.7+)

1. **Activate the virtual environment and install dependencies:**
   ```bash
   ./run.sh
   ```

2. **Access the web interface:**
   - Local: http://localhost:5000
   - Network: http://[YOUR_JETSON_IP]:5000

## Docker Commands

### Building
```bash
# Build for ARM64 (Jetson Nano)
./docker_build.sh -a arm64

# Build ARM64 and create deployment scripts
./docker_build.sh -a arm64 -s

# Build for multiple architectures
./docker_build.sh -m

# Build with custom tag
./docker_build.sh -t v1.0.0 -a arm64 -s
```

### Remote Deployment (Generated Scripts)
```bash
# Deploy to Jetson Nano (creates transfer_arm64.sh and deploy_arm64.sh)
./docker_build.sh -a arm64 -s

# Deploy with quick setup
./deploy_arm64.sh <jetson-ip> jetson deploy quick

# Deploy with production setup
./deploy_arm64.sh <jetson-ip> jetson deploy production

# Deploy with debug mode
./deploy_arm64.sh <jetson-ip> jetson deploy debug

# Container management
./deploy_arm64.sh <jetson-ip> jetson stop
./deploy_arm64.sh <jetson-ip> jetson delete
./deploy_arm64.sh <jetson-ip> jetson clean
./deploy_arm64.sh <jetson-ip> jetson status
./deploy_arm64.sh <jetson-ip> jetson logs

# Transfer only (manual deployment)
./transfer_arm64.sh <jetson-ip> jetson
```

## Manual Setup (Python 3.7+ Required)

If you prefer native Python setup:

1. **Activate virtual environment:**
   ```bash
   source .venv/bin/activate
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install pyrealsense2
   ```

3. **Run the application:**
   ```bash
   python3 app.py
   ```

## Architecture

### Backend (Python Flask)
- **app.py**: Main Flask application with RealSense camera integration
- **RealSenseCamera class**: Handles camera initialization, frame capture, and streaming
- **Threading**: Separate thread for continuous frame capture
- **MJPEG Streaming**: HTTP multipart streaming for real-time video

### Frontend (HTML/CSS/JS)
- **templates/index.html**: Responsive web interface
- **Real-time streams**: RGB and depth feeds displayed side-by-side
- **Status monitoring**: Live camera status with visual indicators
- **Controls**: Stream refresh, status check, fullscreen toggle

## API Endpoints

- `GET /` - Main web interface
- `GET /video_feed_rgb` - RGB camera MJPEG stream
- `GET /video_feed_depth` - Depth camera MJPEG stream
- `GET /status` - Camera status JSON response

## Configuration

### Camera Settings (in app.py)
```python
# Configure streams
self.config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
self.config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
```

### Depth Visualization
The depth stream uses OpenCV's COLORMAP_JET for visualization:
- **Blue**: Close objects
- **Red**: Far objects
- **Green/Yellow**: Medium distance

## Troubleshooting

### Camera Not Detected
```bash
# Check if camera is connected
lsusb | grep Intel

# Test with RealSense viewer
realsense-viewer

# Check permissions
sudo usermod -a -G video $USER
```

### Performance Issues
- Ensure USB 3.0 connection (blue USB port)
- Reduce resolution or frame rate if needed
- Check system resources with `htop`

### Network Access
- Firewall: Ensure port 5000 is open
- Find Jetson IP: `hostname -I`
- Test connectivity: `ping [JETSON_IP]`

## Development

### Adding New Features
1. **New camera stream**: Add endpoint in app.py
2. **UI changes**: Modify templates/index.html
3. **Camera settings**: Update RealSenseCamera class

### Dependencies

**Container Dependencies:**
- **Python 3.8**: Modern Python runtime from [pyrealsense2 PyPI](https://pypi.org/project/pyrealsense2/)
- **pyrealsense2**: RealSense camera interface (from PyPI)
- **opencv-python**: Image processing and encoding
- **flask**: Web framework
- **numpy**: Array operations

**System Dependencies:**
- **Docker**: Container runtime
- **USB 3.0**: For RealSense camera connection
- **Device access**: Container needs `/dev` access for camera

## Hardware Requirements

- **Jetson Nano**: 4GB recommended for smooth streaming
- **USB 3.0**: Required for full frame rate
- **Network**: WiFi or Ethernet for remote access
- **Power**: Ensure adequate power supply for Jetson + camera

## License

This project is open source. Feel free to modify and distribute.

## Support

For issues:
1. Check camera connection and permissions
2. Verify librealsense2 installation
3. Test with `realsense-viewer` first
4. Check system logs: `dmesg | grep realsense`