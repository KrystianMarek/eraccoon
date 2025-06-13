#!/bin/bash
set -e

# Docker build script for Motor Controller Proxy/Multiplexer
# Supports multi-architecture builds for AMD64 and ARM64
# Target: Nvidia Jetson Nano (ARM64)

# Configuration
IMAGE_NAME="motor-controller-proxy"
IMAGE_TAG="latest"
FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is available
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running or you don't have permission"
        print_warning "Try: sudo usermod -aG docker \$USER (then log out and back in)"
        exit 1
    fi

    print_success "Docker is available"
}

# Function to detect host architecture
detect_architecture() {
    local arch=$(uname -m)
    case $arch in
        x86_64)
            HOST_ARCH="amd64"
            ;;
        aarch64|arm64)
            HOST_ARCH="arm64"
            ;;
        armv7l)
            HOST_ARCH="arm/v7"
            ;;
        *)
            print_warning "Unknown architecture: $arch, defaulting to amd64"
            HOST_ARCH="amd64"
            ;;
    esac
    print_status "Host architecture detected: $HOST_ARCH"
}

# Function to generate build information
generate_build_info() {
    local build_info_file="src/build_info.json"

    print_status "Collecting git information..."

    # Get git information
    local git_commit="unknown"
    local git_branch="unknown"
    local git_root="unknown"
    local git_dirty=false

    if command -v git &> /dev/null; then
        # Get git root
        if git_root_output=$(git rev-parse --show-toplevel 2>/dev/null); then
            git_root="$git_root_output"
        fi

        # Get commit hash
        if git_commit_output=$(git rev-parse --short HEAD 2>/dev/null); then
            git_commit="$git_commit_output"
        fi

        # Get branch name
        if git_branch_output=$(git rev-parse --abbrev-ref HEAD 2>/dev/null); then
            git_branch="$git_branch_output"
        fi

        # Check if working directory is dirty
        if ! git diff --quiet 2>/dev/null; then
            git_dirty=true
        fi
    fi

    # Get current timestamp
    local build_date=$(date -u '+%Y-%m-%d %H:%M:%S UTC')
    local build_timestamp=$(date -u +%s)

    # Create build info JSON
    cat > "$build_info_file" << EOF
{
  "version": "2.1.0",
  "build_date": "$build_date",
  "build_timestamp": $build_timestamp,
  "git_commit": "$git_commit",
  "git_branch": "$git_branch",
  "git_root": "$git_root",
  "git_dirty": $git_dirty,
  "build_environment": "container"
}
EOF

    if [ -f "$build_info_file" ]; then
        print_success "Build info written to: $build_info_file"
        print_status "📦 Version: 2.1.0"
        print_status "🌲 Branch: $git_branch"
        print_status "📝 Commit: $git_commit"
        print_status "🏗️  Date: $build_date"
        if [ "$git_dirty" = true ]; then
            print_warning "⚠️  Working directory has uncommitted changes"
        fi
    else
        print_error "Failed to create build info file"
        exit 1
    fi
}

# Function to setup buildx for multi-arch builds
setup_buildx() {
    print_status "Setting up Docker Buildx for multi-architecture builds..."

    # Check if buildx is available
    if ! docker buildx version &> /dev/null; then
        print_error "Docker Buildx is not available. Please update Docker to a newer version."
        exit 1
    fi

    # Create or use existing builder
    local builder_name="motor-proxy-builder"
    if ! docker buildx inspect $builder_name &> /dev/null; then
        print_status "Creating new buildx builder: $builder_name"
        docker buildx create --name $builder_name --use
    else
        print_status "Using existing buildx builder: $builder_name"
        docker buildx use $builder_name
    fi

    # Bootstrap the builder
    print_status "Bootstrapping builder..."
    docker buildx inspect --bootstrap

    print_success "Buildx setup complete"
}

