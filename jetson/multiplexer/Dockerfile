# Multi-stage Dockerfile for Motor Controller Proxy/Multiplexer
# Supports both amd64 and arm64 architectures
# Target deployment: Nvidia Jetson Nano (ARM64)

FROM python:3.9-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libc-dev \
    udev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r motor && useradd -r -g motor motor

# Set working directory
WORKDIR /app

# Copy requirements first for better cache layering
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY src/ ./src/
COPY main.py .

# Create necessary directories and set permissions
RUN mkdir -p /var/log/motor-proxy /tmp/motor-proxy && \
    chown -R motor:motor /app /var/log/motor-proxy /tmp/motor-proxy

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Function to handle shutdown\n\
shutdown_handler() {\n\
    echo "🛑 Received shutdown signal, stopping motor proxy..."\n\
    kill -TERM "$child" 2>/dev/null || true\n\
    wait "$child"\n\
    echo "👋 Motor proxy stopped"\n\
    exit 0\n\
}\n\
\n\
# Set up signal handlers\n\
trap shutdown_handler SIGTERM SIGINT\n\
\n\
# Print startup information\n\
echo "🚀 Starting Motor Controller Proxy/Multiplexer"\n\
echo "📅 $(date)"\n\
echo "🏗️  Architecture: $(uname -m)"\n\
echo "🐍 Python version: $(python --version)"\n\
echo "👤 Running as: $(whoami)"\n\
echo "📂 Working directory: $(pwd)"\n\
echo "🔧 Environment variables:"\n\
env | grep -E "^(SERIAL_|SOCKET_|LOG_)" | sort || echo "   No motor proxy environment variables set"\n\
echo ""\n\
\n\
# Detect available serial ports\n\
echo "🔍 Detecting available serial ports..."\n\
if ls /dev/ttyACM* 2>/dev/null; then\n\
    echo "✅ Found Arduino-compatible ports"\n\
elif ls /dev/ttyUSB* 2>/dev/null; then\n\
    echo "✅ Found USB serial ports"\n\
else\n\
    echo "⚠️  No serial ports detected - ensure Arduino is connected"\n\
fi\n\
echo ""\n\
\n\
# Build command line arguments from environment variables\n\
ARGS=()\n\
if [ -n "$SERIAL_PORT" ]; then\n\
    ARGS+=(--serial-port "$SERIAL_PORT")\n\
fi\n\
if [ -n "$BAUD_RATE" ]; then\n\
    ARGS+=(--baud-rate "$BAUD_RATE")\n\
fi\n\
if [ -n "$SOCKET_PATH" ]; then\n\
    ARGS+=(--socket-path "$SOCKET_PATH")\n\
fi\n\
if [ -n "$LOG_LEVEL" ]; then\n\
    ARGS+=(--log-level "$LOG_LEVEL")\n\
fi\n\
if [ -n "$LOG_FILE" ]; then\n\
    ARGS+=(--log-file "$LOG_FILE")\n\
fi\n\
if [ "$DAEMON_MODE" = "true" ]; then\n\
    ARGS+=(--daemon)\n\
fi\n\
\n\
# Start the motor proxy\n\
echo "🎯 Starting with arguments: ${ARGS[*]}"\n\
python main.py "${ARGS[@]}" &\n\
child=$!\n\
\n\
# Wait for child process\n\
wait "$child"\n' > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Switch to non-root user
USER motor

# Expose volume for socket file
VOLUME ["/tmp/motor-proxy"]

# Environment variables with defaults
ENV SERIAL_PORT=""
ENV BAUD_RATE=115200
ENV SOCKET_PATH=/tmp/motor-proxy/motor_controller.sock
ENV LOG_LEVEL=INFO
ENV LOG_FILE=""
ENV DAEMON_MODE=false

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD test -S "${SOCKET_PATH}" || exit 1

# Labels for metadata
LABEL maintainer="Motor Proxy Team" \
      version="1.0.0" \
      description="Arduino Motor Controller Proxy/Multiplexer Service" \
      target="Nvidia Jetson Nano"

# Entry point
ENTRYPOINT ["/app/entrypoint.sh"]