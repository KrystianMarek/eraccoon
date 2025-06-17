#!/bin/bash

# RealSense Webcam Streaming Application
# Run script for Jetson Nano

echo "🚀 Starting RealSense D435i Web Streaming Application..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please create one first:"
    echo "python3 -m venv .venv"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source .venv/bin/activate

# Check if requirements are installed
echo "🔍 Checking dependencies..."
pip install -r requirements.txt

# Check if RealSense camera is connected
echo "📹 Checking for RealSense camera..."
if ! python3 -c "import pyrealsense2 as rs; ctx = rs.context(); print(f'Found {len(ctx.devices)} RealSense device(s)')"; then
    echo "❌ Error: Could not detect RealSense camera or pyrealsense2 not available"
    echo "Please ensure:"
    echo "1. RealSense D435i is connected via USB 3.0"
    echo "2. pyrealsense2 is available in the system Python"
    echo "3. User has permissions to access the camera"
    exit 1
fi

# Get local IP address for convenience
LOCAL_IP=$(hostname -I | awk '{print $1}')

echo "✅ Starting Flask web application..."
echo "🌐 Access the stream at:"
echo "   Local: http://localhost:5000"
echo "   Network: http://$LOCAL_IP:5000"
echo ""
echo "📱 On mobile devices, use the network address"
echo "🛑 Press Ctrl+C to stop the application"
echo ""

# Run the application
python3 app.py