# Function to build for single architecture
build_single_arch() {
    local target_arch=$1
    local tag_suffix=""

    if [ "$target_arch" != "$HOST_ARCH" ]; then
        tag_suffix="-${target_arch//\//-}"
    fi

    local full_tag="${IMAGE_NAME}:${IMAGE_TAG}${tag_suffix}"

    print_status "Building for architecture: $target_arch"
    print_status "Image tag: $full_tag"

    docker buildx build \
        --platform linux/$target_arch \
        --tag $full_tag \
        --load \
        --progress plain \
        .

    print_success "Build completed for $target_arch"
    return 0
}

# Function to build multi-architecture image
build_multi_arch() {
    print_status "Building multi-architecture image..."
    print_status "Platforms: linux/amd64, linux/arm64"

    # For multi-arch, we can't use --load, so we build and push
    # If no registry is specified, we'll build for each platform separately
    if [ -z "$REGISTRY" ]; then
        print_warning "No registry specified, building individual images for each platform"
        build_single_arch "amd64"
        build_single_arch "arm64"
    else
        docker buildx build \
            --platform linux/amd64,linux/arm64 \
            --tag $REGISTRY/$FULL_IMAGE_NAME \
            --push \
            --progress plain \
            .
        print_success "Multi-arch image pushed to $REGISTRY/$FULL_IMAGE_NAME"
    fi
}

