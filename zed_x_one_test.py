#!/usr/bin/env python3
"""
Simple GStreamer test script for ZED X One camera
Displays the camera stream with FPS information
"""

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import sys

def on_message(bus, message, loop):
    """Handle GStreamer bus messages"""
    mtype = message.type
    
    if mtype == Gst.MessageType.EOS:
        print("End of stream")
        loop.quit()
    elif mtype == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        print(f"Error: {err}", file=sys.stderr)
        print(f"Debug info: {debug}", file=sys.stderr)
        loop.quit()
    elif mtype == Gst.MessageType.WARNING:
        err, debug = message.parse_warning()
        print(f"Warning: {err}", file=sys.stderr)
    
    return True

def main():
    # Initialize GStreamer
    Gst.init(None)
    
    # Create pipeline
    # This opens the first ZED X One camera with default settings (HD1200 @ 30 FPS)
    pipeline_str = "zedxonesrc ! queue ! autovideoconvert ! queue ! fpsdisplaysink"
    
    print(f"Creating pipeline: {pipeline_str}")
    pipeline = Gst.parse_launch(pipeline_str)
    
    if not pipeline:
        print("Failed to create pipeline", file=sys.stderr)
        return -1
    
    # Create main loop
    loop = GLib.MainLoop()
    
    # Get bus and add signal watch
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", on_message, loop)
    
    # Start playing
    print("Starting pipeline...")
    ret = pipeline.set_state(Gst.State.PLAYING)
    
    if ret == Gst.StateChangeReturn.FAILURE:
        print("Unable to set the pipeline to playing state", file=sys.stderr)
        return -1
    
    print("Pipeline is running. Press Ctrl+C to stop.")
    
    # Run main loop
    try:
        loop.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    # Clean up
    print("Stopping pipeline...")
    pipeline.set_state(Gst.State.NULL)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())