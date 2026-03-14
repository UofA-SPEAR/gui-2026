import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo, GLib
import sys
import rclpy
from rclpy.node import Node
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QSlider, QPushButton, QGraphicsDropShadowEffect
from PySide6.QtCore import QThread, Signal, QTimer, QVariantAnimation, QEasingCurve, Qt, QObject, QEvent, QElapsedTimer
from PySide6.QtGui import QColor, QPainter, QFontDatabase, QFont, QPolygonF
from PySide6.QtCore import QPointF
from std_msgs.msg import String
from collections import deque
from PySide6.QtCore import qInstallMessageHandler
from typing import Optional
from spear_gui.gui_vars import CAMERA_LAYOUT
from spear_gui.overlay_system import LoadingOverlay, SelectionOverlay

def _qt_message_handler(mode, context, message):
    if 'Painter not active' in message or 'painter' in message.lower() and 'not active' in message.lower():
        return
    print(message)

qInstallMessageHandler(_qt_message_handler)

# ──────────────────────── Key Event Filter ────────────────────────
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

# ──────────────────────── GStreamer ────────────────────────
class GStreamerThread(QThread):
    finished = Signal()
    error_occured = Signal(str)
    video_loaded = Signal()

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

# ──────────────────────── Camera Settings Panel ────────────────────────

RESOLUTION_OPTIONS = {
    "zedxonesrc": [
        ("4K  — 3840×2160",   3840, 2160, 0),
        ("2.2K — 2208×1242",  2208, 1242, 1),
        ("1080p — 1920×1080", 1920, 1080, 2),
        ("720p  — 1280×720",  1280,  720, 3),
        ("WVGA  — 752×480",    752,  480, 4),
    ],
    "zedsrc": [
        ("2.2K — 2208×1242",  2208, 1242, 0),
        ("1080p — 1920×1080", 1920, 1080, 1),
        ("720p  — 1280×720",  1280,  720, 2),
        ("WVGA  — 752×480",    752,  480, 3),
        ("VGA   — 672×376",    672,  376, 4),
        ("300FPS — 384×192",   384,  192, 5),
        ("120FPS — 640×360",   640,  360, 6),
    ],
    "default": [
        ("1080p — 1920×1080", 1920, 1080, 0),
        ("720p  — 1280×720",  1280,  720, 1),
    ],
}

_SRC_MODE_PROP = {
    "zedxonesrc": None,
    "zedsrc":     None,
}

class Slider(QSlider):
    """QSlider with a rotated-square (diamond) handle drawn via paintEvent."""
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        
        self.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 2px;
                background: rgba(255,255,255,35);
                border-radius: 1px;
            }
            QSlider::handle:horizontal {
                background: transparent;
                border: none;
                width: 16px;
                height: 16px;
                margin: -7px 0;
                image: none;
            }
            QSlider::sub-page:horizontal {
                background: #ffffff;
                border-radius: 1px;
            }""")

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        if not painter.isActive():
            return
        painter.setRenderHint(QPainter.Antialiasing)

        opt_w = self.width()
        opt_h = self.height()
        rng = self.maximum() - self.minimum()
        if rng == 0:
            ratio = 0.0
        else:
            ratio = (self.value() - self.minimum()) / rng

        handle_size = 10
        groove_margin = handle_size
        usable_w = opt_w - 2 * groove_margin
        cx = groove_margin + ratio * usable_w
        cy = opt_h / 2

        diamond = QPolygonF([
            QPointF(cx,                cy - handle_size),
            QPointF(cx + handle_size,  cy),
            QPointF(cx,                cy + handle_size),
            QPointF(cx - handle_size,  cy),
        ])

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255))
        painter.drawPolygon(diamond)
        painter.end()


class ResolutionSelector(QWidget):
    changed = Signal(int)

    def __init__(self, options, current_idx, parent=None):
        super().__init__(parent)
        self._options = options
        self._selected = current_idx
        self._btns = []
        self.setStyleSheet("background: transparent;")

        btn_h = 26
        self.setFixedHeight(btn_h)

        total = len(options)
        self._total = total
        for i, (label, *_) in enumerate(options):
            btn = QPushButton(label, self)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("sel_idx", i)
            btn.clicked.connect(lambda checked=False, idx=i: self._select(idx))
            self._btns.append(btn)

        self._refresh_styles()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        h = self.height()
        n = len(self._btns)
        btn_w = w // n
        for i, btn in enumerate(self._btns):
            btn.setGeometry(i * btn_w, 0, btn_w - 2, h)

    def _select(self, idx):
        self._selected = idx
        self._refresh_styles()
        self.changed.emit(idx)

    def selected_index(self):
        return self._selected

    def _refresh_styles(self):
        for i, btn in enumerate(self._btns):
            if i == self._selected:
                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(255,255,255,220);
                        color: #0a0a0e;
                        border: none;
                        border-radius: 2px;
                        font-family: 'Oxanium SemiBold';
                        font-size: 9px;
                        letter-spacing: 1px;
                        padding: 0 4px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(255,255,255,10);
                        color: rgba(255,255,255,140);
                        border: 1px solid rgba(255,255,255,20);
                        border-radius: 2px;
                        font-family: 'Oxanium';
                        font-size: 9px;
                        letter-spacing: 1px;
                        padding: 0 4px;
                    }
                    QPushButton:hover {
                        background: rgba(255,255,255,20);
                        color: rgba(255,255,255,220);
                    }
                """)


