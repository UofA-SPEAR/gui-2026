import ctypes
ctypes.cdll.LoadLibrary('libX11.so.6').XInitThreads()

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import sys
import os
import threading
import rclpy
from rclpy.node import Node
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import QThread, Signal, QTimer, QEasingCurve, Qt, QObject, QEvent, qInstallMessageHandler
from PySide6.QtGui import QColor, QPainter, QFontDatabase, QFont, QPen, QFontMetrics, QImage, QPixmap, QSurfaceFormat
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtOpenGL import QOpenGLShaderProgram, QOpenGLShader, QOpenGLTexture
from OpenGL import GL
from std_msgs.msg import String
from collections import deque
from spear_gui.gui_vars import CAMERA_LAYOUT
from spear_gui.overlay_system import SettingsOverlay, CameraSelectOverlay, OverlayCanvas, InlineLoadingOverlay, InlineSelectionOverlay
from spear_gui.overlay_defs import SETTING_DEFS, SETTING_TEXT_DEFS, SETTING_SLIDER_DEFS, SETTING_BUTTON_DEFS
from spear_gui.egl_bridge import get_egl_handles, wrap_gst_gl_context, set_pipeline_contexts, get_gl_texture_id

qInstallMessageHandler(lambda mode, ctx, msg: None if 'painter' in msg.lower() and 'not active' in msg.lower() else print(msg))

Gst.init(None)
_glib_loop   = GLib.MainLoop()
_glib_thread = threading.Thread(target=_glib_loop.run, daemon=True)


# ── GLSL shaders ─────────────────────────────────────────────────────────────

_VERT = """
#version 330 core
const vec2 POSITIONS[4] = vec2[](
    vec2(-1.0,  1.0),
    vec2(-1.0, -1.0),
    vec2( 1.0,  1.0),
    vec2( 1.0, -1.0)
);
const vec2 TEXCOORDS[4] = vec2[](
    vec2(0.0, 0.0),
    vec2(0.0, 1.0),
    vec2(1.0, 0.0),
    vec2(1.0, 1.0)
);
out vec2 vTex;
void main() {
    vTex        = TEXCOORDS[gl_VertexID];
    gl_Position = vec4(POSITIONS[gl_VertexID], 0.0, 1.0);
}
"""

_FRAG = """
#version 330 core
in  vec2      vTex;
out vec4      fragColor;
uniform sampler2D uTex;
uniform vec2      uScale;   // (render_w/widget_w, render_h/widget_h)
uniform vec2      uOffset;  // (ox/widget_w, oy/widget_h) in NDC terms
void main() {
    // Map fragment tex-coord through cover-fill offset/scale
    vec2 t = vTex * uScale + uOffset;
    if (t.x < 0.0 || t.x > 1.0 || t.y < 0.0 || t.y > 1.0) {
        fragColor = vec4(0.051, 0.051, 0.051, 1.0); // #0d0d0d letterbox
    } else {
        fragColor = texture(uTex, t);
    }
}
"""


class KeyEventFilter(QObject):
    def __init__(self, node):
        super().__init__()
        self.node = node

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            key = event.text() or ('\r' if event.key() in (Qt.Key_Return, Qt.Key_Enter) else None)
            if key:
                msg = String()
                msg.data = key
                self.node.key_pub.publish(msg)
            return True
        return False


# ── GStreamer thread ──────────────────────────────────────────────────────────

