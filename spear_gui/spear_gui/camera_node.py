import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo, GLib
import sys
import rclpy
from rclpy.node import Node
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QFrame
from PySide6.QtCore import QThread, Signal, QTimer, QVariantAnimation, QEasingCurve, Qt, QObject, QEvent
from PySide6.QtGui import QColor
from std_msgs.msg import String
from collections import deque

# ------------------------ Key Event Filter ------------------------
class KeyEventFilter(QObject):
    def __init__(self, node):
        super().__init__()
        self.node = node

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            key = event.text()
            if key:
                msg = String()
                msg.data = key
                self.node.key_pub.publish(msg)
                print(f"[KeyEventFilter] Published key: {key}")
            return True
        return False

# ------------------------ GStreamer ------------------------
class GStreamerThread(QThread):
    finished = Signal()
    error_occured = Signal(str)
    state_changed = Signal(str)

    def __init__(self, pipeline_str, window_id=None, parent=None):
        super().__init__(parent)
        self.pipeline_str = pipeline_str
        self.window_id = window_id
        self.pipeline = None
        self.bus = None
        self.loop = GLib.MainLoop()

        try:
            Gst.init(None)
            self.pipeline = Gst.parse_launch(self.pipeline_str)

            if not self.pipeline:
                raise RuntimeError(f"Failed to create pipeline: {self.pipeline_str}")

            self.bus = self.pipeline.get_bus()
            self.bus.add_signal_watch()
            self.bus.connect("message", self.on_message)
            
            if self.window_id is not None:
                self.bus.enable_sync_message_emission()
                self.bus.connect("sync-message::element", self.on_sync_message)
        except Exception as e:
            error_msg = f"Pipeline creation failed: {e}"
            print(error_msg, file=sys.stderr)
            self.error_occured.emit(error_msg)
            self.pipeline = None

    def on_sync_message(self, bus, message):
        if message.get_structure() and message.get_structure().get_name() == 'prepare-window-handle':
            if self.window_id is not None:
                try:
                    print(f"Setting window handle in sync: {self.window_id}")
                    message.src.set_window_handle(self.window_id)
                except Exception as e:
                    print(f"Failed to set window handle: {e}", file=sys.stderr)

    def run(self):
        if not self.pipeline:
            print("Pipeline not initialized, cannot run", file=sys.stderr)
            return
            
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            print("Unable to set the pipeline to playing state", file=sys.stderr)
            self.error_occured.emit("Failed to set pipeline to PLAYING state")
            return

        print("Pipeline is running.")
        self.loop.run()

    def stop(self):
        if self.pipeline:
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
            self.error_occured.emit(f"GStreamer error: {err}")
            self.loop.quit()
        elif mtype == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipeline:
                old_state, new_state, pending_state = message.parse_state_changed()
                state_name = new_state.value_nick
                self.state_changed.emit(state_name)
                print(f"Pipeline state changed to: {state_name}")

        return True
    
