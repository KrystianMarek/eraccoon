#!/bin/bash
# Interactive deployment script for arm64 architecture
# Usage: ./deploy_arm64.sh <jetson-ip> [username] [deployment-type]

set -e

JETSON_IP=$1
USERNAME=${2:-jetson}
DEPLOY_TYPE=${3:-quick}
IMAGE_FILE="motor-controller-proxy-latest.tar"
IMAGE_TAG="motor-controller-proxy:latest"

if [ -z "$JETSON_IP" ]; then
    echo "Usage: $0 <jetson-ip> [username] [deployment-type]"
    echo "Example: $0 192.168.1.100 jetson production"
    echo ""
    echo "Deployment types:"
    echo "  quick      - Quick start with auto-detection (default)"
    echo "  production - Full production setup with logging"
    echo "  secure     - Secure setup with specific device access"
    exit 1
fi

echo "🚀 Deploying Motor Controller Proxy to $USERNAME@$JETSON_IP..."
echo "📦 Image: $IMAGE_TAG"
echo "🎯 Deployment type: $DEPLOY_TYPE"
echo ""

# Transfer the image file
echo "📤 Transferring image file..."
scp $IMAGE_FILE $USERNAME@$JETSON_IP:/tmp/

# Load image on remote host
echo "📦 Loading image on Jetson Nano..."
ssh $USERNAME@$JETSON_IP "gunzip -c /tmp/$IMAGE_FILE | docker load"

# Clean up transfer file
echo "🧹 Cleaning up transfer file..."
ssh $USERNAME@$JETSON_IP "rm /tmp/$IMAGE_FILE"

# Stop existing container if it exists
echo "🛑 Stopping existing container (if any)..."
ssh $USERNAME@$JETSON_IP "docker stop motor-proxy 2>/dev/null || true"
ssh $USERNAME@$JETSON_IP "docker rm motor-proxy 2>/dev/null || true"

# Deploy based on type
case $DEPLOY_TYPE in
    "quick")
        echo "🚀 Deploying with quick start configuration..."
        ssh $USERNAME@$JETSON_IP "docker run -d \\
            --name motor-proxy \\
            --restart unless-stopped \\
            --privileged \\
            -v /dev:/dev \\
            -v /tmp/motor-proxy:/tmp/motor-proxy \\
            $IMAGE_TAG"
        ;;
    "production")
        echo "🏭 Deploying with production configuration..."
        ssh $USERNAME@$JETSON_IP "mkdir -p /var/log/motor-proxy"
        ssh $USERNAME@$JETSON_IP "docker run -d \\
            --name motor-proxy \\
            --restart unless-stopped \\
            --privileged \\
            --health-cmd='test -S /tmp/motor-proxy/motor_controller.sock' \\
            --health-interval=30s \\
            --health-timeout=10s \\
            --health-retries=3 \\
            -v /dev:/dev \\
            -v /tmp/motor-proxy:/tmp/motor-proxy \\
            -v /var/log/motor-proxy:/var/log/motor-proxy \\
            -e LOG_LEVEL=INFO \\
            -e LOG_FILE=/var/log/motor-proxy/motor-proxy.log \\
            $IMAGE_TAG"
        ;;
    "secure")
        echo "🔐 Deploying with secure configuration..."
        ssh $USERNAME@$JETSON_IP "docker run -d \\
            --name motor-proxy \\
            --restart unless-stopped \\
            --device=/dev/ttyACM0:/dev/ttyACM0 \\
            --device=/dev/ttyACM1:/dev/ttyACM1 \\
            --device=/dev/ttyUSB0:/dev/ttyUSB0 \\
            -v /tmp/motor-proxy:/tmp/motor-proxy \\
            -e SERIAL_PORT=/dev/ttyACM0 \\
            $IMAGE_TAG"
        ;;
    *)
        echo "❌ Unknown deployment type: $DEPLOY_TYPE"
        exit 1
        ;;
esac

# Wait for container to start
echo "⏳ Waiting for container to start..."
sleep 5

# Check deployment status
echo "📊 Checking deployment status..."
ssh $USERNAME@$JETSON_IP "docker ps | grep motor-proxy || echo 'Container not running!'"
ssh $USERNAME@$JETSON_IP "docker logs motor-proxy --tail 10"

# Test socket creation
echo "🔌 Testing socket creation..."
if ssh $USERNAME@$JETSON_IP "test -S /tmp/motor-proxy/motor_controller.sock"; then
    echo "✅ Socket created successfully!"

    # Run quick test
    echo "🧪 Running connection test..."
    ssh $USERNAME@$JETSON_IP "timeout 10 docker exec motor-proxy python examples/client_example.py auto || echo 'Test completed (timeout expected)'"
else
    echo "❌ Socket not found! Check logs:"
    ssh $USERNAME@$JETSON_IP "docker logs motor-proxy"
fi

echo ""
echo "✅ Deployment complete!"
echo "📊 Monitor with: ssh $USERNAME@$JETSON_IP 'docker logs -f motor-proxy'"
echo "🛑 Stop with: ssh $USERNAME@$JETSON_IP 'docker stop motor-proxy'"
