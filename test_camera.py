#!/usr/bin/env python3
import cv2

# GStreamer pipeline for Tegra camera
gst_pipeline = (
    "v4l2src device=/dev/video0 ! "
    "video/x-raw, width=1280, height=720, framerate=30/1 ! "
    "videoconvert ! "
    "appsink"
)

print("Trying GStreamer pipeline...")
cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

if not cap.isOpened():
    print("Error: Cannot open camera with GStreamer")
    exit()

print("Camera opened successfully! Press 'q' to quit")

while True:
    # Read frame
    ret, frame = cap.read()

    if not ret:
        print("Error: Failed to read frame")
        break

    # Display frame
    cv2.imshow('Camera 0', frame)

    # Press 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()