class GStreamerVideoWidget(QWidget):
    pipeline_ready = Signal()
    def __init__(self, pipeline_str, camera_name="", camera_id="", use_overlay=True, parent=None, cam_width=1920, cam_height=1080):
        super().__init__(parent)
        self.pipeline_str = pipeline_str
        self.use_overlay = use_overlay
        self.thread = None
        self.placeholder_label = None
        self.is_streaming = False
        
        self.camera_aspect_ratio = cam_width / cam_height

        self.setStyleSheet("background-color: black; border: 3px solid red;")
        
        self.name_label = QLabel(camera_name, self)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet("""
            color: white; 
            font-size: 14px; 
            font-weight: bold; 
            background-color: rgba(0, 0, 0, 150); 
            border: none;
            padding: 2px;
        """)

        self.id_label = QLabel(f"ID: {camera_id}", self)
        self.id_label.setAlignment(Qt.AlignCenter)
        self.id_label.setStyleSheet("""
            color: white; 
            font-size: 10px; 
            background-color: rgba(0, 0, 0, 150); 
            border: none;
            padding: 2px;
        """)

        self.name_label.raise_()
        self.id_label.raise_()
        
        if use_overlay:
            self.setAttribute(Qt.WA_NativeWindow)
        else:
            self.placeholder_label = QLabel("No Camera\nDetected", self)
            self.placeholder_label.setAlignment(Qt.AlignCenter)
            self.placeholder_label.setStyleSheet("color: white; font-size: 16px; background-color: #1a1a1a;")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        name_height = 20
        self.name_label.setGeometry(0, 5, self.width(), name_height)
        
        id_height = 15
        self.id_label.setGeometry(0, 5 + name_height, self.width(), id_height)
        
        if self.placeholder_label:
            self.placeholder_label.setGeometry(0, 0, self.width(), self.height())
        
        self.name_label.raise_()
        self.id_label.raise_()

    def _resize_video_area(self):
        container_w, container_h = self.width(), self.height()
        target_ar = self.camera_aspect_ratio
        container_ar = container_w / container_h

        if container_ar > target_ar: # container is wider, limit by height
            video_h = container_h
            video_w = int(video_h * target_ar)
        else:
            video_w = container_w # container is taller, limit by width
            video_h = int(video_w / target_ar)

        video_x = (container_w - video_w) // 2
        video_y = (container_h - video_h) // 2

        if self.use_overlay:
            self.setContentsMargins(video_x, video_y, container_w - video_w - video_x, container_h - video_h - video_y)
        elif self.placeholder_label:
            self.placeholder_label.setGeometry(video_x, video_y, video_w, video_h)


    def start(self):
        if not self.use_overlay:
            print("Overlay disabled, showing placeholder")
            self.name_label.raise_()
            self.id_label.raise_() 
            return
            
        self.show()
        QApplication.processEvents()
        
        print(f"Widget winId: {self.winId()}, size: {self.size()}, visible: {self.isVisible()}")
        self.thread = GStreamerThread(self.pipeline_str, self.winId(), parent=self)
        self.thread.finished.connect(self.on_finished)
        self.thread.error_occured.connect(self.on_error)
        self.thread.state_changed.connect(self.on_state_changed)
        self.thread.start()
        
        self.name_label.raise_()
        self.id_label.raise_()

    def stop(self):
        if self.thread:
            self.thread.stop()
            self.thread.wait(1000)

    def on_error(self, error_msg):
        print(f"GStreamer error: {error_msg}")
        if self.placeholder_label:
            self.placeholder_label.setText("An Error\nOccured")
    
    def on_state_changed(self, state_name):
        if state_name == "playing":
            self.is_streaming = True
            self.pipeline_ready.emit()
            print("Pipeline is now streaming")

    def on_finished(self):
        print("GStreamer pipeline finished.")

    def showEvent(self, event):
        super().showEvent(event)
        self.name_label.raise_()
        self.id_label.raise_()
        self.name_label.show() 
        self.id_label.show()   

    def update_labels(self, camera_name, camera_id):
        self.name_label.setText(camera_name)
        self.id_label.setText(f"ID: {camera_id}")
        self.name_label.raise_()
        self.id_label.raise_()

    def set_border_color(self, color):
        self.setStyleSheet(f"background-color: black; border: 3px solid {color};")
        if self.placeholder_label:
            self.placeholder_label.setStyleSheet(f"color: white; font-size: 16px; background-color: #1a1a1a; border: 3px solid {color};")

class ResizableContainer(QWidget):
    resized = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resized.emit()

