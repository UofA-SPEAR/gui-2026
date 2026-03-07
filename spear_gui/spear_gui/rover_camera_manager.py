#!/usr/bin/env python3
"""
Jetson Camera Sender - ROS2 Node
---------------------------------
Streams multiple ZED cameras over multicast UDP.

Usage:
    python3 jetson_camera_sender.py
    ros2 run <package> jetson_camera_sender
"""

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import threading
import signal
import sys
import rclpy
from rclpy.node import Node

# ──────────────────────── Config ────────────────────────

CAMERA_IDS      = [0, 1]       # ZED camera IDs to stream
BASE_PORT       = 5000          # Camera 0 -> 5000, Camera 1 -> 5001, etc.
MULTICAST_GROUP = "224.1.1.1"
BITRATE         = 4000          # kbps

# ──────────────────────── Pipeline ────────────────────────

def build_pipeline(camera_id, port):
    return (
        f"zedxonesrc camera-id={camera_id} "
        f"! queue "
        f"! videoconvert "
        f"! x264enc tune=zerolatency speed-preset=ultrafast bitrate={BITRATE} "
        f"! rtph264pay config-interval=1 pt=96 "
        f"! udpsink host={MULTICAST_GROUP} port={port} auto-multicast=true sync=false"
    )

# ──────────────────────── Camera Stream ────────────────────────

class CameraStream:
    def __init__(self, camera_id, port, logger):
        self.camera_id = camera_id
        self.port = port
        self.logger = logger
        self.pipeline = None
        self.loop = None
        self.thread = None

    def start(self):
        pipeline_str = build_pipeline(self.camera_id, self.port)
        self.logger.info(f"Camera {self.camera_id} pipeline: {pipeline_str}")

        self.pipeline = Gst.parse_launch(pipeline_str)
        if not self.pipeline:
            self.logger.error(f"Camera {self.camera_id}: failed to create pipeline")
            return

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        self.loop = GLib.MainLoop()
        bus.connect("message", self._on_message)

        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            self.logger.error(f"Camera {self.camera_id}: failed to set pipeline to PLAYING")
            return

        self.logger.info(f"Camera {self.camera_id} streaming on {MULTICAST_GROUP}:{self.port}")
        self.thread = threading.Thread(target=self.loop.run, daemon=True)
        self.thread.start()

    def stop(self):
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
        if self.loop:
            self.loop.quit()
        if self.thread:
            self.thread.join(timeout=2)
        self.logger.info(f"Camera {self.camera_id} stopped")

    def _on_message(self, bus, message):
        if message.type == Gst.MessageType.EOS:
            self.logger.info(f"Camera {self.camera_id}: end of stream")
            self.loop.quit()
        elif message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            self.logger.error(f"Camera {self.camera_id} error: {err}")
            self.logger.error(f"Camera {self.camera_id} debug: {debug}")
            self.loop.quit()

# ──────────────────────── ROS2 Node ────────────────────────

class CameraSenderNode(Node):
    def __init__(self):
        super().__init__('camera_sender_node')
        Gst.init(None)

        self.streams = []
        for camera_id in CAMERA_IDS:
            port = BASE_PORT + camera_id
            stream = CameraStream(camera_id, port, self.get_logger())
            self.streams.append(stream)

        self.get_logger().info(f"Starting {len(self.streams)} camera stream(s)...")
        self.get_logger().info(f"Multicast group: {MULTICAST_GROUP}")
        self.get_logger().info(f"Ports: {[BASE_PORT + cid for cid in CAMERA_IDS]}")

        for stream in self.streams:
            stream.start()

    def shutdown(self):
        self.get_logger().info("Shutting down streams...")
        for stream in self.streams:
            stream.stop()

# ──────────────────────── Main ────────────────────────

def main():
    rclpy.init()
    node = CameraSenderNode()

    def on_sigint(sig, frame):
        node.shutdown()
        rclpy.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, on_sigint)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.shutdown()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()