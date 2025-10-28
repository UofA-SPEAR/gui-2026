import sys
import cv2
import rclpy
from rclpy.node import Node
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QTabWidget
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap
from std_msgs.msg import String


class ListenerNode(Node):
    def __init__(self):
        super().__init__('gui_listener')
        self.subscription = self.create_subscription(
            String, 'chatter', self.listener_callback, 10
        )
        self.last_msg = ""

    def listener_callback(self, msg):
        self.last_msg = msg.data
        self.get_logger().info(f"Received: {msg.data}")


class CameraView(QWidget):
    def __init__(self, source, label="Camera"):
        super().__init__()
        self.source = source
        self.label_text = label

        self.layout = QVBoxLayout()
        self.label = QLabel(f"{label} (initializing...)")
        self.label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)

        self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            self.label.setText(f"⚠️ Could not open {label}")

        # Timer to grab frames
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(33)  # ~30 fps

    def update_frame(self):
        if self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                # Convert to RGB for Qt
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                bytes_per_line = ch * w
                qt_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_img)
                self.label.setPixmap(pixmap.scaled(
                    self.label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))
            else:
                self.label.setText(f"{self.label_text} — no frame")

    def closeEvent(self, event):
        if self.cap.isOpened():
            self.cap.release()
        super().closeEvent(event)


class MainWindow(QMainWindow):
    def __init__(self, node):
        super().__init__()
        self.node = node

        self.setWindowTitle("ROS2 Multi-Camera GUI")
        self.resize(800, 600)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Add multiple camera feeds (can be /dev/video0, /dev/video10, etc.)
        self.add_camera_view("/dev/video10", "VirtualCam1")
        self.add_camera_view("/dev/video11", "VirtualCam2")

        # Update ROS message display periodically
        self.status_label = QLabel("Waiting for ROS messages...")
        self.statusBar().addPermanentWidget(self.status_label)

        self.msg_timer = QTimer()
        self.msg_timer.timeout.connect(self.update_ros_label)
        self.msg_timer.start(500)

    def add_camera_view(self, source, label):
        cam_view = CameraView(source, label)
        self.tabs.addTab(cam_view, label)

    def update_ros_label(self):
        if self.node.last_msg:
            self.status_label.setText(f"ROS msg: {self.node.last_msg}")


def main():
    rclpy.init()
    node = ListenerNode()

    app = QApplication(sys.argv)
    window = MainWindow(node)
    window.show()

    ros_timer = QTimer()
    ros_timer.timeout.connect(lambda: rclpy.spin_once(node, timeout_sec=0))
    ros_timer.start(100)

    app.exec()

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