# ------------------------ Loading Animation ------------------------
class LoadingAnimationWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setParent(parent)

        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setStyleSheet("background: transparent;")
        
        self.outline_rect = QWidget(self)
        self.outline_rect.setStyleSheet("background: transparent; border: 2px solid white;")
        
        self.fill_rect = QWidget(self.outline_rect)
        self.fill_rect.setStyleSheet("background: rgba(100, 200, 255, 200); border: none;")
        
        self.outline_animation = None
        self.fill_animation = None
        self.fade_animation = None
        self.expand_animation = None
        
        self.is_complete = False
        self.outline_drawn = False
        self.current_progress = 0.0

        # Thickness of the animated border
        self.outline_thickness = 4  # adjust as needed

        # --- Animated segments (4 sides) ---

        # Top: grows left → right
        self.left_segment = QFrame(self)
        self.left_segment.setStyleSheet("background-color: white;")
        self.left_segment.setGeometry(0, 0, 0, self.outline_thickness)
        self.left_segment.hide()

        # Right: grows top → bottom
        self.down_segment = QFrame(self)
        self.down_segment.setStyleSheet("background-color: white;")
        self.down_segment.setGeometry(0, 0, self.outline_thickness, 0)
        self.down_segment.hide()

        # Bottom: grows right → left
        self.right_segment = QFrame(self)
        self.right_segment.setStyleSheet("background-color: white;")
        self.right_segment.setGeometry(0, 0, 0, self.outline_thickness)
        self.right_segment.hide()

        # Left: grows bottom → top
        self.up_segment = QFrame(self)
        self.up_segment.setStyleSheet("background-color: white;")
        self.up_segment.setGeometry(0, 0, self.outline_thickness, 0)
        self.up_segment.hide()

        # Final static rectangle that replaces segments after animation
        self.outline_rect = QFrame(self)
        self.outline_rect.setStyleSheet(f"border: {self.outline_thickness}px solid white;")
        self.outline_rect.hide()

        # Fill bar (becomes visible after outline is fully drawn)
        self.fill_rect = QFrame(self.outline_rect)
        self.fill_rect.setStyleSheet("background-color: white;")
        self.fill_rect.hide()
        
        self.draw_timer = QTimer()
        self.draw_timer.timeout.connect(self.animate_outline_draw)
        self.draw_progress = 0.0
        self.draw_step = 0.05
        
    def start_loading_animation(self, center_x, center_y, bar_width=200, bar_height=20):
        self.bar_width = bar_width
        self.bar_height = bar_height
        p = self.parent()
        self.center_x = p.width() // 2
        self.center_y = p.height() // 2
        self.gap = 4

        self.outline_rect.setGeometry(
            center_x - bar_width // 2,
            center_y - bar_height // 2,
            0, 0
        )
        
        self.outline_drawn = False
        self.draw_progress = 0.0
        self.draw_timer.start(16)
        
    def animate_outline_draw(self):
        self.draw_progress += self.draw_step

        raw_t = min(self.draw_progress, 1.0)

        if hasattr(self, "ease_func") and callable(self.ease_func):
            t = self.ease_func(raw_t)
        else:
            t = raw_t
        # -------------------------------------------------------------

        # Total perimeter
        P = 2 * (self.bar_width + self.bar_height)

        if t >= 1.0: # Animation is done
            self.draw_timer.stop()
            self.outline_drawn = True

            final_x = self.center_x - self.bar_width // 2
            final_y = self.center_y - self.bar_height // 2
            self.outline_rect.setGeometry(final_x, final_y, self.bar_width, self.bar_height)
            self.fill_rect.setGeometry(
                self.gap,
                self.gap,
                0,
                self.bar_height - 2 * self.gap
            )
            self.outline_rect.show()
            self.fill_rect.show()

            for seg in (self.left_segment, self.down_segment, self.right_segment, self.up_segment):
                seg.hide()

            # Create the progress bar fill
            self.fill_rect.setGeometry(
                self.gap,
                self.gap,
                0,
                self.bar_height - 2 * self.gap
            )
            self.fill_rect.show()
            return

        # Convert eased progress → perimeter distance
        d = t * P

        L = self.bar_width
        H = self.bar_height
        L2 = self.bar_width
        H2 = self.bar_height

        x0 = self.center_x - self.bar_width // 2
        y0 = self.center_y - self.bar_height // 2

        self.left_segment.show()
        self.down_segment.show()
        self.right_segment.show()
        self.up_segment.show()

        # ---------------- TOP SEGMENT (left → right) ----------------
        if d <= L:
            self.left_segment.setGeometry(
                x0, y0,
                int(d), self.outline_thickness
            )
            self.down_segment.resize(0, 0)
            self.right_segment.resize(0, 0)
            self.up_segment.resize(0, 0)
            return

        self.left_segment.setGeometry(
            x0, y0,
            L, self.outline_thickness
        )

        # ---------------- RIGHT SEGMENT (top → bottom) ----------------
        if d <= L + H:
            h = int(d - L)
            self.down_segment.setGeometry(
                x0 + L - self.outline_thickness,
                y0,
                self.outline_thickness,
                h
            )
            self.right_segment.resize(0, 0)
            self.up_segment.resize(0, 0)
            return

        self.down_segment.setGeometry(
            x0 + L - self.outline_thickness,
            y0,
            self.outline_thickness,
            H
        )

        # ---------------- BOTTOM SEGMENT (right → left) ----------------
        if d <= L + H + L2:
            w = int(d - (L + H))
            self.right_segment.setGeometry(
                x0 + L - w,
                y0 + H - self.outline_thickness,
                w,
                self.outline_thickness
            )
            self.up_segment.resize(0, 0)
            return

        self.right_segment.setGeometry(
            x0,
            y0 + H - self.outline_thickness,
            L,
            self.outline_thickness
        )

        # ---------------- LEFT SEGMENT (bottom → top) ----------------
        remaining = d - (L + H + L2)
        self.up_segment.setGeometry(
            x0,
            y0 + H - remaining,
            self.outline_thickness,
            int(remaining)
        )

        
    def update_progress(self, progress):
        if not self.outline_drawn or self.is_complete:
            return
            
        self.current_progress = progress
        target_width = int((self.bar_width - 2 * self.gap) * progress)
        
        if self.fill_animation:
            self.fill_animation.stop()
            
        self.fill_animation = QVariantAnimation()
        self.fill_animation.setDuration(500)
        self.fill_animation.setStartValue(self.fill_rect.width())
        self.fill_animation.setEndValue(target_width)
        self.fill_animation.setEasingCurve(QEasingCurve.InOutCubic)
        
        def update_fill_width(value):
            if self.fill_rect:
                self.fill_rect.setGeometry(
                    self.gap,
                    self.gap,
                    int(value),
                    self.bar_height - 2 * self.gap
                )
        
        self.fill_animation.valueChanged.connect(update_fill_width)
        self.fill_animation.start()
        
    def complete_animation(self, final_border_color="blue"):
        if self.is_complete:
            return
            
        self.is_complete = True
        
        self.fill_animation = QVariantAnimation()
        self.fill_animation.setDuration(300)
        self.fill_animation.setStartValue(self.fill_rect.width())
        self.fill_animation.setEndValue(self.bar_width - 2 * self.gap)
        self.fill_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        def update_fill_complete(value):
            if self.fill_rect:
                self.fill_rect.setGeometry(
                    self.gap,
                    self.gap,
                    int(value),
                    self.bar_height - 2 * self.gap
                )
        
        self.fill_animation.valueChanged.connect(update_fill_complete)
        self.fill_animation.finished.connect(self.expand_to_border)
        self.fill_animation.start()
        
    def expand_to_border(self):
        if not self.parent():
            return
            
        parent_width = self.parent().width()
        parent_height = self.parent().height()
        
        self.expand_animation = QVariantAnimation()
        self.expand_animation.setDuration(500)
        self.expand_animation.setStartValue(0.0)
        self.expand_animation.setEndValue(1.0)
        self.expand_animation.setEasingCurve(QEasingCurve.OutExpo)
        
        start_x = self.outline_rect.x()
        start_y = self.outline_rect.y()
        start_w = self.outline_rect.width()
        start_h = self.outline_rect.height()
        
        fill_w = self.fill_rect.width()
        fill_h = self.fill_rect.height()
        
        def update_expansion(value):
            if not self.outline_rect or not self.fill_rect:
                return
                
            new_x = int(start_x * (1 - value) + 0 * value)
            new_y = int(start_y * (1 - value) + 0 * value)
            new_w = int(start_w * (1 - value) + parent_width * value)
            new_h = int(start_h * (1 - value) + parent_height * value)
            
            self.outline_rect.setGeometry(new_x, new_y, new_w, new_h)
            
            fill_new_w = int(fill_w * (1 - value) + (parent_width - 2 * self.gap) * value)
            fill_new_h = int(fill_h * (1 - value) + (parent_height - 2 * self.gap) * value)
            
            self.fill_rect.setGeometry(self.gap, self.gap, fill_new_w, fill_new_h)
            
            opacity = int(200 * (1 - value))
            self.fill_rect.setStyleSheet(f"background: rgba(100, 200, 255, {opacity}); border: none;")
            
        self.expand_animation.valueChanged.connect(update_expansion)
        self.expand_animation.finished.connect(self.finish_and_cleanup)
        self.expand_animation.start()

    def resizeEvent(self, event):
        self.update_center()
        super().resizeEvent(event)

    def update_center(self):
        if not self.parent():
            return
        p = self.parent()
        self.center_x = p.width() // 2
        self.center_y = p.height() // 2


    def finish_and_cleanup(self):
        if self.parent():
            parent = self.parent()
            if hasattr(parent, 'set_border_color'):
                parent.set_border_color("red")
        
        self.hide()
        QTimer.singleShot(100, self.cleanup_widgets)

    def cleanup_widgets(self):
        if self.outline_rect:
            self.outline_rect.deleteLater()
            self.outline_rect = None
        if self.fill_rect:
            self.fill_rect.deleteLater()
            self.fill_rect = None
        self.deleteLater()
