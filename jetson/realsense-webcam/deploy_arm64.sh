#!/bin/bash
# Interactive deployment script for arm64 architecture
# Usage: ./deploy_arm64.sh <jetson-ip> [username] [action] [deployment-type] [--no-clean]

set -e

# Default values
JETSON_IP=$1
USERNAME=${2:-jetson}
ACTION=${3:-deploy}
DEPLOY_TYPE=${4:-quick}
IMAGE_FILE="realsense-webcam-latest.tar"
IMAGE_TAG="realsense-webcam:latest"
CONTAINER_NAME="realsense-webcam"
SKIP_CLEANUP=false

# Parse additional flags
shift 4 2>/dev/null || true
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-clean)
            SKIP_CLEANUP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            shift
            ;;
    esac
done

# Function to show usage
show_usage() {
    echo "Usage: $0 <jetson-ip> [username] [action] [deployment-type] [--no-clean]"
    echo ""
    echo "Actions:"
    echo "  deploy   - Deploy the container (default, includes automatic cleanup)"
    echo "  stop     - Stop the running container"
    echo "  delete   - Stop and remove the container"
    echo "  clean    - Remove container and clean up images"
    echo "  status   - Show container status"
    echo "  logs     - Show container logs"
    echo ""
    echo "Deployment types (for deploy action):"
    echo "  quick      - Quick start with auto-detection (default)"
    echo "  production - Full production setup with logging"
    echo "  debug      - Debug mode with verbose logging"
    echo ""
    echo "Options:"
    echo "  --no-clean - Skip automatic cleanup before deployment"
    echo ""
    echo "Examples:"
    echo "  $0 192.168.1.100 jetson deploy quick"
    echo "  $0 192.168.1.100 jetson deploy production --no-clean"
    echo "  $0 192.168.1.100 jetson stop"
    echo "  $0 192.168.1.100 jetson delete"
    echo "  $0 192.168.1.100 jetson clean"
    echo "  $0 192.168.1.100 jetson status"
    echo "  $0 192.168.1.100 jetson logs"
}

if [ -z "$JETSON_IP" ]; then
    show_usage
    exit 1
fi

# Function to check if container exists
container_exists() {
    ssh $USERNAME@$JETSON_IP "docker ps -a -q -f name=$CONTAINER_NAME" 2>/dev/null | grep -q .
}

# Function to check if container is running
container_running() {
    ssh $USERNAME@$JETSON_IP "docker ps -q -f name=$CONTAINER_NAME" 2>/dev/null | grep -q .
}

# Function to stop container
stop_container() {
    echo "🛑 Stopping container '$CONTAINER_NAME'..."
    if container_running; then
        ssh $USERNAME@$JETSON_IP "docker stop $CONTAINER_NAME"
        echo "✅ Container stopped successfully"
    else
        echo "ℹ️  Container is not running"
    fi
}

# Function to delete container
delete_container() {
    echo "🗑️  Deleting container '$CONTAINER_NAME'..."
    if container_running; then
        echo "   Stopping running container..."
        ssh $USERNAME@$JETSON_IP "docker stop $CONTAINER_NAME"
    fi
    if container_exists; then
        ssh $USERNAME@$JETSON_IP "docker rm $CONTAINER_NAME"
        echo "✅ Container deleted successfully"
    else
        echo "ℹ️  Container does not exist"
    fi
}

# Function to clean up everything
clean_all() {
    echo "🧹 Cleaning up all realsense-webcam resources..."
    delete_container

    echo "🧹 Removing Docker images..."
    ssh $USERNAME@$JETSON_IP "docker images -q $IMAGE_TAG" 2>/dev/null | while read image_id; do
        if [ -n "$image_id" ]; then
            ssh $USERNAME@$JETSON_IP "docker rmi $image_id" || true
        fi
    done

    echo "✅ Cleanup completed"
}

