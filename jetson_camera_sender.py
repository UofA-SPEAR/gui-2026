#!/usr/bin/env python3
"""
Jetson Camera Sender
--------------------
Captures from ZED camera and streams over UDP to a receiver machine.

Usage:
    python3 jetson_camera_sender.py --host 192.168.1.100 --port 5000 --camera-id 0

Requirements:
    - ZED SDK with GStreamer plugin (zedxonesrc)
    - gstreamer1.0-plugins-good (for rtph264pay, udpsink)
    - gstreamer1.0-plugins-bad or nvidia plugins for encoding
"""

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import argparse
import signal
import sys


def build_pipeline(host, port, camera_id):
    # Try hardware encoder first (Jetson), fall back to software
    pipeline_str = (
        f"zedxonesrc camera-id={camera_id} "
        f"! queue "
        f"! videoconvert "
        f"! nvv4l2h264enc iframeinterval=30 bitrate=4000000 "  # Jetson HW encoder
        f"! rtph264pay config-interval=1 pt=96 "
        f"! udpsink host={host} port={port} sync=false"
    )
    return pipeline_str


def build_pipeline_software(host, port, camera_id):
    # Fallback: software encoding (slower, works on any machine)
    pipeline_str = (
        f"zedxonesrc camera-id={camera_id} "
        f"! queue "
        f"! videoconvert "
        f"! x264enc tune=zerolatency speed-preset=ultrafast bitrate=4000 "
        f"! rtph264pay config-interval=1 pt=96 "
        f"! udpsink host={host} port={port} sync=false"
    )
    return pipeline_str


def main():
    parser = argparse.ArgumentParser(description="Stream ZED camera over UDP")
    parser.add_argument("--host", required=True, help="IP of the receiver machine")
    parser.add_argument("--port", type=int, default=5000, help="UDP port (default: 5000)")
    parser.add_argument("--camera-id", type=int, default=0, help="ZED camera ID (default: 0)")
    parser.add_argument("--software", action="store_true", help="Force software encoding (x264)")
    args = parser.parse_args()

    Gst.init(None)

    if args.software:
        pipeline_str = build_pipeline_software(args.host, args.port, args.camera_id)
        print("Using software encoding (x264)")
    else:
        pipeline_str = build_pipeline(args.host, args.port, args.camera_id)
        print("Using hardware encoding (nvv4l2h264enc)")

    print(f"Pipeline: {pipeline_str}")
    print(f"Streaming to {args.host}:{args.port}")

    pipeline = Gst.parse_launch(pipeline_str)
    if not pipeline:
        print("Failed to create pipeline", file=sys.stderr)
        sys.exit(1)

    bus = pipeline.get_bus()
    bus.add_signal_watch()
    loop = GLib.MainLoop()

    def on_message(bus, message):
        mtype = message.type
        if mtype == Gst.MessageType.EOS:
            print("End of stream")
            loop.quit()
        elif mtype == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"Error: {err}", file=sys.stderr)
            print(f"Debug: {debug}", file=sys.stderr)

            if "nvv4l2h264enc" in str(debug) or "nvv4l2h264enc" in str(err):
                print("\nHardware encoder failed. Try running with --software flag.", file=sys.stderr)

            loop.quit()

    bus.connect("message", on_message)

    ret = pipeline.set_state(Gst.State.PLAYING)
    if ret == Gst.StateChangeReturn.FAILURE:
        print("Failed to start pipeline", file=sys.stderr)
        sys.exit(1)

    print("Streaming... Press Ctrl+C to stop.")

    def shutdown(sig, frame):
        print("\nStopping...")
        loop.quit()

    signal.signal(signal.SIGINT, shutdown)

    try:
        loop.run()
    finally:
        pipeline.set_state(Gst.State.NULL)
        print("Pipeline stopped.")


if __name__ == "__main__":
    main()