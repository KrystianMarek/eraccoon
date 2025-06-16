#!/bin/bash
# Interactive deployment script for arm64 architecture
# Usage: ./deploy_arm64.sh <jetson-ip> [username] [action] [deployment-type]

set -e

# Default values
JETSON_IP=$1
USERNAME=${2:-jetson}
ACTION=${3:-deploy}
DEPLOY_TYPE=${4:-quick}
IMAGE_FILE="remote-control-service-latest.tar"
IMAGE_TAG="remote-control-service:latest"
CONTAINER_NAME="remote-control"

# Function to show usage
show_usage() {
    echo "Usage: $0 <jetson-ip> [username] [action] [deployment-type]"
    echo ""
    echo "Actions:"
    echo "  deploy   - Deploy the container (default)"
    echo "  stop     - Stop the running container"
    echo "  delete   - Stop and remove the container"
    echo "  clean    - Remove container and clean up images"
    echo "  status   - Show container status"
    echo "  logs     - Show container logs"
    echo ""
    echo "Deployment types (for deploy action):"
    echo "  quick      - Quick start in development mode (default)"
    echo "  production - Production setup with socket communication"
    echo "  debug      - Debug mode with verbose logging"
    echo "  secure     - Secure setup with specific device access"
    echo ""
    echo "Examples:"
    echo "  $0 192.168.1.100 jetson deploy quick"
    echo "  $0 192.168.1.100 jetson deploy production"
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
    echo "🧹 Cleaning up all remote-control resources..."
    delete_container

    echo "🧹 Removing Docker images..."
    ssh $USERNAME@$JETSON_IP "docker images -q $IMAGE_TAG" 2>/dev/null | while read image_id; do
        if [ -n "$image_id" ]; then
            ssh $USERNAME@$JETSON_IP "docker rmi $image_id" || true
        fi
    done

    echo "🧹 Cleaning up log files..."
    ssh $USERNAME@$JETSON_IP "rm -rf /var/log/remote-control" || true

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
        echo "🎮 Controller Status:"
        if ssh $USERNAME@$JETSON_IP "docker exec $CONTAINER_NAME ls /dev/input/js* 2>/dev/null"; then
            echo "   ✅ Controller devices found"
        else
            echo "   ❌ No controller devices found"
        fi
        echo ""
        echo "🔌 Socket Status (Production Mode):"
        if ssh $USERNAME@$JETSON_IP "test -S /tmp/motor-proxy/motor_controller.sock"; then
            echo "   ✅ Motor controller socket exists"
        else
            echo "   ❌ Motor controller socket not found"
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
        echo "🚀 Stopping Remote Control Service on $USERNAME@$JETSON_IP..."
        stop_container
        ;;
    "delete")
        echo "🚀 Deleting Remote Control Service on $USERNAME@$JETSON_IP..."
        delete_container
        ;;
    "clean")
        echo "🚀 Cleaning up Remote Control Service on $USERNAME@$JETSON_IP..."
        clean_all
        ;;
    "status")
        echo "🚀 Checking Remote Control Service status on $USERNAME@$JETSON_IP..."
        show_status
        ;;
    "logs")
        echo "🚀 Showing Remote Control Service logs on $USERNAME@$JETSON_IP..."
        show_logs
        ;;
    "deploy")

        echo "🚀 Deploying Remote Control Service to $USERNAME@$JETSON_IP..."
        echo "📦 Image: $IMAGE_TAG"
        echo "🎯 Deployment type: $DEPLOY_TYPE"
        echo ""

        # Check if image file exists
        if [ ! -f "$IMAGE_FILE" ]; then
            echo "❌ Image file '$IMAGE_FILE' not found!"
            echo "💡 Build it first with: ./docker_build.sh arm64"
            exit 1
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

        # Stop existing container if it exists
        echo "🛑 Stopping existing container (if any)..."
        ssh $USERNAME@$JETSON_IP "docker stop $CONTAINER_NAME 2>/dev/null || true"
        ssh $USERNAME@$JETSON_IP "docker rm $CONTAINER_NAME 2>/dev/null || true"

        # Deploy based on type
        case $DEPLOY_TYPE in
            "quick")
                echo "🚀 Deploying with quick start configuration (development mode)..."
                ssh $USERNAME@$JETSON_IP "docker run -d \\
                    --name $CONTAINER_NAME \\
                    --restart unless-stopped \\
                    --privileged \\
                    -v /dev:/dev \\
                    -e DISPLAY=:0 \\
                    -v /tmp/.X11-unix:/tmp/.X11-unix \\
                    $IMAGE_TAG \\
                    python main.py --mode development --log-level INFO"
                ;;
            "production")
                echo "🏭 Deploying with production configuration..."
                ssh $USERNAME@$JETSON_IP "mkdir -p /var/log/remote-control"
                ssh $USERNAME@$JETSON_IP "docker run -d \\
                    --name $CONTAINER_NAME \\
                    --restart unless-stopped \\
                    --privileged \\
                    --health-cmd='pgrep -f \"python main.py\"' \\
                    --health-interval=30s \\
                    --health-timeout=10s \\
                    --health-retries=3 \\
                    -v /dev:/dev \\
                    -v /tmp/motor-proxy:/tmp/motor-proxy \\
                    -v /var/log/remote-control:/var/log/remote-control \\
                    -e LOG_LEVEL=INFO \\
                    $IMAGE_TAG \\
                    python main.py --mode production --socket-path /tmp/motor-proxy/motor_controller.sock --log-level INFO"
                ;;
            "debug")
                echo "🐛 Deploying with debug configuration..."
                ssh $USERNAME@$JETSON_IP "mkdir -p /var/log/remote-control"
                ssh $USERNAME@$JETSON_IP "docker run -d \\
                    --name $CONTAINER_NAME \\
                    --restart unless-stopped \\
                    --privileged \\
                    --health-cmd='pgrep -f \"python main.py\"' \\
                    --health-interval=30s \\
                    --health-timeout=10s \\
                    --health-retries=3 \\
                    -v /dev:/dev \\
                    -v /tmp/motor-proxy:/tmp/motor-proxy \\
                    -v /var/log/remote-control:/var/log/remote-control \\
                    -e LOG_LEVEL=DEBUG \\
                    $IMAGE_TAG \\
                    python main.py --mode production --socket-path /tmp/motor-proxy/motor_controller.sock --log-level DEBUG"
                ;;
            "secure")
                echo "🔐 Deploying with secure configuration..."
                ssh $USERNAME@$JETSON_IP "docker run -d \\
                    --name $CONTAINER_NAME \\
                    --restart unless-stopped \\
                    --device=/dev/input/js0:/dev/input/js0 \\
                    --device=/dev/input/js1:/dev/input/js1 \\
                    --device=/dev/input/event0:/dev/input/event0 \\
                    --device=/dev/input/event1:/dev/input/event1 \\
                    -v /tmp/motor-proxy:/tmp/motor-proxy \\
                    -e CONTROLLER_DEVICE=/dev/input/js0 \\
                    $IMAGE_TAG \\
                    python main.py --mode production --socket-path /tmp/motor-proxy/motor_controller.sock --controller-device /dev/input/js0"
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
        ssh $USERNAME@$JETSON_IP "docker ps | grep $CONTAINER_NAME || echo 'Container not running!'"
        ssh $USERNAME@$JETSON_IP "docker logs $CONTAINER_NAME --tail 10"

        # Test controller detection
        echo "🎮 Testing controller detection..."
        if ssh $USERNAME@$JETSON_IP "docker exec $CONTAINER_NAME ls /dev/input/js* 2>/dev/null"; then
            echo "✅ Controller devices found!"
        else
            echo "❌ No controller devices found! Make sure PS5 controller is connected."
        fi

        echo ""
        echo "✅ Deployment complete!"
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
