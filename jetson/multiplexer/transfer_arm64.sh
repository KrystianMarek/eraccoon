#!/bin/bash
# Transfer script for arm64 architecture
# Usage: ./transfer_arm64.sh <jetson-ip> [username]

set -e

JETSON_IP=$1
USERNAME=${2:-jetson}
IMAGE_FILE="motor-controller-proxy-latest.tar"

if [ -z "$JETSON_IP" ]; then
    echo "Usage: $0 <jetson-ip> [username]"
    echo "Example: $0 192.168.1.100 jetson"
    exit 1
fi

echo "🚀 Transferring $IMAGE_FILE to $USERNAME@$JETSON_IP..."

# Transfer the image file
scp $IMAGE_FILE $USERNAME@$JETSON_IP:/tmp/

echo "📦 Loading image on Jetson Nano..."
ssh $USERNAME@$JETSON_IP "gunzip -c /tmp/$IMAGE_FILE | docker load"

echo "🧹 Cleaning up transfer file..."
ssh $USERNAME@$JETSON_IP "rm /tmp/$IMAGE_FILE"

echo "✅ Transfer complete!"
echo ""
echo "🎯 Next steps on Jetson Nano:"
echo ""
echo "1️⃣  Quick Start (Auto-detection):"
echo "   docker run -d \\"
echo "     --name motor-proxy \\"
echo "     --restart unless-stopped \\"
echo "     --privileged \\"
echo "     -v /dev:/dev \\"
echo "     -v /tmp/motor-proxy:/tmp/motor-proxy \\"
echo "     motor-controller-proxy:latest"
echo ""
echo "2️⃣  Production Setup (with logging and health checks):"
echo "   mkdir -p /var/log/motor-proxy"
echo "   docker run -d \\"
echo "     --name motor-proxy \\"
echo "     --restart unless-stopped \\"
echo "     --privileged \\"
echo "     --health-cmd=\"test -S /tmp/motor-proxy/motor_controller.sock\" \\"
echo "     --health-interval=30s \\"
echo "     --health-timeout=10s \\"
echo "     --health-retries=3 \\"
echo "     -v /dev:/dev \\"
echo "     -v /tmp/motor-proxy:/tmp/motor-proxy \\"
echo "     -v /var/log/motor-proxy:/var/log/motor-proxy \\"
echo "     -e LOG_LEVEL=INFO \\"
echo "     -e LOG_FILE=/var/log/motor-proxy/motor-proxy.log \\"
echo "     motor-controller-proxy:latest"
echo ""
echo "3️⃣  Secure Setup (specific device access):"
echo "   docker run -d \\"
echo "     --name motor-proxy \\"
echo "     --restart unless-stopped \\"
echo "     --device=/dev/ttyACM0:/dev/ttyACM0 \\"
echo "     --device=/dev/ttyACM1:/dev/ttyACM1 \\"
echo "     --device=/dev/ttyUSB0:/dev/ttyUSB0 \\"
echo "     -v /tmp/motor-proxy:/tmp/motor-proxy \\"
echo "     -e SERIAL_PORT=/dev/ttyACM0 \\"
echo "     motor-controller-proxy:latest"
echo ""
echo "📊 Check status:"
echo "   docker ps"
echo "   docker logs motor-proxy"
echo "   docker exec motor-proxy ls -la /tmp/motor-proxy/"
echo ""
echo "🧪 Test connection:"
echo "   docker exec motor-proxy python examples/client_example.py auto"
