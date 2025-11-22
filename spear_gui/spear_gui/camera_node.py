import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo, GLib
import sys
import rclpy
from rclpy.node import Node
from PySide6.QtWidgets import QApplication, QWidget, QFrame
from PySide6.QtCore import QThread, Signal, QTimer, QVariantAnimation, QEasingCurve, Qt, QRect
from PySide6.QtGui import QPainter, QColor
from std_msgs.msg import String

# ------------------------ GStreamer ------------------------
class GStreamerThread(QThread):
    finished = Signal()

    def __init__(self, pipeline_str, window_id=None, parent=None):
        super().__init__(parent)
        self.pipeline_str = pipeline_str
        self.window_id = window_id
        self.pipeline = None
        self.bus = None
        self.loop = GLib.MainLoop()

        Gst.init(None)
        self.pipeline = Gst.parse_launch(self.pipeline_str)

        if not self.pipeline:
            raise RuntimeError(f"Failed to create pipeline: {self.pipeline_str}")

        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self.on_message)
        self.bus.enable_sync_message_emission()
        self.bus.connect("sync-message::element", self.on_sync_message)

    def on_sync_message(self, bus, message):
        if message.get_structure() and message.get_structure().get_name() == 'prepare-window-handle':
            if self.window_id is not None:
                print(f"Setting window handle in sync: {self.window_id}")
                message.src.set_window_handle(self.window_id)

    def run(self):
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            print("Unable to set the pipeline to playing state", file=sys.stderr)
            return

        print("Pipeline is running.")
        self.loop.run()

    def stop(self):
        self.pipeline.set_state(Gst.State.NULL)
        self.loop.quit()

    def on_message(self, bus, message):
        mtype = message.type

        if mtype == Gst.MessageType.EOS:
            print("End of stream")
            self.loop.quit()
        elif mtype == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"Error: {err}", file=sys.stderr)
            print(f"Debug info: {debug}", file=sys.stderr)
            self.loop.quit()

        return True
    
class GStreamerVideoWidget(QWidget):
    def __init__(self, pipeline_str, parent=None):
        super().__init__(parent)
        self.pipeline_str = pipeline_str
        self.thread = None
        self.setStyleSheet("background-color: black; border: 3px solid red;")
        self.setAttribute(Qt.WA_NativeWindow)
        self.setAttribute(Qt.WA_PaintOnScreen)

    def start(self):
        print(f"Widget winId: {self.winId()}, size: {self.size()}, visible: {self.isVisible()}")
        self.thread = GStreamerThread(self.pipeline_str, self.winId(), parent=self)
        self.thread.finished.connect(self.on_finished)
        self.thread.start()

    def stop(self):
        if self.thread:
            self.thread.stop()

    def on_finished(self):
        print("GStreamer pipeline finished.")

    def set_border_color(self, color):
        self.setStyleSheet(f"background-color: black; border: 3px solid {color};")

# ------------------------ Camera Node ------------------------

class Camera:
    def __init__(self, position):
        self.id = -1
        self.index = -1
        self.position = position
        self.active = False
        self.feed_widget = None
        self.pipeline = None
    
