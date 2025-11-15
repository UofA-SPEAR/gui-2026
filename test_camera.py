#!/usr/bin/env python3
import cv2
import pyzed.sl as sl

# Create a ZED camera object
zed = sl.Camera()

# Set configuration parameters for GMSL camera
init_params = sl.InitParameters()
init_params.camera_resolution = sl.RESOLUTION.HD720  # Use HD720 video mode
init_params.camera_fps = 30  # Set fps at 30

# For ZED X cameras connected via GMSL2, use set_from_camera_id
init_params.set_from_camera_id(0)

# Open the camera
err = zed.open(init_params)
if err != sl.ERROR_CODE.SUCCESS:
    print(f"Error opening ZED camera: {err}")
    exit(-1)

print("ZED camera opened successfully! Press 'q' to quit")

# Create sl.Mat objects to store images
image_zed = sl.Mat()

while True:
    # Grab a new frame
    if zed.grab() == sl.ERROR_CODE.SUCCESS:
        # Retrieve the left image
        zed.retrieve_image(image_zed, sl.VIEW.LEFT)

        # Convert to numpy array for OpenCV
        image_ocv = image_zed.get_data()

        # Display the image
        cv2.imshow("ZED Camera", image_ocv)

    # Press 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
zed.close()
cv2.destroyAllWindows()
