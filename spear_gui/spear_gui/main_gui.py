import sys
import cv2
import rclpy
from rclpy.node import Node
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, 
    QGridLayout, QComboBox, QHBoxLayout, QSpacerItem, QSizePolicy
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


class CameraView(QLabel):
    def __init__(self, source, name):
        super().__init__()
        self.source = source
        self.name = name
        self.cap = cv2.VideoCapture(source)
        self.setAlignment(Qt.AlignCenter)
        self.setText(f"{name}\n(Initializing...)")

        if not self.cap.isOpened():
            self.cap = None
            self.setText(f"{name}\n❌ No camera detected")

        # Timer for updating frames
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(100)

    def update_frame(self):
        if self.cap is not None and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame.shape
                img = QImage(frame.data, w, h, ch * w, QImage.Format_RGB888)
                self.setPixmap(QPixmap.fromImage(img).scaled(
                    self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.setText(f"{self.name}\n No frame")
        else:
            self.setText(f"{self.name}\n No camera connected")

    def closeEvent(self, event):
        if self.cap:
            self.cap.release()


class CameraGrid(QWidget):
    def __init__(self, cameras):
        super().__init__()
        self.cameras = cameras
        self.layout = QGridLayout()
        self.setLayout(self.layout)
        self.current_layout = "1 View"
        self.update_layout("1 View")

    def clear_layout(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

    def update_layout(self, layout_type):
        self.clear_layout()
        self.current_layout = layout_type

        if layout_type == "1 View":
            self.layout.addWidget(self.cameras[0], 0, 0)
        elif layout_type == "2 Views":
            self.layout.addWidget(self.cameras[0], 0, 0)
            if len(self.cameras) > 1:
                self.layout.addWidget(self.cameras[1], 0, 1)
        elif layout_type == "4 Views (2x2)":
            for i in range(min(4, len(self.cameras))):
                row, col = divmod(i, 2)
                self.layout.addWidget(self.cameras[i], row, col)


class MainWindow(QMainWindow):
    def __init__(self, node):
        super().__init__()
        self.node = node
        self.setWindowTitle("SPEAR Rover GUI")
        self.resize(1200, 700)

        # === Cameras ===
        camera_sources = [
            (0, "Camera 1"),
            (1, "Camera 2"),
            ("/dev/video10", "Camera 3"),
            ("/dev/video11", "Camera 4")
        ]
        self.cameras = [CameraView(src, name) for src, name in camera_sources]

        self.camera_grid = CameraGrid(self.cameras)

        self.view_selector = QComboBox()
        self.view_selector.addItems(["1 View", "2 Views", "4 Views (2x2)"])
        self.view_selector.currentTextChanged.connect(self.change_view_layout)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("View Layout:"))
        top_bar.addWidget(self.view_selector)
        top_bar.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_bar)
        main_layout.addWidget(self.camera_grid)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.status_label = QLabel("Waiting for ROS messages...")
        self.statusBar().addPermanentWidget(self.status_label)

        self.msg_timer = QTimer()
        self.msg_timer.timeout.connect(self.update_ros_label)
        self.msg_timer.start(500)

    def change_view_layout(self, layout_type):
        print(f"Switching to layout: {layout_type}")
        self.camera_grid.update_layout(layout_type)

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