# ------------------------ Camera Node ------------------------

class Camera:
    def __init__(self, position):
        self.id = -1
        self.index = -1
        self.absolute_position = position
        self.position = position
        self.active = False
        self.feed_widget = None
        self.pipeline = None
        self.is_loading = False
        self.loading_progress = 0.0 # 0 to 1
        self.loading_start_time = None
        self.loading_duration = 0.0 # seconds
        self.loading_animation_widget = None
    
class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')

        self.container = None
        self.command_queue = deque()
        self.processing_command = False

        self.camera_name = ["Placeholder 1", "Placeholder 2", "Placeholder 3", "Placeholder 4", "Placeholder 5", "Placeholder 6"]
        self.camera_id = [307142683, 302801547, 58896881, 3, 4, 5]
        self.camera_ratios = [[1920, 1080], [1920, 1080], [1920, 1080], [1920, 1080], [1920, 1080], [1920, 1080]]
        self.camera_total = len(self.camera_id)
        self.camera_current = 0
        self.camera = [Camera(i) for i in range(self.camera_total)]
        self.switching_cams = False

        self.animations = {} 

        self.focus_mode = False
        self.focused_camera = None
        self.pre_focus_geometries = {}

        self.target_sizes = [
            [[1, 1], [0, 1]], 
            [[2.0/3.0, 1], [1.0/3.0, 1], [1.0/3.0, 0]], 
            [[0.5, 1], [0.5, 0.5], [0.5, 0.5], [0.5, 0]], 
            [[0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0, 0.5]], 
            [[0.5, 0.5], [0.5, 0.5], [1.0/3.0, 0.5], [1.0/3.0, 0.5], [1.0/3.0, 0.5], [0, 0.5]], 
            [[1.0/3.0, 0.5], [1.0/3.0, 0.5], [1.0/3.0, 0.5], [1.0/3.0, 0.5], [1.0/3.0, 0.5], [1.0/3.0, 0.5]]
        ]
        self.target_positions = [
            [[0, 0], [1, 0]],
            [[0, 0], [2.0/3.0, 0], [2.0/3.0, 1]],
            [[0, 0], [0.5, 0], [0.5, 0.5], [0, 1]],
            [[0, 0], [0.5, 0], [0.5, 0.5], [0, 0.5], [0, 0.5]],
            [[0, 0], [0.5, 0], [2.0/3.0, 0.5], [1.0/3.0, 0.5], [0, 0.5], [0, 0]],
            [[1.0/3.0, 0], [2.0/3.0, 0], [2.0/3.0, 0.5], [1.0/3.0, 0.5], [0, 0.5], [0, 0]]
        ]

        self.zed_available = self.check_gstreamer_element('zedxonesrc')
        if not self.zed_available:
            self.get_logger().warn("\033[93mWarning: ZED SDK not detected. Camera display is disabled.\033[0m")

        self.video_sink = self.find_best_video_sink()
        print(f"Using video sink: {self.video_sink}")
        
        self.use_video_overlay = self.video_sink in ['ximagesink', 'xvimagesink', 'glimagesink']
        if not self.use_video_overlay:
            self.get_logger().warn("\033[93mWarning: Video overlay not available. Using placeholder mode.\033[0m")
        
        self.key_pub = self.create_publisher(String, "key", 10)
        self.key_subscription = self.create_subscription(
            String, 'key', self.key_listener, 10
        )

    # ------------------------ Setup ------------------------

    def check_gstreamer_element(self, element_name):
        try:
            Gst.init(None)
            return Gst.ElementFactory.make(element_name, None) is not None
        except Exception as e:
            self.get_logger().error(f"\033[91mError: Failed to check GStreamer element: {e}\033[0m")
            return False

    def find_best_video_sink(self):
        sinks = ['ximagesink', 'xvimagesink', 'glimagesink', 'autovideosink']
        
        for sink in sinks:
            if self.check_gstreamer_element(sink):
                print(f"Found video sink: {sink}")
                return sink
        
        self.get_logger().warn("\033[93mWarning: No video sink available\033[0m")
        return 'fakesink'

    def setup_gui(self, parent=None):
        self.container = ResizableContainer(parent)
        self.container.setMinimumSize(400, 200)
        self.container.resize(800, 400)
        self.container.setStyleSheet("background-color: #2b2b2b;")
        self.container.resized.connect(self.on_container_resized)
        print("GUI setup complete.")
    
    def on_container_resized(self):
        self.set_camera_positions()

    # ------------------------ Key Listener ------------------------

    def key_listener(self, key_msg):
        key = key_msg.data
        print(f"Received key: {key}")
        self.command_queue.append(key.lower())
        if not self.processing_command:
            self.process_command_queue()

    def process_command_queue(self):
        if not self.command_queue:
            self.processing_command = False
            return
        self.processing_command = True
        key = self.command_queue.popleft()
        match key:
            case 'p':
                print("Exiting...")
                rclpy.shutdown()
                return
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
            case 'f':
                self.toggle_focus()
            case 'r':
                self.switching_cams = not self.switching_cams
            case "0" | "1" | "2" | "3" | "4" | "5":
                if self.switching_cams:
                    self.switch_cam(int(key))
            case _:
                if self.switching_cams:
                    self.switching_cams = False
        self.print_infomation()
        self.cleanup_orphaned_widgets()
        QTimer.singleShot(20, self.process_command_queue)

    # ------------------------ Camera Utilities ------------------------

    def get_active_cameras(self):
        return list(filter(lambda c: c.active, self.camera))

    def get_unused_indexes(self):
        used = {cam.index for cam in self.camera if cam.index != -1}
        return [i for i in range(self.camera_total) if i not in used]

    def get_available_index(self):
        unused = self.get_unused_indexes()
        return unused[0] if unused else None

    # ------------------------ Activation / Deactivation ------------------------

    # Activates the lowest position camera with the lowest camera index.
    def activate_camera(self):
        try:
            cam = next(cam for cam in self.camera if not cam.active)
        except StopIteration:
            print("No inactive cameras to activate.")
            return

        cam.active = True

        active_indexes = {c.index for c in self.camera if c.active and c is not cam}
        if cam.index in (-1, *active_indexes):
            cam.index = self.get_available_index()

        cam.id = self.camera_id[cam.index]
        self.camera_current = cam.position

        self.create_camera_widget(cam)
        self.set_camera_positions()

        QApplication.processEvents()

    # Deactivates the current camera and all other cameras past its index if those are inactive.
    def deactivate_camera(self):
        if self.camera_current is None:
            print("No camera currently selected.")
            return
            
        cam = next((c for c in self.camera if c.absolute_position == self.camera_current), None)
        if not cam.active:
            print(f"Camera {self.camera_current} is not active.")
            return
        
        cam.active = False
        
        active_positions = [c.position for c in self.camera if c.active]

        def _remove_feed_widget(camera_obj):
            if camera_obj.feed_widget:
                self.stop_animation_for_widget(camera_obj.feed_widget)
                camera_obj.feed_widget.stop()
                
                camera_obj.feed_widget.hide()
                QApplication.processEvents()
                
                camera_obj.feed_widget.deleteLater()
                camera_obj.feed_widget = None    

        if not active_positions:
            for c in self.camera:
                _remove_feed_widget(c)
            self.camera_current = None
            QApplication.processEvents()
            self.cleanup_orphaned_widgets()
            self.set_camera_positions()
            return
        
        max_active_pos = max(active_positions)

        for c in self.camera:
            if (not c.active) and c.position > max_active_pos:
                _remove_feed_widget(c)
        
        if cam.position > max_active_pos:
            _remove_feed_widget(cam)
        else:
            if cam.feed_widget:
                self.stop_animation_for_widget(cam.feed_widget)
                cam.feed_widget.stop()

                if not hasattr(cam.feed_widget, 'placeholder_label') or cam.feed_widget.placeholder_label is None:
                    cam.feed_widget.placeholder_label = QLabel("Inactive", cam.feed_widget)
                    cam.feed_widget.placeholder_label.setAlignment(Qt.AlignCenter)
                    cam.feed_widget.placeholder_label.setStyleSheet("color: red; font-size: 16px; background-color: #1a1a1a;")
                    cam.feed_widget.placeholder_label.setGeometry(0, 0, cam.feed_widget.width(), cam.feed_widget.height())
                else:
                    cam.feed_widget.placeholder_label.setText("Inactive")

                cam.feed_widget.placeholder_label.show()

        candidates = [p for p in active_positions if p < self.camera_current]
        self.camera_current = max(candidates) if candidates else self.camera_current

        QApplication.processEvents()
        self.cleanup_orphaned_widgets()
        self.set_camera_positions()

    # ------------------------ Selection & Switch & Focus ------------------------

    def select_next_camera(self, direction):
        if self.camera_current is None:
            print("No camera currently selected.")
            return
        active_positions = [c.position for c in self.camera if c.active]
        if not active_positions:
            print("No active cameras.")
            return
        max_pos = max(active_positions) if active_positions else 0
        self.camera_current = (self.camera_current + direction) % (max_pos + 1)
        self.update_camera_borders()
    
    def switch_cam(self, index):
        cam_current_obj = next((c for c in self.camera if c.absolute_position == self.camera_current), None)
        cam_target_obj = next((c for c in self.camera if c.absolute_position == index), None)

        if not cam_current_obj or not cam_target_obj:
            print(f"Could not find cameras to switch: {self.camera_current}, {index}")
            return

        print(f"Switched Cameras {self.camera_current} with {index}")

        attrs_to_swap = [k for k in cam_current_obj.__dict__ if k not in ("feed_widget", "index", "absolute_position")]
        for attr in attrs_to_swap:
            cam_current_obj.__dict__[attr], cam_target_obj.__dict__[attr] = \
                cam_target_obj.__dict__[attr], cam_current_obj.__dict__[attr]

        if cam_current_obj.feed_widget and hasattr(cam_current_obj.feed_widget, "update_labels"):
            cam_current_obj.feed_widget.update_labels(
                self.camera_name[cam_current_obj.index],
                str(self.camera_id[cam_current_obj.index])
            )

        if cam_target_obj.feed_widget and hasattr(cam_target_obj.feed_widget, "update_labels"):
            cam_target_obj.feed_widget.update_labels(
                self.camera_name[cam_target_obj.index],
                str(self.camera_id[cam_target_obj.index])
            )

        cam_current_obj.absolute_position, cam_target_obj.absolute_position = \
            cam_target_obj.absolute_position, cam_current_obj.absolute_position

        self.camera_current = cam_current_obj.absolute_position

        self.switching_cams = False
        self.set_camera_positions()


    def toggle_focus(self):
        if self.camera_current is None:
            print("No camera currently selected.")
            return

        cam = self.camera[self.camera_current]
        if not cam.active or not cam.feed_widget:
            print(f"Camera {self.camera_current} is not active or has no widget.")
            return

        if not self.focus_mode:
            self.focus_mode = True
            self.focused_camera = self.camera_current
            self.pre_focus_geometries = {}

            for c in self.camera:
                if c.feed_widget:
                    self.pre_focus_geometries[c.position] = c.feed_widget.geometry()
                    if c.position != self.camera_current:
                        c.feed_widget.hide()

            self.stop_animation_for_widget(cam.feed_widget)
            self.tween_position_and_size(
                cam.feed_widget, 
                0, 0, 
                self.container.width(), 
                self.container.height(), 
                duration=500
            )
            cam.feed_widget.raise_()
            cam.feed_widget.name_label.raise_()
            cam.feed_widget.id_label.raise_()
            print(f"Entered focus mode on camera {self.camera_current}")
        else:
            self.focus_mode = False
            self.focused_camera = None

            for c in self.camera:
                if c.active and c.feed_widget:
                    c.feed_widget.show()

            self.set_camera_positions()
            print("Exited focus mode")

    # ------------------------ Move Index ------------------------

    def move_index(self, direction):
        if self.camera_current is None:
            print("No camera currently selected.")
            return

        cam = self.camera[self.camera_current]
        if not cam.active:
            print(f"Camera {self.camera_current} is not active.")
            return

        start_index = cam.index
        current_index = start_index
        
        for _ in range(self.camera_total):
            current_index = (current_index + direction) % self.camera_total
            active_indexes = [c.index for c in self.get_active_cameras()]
            if current_index not in active_indexes or current_index == start_index:
                cam.index = current_index
                break

        if cam.feed_widget and hasattr(cam.feed_widget, 'update_labels'):
            cam.feed_widget.update_labels(
                self.camera_name[cam.index],
                str(self.camera_id[cam.index])
            )
        
        # self.set_camera_positions()

    # ------------------------ Camera Widgets ------------------------

    def create_camera_widget(self, cam):
        import time
        cam.is_loading = True
        cam.loading_start_time = time.time()
        cam.loading_progress = 0.0

        active_positions = [c.position for c in self.camera if c.active] or [cam.position]
        max_pos = max(active_positions)

        size = self.target_sizes[max(max_pos - 1, 0)][cam.position]
        pos = self.target_positions[max(max_pos - 1, 0)][cam.position]

        x = int(pos[0] * self.container.width())
        y = int(pos[1] * self.container.height())
        w = int(size[0] * self.container.width())
        h = int(size[1] * self.container.height())

        use_camera = self.zed_available and self.use_video_overlay

        if use_camera:
            pipeline = f"zedxonesrc camera-id={self.camera_id[cam.index]} ! queue ! videoconvert ! queue ! {self.video_sink}"
        else:
            pipeline = None

        cam.loading_progress = 0.2

        try:
            camera_feed_widget = GStreamerVideoWidget(
                pipeline if pipeline else "",
                camera_name=self.camera_name[cam.index],
                camera_id=str(self.camera_id[cam.index]),
                use_overlay=use_camera,
                parent=self.container,
                cam_width=self.camera_ratios[cam.index][0],
                cam_height=self.camera_ratios[cam.index][1]
            )

            camera_feed_widget.setGeometry(x, y, w, h)
            camera_feed_widget.show()
            camera_feed_widget.name_label.show()
            camera_feed_widget.id_label.show()
            camera_feed_widget.name_label.raise_()
            camera_feed_widget.id_label.raise_()

            cam.loading_animation_widget = LoadingAnimationWidget(camera_feed_widget)
            cam.loading_animation_widget.setGeometry(0, 0, w, h)
            cam.loading_animation_widget.show()
            cam.loading_animation_widget.raise_()

            cam.loading_animation_widget.start_loading_animation(
                center_x = w // 2,
                center_y = h // 2,
                bar_width = min(200, max(40, w - 40)),
                bar_height = 20
            )

            QTimer.singleShot(500, lambda: cam.loading_animation_widget.update_progress(0.5)
                              if cam.loading_animation_widget else None)

            def on_camera_ready():
                cam.loading_progress = 1.0
                cam.is_loading = False
                cam.loading_duration = time.time() - cam.loading_start_time
                print(f"Camera {cam.position} loaded in {cam.loading_duration:.2f} seconds")

                if cam.loading_animation_widget:
                    cam.loading_animation_widget.complete_animation()
                    cam.loading_animation_widget = None

            try:
                camera_feed_widget.pipeline_ready.connect(on_camera_ready)
            except Exception:
                pass

            QApplication.processEvents()
            camera_feed_widget.start()

            cam.loading_progress = 0.6
            QTimer.singleShot(1000, lambda: cam.loading_animation_widget.update_progress(0.6)
                              if cam.loading_animation_widget else None)

            cam.feed_widget = camera_feed_widget

            if not use_camera:
                def complete_simulated_loading():
                    if not cam.loading_animation_widget:
                        return
                    cam.loading_progress = 1.0
                    cam.is_loading = False
                    cam.loading_duration = time.time() - cam.loading_start_time
                    cam.loading_animation_widget.complete_animation()
                    cam.loading_animation_widget = None
                QTimer.singleShot(1000, complete_simulated_loading)

        except Exception as e:
            self.get_logger().error(f"Failed to create camera widget: {e}")
            cam.loading_progress = 0.0
            cam.is_loading = False
            cam.loading_duration = time.time() - cam.loading_start_time

            if cam.loading_animation_widget:
                cam.loading_animation_widget.deleteLater()
                cam.loading_animation_widget = None

            placeholder = QWidget(self.container)
            placeholder.setGeometry(x, y, w, h)
            placeholder.setStyleSheet("background-color: #1a1a1a; border: 3px solid red;")
            placeholder.show()
            cam.feed_widget = placeholder

    def set_camera_positions(self):
        active_positions = [c.position for c in self.camera if c.active]
        if not active_positions:
            return
        max_pos = max(active_positions)

        for cam in self.camera:
            if not cam.active and cam.feed_widget:
                self.stop_animation_for_widget(cam.feed_widget)
                continue

        for cam in self.camera:
            if not cam.active:
                continue

            size = self.target_sizes[max_pos][cam.position]
            pos = self.target_positions[max_pos][cam.position]

            end_x = int(pos[0] * self.container.width())
            end_y = int(pos[1] * self.container.height())
            end_w = int(size[0] * self.container.width())
            end_h = int(size[1] * self.container.height())
            self.tween_position_and_size(cam.feed_widget, end_x, end_y, end_w, end_h, duration = 500)

        self.update_camera_borders()

    def cleanup_orphaned_widgets(self):
        if not self.container:
            return
        
        valid_widgets = {id(cam.feed_widget) for cam in self.camera if cam.feed_widget}
        for child in self.container.children():
            if not isinstance(child, QWidget):
                continue
            child_id = id(child)
            if child_id not in valid_widgets and child_id != id(self.container):
                self.stop_animation_for_widget(child)
                child.hide()
                child.deleteLater()

    def update_camera_borders(self):
        for cam in self.camera:
            if not cam.feed_widget:
                continue
            color = "blue" if cam.position == self.camera_current else "red"
            if hasattr(cam.feed_widget, 'set_border_color'):
                cam.feed_widget.set_border_color(color)

    # ------------------------ Tween Animation ------------------------
    def stop_animation_for_widget(self, widget):
        if not widget:
            return
        wid = id(widget)
        if wid in self.animations:
            anim = self.animations.pop(wid)
            if anim:
                anim.stop()
                anim.deleteLater()

    def tween_position_and_size(self, widget, end_x, end_y, end_w, end_h, ease_style=QEasingCurve.OutExpo, duration=500):
        if not widget or not widget.parent():
            return

        cam = next((cam for cam in self.camera if cam.feed_widget == widget), None)
        if not cam: #or not cam.active:
            return

        self.stop_animation_for_widget(widget)

        start_geom = widget.geometry()

        animation = QVariantAnimation()
        animation.setDuration(duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(ease_style)

        def update_geometry(value):
            if not widget or widget.parent() is None or not cam.active:
                animation.stop()
                return
            new_x = int(start_geom.x() + (end_x - start_geom.x()) * value)
            new_y = int(start_geom.y() + (end_y - start_geom.y()) * value)
            new_w = int(start_geom.width() + (end_w - start_geom.width()) * value)
            new_h = int(start_geom.height() + (end_h - start_geom.height()) * value)
            widget.setGeometry(new_x, new_y, new_w, new_h)
            if hasattr(widget, 'name_label') and hasattr(widget, 'id_label'):
                widget.name_label.raise_()
                widget.id_label.raise_()

        animation.valueChanged.connect(update_geometry)
        animation.start()
        self.animations[id(widget)] = animation

    # ------------------------ Print Information ------------------------

    def print_infomation(self):
        print(f"Current Selected: {self.camera_current}")
        print(f"{'Pos':>3} | {'Active':>6} | {'Index':>5} | {'ID':>9} | {'X':>4} | {'Y':>4} | {'W':>4} | {'H':>4}")
        print("-" * 50)
        for cam in self.camera:
            widget = cam.feed_widget
            if widget:
                geom = widget.geometry()
                x, y, w, h = geom.x(), geom.y(), geom.width(), geom.height()
            else:
                x = y = w = h = 0
            active_str = "\033[92mTrue  \033[0m" if cam.active else "\033[91mFalse \033[0m"
            print(f"{cam.position:>3} | {active_str} | {cam.index:>5} | {cam.id:>9} | {x:>4} | {y:>4} | {w:>4} | {h:>4}")


def main():
    rclpy.init()
    node = CameraNode()

    app = QApplication([])

    key_filter = KeyEventFilter(node)
    app.installEventFilter(key_filter)

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