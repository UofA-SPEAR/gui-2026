import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import QTimer
import rclpy
from rclpy.node import Node
from std_msgs.msg import String  


class ListenerNode(Node):
    def __init__(self):
        super().__init__('gui_listener')
        self.subscription = self.create_subscription(
            String,                   
            'chatter',                 
            self.listener_callback,    
            10                         
        )
        self.last_msg = ""  

    def listener_callback(self, msg):
        self.last_msg = msg.data
        self.get_logger().info(f"Received: {msg.data}")


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

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_label)
        self.timer.start(500) 

    def update_label(self):
        if self.node.last_msg:
            self.label.setText(f"Latest message: {self.node.last_msg}")


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
