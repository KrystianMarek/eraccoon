#!/bin/bash
set -e

# Docker build script for RealSense D435i Web Streaming Application
# Supports multi-architecture builds for AMD64 and ARM64
# Target: Nvidia Jetson Nano (ARM64)

# Configuration
IMAGE_NAME="realsense-webcam"
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
    print_status "Collecting build information..."

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

    print_success "Build information collected"
    print_status "📦 Version: 1.0.0"
    print_status "🌲 Branch: $git_branch"
    print_status "📝 Commit: $git_commit"
    print_status "🏗️  Date: $build_date"
    if [ "$git_dirty" = true ]; then
        print_warning "⚠️  Working directory has uncommitted changes"
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
    local builder_name="realsense-webcam-builder"
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
    generate_transfer_script "$arch" "$full_tag" "$output_file"

    # Create deployment script
    generate_deploy_script "$arch" "$full_tag" "$output_file"
}

# Function to build multi-architecture image
build_multi_arch() {
    print_status "Building multi-architecture image..."
    print_status "Platforms: linux/amd64, linux/arm64"

    # For multi-arch, we can't use --load, so we build for each platform separately
    print_warning "Building separate images for each architecture (multi-arch with --load not supported)"

    build_single_arch "amd64"
    build_single_arch "arm64"

    print_success "Multi-architecture build completed"
}

# Function to test the built image
test_image() {
    local image_tag=$1
    print_status "Testing image: $image_tag"

    # Test if image can start (dry run)
    if docker run --rm --entrypoint="" $image_tag python --version; then
        print_success "Image test passed - Python is working"
    else
        print_error "Image test failed - Python not working"
        return 1
    fi

    # Test if pyrealsense2 is available and functional
    if docker run --rm --entrypoint="" $image_tag python -c "import pyrealsense2 as rs; ctx = rs.context(); print('pyrealsense2 imported successfully - found', len(ctx.devices), 'device(s)')"; then
        print_success "pyrealsense2 is available and functional in the image"
    else
        print_error "pyrealsense2 is not available in the image"
        return 1
    fi

    print_success "All image tests passed"
}

