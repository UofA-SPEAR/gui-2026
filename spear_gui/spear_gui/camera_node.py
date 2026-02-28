import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo, GLib
import sys
import rclpy
from rclpy.node import Node
from PySide6.QtWidgets import QApplication, QWidget, QLabel
from PySide6.QtCore import QThread, Signal, QTimer, QVariantAnimation, QEasingCurve, Qt, QObject, QEvent, QElapsedTimer
from PySide6.QtGui import QColor, QPainter, QPen, QFontDatabase
from std_msgs.msg import String
from collections import deque
from PySide6.QtCore import qInstallMessageHandler

def _qt_message_handler(mode, context, message):
    if 'Painter not active' in message or 'painter' in message.lower() and 'not active' in message.lower():
        return  # suppress noisy painter warnings from overlay
    print(message)

qInstallMessageHandler(_qt_message_handler)

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
            elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
                msg = String()
                msg.data = '\r'
                self.node.key_pub.publish(msg)
                print(f"[KeyEventFilter] Published key: Enter")
            return True
        return False

# ------------------------ GStreamer ------------------------
class GStreamerThread(QThread):
    finished = Signal()
    error_occured = Signal(str)
    video_loaded = Signal()  # emitted once when first frame is ready

    def __init__(self, pipeline_str, window_id=None, parent=None):
        super().__init__(parent)
        self.pipeline_str = pipeline_str
        self.window_id = window_id
        self.pipeline = None
        self.bus = None
        self.loop = GLib.MainLoop()
        self._loaded = False

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
        elif mtype == Gst.MessageType.ASYNC_DONE and not self._loaded:
            self._loaded = True
            self.video_loaded.emit()

        return True


# ------------------------ Loading Overlay ------------------------

from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Tween:
    tx: float; ty: float; tw: float; th: float # Tween Geometry (0.0 - 1.0)
    tween_start: float              # seconds
    tween_dur:   float              # seconds
    phase:       str                # 'create' or 'loaded'
    ease:        object = QEasingCurve.OutQuint
    color:       object = None      # QColor to lerp to (optional)

@dataclass
class RectDef:
    ix: float; iy: float; iw: float; ih: float 
    color: object = None
    tweens: List[Tween] = field(default_factory=list)

RECT_DEFS = [
    RectDef(ix=0.0, iy=0.0, iw=1.0, ih=1.0, color=QColor(20, 20, 20), tweens=[
        Tween(tx=0.0, ty=-1.0, tw=1.0, th=1.0,
              tween_start=0.0, tween_dur=0.45,
              phase='loaded', ease=QEasingCurve.InOutQuint),
    ]),

    RectDef(ix=0.0, iy=0.92, iw=1.0, ih=0.04, color=QColor(50, 50, 50), tweens=[
        Tween(tx=0.0, ty=-1.0, tw=1.0, th=0.04,
              tween_start=0.05, tween_dur=0.4,
              phase='loaded', ease=QEasingCurve.InOutQuint),
    ]),

    RectDef(ix=0.0, iy=0.92, iw=0.0, ih=0.04, color=QColor(180, 180, 180), tweens=[
        Tween(tx=0.0, ty=0.92, tw=1.0, th=0.04,
              tween_start=0.0, tween_dur=4.0,
              phase='create', ease=QEasingCurve.Linear),
        Tween(tx=0.0, ty=0.92, tw=1.0, th=0.04,
              tween_start=0.0, tween_dur=0.15,
              phase='loaded', ease=QEasingCurve.OutQuint,
              color=QColor(220, 220, 220)),
        Tween(tx=0.0, ty=-1.0, tw=1.0, th=0.04,
              tween_start=0.05, tween_dur=0.4,
              phase='loaded', ease=QEasingCurve.InOutQuint),
    ]),
]

def _lerp_color(a: QColor, b: QColor, t: float) -> QColor:
    return QColor(
        int(a.red()   + (b.red()   - a.red())   * t),
        int(a.green() + (b.green() - a.green()) * t),
        int(a.blue()  + (b.blue()  - a.blue())  * t),
        int(a.alpha() + (b.alpha() - a.alpha()) * t),
    )

