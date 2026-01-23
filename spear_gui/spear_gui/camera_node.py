import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo, GLib
import sys
import rclpy
import math
from rclpy.node import Node
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QFrame
from PySide6.QtCore import QThread, Signal, QTimer, QVariantAnimation, QEasingCurve, Qt, QObject, QEvent
from PySide6.QtGui import QColor
from std_msgs.msg import String
from collections import deque
from dataclasses import dataclass, field
from typing import Optional
import time

# ------------------------ CONFIGURATION ------------------------
@dataclass
class CameraConfig:
    # Configuration for camera system
    names: list = field(default_factory=lambda: [f"Placeholder {i+1}" for i in range(8)])
    ids: list = field(default_factory=lambda: [307142683, 302801547, 58896881, 3, 4, 5, 6, 7])
    ratios: list = field(default_factory=lambda: [[1920, 1080]] * 8)
    
    # Display layout configurations [Target Camera][Display Mode][Scales][Position(0-1), Size(2-3)]
    layouts: list = field(default_factory=lambda: [
        [[[0,1,1,1],[0,0,1,1],[1/6,0,5/6,1],[1/6,0,5/6,1],[1/6,0,5/6,1],[1/6,0,5/6,1],[1/6,0,4/6,1]],
         [[0,1,1,1],[0,0,1,1],[0,0,1,1/2],[0,0,1,1/2],[0,0,1/2,1/2],[0,0,1/2,1/2],[0,0,1/3,1/2],[0,0,1/3,1/2],[0,0,1/4,1/2]],
         [[0,1,1,1],[0,0,1,1],[0,0,1,1/2]]],
        [[[-1/6,0,1/6,1],[0,0,1/6,1],[0,0,1/6,1/2],[0,0,1/6,1/3],[0,0,1/6,1/4]],
         [[0,1,1,1/2],[0,1/2,1,1/2],[0,1/2,1/2,1/2],[1/2,0,1/2,1/2],[1/2,0,1/2,1/2],[1/3,0,1/3,1/2],[1/3,0,1/3,1/2],[1/4,0,1/4,1/2]],
         [[0,1,1,1/2],[0,1/2,1,1/2],[0,1/2,1/2,1/2]]],
        [[[0,1,1/6,1/2],[0,1/2,1/6,1/2],[0,1/3,1/6,1/3],[0,1/4,1/6,1/4]],
         [[1,1/2,1/2,1/2],[1/2,1/2,1/2,1/2],[0,1/2,1/2,1/2],[0,1/2,1/3,1/2],[2/3,0,1/3,1/2],[2/3,0,1/3,1/2],[2/4,0,1/4,1/2]],
         [[1,1/2,1/2,1/2],[1/2,1/2,1/2,1/2],[1/2,1/2,1/2,1/4],[1/2,1/2,1/2,1/4],[1/2,1/2,1/4,1/4],[1/2,1/2,1/4,1/4],[1/2,1/2,1/6,1/4]]],
        [[[0,1,1/6,1/3],[0,2/3,1/6,1/3],[0,2/4,1/6,1/4]],
         [[1,1/2,1/2,1/2],[1/2,1/2,1/2,1/2],[1/3,1/2,1/3,1/2],[0,1/2,1/3,1/2],[0,1/2,1/4,1/2],[3/4,0,1/4,1/2]],
         [[1/2,1,1/2,1/4],[1/2,3/4,1/2,1/4],[1/2,3/4,1/4,1/4],[3/4,1/2,1/4,1/4],[3/4,1/2,1/4,1/4],[4/6,1/2,1/6,1/4]]],
        [[[0,1,1/6,1/4],[0,3/4,1/6,1/4]],
         [[1,1/2,1/3,1/2],[2/3,1/2,1/3,1/2],[1/3,1/2,1/3,1/2],[1/4,1/2,1/4,1/2],[0,1/2,1/4,1/2]],
         [[1,3/4,1/4,1/4],[3/4,3/4,1/4,1/4],[1/2,3/4,1/4,1/4],[1/2,3/4,1/6,1/4],[5/6,1/2,1/6,1/4]]],
        [[[1,0,1/6,1],[5/6,0,1/6,1],[5/6,0,1/6,1/2],[5/6,0,1/6,1/3]],
         [[1,1/2,1/3,1/2],[2/3,1/2,1/3,1/2],[2/4,1/2,1/4,1/2],[1/4,1/2,1/4,1/2]],
         [[1,3/4,1/4,1/4],[3/4,3/4,1/4,1/4],[4/6,3/4,1/6,1/4],[1/2,3/4,1/6,1/4]]],
        [[[5/6,1,1/6,1/2],[5/6,1/2,1/6,1/2],[5/6,1/3,1/6,1/3]],
         [[1,1/2,1/4,1/2],[3/4,1/2,1/4,1/2],[2/4,1/2,1/4,1/2]],
         [[1,3/4,1/6,1/4],[5/6,3/4,1/6,1/4],[4/6,3/4,1/6,1/4]]],
        [[[5/6,1,1/6,1/3],[5/6,2/3,1/6,1/3]],
         [[1,1/2,1/4,1/2],[3/4,1/2,1/4,1/2]],
         [[1,3/4,1/6,1/4],[5/6,3/4,1/6,1/4]]],
    ])

