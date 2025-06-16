#!/bin/bash
# Interactive deployment script for arm64 architecture
# Usage: ./deploy_arm64.sh <jetson-ip> [username] [action] [deployment-type] [--no-clean]

set -e

# Default values
JETSON_IP=$1
USERNAME=${2:-jetson}
ACTION=${3:-deploy}
DEPLOY_TYPE=${4:-quick}
IMAGE_FILE="motor-controller-proxy-latest.tar"
IMAGE_TAG="motor-controller-proxy:latest"
CONTAINER_NAME="motor-proxy"
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
    echo "  secure     - Secure setup with specific device access"
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
    echo ""
    echo "Note: By default, 'deploy' action automatically cleans up existing"
    echo "      containers and images before deploying. Use --no-clean to skip this."
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
    echo "🧹 Cleaning up all motor-proxy resources..."
    delete_container

    echo "🧹 Removing Docker images..."
    ssh $USERNAME@$JETSON_IP "docker images -q $IMAGE_TAG" 2>/dev/null | while read image_id; do
        if [ -n "$image_id" ]; then
            ssh $USERNAME@$JETSON_IP "docker rmi $image_id" || true
        fi
    done

    echo "🧹 Cleaning up socket files..."
    ssh $USERNAME@$JETSON_IP "rm -rf /var/eraccoon/multiplexer/socket/*sock" || true

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
        echo "🔌 Socket Status:"
        if ssh $USERNAME@$JETSON_IP "test -S /var/eraccoon/multiplexer/socket/motor_proxy_service.sock"; then
            echo "   ✅ Socket exists at /var/eraccoon/multiplexer/socket/motor_proxy_service.sock"
        else
            echo "   ❌ Socket not found"
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
        echo "🚀 Stopping Motor Controller Proxy on $USERNAME@$JETSON_IP..."
        stop_container
        ;;
    "delete")
        echo "🚀 Deleting Motor Controller Proxy on $USERNAME@$JETSON_IP..."
        delete_container
        ;;
    "clean")
        echo "🚀 Cleaning up Motor Controller Proxy on $USERNAME@$JETSON_IP..."
        clean_all
        ;;
    "status")
        echo "🚀 Checking Motor Controller Proxy status on $USERNAME@$JETSON_IP..."
        show_status
        ;;
    "logs")
        echo "🚀 Showing Motor Controller Proxy logs on $USERNAME@$JETSON_IP..."
        show_logs
        ;;
    "deploy")

        echo "🚀 Deploying Motor Controller Proxy to $USERNAME@$JETSON_IP..."
        echo "📦 Image: $IMAGE_TAG"
        echo "🎯 Deployment type: $DEPLOY_TYPE"
        echo ""

        # Check if image file exists
        if [ ! -f "$IMAGE_FILE" ]; then
            echo "❌ Image file '$IMAGE_FILE' not found!"
            echo "💡 Build it first with: ./docker_build.sh arm64"
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

        # Deploy based on type
        case $DEPLOY_TYPE in
            "quick")
                echo "🚀 Deploying with quick start configuration..."
                ssh $USERNAME@$JETSON_IP "mkdir -p /var/eraccoon/multiplexer/socket"
                ssh $USERNAME@$JETSON_IP "docker run -d \\
                    --name $CONTAINER_NAME \\
                    --restart unless-stopped \\
                    --privileged \\
                    -v /dev:/dev \\
                    -v /var/eraccoon:/var/eraccoon \\
                    $IMAGE_TAG"
                ;;
            "production")
                echo "🏭 Deploying with production configuration..."
                ssh $USERNAME@$JETSON_IP "mkdir -p /var/log/motor-proxy /var/eraccoon/multiplexer/socket"
                ssh $USERNAME@$JETSON_IP "docker run -d \\
                    --name $CONTAINER_NAME \\
                    --restart unless-stopped \\
                    --privileged \\
                    --health-cmd='test -S /var/eraccoon/multiplexer/socket/motor_proxy_service.sock' \\
                    --health-interval=30s \\
                    --health-timeout=10s \\
                    --health-retries=3 \\
                    -v /dev:/dev \\
                    -v /var/eraccoon:/var/eraccoon \\
                    -v /var/log/motor-proxy:/var/log/motor-proxy \\
                    -e LOG_LEVEL=INFO \\
                    -e LOG_FILE=/var/log/motor-proxy/motor-proxy.log \\
                    $IMAGE_TAG"
                ;;
            "debug")
                echo "🐛 Deploying with debug configuration..."
                ssh $USERNAME@$JETSON_IP "mkdir -p /var/log/motor-proxy /var/eraccoon/multiplexer/socket"
                ssh $USERNAME@$JETSON_IP "docker run -d \\
                    --name $CONTAINER_NAME \\
                    --restart unless-stopped \\
                    --privileged \\
                    --health-cmd='test -S /var/eraccoon/multiplexer/socket/motor_proxy_service.sock' \\
                    --health-interval=30s \\
                    --health-timeout=10s \\
                    --health-retries=3 \\
                    -v /dev:/dev \\
                    -v /var/eraccoon:/var/eraccoon \\
                    -v /var/log/motor-proxy:/var/log/motor-proxy \\
                    -e LOG_LEVEL=DEBUG \\
                    -e LOG_FILE=/var/log/motor-proxy/motor-proxy-debug.log \\
                    $IMAGE_TAG"
                ;;
            "secure")
                echo "🔐 Deploying with secure configuration..."
                ssh $USERNAME@$JETSON_IP "mkdir -p /var/eraccoon/multiplexer/socket"
                ssh $USERNAME@$JETSON_IP "docker run -d \\
                    --name $CONTAINER_NAME \\
                    --restart unless-stopped \\
                    --device=/dev/ttyACM0:/dev/ttyACM0 \\
                    --device=/dev/ttyACM1:/dev/ttyACM1 \\
                    --device=/dev/ttyUSB0:/dev/ttyUSB0 \\
                    -v /var/eraccoon:/var/eraccoon \\
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
        ssh $USERNAME@$JETSON_IP "docker ps | grep $CONTAINER_NAME || echo 'Container not running!'"
        ssh $USERNAME@$JETSON_IP "docker logs $CONTAINER_NAME --tail 10"

        # Test socket creation
        echo "🔌 Testing socket creation..."
        if ssh $USERNAME@$JETSON_IP "test -S /var/eraccoon/multiplexer/socket/motor_proxy_service.sock"; then
            echo "✅ Socket created successfully!"

            # Run quick test
            echo "🧪 Running connection test..."
            ssh $USERNAME@$JETSON_IP "timeout 10 docker exec $CONTAINER_NAME python examples/client_example.py --mode demo || echo 'Test completed (timeout expected)'"
        else
            echo "❌ Socket not found! Check logs:"
            ssh $USERNAME@$JETSON_IP "docker logs $CONTAINER_NAME"
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