# Function to save image to tar file
save_image() {
    local arch=${1:-$HOST_ARCH}
    local tag_suffix=""

    if [ "$arch" != "$HOST_ARCH" ]; then
        tag_suffix="-${arch//\//-}"
    fi

    local full_tag="${IMAGE_NAME}:${IMAGE_TAG}${tag_suffix}"
    local output_file="${IMAGE_NAME}-${IMAGE_TAG}${tag_suffix}.tar"

    print_status "Saving image $full_tag to $output_file..."

    docker save $full_tag | gzip > $output_file

    local file_size=$(du -h $output_file | cut -f1)
    print_success "Image saved to $output_file (size: $file_size)"

    # Create transfer script
    cat > transfer_${arch//\//-}.sh << EOF
#!/bin/bash
# Transfer script for $arch architecture
# Usage: ./transfer_${arch//\//-}.sh <jetson-ip> [username]

set -e

JETSON_IP=\$1
USERNAME=\${2:-jetson}
IMAGE_FILE="$output_file"

if [ -z "\$JETSON_IP" ]; then
    echo "Usage: \$0 <jetson-ip> [username]"
    echo "Example: \$0 192.168.1.100 jetson"
    exit 1
fi

echo "🚀 Transferring \$IMAGE_FILE to \$USERNAME@\$JETSON_IP..."

# Transfer the image file
scp \$IMAGE_FILE \$USERNAME@\$JETSON_IP:/tmp/

echo "📦 Loading image on Jetson Nano..."
ssh \$USERNAME@\$JETSON_IP "gunzip -c /tmp/\$IMAGE_FILE | docker load"

echo "🧹 Cleaning up transfer file..."
ssh \$USERNAME@\$JETSON_IP "rm /tmp/\$IMAGE_FILE"

echo "✅ Transfer complete!"
echo ""
echo "🎯 Next steps on Jetson Nano:"
echo ""
echo "1️⃣  Quick Start (Auto-detection):"
echo "   docker run -d \\\\"
echo "     --name motor-proxy \\\\"
echo "     --restart unless-stopped \\\\"
echo "     --privileged \\\\"
echo "     -v /dev:/dev \\\\"
echo "     -v /tmp/motor-proxy:/tmp/motor-proxy \\\\"
echo "     $full_tag"
echo ""
echo "2️⃣  Production Setup (with logging and health checks):"
echo "   mkdir -p /var/log/motor-proxy"
echo "   docker run -d \\\\"
echo "     --name motor-proxy \\\\"
echo "     --restart unless-stopped \\\\"
echo "     --privileged \\\\"
echo "     --health-cmd=\"test -S /tmp/motor-proxy/motor_controller.sock\" \\\\"
echo "     --health-interval=30s \\\\"
echo "     --health-timeout=10s \\\\"
echo "     --health-retries=3 \\\\"
echo "     -v /dev:/dev \\\\"
echo "     -v /tmp/motor-proxy:/tmp/motor-proxy \\\\"
echo "     -v /var/log/motor-proxy:/var/log/motor-proxy \\\\"
echo "     -e LOG_LEVEL=INFO \\\\"
echo "     -e LOG_FILE=/var/log/motor-proxy/motor-proxy.log \\\\"
echo "     $full_tag"
echo ""
echo "3️⃣  Secure Setup (specific device access):"
echo "   docker run -d \\\\"
echo "     --name motor-proxy \\\\"
echo "     --restart unless-stopped \\\\"
echo "     --device=/dev/ttyACM0:/dev/ttyACM0 \\\\"
echo "     --device=/dev/ttyACM1:/dev/ttyACM1 \\\\"
echo "     --device=/dev/ttyUSB0:/dev/ttyUSB0 \\\\"
echo "     -v /tmp/motor-proxy:/tmp/motor-proxy \\\\"
echo "     -e SERIAL_PORT=/dev/ttyACM0 \\\\"
echo "     $full_tag"
echo ""
echo "📊 Check status:"
echo "   docker ps"
echo "   docker logs motor-proxy"
echo "   docker exec motor-proxy ls -la /tmp/motor-proxy/"
echo ""
echo "🧪 Test connection:"
echo "   docker exec motor-proxy python examples/client_example.py auto"
EOF

    chmod +x transfer_${arch//\//-}.sh
    print_success "Transfer script created: transfer_${arch//\//-}.sh"

    # Create interactive deployment script
    cat > deploy_${arch//\//-}.sh << EOF
#!/bin/bash
# Interactive deployment script for $arch architecture
# Usage: ./deploy_${arch//\//-}.sh <jetson-ip> [username] [action] [deployment-type]

set -e

# Default values
JETSON_IP=\$1
USERNAME=\${2:-jetson}
ACTION=\${3:-deploy}
DEPLOY_TYPE=\${4:-quick}
IMAGE_FILE="$output_file"
IMAGE_TAG="$full_tag"
CONTAINER_NAME="motor-proxy"

# Function to show usage
show_usage() {
    echo "Usage: \$0 <jetson-ip> [username] [action] [deployment-type]"
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
    echo "  \$0 192.168.1.100 jetson deploy quick"
    echo "  \$0 192.168.1.100 jetson stop"
    echo "  \$0 192.168.1.100 jetson delete"
    echo "  \$0 192.168.1.100 jetson clean"
    echo "  \$0 192.168.1.100 jetson status"
    echo "  \$0 192.168.1.100 jetson logs"
}

if [ -z "\$JETSON_IP" ]; then
    show_usage
    exit 1
fi

# Function to check if container exists
container_exists() {
    ssh \$USERNAME@\$JETSON_IP "docker ps -a -q -f name=\$CONTAINER_NAME" 2>/dev/null | grep -q .
}

# Function to check if container is running
container_running() {
    ssh \$USERNAME@\$JETSON_IP "docker ps -q -f name=\$CONTAINER_NAME" 2>/dev/null | grep -q .
}

# Function to stop container
stop_container() {
    echo "🛑 Stopping container '\$CONTAINER_NAME'..."
    if container_running; then
        ssh \$USERNAME@\$JETSON_IP "docker stop \$CONTAINER_NAME"
        echo "✅ Container stopped successfully"
    else
        echo "ℹ️  Container is not running"
    fi
}

# Function to delete container
delete_container() {
    echo "🗑️  Deleting container '\$CONTAINER_NAME'..."
    if container_running; then
        echo "   Stopping running container..."
        ssh \$USERNAME@\$JETSON_IP "docker stop \$CONTAINER_NAME"
    fi
    if container_exists; then
        ssh \$USERNAME@\$JETSON_IP "docker rm \$CONTAINER_NAME"
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
    ssh \$USERNAME@\$JETSON_IP "docker images -q \$IMAGE_TAG" 2>/dev/null | while read image_id; do
        if [ -n "\$image_id" ]; then
            ssh \$USERNAME@\$JETSON_IP "docker rmi \$image_id" || true
        fi
    done

    echo "🧹 Cleaning up socket files..."
    ssh \$USERNAME@\$JETSON_IP "rm -rf /tmp/motor-proxy" || true

    echo "✅ Cleanup completed"
}

# Function to show status
show_status() {
    echo "📊 Container Status for '\$CONTAINER_NAME':"
    if container_exists; then
        ssh \$USERNAME@\$JETSON_IP "docker ps -a --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}' --filter name=\$CONTAINER_NAME"
        echo ""
        echo "📊 Resource Usage:"
        ssh \$USERNAME@\$JETSON_IP "docker stats --no-stream --format 'table {{.Name}}\\t{{.CPUPerc}}\\t{{.MemUsage}}\\t{{.NetIO}}' \$CONTAINER_NAME" 2>/dev/null || echo "   Container not running"
        echo ""
        echo "🔌 Socket Status:"
        if ssh \$USERNAME@\$JETSON_IP "test -S /tmp/motor-proxy/motor_controller.sock"; then
            echo "   ✅ Socket exists at /tmp/motor-proxy/motor_controller.sock"
        else
            echo "   ❌ Socket not found"
        fi
    else
        echo "   ❌ Container does not exist"
    fi
}

# Function to show logs
show_logs() {
    echo "📜 Container Logs for '\$CONTAINER_NAME':"
    if container_exists; then
        ssh \$USERNAME@\$JETSON_IP "docker logs --tail 50 \$CONTAINER_NAME"
    else
        echo "   ❌ Container does not exist"
    fi
}

# Execute action
case \$ACTION in
    "stop")
        echo "🚀 Stopping Motor Controller Proxy on \$USERNAME@\$JETSON_IP..."
        stop_container
        ;;
    "delete")
        echo "🚀 Deleting Motor Controller Proxy on \$USERNAME@\$JETSON_IP..."
        delete_container
        ;;
    "clean")
        echo "🚀 Cleaning up Motor Controller Proxy on \$USERNAME@\$JETSON_IP..."
        clean_all
        ;;
    "status")
        echo "🚀 Checking Motor Controller Proxy status on \$USERNAME@\$JETSON_IP..."
        show_status
        ;;
    "logs")
        echo "🚀 Showing Motor Controller Proxy logs on \$USERNAME@\$JETSON_IP..."
        show_logs
        ;;
    "deploy")

        echo "🚀 Deploying Motor Controller Proxy to \$USERNAME@\$JETSON_IP..."
        echo "📦 Image: \$IMAGE_TAG"
        echo "🎯 Deployment type: \$DEPLOY_TYPE"
        echo ""

        # Check if image file exists
        if [ ! -f "\$IMAGE_FILE" ]; then
            echo "❌ Image file '\$IMAGE_FILE' not found!"
            echo "💡 Build it first with: ./docker_build.sh ${arch//\//-}"
            exit 1
        fi

        # Transfer the image file
        echo "📤 Transferring image file..."
        scp \$IMAGE_FILE \$USERNAME@\$JETSON_IP:/tmp/