class LoadingRect:
    """Tracks one rectangle across all its tweens in sequence."""
    def __init__(self, defn: RectDef):
        self.defn   = defn
        self.cur_x  = defn.ix
        self.cur_y  = defn.iy
        self.cur_w  = defn.iw
        self.cur_h  = defn.ih
        self.cur_color = QColor(defn.color)
        self._tween_idx     = 0
        self._tween_start_x = defn.ix
        self._tween_start_y = defn.iy
        self._tween_start_w = defn.iw
        self._tween_start_h = defn.ih
        self._tween_start_color = QColor(self.cur_color)
        self.hidden = False

    @property
    def _current_tween(self):
        t = self.defn.tweens
        return t[self._tween_idx] if self._tween_idx < len(t) else None

    def update(self, create_elapsed, loaded_elapsed):
        if self.hidden:
            return
        while True:
            tween = self._current_tween
            if tween is None:
                self.hidden = True
                return

            elapsed = create_elapsed if tween.phase == 'create' else loaded_elapsed
            if elapsed is None:
                return  # phase not started yet

            local = elapsed - tween.tween_start
            if local < 0:
                return  # not started yet

            t = min(1.0, local / tween.tween_dur) if tween.tween_dur > 0 else 1.0
            v = QEasingCurve(tween.ease).valueForProgress(t)

            self.cur_x = self._tween_start_x + (tween.tx - self._tween_start_x) * v
            self.cur_y = self._tween_start_y + (tween.ty - self._tween_start_y) * v
            self.cur_w = self._tween_start_w + (tween.tw - self._tween_start_w) * v
            self.cur_h = self._tween_start_h + (tween.th - self._tween_start_h) * v

            if tween.color is not None:
                self.cur_color = _lerp_color(self._tween_start_color, tween.color, v)

            if t < 1.0:
                return

            # Snap and advance to next tween
            self.cur_x = tween.tx; self.cur_y = tween.ty
            self.cur_w = tween.tw; self.cur_h = tween.th
            if tween.color is not None:
                self.cur_color = QColor(tween.color)
            self._tween_start_x = tween.tx; self._tween_start_y = tween.ty
            self._tween_start_w = tween.tw; self._tween_start_h = tween.th
            self._tween_start_color = QColor(self.cur_color)
            self._tween_idx += 1

    def to_rect(self, w: int, h: int):
        return (int(self.cur_x * w), int(self.cur_y * h),
                int(self.cur_w * w), int(self.cur_h * h))