class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')

        self.container = None

        self.window_width = 400
        self.window_height = 200

        self.camera_id = [0, 1, 2, 3, 4, 5]
        self.camera_total = len(self.camera_id)
        self.camera_current = 0
        self.camera = [Camera(i) for i in range(self.camera_total)]

        self.animations = {} 

        self.target_sizes = [
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
            [[0, 0], [0.5, 0], [0.5, 0.5], [0, 0.5], [0, 0.5]],
            [[0, 0], [0.5, 0], [2.0/3.0, 0.5], [1.0/3.0, 0.5], [0, 0.5], [0, 0]],
            [[1.0/3.0, 0], [2.0/3.0, 0], [2.0/3.0, 0.5], [1.0/3.0, 0.5], [0, 0.5], [0, 0]]
        ]

        self.key_subscription = self.create_subscription(
            String, 'key', self.key_listener, 10
        )

    # ------------------------ GUI ------------------------

    def setup_gui(self, parent=None):
        self.container = QWidget(parent)
        self.container.setFixedSize(self.window_width, self.window_height)
        self.container.setStyleSheet("background-color: #2b2b2b;")
        self.get_logger().info("GUI setup complete.")

    # ------------------------ Key Listener ------------------------

    def key_listener(self, key_msg):
        key = key_msg.data
        self.get_logger().info(f"Received key: {key}")
        match key:
            case 'p':
                self.get_logger().info("Exiting...")
                rclpy.shutdown()
            case 'w':
                self.activate_camera()
            case 's':
                self.deactivate_camera()
            case 'e':
                self.select_next_camera(1)
            case 'q':
                self.select_next_camera(-1)
            case 'd':
                self.move_index(1)
            case 'a':
                self.move_index(-1)
        self.print_infomation()

    # ------------------------ Camera Utilities ------------------------

    def get_active_cameras(self):
        return [cam for cam in self.camera if cam.active]

    def get_unused_indexes(self):
        return [i for i, cam in enumerate(self.camera) if cam.index == -1]

    def get_available_index(self):
        unused = self.get_unused_indexes()
        if unused:
            return min(unused)
        return None

    # ------------------------ Activation / Deactivation ------------------------

    def activate_camera(self):
        inactive_cams = [cam for cam in self.camera if not cam.active]
        if not inactive_cams:
            self.get_logger().info("No inactive cameras to activate.")
            return

        cam = min(inactive_cams, key=lambda c: c.position)
        cam.active = True
        cam.id = self.camera_id[cam.position]

        if cam.index == -1 or cam.index in [c.index for c in self.camera if c != cam and c.active]:
            cam.index = self.get_available_index()

        self.camera_current = cam.position

        self.create_camera_widget(cam)
        self.set_camera_positions()

    def deactivate_camera(self):
        cam = self.camera[self.camera_current]
        if not cam.active:
            self.get_logger().info(f"Camera {self.camera_current} is not active.")
            return
        
        cam.active = False
        
        if cam.feed_widget:
            cam.feed_widget.stop()
            cam.feed_widget.deleteLater()
            cam.feed_widget = None

        active_positions = [c.position for c in self.camera if c.active]
        if active_positions:
            smaller_positions = [p for p in active_positions if p < cam.position]
            if smaller_positions:
                self.camera_current = max(smaller_positions)
            else:
                self.camera_current = max(active_positions)
        else:
            self.camera_current = None
        
        self.set_camera_positions()

    # ------------------------ Selection ------------------------

    def select_next_camera(self, direction):
        active_positions = [c.position for c in self.camera if c.active]
        max_pos = max(active_positions) if active_positions else 0
        self.camera_current = (self.camera_current + direction) % (max_pos + 1)
        self.update_camera_borders()

    # ------------------------ Move Index ------------------------

    def move_index(self, direction):
        cam = self.camera[self.camera_current]
        if not cam.active:
            self.get_logger().info(f"Camera {self.camera_current} is not active.")
            return

        start_index = cam.index
        current_index = start_index
        for _ in range(self.camera_total):
            current_index = (current_index + direction) % self.camera_total
            active_indexes = [c.index for c in self.get_active_cameras()]
            if current_index not in active_indexes or current_index == start_index:
                cam.index = current_index
                break

        self.set_camera_positions()

    # ------------------------ Camera Widgets ------------------------

    def create_camera_widget(self, cam):
        active_positions = [c.position for c in self.camera if c.active] or [cam.position]
        max_pos = max(active_positions)

        size = self.target_sizes[max(max_pos - 1, 0)][cam.index]
        pos = self.target_positions[max(max_pos - 1, 0)][cam.index]

        x = int(pos[0] * self.window_width)
        y = int(pos[1] * self.window_height)
        w = int(size[0] * self.window_width)
        h = int(size[1] * self.window_height)

        camera_feed_widget = GStreamerVideoWidget(
            f"videotestsrc ! videoconvert ! xvimagesink",
            parent=self.container
        )

        camera_feed_widget.setGeometry(x, y, w, h)
        camera_feed_widget.show()
        camera_feed_widget.start()

        cam.feed_widget = camera_feed_widget

    def set_camera_positions(self):
        active_positions = [c.position for c in self.camera if c.active]
        if not active_positions:
            return
        max_pos = max(active_positions)

        for cam in self.camera:
            if cam.index == -1 or not cam.active:
                continue
            size = self.target_sizes[max_pos][cam.index]
            pos = self.target_positions[max_pos][cam.index]

            end_x = int(pos[0] * self.window_width)
            end_y = int(pos[1] * self.window_height)
            end_w = int(size[0] * self.window_width)
            end_h = int(size[1] * self.window_height)
            self.tween_position_and_size(cam.feed_widget, end_x, end_y, end_w, end_h)

        self.update_camera_borders()

    def update_camera_borders(self):
        for cam in self.camera:
            if not cam.feed_widget:
                continue
            color = "blue" if cam.position == self.camera_current else "red"
            cam.feed_widget.set_border_color(color)

    # ------------------------ Tween Animation ------------------------

    def tween_position_and_size(self, widget, end_x, end_y, end_w, end_h, ease_style=QEasingCurve.InOutQuad, duration=500):
        if not widget:
            return

        cam = next((cam for cam in self.camera if cam.feed_widget == widget), None)
        if not cam:
            return

        start_geom = widget.geometry()

        animation = QVariantAnimation()
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(ease_style)

        def update_geometry(value):
            new_x = int(start_geom.x() + (end_x - start_geom.x()) * value)
            new_y = int(start_geom.y() + (end_y - start_geom.y()) * value)
            new_w = int(start_geom.width() + (end_w - start_geom.width()) * value)
            new_h = int(start_geom.height() + (end_h - start_geom.height()) * value)
            widget.setGeometry(new_x, new_y, new_w, new_h)

        animation.valueChanged.connect(update_geometry)
        animation.start()
        self.animations[id(widget)] = animation

    # ------------------------ Print Information ------------------------

    def print_infomation(self):
        self.get_logger().info(f"Current Selected: {self.camera_current}")
        self.get_logger().info(f"{'Pos':>3} | {'Active':>6} | {'ID':>2} | {'X':>4} | {'Y':>4} | {'W':>4} | {'H':>4}")
        self.get_logger().info("-" * 50)
        for cam in self.camera:
            widget = cam.feed_widget
            if widget:
                geom = widget.geometry()
                x, y, w, h = geom.x(), geom.y(), geom.width(), geom.height()
            else:
                x = y = w = h = 0
            active_str = "\033[92mTrue \033[0m" if cam.active else "\033[91mFalse\033[0m"
            self.get_logger().info(f"{cam.position:>3} | {active_str} | {cam.id:>2} | {x:>4} | {y:>4} | {w:>4} | {h:>4}")


def main():
    rclpy.init()
    node = CameraNode()

    app = QApplication([])

    node.setup_gui()
    node.container.show()

    timer = QTimer()
    timer.timeout.connect(lambda: rclpy.spin_once(node, timeout_sec=0))
    timer.start(30)

    app.exec()

    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()