# Load image on remote host
echo "📦 Loading image on Jetson Nano..."
ssh \$USERNAME@\$JETSON_IP "gunzip -c /tmp/\$IMAGE_FILE | docker load"

# Clean up transfer file
echo "🧹 Cleaning up transfer file..."
ssh \$USERNAME@\$JETSON_IP "rm /tmp/\$IMAGE_FILE"

        # Stop existing container if it exists
        echo "🛑 Stopping existing container (if any)..."
        ssh \$USERNAME@\$JETSON_IP "docker stop \$CONTAINER_NAME 2>/dev/null || true"
        ssh \$USERNAME@\$JETSON_IP "docker rm \$CONTAINER_NAME 2>/dev/null || true"

        # Deploy based on type
        case \$DEPLOY_TYPE in
            "quick")
                echo "🚀 Deploying with quick start configuration..."
                ssh \$USERNAME@\$JETSON_IP "docker run -d \\\\
                    --name \$CONTAINER_NAME \\\\
                    --restart unless-stopped \\\\
                    --privileged \\\\
                    -v /dev:/dev \\\\
                    -v /tmp/motor-proxy:/tmp/motor-proxy \\\\
                    \$IMAGE_TAG"
                ;;
            "production")
                echo "🏭 Deploying with production configuration..."
                ssh \$USERNAME@\$JETSON_IP "mkdir -p /var/log/motor-proxy"
                ssh \$USERNAME@\$JETSON_IP "docker run -d \\\\
                    --name \$CONTAINER_NAME \\\\
                    --restart unless-stopped \\\\
                    --privileged \\\\
                    --health-cmd='test -S /tmp/motor-proxy/motor_controller.sock' \\\\
                    --health-interval=30s \\\\
                    --health-timeout=10s \\\\
                    --health-retries=3 \\\\
                    -v /dev:/dev \\\\
                    -v /tmp/motor-proxy:/tmp/motor-proxy \\\\
                    -v /var/log/motor-proxy:/var/log/motor-proxy \\\\
                    -e LOG_LEVEL=INFO \\\\
                    -e LOG_FILE=/var/log/motor-proxy/motor-proxy.log \\\\
                    \$IMAGE_TAG"
                ;;
            "debug")
                echo "🐛 Deploying with debug configuration..."
                ssh \$USERNAME@\$JETSON_IP "mkdir -p /var/log/motor-proxy"
                ssh \$USERNAME@\$JETSON_IP "docker run -d \\\\
                    --name \$CONTAINER_NAME \\\\
                    --restart unless-stopped \\\\
                    --privileged \\\\
                    --health-cmd='test -S /tmp/motor-proxy/motor_controller.sock' \\\\
                    --health-interval=30s \\\\
                    --health-timeout=10s \\\\
                    --health-retries=3 \\\\
                    -v /dev:/dev \\\\
                    -v /tmp/motor-proxy:/tmp/motor-proxy \\\\
                    -v /var/log/motor-proxy:/var/log/motor-proxy \\\\
                    -e LOG_LEVEL=DEBUG \\\\
                    -e LOG_FILE=/var/log/motor-proxy/motor-proxy-debug.log \\\\
                    \$IMAGE_TAG"
                ;;
            "secure")
                echo "🔐 Deploying with secure configuration..."
                ssh \$USERNAME@\$JETSON_IP "docker run -d \\\\
                    --name \$CONTAINER_NAME \\\\
                    --restart unless-stopped \\\\
                    --device=/dev/ttyACM0:/dev/ttyACM0 \\\\
                    --device=/dev/ttyACM1:/dev/ttyACM1 \\\\
                    --device=/dev/ttyUSB0:/dev/ttyUSB0 \\\\
                    -v /tmp/motor-proxy:/tmp/motor-proxy \\\\
                    -e SERIAL_PORT=/dev/ttyACM0 \\\\
                    \$IMAGE_TAG"
                ;;
            *)
                echo "❌ Unknown deployment type: \$DEPLOY_TYPE"
                exit 1
                ;;
        esac

        # Wait for container to start
        echo "⏳ Waiting for container to start..."
        sleep 5

        # Check deployment status
        echo "📊 Checking deployment status..."
        ssh \$USERNAME@\$JETSON_IP "docker ps | grep \$CONTAINER_NAME || echo 'Container not running!'"
        ssh \$USERNAME@\$JETSON_IP "docker logs \$CONTAINER_NAME --tail 10"

        # Test socket creation
        echo "🔌 Testing socket creation..."
        if ssh \$USERNAME@\$JETSON_IP "test -S /tmp/motor-proxy/motor_controller.sock"; then
            echo "✅ Socket created successfully!"

            # Run quick test
            echo "🧪 Running connection test..."
            ssh \$USERNAME@\$JETSON_IP "timeout 10 docker exec \$CONTAINER_NAME python examples/client_example.py auto || echo 'Test completed (timeout expected)'"
        else
            echo "❌ Socket not found! Check logs:"
            ssh \$USERNAME@\$JETSON_IP "docker logs \$CONTAINER_NAME"
        fi

        echo ""
        echo "✅ Deployment complete!"
        echo "📊 Monitor with: ssh \$USERNAME@\$JETSON_IP 'docker logs -f \$CONTAINER_NAME'"
        echo "🛑 Stop with: \$0 \$JETSON_IP \$USERNAME stop"
        echo "🗑️  Delete with: \$0 \$JETSON_IP \$USERNAME delete"
        ;;
    *)
        echo "❌ Unknown action: \$ACTION"
        show_usage
        exit 1
        ;;
