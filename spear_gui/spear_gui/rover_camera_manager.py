#!/usr/bin/env python3
"""
Jetson Camera Sender - ROS2 Node
---------------------------------
Streams multiple ZED cameras over UDP to a receiver machine.

Usage:
    python3 jetson_camera_sender.py
    ros2 run <package> jetson_camera_sender
"""

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import threading
import sys
import rclpy
from rclpy.node import Node

# ──────────────────────── Config ────────────────────────

RECEIVER_IP = "192.168.8.224"  # IP of the machine receiving the stream
BITRATE     = 4000              # kbps

CAMERAS = [
    {"camera_id": 0, "source": "zedxonesrc", "port": 5000},
    {"camera_id": 1, "source": "zedxonesrc", "port": 5001},
    {"camera_id": 0, "source": "zedsrc",     "port": 5002},  # ZED X Mini
]

# ──────────────────────── Pipeline ────────────────────────

def build_pipeline(source, camera_id, port):
    return (
        f"{source} camera-id={camera_id} "
        f"! queue "
        f"! videoconvert "
        f"! x264enc tune=zerolatency speed-preset=ultrafast bitrate={BITRATE} "
        f"! rtph264pay config-interval=1 pt=96 "
        f"! udpsink host={RECEIVER_IP} port={port} sync=false"
    )

# ──────────────────────── Camera Stream ────────────────────────

class CameraStream:
    def __init__(self, source, camera_id, port, logger):
        self.source = source
        self.camera_id = camera_id
        self.port = port
        self.logger = logger
        self.pipeline = None
        self.loop = None
        self.thread = None

    def start(self):
        pipeline_str = build_pipeline(self.source, self.camera_id, self.port)
        self.logger.info(f"[{self.source} cam {self.camera_id}] pipeline: {pipeline_str}")

        self.pipeline = Gst.parse_launch(pipeline_str)
        if not self.pipeline:
            self.logger.error(f"[{self.source} cam {self.camera_id}] failed to create pipeline")
            return

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        self.loop = GLib.MainLoop()
        bus.connect("message", self._on_message)

        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            self.logger.error(f"[{self.source} cam {self.camera_id}] failed to set pipeline to PLAYING")
            return

        self.logger.info(f"[{self.source} cam {self.camera_id}] streaming to {RECEIVER_IP}:{self.port}")
        self.thread = threading.Thread(target=self.loop.run, daemon=True)
        self.thread.start()

    def stop(self):
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
        if self.loop:
            self.loop.quit()
        if self.thread:
            self.thread.join(timeout=2)
        self.logger.info(f"[{self.source} cam {self.camera_id}] stopped")

    def _on_message(self, bus, message):
        if message.type == Gst.MessageType.EOS:
            self.logger.info(f"[{self.source} cam {self.camera_id}] end of stream")
            self.loop.quit()
        elif message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            self.logger.error(f"[{self.source} cam {self.camera_id}] error: {err}")
            self.logger.error(f"[{self.source} cam {self.camera_id}] debug: {debug}")
            self.loop.quit()

# ──────────────────────── ROS2 Node ────────────────────────

class CameraSenderNode(Node):
    def __init__(self):
        super().__init__('camera_sender_node')
        Gst.init(None)

        self.streams = []
        for cam in CAMERAS:
            stream = CameraStream(cam["source"], cam["camera_id"], cam["port"], self.get_logger())
            self.streams.append(stream)

        self.get_logger().info(f"Starting {len(self.streams)} camera stream(s)...")
        self.get_logger().info(f"Receiver: {RECEIVER_IP}")
        for cam in CAMERAS:
            self.get_logger().info(f"  {cam['source']} camera-id={cam['camera_id']} -> port {cam['port']}")

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