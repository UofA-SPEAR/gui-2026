#!/usr/bin/env python3
import cv2

# Open camera 0
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Cannot open camera 0")
    exit()

print("Press 'q' to quit")

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
