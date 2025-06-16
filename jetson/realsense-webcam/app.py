#!/usr/bin/env python3
"""
RealSense D435i Web Streaming Application
Streams RGB and Depth camera feeds to a web interface
"""

import cv2
import numpy as np
import pyrealsense2 as rs
from flask import Flask, render_template, Response
import threading
import time

app = Flask(__name__)

class RealSenseCamera:
    def __init__(self):
        self.pipeline = None
        self.config = None
        self.is_streaming = False
        self.rgb_frame = None
        self.depth_frame = None
        self.lock = threading.Lock()

    def start_streaming(self):
        """Initialize and start the RealSense pipeline"""
        try:
            print("Initializing RealSense camera...")

            # Configure depth and color streams
            self.pipeline = rs.pipeline()
            self.config = rs.config()

            # Get device product line for setting a supporting resolution
            pipeline_wrapper = rs.pipeline_wrapper(self.pipeline)
            pipeline_profile = self.config.resolve(pipeline_wrapper)
            device = pipeline_profile.get_device()
            device_product_line = str(device.get_info(rs.camera_info.product_line))

            print(f"Device product line: {device_product_line}")
            print(f"Device name: {device.get_info(rs.camera_info.name)}")
            print(f"Device serial: {device.get_info(rs.camera_info.serial_number)}")

            # Check for RGB camera
            found_rgb = False
            sensors = device.sensors
            print(f"Found {len(sensors)} sensors:")
            for i, s in enumerate(sensors):
                sensor_name = s.get_info(rs.camera_info.name)
                print(f"  Sensor {i}: {sensor_name}")
                if sensor_name == 'RGB Camera':
                    found_rgb = True

            if not found_rgb:
                print("ERROR: RGB Camera sensor not found!")
                return False

            print("Configuring streams...")
            # Configure streams with more conservative settings
            self.config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
            self.config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

            print("Starting pipeline...")
            # Start streaming
            profile = self.pipeline.start(self.config)

            # Get stream details
            depth_stream = profile.get_stream(rs.stream.depth)
            color_stream = profile.get_stream(rs.stream.color)
            print(f"Depth stream: {depth_stream}")
            print(f"Color stream: {color_stream}")

            self.is_streaming = True

            # Start capture thread
            print("Starting capture thread...")
            self.capture_thread = threading.Thread(target=self._capture_frames)
            self.capture_thread.daemon = True
            self.capture_thread.start()

            print("RealSense streaming started successfully")
            return True

        except Exception as e:
            print(f"Error starting RealSense: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _capture_frames(self):
        """Continuously capture frames from the camera"""
        print("Frame capture thread started")
        frame_count = 0

        while self.is_streaming:
            try:
                # Wait for a coherent pair of frames: depth and color (with timeout)
                frames = self.pipeline.wait_for_frames(timeout_ms=5000)
                depth_frame = frames.get_depth_frame()
                color_frame = frames.get_color_frame()

                if not depth_frame or not color_frame:
                    print(f"Missing frames - depth: {depth_frame is not None}, color: {color_frame is not None}")
                    continue

                # Convert images to numpy arrays
                depth_image = np.asanyarray(depth_frame.get_data())
                color_image = np.asanyarray(color_frame.get_data())

                # Apply colormap on depth image (image must be converted to 8-bit per pixel first)
                depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)

                with self.lock:
                    self.rgb_frame = color_image.copy()
                    self.depth_frame = depth_colormap.copy()

                frame_count += 1
                if frame_count % 30 == 0:  # Log every 30 frames (roughly every second at 30fps)
                    print(f"Captured {frame_count} frames successfully")

            except RuntimeError as e:
                print(f"Runtime error capturing frame: {e}")
                if "No device is connected" in str(e):
                    print("Camera disconnected, stopping capture")
                    self.is_streaming = False
                    break
                time.sleep(0.1)
            except Exception as e:
                print(f"Unexpected error capturing frame: {e}")
                time.sleep(0.1)

        print("Frame capture thread ended")

    def get_rgb_frame(self):
        """Get the latest RGB frame"""
        with self.lock:
            return self.rgb_frame.copy() if self.rgb_frame is not None else None

    def get_depth_frame(self):
        """Get the latest depth frame"""
        with self.lock:
            return self.depth_frame.copy() if self.depth_frame is not None else None

    def stop_streaming(self):
        """Stop the RealSense pipeline"""
        self.is_streaming = False
        if self.pipeline:
            self.pipeline.stop()

# Global camera instance
camera = RealSenseCamera()

def generate_frames(stream_type='rgb'):
    """Generate video frames for streaming"""
    while True:
        if stream_type == 'rgb':
            frame = camera.get_rgb_frame()
        elif stream_type == 'depth':
            frame = camera.get_depth_frame()
        else:
            frame = None

        if frame is not None:
            # Encode frame to JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        else:
            # If no frame available, wait a bit
            time.sleep(0.1)

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/video_feed_rgb')
def video_feed_rgb():
    """RGB video streaming route"""
    return Response(generate_frames('rgb'),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed_depth')
def video_feed_depth():
    """Depth video streaming route"""
    return Response(generate_frames('depth'),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def status():
    """Camera status endpoint"""
    return {
        'streaming': camera.is_streaming,
        'rgb_frame_available': camera.rgb_frame is not None,
        'depth_frame_available': camera.depth_frame is not None,
        'pipeline_active': camera.pipeline is not None
    }

@app.route('/debug')
def debug():
    """Debug endpoint with detailed camera information"""
    try:
        ctx = rs.context()
        devices = ctx.devices
        device_info = []

        for i, device in enumerate(devices):
            info = {
                'index': i,
                'name': device.get_info(rs.camera_info.name),
                'serial': device.get_info(rs.camera_info.serial_number),
                'product_line': device.get_info(rs.camera_info.product_line)
            }
            device_info.append(info)

        return {
            'camera_status': {
                'streaming': camera.is_streaming,
                'rgb_frame_available': camera.rgb_frame is not None,
                'depth_frame_available': camera.depth_frame is not None,
                'pipeline_active': camera.pipeline is not None
            },
            'realsense_devices': device_info,
            'device_count': len(devices)
        }
    except Exception as e:
        return {
            'error': str(e),
            'camera_status': {
                'streaming': camera.is_streaming,
                'rgb_frame_available': camera.rgb_frame is not None,
                'depth_frame_available': camera.depth_frame is not None,
                'pipeline_active': camera.pipeline is not None
            }
        }

if __name__ == '__main__':
    # Start the camera
    if camera.start_streaming():
        try:
            # Run the Flask app
            app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
        finally:
            # Clean up
            camera.stop_streaming()
    else:
        print("Failed to start camera. Please check your RealSense connection.")