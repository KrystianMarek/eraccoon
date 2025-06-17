#!/bin/bash
# Transfer script for arm64 architecture
# Usage: ./transfer_arm64.sh <jetson-ip> [username]

set -e

JETSON_IP=$1
USERNAME=${2:-jetson}
IMAGE_FILE="realsense-webcam-latest.tar"

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
echo "1️⃣  Quick Start:"
echo "   docker run -d \\"
echo "     --name realsense-webcam \\"
echo "     --restart unless-stopped \\"
echo "     --privileged \\"
echo "     -v /dev:/dev \\"
echo "     -p 5000:5000 \\"
echo "     realsense-webcam:latest"
echo ""
echo "2️⃣  Production Setup (with logging):"
echo "   mkdir -p /var/log/realsense-webcam"
echo "   docker run -d \\"
echo "     --name realsense-webcam \\"
echo "     --restart unless-stopped \\"
echo "     --privileged \\"
echo "     --health-cmd='curl -f http://localhost:5000/status || exit 1' \\"
echo "     --health-interval=30s \\"
echo "     --health-timeout=10s \\"
echo "     --health-retries=3 \\"
echo "     -v /dev:/dev \\"
echo "     -v /var/log/realsense-webcam:/var/log/realsense-webcam \\"
echo "     -p 5000:5000 \\"
echo "     -e FLASK_ENV=production \\"
echo "     realsense-webcam:latest"
echo ""
echo "📊 Check status:"
echo "   docker ps"
echo "   docker logs realsense-webcam"
echo "   curl http://localhost:5000/status"
echo ""
echo "🌐 Access stream:"
echo "   http://$(hostname -I | awk '{print $1}'):5000"