esac
EOF

    chmod +x deploy_${arch//\//-}.sh
    print_success "Interactive deployment script created: deploy_${arch//\//-}.sh"
}

# Function to test the built image
test_image() {
    local arch=${1:-$HOST_ARCH}
    local tag_suffix=""

    if [ "$arch" != "$HOST_ARCH" ]; then
        tag_suffix="-${arch//\//-}"
    fi

    local full_tag="${IMAGE_NAME}:${IMAGE_TAG}${tag_suffix}"

    print_status "Testing image: $full_tag"

    # Test basic functionality (help output)
    if docker run --rm $full_tag python main.py --help > /dev/null; then
        print_success "Image test passed: Help command works"
    else
        print_error "Image test failed: Help command failed"
        return 1
    fi

    # Test image size
    local image_size=$(docker images $full_tag --format "{{.Size}}")
    print_status "Image size: $image_size"

    return 0
}

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -a, --arch ARCH      Build for specific architecture (amd64, arm64)"
    echo "  -m, --multi-arch     Build multi-architecture image"
    echo "  -s, --save           Save image to tar file for transfer"
    echo "  -t, --test           Test the built image"
    echo "  -r, --registry REG   Docker registry for multi-arch builds"
    echo "  -n, --name NAME      Image name (default: motor-controller-proxy)"
    echo "  --tag TAG            Image tag (default: latest)"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                   # Build for host architecture"
    echo "  $0 -a arm64 -s       # Build for ARM64 and save to tar"
    echo "  $0 -m                # Build multi-arch (requires registry or builds separately)"
    echo "  $0 -t                # Build and test"
    echo ""
    echo "For Jetson Nano deployment:"
    echo "  $0 -a arm64 -s -t    # Build ARM64, save, and test"
}

