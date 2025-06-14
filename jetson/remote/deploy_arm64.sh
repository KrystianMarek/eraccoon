#!/bin/bash
# Interactive deployment script for Remote Control Service (arm64 architecture)
# Usage: ./deploy_arm64.sh <jetson-ip> [username] [action] [deployment-type]

set -e

# Default values
JETSON_IP=$1
USERNAME=${2:-jetson}
ACTION=${3:-deploy}
DEPLOY_TYPE=${4:-quick}
IMAGE_FILE="remote-control-service-1.0.0-arm64.tar"
IMAGE_TAG="remote-control-service:1.0.0-arm64"
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
    echo "  quick      - Quick start with auto-detection (default)"
    echo "  production - Full production setup with logging"
    echo "  debug      - Debug mode with verbose logging"
    echo "  secure     - Secure setup with specific device access"
    echo ""
    echo "Examples:"
    echo "  $0 192.168.1.100 jetson deploy quick"
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
    ssh $USERNAME@$JETSON_IP "docker images -q remote-control-service" 2>/dev/null | while read image_id; do
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
        echo "🎮 Controller Status:"
        if ssh $USERNAME@$JETSON_IP "test -e /dev/input/js0"; then
            echo "   ✅ Controller device exists at /dev/input/js0"
        else
            echo "   ❌ Controller device not found"
        fi
        echo ""
        echo "🔌 Socket Status:"
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
        echo "📦 Loading image on Jetson..."
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
                echo "🚀 Deploying with quick start configuration..."
                ssh $USERNAME@$JETSON_IP "docker run -d \\
                    --name $CONTAINER_NAME \\
                    --restart unless-stopped \\
                    --privileged \\
                    -v /dev:/dev \\
                    -v /tmp/motor-proxy:/tmp/motor-proxy \\
                    $IMAGE_TAG \\
                    python main.py --mode production"
                ;;
            "production")
                echo "🏭 Deploying with production configuration..."
                ssh $USERNAME@$JETSON_IP "mkdir -p /var/log/remote-control"
                ssh $USERNAME@$JETSON_IP "docker run -d \\
                    --name $CONTAINER_NAME \\
                    --restart unless-stopped \\
                    --privileged \\
                    -v /dev:/dev \\
                    -v /tmp/motor-proxy:/tmp/motor-proxy \\
                    -v /var/log/remote-control:/var/log/remote-control \\
                    --log-driver json-file \\
                    --log-opt max-size=10m \\
                    --log-opt max-file=3 \\
                    $IMAGE_TAG \\
                    python main.py --mode production --log-level INFO"
                ;;
            "debug")
                echo "🐛 Deploying with debug configuration..."
                ssh $USERNAME@$JETSON_IP "docker run -d \\
                    --name $CONTAINER_NAME \\
                    --restart unless-stopped \\
                    --privileged \\
                    -v /dev:/dev \\
                    -v /tmp/motor-proxy:/tmp/motor-proxy \\
                    $IMAGE_TAG \\
                    python main.py --mode production --log-level DEBUG"
                ;;
            "secure")
                echo "🔒 Deploying with secure configuration..."
                ssh $USERNAME@$JETSON_IP "docker run -d \\
                    --name $CONTAINER_NAME \\
                    --restart unless-stopped \\
                    --device=/dev/input/js0:/dev/input/js0 \\
                    -v /tmp/motor-proxy:/tmp/motor-proxy \\
                    --security-opt no-new-privileges \\
                    --read-only \\
                    --tmpfs /tmp \\
                    $IMAGE_TAG \\
                    python main.py --mode production --controller-device /dev/input/js0"
                ;;
            *)
                echo "❌ Unknown deployment type: $DEPLOY_TYPE"
                exit 1
                ;;
        esac

        # Wait a moment for container to start
        echo "⏳ Waiting for container to start..."
        sleep 3

        # Check if container is running
        if container_running; then
            echo "✅ Remote Control Service deployed successfully!"
            echo ""
            echo "📊 Container Status:"
            show_status
            echo ""
            echo "💡 Useful commands:"
            echo "   View logs: docker logs -f $CONTAINER_NAME"
            echo "   Stop service: ./deploy_arm64.sh $JETSON_IP $USERNAME stop"
            echo "   Check status: ./deploy_arm64.sh $JETSON_IP $USERNAME status"
            echo ""
            echo "🎮 Controller Mapping:"
            echo "   Left Stick: Movement (forward/back, strafe left/right)"
            echo "   Right Stick X: Rotation"
            echo "   R2 Trigger: Speed boost"
            echo "   L2 Trigger: Precision mode"
            echo "   Circle: Emergency stop"
            echo "   Square: Resume from emergency stop"
            echo "   Options: Quit application"
        else
            echo "❌ Failed to deploy Remote Control Service"
            echo "📜 Container logs:"
            show_logs
            exit 1
        fi
        ;;
    *)
        echo "❌ Unknown action: $ACTION"
        show_usage
        exit 1
        ;;
esac