# Function to generate transfer script
generate_transfer_script() {
    local arch=$1
    local full_tag=$2
    local output_file=$3

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
echo "1️⃣  Quick Start:"
echo "   docker run -d \\\\"
echo "     --name realsense-webcam \\\\"
echo "     --restart unless-stopped \\\\"
echo "     --privileged \\\\"
echo "     -v /dev:/dev \\\\"
echo "     -p 5000:5000 \\\\"
echo "     $full_tag"
echo ""
echo "2️⃣  Production Setup (with logging):"
echo "   mkdir -p /var/log/realsense-webcam"
echo "   docker run -d \\\\"
echo "     --name realsense-webcam \\\\"
echo "     --restart unless-stopped \\\\"
echo "     --privileged \\\\"
echo "     --health-cmd='curl -f http://localhost:5000/status || exit 1' \\\\"
echo "     --health-interval=30s \\\\"
echo "     --health-timeout=10s \\\\"
echo "     --health-retries=3 \\\\"
echo "     -v /dev:/dev \\\\"
echo "     -v /var/log/realsense-webcam:/var/log/realsense-webcam \\\\"
echo "     -p 5000:5000 \\\\"
echo "     -e FLASK_ENV=production \\\\"
echo "     $full_tag"
echo ""
echo "📊 Check status:"
echo "   docker ps"
echo "   docker logs realsense-webcam"
echo "   curl http://localhost:5000/status"
echo ""
echo "🌐 Access stream:"
echo "   http://\$(hostname -I | awk '{print \$1}'):5000"
EOF

    chmod +x transfer_${arch//\//-}.sh
    print_success "Transfer script created: transfer_${arch//\//-}.sh"
}

# Function to generate deployment script
generate_deploy_script() {
    local arch=$1
    local full_tag=$2
    local output_file=$3

    cat > deploy_${arch//\//-}.sh << EOF
#!/bin/bash
# Interactive deployment script for $arch architecture
# Usage: ./deploy_${arch//\//-}.sh <jetson-ip> [username] [action] [deployment-type] [--no-clean]

set -e

# Default values
JETSON_IP=\$1
USERNAME=\${2:-jetson}
ACTION=\${3:-deploy}
DEPLOY_TYPE=\${4:-quick}
IMAGE_FILE="$output_file"
IMAGE_TAG="$full_tag"
CONTAINER_NAME="realsense-webcam"
SKIP_CLEANUP=false

# Parse additional flags
shift 4 2>/dev/null || true
while [[ \$# -gt 0 ]]; do
    case \$1 in
        --no-clean)
            SKIP_CLEANUP=true
            shift
            ;;
        *)
            echo "Unknown option: \$1"
            shift
            ;;
    esac
done

# Function to show usage
show_usage() {
    echo "Usage: \$0 <jetson-ip> [username] [action] [deployment-type] [--no-clean]"
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
    echo "  \$0 192.168.1.100 jetson deploy quick"
    echo "  \$0 192.168.1.100 jetson deploy production --no-clean"
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
    echo "🧹 Cleaning up all realsense-webcam resources..."
    delete_container

    echo "🧹 Removing Docker images..."
    ssh \$USERNAME@\$JETSON_IP "docker images -q \$IMAGE_TAG" 2>/dev/null | while read image_id; do
        if [ -n "\$image_id" ]; then
            ssh \$USERNAME@\$JETSON_IP "docker rmi \$image_id" || true
        fi
    done

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
        echo "🌐 Web Interface:"
        local jetson_ip=\$(ssh \$USERNAME@\$JETSON_IP "hostname -I | awk '{print \$1}'")
        if container_running; then
            echo "   ✅ Stream should be available at: http://\$jetson_ip:5000"
            echo "   📊 Status API: http://\$jetson_ip:5000/status"
        else
            echo "   ❌ Container not running - web interface unavailable"
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
        echo "🚀 Stopping RealSense Webcam on \$USERNAME@\$JETSON_IP..."
        stop_container
        ;;
    "delete")
        echo "🚀 Deleting RealSense Webcam on \$USERNAME@\$JETSON_IP..."
        delete_container
        ;;
    "clean")
        echo "🚀 Cleaning up RealSense Webcam on \$USERNAME@\$JETSON_IP..."
        clean_all
        ;;
    "status")
        echo "🚀 Checking RealSense Webcam status on \$USERNAME@\$JETSON_IP..."
        show_status
        ;;
    "logs")
        echo "🚀 Showing RealSense Webcam logs on \$USERNAME@\$JETSON_IP..."
        show_logs
        ;;
    "deploy")
        echo "🚀 Deploying RealSense Webcam to \$USERNAME@\$JETSON_IP..."
        echo "📦 Image: \$IMAGE_TAG"
        echo "🎯 Deployment type: \$DEPLOY_TYPE"
        echo ""

        # Check if image file exists
        if [ ! -f "\$IMAGE_FILE" ]; then
            echo "❌ Image file '\$IMAGE_FILE' not found!"
            echo "💡 Build it first with: ./docker_build.sh -a ${arch//\//-} -s"
            exit 1
        fi

        # Clean up existing deployment first (default behavior)
        if [ "\$SKIP_CLEANUP" = false ]; then
            echo "🧹 Cleaning up existing deployment..."
            clean_all
        else
            echo "⚠️  Skipping cleanup (--no-clean specified)"
            echo "🛑 Stopping existing container (if any)..."
            ssh \$USERNAME@\$JETSON_IP "docker stop \$CONTAINER_NAME 2>/dev/null || true"
            ssh \$USERNAME@\$JETSON_IP "docker rm \$CONTAINER_NAME 2>/dev/null || true"
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

        # Deploy based on type
        case \$DEPLOY_TYPE in
            "quick")
                echo "🚀 Deploying with quick start configuration..."
                ssh \$USERNAME@\$JETSON_IP "docker run -d \\\\
                    --name \$CONTAINER_NAME \\\\
                    --restart unless-stopped \\\\
                    --privileged \\\\
                    -v /dev:/dev \\\\
                    -p 5000:5000 \\\\
                    \$IMAGE_TAG"
                ;;
            "production")
                echo "🏭 Deploying with production configuration..."
                ssh \$USERNAME@\$JETSON_IP "mkdir -p /var/log/realsense-webcam"
                ssh \$USERNAME@\$JETSON_IP "docker run -d \\\\
                    --name \$CONTAINER_NAME \\\\
                    --restart unless-stopped \\\\
                    --privileged \\\\
                    --health-cmd='curl -f http://localhost:5000/status || exit 1' \\\\
                    --health-interval=30s \\\\
                    --health-timeout=10s \\\\
                    --health-retries=3 \\\\
                    -v /dev:/dev \\\\
                    -v /var/log/realsense-webcam:/var/log/realsense-webcam \\\\
                    -p 5000:5000 \\\\
                    -e FLASK_ENV=production \\\\
                    \$IMAGE_TAG"
                ;;
            "debug")
                echo "🐛 Deploying with debug configuration..."
                ssh \$USERNAME@\$JETSON_IP "mkdir -p /var/log/realsense-webcam"
                ssh \$USERNAME@\$JETSON_IP "docker run -d \\\\
                    --name \$CONTAINER_NAME \\\\
                    --restart unless-stopped \\\\
                    --privileged \\\\
                    -v /dev:/dev \\\\
                    -v /var/log/realsense-webcam:/var/log/realsense-webcam \\\\
                    -p 5000:5000 \\\\
                    -e FLASK_ENV=development \\\\
                    -e FLASK_DEBUG=1 \\\\
                    \$IMAGE_TAG"
                ;;
            *)
                echo "❌ Unknown deployment type: \$DEPLOY_TYPE"
                exit 1
                ;;
        esac

        # Wait for container to start
        echo "⏳ Waiting for container to start..."
        sleep 10

        # Check deployment status
        echo "📊 Checking deployment status..."
        ssh \$USERNAME@\$JETSON_IP "docker ps | grep \$CONTAINER_NAME || echo 'Container not running!'"
        ssh \$USERNAME@\$JETSON_IP "docker logs \$CONTAINER_NAME --tail 10"

        # Test web interface
        echo "🌐 Testing web interface..."
        local jetson_ip=\$(ssh \$USERNAME@\$JETSON_IP "hostname -I | awk '{print \$1}'")
        if ssh \$USERNAME@\$JETSON_IP "curl -s http://localhost:5000/status" >/dev/null 2>&1; then
            echo "✅ Web interface is responding!"
            echo "🎥 Stream available at: http://\$jetson_ip:5000"
        else
            echo "❌ Web interface not responding. Check logs:"
            ssh \$USERNAME@\$JETSON_IP "docker logs \$CONTAINER_NAME"
        fi

        echo ""
        echo "✅ Deployment complete!"
        echo "🌐 Access stream: http://\$jetson_ip:5000"
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
    print_status "📋 Deployment script features:"
    print_status "   • Remote deployment with SSH"
    print_status "   • Automatic cleanup by default (use --no-clean to skip)"
    print_status "   • Multiple deployment types: quick, production, debug"
    print_status "   • Container management: stop, delete, clean, status, logs"
    print_status "   • Web interface testing and monitoring"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -a, --arch ARCH     Build for specific architecture (amd64, arm64, arm/v7)"
    echo "  -m, --multi-arch    Build for multiple architectures"
    echo "  -s, --save          Save image to tar file and generate deployment scripts"
    echo "  -t, --tag TAG       Specify image tag (default: latest)"
    echo "  -n, --name NAME     Specify image name (default: realsense-webcam)"
    echo "  --no-test           Skip image testing"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                          # Build for host architecture"
    echo "  $0 -a arm64                 # Build for ARM64"
    echo "  $0 -a arm64 -s              # Build ARM64, save to tar and create scripts"
    echo "  $0 -m                       # Build for multiple architectures"
    echo "  $0 -t v1.0.0 -n my-webcam  # Custom name and tag"
    echo ""
    echo "For Jetson Nano deployment:"
    echo "  $0 -a arm64 -s              # Build, save, and create deployment scripts"
    echo "  # Then use: ./deploy_arm64.sh <jetson-ip> jetson deploy"
}