class GStreamerThread(QThread):
    finished      = Signal()
    error_occured = Signal(str)
    video_loaded  = Signal()
    new_texture   = Signal(int, int, int)   # texture_id, width, height

    def __init__(self, pipeline_str, parent=None):
        super().__init__(parent)
        self.pipeline_str   = pipeline_str
        self.pipeline       = None
        self._loaded        = False
        self._stop_event    = threading.Event()
        self._gst_contexts  = None   # (display_capsule, app_capsule) set by widget

        self.pipeline = Gst.parse_launch(pipeline_str)
        sink = self.pipeline.get_by_name("sink")
        sink.connect("new-sample", self._on_new_sample)

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_message)

    def set_gl_contexts(self, display_capsule, app_capsule):
        self._gst_contexts = (display_capsule, app_capsule)

    def _on_new_sample(self, sink):
        sample = sink.emit("pull-sample")
        if sample is None:
            return Gst.FlowReturn.OK

        buf  = sample.get_buffer()
        caps = sample.get_caps()
        s    = caps.get_structure(0)
        w    = s.get_int("width")[1]
        h    = s.get_int("height")[1]

        # Extract GL texture ID via C bridge — zero CPU pixel copy
        buf_ptr = buf.__gpointer__
        try:
            tex_id = get_gl_texture_id(buf_ptr)
        except RuntimeError as e:
            print(f"[GST] texture error: {e}", file=sys.stderr)
            return Gst.FlowReturn.OK

        if not self._loaded:
            self._loaded = True
            self.video_loaded.emit()

        self.new_texture.emit(tex_id, w, h)
        return Gst.FlowReturn.OK

    def _on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.NEED_CONTEXT:
            # Provide our wrapped EGL context to GStreamer so glupload can
            # share the same EGL display/context as Qt
            if self._gst_contexts is not None:
                ctx_type = message.parse_context_type()
                if ctx_type in ("gst.gl.display_context", "gst.gl.app_context"):
                    set_pipeline_contexts(self.pipeline.__gpointer__, *self._gst_contexts)
        elif t == Gst.MessageType.ERROR:
            err, _ = message.parse_error()
            self.error_occured.emit(str(err))
            self._stop_event.set()
        elif t == Gst.MessageType.EOS:
            self._stop_event.set()
        return True

    def run(self):
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            self.error_occured.emit("Failed to set pipeline to PLAYING")
            return
        self._stop_event.wait()
        self.pipeline.set_state(Gst.State.NULL)
        self.finished.emit()

    def stop(self):
        self._stop_event.set()


# ── Video widget (QOpenGLWidget, zero-copy GPU path) ─────────────────────────

class GStreamerVideoWidget(QOpenGLWidget):
    clicked = Signal()

    def __init__(self, pipeline_str, camera_width=1920, camera_height=1080, parent=None):
        fmt = QSurfaceFormat()
        fmt.setVersion(3, 3)
        fmt.setProfile(QSurfaceFormat.CoreProfile)

        super().__init__(parent)
        self.setFormat(fmt)

        self.pipeline_str  = pipeline_str
        self.camera_width  = camera_width
        self.camera_height = camera_height
        self.thread        = None

        self._shader       = None
        self._vao          = None
        self._tex_id       = 0
        self._tex_w        = camera_width
        self._tex_h        = camera_height
        self._paint_pending = False

    # ── GL lifecycle ──────────────────────────────────────────────────────────

    def initializeGL(self):
        # Qt's EGL context is now current — grab handles and wrap for GStreamer
        display_ptr, context_ptr = get_egl_handles()
        display_cap, app_cap     = wrap_gst_gl_context(display_ptr, context_ptr)

        self._shader = QOpenGLShaderProgram(self)
        self._shader.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex,   _VERT)
        self._shader.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment, _FRAG)
        self._shader.link()

        self._vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self._vao)
        GL.glBindVertexArray(0)

        GL.glClearColor(0.051, 0.051, 0.051, 1.0)

        # Start the pipeline now that we have a valid GL context
        self.thread = GStreamerThread(self.pipeline_str, parent=self)
        self.thread.set_gl_contexts(display_cap, app_cap)
        self.thread.error_occured.connect(lambda msg: print(f"GST error: {msg}", file=sys.stderr))
        self.thread.new_texture.connect(self._on_new_texture, Qt.QueuedConnection)
        self.thread.start()

    def paintGL(self):
        self._paint_pending = False
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)

        if not self._tex_id or not self._shader:
            return

        w, h   = self.width(), self.height()
        fw, fh = self._tex_w, self._tex_h
        scale  = max(w / fw, h / fh)
        rw, rh = fw * scale, fh * scale
        ox     = (w - rw) / 2.0
        oy     = (h - rh) / 2.0

        # Convert pixel offset/scale to UV-space for the shader
        scale_u  = rw / w
        scale_v  = rh / h
        offset_u = -ox / rw
        offset_v = -oy / rh

        self._shader.bind()
        self._shader.setUniformValue("uTex",    0)
        self._shader.setUniformValue("uScale",  scale_u,  scale_v)
        self._shader.setUniformValue("uOffset", offset_u, offset_v)

        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._tex_id)
        GL.glBindVertexArray(self._vao)
        GL.glDrawArrays(GL.GL_TRIANGLE_STRIP, 0, 4)
        GL.glBindVertexArray(0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
        self._shader.release()

    def resizeGL(self, w, h):
        GL.glViewport(0, 0, w, h)

    # ── Frame receiver ────────────────────────────────────────────────────────

    def _on_new_texture(self, tex_id: int, w: int, h: int):
        self._tex_id = tex_id
        self._tex_w  = w
        self._tex_h  = h
        if not self._paint_pending:
            self._paint_pending = True
            self.update()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self):
        # Pipeline is started in initializeGL() once the GL context exists.
        # This stub is called by CameraNode for API compatibility.
        pass

    def stop(self):
        if self.thread:
            self.thread.stop()
            self.thread.wait(3000)

    def apply_video_resize(self):
        pass

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