# ------------------------ UTILITIES ------------------------
class KeyEventFilter(QObject):
    # Global key event filter for ROS2 publishing
    def __init__(self, node):
        super().__init__()
        self.node = node

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and event.text():
            msg = String(data=event.text())
            self.node.key_pub.publish(msg)
            print(f"[Key] {event.text()}")
            return True
        return False

class AnimationManager:
    # Manages widget animations
    def __init__(self):
        self.animations = {}
    
    def stop(self, widget):
        wid = id(widget)
        if wid in self.animations:
            anim = self.animations.pop(wid)
            anim.stop()
            anim.deleteLater()
    
    def tween(self, widget, end_x, end_y, end_w, end_h, duration=500, easing=QEasingCurve.OutExpo):
        if not widget or not widget.parent(): return
        
        self.stop(widget)
        start = widget.geometry()
        anim = QVariantAnimation()
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(easing)
        
        def update(t):
            if widget and widget.parent():
                widget.setGeometry(
                    int(start.x() + (end_x - start.x()) * t),
                    int(start.y() + (end_y - start.y()) * t),
                    int(start.width() + (end_w - start.width()) * t),
                    int(start.height() + (end_h - start.height()) * t)
                )
        
        anim.valueChanged.connect(update)
        anim.start()
        self.animations[id(widget)] = anim

# ------------------------ GSTREAMER ------------------------
class GStreamerThread(QThread):
    # Handles GStreamer pipeline in a separate thread
    finished = Signal()
    error_occurred = Signal(str)
    state_changed = Signal(str)

    def __init__(self, pipeline_str, window_id=None):
        super().__init__()
        self.pipeline_str = pipeline_str
        self.window_id = window_id
        self.pipeline = None
        self.loop = GLib.MainLoop()
        self._init_pipeline()

    def _init_pipeline(self):
        try:
            Gst.init(None)
            self.pipeline = Gst.parse_launch(self.pipeline_str)
            if not self.pipeline:
                raise RuntimeError(f"Failed to create pipeline: {self.pipeline_str}")
            
            self.bus = self.pipeline.get_bus()
            self.bus.add_signal_watch()
            self.bus.connect("message", self._on_message)
            
            if self.window_id is not None:
                self.bus.enable_sync_message_emission()
                self.bus.connect("sync-message::element", self._on_sync_message)
        except Exception as e:
            print(f"Pipeline creation failed: {e}", file=sys.stderr)
            self.error_occurred.emit(str(e))
            self.pipeline = None

    def _on_sync_message(self, bus, message):
        if message.get_structure() and message.get_structure().get_name() == 'prepare-window-handle':
            if self.window_id is not None:
                try:
                    message.src.set_window_handle(self.window_id)
                except Exception as e:
                    print(f"Failed to set window handle: {e}", file=sys.stderr)

    def run(self):
        if not self.pipeline: return
        
        if self.pipeline.set_state(Gst.State.PLAYING) == Gst.StateChangeReturn.FAILURE:
            self.error_occurred.emit("Failed to set pipeline to PLAYING")
            return
        
        print("Pipeline running")
        self.loop.run()

    def stop(self):
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
        self.loop.quit()

    def _on_message(self, bus, message):
        mtype = message.type
        if mtype == Gst.MessageType.EOS:
            print("End of stream")
            self.loop.quit()
        elif mtype == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"Error: {err}\nDebug: {debug}", file=sys.stderr)
            self.error_occurred.emit(f"GStreamer error: {err}")
            self.loop.quit()
        elif mtype == Gst.MessageType.STATE_CHANGED and message.src == self.pipeline:
            _, new_state, _ = message.parse_state_changed()
            self.state_changed.emit(new_state.value_nick)
        return True