# Main function
main() {
    local target_arch=""
    local multi_arch=false
    local skip_test=false
    local save_image_flag=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -a|--arch)
                target_arch="$2"
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
            -t|--tag)
                IMAGE_TAG="$2"
                FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"
                shift 2
                ;;
            -n|--name)
                IMAGE_NAME="$2"
                FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"
                shift 2
                ;;
            --no-test)
                skip_test=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    # Print banner
    echo "🎥 RealSense D435i Web Streaming - Docker Build Script"
    echo "=================================================="

    # Check prerequisites
    check_docker
    detect_architecture
    generate_build_info

    # Determine build strategy
    if [ "$multi_arch" = true ]; then
        setup_buildx
        build_multi_arch
    elif [ -n "$target_arch" ]; then
        setup_buildx
        build_single_arch "$target_arch"

                # Test the built image
        if [ "$skip_test" = false ]; then
            local tag_suffix=""
            if [ "$target_arch" != "$HOST_ARCH" ]; then
                tag_suffix="-${target_arch//\//-}"
            fi
            test_image "${IMAGE_NAME}:${IMAGE_TAG}${tag_suffix}"
        fi

        # Save image if requested
        if [ "$save_image_flag" = true ]; then
            save_image "$target_arch"
        fi
    else
        # Build for host architecture
        setup_buildx
        build_single_arch "$HOST_ARCH"

        # Test the built image
        if [ "$skip_test" = false ]; then
            test_image "$FULL_IMAGE_NAME"
        fi

        # Save image if requested
        if [ "$save_image_flag" = true ]; then
            save_image "$HOST_ARCH"
        fi
    fi

    # Show summary
    echo ""
    print_success "🎉 Build completed successfully!"
    print_status "📦 Image: $FULL_IMAGE_NAME"
    print_status "🏗️  Architecture: ${target_arch:-$HOST_ARCH}"

    echo ""
    echo "🚀 To run the container:"
    echo "  docker run -d \\"
    echo "    --name realsense-webcam \\"
    echo "    --device /dev/bus/usb \\"
    echo "    --privileged \\"
    echo "    -v /dev:/dev \\"
    echo "    -p 5000:5000 \\"
    echo "    $FULL_IMAGE_NAME"
    echo ""
    echo "🌐 Then access: http://localhost:5000"
}

# Run main function with all arguments
main "$@"