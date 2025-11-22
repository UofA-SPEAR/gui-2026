import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo, GLib

import rclpy
from rclpy.node import Node
from PySide6.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QGraphicsRectItem, QScrollArea, QWidget, QVBoxLayout
from PySide6.QtCore import QTimer, QVariantAnimation, QPointF, QRectF, QEasingCurve, Qt
from PySide6.QtGui import QPen, QPainter
from std_msgs.msg import String

# ------------------------ GStreamer ------------------------

class GStreamerVideoWidget(QWidget):
    def __init__(self, pipeline_str, parent=None):
        super().__init__(parent)
        self.pipeline_str = pipeline_str
        self.pipeline = None
        self.bus = None
        self.loop = GLib.MainLoop()

        Gst.init(None)
        self.pipeline = Gst.parse_launch(pipeline_str)

        if not self.pipeline:
            raise RuntimeError(f"Failed to create pipeline: {pipeline_str}")
        
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self.on_message)

        self.setLayout(QVBoxLayout())
        self.setFixedSize(640, 480) 

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

    def start(self):
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            print("Unable to set the pipeline to playing state", file=sys.stderr)
            return

        print("Pipeline is running.")
        self.loop.run()

    def stop(self):
        self.pipeline.set_state(Gst.State.NULL)

# ------------------------ Camera Node ------------------------

class Camera:
    def __init__(self, position):
        self.id = -1
        self.index = -1             # Index in the camera id list
        self.position = position    # Position in the camera list
        self.active = False
        self.rect = None
        self.feed_widget = None
        self.pipeline = None
    
class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')

        self.scene = None
        self.view = None

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
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene, parent)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setRenderHint(QPainter.SmoothPixmapTransform)
        self.view.setFixedSize(self.window_width, self.window_height)
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
            self.logger().info("No inactive cameras to activate.")
            return
        
        if not inactive_cams:
            self.get_logger().info("No inactive cameras to activate.")
            return

        cam = min(inactive_cams, key=lambda c: c.position)
        cam.active = True
        cam.id = self.camera_id[cam.position]

        if cam.index == -1 or cam.index in [c.index for c in self.camera if c != cam and c.active]:
            cam.index = self.get_available_index()

        self.camera_current = cam.position

        self.create_camera_rect(cam)
        self.set_camera_positions()

    def deactivate_camera(self):
        cam = self.camera[self.camera_current]
        if not cam.active:
            self.get_logger().info(f"Camera {self.camera_current} is not active.")
            return
        
        cam.active = False
        if cam.rect:
            self.scene.removeItem(cam.rect)
            cam.rect = None
        
        if cam.feed_widget:
            cam.feed_widget.stop()
            self.scene.removeItem(cam.feed_widget)
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

    # ------------------------ Move Index ------------------------

    def move_index(self, direction):
        # Moves the selected screen's camera index up or down 1. Attempts to find the nearest unique index in its direction.
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

    # ------------------------ Camera Rectangles ------------------------

    def create_camera_rect(self, cam):
        active_positions = [c.position for c in self.camera if c.active] or [cam.position]
        max_pos = max(active_positions)

        size = self.target_sizes[max(max_pos - 1, 0)][cam.index]
        pos = self.target_positions[max(max_pos - 1, 0)][cam.index]

        x = pos[0] * self.view.width()
        y = pos[1] * self.view.height()
        w = size[0] * self.view.width()
        h = size[1] * self.view.height()

        rect = QGraphicsRectItem(0, 0, w, h)
        rect.setBrush(Qt.lightGray)

        pen = QPen(Qt.red)
        pen.setWidth(3)
        rect.setPen(pen)

        rect.setPos(x, y)

        camera_feed_widget = GStreamerVideoWidget(f"zedxonesrc ! queue ! autovideoconvert ! queue ! fpsdisplaysink", parent=self.view)
        camera_feed_widget.start()

        proxy_widget = QGraphicsProxyWidget()
        proxy_widget.setWidget(camera_feed_widget)
        proxy_widget.setPos(x, y)
        proxy_widget.setGeometry(x, y, w, h)
        
        self.scene.addItem(proxy_widget)

        cam.rect = rect
        cam.feed_widget = camera_feed_widget

        self.scene.addItem(rect)

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

            end_x = pos[0] * self.view.width()
            end_y = pos[1] * self.view.height()
            end_w = size[0] * self.view.width()
            end_h = size[1] * self.view.height()
            self.tween_position_and_size(cam.rect, end_x, end_y, end_w, end_h)

        self.update_camera_borders()

    def update_camera_borders(self):
        for cam in self.camera:
            if not cam.rect:
                continue
            pen = QPen(Qt.red if cam.position != self.camera_current else Qt.blue)
            pen.setWidth(3)
            cam.rect.setPen(pen)

    # ------------------------ Tween Animation ------------------------

    def tween_position_and_size(self, rect, end_x, end_y, end_w, end_h, ease_style = QEasingCurve.InOutQuad, duration = 500):
        if not isinstance(rect, QGraphicsRectItem):
            self.get_logger().error(f"Invalid target for animation: {rect}")
            return

        cam = next((cam for cam in self.camera if cam.rect == rect), None)
        if not cam:
            return

        start_rect = rect.rect()
        start_pos = rect.pos()

        proxy_widget = cam.feed_widget.parentWidget()

        animation = QVariantAnimation()
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(ease_style)

        def update_rect(value):
            new_x = start_pos.x() + (end_x - start_pos.x()) * value
            new_y = start_pos.y() + (end_y - start_pos.y()) * value
            rect.setPos(new_x, new_y)
            new_w = start_rect.width() + (end_w - start_rect.width()) * value
            new_h = start_rect.height() + (end_h - start_rect.height()) * value
            rect.setRect(0, 0, new_w, new_h)

            if proxy_widget:
                proxy_widget.setGeometry(new_x, new_y, new_w, new_h)


        animation.valueChanged.connect(update_rect)
        animation.start()
        self.animations[id(rect)] = animation

    # ------------------------ Print Infomation ------------------------

    def print_infomation(self):
        self.get_logger().info(F"Current Selected: {self.camera_current}")
        self.get_logger().info(f"{'Pos':>3} | {'Active':>6} | {'ID':>2} | {'X':>4} | {'Y':>4} | {'W':>4} | {'H':>4}")
        self.get_logger().info("-" * 35)
        for cam in self.camera:
            rect = cam.rect
            if rect:
                r = rect.rect()
                x, y, w, h = round(rect.x()), round(rect.y()), round(r.width()), round(r.height())
            else:
                x = y = w = h = 0
            active_str = "\033[92mTrue \033[0m" if cam.active else "\033[91mFalse\033[0m"
            self.get_logger().info(f"{cam.position:>3} | {active_str:>6} | {cam.id:>2} | {x:>4} | {y:>4} | {w:>4} | {h:>4}")


def main():
    rclpy.init()
    node = CameraNode()

    app = QApplication([])

    scroll = QScrollArea()
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    node.setup_gui()
    node.view.show()

    timer = QTimer()
    timer.timeout.connect(lambda: rclpy.spin_once(node, timeout_sec=0))
    timer.start(30)

    app.exec()

    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()
