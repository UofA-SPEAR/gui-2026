#!/usr/bin/env python3
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import QTimer
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class ListenerNode(Node):
    def __init__(self):
        super().__init__('gui_listener')

        # Publisher for key events
        self.key_pub = self.create_publisher(String, "key", 10)

        # Subscriber for any other messages (optional)
        self.sub = self.create_subscription(
            String, 'chatter', self.callback, 10
        )

        self.last_msg = ""

    def callback(self, msg):
        """Update last received message."""
        self.last_msg = msg.data
        self.get_logger().info(f"Received message: {msg.data}")


class MainWindow(QMainWindow):
    def __init__(self, node):
        super().__init__()
        self.node = node

        self.setWindowTitle("ROS2 GUI")
        self.resize(400, 200)

        self.label = QLabel("Waiting for messages...")
        layout = QVBoxLayout()
        layout.addWidget(self.label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Timer to update GUI from ROS2 callbacks
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_label)
        self.timer.start(200)

    def keyPressEvent(self, event):
        """Capture key press and publish to ROS2 topic 'key'."""
        key = event.text()
        if key:
            msg = String()
            msg.data = key
            self.node.key_pub.publish(msg)
            print(f"Published key: {key}")  # Also logs in terminal

    def update_label(self):
        """Update label with latest message from 'chatter' topic."""
        if self.node.last_msg:
            self.label.setText(f"Latest message: {self.node.last_msg}")


def main():
    rclpy.init()
    node = ListenerNode()

    app = QApplication(sys.argv)
    window = MainWindow(node)
    window.show()

    # Timer to spin ROS2 node periodically
    ros_timer = QTimer()
    ros_timer.timeout.connect(lambda: rclpy.spin_once(node, timeout_sec=0))
    ros_timer.start(30)

    app.exec()

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