# Function to show status
show_status() {
    echo "📊 Container Status for '$CONTAINER_NAME':"
    if container_exists; then
        ssh $USERNAME@$JETSON_IP "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' --filter name=$CONTAINER_NAME"
        echo ""
        echo "📊 Resource Usage:"
        ssh $USERNAME@$JETSON_IP "docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}' $CONTAINER_NAME" 2>/dev/null || echo "   Container not running"
        echo ""
        echo "🌐 Web Interface:"
        local jetson_ip=$(ssh $USERNAME@$JETSON_IP "hostname -I | awk '{print $1}'")
        if container_running; then
            echo "   ✅ Stream should be available at: http://$jetson_ip:5000"
            echo "   📊 Status API: http://$jetson_ip:5000/status"
        else
            echo "   ❌ Container not running - web interface unavailable"
        fi
    else
        echo "   ❌ Container does not exist"
    fi
}

# Function to show logs
show_logs() {
    echo "📜 Container Logs for '$CONTAINER_NAME':"
    if container_exists; then
        ssh $USERNAME@$JETSON_IP "docker logs --tail 50 $CONTAINER_NAME"
    else
        echo "   ❌ Container does not exist"
    fi
}

# Execute action
case $ACTION in
    "stop")
        echo "🚀 Stopping RealSense Webcam on $USERNAME@$JETSON_IP..."
        stop_container
        ;;
    "delete")
        echo "🚀 Deleting RealSense Webcam on $USERNAME@$JETSON_IP..."
        delete_container
        ;;
    "clean")
        echo "🚀 Cleaning up RealSense Webcam on $USERNAME@$JETSON_IP..."
        clean_all
        ;;
    "status")
        echo "🚀 Checking RealSense Webcam status on $USERNAME@$JETSON_IP..."
        show_status
        ;;
    "logs")
        echo "🚀 Showing RealSense Webcam logs on $USERNAME@$JETSON_IP..."
        show_logs
        ;;
    "deploy")
        echo "🚀 Deploying RealSense Webcam to $USERNAME@$JETSON_IP..."
        echo "📦 Image: $IMAGE_TAG"
        echo "🎯 Deployment type: $DEPLOY_TYPE"
        echo ""

        # Check if image file exists
        if [ ! -f "$IMAGE_FILE" ]; then
            echo "❌ Image file '$IMAGE_FILE' not found!"
            echo "💡 Build it first with: ./docker_build.sh -a arm64 -s"
            exit 1
        fi

        # Clean up existing deployment first (default behavior)
        if [ "$SKIP_CLEANUP" = false ]; then
            echo "🧹 Cleaning up existing deployment..."
            clean_all
        else
            echo "⚠️  Skipping cleanup (--no-clean specified)"
            echo "🛑 Stopping existing container (if any)..."
            ssh $USERNAME@$JETSON_IP "docker stop $CONTAINER_NAME 2>/dev/null || true"
            ssh $USERNAME@$JETSON_IP "docker rm $CONTAINER_NAME 2>/dev/null || true"
        fi

        # Transfer the image file
        echo "📤 Transferring image file..."
        scp $IMAGE_FILE $USERNAME@$JETSON_IP:/tmp/

        # Load image on remote host
        echo "📦 Loading image on Jetson Nano..."
        ssh $USERNAME@$JETSON_IP "gunzip -c /tmp/$IMAGE_FILE | docker load"

        # Clean up transfer file
        echo "🧹 Cleaning up transfer file..."
        ssh $USERNAME@$JETSON_IP "rm /tmp/$IMAGE_FILE"

                # Find RealSense USB device
        echo "🔍 Detecting RealSense USB device..."
        REALSENSE_DEVICE=$(ssh $USERNAME@$JETSON_IP "lsusb | grep '8086:0b3a' | awk '{print $2\" \"$4}' | sed 's/://'" || echo "")
        if [ -n "$REALSENSE_DEVICE" ]; then
            REALSENSE_USB="/dev/bus/usb/$(echo $REALSENSE_DEVICE | tr ' ' '/')"
            echo "✅ Found RealSense at: $REALSENSE_USB"
            USB_DEVICE_ARGS="--device=$REALSENSE_USB"
        else
            echo "⚠️  RealSense device not found, using general USB access"
            USB_DEVICE_ARGS="--device=/dev/bus/usb -v /sys/bus/usb:/sys/bus/usb -v /sys/devices:/sys/devices"
        fi

        # Deploy based on type
        case $DEPLOY_TYPE in
            "quick")
                echo "🚀 Deploying with quick start configuration..."
                ssh $USERNAME@$JETSON_IP "docker run -d \\
                    --name $CONTAINER_NAME \\
                    --restart unless-stopped \\
                    --privileged \\
                    $USB_DEVICE_ARGS \\
                    -v /dev:/dev \\
                    -p 5000:5000 \\
                    $IMAGE_TAG"
                ;;
            "production")
                                 echo "🏭 Deploying with production configuration..."
                 ssh $USERNAME@$JETSON_IP "mkdir -p /var/log/realsense-webcam"
                 ssh $USERNAME@$JETSON_IP "docker run -d \\
                     --name $CONTAINER_NAME \\
                     --restart unless-stopped \\
                     --privileged \\
                     $USB_DEVICE_ARGS \\
                     --health-cmd='curl -f http://localhost:5000/status || exit 1' \\
                     --health-interval=30s \\
                     --health-timeout=10s \\
                     --health-retries=3 \\
                     -v /dev:/dev \\
                     -v /var/log/realsense-webcam:/var/log/realsense-webcam \\
                     -p 5000:5000 \\
                     -e FLASK_ENV=production \\
                     $IMAGE_TAG"
                ;;
            "debug")
                                 echo "🐛 Deploying with debug configuration..."
                 ssh $USERNAME@$JETSON_IP "mkdir -p /var/log/realsense-webcam"
                 ssh $USERNAME@$JETSON_IP "docker run -d \\
                     --name $CONTAINER_NAME \\
                     --restart unless-stopped \\
                     --privileged \\
                     $USB_DEVICE_ARGS \\
                     -v /dev:/dev \\
                     -v /var/log/realsense-webcam:/var/log/realsense-webcam \\
                     -p 5000:5000 \\
                     -e FLASK_ENV=development \\
                     -e FLASK_DEBUG=1 \\
                     $IMAGE_TAG"
                ;;
            *)
                echo "❌ Unknown deployment type: $DEPLOY_TYPE"
                exit 1
                ;;
        esac

        # Wait for container to start
        echo "⏳ Waiting for container to start..."
        sleep 10

        # Check deployment status
        echo "📊 Checking deployment status..."
        ssh $USERNAME@$JETSON_IP "docker ps | grep $CONTAINER_NAME || echo 'Container not running!'"
        ssh $USERNAME@$JETSON_IP "docker logs $CONTAINER_NAME --tail 10"

        # Test web interface
        echo "🌐 Testing web interface..."
        local jetson_ip=$(ssh $USERNAME@$JETSON_IP "hostname -I | awk '{print $1}'")
        if ssh $USERNAME@$JETSON_IP "curl -s http://localhost:5000/status" >/dev/null 2>&1; then
            echo "✅ Web interface is responding!"
            echo "🎥 Stream available at: http://$jetson_ip:5000"
        else
            echo "❌ Web interface not responding. Check logs:"
            ssh $USERNAME@$JETSON_IP "docker logs $CONTAINER_NAME"
        fi

        echo ""
        echo "✅ Deployment complete!"
        echo "🌐 Access stream: http://$jetson_ip:5000"
        echo "📊 Monitor with: ssh $USERNAME@$JETSON_IP 'docker logs -f $CONTAINER_NAME'"
        echo "🛑 Stop with: $0 $JETSON_IP $USERNAME stop"
        echo "🗑️  Delete with: $0 $JETSON_IP $USERNAME delete"
        ;;
    *)
        echo "❌ Unknown action: $ACTION"
        show_usage
        exit 1
        ;;
esac
