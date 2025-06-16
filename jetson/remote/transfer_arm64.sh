#!/bin/bash
# Transfer script for arm64 architecture
# Usage: ./transfer_arm64.sh <jetson-ip> [username]

set -e

JETSON_IP=$1
USERNAME=${2:-jetson}
IMAGE_FILE="remote-control-service-latest.tar"

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
echo "1️⃣  Quick Start (Development Mode):"
echo "   docker run -d \\"
echo "     --name remote-control \\"
echo "     --restart unless-stopped \\"
echo "     --privileged \\"
echo "     -v /dev:/dev \\"
echo "     -e DISPLAY=:0 \\"
echo "     -v /tmp/.X11-unix:/tmp/.X11-unix \\"
echo "     remote-control-service:latest \\"
echo "     python main.py --mode development"
echo ""
echo "2️⃣  Production Setup (with socket communication):"
echo "   docker run -d \\"
echo "     --name remote-control \\"
echo "     --restart unless-stopped \\"
echo "     --privileged \\"
echo "     -v /dev:/dev \\"
echo "     -v /var/eraccoon:/var/eraccoon \\"
echo "     $IMAGE_TAG \\"
echo "     python main.py --mode production --socket-path /var/eraccoon/multiplexer/socket/motor_proxy_service.sock"
echo ""
echo "3️⃣  Debug Setup (verbose logging):"
echo "   docker run -d \\"
echo "     --name remote-control \\"
echo "     --restart unless-stopped \\"
echo "     --privileged \\"
echo "     -v /dev:/dev \\"
echo "     -v /var/eraccoon:/var/eraccoon \\"
echo "     $IMAGE_TAG \\"
echo "     python main.py --mode production --socket-path /var/eraccoon/multiplexer/socket/motor_proxy_service.sock"
echo ""
echo "📊 Check status:"
echo "   docker ps"
echo "   docker logs remote-control"
echo ""
echo "🧪 Test controller connection:"
echo "   docker exec remote-control ls -la /dev/input/"
