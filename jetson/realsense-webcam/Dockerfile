# Multi-stage Dockerfile for RealSense D435i Web Streaming Application
# Supports both amd64 and arm64 architectures
# Target deployment: Nvidia Jetson Nano (ARM64)

FROM python:3.8-slim AS base

# Install system dependencies for RealSense and OpenCV
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libc-dev \
    udev \
    libusb-1.0-0-dev \
    libudev-dev \
    pkg-config \
    python3-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libfontconfig1 \
    libice6 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r realsense && useradd -r -g realsense realsense

# Set working directory
WORKDIR /app

# Copy requirements first for better cache layering
COPY requirements.txt .

# Install Python dependencies including pyrealsense2
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir pyrealsense2==2.55.1.6486

# Copy application source code
COPY app.py .
COPY templates/ ./templates/

# Create necessary directories and set permissions
RUN mkdir -p /var/log/realsense-webcam && \
    chown -R realsense:realsense /app /var/log/realsense-webcam

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Function to handle shutdown\n\
shutdown_handler() {\n\
    echo "🛑 Received shutdown signal, stopping RealSense webcam..."\n\
    kill -TERM "$child" 2>/dev/null || true\n\
    wait "$child"\n\
    echo "👋 RealSense webcam stopped"\n\
    exit 0\n\
}\n\
\n\
# Set up signal handlers\n\
trap shutdown_handler SIGTERM SIGINT\n\
\n\
# Print startup information\n\
echo "🚀 Starting RealSense D435i Web Streaming Application"\n\
echo "📅 $(date)"\n\
echo "🏗️  Architecture: $(uname -m)"\n\
echo "🐍 Python version: $(python --version)"\n\
echo "👤 Running as: $(whoami)"\n\
echo "📂 Working directory: $(pwd)"\n\
echo "🔧 Environment variables:"\n\
env | grep -E "^(FLASK_|REALSENSE_)" | sort || echo "   No RealSense environment variables set"\n\
echo ""\n\
\n\
# Check for RealSense devices\n\
echo "🔍 Detecting RealSense devices..."\n\
if ls /dev/video* 2>/dev/null; then\n\
    echo "✅ Found video devices:"\n\
    ls -la /dev/video* | head -5\n\
else\n\
    echo "⚠️  No video devices detected"\n\
fi\n\
\n\
if python -c "import pyrealsense2 as rs; ctx = rs.context(); devices = ctx.devices; print(f'"'"'📹 Found {len(devices)} RealSense device(s)'"'"')" 2>/dev/null; then\n\
    echo "✅ RealSense SDK working correctly"\n\
else\n\
    echo "⚠️  RealSense SDK not detecting devices - ensure camera is connected"\n\
fi\n\
echo ""\n\
\n\
# Build command line arguments from environment variables\n\
ARGS=()\n\
if [ -n "$FLASK_PORT" ]; then\n\
    ARGS+=(--port "$FLASK_PORT")\n\
fi\n\
if [ -n "$FLASK_HOST" ]; then\n\
    ARGS+=(--host "$FLASK_HOST")\n\
fi\n\
\n\
# Get local IP for convenience\n\
LOCAL_IP=$(hostname -i 2>/dev/null || echo "unknown")\n\
FLASK_PORT_VAL=${FLASK_PORT:-5000}\n\
FLASK_HOST_VAL=${FLASK_HOST:-0.0.0.0}\n\
\n\
echo "🌐 Access the stream at:"\n\
echo "   Local: http://localhost:${FLASK_PORT_VAL}"\n\
echo "   Container: http://${LOCAL_IP}:${FLASK_PORT_VAL}"\n\
echo "   Network: http://[HOST_IP]:${FLASK_PORT_VAL}"\n\
echo "📱 Use the network address from mobile devices"\n\
echo "🛑 Press Ctrl+C to stop the application"\n\
echo ""\n\
\n\
# Start the RealSense web app\n\
echo "🎯 Starting Flask application..."\n\
python app.py &\n\
child=$!\n\
\n\
# Wait for child process\n\
wait "$child"\n' > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Switch to non-root user
USER realsense

# Expose the Flask port
EXPOSE 5000

# Environment variables with defaults
ENV FLASK_HOST=0.0.0.0
ENV FLASK_PORT=5000
ENV FLASK_ENV=production

# Health check - test if the Flask app is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${FLASK_PORT}/status || exit 1

# Labels for metadata
LABEL maintainer="RealSense Webcam Team" \
      version="1.0.0" \
      description="Intel RealSense D435i Web Streaming Application" \
      target="Nvidia Jetson Nano" \
      python.version="3.8"

# Entry point
ENTRYPOINT ["/app/entrypoint.sh"]