# Main execution
main() {
    local build_arch=""
    local multi_arch=false
    local save_image_flag=false
    local test_image_flag=false
    local registry=""

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -a|--arch)
                build_arch="$2"
                shift 2
                ;;
            -m|--multi-arch)
                multi_arch=true
                shift
                ;;
            -s|--save)
                save_image_flag=true
                shift
                ;;
            -t|--test)
                test_image_flag=true
                shift
                ;;
            -r|--registry)
                registry="$2"
                shift 2
                ;;
            -n|--name)
                IMAGE_NAME="$2"
                FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"
                shift 2
                ;;
            --tag)
                IMAGE_TAG="$2"
                FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    # Print banner
    echo "================================"
    echo "🚀 Motor Controller Proxy Build"
    echo "================================"

    # Generate build information
    print_status "Generating build information..."
    generate_build_info

    # Check prerequisites
    check_docker
    detect_architecture

    # Set registry environment variable if provided
    if [ -n "$registry" ]; then
        export REGISTRY="$registry"
    fi

    # Setup buildx if needed
    if [ "$multi_arch" = true ] || [ -n "$build_arch" ]; then
        setup_buildx
    fi

    # Perform the build
    if [ "$multi_arch" = true ]; then
        build_multi_arch
    elif [ -n "$build_arch" ]; then
        build_single_arch "$build_arch"
    else
        build_single_arch "$HOST_ARCH"
    fi

    # Test if requested
    if [ "$test_image_flag" = true ]; then
        test_image "$build_arch"
    fi

    # Save if requested
    if [ "$save_image_flag" = true ]; then
        save_image "$build_arch"
    fi

    print_success "Build process completed!"

    # Display next steps
    echo ""
    echo "📋 Next Steps:"
    if [ "$save_image_flag" = true ]; then
        echo "   1. Use the generated transfer script to deploy to Jetson Nano"
        echo "   2. Or manually transfer the .tar file and load with 'docker load'"
    else
        echo "   1. Tag and push to your registry if needed"
        echo "   2. Or use -s flag to save for transfer to Jetson Nano"
    fi
    echo ""
}

# Execute main function with all arguments
main "$@"