#!/usr/bin/env python3
"""display mini map of rover's current position"""
import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import QTimer
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import NavSatFix
from map_viewer import MapViewer

# ------------------------ rover position tracker listener ------------------------
class TrackRoverPosition(Node):
    def __init__(self):
        super().__init__('gui_listener')

        self.lat = None
        self.lon = None

        # Publisher for key events
        self.key_pub = self.create_publisher(String, "key", 10)

        self.gps_sub = self.create_subscription(NavSatFix, "/gps/fix", self.gps_callback, 10)

    def gps_callback(self, msg: NavSatFix):
        self.lat = msg.latitude
        self.lon = msg.longitude

class MainWindow(QMainWindow):
    def __init__(self, node: TrackRoverPosition):
        super().__init__()
        self.node = node

        # window setup
        self.setWindowTitle("ROS2 GUI - Rover Mini Map")
        self.resize(400, 200)

        # finds the script's directory and build path from there
        script_dir = os.path.dirname(os.path.abspath(__file__))
        tiles_path = os.path.join(script_dir, "../../MDRS_2025-11-25_163543/Bing Satellite")
        tiles_path = os.path.normpath(tiles_path)  # Cleaning up the path
        
        # creating map viewer widget to display minimap
        self.map_viewer = MapViewer(tiles_path, self)

        layout = QVBoxLayout()
        layout.addWidget(self.map_viewer)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Timer to update GUI from ROS2 callbacks
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_rover)
        self.timer.start(200)

    def keyPressEvent(self, event):
        """Capture key press and publish to ROS2 topic 'key'."""
        key = event.text()
        if key:
            msg = String()
            msg.data = key
            self.node.key_pub.publish(msg)
            print(f"Published key: {key}")  # Also logs in terminal

    def update_rover(self):
        """Update label with latest position for the rover"""
        if self.node.lat is None or self.node.lon is None:
            return
        
        self.map_viewer.update_marker_gps(self.node.lat, self.node.lon)

def main():
    rclpy.init()
    node = TrackRoverPosition()

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
