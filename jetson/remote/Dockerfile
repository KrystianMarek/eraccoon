# Remote Control Service for Mecanum Wheel Robot
# Production Docker Image

FROM python:3.11-slim

# Set metadata
LABEL maintainer="Remote Control Team"
LABEL description="Remote Control Service for Mecanum Wheel Robot"
LABEL version="1.0.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV MODE=production

# Create app user (security best practice)
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    # Required for controller access
    udev \
    # Required for pygame (even in headless mode)
    libasound2-dev \
    libpulse-dev \
    libaudio-dev \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libxtst6 \
    libxi6 \
    # Required for input device access
    libevdev2 \
    libudev1 \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy requirements first (for better Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY src/ ./src/

# Create directories for runtime
RUN mkdir -p /tmp/remote-control \
    && chown -R appuser:appuser /app /tmp/remote-control

# Switch to app user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command
CMD ["python", "main.py", "--mode", "production"]