# ------------------------ UI COMPONENTS ------------------------
class CornerIndicator(QWidget):
    # Animated corner brackets for camera selection
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setStyleSheet("background: transparent;")
        
        self.gap, self.length, self.thickness = 8, 40, 4
        self.progress = 0.0
        self.animation = None
        self.lines = [QFrame(self) for _ in range(8)]
        for line in self.lines:
            line.hide()
    
    def set_selected(self, selected):
        target = 1.0 if selected else 0.0
        if self.animation:
            self.animation.stop()
        
        self.animation = QVariantAnimation()
        self.animation.setDuration(200)
        self.animation.setStartValue(self.progress)
        self.animation.setEndValue(target)
        self.animation.valueChanged.connect(lambda v: self._update(v))
        self.animation.start()
    
    def _update(self, progress):
        try:
            if not self.parent(): return
        except:
            return
        self.progress = progress
        
        w, h = self.parent().width(), self.parent().height()
        t = min(1, max(math.sqrt(1 - (progress - 1) ** 4), 0))
        
        ox = int((1 - t) * (w / 2 - self.gap - self.length))
        oy = int((1 - t) * (h / 2 - self.gap - self.length))
        l, th = t * self.length, math.ceil(t * self.thickness)
        
        geometries = [
            (self.gap + ox, self.gap + oy, l, th),
            (self.gap + ox, self.gap + oy, th, l),
            (w - self.gap - l - ox, self.gap + oy, l, th),
            (w - self.gap - th - ox, self.gap + oy, th, l),
            (w - self.gap - l - ox, h - self.gap - th - oy, l, th),
            (w - self.gap - th - ox, h - self.gap - l - oy, th, l),
            (self.gap + ox, h - self.gap - th - oy, l, th),
            (self.gap + ox, h - self.gap - l - oy, th, l),
        ]

        for i, (x, y, width, height) in enumerate(geometries):
            self.lines[i].setGeometry(x, y, width, height)
            self.lines[i].setStyleSheet("background-color: rgba(255, 255, 255, 255);")
            self.lines[i].setVisible(progress > 0.01)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update(self.progress)
        self.setGeometry(0, 0, self.parent().width(), self.parent().height())