# ── Placeholder widget ────────────────────────────────────────────────────────

class PlaceholderCameraWidget(QWidget):
    clicked = Signal()

    def __init__(self, camera_width=1920, camera_height=1080, parent=None):
        super().__init__(parent)
        self.camera_width  = camera_width
        self.camera_height = camera_height
        self.setStyleSheet("background-color: #0d0d0d;")
        self._cache = self._cache_w = self._cache_h = None

    def stop(self):
        pass

    def apply_video_resize(self):
        pass

    def _rebuild_cache(self, w, h):
        px = QPixmap(w, h)
        px.fill(QColor(13, 13, 13))
        p = QPainter(px)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(255, 255, 255, 18))
        pen.setWidthF(1.0)
        p.setPen(pen)
        step = max(40, min(w, h) // 8)
        for gx in range(0, w, step):
            p.drawLine(gx, 0, gx, h)
        for gy in range(0, h, step):
            p.drawLine(0, gy, w, gy)
        cx, cy = w / 2, h / 2
        icon_w, icon_h = min(w * 0.18, 80), min(h * 0.14, 54)
        body = QRectF(cx - icon_w / 2, cy - icon_h / 2, icon_w, icon_h)
        p.setBrush(Qt.NoBrush)
        pen2 = QPen(QColor(255, 255, 255, 50))
        pen2.setWidthF(2.0)
        p.setPen(pen2)
        p.drawRoundedRect(body, 4, 4)
        p.drawEllipse(QPointF(cx, cy), min(icon_w, icon_h) * 0.26, min(icon_w, icon_h) * 0.26)
        p.drawRoundedRect(QRectF(cx - icon_w * 0.11, body.top() - icon_h * 0.25, icon_w * 0.22, icon_h * 0.25), 2, 2)
        f = QFont()
        f.setFamily("Oxanium SemiBold")
        f.setPointSizeF(max(6.0, min(h * 0.03, 11.0)))
        p.setFont(f)
        p.setPen(QColor(255, 255, 255, 55))
        fm = QFontMetrics(f)
        label = "NO SIGNAL"
        p.drawText(int(cx - fm.horizontalAdvance(label) / 2), int(cy + icon_h / 2 + fm.ascent() + 6), label)
        p.end()
        self._cache, self._cache_w, self._cache_h = px, w, h

    def paintEvent(self, event):
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        if self._cache_w != w or self._cache_h != h:
            self._rebuild_cache(w, h)
        painter = QPainter(self)
        if painter.isActive():
            painter.drawPixmap(0, 0, self._cache)
            painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ResizableContainer(QWidget):
    resized = Signal()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resized.emit()


class CameraConfig:
    serials             = [302801647, 303928833, 305325257, 307142683, 308873104, 309256978, 44249482, 58896881]
    default_resolutions = [4, 4, 6, 0, 0, 0, 0, 0]
    camera_ids          = [0, 1, 0, 3, 4, 5, 6, 7]
    ratios              = [[1920, 1080]] * 8
    layout              = CAMERA_LAYOUT


class Camera:
    def __init__(self, position, default_resolution):
        self.serial           = None
        self.camera_id        = 0
        self.index            = -1
        self.position         = position
        self.active           = False
        self.border_ready     = False
        self.widget           = None
        self.source_type      = None
        self.resolution       = default_resolution
        self.exposure         = 5000
        self.gain             = 40
        self.gamma            = 2
        self.pending_exposure = None
        self.pending_gain     = None
        self.pending_gamma    = None
        self.port             = None

    def has_pending_changes(self):
        return any(v is not None for v in [self.pending_exposure, self.pending_gain, self.pending_gamma])

    def apply_pending(self):
        if self.pending_exposure is not None:
            self.exposure, self.pending_exposure = self.pending_exposure, None
        if self.pending_gain is not None:
            self.gain, self.pending_gain = self.pending_gain, None
        if self.pending_gamma is not None:
            self.gamma, self.pending_gamma = self.pending_gamma, None

    def discard_pending(self):
        self.pending_exposure = self.pending_gain = self.pending_gamma = None


class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')

        self.container          = None
        self.command_queue      = deque()
        self.processing_command = False
        self.config             = CameraConfig()
        self.cameras            = [Camera(i, self.config.default_resolutions[i]) for i in range(len(self.config.serials))]
        self.current_index      = 0
        self.focused_camera     = None
        self.focus_mode         = False
        self.switching_mode     = False
        self.display_mode       = 2
        self.always_remove_inactive_cams = True
        self._tweens            = {}
        self._settings_panel    = None
        self._cam_select_panel  = None

        self._master_timer = QTimer()
        self._master_timer.setInterval(16)
        self._master_timer.timeout.connect(self._master_tick)

        self.key_pub = self.create_publisher(String, "key", 10)
        self.create_subscription(String, 'key', self.key_listener, 10)

        self.zed_sources = {"zedxone": "zedxonesrc", "zed": "zedsrc"}
        self.available_zed_sources = {
            name: Gst.ElementFactory.make(element, None) is not None
            for name, element in self.zed_sources.items()
        }

        self.camera_info = {
            302801647: {"type": "ZED X One", "source": "zedxonesrc", "camera_id": 0,  "name": "ZED X ONE #1", "exposure": 10000, "gain": 30000, "gamma": 2, "port": 5000},
            303928833: {"type": "ZED X One", "source": "zedxonesrc", "camera_id": 1,  "name": "ZED X ONE #2", "exposure": 10000, "gain": 30000, "gamma": 2, "port": 5001},
            305325257: {"type": "ZED X One", "source": "zedxonesrc", "camera_id": 2,  "name": "ZED X ONE #3", "exposure": 10000, "gain": 30000, "gamma": 2, "port": 5002},
            307142683: {"type": "ZED X One", "source": "zedxonesrc", "camera_id": 3,  "name": "ZED X ONE #4", "exposure": 10000, "gain": 30000, "gamma": 2, "port": 5003},
            308873104: {"type": "ZED X One", "source": "zedxonesrc", "camera_id": 4,  "name": "ZED X ONE #5", "exposure": 10000, "gain": 30000, "gamma": 2, "port": 5004},
            309256978: {"type": "ZED X One", "source": "zedxonesrc", "camera_id": 5,  "name": "ZED X ONE #6", "exposure": 10000, "gain": 30000, "gamma": 2, "port": 5005},
            44249482:  {"type": "ZED X Mini", "source": "zedsrc",    "camera_id": 0,  "name": "ZED X MINI #1", "exposure": 10000, "gain": 30000, "gamma": 2, "port": 5006},
            58896881:  {"type": "ZED X Mini", "source": "zedsrc",    "camera_id": 1,  "name": "ZED X MINI #2", "exposure": 10000, "gain": 30000, "gamma": 2, "port": 5007},
        }

    def setup_gui(self, parent=None):
        self.container = ResizableContainer(parent)
        self.container.setMinimumSize(400, 200)
        self.container.resize(800, 400)
        self.container.setStyleSheet("background-color: #2b2b2b;")
        self.container.resized.connect(self.on_container_resized)
        self._overlay_canvas = OverlayCanvas(self.container, external_tick=True)
        self._overlay_canvas.setAttribute(Qt.WA_TranslucentBackground)
        self._overlay_canvas.setGeometry(self.container.rect())
        self._overlay_canvas.show()
        self._overlay_canvas.raise_()
        self._master_timer.start()

    def on_container_resized(self):
        self._overlay_canvas.setGeometry(self.container.rect())
        self._overlay_canvas.raise_()
        self.set_camera_positions()

    def key_listener(self, key_msg):
        self.command_queue.append(key_msg.data.lower())
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
                rclpy.shutdown()
                return
            case 'w': self.activate_camera()
            case 's': self.deactivate_camera()
            case 'e': self.select_next_camera(1)
            case 'q': self.select_next_camera(-1)
            case 'd': self.move_index(1)
            case 'a': self.move_index(-1)
            case 'm': self.change_display(1)
            case 'n': self.change_display(-1)
            case 't': self.show_cam_select_panel()
            case 'f': self.toggle_focus()
            case 'r': self.toggle_switching_mode()
            case key if key in '01234567':
                if self.switching_mode:
                    self.switch_cameras(int(key))
                    self.switching_mode = False
        self.update_camera_borders()
        self.print_infomation()
        self.cleanup_orphaned_widgets()
        QTimer.singleShot(20, self.process_command_queue)

    def get_available_index(self):
        used = {cam.index for cam in self.cameras if cam.index != -1}
        unused = [i for i in range(len(self.cameras)) if i not in used]
        return unused[0] if unused else None

    def show_settings_panel(self, cam):
        if self._settings_panel is not None or self._cam_select_panel is not None:
            return
        screen = QApplication.primaryScreen().geometry()
        _PW, _PH = 1920, 1080
        panel = SettingsOverlay(SETTING_DEFS, SETTING_TEXT_DEFS, SETTING_SLIDER_DEFS, SETTING_BUTTON_DEFS, cam_w=_PW, cam_h=_PH)
        panel.setFixedSize(_PW, _PH)
        panel.move(screen.left() + (screen.width() - _PW) // 2, screen.top() + (screen.height() - _PH) // 2)

        def on_apply():
            cam.apply_pending()
            geom = cam.widget.geometry()
            self.remove_widget(cam)
            self.create_camera_widget(cam)
            cam.widget.setGeometry(geom)
            self._settings_panel = None

        panel.open(cam, on_apply=on_apply, on_cancel=lambda: (cam.discard_pending(), setattr(self, '_settings_panel', None)))
        self._settings_panel = panel

    def show_cam_select_panel(self):
        if self._cam_select_panel is not None:
            return
        screen = QApplication.primaryScreen().geometry()
        _PW, _PH = 1920, 1080
        panel = CameraSelectOverlay(cam_w=_PW, cam_h=_PH, initial_display_mode=self.display_mode, initial_cams=sum(c.active for c in self.cameras))
        panel.setFixedSize(_PW, _PH)
        panel.move(screen.left() + (screen.width() - _PW) // 2, screen.top() + (screen.height() - _PH) // 2)

        def on_apply(display_mode, num_cams):
            self.display_mode = display_mode
            active = [c for c in self.cameras if c.active]
            while len(active) < num_cams:
                self.activate_camera()
                active = [c for c in self.cameras if c.active]
            while len(active) > num_cams:
                active = [c for c in self.cameras if c.active]
                if active:
                    self.current_index = active[-1].position
                self.deactivate_camera()
                active = [c for c in self.cameras if c.active]
            active = [c for c in self.cameras if c.active]
            if active:
                self.current_index = active[-1].position
            self.update_camera_borders()
            self.set_camera_positions()
            self._cam_select_panel = None

        panel.open(on_apply=on_apply, on_cancel=lambda: setattr(self, '_cam_select_panel', None))
        self._cam_select_panel = panel
        panel.raise_()
        if self._overlay_canvas:
            self._overlay_canvas.stackUnder(panel)

    def activate_camera(self):
        if not any(not c.active for c in self.cameras):
            return
        cam = next(c for c in self.cameras if not c.active)
        cam.active = True
        active_indexes = {c.index for c in self.cameras if c.active and c is not cam}
        if cam.index in (-1, *active_indexes):
            cam.index = self.get_available_index()
        cam.serial = self.config.serials[cam.index]

        if cam.serial in self.camera_info:
            info = self.camera_info[cam.serial]
            cam.name, cam.source_type, cam.camera_id = info["name"], info["source"], info["camera_id"]
            cam.exposure, cam.gain, cam.gamma = info.get("exposure"), info.get("gain"), info.get("gamma")
            source_ok = any(el == cam.source_type and self.available_zed_sources.get(n) for n, el in self.zed_sources.items())
            if not source_ok:
                cam.source_type, cam.camera_id, cam.port = None, 0, info.get("port")
        else:
            cam.camera_id = self.config.camera_ids[cam.index]
            if self.available_zed_sources.get("zedxone"):
                cam.source_type = "zedxonesrc"
            else:
                cam.source_type, cam.port = None, 5000 + cam.index

        self.current_index = cam.position
        self.create_camera_widget(cam)
        self.set_camera_positions()

    def deactivate_camera(self):
        if self.current_index is None:
            return
        cam = self.cameras[self.current_index]
        if not cam.active:
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
            if not c.active and c.position > max_pos:
                self.remove_widget(c)

        if self.always_remove_inactive_cams:
            self.remove_widget(cam)
            found = True
            while found:
                found = False
                for i in range(len(self.cameras)):
                    if not self.cameras[i].active and self.cameras[i].position < max_pos:
                        found = True
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

    def select_camera(self, index, bypass_inactive=False):
        if not bypass_inactive and not self.cameras[index].active:
            return
        if bypass_inactive:
            index = next((c.position for c in self.cameras if c.position == index), 0)
        self.current_index = index

    def select_next_camera(self, direction):
        if self.current_index is None:
            return
        active_positions = [c.position for c in self.cameras if c.active]
        if not active_positions:
            return
        self.current_index = (self.current_index + direction) % (max(active_positions) + 1)

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
            for c in self.cameras:
                if c.position != self.focused_camera:
                    ov = self._overlay_canvas.get_selection(c.widget) if c.widget else None
                    if ov:
                        ov.notify_unfocused()
            cam.widget.raise_()
            self.stop_animation_for_widget(cam.widget)
            self.tween_position_and_size(cam.widget, 0, 0, self.container.width(), self.container.height(), duration=500)
        else:
            prev = self.focused_camera
            self.focus_mode = False
            self.focused_camera = None
            for c in self.cameras:
                if c.position == prev:
                    continue
                ov = self._overlay_canvas.get_selection(c.widget) if c.widget else None
                if ov:
                    ov.notify_reselected() if c.position == self.current_index and c.active else ov.notify_focused()
            self.set_camera_positions()

    def toggle_switching_mode(self):
        self.switching_mode = not self.switching_mode

    def switch_cameras(self, target_pos, bypass_inactive=False):
        cam_current = next((c for c in self.cameras if c.position == self.current_index), None)
        cam_target  = next((c for c in self.cameras if c.position == target_pos), None)
        active_positions = [c.position for c in self.cameras if c.active]
        if not bypass_inactive:
            if not cam_current or not cam_target or not active_positions:
                return
            if max(active_positions) < cam_target.position:
                return
        for attr in ('index', 'active'):
            temp = getattr(cam_current, attr)
            setattr(cam_current, attr, getattr(cam_target, attr))
            setattr(cam_target, attr, temp)
        cam_current.widget, cam_target.widget = cam_target.widget, cam_current.widget
        self.switching_mode = False
        self.set_camera_positions()

    def move_index(self, direction):
        if self.current_index is None:
            return
        cam = self.cameras[self.current_index]
        if not cam.active:
            return
        start = cam.index
        idx   = start
        for _ in range(len(self.cameras)):
            idx = (idx + direction) % len(self.cameras)
            active_indexes = [c.index for c in self.cameras if c.active]
            if idx not in active_indexes or idx == start:
                cam.index  = idx
                cam.serial = self.config.serials[idx]
                if cam.serial in self.camera_info:
                    cam.source_type = self.camera_info[cam.serial]["source"]
                    cam.camera_id   = self.camera_info[cam.serial]["camera_id"]
                else:
                    cam.camera_id = self.config.camera_ids[idx]
                break

    def _gl_pipeline(self, source: str) -> str:
        # glupload uploads the decoded frame to GPU memory.
        # glcolorconvert converts YUV→RGB on the GPU.
        # appsink pulls the GLMemory buffer — texture ID only, no pixel copy.
        return (
            f"{source}"
            f" ! glupload"
            f" ! glcolorconvert"
            f" ! appsink name=sink emit-signals=true sync=false"
            f" caps=video/x-raw(memory:GLMemory),format=RGBA"
            f" max-buffers=2 drop=true"
        )

    def create_camera_widget(self, cam):
        active_positions = [c.position for c in self.cameras if c.active] + [cam.position]
        max_pos  = max(active_positions)
        layouts  = self.config.layout[cam.position][self.display_mode]
        dims     = layouts[max(0, min(max_pos + 1 - cam.position, len(layouts) - 1))]
        x, y     = round(dims[0] * self.container.width()), round(dims[1] * self.container.height())
        w, h     = round(dims[2] * self.container.width()), round(dims[3] * self.container.height())
        cam_w, cam_h = (self.config.ratios[cam.index] if cam.index >= 0 else [1920, 1080])

        pipeline   = None
        use_camera = False

        if cam.port is not None:
            pipeline = self._gl_pipeline(
                f"udpsrc port={cam.port} ! application/x-rtp,encoding-name=H265,payload=96"
                f" ! rtph265depay ! h265parse ! avdec_h265"
                f" ! queue max-size-buffers=4 leaky=downstream"
            )
            use_camera = True
        elif cam.source_type is not None:
            if cam.source_type == "zedxonesrc":
                props = (f"camera-id={cam.camera_id} ctrl-auto-exposure=false"
                         f" ctrl-auto-exposure-range-min={cam.exposure} ctrl-auto-exposure-range-max={cam.exposure}"
                         f" ctrl-exposure-time={cam.exposure} ctrl-analog-gain={cam.gain} ctrl-gamma={cam.gamma}")
            else:
                props = f"camera-id={cam.camera_id}"
            pipeline   = self._gl_pipeline(f"{cam.source_type} {props} ! queue")
            use_camera = True

        if use_camera:
            widget = GStreamerVideoWidget(pipeline, camera_width=cam_w, camera_height=cam_h, parent=self.container)
        else:
            widget = PlaceholderCameraWidget(camera_width=cam_w, camera_height=cam_h, parent=self.container)

        widget.setGeometry(x, y, w, h)
        widget.show()

        def on_clicked(pos=cam.position, c=cam):
            if self._settings_panel is not None or self._cam_select_panel is not None:
                return
            if self.current_index == pos and c.active:
                self.show_settings_panel(c)
            else:
                self.select_camera(pos)
                self.update_camera_borders()

        widget.clicked.connect(on_clicked)

        if use_camera:
            QApplication.processEvents()
            widget.start()

            def on_loaded(c=cam, wgt=widget):
                lo = self._overlay_canvas.get_loading(wgt)
                if lo:
                    lo.notify_loaded()
                QTimer.singleShot(1000, lambda: (setattr(c, 'border_ready', True), self.update_camera_borders()))

            # video_loaded is on the thread, which is started in initializeGL
            # — wire it up now so it's ready when the pipeline fires
            if hasattr(widget, 'thread') and widget.thread:
                widget.thread.video_loaded.connect(on_loaded)
            else:
                # thread starts in initializeGL which fires after show();
                # use a short poll to wire up once the thread exists
                def _wire_loaded(c=cam, wgt=widget, cb=on_loaded):
                    if wgt.thread:
                        wgt.thread.video_loaded.connect(cb)
                    else:
                        QTimer.singleShot(50, lambda: _wire_loaded(c, wgt, cb))
                QTimer.singleShot(50, lambda: _wire_loaded(cam, widget, on_loaded))

        overlay = InlineLoadingOverlay(cam_w=cam_w, cam_h=cam_h)
        overlay._click_target = widget
        self._overlay_canvas.register(widget, loading_ov=overlay)
        overlay.start()

        if not use_camera:
            QTimer.singleShot(300, lambda ov=overlay, c=cam: (
                ov.notify_loaded(), setattr(c, 'border_ready', True), self.update_camera_borders()
            ))

        self._overlay_canvas.raise_()
        cam.widget = widget

    def set_camera_positions(self):
        active_positions = [c.position for c in self.cameras if c.active]
        if not active_positions:
            return
        active_count = len(active_positions)
        for cam in self.cameras:
            if not cam.widget:
                continue
            if not cam.active:
                self.stop_animation_for_widget(cam.widget)
                continue
            rank    = sorted(active_positions).index(cam.position)
            layouts = self.config.layout[rank][self.display_mode]
            dims    = layouts[max(0, min(active_count - rank, len(layouts) - 1))]
            self.tween_position_and_size(
                cam.widget,
                round(dims[0] * self.container.width()),
                round(dims[1] * self.container.height()),
                round(dims[2] * self.container.width()),
                round(dims[3] * self.container.height()),
                duration=500,
            )

    def cleanup_orphaned_widgets(self):
        if not self.container:
            return
        valid = {id(c.widget) for c in self.cameras if c.widget} | {id(self._overlay_canvas)}
        for child in self.container.children():
            if isinstance(child, QWidget) and id(child) not in valid and id(child) != id(self.container):
                self.stop_animation_for_widget(child)
                child.hide()
                child.deleteLater()

    def update_camera_borders(self):
        for cam in self.cameras:
            if not cam.widget:
                continue
            is_selected = cam.position == self.current_index and cam.active
            existing    = self._overlay_canvas.get_selection(cam.widget)

            if cam.active and cam.border_ready and existing is None:
                cam_w = getattr(cam.widget, 'camera_width', 1920)
                cam_h = getattr(cam.widget, 'camera_height', 1080)
                ov = InlineSelectionOverlay(cam_w=cam_w, cam_h=cam_h)
                ov._click_target = cam.widget
                ov.set_context(cam)
                self._overlay_canvas.register(cam.widget, selection_ov=ov)
                ov.start()
                existing = ov

            if is_selected and cam.border_ready and existing:
                existing.notify_reselected()
                if self.focus_mode and cam.position != self.focused_camera:
                    existing.notify_unfocused()
            elif not is_selected and existing:
                existing.notify_deselected()

    def remove_widget(self, cam):
        if cam.widget:
            self._overlay_canvas.unregister(cam.widget)
            if hasattr(cam.widget, 'stop'):
                cam.widget.stop()
            cam.widget.hide()
            cam.widget.deleteLater()
            cam.widget = None
            if self.container:
                self.container.update()

    def _master_tick(self):
        done = []
        for wid, tw in self._tweens.items():
            widget = tw['widget']
            if not widget or widget.parent() is None:
                done.append(wid)
                continue
            tw['elapsed'] += 16
            t  = min(tw['elapsed'] / tw['duration'], 1.0)
            v  = 1.0 - (1.0 - t) ** 5
            sg = tw['start_geom']
            widget.setGeometry(
                int(sg.x()      + (tw['end_x'] - sg.x())      * v),
                int(sg.y()      + (tw['end_y'] - sg.y())      * v),
                int(sg.width()  + (tw['end_w'] - sg.width())  * v),
                int(sg.height() + (tw['end_h'] - sg.height()) * v),
            )
            if t >= 1.0:
                done.append(wid)
        for wid in done:
            self._tweens.pop(wid, None)
        if self._overlay_canvas:
            self._overlay_canvas.external_tick()
        if not self._tweens and (not self._overlay_canvas or not self._overlay_canvas.has_active()):
            self._master_timer.stop()

    def stop_animation_for_widget(self, widget):
        if widget:
            self._tweens.pop(id(widget), None)

    def tween_position_and_size(self, widget, end_x, end_y, end_w, end_h, ease_style=QEasingCurve.OutQuint, duration=500):
        if not widget or not widget.parent():
            return
        self.stop_animation_for_widget(widget)
        self._tweens[id(widget)] = {
            'widget': widget, 'start_geom': widget.geometry(),
            'end_x': end_x, 'end_y': end_y, 'end_w': end_w, 'end_h': end_h,
            'elapsed': 0, 'duration': max(1, duration),
        }
        if not self._master_timer.isActive():
            self._master_timer.start()

    def print_infomation(self):
        print(f"Selected: {self.current_index}")
        print(f"{'Pos':>3} | {'Active':>6} | {'Index':>5} | {'Serial':>9} | {'CamID':>5} | {'X':>4} | {'Y':>4} | {'W':>4} | {'H':>4}")
        print("-" * 75)
        for cam in self.cameras:
            g = cam.widget.geometry() if cam.widget else None
            x, y, w, h = (g.x(), g.y(), g.width(), g.height()) if g else (0, 0, 0, 0)
            active_str = "\033[92mTrue  \033[0m" if cam.active else "\033[91mFalse \033[0m"
            print(f"{cam.position:>3} | {active_str} | {cam.index:>5} | {str(cam.serial) if cam.serial else 'N/A':>9} | {cam.camera_id:>5} | {x:>4} | {y:>4} | {w:>4} | {h:>4}")


def main():
    os.environ.pop("QT_QPA_PLATFORM", None)
    rclpy.init()
    node = CameraNode()
    app  = QApplication([])
    _glib_thread.start()

    QFontDatabase.addApplicationFont(os.path.join(os.path.dirname(__file__), "Oxanium-VariableFont.ttf"))
    key_filter = KeyEventFilter(node)
    app.installEventFilter(key_filter)

    node.setup_gui()
    node.container.show()
    QApplication.processEvents()

    def on_app_state_changed(state):
        for cam in node.cameras:
            if not cam.widget:
                continue
            ov = node._overlay_canvas.get_selection(cam.widget)
            if ov:
                ov.notify_focused() if state == Qt.ApplicationActive else ov.notify_unfocused()

    app.applicationStateChanged.connect(on_app_state_changed)

    ros_timer = QTimer()
    ros_timer.timeout.connect(lambda: rclpy.spin_once(node, timeout_sec=0))
    ros_timer.start(30)

    app.exec()

    _glib_loop.quit()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()