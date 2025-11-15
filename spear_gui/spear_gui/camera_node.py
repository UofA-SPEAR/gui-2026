import rclpy
from rclpy.node import Node
from PySide6.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QGraphicsRectItem
from PySide6.QtCore import QTimer, QPropertyAnimation, QPointF, QRectF, QEasingCurve, Qt
from PySide6.QtGui import QPen, QPainter
from std_msgs.msg import String

class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')

        self.scene = None
        self.view = None

        self.window_width = 400
        self.window_height = 200

        self.camera_id = [0, 1, 2, 3, 4, 5]
        self.total_cameras = len(self.camera_id)
        self.active = [False] * self.total_cameras
        self.indexes = [-1] * self.total_cameras
        self.rectangles = {}
        self.animations = {} 

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
            [[0, 0], [0, 0.5], [0.5, 0.5], [0, 1]],
            [[0, 0], [0.5, 0], [0.5, 0], [0.5, 0.5], [1.0/3.0, 0.5]],
            [[0, 0], [0.5, 0], [2.0/3.0, 0.5], [1.0/3.0, 0.5], [1.0/3.0, 0], [0, 0.5]],
            [[0, 0], [2.0/3.0, 0], [2.0/3.0, 0.5], [1.0/3.0, 0.5], [0, 0.5], [1.0/3.0, 0]]
        ]

        self.key_subscription = self.create_subscription(
            String, 'key', self.key_listener, 10
        )

    def setup_gui(self, parent=None):
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene, parent)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setRenderHint(QPainter.SmoothPixmapTransform)
        self.view.setFixedSize(self.window_width, self.window_height)
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

    def get_available_index(self):
        used = self.get_used_indexes()
        available_index = next((i for i in range(self.total_cameras) if i not in used), None)
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

        self.create_camera_rect(cam_id)
        self.set_camera_positions()

    def deactivate_camera(self):
        used = self.get_used_indexes()
        if not used:
            self.get_logger().info("No active cameras to deactivate.")
            return

        idx = max(used)
        self.get_logger().info(f"Deactivating camera {idx}")
        self.active[idx] = False
        rect = self.rectangles.pop(idx, None)
        if rect:
            self.scene.removeItem(rect)

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

    def create_camera_rect(self, cam_id):
        self.get_logger().info(f"Creating rectangle for camera {cam_id}")
        rect = QGraphicsRectItem(0, 0, 50, 50)
        rect.setBrush(Qt.lightGray)
        pen = QPen(Qt.red)
        pen.setWidth(3)
        rect.setPen(pen)

        self.scene.addItem(rect)
        self.rectangles[cam_id] = rect

    def tween_position_and_size(self, rect, end_x, end_y, end_w, end_h, ease_style=QEasingCurve.InOutQuad, duration=500):
        if not isinstance(rect, QGraphicsRectItem):
            self.get_logger().error(f"Invalid target for animation: {rect}")
            return

        # Animate position using QPropertyAnimation
        position_animation = QPropertyAnimation(rect, b"pos")
        position_animation.setDuration(duration)
        position_animation.setStartValue(rect.pos())
        position_animation.setEndValue(QPointF(end_x, end_y))
        position_animation.setEasingCurve(ease_style)
        position_animation.start()

        # Animate size using QPropertyAnimation
        size_animation = QPropertyAnimation(rect, b"rect")
        size_animation.setDuration(duration)
        size_animation.setStartValue(rect.rect())
        size_animation.setEndValue(QRectF(end_x, end_y, end_w, end_h))
        size_animation.setEasingCurve(ease_style)
        size_animation.start()

    def set_camera_positions(self):
        active_rects = [cam_id for cam_id, active in enumerate(self.active) if active]
        num_active = len(active_rects)
        self.get_logger().info(f"Setting positions for {num_active} active cameras.")

        if num_active == 0:
            return

        for idx, cam_id in enumerate(active_rects):
            rect = self.rectangles[cam_id]
            ratio = self.target_ratios[num_active-1][idx]
            pos = self.target_positions[num_active-1][idx]

            end_x = pos[0] * self.window_width
            end_y = pos[1] * self.window_height
            end_w = ratio[0] * self.window_width
            end_h = ratio[1] * self.window_height

            self.get_logger().info(f"Setting position for camera {cam_id} to ({end_x}, {end_y}) and size ({end_w}, {end_h})")
            self.tween_position_and_size(rect, end_x, end_y, end_w, end_h)

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

    node.destroy_node()  # Clean up ROS 2 node
    rclpy.shutdown()

if __name__ == "__main__":
    main()