class LoadingAnimation(QWidget):
    # Loading bar animation for camera initialization
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setStyleSheet("background: transparent;")
        
        self.outline_segments = [QFrame(self) for _ in range(4)]
        for seg in self.outline_segments:
            seg.setStyleSheet("background-color: white;")
            seg.hide()
        
        self.outline = QFrame(self)
        self.outline.setStyleSheet("border: 2px solid white;")
        self.outline.hide()
        
        self.fill = QFrame(self.outline)
        self.fill.setStyleSheet("background-color: white;")
        self.fill.hide()
        
        self.draw_timer = QTimer()
        self.draw_timer.timeout.connect(self._animate_draw)
        self.draw_progress = 0.0
        self.is_complete = False
        self.gap = 4
    
    def start(self, center_x, center_y, bar_width=200, bar_height=20):
        self.bar_w, self.bar_h = bar_width, bar_height
        self.center_x, self.center_y = center_x, center_y
        self.draw_progress = 0.0
        self.draw_timer.start(16)
    
    def _animate_draw(self):
        self.draw_progress = min(1.0, self.draw_progress + 0.04)
        t = 1 - (1 - self.draw_progress) ** 5
        
        if t >= 1.0:
            self.draw_timer.stop()
            for seg in self.outline_segments:
                seg.hide()
            self.outline.show()
            self.fill.show()
            
            x = self.center_x - self.bar_w // 2
            y = self.center_y - self.bar_h // 2
            self.outline.setGeometry(x, y, self.bar_w, self.bar_h)
            self.fill.setGeometry(self.gap, self.gap, 0, self.bar_h - 2 * self.gap)
            return
        
        # Draw outline segments
        for seg in self.outline_segments:
            seg.show()
        
        d = t * 2 * (self.bar_w + self.bar_h)
        x0 = self.center_x - self.bar_w // 2
        y0 = self.center_y - self.bar_h // 2
        w = self.bar_w
        h = self.bar_h
        
        self.outline_segments[0].setGeometry(x0, y0, int(min(d, w)), 2)
        self.outline_segments[1].setGeometry(x0 + w - 2, y0, 2, int(min(max(0, d - w), h)))
        self.outline_segments[2].setGeometry(x0 + max(0, w - int(max(0, d - w - h))), y0 + h - 2, int(max(0, min(d - w - h, w))), 2)
        self.outline_segments[3].setGeometry(x0, y0 + h - int(max(0, d - 2 * w - h)), 2, int(max(0, d - 2 * w - h)))
    
    def update_progress(self, progress):
        # Update fill progress
        try:
            if self.is_complete or not self.fill or self.fill.isHidden():
                return
        except:
            return
        
        target = int((self.bar_w - 2 * self.gap) * progress)
        anim = QVariantAnimation()
        anim.setDuration(500)
        anim.setStartValue(self.fill.width())
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.InOutCubic)
        
        def update_fill(v):
            try:
                if self.fill and not self.fill.isHidden():
                    self.fill.setGeometry(self.gap, self.gap, int(v), self.bar_h - 2 * self.gap)
            except:
                return
        
        anim.valueChanged.connect(update_fill)
        anim.start()
        self._fill_anim = anim  # Keep reference
    
    def complete_animation(self):
        # Complete and expand to border
        try:
            if self.is_complete or not self.fill or self.fill.isHidden():
                return
        except:
            return
        self.is_complete = True
        
        # Fill to 100%
        anim = QVariantAnimation()
        anim.setDuration(300)
        anim.setStartValue(self.fill.width())
        anim.setEndValue(self.bar_w - 2 * self.gap)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        
        def update_complete(v):
            if self.fill and not self.fill.isHidden():
                self.fill.setGeometry(self.gap, self.gap, int(v), self.bar_h - 2 * self.gap)
        
        anim.valueChanged.connect(update_complete)
        anim.finished.connect(self._expand_to_border)
        anim.start()
        self._complete_anim = anim  # Keep reference
    
    def _expand_to_border(self):
        # Expand to fill parent
        try:
            if not self.parent() or not self.outline or not self.fill:
                return
        except:
            return
        
        pw, ph = self.parent().width(), self.parent().height()
        sx, sy = self.outline.x(), self.outline.y()
        sw, sh = self.outline.width(), self.outline.height()
        fw, fh = self.fill.width(), self.fill.height()
        
        anim = QVariantAnimation()
        anim.setDuration(500)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutExpo)
        
        def update(t):
            if not self.outline or not self.fill or not self.parent():
                return
            
            # Animate outline expansion
            self.outline.setGeometry(
                int(sx * (1 - t)), 
                int(sy * (1 - t)),
                int(sw * (1 - t) + pw * t), 
                int(sh * (1 - t) + ph * t)
            )
            
            # Animate fill expansion
            new_fw = int(fw * (1 - t) + (pw - 2 * self.gap) * t)
            new_fh = int(fh * (1 - t) + (ph - 2 * self.gap) * t)
            self.fill.setGeometry(self.gap, self.gap, new_fw, new_fh)
            
            # Fade out fill
            opacity = max(0, int(200 * (1 - t) ** 5))
            self.fill.setStyleSheet(f"background: rgba(255, 255, 255, {opacity});")
            
            if t >= 0.95:
                self.fill.hide()
        
        anim.valueChanged.connect(update)
        anim.finished.connect(lambda: (self.hide(), QTimer.singleShot(100, self.deleteLater)))
        anim.start()
        self._expand_anim = anim  # Keep reference

