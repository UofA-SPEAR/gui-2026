#!/usr/bin/env python3
"""
Jetson Camera Sender
--------------------
Captures from ZED camera and streams over UDP to a receiver machine.

Usage:
    python3 jetson_camera_sender.py --host 192.168.1.100 --port 5000 --camera-id 0
"""

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import argparse
import signal
import sys


def build_pipeline(host, port, camera_id):
    return (
        f"zedxonesrc camera-id={camera_id} "
        f"! queue "
        f"! videoconvert "
        f"! x264enc tune=zerolatency speed-preset=ultrafast bitrate=4000 "
        f"! rtph264pay config-interval=1 pt=96 "
        f"! udpsink host={host} port={port} sync=false"
    )


def main():
    parser = argparse.ArgumentParser(description="Stream ZED camera over UDP")
    parser.add_argument("--host", required=True, help="IP of the receiver machine")
    parser.add_argument("--port", type=int, default=5000, help="UDP port (default: 5000)")
    parser.add_argument("--camera-id", type=int, default=0, help="ZED camera ID (default: 0)")
    args = parser.parse_args()

    Gst.init(None)

    pipeline_str = build_pipeline(args.host, args.port, args.camera_id)
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
        if message.type == Gst.MessageType.EOS:
            print("End of stream")
            loop.quit()
        elif message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"Error: {err}", file=sys.stderr)
            print(f"Debug: {debug}", file=sys.stderr)
            loop.quit()

    bus.connect("message", on_message)

    ret = pipeline.set_state(Gst.State.PLAYING)
    if ret == Gst.StateChangeReturn.FAILURE:
        print("Failed to start pipeline", file=sys.stderr)
        sys.exit(1)

    print("Streaming... Press Ctrl+C to stop.")

    signal.signal(signal.SIGINT, lambda s, f: loop.quit())

    try:
        loop.run()
    finally:
        pipeline.set_state(Gst.State.NULL)
        print("Pipeline stopped.")


if __name__ == "__main__":
    main()