class CameraSettingsPanel(QWidget):
    applied   = Signal(int, int, int, int, int)  # exposure, gain, gamma, res_w, res_h
    cancelled = Signal()

    RANGES = {
        "zedxonesrc": {
            "exposure": (5000,  60000, 1000),
            "gain":     (1000,  5000,  100),
            "gamma":    (1,     10,     1),
        },
        "zedsrc": {
            "exposure": (0,     100,    1),
            "gain":     (0,     100,    1),
            "gamma":    (1,     10,     1),
        },
        "default": {
            "exposure": (0,     60000, 1000),
            "gain":     (0,     5000,  100),
            "gamma":    (1,     10,     1),
        },
    }

    def __init__(self, cam, parent=None):
        super().__init__(parent)
        self.cam = cam

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWindowFlag(Qt.X11BypassWindowManagerHint, False)

        src = getattr(cam, 'source_type', None) or 'default'
        ranges = self.RANGES.get(src, self.RANGES['default'])
        res_options = RESOLUTION_OPTIONS.get(src, RESOLUTION_OPTIONS['default'])

        cur_res_idx = getattr(cam, 'resolution', 0)
        cur_res_idx = max(0, min(cur_res_idx, len(res_options) - 1))

        panel_w, panel_h = 960, 370
        self.setFixedSize(panel_w, panel_h)

        self._bg = QWidget(self)
        self._bg.setGeometry(0, 0, panel_w, panel_h)
        self._bg.setStyleSheet("""
            background-color: rgba(8, 8, 10, 240);
            border: 1px solid rgba(255,255,255,35);
            border-radius: 3px;
        """)

        accent = QWidget(self)
        accent.setGeometry(0, 0, panel_w, 2)
        accent.setStyleSheet("background-color: #ffffff; border-radius: 0px;")

        title = QLabel("CAMERA SETTINGS", self)
        title.setGeometry(20, 16, panel_w - 40, 20)
        title.setStyleSheet("""
            color: #ffffff;
            font-family: 'Oxanium SemiBold';
            font-size: 12px;
            letter-spacing: 4px;
            background: transparent;
        """)

        subtitle = QLabel(f"SN: {cam.serial}", self)
        subtitle.setGeometry(20, 36, panel_w - 40, 14)
        subtitle.setStyleSheet("""
            color: rgba(255,255,255,80);
            font-family: 'Oxanium';
            font-size: 9px;
            letter-spacing: 1px;
            background: transparent;
        """)

        sep = QWidget(self)
        sep.setGeometry(20, 56, panel_w - 40, 1)
        sep.setStyleSheet("background: rgba(255,255,255,20);")

        init_exposure = cam.pending_exposure if cam.pending_exposure is not None else cam.exposure
        init_gain     = cam.pending_gain     if cam.pending_gain     is not None else cam.gain
        init_gamma    = cam.pending_gamma    if cam.pending_gamma    is not None else cam.gamma

        self._sliders = {}
        self._value_labels = {}

        settings = [
            ("EXPOSURE",  "exposure",  init_exposure, ranges["exposure"],  "µs"),
            ("GAIN",      "gain",      init_gain,     ranges["gain"],      ""),
            ("GAMMA",     "gamma",     init_gamma,    ranges["gamma"],     ""),
        ]

        y_start = 68
        row_h   = 56

        for i, (label_text, key, init_val, (rmin, rmax, rstep), unit) in enumerate(settings):
            y = y_start + i * row_h

            lbl = QLabel(label_text, self)
            lbl.setGeometry(20, y, 120, 16)
            lbl.setStyleSheet("""
                color: rgba(255,255,255,130);
                font-family: 'Oxanium';
                font-size: 9px;
                letter-spacing: 2px;
                background: transparent;
            """)

            val_lbl = QLabel(f"{init_val}{(' ' + unit) if unit else ''}", self)
            val_lbl.setGeometry(panel_w - 130, y, 110, 16)
            val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            val_lbl.setStyleSheet("""
                color: #ffffff;
                font-family: 'Oxanium SemiBold';
                font-size: 11px;
                background: transparent;
            """)
            self._value_labels[key] = (val_lbl, unit)

            slider = Slider(Qt.Horizontal, self)
            slider.setGeometry(20, y + 20, panel_w - 40, 24)
            steps = max(1, (rmax - rmin) // rstep)
            slider.setRange(0, steps)
            init_step = max(0, min(steps, (init_val - rmin) // rstep))
            slider.setValue(init_step)

            def make_callback(mn, step, lbl_ref, unit_ref):
                def on_change(v):
                    actual = mn + v * step
                    lbl_ref.setText(f"{actual}{(' ' + unit_ref) if unit_ref else ''}")
                return on_change

            slider.valueChanged.connect(make_callback(rmin, rstep, val_lbl, unit))
            self._sliders[key] = (slider, rmin, rstep)

        res_y = y_start + 3 * row_h + 4

        sep_res = QWidget(self)
        sep_res.setGeometry(20, res_y, panel_w - 40, 1)
        sep_res.setStyleSheet("background: rgba(255,255,255,20);")

        res_lbl = QLabel("RESOLUTION", self)
        res_lbl.setGeometry(20, res_y + 10, 120, 16)
        res_lbl.setStyleSheet("""
            color: rgba(255,255,255,130);
            font-family: 'Oxanium';
            font-size: 9px;
            letter-spacing: 2px;
            background: transparent;
        """)

        self._res_selector = ResolutionSelector(res_options, cur_res_idx, self)
        self._res_selector.setGeometry(20, res_y + 30, panel_w - 40, 26)
        self._res_options = res_options

        btn_sep_y = res_y + 68
        sep2 = QWidget(self)
        sep2.setGeometry(20, btn_sep_y, panel_w - 40, 1)
        sep2.setStyleSheet("background: rgba(255,255,255,20);")

        btn_y_pos = btn_sep_y + 12
        btn_h = 32
        btn_w = (panel_w - 60) // 2

        self._btn_cancel = QPushButton("CANCEL", self)
        self._btn_cancel.setGeometry(20, btn_y_pos, btn_w, btn_h)
        self._btn_cancel.setCursor(Qt.PointingHandCursor)
        self._btn_cancel.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,8);
                color: rgba(255,255,255,120);
                border: 1px solid rgba(255,255,255,25);
                border-radius: 2px;
                font-family: 'Oxanium SemiBold';
                font-size: 10px;
                letter-spacing: 2px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,16);
                color: rgba(255,255,255,200);
            }
            QPushButton:pressed {
                background: rgba(255,255,255,6);
            }
        """)
        self._btn_cancel.clicked.connect(self._on_cancel)

        self._btn_apply = QPushButton("APPLY", self)
        self._btn_apply.setGeometry(40 + btn_w, btn_y_pos, btn_w, btn_h)
        self._btn_apply.setCursor(Qt.PointingHandCursor)
        self._btn_apply.setStyleSheet("""
            QPushButton {
                background: #ffffff;
                color: #0a0a0e;
                border: none;
                border-radius: 2px;
                font-family: 'Oxanium SemiBold';
                font-size: 10px;
                letter-spacing: 2px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,210);
            }
            QPushButton:pressed {
                background: rgba(255,255,255,160);
            }
        """)
        self._btn_apply.clicked.connect(self._on_apply)

    def _read_values(self):
        result = {}
        for key, (slider, rmin, rstep) in self._sliders.items():
            result[key] = rmin + slider.value() * rstep
        idx = self._res_selector.selected_index()
        _, rw, rh, _ = self._res_options[idx]
        result['res_w'] = rw
        result['res_h'] = rh
        return result

    def _on_apply(self):
        vals = self._read_values()
        self.applied.emit(vals['exposure'], vals['gain'], vals['gamma'], vals['res_w'], vals['res_h'])
        self.close()

    def _on_cancel(self):
        self.cancelled.emit()
        self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        if not painter.isActive():
            return
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.transparent)
        painter.end()

    def showEvent(self, event):
        super().showEvent(event)
        self.raise_()
        self.activateWindow()


# ──────────────────────── GStreamer Video Widget ────────────────────────

class GStreamerVideoWidget(QWidget):
    clicked = Signal()

    def __init__(self, pipeline_str, use_overlay=True, camera_width=1920, camera_height=1080, parent=None):
        super().__init__(parent)

        self.pipeline_str = pipeline_str
        self.use_overlay = use_overlay
        self.thread = None
        self.video_resize_enabled = True
        self.camera_width = camera_width
        self.camera_height = camera_height
        self.selection_overlay = None
        self.loading_overlay = None

        self.setStyleSheet("background-color: black;")

        self.setAttribute(Qt.WA_NativeWindow)

        self.video_surface = QWidget(self)
        self.video_surface.setAttribute(Qt.WA_NativeWindow)
        self.video_surface.setStyleSheet("background:black;")

    def _compute_video_rect(self, widget_w, widget_h):
        cam_w = self.camera_width
        cam_h = self.camera_height

        scale_w = widget_w / cam_w
        scale_h = widget_h / cam_h
        scale = max(scale_w, scale_h)

        render_w = int(cam_w * scale)
        render_h = int(cam_h * scale)

        x_offset = (widget_w - render_w) // 2
        y_offset = (widget_h - render_h) // 2

        return x_offset, y_offset, render_w, render_h

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        x_off, y_off, render_w, render_h = self._compute_video_rect(w, h)
        self.video_surface.setGeometry(x_off, y_off, render_w, render_h)
        self.update_video_render_rectangle(w, h)

    def apply_video_resize(self):
        if not self.video_resize_enabled:
            return
        w, h = self.width(), self.height()
        x_off, y_off, render_w, render_h = self._compute_video_rect(w, h)
        self.video_surface.setGeometry(x_off, y_off, render_w, render_h)
        self.update_video_render_rectangle(w, h)

    def start(self):
        if not self.use_overlay:
            return

        # Ensure the widget and video_surface are shown and correctly sized
        # before handing the native window handle to GStreamer.
        # If video_surface has no size yet, force a geometry update now.
        self.show()
        if self.video_surface.width() == 0 or self.video_surface.height() == 0:
            w, h = self.width(), self.height()
            if w > 0 and h > 0:
                x_off, y_off, rw, rh = self._compute_video_rect(w, h)
                self.video_surface.setGeometry(x_off, y_off, rw, rh)
        self.video_surface.show()
        # Force the native X11 window to be created and mapped before winId() is used
        self.video_surface.winId()
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

        surf_w = self.video_surface.width()
        surf_h = self.video_surface.height()
        if surf_w <= 0 or surf_h <= 0:
            return

        sink = self.thread.pipeline.get_by_interface(GstVideo.VideoOverlay.__gtype__)
        if sink:
            try:
                sink.set_render_rectangle(0, 0, surf_w, surf_h)
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


class ResizableContainer(QWidget):
    resized = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resized.emit()

# ──────────────────────── Camera Node ────────────────────────

class CameraConfig:
    names = ["ZED X One #1", "ZED X One #2", "ZED X Mini #1", "Placeholder 4", "Placeholder 5", "Placeholder 6", "Placeholder 7", "Placeholder 8"]
    serials = [309256978, 305325257, 58896881, 0, 0, 0, 0, 0]
    default_resolutions = [4, 4, 6, 0, 0, 0, 0, 0]
    camera_ids = [0, 1, 0, 3, 4, 5, 6, 7]
    ratios = [[1920, 1080]] * 8
    layout = CAMERA_LAYOUT

class Camera:
    def __init__(self, position, default_resolution):
        self.serial = None
        self.camera_id = 0
        self.index = -1
        self.position = position
        self.active = False
        self.border_ready = False
        self.widget = None
        self.pipeline = None
        self.source_type = None
        self.resolution = default_resolution
        self.exposure = 5000
        self.gain = 40
        self.gamma = 2
        self.pending_exposure = None
        self.pending_gain = None
        self.pending_gamma = None

    def has_pending_changes(self):
        return any(v is not None for v in [self.pending_exposure, self.pending_gain, self.pending_gamma])

    def apply_pending(self):
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
        
        self.current_index = 0
        self.focused_camera = None
        self.focus_mode = False
        self.switching_mode = False
        self.display_mode = 2

        self.always_remove_inactive_cams = True
        self.animations = {}
        self._settings_panel = None
        self._selection_overlay: Optional[SelectionOverlay] = None
        
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
                        "name": "ZED X ONE #1", "exposure": 10000, "gain": 30000, "gamma": 2},
            305325257: {"type": "ZED X One", "source": "zedxonesrc", "camera_id": 1,
                        "name": "ZED X ONE #2","exposure": 10000, "gain": 30000, "gamma": 2},
            58896881:  {"type": "ZED X Mini", "source": "zedsrc",    "camera_id": 0,
                        "name": "ZED X MINI #1","exposure": 50,   "gain": 50, "gamma": 2},
        }

        print(f"\nConfigured cameras:")
        for serial, info in self.camera_info.items():
            print(f"  Serial {serial}: {info['type']} using {info['source']} (camera-id={info['camera_id']})")

    # ──────────────────────── Setup ────────────────────────

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
        # Snap overlay geometry to match camera widget in global coords
        try:
            gp = self.container.mapToGlobal(self.container.rect().topLeft())
        except RuntimeError:
            return
        for cam in self.cameras:
            if not cam.widget:
                continue
            geom = cam.widget.geometry()
            for attr in ('loading_overlay', 'selection_overlay'):
                ov = getattr(cam.widget, attr, None)
                if ov:
                    try:
                        ov.setGeometry(gp.x() + geom.x(), gp.y() + geom.y(), geom.width(), geom.height())
                    except RuntimeError:
                        setattr(cam.widget, attr, None)

    # ──────────────────────── Key Listener ────────────────────────

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
        self.update_camera_borders()
        self.print_infomation()
        self.cleanup_orphaned_widgets()
        QTimer.singleShot(20, self.process_command_queue)

    # ──────────────────────── Camera Utilities ────────────────────────

    def get_available_index(self):
        used = {cam.index for cam in self.cameras if cam.index != -1}
        unused = [i for i in range(len(self.cameras)) if i not in used]
        return unused[0] if unused else None

    # ──────────────────────── Settings Panel (Mouse) ────────────────────────

    def show_settings_panel(self, cam):
        if self._settings_panel is not None:
            try:
                self._settings_panel.close()
            except RuntimeError:
                pass
            self._settings_panel = None

        panel = CameraSettingsPanel(cam)

        def on_apply(exposure, gain, gamma, res_w, res_h):
            cam.pending_exposure = exposure
            cam.pending_gain = gain
            cam.pending_gamma = gamma
            src = getattr(cam, 'source_type', None) or 'default'
            opts = RESOLUTION_OPTIONS.get(src, RESOLUTION_OPTIONS['default'])
            for label, ow, oh, ridx in opts:
                if ow == res_w and oh == res_h:
                    cam.resolution = ridx
                    if cam.index >= 0:
                        self.config.ratios[cam.index] = [res_w, res_h]
                    break
            cam.apply_pending()

            geom = cam.widget.geometry()
            self.remove_widget(cam)
            self.create_camera_widget(cam)
            cam.widget.setGeometry(geom)
            self._settings_panel = None

        def on_cancel():
            cam.discard_pending()
            self._settings_panel = None

        panel.applied.connect(on_apply)
        panel.cancelled.connect(on_cancel)

        screen = QApplication.primaryScreen().geometry()
        px = screen.left() + (screen.width()  - panel.width())  // 2
        py = screen.top()  + (screen.height() - panel.height()) // 2

        panel.move(px, py)
        panel.show()
        panel.raise_()
        panel.activateWindow()
        self._settings_panel = panel

    # ──────────────────────── Activation / Deactivation ────────────────────────

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
            cam.name        = info["name"]
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
        
        self.current_index = cam.position

        print(f'Current Camera: {self.current_index}')
        self.create_camera_widget(cam)
        self.set_camera_positions()

    def deactivate_camera(self):
        if self.current_index is None:
            print("No camera currently selected.")
            return
            
        cam = self.cameras[self.current_index]
        if not cam.active:
            print(f"Camera {self.current_index} is not active.")
            return
        
        cam.discard_pending()
        cam.border_ready = False

        original_pos = cam.position
        cam.active = False
        active_positions = [c.position for c in self.cameras if c.active]
        if not active_positions:
            for c in self.cameras:
                self.remove_widget(c)
            self.current_index = None
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

        candidates = [p for p in active_positions if p < self.current_index]
        self.current_index = max(candidates) if candidates else self.current_index
        if self.always_remove_inactive_cams:
            self.select_camera(original_pos, True)
            if not self.cameras[self.current_index].active:
                self.select_camera(max(candidates), True)

        QApplication.processEvents()
        self.cleanup_orphaned_widgets()
        self.set_camera_positions()

    # ──────────────────────── Selection ────────────────────────

    def select_camera(self, index, bypass_inactive=False):
        if not bypass_inactive and not self.cameras[index].active:
            print(f"Camera {index} not active")
            return
        if bypass_inactive:
            index = next((c.position for c in self.cameras if c.position == index), 0)
        self.current_index = index
        print(f"Current Index: {index}")

    def select_next_camera(self, direction):
        if self.current_index is None:
            print("No camera currently selected.")
            return
        active_positions = [c.position for c in self.cameras if c.active]
        if not active_positions:
            print("No active cameras.")
            return
        max_pos = max(active_positions)
        self.current_index = (self.current_index + direction) % (max_pos + 1)

    def change_display(self, direction):
        self.display_mode = (self.display_mode + direction) % len(self.config.layout[0])
        self.set_camera_positions()

    def toggle_focus(self):
        if self.current_index is None:
            return
        cam = self.cameras[self.current_index]
        if not cam.active or not cam.widget:
            return

        if not self.focus_mode:
            self.focus_mode = True
            self.focused_camera = self.current_index

            # Hide selection overlays on all non-focused cameras
            for c in self.cameras:
                if c.position == self.focused_camera:
                    continue
                ov = getattr(c.widget, 'selection_overlay', None) if c.widget else None
                if ov:
                    ov.notify_unfocused()

            cam.widget.raise_()
            self.stop_animation_for_widget(cam.widget)
            self.tween_position_and_size(cam.widget, 0, 0, self.container.width(), self.container.height(), duration=500)
        else:
            prev_focused = self.focused_camera
            self.focus_mode = False
            self.focused_camera = None

            # Restore selection overlays on all cameras that were suppressed
            for c in self.cameras:
                if c.position == prev_focused:
                    continue
                ov = getattr(c.widget, 'selection_overlay', None) if c.widget else None
                if ov:
                    if c.position == self.current_index and c.active:
                        ov.notify_reselected()
                    else:
                        ov.notify_focused()  # exits unfocused back to unselected

            self.set_camera_positions()
    
    def toggle_switching_mode(self):
        self.switching_mode = not self.switching_mode
    
    def switch_cameras(self, target_pos, bypass_inactive=False):
        cam_current = next((c for c in self.cameras if c.position == self.current_index), None)
        cam_target = next((c for c in self.cameras if c.position == target_pos), None)
        active_positions = [c.position for c in self.cameras if c.active]

        restrictions = [
            [not cam_current, 'No current camera. '],
            [not cam_target, 'No target camera. '],
            [not active_positions, 'No active positions. '],
            [cam_target and max(active_positions) < cam_target.position, 'Target camera is beyond max active positions. ']
        ]
        if not bypass_inactive:
            fail_reason = ''.join([r[1] for r in restrictions if r[0]])
            if len(fail_reason) > 0:            
                print(f'Failed to switch due to the following reason(s):\n{fail_reason}')
                return
        print(f"Switched cameras {self.current_index} <-> {target_pos}")
        
        attrs_to_swap = ['index', 'active']
        for attr in attrs_to_swap:
            temp = getattr(cam_current, attr)
            setattr(cam_current, attr, getattr(cam_target, attr))
            setattr(cam_target, attr, temp)
        
        cam_current.widget, cam_target.widget = cam_target.widget, cam_current.widget
        
        self.switching_mode = False        
        self.set_camera_positions()

    # ──────────────────────── Move Index ────────────────────────

    def move_index(self, direction):
        if self.current_index is None:
            print("No camera currently selected.")
            return

        cam = self.cameras[self.current_index]
        if not cam.active:
            print(f"Camera {self.current_index} is not active.")
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

    # ──────────────────────── Camera Widgets ────────────────────────

    def create_camera_widget(self, cam):
        active_positions = [c.position for c in self.cameras if c.active] + [cam.position]
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

            mode_prop = _SRC_MODE_PROP.get(src, "")
            mode_val  = getattr(cam, 'resolution', 0)
            mode_str  = f"{mode_prop}={mode_val} " if mode_prop else ""

            if src == "zedxonesrc":
                cam_props = (
                    f"camera-id={cid} "
                    f"{mode_str}"
                    f"ctrl-auto-exposure=false "
                    f"ctrl-auto-exposure-range-min={exp} "
                    f"ctrl-auto-exposure-range-max={exp} "
                    f"ctrl-exposure-time={exp} "
                    f"ctrl-analog-gain={gain} "
                    f"ctrl-gamma={gamma}"
                )
            elif src == "zedsrc":
                cam_props = (
                    f"camera-id={cid} "
                    f"{mode_str}"
                )

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
                use_overlay=use_camera,
                camera_width=cam_w,
                camera_height=cam_h,
                parent=self.container
            )
            camera_feed_widget.setGeometry(x, y, w, h)
            camera_feed_widget.show()

            # ── Connect click handler ──────────────────────────────────────
            def on_widget_clicked(pos=cam.position, c=cam):
                if self.current_index == pos and c.active:
                    self.show_settings_panel(c)
                else:
                    self.select_camera(pos)
                    self.update_camera_borders()

            camera_feed_widget.clicked.connect(on_widget_clicked)

            # ── Start pipeline and wire up post-load border delay ──────────
            if use_camera:
                QApplication.processEvents()
                camera_feed_widget.start()

                def on_video_loaded(c=cam):
                    def _reveal_border():
                        c.border_ready = True
                        self.update_camera_borders()
                    QTimer.singleShot(1000, _reveal_border)
                camera_feed_widget.thread.video_loaded.connect(on_video_loaded)

                # Overlay is a top-level window positioned over the camera widget.
                # It cannot be a child widget because native X11 windows (video_surface)
                # always render above Qt-painted siblings regardless of Z-order.
                overlay = LoadingOverlay(cam_w=cam_w, cam_h=cam_h)
                gp = self.container.mapToGlobal(self.container.rect().topLeft())
                overlay.setGeometry(gp.x() + x, gp.y() + y, w, h)
                overlay._click_target = camera_feed_widget
                camera_feed_widget.loading_overlay = overlay
                overlay.start()
            else:
                cam.border_ready = True

            cam.widget = camera_feed_widget
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

        for i, cam in enumerate(self.cameras):
            if not cam.widget:
                continue
            if not cam.active:
                self.stop_animation_for_widget(cam.widget)
                continue

            layouts = self.config.layout[i][self.display_mode]
            dims = layouts[max(0, min(max_pos + 1 - i, len(layouts) - 1))]
            
            x = round(dims[0] * self.container.width())
            y = round(dims[1] * self.container.height())
            w = round(dims[2] * self.container.width())
            h = round(dims[3] * self.container.height())

            self.tween_position_and_size(cam.widget, x, y, w, h, duration=500)

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
    
            is_selected = (cam.position == self.current_index and cam.active)
            existing = getattr(cam.widget, 'selection_overlay', None)
    
            if is_selected:
                if not cam.border_ready:
                    continue
                if existing is not None:
                    existing.notify_reselected()
                else:
                    try:
                        cam_w = cam.widget.camera_width
                        cam_h = cam.widget.camera_height
                    except AttributeError:
                        cam_w, cam_h = 1920, 1080

                    # Top-level window, same reasoning as LoadingOverlay.
                    overlay = SelectionOverlay(cam_w=cam_w, cam_h=cam_h)
                    geom = cam.widget.geometry()
                    if cam.widget.parent():
                        gp = cam.widget.parent().mapToGlobal(cam.widget.parent().rect().topLeft())
                        overlay.setGeometry(gp.x() + geom.x(), gp.y() + geom.y(), geom.width(), geom.height())
                    else:
                        overlay.setGeometry(geom)
                    overlay._click_target = cam.widget
                    overlay.set_context(cam)

                    cam.widget.selection_overlay = overlay
                    overlay.start()

                    # If we're in focus mode and this is not the focused camera,
                    # immediately suppress the overlay.
                    if self.focus_mode and cam.position != self.focused_camera:
                        overlay.notify_unfocused()
            else:
                if existing is not None:
                    existing.notify_deselected()

    # ──────────────────────── Tween Animation ────────────────────────

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
            for attr in ('loading_overlay', 'selection_overlay'):
                ov = getattr(cam.widget, attr, None)
                if ov:
                    try:
                        ov.hide()
                        ov.deleteLater()
                    except RuntimeError:
                        pass
                    setattr(cam.widget, attr, None)
    
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
            new_w = int(start_geom.width()  + (end_w - start_geom.width())  * value)
            new_h = int(start_geom.height() + (end_h - start_geom.height()) * value)
            widget.setGeometry(new_x, new_y, new_w, new_h)
            try:
                if widget.parent():
                    gp = widget.parent().mapToGlobal(widget.parent().rect().topLeft())
                    for attr in ('loading_overlay', 'selection_overlay'):
                        ov = getattr(widget, attr, None)
                        if ov:
                            try:
                                ov.setGeometry(gp.x() + new_x, gp.y() + new_y, new_w, new_h)
                            except RuntimeError:
                                setattr(widget, attr, None)
            except RuntimeError:
                pass

        animation.valueChanged.connect(update_geometry)
        animation.start()
        self.animations[id(widget)] = animation

        if hasattr(widget, "video_resize_enabled"):
            widget.video_resize_enabled = False

        def finish_animation():
            if hasattr(widget, "video_resize_enabled"):
                widget.video_resize_enabled = True
                widget.apply_video_resize()

        animation.finished.connect(finish_animation)

    # ──────────────────────── Print Information ────────────────────────

    def print_infomation(self):
        print(f"Current Selected: {self.current_index}")
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

    def on_app_state_changed(state):
        for cam in node.cameras:
            if not cam.widget:
                continue
            existing = getattr(cam.widget, 'selection_overlay', None)
            if existing is None:
                continue
            if state == Qt.ApplicationActive:
                existing.notify_focused()
            else:
                existing.notify_unfocused()

    app.applicationStateChanged.connect(on_app_state_changed)

    timer = QTimer()
    timer.timeout.connect(lambda: rclpy.spin_once(node, timeout_sec=0))
    timer.start(30)

    app.exec()

    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()