class VideoWidget(QWidget):
    pipeline_ready = Signal()
    
    def __init__(self, pipeline_str, name="", cam_id="", use_overlay=True, parent=None, cam_width=1920, cam_height=1080):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self.camera_aspect_ratio = cam_width / cam_height
        
        # Video layer
        self.video_layer = QWidget(self)
        self.video_layer.setStyleSheet("background-color: black;")
        if use_overlay:
            self.video_layer.setAttribute(Qt.WA_NativeWindow)
        
        # Overlay layer
        self.overlay = QWidget(self)
        self.overlay.setStyleSheet("background: transparent;")
        self.overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        self.border = QFrame(self.overlay)
        self.border.setStyleSheet("background: transparent; border: 3px solid white;")
        self.border.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        self.name_label = QLabel(name, self.overlay)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold; background-color: rgba(0,0,0,150); padding: 2px;")
        
        self.id_label = QLabel(f"ID: {cam_id}", self.overlay)
        self.id_label.setAlignment(Qt.AlignCenter)
        self.id_label.setStyleSheet("color: white; font-size: 10px; background-color: rgba(0,0,0,150); padding: 2px;")
        
        self.corner = CornerIndicator(self.overlay)
        
        self.placeholder = None
        if not use_overlay:
            self.placeholder = QLabel("No Camera\nDetected", self.video_layer)
            self.placeholder.setAlignment(Qt.AlignCenter)
            self.placeholder.setStyleSheet("color: white; font-size: 16px; background-color: #1a1a1a;")
        
        self._setup_layers()
        self.thread = None
        self.pipeline_str = pipeline_str
        self.use_overlay = use_overlay
    
    def _setup_layers(self):
        # Set up layer z-order
        self.video_layer.lower()
        self.overlay.raise_()
        self.border.raise_()
        self.name_label.raise_()
        self.id_label.raise_()
        self.corner.raise_()
    
    def _resize_video_area(self):
        # Resize video layer to maintain aspect ratio
        container_w, container_h = self.width(), self.height()
        target_ar = self.camera_aspect_ratio
        container_ar = container_w / container_h

        if container_ar > target_ar:  # container is wider
            video_h = container_h
            video_w = int(video_h * target_ar)
        else:  # container is taller
            video_w = container_w
            video_h = int(video_w / target_ar)

        video_x = (container_w - video_w) // 2
        video_y = (container_h - video_h) // 2
        
        self.video_layer.setGeometry(video_x, video_y, video_w, video_h)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        
        self._resize_video_area()
        
        self.overlay.setGeometry(0, 0, w, h)
        self.border.setGeometry(0, 0, w, h)
        self.name_label.setGeometry(0, 5, w, 20)
        self.id_label.setGeometry(0, 25, w, 15)
        if self.placeholder:
            self.placeholder.setGeometry(0, 0, self.video_layer.width(), self.video_layer.height())
        self.corner._update(self.corner.progress)
    
    def start(self):
        if not self.use_overlay:
            return
        
        self.show()
        self.video_layer.show()
        QApplication.processEvents()
        
        print(f"Video layer winId: {self.video_layer.winId()}, size: {self.video_layer.size()}, visible: {self.video_layer.isVisible()}")
        
        self.thread = GStreamerThread(self.pipeline_str, self.video_layer.winId())
        self.thread.state_changed.connect(lambda s: self.pipeline_ready.emit() if s == "playing" else None)
        self.thread.start()
        
        self._setup_layers()
    
    def stop(self):
        if self.thread:
            self.thread.stop()
            self.thread.wait(1000)
    
    def update_labels(self, name, cam_id):
        self.name_label.setText(name)
        self.id_label.setText(f"ID: {cam_id}")
    
    def set_selected(self, selected):
        self.corner.set_selected(selected)

# ------------------------ CAMERA MODEL ------------------------
@dataclass
class Camera:
    # Camera state model
    position: int
    index: int = -1
    active: bool = False
    widget: Optional[QWidget] = None
    loading_animation: Optional[LoadingAnimation] = None
    loading_start: float = 0.0
    
    @property
    def id(self):
        return -1 if self.index == -1 else self.index

