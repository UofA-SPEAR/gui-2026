#!/usr/bin/env python3
import cv2

# GStreamer pipeline for ZED X One camera
gst_pipeline = (
    "zedxonesrc camera-id=0 camera-resolution=2 camera-fps=30 ! "
    "queue ! "
    "videoconvert ! "
    "video/x-raw, format=BGR ! "
    "appsink"
)

print("Opening ZED X One camera with GStreamer...")
cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

if not cap.isOpened():
    print("Error: Cannot open ZED X One camera")
    exit(-1)

print("ZED X One camera opened successfully! Press 'q' to quit")

while True:
    ret, frame = cap.read()

    if not ret:
        print("Error: Failed to read frame")
        break

    cv2.imshow("ZED X One Camera", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
