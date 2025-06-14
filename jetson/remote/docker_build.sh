#!/bin/bash
# Docker build script for Remote Control Service
# Builds images for both x86_64 and arm64 architectures

set -e

# Default values
ARCHITECTURE="arm64"
PUSH_TO_REGISTRY=false
REGISTRY_URL=""
IMAGE_NAME="remote-control-service"
VERSION="1.0.0"
BUILD_TYPE="release"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to show usage
show_usage() {
    echo -e "${BLUE}Remote Control Service Docker Build Script${NC}"
    echo ""
    echo "Usage: $0 [architecture] [options]"
    echo ""
    echo "Architectures:"
    echo "  x86_64, amd64  - Build for x86_64/amd64 architecture"
    echo "  arm64, aarch64 - Build for ARM64/aarch64 architecture (default)"
    echo "  both           - Build for both architectures"
    echo ""
    echo "Options:"
    echo "  --push             - Push to registry after build"
    echo "  --registry URL     - Registry URL (required if --push is used)"
    echo "  --version VERSION  - Image version tag (default: $VERSION)"
    echo "  --debug            - Build debug version"
    echo "  --dev              - Build development version"
    echo ""
    echo "Examples:"
    echo "  $0 arm64                           # Build ARM64 image"
    echo "  $0 x86_64 --version 1.1.0         # Build x86_64 with custom version"
    echo "  $0 both --push --registry myregistry.com/robotics"
    echo ""
}

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to get build information
get_build_info() {
    local git_commit=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    local git_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    local git_dirty=""

    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        git_dirty="-dirty"
    fi

    local build_date=$(date -u '+%Y-%m-%d %H:%M:%S UTC')

    echo "Git: ${git_branch}@${git_commit}${git_dirty}, Built: ${build_date}"
}

# Function to build Docker image
build_image() {
    local arch=$1
    local platform=""
    local dockerfile="Dockerfile"

    case $arch in
        "x86_64"|"amd64")
            platform="linux/amd64"
            arch="amd64"
            ;;
        "arm64"|"aarch64")
            platform="linux/arm64"
            arch="arm64"
            ;;
        *)
            print_error "Unsupported architecture: $arch"
            return 1
            ;;
    esac

    local tag="${IMAGE_NAME}:${VERSION}-${arch}"
    local latest_tag="${IMAGE_NAME}:latest-${arch}"

    print_info "Building Docker image for $arch..."
    print_info "Platform: $platform"
    print_info "Tag: $tag"

    # Build arguments
    local build_args=""
    build_args+="--build-arg BUILD_DATE='$(date -u '+%Y-%m-%d %H:%M:%S UTC')' "
    build_args+="--build-arg VERSION='$VERSION' "
    build_args+="--build-arg BUILD_TYPE='$BUILD_TYPE' "
    build_args+="--build-arg GIT_COMMIT='$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")' "
    build_args+="--build-arg GIT_BRANCH='$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")' "

    # Build command
    local build_cmd="docker buildx build"
    build_cmd+=" --platform $platform"
    build_cmd+=" --tag $tag"
    build_cmd+=" --tag $latest_tag"
    build_cmd+=" $build_args"
    build_cmd+=" --file $dockerfile"

    if [ "$BUILD_TYPE" = "debug" ]; then
        build_cmd+=" --build-arg LOG_LEVEL=DEBUG"
    fi

    build_cmd+=" ."

    print_info "Executing: $build_cmd"

    if eval $build_cmd; then
        print_success "Successfully built $tag"

        # Save image to tar file
        local tar_file="${IMAGE_NAME}-${VERSION}-${arch}.tar"
        print_info "Saving image to $tar_file..."

        if docker save "$tag" | gzip > "$tar_file"; then
            print_success "Image saved to $tar_file"
            print_info "Image size: $(du -h "$tar_file" | cut -f1)"
        else
            print_warning "Failed to save image to tar file"
        fi

        return 0
    else
        print_error "Failed to build $tag"
        return 1
    fi
}

# Function to push image to registry
push_image() {
    local arch=$1
    local tag="${IMAGE_NAME}:${VERSION}-${arch}"
    local latest_tag="${IMAGE_NAME}:latest-${arch}"

    if [ -z "$REGISTRY_URL" ]; then
        print_error "Registry URL not specified. Use --registry option."
        return 1
    fi

    local remote_tag="${REGISTRY_URL}/${tag}"
    local remote_latest_tag="${REGISTRY_URL}/${latest_tag}"

    print_info "Tagging image for registry..."
    docker tag "$tag" "$remote_tag"
    docker tag "$latest_tag" "$remote_latest_tag"

    print_info "Pushing $remote_tag..."
    if docker push "$remote_tag"; then
        print_success "Successfully pushed $remote_tag"
    else
        print_error "Failed to push $remote_tag"
        return 1
    fi

    print_info "Pushing $remote_latest_tag..."
    if docker push "$remote_latest_tag"; then
        print_success "Successfully pushed $remote_latest_tag"
    else
        print_error "Failed to push $remote_latest_tag"
        return 1
    fi
}

# Function to setup buildx
setup_buildx() {
    print_info "Setting up Docker Buildx..."

    if ! docker buildx version >/dev/null 2>&1; then
        print_error "Docker Buildx is not available. Please update Docker."
        return 1
    fi

    # Create/use multiarch builder
    if ! docker buildx inspect multiarch >/dev/null 2>&1; then
        print_info "Creating multiarch builder..."
        docker buildx create --name multiarch --driver docker-container --use
    else
        print_info "Using existing multiarch builder..."
        docker buildx use multiarch
    fi

    # Bootstrap builder
    docker buildx inspect --bootstrap
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        x86_64|amd64|arm64|aarch64|both)
            ARCHITECTURE="$1"
            shift
            ;;
        --push)
            PUSH_TO_REGISTRY=true
            shift
            ;;
        --registry)
            REGISTRY_URL="$2"
            shift 2
            ;;
        --version)
            VERSION="$2"
            shift 2
            ;;
        --debug)
            BUILD_TYPE="debug"
            shift
            ;;
        --dev)
            BUILD_TYPE="development"
            shift
            ;;
        --help|-h)
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

# Main build process
main() {
    print_info "🚀 Starting Remote Control Service Docker Build"
    print_info "Architecture: $ARCHITECTURE"
    print_info "Version: $VERSION"
    print_info "Build Type: $BUILD_TYPE"
    print_info "Build Info: $(get_build_info)"
    echo ""

    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi

    # Setup buildx for multi-architecture builds
    setup_buildx

    # Build images
    local success=0

    if [ "$ARCHITECTURE" = "both" ]; then
        print_info "Building for both architectures..."

        if build_image "arm64" && build_image "amd64"; then
            print_success "All builds completed successfully"
        else
            print_error "One or more builds failed"
            success=1
        fi

        # Push if requested
        if [ "$PUSH_TO_REGISTRY" = true ] && [ $success -eq 0 ]; then
            push_image "arm64" && push_image "amd64"
        fi

    else
        if build_image "$ARCHITECTURE"; then
            print_success "Build completed successfully"

            # Push if requested
            if [ "$PUSH_TO_REGISTRY" = true ]; then
                push_image "$ARCHITECTURE"
            fi
        else
            print_error "Build failed"
            success=1
        fi
    fi

    # Summary
    echo ""
    if [ $success -eq 0 ]; then
        print_success "🎉 Docker build process completed successfully!"
        print_info "Available images:"
        docker images | grep "$IMAGE_NAME" | head -10
    else
        print_error "💥 Docker build process failed!"
    fi

    exit $success
}

# Run main function
main