# ------------------------ CAMERA NODE ------------------------
class CameraNode(Node):
    # ROS2 node for camera management
    def __init__(self):
        super().__init__('camera_node')
        
        self.config = CameraConfig()
        self.cameras = [Camera(position=i) for i in range(len(self.config.ids))]
        self.current = 0
        self.display_mode = 0
        self.focus_mode = False
        self.switching_mode = False
        self.always_remove_inactive_cams = True
        
        self.container = None
        self.anim_manager = AnimationManager()
        self.command_queue = deque()
        self.processing = False
        
        # Check capabilities
        Gst.init(None)
        self.zed_available = self._check_element('zedxonesrc')
        self.video_sink = self._find_video_sink()
        self.use_overlay = self.video_sink in ['ximagesink', 'xvimagesink', 'glimagesink']
        
        if not self.zed_available:
            self.get_logger().warn("\033[93mZED SDK not detected\033[0m")
        if not self.use_overlay:
            self.get_logger().warn("\033[93mVideo overlay unavailable\033[0m")
        
        # ROS2 publishers/subscribers
        self.key_pub = self.create_publisher(String, "key", 10)
        self.create_subscription(String, 'key', self._on_key, 10)
    
    def _check_element(self, name):
        try:
            element = Gst.ElementFactory.make(name, None)
            if element is not None:
                return True
            else:
                self.get_logger().warn(f"GStreamer element '{name}' not found")
                return False
        except Exception as e:
            self.get_logger().error(f"Failed to check GStreamer element '{name}': {e}")
            return False

    def _find_video_sink(self):
        sinks = ['ximagesink', 'xvimagesink', 'glimagesink', 'autovideosink']
        
        for sink in sinks:
            if self._check_element(sink):
                print(f"Found video sink: {sink}")
                return sink
    
    def setup_gui(self, parent=None):
        # Initialize GUI container
        self.container = QWidget(parent)
        self.container.setMinimumSize(400, 200)
        self.container.resize(800, 400)
        self.container.setStyleSheet("background-color: #2b2b2b;")
    
    def _on_key(self, msg):
        # Handle keyboard input
        self.command_queue.append(msg.data.lower())
        if not self.processing:
            self._process_queue()
    
    def _process_queue(self):
        # Process command queue for keyboard inputs
        if not self.command_queue:
            self.processing = False
            return
        
        self.processing = True
        key = self.command_queue.popleft()
        
        handlers = {
            'p': lambda: rclpy.shutdown(),
            'w': self._activate_camera,
            's': self._deactivate_camera,
            'e': lambda: self._select_next(1),
            'q': lambda: self._select_next(-1),
            'd': lambda: self._move_index(1),
            'a': lambda: self._move_index(-1),
            'n': lambda: self._change_display(-1),
            'm': lambda: self._change_display(1),
            'f': self._toggle_focus,
            'r': lambda: setattr(self, 'switching_mode', not self.switching_mode),
        }
        
        if key in handlers:
            handlers[key]()
        elif key.isdigit():
            idx = int(key)
            if self.switching_mode:
                self._switch_cameras(idx)
            else:
                self._select_camera(idx)
        
        if self.switching_mode and key != 'r' and not key.isdigit():
            self.switching_mode = False
        
        self._print_status()
        self._cleanup_orphans()
        QTimer.singleShot(20, self._process_queue)
    
    def _activate_camera(self):
        # Activate next inactive camera
        try:
            cam = next(c for c in self.cameras if not c.active)
        except StopIteration:
            print("No inactive cameras available")
            return
        
        cam.active = True
        
        # Find an unused index
        active_indices = {c.index for c in self.cameras if c.active and c is not cam}
        if cam.index == -1 or cam.index in active_indices:
            for i in range(len(self.config.ids)):
                if i not in active_indices:
                    cam.index = i
                    break
        
        self.current = cam.position
        self._create_widget(cam)
        self._update_layout()
    
    def _deactivate_camera(self):
        # Deactivate current camera
        cam = next((c for c in self.cameras if c.position == self.current), None)
        if not cam or not cam.active:
            print(f"Camera {self.current} not active")
            return
        
        original_pos = cam.position
        print(original_pos)
        cam.active = False
        active_positions = [c.position for c in self.cameras if c.active]
        
        if not active_positions:
            for c in self.cameras:
                self._remove_widget(c)
            self.current = None
            self._update_layout()
            return
        
        max_pos = max(active_positions)
        
        # Remove widgets beyond max active position
        for c in self.cameras:
            if not c.active and (self.always_remove_inactive_cams or c.position > max_pos):
                self._remove_widget(c)
        
        if self.always_remove_inactive_cams:
            self._remove_widget(cam)
            found_inactive = True
            while found_inactive:
                found_inactive = False
                for i in range(len(self.cameras)):
                    if not self.cameras[i].active and self.cameras[i].position < max_pos:
                        found_inactive = True
                        self._select_camera(i, True)
                        self._switch_cameras(i + 1, True)
                        self._print_status()
                        
        elif cam.position > max_pos:
            self._remove_widget(cam)
        else:
            # Show inactive placeholder
            if cam.widget:
                self.anim_manager.stop(cam.widget)
                cam.widget.stop()
                if not cam.widget.placeholder is None:
                    print("Test")
                    cam.widget.placeholder = QLabel("Inactive", cam.widget.video_layer)
                    cam.widget.placeholder.setAlignment(Qt.AlignCenter)
                    cam.widget.placeholder.setStyleSheet("color: white; font-size: 16px; background-color: #1a1a1a;")
                cam.widget.placeholder.setGeometry(0, 0, cam.widget.width(), cam.widget.height())
                cam.widget.placeholder.show()
        
        # Update current selection
        candidates = [p for p in active_positions if p < self.current]
        self.current = max(candidates) if candidates else self.current
        if self.always_remove_inactive_cams:
            self._select_camera(original_pos, True)
            if not self.cameras[self.current].active:
                self._select_camera(max(candidates), True)
        
        self._update_layout()
    
    def _select_camera(self, index, bypass_inactive=False):
        # Select camera by position
        if not bypass_inactive and not self.cameras[index].active:
            print(f"Camera {index} not active")
            return
        if bypass_inactive:
            index = next((c.position for c in self.cameras if c.position == index), 0)
        self.current = index
        print(f"Current Index: {index}")
        self._update_borders()
    
    def _select_next(self, direction):
        # Select next/previous camera
        active_positions = [c.position for c in self.cameras if c.active]
        if not active_positions:
            return
        max_pos = max(active_positions)
        self.current = (self.current + direction) % (max_pos + 1)
        self._update_borders()
    
    def _switch_cameras(self, target_pos, bypass_inactive=False):
        # Switch two camera positions
        cam_current = next((c for c in self.cameras if c.position == self.current), None)
        cam_target = next((c for c in self.cameras if c.position == target_pos), None)
        active_positions = [c.position for c in self.cameras if c.active]

        if not bypass_inactive and (not cam_current or not cam_target or not active_positions or max(active_positions) < cam_target.position):
            return
        
        print(f"Switched cameras {self.current} <-> {target_pos}")
        
        # Swap all attributes except position and widget
        attrs_to_swap = ['index', 'active', 'loading_animation', 'loading_start']
        for attr in attrs_to_swap:
            temp = getattr(cam_current, attr)
            setattr(cam_current, attr, getattr(cam_target, attr))
            setattr(cam_target, attr, temp)
        
        # Swap widgets
        cam_current.widget, cam_target.widget = cam_target.widget, cam_current.widget
        
        # Update labels on both widgets
        if cam_current.widget and hasattr(cam_current.widget, 'update_labels'):
            cam_current.widget.update_labels(
                self.config.names[cam_current.index] if cam_current.index >= 0 else "Unknown",
                str(self.config.ids[cam_current.index]) if cam_current.index >= 0 else "N/A"
            )
        
        if cam_target.widget and hasattr(cam_target.widget, 'update_labels'):
            cam_target.widget.update_labels(
                self.config.names[cam_target.index] if cam_target.index >= 0 else "Unknown",
                str(self.config.ids[cam_target.index]) if cam_target.index >= 0 else "N/A"
            )
        
        self.current = self.current  # Keep current selection on same position
        self.switching_mode = False
        
        # Animate the widgets to their new positions
        self._update_layout()
    
    def _move_index(self, direction):
        # Move camera index (change camera feed)
        cam = next((c for c in self.cameras if c.position == self.current), None)
        if not cam or not cam.active:
            return
        
        start_idx = cam.index
        active_indices = [c.index for c in self.cameras if c.active]
        
        for _ in range(len(self.config.ids)):
            cam.index = (cam.index + direction) % len(self.config.ids)
            if cam.index not in active_indices or cam.index == start_idx:
                break
        
        if cam.widget and hasattr(cam.widget, 'update_labels'):
            cam.widget.update_labels(self.config.names[cam.index], str(self.config.ids[cam.index]))
    
    def _change_display(self, direction):
        # Change display layout mode
        self.display_mode = (self.display_mode + direction) % len(self.config.layouts[0])
        self._update_layout()
    
    def _toggle_focus(self):
        # Toggle focus mode on current camera
        cam = next((c for c in self.cameras if c.position == self.current), None)
        if not cam or not cam.active or not cam.widget:
            return
        
        if not self.focus_mode:
            self.focus_mode = True
            for c in self.cameras:
                if c.widget and c.position != self.current:
                    c.widget.hide()
            
            self.anim_manager.stop(cam.widget)
            self.anim_manager.tween(cam.widget, 0, 0, self.container.width(), self.container.height())
            print(f"Focus mode: camera {self.current}")
        else:
            self.focus_mode = False
            for c in self.cameras:
                if c.active and c.widget:
                    c.widget.show()
            self._update_layout()
            print("Focus mode: off")
    
    def _create_widget(self, cam):
        # Create video widget for camera
        cam.loading_start = time.time()
        
        active_positions = [c.position for c in self.cameras if c.active]
        max_pos = max(active_positions) if active_positions else cam.position
        
        dims = self.config.layouts[max(max_pos, 0)][self.display_mode][0]
        x = round(dims[0] * self.container.width())
        y = round(dims[1] * self.container.height())
        w = round(dims[2] * self.container.width())
        h = round(dims[3] * self.container.height())
        
        use_camera = self.zed_available and self.use_overlay
        pipeline = f"zedxonesrc camera-id={self.config.ids[cam.index]} ! queue ! videoconvert ! queue ! {self.video_sink}" if use_camera else ""
        
        try:
            widget = VideoWidget(
                pipeline, 
                self.config.names[cam.index],
                str(self.config.ids[cam.index]),
                use_camera,
                self.container,
                self.config.ratios[cam.index][0],
                self.config.ratios[cam.index][1]
            )
            widget.setGeometry(x, y, w, h)
            widget.show()
            
            # Loading animation
            loading = LoadingAnimation(widget)
            loading.setGeometry(0, 0, w, h)
            loading.show()
            loading.raise_()
            loading.start(w // 2, h // 2, min(200, max(40, w - 40)), 20)
            
            cam.loading_animation = loading
            
            # Progress updates
            QTimer.singleShot(500, lambda: loading.update_progress(0.5) if loading else None)
            QTimer.singleShot(1000, lambda: loading.update_progress(0.6) if loading else None)
            
            def on_ready():
                print(f"Camera {cam.position} ready ({time.time() - cam.loading_start:.2f}s)")
                if cam.loading_animation:
                    cam.loading_animation.complete_animation()
                    cam.loading_animation = None
            
            if use_camera:
                widget.pipeline_ready.connect(on_ready)
            else:
                QTimer.singleShot(1500, on_ready)
            
            QApplication.processEvents()
            widget.start()
            cam.widget = widget
            
        except Exception as e:
            self.get_logger().error(f"Widget creation failed: {e}")
            placeholder = QWidget(self.container)
            placeholder.setGeometry(x, y, w, h)
            placeholder.setStyleSheet("background-color: #1a1a1a; border: 2px solid white;")
            placeholder.show()
            cam.widget = placeholder
    
    def _remove_widget(self, cam):
        # Remove widget from camera
        if cam.widget:
            self.anim_manager.stop(cam.widget)
            if hasattr(cam.widget, 'stop'):
                cam.widget.stop()
            cam.widget.hide()
            cam.widget.deleteLater()
            cam.widget = None
    
    def _update_layout(self):
        # Update all camera positions based on layout
        active_positions = [c.position for c in self.cameras if c.active]
        if not active_positions:
            return
        
        max_pos = max(active_positions)
        
        for i, cam in enumerate(self.cameras):
            if not cam.widget:
                continue
            
            layouts = self.config.layouts[i][self.display_mode]
            dims = layouts[max(0, min(max_pos + 1 - i, len(layouts) - 1))]
            
            x = round(dims[0] * self.container.width())
            y = round(dims[1] * self.container.height())
            w = round(dims[2] * self.container.width())
            h = round(dims[3] * self.container.height())
            
            self.anim_manager.tween(cam.widget, x, y, w, h)
        
        self._update_borders()
    
    def _update_borders(self):
        # Update border selection indicators
        for cam in self.cameras:
            if cam.widget and hasattr(cam.widget, 'set_selected'):
                cam.widget.set_selected(cam.position == self.current)
    
    def _cleanup_orphans(self):
        # Remove orphaned widgets
        if not self.container:
            return
        
        valid = {id(cam.widget) for cam in self.cameras if cam.widget}
        for child in self.container.children():
            if isinstance(child, QWidget) and id(child) not in valid:
                self.anim_manager.stop(child)
                child.hide()
                child.deleteLater()
    
    def _print_status(self):
        # Print current camera status
        print(f"\nCurrent: {self.current}")
        print(f"{'Pos':>3} | {'Active':>6} | {'Index':>5} | {'ID':>9} | {'Geometry':>20}")
        print(f"{'-' * 4}+{'-' * 8}+{'-' * 7}+{'-' * 11}+{'-' * 26}")
        for cam in self.cameras:
            if cam.widget:
                g = cam.widget.geometry()
                geom = f"{g.x():>4},{g.y():>4},{g.width():>4},{g.height():>4}"
            else:
                geom = "-"
            
            active = "\033[92mTrue  \033[0m" if cam.active else "\033[91mFalse \033[0m"
            cam_id = self.config.ids[cam.index] if 0 <= cam.index < len(self.config.ids) else -1
            print(f"{cam.position:>3} | {active} | {cam.index:>5} | {cam_id:>9} | {geom:>20}")

# ------------------------ MAIN ------------------------
def main():
    rclpy.init()
    node = CameraNode()
    
    app = QApplication([])
    
    # Install key filter
    key_filter = KeyEventFilter(node)
    app.installEventFilter(key_filter)
    
    # Setup GUI
    node.setup_gui()
    node.container.show()
    
    # ROS2 spinner
    timer = QTimer()
    timer.timeout.connect(lambda: rclpy.spin_once(node, timeout_sec=0))
    timer.start(30)
    
    app.exec()
    
    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()
