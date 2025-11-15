import rclpy
from rclpy.node import Node
from PySide6.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QGraphicsPixmapItem
from PySide6.QtCore import QTimer, QVariantAnimation, QEasingCurve, Qt
from PySide6.QtGui import QPen, QPainter, QImage, QPixmap
from std_msgs.msg import String
import cv2
import glob
import numpy as np

class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')

        self.scene = None
        self.view = None

        self.window_width = 800
        self.window_height = 600

        # Auto-detect video devices
        self.detect_cameras()

        self.active = [False] * self.total_cameras
        self.indexes = [-1] * self.total_cameras
        self.pixmap_items = {}
        self.animations = {}
        self.video_captures = {} 

        self.target_ratios = [
            [[1, 1], [0, 1]], 
            [[2.0/3.0, 1], [1.0/3.0, 1], [0.5, 0]], 
            [[0.5, 1], [0.5, 0.5], [0.5, 0.5], [0.5, 0]], 
            [[0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0, 0.5]], 
            [[0.5, 0.5], [0.5, 0.5], [1.0/3.0, 0.5], [1.0/3.0, 0.5], [1.0/3.0, 0.5], [0, 0.5]], 
            [[1.0/3.0, 0.5], [1.0/3.0, 0.5], [1.0/3.0, 0.5], [1.0/3.0, 0.5], [1.0/3.0, 0.5], [1.0/3.0, 0.5]]
        ]
        self.target_positions = [
            [[0, 0], [1, 0]],
            [[0, 0], [2.0/3.0, 0], [0.5, 1]],
            [[0, 0], [0.5, 0], [0.5, 0.5], [0, 1]],
            [[0, 0], [0.5, 0], [0.5, 0.5], [0, 0.5], [1.0/3.0, 0.5]],
            [[0, 0], [0.5, 0], [2.0/3.0, 0.5], [1.0/3.0, 0.5], [0, 0.5], [0, 0.5]],
            [[1.0/3.0, 0], [2.0/3.0, 0], [2.0/3.0, 0.5], [1.0/3.0, 0.5], [0, 0.5], [0, 0]]
        ]

        self.key_subscription = self.create_subscription(
            String, 'key', self.key_listener, 10
        )

    def detect_cameras(self):
        """Detect available /dev/video* devices."""
        video_devices = sorted(glob.glob('/dev/video*'))
        self.camera_id = [int(dev.replace('/dev/video', '')) for dev in video_devices]
        self.total_cameras = len(self.camera_id)

        if self.total_cameras == 0:
            self.get_logger().warn("No /dev/video* devices found. Using dummy camera.")
            self.camera_id = [0]
            self.total_cameras = 1
        else:
            self.get_logger().info(f"Detected cameras: {self.camera_id}")

    def setup_gui(self, parent=None):
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene, parent)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setRenderHint(QPainter.SmoothPixmapTransform)
        self.view.setFixedSize(self.window_width, self.window_height)

        # Timer to update camera frames
        self.frame_timer = QTimer()
        self.frame_timer.timeout.connect(self.update_frames)
        self.frame_timer.start(33)  # ~30 FPS

        self.get_logger().info("GUI setup complete.")

    def key_listener(self, key_msg):
        key = key_msg.data
        self.get_logger().info(f"Received key: {key}")
        if key == 'p':
            self.get_logger().info("Exiting...")
            rclpy.shutdown()
        elif key == 'w':
            self.activate_camera(self.get_available_index())
        elif key == 's':
            self.deactivate_camera()
        elif key == 'd':
            used = self.get_used_indexes()
            if used:
                self.move_index(max(used), 1)
        elif key == 'a':
            used = self.get_used_indexes()
            if used:
                self.move_index(max(used), -1)

    def get_used_indexes(self):
        used = {idx for idx in self.indexes if idx != -1}
        self.get_logger().info(f"Used indexes: {used}")
        return used
    
    def get_inactive_indexes(self):
        get_inactive_indexes = {}
        for i in range(len(self.active)):
            if not self.active[i]:
                active.append(i)
        return inactive

    def get_active_indexes(self):
        active = []
        for i in range(len(self.active)):
            if self.active[i]:
                active.append(i)
        return active

    def get_available_index(self):
        used = self.get_used_indexes()
        available_index = next((i for i in range(self.total_cameras) if i not in used), None)
        if available_index == None:
            available_index = next(get_inactive_indexes())
        self.get_logger().info(f"Available index: {available_index}")
        return available_index

    def activate_camera(self, cam_id):
        self.get_logger().info(f"Activating camera {cam_id}")
        if cam_id is None or self.active[cam_id]:
            self.get_logger().info(f"Camera {cam_id} is already active or invalid.")
            return

        self.active[cam_id] = True
        if self.indexes[cam_id] == -1:
            new_index = self.get_available_index()
            if new_index is not None:
                self.indexes[cam_id] = new_index

        # Open video capture for this camera
        video_index = self.camera_id[cam_id]
        self.video_captures[cam_id] = cv2.VideoCapture(video_index)
        if not self.video_captures[cam_id].isOpened():
            self.get_logger().warn(f"Failed to open camera /dev/video{video_index}. Using dummy feed.")
            self.video_captures[cam_id] = None

        self.create_camera_item(cam_id)
        self.set_camera_positions()

    def deactivate_camera(self):
        active = self.get_active_indexes()
        if not active:
            self.get_logger().info("No active cameras to deactivate.")
            return

        # Find the camera ID with the highest index
        cam_id = None
        max_idx = max(used)
        for cid, idx in enumerate(self.indexes):
            if idx == max_idx:
                cam_id = cid
                break

        if cam_id is None:
            return

        self.get_logger().info(f"Deactivating camera {cam_id}")
        self.active[cam_id] = False
        self.indexes[cam_id] = -1

        # Release video capture
        if cam_id in self.video_captures and self.video_captures[cam_id] is not None:
            self.video_captures[cam_id].release()
            del self.video_captures[cam_id]

        # Remove pixmap item from scene
        item = self.pixmap_items.pop(cam_id, None)
        if item:
            self.scene.removeItem(item)

        self.set_camera_positions()

    def move_index(self, cam_id, direction):
        self.get_logger().info(f"Moving camera {cam_id} by {direction} index.")
        if not self.active[cam_id]:
            self.get_logger().info(f"Camera {cam_id} is not active.")
            return

        start_index = self.indexes[cam_id]
        current = start_index
        for _ in range(self.total_cameras):
            current = (current + direction) % self.total_cameras
            if current not in self.get_used_indexes() or current == start_index:
                self.indexes[cam_id] = current
                break

        self.set_camera_positions()

    def create_camera_item(self, cam_id):
        self.get_logger().info(f"Creating pixmap item for camera {cam_id}")
        pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(pixmap_item)
        self.pixmap_items[cam_id] = pixmap_item

    def tween_position_and_size(self, item, end_x, end_y, end_w, end_h, ease_style=QEasingCurve.InOutQuad, duration=500):
        if not isinstance(item, QGraphicsPixmapItem):
            self.get_logger().error(f"Invalid target for animation: {item}")
            return

        start_pos = item.pos()
        start_w = item.pixmap().width() if not item.pixmap().isNull() else 0
        start_h = item.pixmap().height() if not item.pixmap().isNull() else 0

        animation = QVariantAnimation()
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(ease_style)

        def update_item(value):
            # Interpolate position
            new_x = start_pos.x() + (end_x - start_pos.x()) * value
            new_y = start_pos.y() + (end_y - start_pos.y()) * value
            item.setPos(new_x, new_y)

            # Store target size for frame updates
            item.target_width = int(start_w + (end_w - start_w) * value)
            item.target_height = int(start_h + (end_h - start_h) * value)

        animation.valueChanged.connect(update_item)
        animation.start()

        # Store animation to prevent garbage collection
        self.animations[id(item)] = animation

        # Set initial target size
        item.target_width = int(end_w)
        item.target_height = int(end_h)

    def set_camera_positions(self):
        active_cams = [cam_id for cam_id, active in enumerate(self.active) if active]
        num_active = len(active_cams)
        self.get_logger().info(f"Setting positions for {num_active} active cameras.")

        if num_active == 0:
            return

        for idx, cam_id in enumerate(active_cams):
            item = self.pixmap_items[cam_id]
            ratio = self.target_ratios[num_active-1][idx]
            pos = self.target_positions[num_active-1][idx]

            end_x = pos[0] * self.window_width
            end_y = pos[1] * self.window_height
            end_w = ratio[0] * self.window_width
            end_h = ratio[1] * self.window_height

            self.get_logger().info(f"Setting position for camera {cam_id} to ({end_x}, {end_y}) and size ({end_w}, {end_h})")
            self.tween_position_and_size(item, end_x, end_y, end_w, end_h)

    def update_frames(self):
        """Update camera frames from video captures."""
        for cam_id, cap in self.video_captures.items():
            if cam_id not in self.pixmap_items:
                continue

            item = self.pixmap_items[cam_id]

            # Read frame from camera
            if cap is not None and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    frame = self.create_dummy_frame(cam_id)
            else:
                frame = self.create_dummy_frame(cam_id)

            # Convert frame to QPixmap
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape

            # Resize to target size if available
            target_w = getattr(item, 'target_width', w)
            target_h = getattr(item, 'target_height', h)

            if target_w > 0 and target_h > 0:
                frame_rgb = cv2.resize(frame_rgb, (target_w, target_h))
                h, w = target_h, target_w

            bytes_per_line = ch * w
            q_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)
            item.setPixmap(pixmap)

    def create_dummy_frame(self, cam_id):
        """Create a dummy frame with camera ID text."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (50, 50, 50)  # Dark gray background

        text = f"Camera {self.camera_id[cam_id]}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        text_size = cv2.getTextSize(text, font, 2, 3)[0]
        text_x = (640 - text_size[0]) // 2
        text_y = (480 + text_size[1]) // 2

        cv2.putText(frame, text, (text_x, text_y), font, 2, (255, 255, 255), 3)
        return frame

    def cleanup(self):
        """Release all video captures."""
        for cap in self.video_captures.values():
            if cap is not None:
                cap.release()
        self.video_captures.clear()

def main():
    rclpy.init()
    node = CameraNode()

    app = QApplication([])  # Initialize the PySide6 application

    node.setup_gui()  # Set up the GUI
    node.view.show()  # Display the QGraphicsView

    # Use QTimer to handle the ROS 2 event loop alongside the PySide6 event loop
    timer = QTimer()
    timer.timeout.connect(lambda: rclpy.spin_once(node, timeout_sec=0))  # Spin ROS once
    timer.start(30)  # Check every 30ms

    app.exec()  # Start the PySide6 event loop

    node.cleanup()  # Release cameras
    node.destroy_node()  # Clean up ROS 2 node
    rclpy.shutdown()

if __name__ == "__main__":
    main()
