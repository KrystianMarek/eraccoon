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
echo "💡 To run on Jetson Nano:"
echo "   docker run -d --name motor-proxy -v /tmp/motor-proxy:/tmp/motor-proxy motor-controller-proxy:latest"