class LoadingOverlay(QWidget):
    """
    Top-level frameless window that sits above the video surface.
    'create' phase: timer from widget creation, freezes when video loads.
    'loaded' phase: timer from first video frame.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        self._create_timer  = None
        self._create_frozen = None
        self._loaded_timer  = None
        self._rects = [LoadingRect(d) for d in RECT_DEFS]

        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(16)
        self._tick_timer.timeout.connect(self._tick)

    def start(self):
        self._create_timer = QElapsedTimer()
        self._create_timer.start()
        self.show()
        self._tick_timer.start()

    def notify_loaded(self):
        if self._loaded_timer is not None:
            return
        QTimer.singleShot(50, self._do_notify_loaded)

    def _do_notify_loaded(self):
        if self._loaded_timer is not None:
            return
        if self._create_timer is not None:
            self._create_frozen = self._create_timer.elapsed() / 1000.0
        # Force-complete any create-phase tween that is currently in progress
        # so the rect snaps to its end position and the loaded tweens can start
        for rect in self._rects:
            if rect.hidden:
                continue
            tween = rect._current_tween
            if tween is not None and tween.phase == 'create':
                rect.cur_x = tween.tx; rect.cur_y = tween.ty
                rect.cur_w = tween.tw; rect.cur_h = tween.th
                if tween.color is not None:
                    rect.cur_color = QColor(tween.color)
                rect._tween_start_x = tween.tx; rect._tween_start_y = tween.ty
                rect._tween_start_w = tween.tw; rect._tween_start_h = tween.th
                rect._tween_start_color = QColor(rect.cur_color)
                rect._tween_idx += 1
        self._loaded_timer = QElapsedTimer()
        self._loaded_timer.start()

    def _elapsed(self):
        if self._create_frozen is not None:
            ce = self._create_frozen
        elif self._create_timer is not None:
            ce = self._create_timer.elapsed() / 1000.0
        else:
            ce = None
        le = self._loaded_timer.elapsed() / 1000.0 if self._loaded_timer else None
        return ce, le

    def _tick(self):
        ce, le = self._elapsed()
        for r in self._rects:
            r.update(ce, le)
        if all(r.hidden for r in self._rects):
            self._cleanup()
            return
        self.update()

    def _cleanup(self):
        self._tick_timer.stop()
        self.hide()
        try:
            app = QApplication.instance()
            if app:
                for w in app.allWidgets():
                    if getattr(w, 'loading_overlay', None) is self:
                        w.loading_overlay = None
                        break
        except Exception:
            pass
        self.deleteLater()

    def paintEvent(self, event):
        painter = QPainter(self)
        if not painter.isActive():
            return
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.transparent)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.setPen(Qt.NoPen)
        w, h = self.width(), self.height()
        for rect in self._rects:
            if not rect.hidden:
                x, y, rw, rh = rect.to_rect(w, h)
                painter.fillRect(x, y, rw, rh, rect.cur_color)
        painter.end()


class GStreamerVideoWidget(QWidget):
    clicked = Signal()

    def __init__(self, pipeline_str, camera_name="", camera_serial="", use_overlay=True,
                 camera_width=1920, camera_height=1080, parent=None):
        super().__init__(parent)

        self.pipeline_str = pipeline_str
        self.use_overlay = use_overlay
        self.thread = None
        self.placeholder_label = None
        self.video_resize_enabled = True
        self.camera_width = camera_width
        self.camera_height = camera_height

        self.setStyleSheet("background-color: black;")
        self.border_color = QColor("red")
        self.border_width = 3

        self.setAttribute(Qt.WA_NativeWindow)

        self.video_surface = QWidget(self)
        self.video_surface.setAttribute(Qt.WA_NativeWindow)
        self.video_surface.setStyleSheet("background:black;")

        self.name_label = QLabel(camera_name, self)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet("""
            color: white;
            font-size: 14px;
            font-family: 'Oxanium SemiBold';
            background-color: rgba(0,0,0,150);
            padding: 2px;
        """)

        self.id_label = QLabel(f"SN: {camera_serial}", self)
        self.id_label.setAlignment(Qt.AlignCenter)
        self.id_label.setStyleSheet("""
            color: white;
            font-size: 10px;
            font-family: 'Oxanium';
            background-color: rgba(0,0,0,150);
            padding: 2px;
        """)

        self.stats_label = QLabel("", self)
        self.stats_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.stats_label.setStyleSheet("""
            color: white;
            font-size: 11px;
            font-family: 'Oxanium';
            background-color: rgba(0,0,0,150);
            padding: 3px;
        """)

        self.loading_overlay = None

        if not use_overlay:
            self.placeholder_label = QLabel(
                "No Camera\nDetected", self
            )
            self.placeholder_label.setAlignment(Qt.AlignCenter)
            self.placeholder_label.setStyleSheet("""
                color: white;
                font-size: 16px;
                font-family: 'Oxanium';
                background-color: #1a1a1a;
            """)

    def _compute_video_rect(self, widget_w, widget_h):
        cam_w = self.camera_width
        cam_h = self.camera_height

        scale_w = widget_w / cam_w
        scale_h = widget_h / cam_h

        # Use the larger scale so the video covers the widget entirely
        scale = max(scale_w, scale_h)

        render_w = int(cam_w * scale)
        render_h = int(cam_h * scale)

        x_offset = (widget_w - render_w) // 2
        y_offset = (widget_h - render_h) // 2

        return x_offset, y_offset, render_w, render_h

    def resizeEvent(self, event):
        super().resizeEvent(event)

        w, h = self.width(), self.height()
        bw = self.border_width
        inner_w = w - 2 * bw
        inner_h = h - 2 * bw

        x_off, y_off, render_w, render_h = self._compute_video_rect(inner_w, inner_h)
        self.video_surface.setGeometry(bw + x_off, bw + y_off, render_w, render_h)

        name_height = 20
        self.name_label.setGeometry(3, 3, w - 6, name_height)

        id_height = 15
        self.id_label.setGeometry(3, 3 + name_height, w - 6, id_height)

        stats_height = 52
        self.stats_label.setGeometry(3, h - stats_height - 3, 160, stats_height)
        self.stats_label.raise_()

        self.name_label.raise_()
        self.id_label.raise_()

        if self.placeholder_label:
            self.placeholder_label.setGeometry(0, 0, w, h)
            self.placeholder_label.raise_()

        self.update_video_render_rectangle(inner_w, inner_h)

    def apply_video_resize(self):
        if not self.video_resize_enabled:
            return
        bw = self.border_width
        inner_w = self.width() - 2 * bw
        inner_h = self.height() - 2 * bw
        x_off, y_off, render_w, render_h = self._compute_video_rect(inner_w, inner_h)
        self.video_surface.setGeometry(bw + x_off, bw + y_off, render_w, render_h)
        self.update_video_render_rectangle(inner_w, inner_h)

    def start(self):
        if not self.use_overlay:
            return

        self.show()
        QApplication.processEvents()

        self.thread = GStreamerThread(
            self.pipeline_str,
            self.video_surface.winId(),
            parent=self
        )

        self.thread.finished.connect(self.on_finished)
        self.thread.error_occured.connect(self.on_error)
        self.thread.video_loaded.connect(self._on_video_loaded)
        self.thread.start()

    def stop(self):
        if self.thread:
            self.thread.stop()
            self.thread.wait(1000)

    def update_video_render_rectangle(self, w, h):
        if not self.thread or not self.thread.pipeline:
            return

        _, _, render_w, render_h = self._compute_video_rect(w, h)

        sink = self.thread.pipeline.get_by_interface(GstVideo.VideoOverlay.__gtype__)
        if sink:
            try:
                sink.set_render_rectangle(0, 0, render_w, render_h)
                sink.expose()
            except Exception:
                pass

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def _on_video_loaded(self):
        if self.loading_overlay:
            self.loading_overlay.notify_loaded()

    def on_error(self, error_msg):
        print("GStreamer error:", error_msg)

    def on_finished(self):
        print("Pipeline finished.")

    def update_labels(self, camera_name, camera_serial):
        self.name_label.setText(camera_name)
        self.id_label.setText(f"SN: {camera_serial}")
    
    def update_stats(self, exposure, gain, gamma, pending=False):
        # Show a * prefix on each line when there are unapplied changes
        prefix = "* " if pending else ""
        self.stats_label.setText(
            f"{prefix}Exposure: {exposure} µs\n"
            f"{prefix}Gain: {gain}\n"
            f"{prefix}Gamma: {gamma}"
        )

    def set_border_color(self, color):
        self.border_color = QColor(color)
        self.update()
    
    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        pen = QPen(self.border_color)
        pen.setWidth(self.border_width)
        painter.setPen(pen)

        rect = self.rect().adjusted(
            self.border_width // 2,
            self.border_width // 2,
            -self.border_width // 2,
            -self.border_width // 2
        )

        painter.drawRect(rect)

    def apply_video_resize(self):
        if not self.video_resize_enabled:
            return
        bw = self.border_width
        self.update_video_render_rectangle(
            self.width() - 2 * bw,
            self.height() - 2 * bw
        )

class ResizableContainer(QWidget):
    resized = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resized.emit()

# ------------------------ Camera Node ------------------------

class CameraConfig:
    names = ["ZED X One #1", "ZED X One #2", "ZED X Mini #1", "Placeholder 4", "Placeholder 5", "Placeholder 6", "Placeholder 7", "Placeholder 8"]
    serials = [309256978, 305325257, 58896881, 0, 0, 0, 0, 0]
    default_resolutions = [4, 4, 6, 0, 0, 0, 0, 0]
    camera_ids = [0, 1, 0, 3, 4, 5, 6, 7]
    ratios = [[1920, 1080]] * 8
    layout = [
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
    ]

class Camera:
    def __init__(self, position, default_resolution):
        self.serial = None
        self.camera_id = 0
        self.index = -1
        self.position = position
        self.active = False
        self.widget = None
        self.pipeline = None
        self.source_type = None
        self.resolution = default_resolution
        self.exposure = 5000
        self.gain = 40
        self.gamma = 2
        # Pending (unapplied) settings — None means no pending change
        self.pending_exposure = None
        self.pending_gain = None
        self.pending_gamma = None

    def has_pending_changes(self):
        return any(v is not None for v in [self.pending_exposure, self.pending_gain, self.pending_gamma])

    def apply_pending(self):
        # Commit pending values to live values and clear pending state.
        if self.pending_exposure is not None:
            self.exposure = self.pending_exposure
            self.pending_exposure = None
        if self.pending_gain is not None:
            self.gain = self.pending_gain
            self.pending_gain = None
        if self.pending_gamma is not None:
            self.gamma = self.pending_gamma
            self.pending_gamma = None

    def discard_pending(self):
        self.pending_exposure = None
        self.pending_gain = None
        self.pending_gamma = None

    
class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')

        self.container = None
        self.command_queue = deque()
        self.processing_command = False

        self.config = CameraConfig()
        self.cameras = [Camera(i, self.config.default_resolutions[i]) for i in range(len(self.config.serials))]
        
        self.camera_current = 0
        self.focused_camera = None
        self.focus_mode = False
        self.switching_mode = False
        self.display_mode = 0

        self.always_remove_inactive_cams = True
        self.animations = {} 
        
        self.key_pub = self.create_publisher(String, "key", 10)
        self.key_subscription = self.create_subscription(
            String, 'key', self.key_listener, 10
        )

        self.zed_sources = {
            "zedxone": "zedxonesrc",
            "zed": "zedsrc",
        }

        self.available_zed_sources = {
            name: self.check_gstreamer_element(element)
            for name, element in self.zed_sources.items()
        }

        print(f"Checking available ZED GStreamer elements:")
        for name, element in self.zed_sources.items():
            status = "✓ Available" if self.available_zed_sources[name] else "✗ Not found"
            print(f"  {element}: {status}")

        if not any(self.available_zed_sources.values()):
            self.get_logger().warn(
                "\033[93mWarning: No ZED SDK cameras detected. Camera display is disabled.\033[0m"
            )

        self.video_sink = self.find_best_video_sink()
        print(f"Using video sink: {self.video_sink}")
        
        self.use_video_overlay = self.video_sink in ['ximagesink', 'xvimagesink', 'glimagesink']
        if not self.use_video_overlay:
            self.get_logger().warn("\033[93mWarning: Video overlay not available. Using placeholder mode.\033[0m")

        self.camera_info = {
            309256978: {"type": "ZED X One", "source": "zedxonesrc", "camera_id": 0,
                        "exposure": 10000, "gain": 30000, "gamma": 2},
            305325257: {"type": "ZED X One", "source": "zedxonesrc", "camera_id": 1,
                        "exposure": 10000, "gain": 30000, "gamma": 2},
            58896881:  {"type": "ZED X Mini", "source": "zedsrc",    "camera_id": 0,
                        "exposure": 50,   "gain": 30000, "gamma": 2},
        }

        print(f"\nConfigured cameras:")
        for serial, info in self.camera_info.items():
            print(f"  Serial {serial}: {info['type']} using {info['source']} (camera-id={info['camera_id']})")

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
        # Reposition any active overlays to match new global coords
        for cam in self.cameras:
            if cam.widget and hasattr(cam.widget, 'loading_overlay') and cam.widget.loading_overlay:
                try:
                    geom = cam.widget.geometry()
                    gp = self.container.mapToGlobal(self.container.rect().topLeft())
                    cam.widget.loading_overlay.setGeometry(
                        gp.x() + geom.x(), gp.y() + geom.y(),
                        geom.width(), geom.height()
                    )
                except RuntimeError:
                    cam.widget.loading_overlay = None

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
            case 'm':
                self.change_display(1)
            case 'n':
                self.change_display(-1)
            case 'f':
                self.toggle_focus()
            case 'r':
                self.toggle_switching_mode()
                print(f'Switch Mode: {self.switching_mode}')
            case key if key in ['0', '1', '2', '3', '4', '5', '6', '7']:
                if self.switching_mode:
                    self.switch_cameras(int(key))
                    self.switching_mode = False
                else:
                    print(f'Failed to swap with {key}')
            case 'o':  # increase exposure
                self.adjust_current_camera('exposure', +10000 if self.cameras[self.camera_current].source_type == 'zedxonesrc' else +30)
            case 'l':  # decrease exposure
                self.adjust_current_camera('exposure', -10000 if self.cameras[self.camera_current].source_type == 'zedxonesrc' else -30)
            case 'i':  # increase gain
                self.adjust_current_camera('gain', +5000)
            case 'k':  # decrease gain
                self.adjust_current_camera('gain', -5000)
            case 'u':  # increase gamma
                self.adjust_current_camera('gamma', +7)
            case 'j':  # decrease gamma
                self.adjust_current_camera('gamma', -7)
            case '\r':  # Enter — commit pending settings and restart camera
                self.apply_pending_settings()
        self.print_infomation()
        self.cleanup_orphaned_widgets()
        QTimer.singleShot(20, self.process_command_queue)

    # ------------------------ Camera Utilities ------------------------

    def get_available_index(self):
        used = {cam.index for cam in self.cameras if cam.index != -1}
        unused = [i for i in range(len(self.cameras)) if i not in used]
        return unused[0] if unused else None

    def adjust_current_camera(self, attr, delta):
        cam = self.cameras[self.camera_current]
        if not cam.active:
            return

        pending_attr = f"pending_{attr}"
        base = getattr(cam, pending_attr) if getattr(cam, pending_attr) is not None else getattr(cam, attr)
        new_val = max(0, base + delta)
        setattr(cam, pending_attr, new_val)

        print(f"  {attr} (pending) -> {new_val}  [press Enter to apply]")

        # Update stats label with pending marker
        if cam.widget and hasattr(cam.widget, 'update_stats'):
            disp_exposure = cam.pending_exposure if cam.pending_exposure is not None else cam.exposure
            disp_gain     = cam.pending_gain     if cam.pending_gain     is not None else cam.gain
            disp_gamma    = cam.pending_gamma    if cam.pending_gamma    is not None else cam.gamma
            cam.widget.update_stats(disp_exposure, disp_gain, disp_gamma, pending=True)

    def apply_pending_settings(self):
        cam = self.cameras[self.camera_current]
        if not cam.active:
            return
        if not cam.has_pending_changes():
            print("No pending changes to apply.")
            return

        print("Applying pending settings and restarting camera...")
        cam.apply_pending()

        geom = cam.widget.geometry()
        self.remove_widget(cam)
        self.create_camera_widget(cam)
        cam.widget.setGeometry(geom)

    # ------------------------ Activation / Deactivation ------------------------

    def activate_camera(self):
        inactive = [c for c in self.cameras if not c.active]

        if not inactive:
            print("No inactive camera slots.")
            return
        
        cam = next(cam for cam in self.cameras if not cam.active)
        cam.active = True
            
        active_indexes = {c.index for c in self.cameras if c.active and c is not cam}
        if cam.index in (-1, *active_indexes):
            cam.index = self.get_available_index()
        
        cam.serial = self.config.serials[cam.index]
        
        if cam.serial in self.camera_info:
            info = self.camera_info[cam.serial]
            cam.source_type = info["source"]
            cam.camera_id = info["camera_id"]
            cam.source_type = info["source"]
            cam.camera_id   = info["camera_id"]
            cam.exposure    = info.get("exposure")
            cam.gain        = info.get("gain")
            cam.gamma       = info.get("gamma")
            
            source_available = False
            for name, element in self.zed_sources.items():
                if element == cam.source_type and self.available_zed_sources.get(name):
                    source_available = True
                    break
            
            if source_available:
                print(f"Activated {info['type']} (Serial: {cam.serial}, Source: {cam.source_type}, Camera ID: {cam.camera_id})")
            else:
                print(f"ERROR: {info['type']} requires {cam.source_type} which is not available!")
                cam.source_type = None
                cam.camera_id = 0
        else:
            cam.camera_id = self.config.camera_ids[cam.index]
            if self.available_zed_sources.get("zedxone"):
                cam.source_type = "zedxonesrc"
                print(f"Warning: Using zedxonesrc for unknown camera serial {cam.serial}")
            else:
                cam.source_type = None
                print(f"Warning: No ZED source available for camera {cam.serial}")
        
        self.camera_current = cam.position

        print(f'Current Camera: {self.camera_current}')
        self.create_camera_widget(cam)
        self.set_camera_positions()

    def deactivate_camera(self):
        if self.camera_current is None:
            print("No camera currently selected.")
            return
            
        cam = self.cameras[self.camera_current]
        if not cam.active:
            print(f"Camera {self.camera_current} is not active.")
            return
        
        cam.discard_pending()

        original_pos = cam.position
        cam.active = False
        active_positions = [c.position for c in self.cameras if c.active]

        if not active_positions:
            for c in self.cameras:
                self.remove_widget(c)
            self.camera_current = None
            QApplication.processEvents()
            self.cleanup_orphaned_widgets()
            self.set_camera_positions()
            return
        
        max_pos = max(active_positions)

        for c in self.cameras:
            if (not c.active) and c.position > max_pos:
                self.remove_widget(c)
        
        if self.always_remove_inactive_cams:
            self.remove_widget(cam)
            found_inactive = True
            while found_inactive:
                found_inactive = False
                for i in range(len(self.cameras)):
                    if not self.cameras[i].active and self.cameras[i].position < max_pos:
                        found_inactive = True
                        self.select_camera(i, True)
                        self.switch_cameras(i + 1, True)
        elif cam.position > max_pos:
            self.remove_widget(cam)
        else:
            if cam.widget:
                self.stop_animation_for_widget(cam.widget)
                cam.widget.stop()

                if not hasattr(cam.widget, 'placeholder_label') or cam.widget.placeholder_label is None:
                    cam.widget.placeholder_label = QLabel("Inactive", cam.widget)
                    cam.widget.placeholder_label.setAlignment(Qt.AlignCenter)
                    cam.widget.placeholder_label.setStyleSheet("color: red; font-size: 16px; font-family: Oxanium; background-color: #1a1a1a;")
                    cam.widget.placeholder_label.setGeometry(0, 0, cam.widget.width(), cam.widget.height())
                else:
                    cam.widget.placeholder_label.setText("Inactive")

                cam.widget.placeholder_label.show()

        candidates = [p for p in active_positions if p < self.camera_current]
        self.camera_current = max(candidates) if candidates else self.camera_current
        if self.always_remove_inactive_cams:
            self.select_camera(original_pos, True)
            if not self.cameras[self.camera_current].active:
                self.select_camera(max(candidates), True)

        QApplication.processEvents()
        self.cleanup_orphaned_widgets()
        self.set_camera_positions()

    # ------------------------ Selection ------------------------

    def select_camera(self, index, bypass_inactive=False):
        if not bypass_inactive and not self.cameras[index].active:
            print(f"Camera {index} not active")
            return
        if bypass_inactive:
            index = next((c.position for c in self.cameras if c.position == index), 0)
        self.camera_current = index
        print(f"Current Index: {index}")
        self.update_camera_borders()

    def select_next_camera(self, direction):
        if self.camera_current is None:
            print("No camera currently selected.")
            return
        active_positions = [c.position for c in self.cameras if c.active]
        if not active_positions:
            print("No active cameras.")
            return
        max_pos = max(active_positions) if active_positions else 0
        self.camera_current = (self.camera_current + direction) % (max_pos + 1)
        self.update_camera_borders()

    def change_display(self, direction):
        self.display_mode = (self.display_mode + direction) % len(self.config.layout[0])
        self.set_camera_positions()

    def toggle_focus(self):
        if self.camera_current is None:
            return
        cam = self.cameras[self.camera_current]
        if not cam.active or cam.widget:
            pass
        if not self.focus_mode:
            self.focus_mode = True
            self.focused_camera = self.camera_current

            cam.widget.raise_()
            cam.widget.name_label.raise_()
            cam.widget.id_label.raise_()
            self.stop_animation_for_widget(cam.widget)
            self.tween_position_and_size(cam.widget, 0, 0, self.container.width(), self.container.height(), duration = 500)
        else:
            self.focus_mode = False
            self.focused_camera = None
            self.set_camera_positions()
    
    def toggle_switching_mode(self):
        self.switching_mode = not self.switching_mode
    
    def switch_cameras(self, target_pos, bypass_inactive = False):
        cam_current = next((c for c in self.cameras if c.position == self.camera_current), None)
        cam_target = next((c for c in self.cameras if c.position == target_pos), None)
        active_positions = [c.position for c in self.cameras if c.active]

        if not bypass_inactive and (not cam_current or not cam_target or not active_positions or max(active_positions) < cam_target.position):
            reason = ''
            if not cam_current:
                reason += 'No current cam. '
            if not cam_target:
                reason += 'No target cam. '
            if not active_positions:
                reason += 'No active positions. '
            if cam_target and max(active_positions) < cam_target.position:
                reason += 'Target cam is out of max active positions.'
            
            print(f'Failed to switch due to the following reason(s): {reason}')

            return
        
        print(f"Switched cameras {self.camera_current} <-> {target_pos}")
        
        attrs_to_swap = ['index', 'active']
        for attr in attrs_to_swap:
            temp = getattr(cam_current, attr)
            setattr(cam_current, attr, getattr(cam_target, attr))
            setattr(cam_target, attr, temp)
        
        cam_current.widget, cam_target.widget = cam_target.widget, cam_current.widget
        
        if cam_current.widget and hasattr(cam_current.widget, 'update_labels'):
            cam_current.widget.update_labels(
                self.config.names[cam_current.index] if cam_current.index >= 0 else "Unknown",
                str(self.config.serials[cam_current.index]) if cam_current.index >= 0 else "N/A"
            )
        
        if cam_target.widget and hasattr(cam_target.widget, 'update_labels'):
            cam_target.widget.update_labels(
                self.config.names[cam_target.index] if cam_target.index >= 0 else "Unknown",
                str(self.config.serials[cam_target.index]) if cam_target.index >= 0 else "N/A"
            )
        
        self.camera_current = self.camera_current
        self.switching_mode = False
        
        self.set_camera_positions()

    # ------------------------ Move Index ------------------------

    def move_index(self, direction):
        if self.camera_current is None:
            print("No camera currently selected.")
            return

        cam = self.cameras[self.camera_current]
        if not cam.active:
            print(f"Camera {self.camera_current} is not active.")
            return

        start_index = cam.index
        current_index = start_index
        
        for _ in range(len(self.cameras)):
            current_index = (current_index + direction) % len(self.cameras)
            active_indexes = [c.index for c in list(filter(lambda c: c.active, self.cameras))]
            if current_index not in active_indexes or current_index == start_index:
                cam.index = current_index
                cam.serial = self.config.serials[cam.index]
                
                if cam.serial in self.camera_info:
                    info = self.camera_info[cam.serial]
                    cam.source_type = info["source"]
                    cam.camera_id = info["camera_id"]
                else:
                    cam.camera_id = self.config.camera_ids[cam.index]
                break

        if cam.widget and hasattr(cam.widget, 'update_labels'):
            cam.widget.update_labels(
                self.config.names[cam.index],
                str(self.config.serials[cam.index])
            )

    # ------------------------ Camera Widgets ------------------------

    def create_camera_widget(self, cam):
        active_positions = [c.position for c in self.cameras if c.active] or [cam.position]
        max_pos = max(active_positions)

        dims = self.config.layout[max(max_pos, 0)][self.display_mode][0]
        x = round(dims[0] * self.container.width())
        y = round(dims[1] * self.container.height())
        w = round(dims[2] * self.container.width())
        h = round(dims[3] * self.container.height())

        use_camera = self.use_video_overlay and cam.source_type is not None

        cam_ratio = self.config.ratios[cam.index] if cam.index >= 0 else [1920, 1080]
        cam_w, cam_h = cam_ratio[0], cam_ratio[1]

        if use_camera:
            src = cam.source_type
            cid = cam.camera_id
            exp = cam.exposure
            gain = cam.gain
            gamma = cam.gamma

            if src == "zedxonesrc":
                cam_props = (
                    f"camera-id={cid} "
                    f"ctrl-auto-exposure=false "
                    f"ctrl-auto-exposure-range-min={exp} "
                    f"ctrl-auto-exposure-range-max={exp} "
                    f"ctrl-exposure-time={exp} "
                    f"ctrl-analog-gain={gain} "
                    f"ctrl-gamma={gamma}"
                )
            else:
                cam_props = f"camera-id={cid} aec-agc=false exposure={exp} gain={gain}"

            pipeline = (
                f"{src} {cam_props} "
                f"! queue ! videoconvert ! videoscale "
                f"! {self.video_sink} force-aspect-ratio=false"
            )
        else:
            pipeline = None

        try:
            camera_feed_widget = GStreamerVideoWidget(
                pipeline if pipeline else "", 
                camera_name=self.config.names[cam.index],
                camera_serial=str(cam.serial),
                use_overlay=use_camera,
                camera_width=cam_w,
                camera_height=cam_h,
                parent=self.container
            )
            camera_feed_widget.setGeometry(x, y, w, h)
            camera_feed_widget.show()
            
            camera_feed_widget.name_label.show()
            camera_feed_widget.id_label.show()
            camera_feed_widget.name_label.raise_()
            camera_feed_widget.id_label.raise_()
            
            if use_camera:
                QApplication.processEvents()
                camera_feed_widget.start()

            camera_feed_widget.clicked.connect(
                lambda pos=cam.position: self.select_camera(pos)
            )

            if use_camera:
                overlay = LoadingOverlay(None)
                overlay.setWindowFlags(
                    Qt.FramelessWindowHint |
                    Qt.WindowStaysOnTopHint |
                    Qt.Tool
                )
                overlay.setStyleSheet("background: transparent;")
                global_pos = self.container.mapToGlobal(
                    self.container.rect().topLeft()
                )
                overlay.setGeometry(
                    global_pos.x() + x,
                    global_pos.y() + y,
                    w, h
                )
                overlay.show()
                camera_feed_widget.loading_overlay = overlay
                overlay.start()

            cam.widget = camera_feed_widget
            if use_camera and hasattr(camera_feed_widget, 'update_stats'):
                camera_feed_widget.update_stats(cam.exposure, cam.gain, cam.gamma)
        except Exception as e:
            self.get_logger().error(f"Failed to create camera widget: {e}")
            placeholder = QWidget(self.container)
            placeholder.setGeometry(x, y, w, h)
            placeholder.setStyleSheet("background-color: #1a1a1a; border: 3px solid red;")
            placeholder.show()
            cam.widget = placeholder

    def set_camera_positions(self):
        active_positions = [c.position for c in self.cameras if c.active]
        if not active_positions:
            return
        max_pos = max(active_positions)

        for cam in self.cameras:
            if not cam.active and cam.widget:
                self.stop_animation_for_widget(cam.widget)
                continue

        for i, cam in enumerate(self.cameras):
            if not cam.widget:
                continue

            layouts = self.config.layout[i][self.display_mode]
            dims = layouts[max(0, min(max_pos + 1 - i, len(layouts) - 1))]
            
            x = round(dims[0] * self.container.width())
            y = round(dims[1] * self.container.height())
            w = round(dims[2] * self.container.width())
            h = round(dims[3] * self.container.height())

            self.tween_position_and_size(cam.widget, x, y, w, h, duration = 500)

        self.update_camera_borders()

    def cleanup_orphaned_widgets(self):
        if not self.container:
            return
        
        valid_widgets = {id(cam.widget) for cam in self.cameras if cam.widget}
        for child in self.container.children():
            if not isinstance(child, QWidget):
                continue
            child_id = id(child)
            if child_id not in valid_widgets and child_id != id(self.container):
                self.stop_animation_for_widget(child)
                child.hide()
                child.deleteLater()

    def update_camera_borders(self):
        for cam in self.cameras:
            if not cam.widget:
                continue
            color = "blue" if cam.position == self.camera_current else "red"
            if hasattr(cam.widget, 'set_border_color'):
                cam.widget.set_border_color(color)

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

    def remove_widget(self, cam):
        if cam.widget:
            if hasattr(cam.widget, 'loading_overlay') and cam.widget.loading_overlay:
                try:
                    cam.widget.loading_overlay.hide()
                    cam.widget.loading_overlay.deleteLater()
                except RuntimeError:
                    pass
                cam.widget.loading_overlay = None
            if hasattr(cam.widget, 'stop'):
                cam.widget.stop()
            cam.widget.hide()
            cam.widget.deleteLater()
            cam.widget = None

    def tween_position_and_size(self, widget, end_x, end_y, end_w, end_h, ease_style=QEasingCurve.OutQuint, duration=500):
        if not widget or not widget.parent():
            return

        cam = next((cam for cam in self.cameras if cam.widget == widget), None)
        if not cam:
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
            try:
                if hasattr(widget, 'loading_overlay') and widget.loading_overlay:
                    if widget.parent():
                        gp = widget.parent().mapToGlobal(widget.parent().rect().topLeft())
                        widget.loading_overlay.setGeometry(
                            gp.x() + new_x, gp.y() + new_y, new_w, new_h
                        )
            except RuntimeError:
                if hasattr(widget, 'loading_overlay'):
                    widget.loading_overlay = None

        animation.valueChanged.connect(update_geometry)
        animation.start()
        self.animations[id(widget)] = animation

        if hasattr(widget, "video_resize_enabled"):
            widget.video_resize_enabled = False

        def finish_animation():
            if hasattr(widget, "video_resize_enabled"):
                widget.video_resize_enabled = True
                widget.apply_video_resize()
            try:
                if hasattr(widget, 'loading_overlay') and widget.loading_overlay:
                    if widget.parent():
                        gp = widget.parent().mapToGlobal(widget.parent().rect().topLeft())
                        widget.loading_overlay.setGeometry(
                            gp.x() + end_x, gp.y() + end_y, end_w, end_h
                        )
            except RuntimeError:
                if hasattr(widget, 'loading_overlay'):
                    widget.loading_overlay = None

        animation.finished.connect(finish_animation)

    # ------------------------ Print Information ------------------------

    def print_infomation(self):
        print(f"Current Selected: {self.camera_current}")
        print(f"{'Pos':>3} | {'Active':>6} | {'Index':>5} | {'Serial':>9} | {'CamID':>5} | {'X':>4} | {'Y':>4} | {'W':>4} | {'H':>4}")
        print("-" * 75)
        for cam in self.cameras:
            widget = cam.widget
            if widget:
                geom = widget.geometry()
                x, y, w, h = geom.x(), geom.y(), geom.width(), geom.height()
            else:
                x = y = w = h = 0
            active_str = "\033[92mTrue  \033[0m" if cam.active else "\033[91mFalse \033[0m"
            serial_str = str(cam.serial) if cam.serial else "N/A"
            print(f"{cam.position:>3} | {active_str} | {cam.index:>5} | {serial_str:>9} | {cam.camera_id:>5} | {x:>4} | {y:>4} | {w:>4} | {h:>4}")


def main():
    rclpy.init()
    node = CameraNode()

    app = QApplication([])

    import os
    font_path = os.path.join(os.path.dirname(__file__), "Oxanium-VariableFont.ttf")
    QFontDatabase.addApplicationFont(font_path)

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