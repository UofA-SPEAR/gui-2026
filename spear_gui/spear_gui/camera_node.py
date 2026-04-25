import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo, GLib
import sys
import rclpy
from rclpy.node import Node
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import QThread, Signal, QTimer, QVariantAnimation, QEasingCurve, Qt, QObject, QEvent, QElapsedTimer
from PySide6.QtGui import QColor, QPainter, QFontDatabase, QFont
from std_msgs.msg import String
from collections import deque
from PySide6.QtCore import qInstallMessageHandler
from typing import Optional
from spear_gui.gui_vars import CAMERA_LAYOUT
from spear_gui.overlay_system import LoadingOverlay, SelectionOverlay, SettingsOverlay, CameraSelectOverlay
from spear_gui.overlay_defs import (
    SETTING_DEFS, SETTING_TEXT_DEFS,
    SETTING_SLIDER_DEFS, SETTING_BUTTON_DEFS,
)

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

        self.show()
        if self.video_surface.width() == 0 or self.video_surface.height() == 0:
            w, h = self.width(), self.height()
            if w > 0 and h > 0:
                x_off, y_off, rw, rh = self._compute_video_rect(w, h)
                self.video_surface.setGeometry(x_off, y_off, rw, rh)
        self.video_surface.show()
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

    stream_ports = [5000, 5001, 5002, None, None, None, None, None]


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
        self.stream_port = None

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
        self._cam_select_panel = None
        self._selection_overlay: Optional[SelectionOverlay] = None

        self.key_pub = self.create_publisher(String, "key", 10)
        self.key_subscription = self.create_subscription(
            String, 'key', self.key_listener, 10
        )

        self.video_sink = self.find_best_video_sink()
        print(f"Using video sink: {self.video_sink}")

        self.use_video_overlay = self.video_sink in ['ximagesink', 'xvimagesink', 'glimagesink']
        if not self.use_video_overlay:
            self.get_logger().warn("\033[93mWarning: Video overlay not available. Using placeholder mode.\033[0m")

        self.camera_info = {
            309256978: {"type": "ZED X One", "camera_id": 0,
                        "name": "ZED X ONE #1", "port": 5000},
            305325257: {"type": "ZED X One", "camera_id": 1,
                        "name": "ZED X ONE #2", "port": 5001},
            58896881:  {"type": "ZED X Mini", "camera_id": 0,
                        "name": "ZED X MINI #1", "port": 5002},
            307142683:  {"type": "ZED X One", "camera_id": 2,
                        "name": "ZED X ONE #3", "port": 5003},
            308873104:  {"type": "ZED X One", "camera_id": 3,
                        "name": "ZED X ONE #4", "port": 5004},
            302801647:  {"type": "ZED X One", "camera_id": 4,
                        "name": "ZED X ONE #5", "port": 5005},
            303928833:  {"type": "ZED X One", "camera_id": 5,
                        "name": "ZED X ONE #6", "port": 5006},
            44249482:  {"type": "ZED X Mini", "camera_id": 1,
                        "name": "ZED X MINI #2", "port": 5007},
        }

        print(f"\nConfigured cameras (stream receiver):")
        for serial, info in self.camera_info.items():
            print(f"  Serial {serial}: {info['type']} receiving on UDP port {info['port']}")

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
            case 't':
                self.show_cam_select_panel()
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

    # ──────────────────────── Settings Panel ────────────────────────

    def show_settings_panel(self, cam):
        if self._settings_panel is not None or self._cam_select_panel is not None:
            return

        screen = QApplication.primaryScreen().geometry()
        _PW, _PH = 1920, 1080
        panel = SettingsOverlay(
            SETTING_RECT_DEFS, SETTING_TEXT_DEFS,
            SETTING_SLIDER_DEFS, SETTING_BUTTON_DEFS,
            cam_w=_PW, cam_h=_PH,
        )
        panel.setFixedSize(_PW, _PH)
        panel.move(
            screen.left() + (screen.width()  - _PW) // 2,
            screen.top()  + (screen.height() - _PH) // 2,
        )

        def on_apply():
            cam.apply_pending()
            geom = cam.widget.geometry()
            self.remove_widget(cam)
            self.create_camera_widget(cam)
            cam.widget.setGeometry(geom)
            self._settings_panel = None

        def on_cancel():
            cam.discard_pending()
            self._settings_panel = None

        panel.open(cam, on_apply=on_apply, on_cancel=on_cancel)
        self._settings_panel = panel

    def show_cam_select_panel(self):
        if self._cam_select_panel is not None:
            return

        screen = QApplication.primaryScreen().geometry()
        _PW, _PH = 1920, 1080

        active_cams = len([c for c in self.cameras if c.active])

        panel = CameraSelectOverlay(
            cam_w=_PW, cam_h=_PH,
            initial_display_mode=self.display_mode,
            initial_cams=active_cams,
        )
        panel.setFixedSize(_PW, _PH)
        panel.move(
            screen.left() + (screen.width()  - _PW) // 2,
            screen.top()  + (screen.height() - _PH) // 2,
        )

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

        def on_cancel():
            self._cam_select_panel = None

        panel.open(on_apply=on_apply, on_cancel=on_cancel)
        self._cam_select_panel = panel

        panel.raise_()
        for cam in self.cameras:
            for attr in ('loading_overlay', 'selection_overlay'):
                ov = getattr(cam.widget, attr, None) if cam.widget else None
                if ov:
                    try:
                        ov.stackUnder(panel)
                    except Exception:
                        pass

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
            cam.camera_id   = info["camera_id"]
            cam.stream_port = info["port"]
            cam.source_type = "udp_stream"
            print(f"Activated {info['type']} (Serial: {cam.serial}, UDP port: {cam.stream_port})")
        else:
            cam.camera_id   = self.config.camera_ids[cam.index]
            cam.stream_port = self.config.stream_ports[cam.index]
            if cam.stream_port is not None:
                cam.source_type = "udp_stream"
                print(f"Warning: Unknown serial {cam.serial}, using stream port {cam.stream_port}")
            else:
                cam.source_type = None
                print(f"Warning: No stream port configured for camera index {cam.index}")

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

            for c in self.cameras:
                if c.position == prev_focused:
                    continue
                ov = getattr(c.widget, 'selection_overlay', None) if c.widget else None
                if ov:
                    if c.position == self.current_index and c.active:
                        ov.notify_reselected()
                    else:
                        ov.notify_focused()

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
                    cam.stream_port = info["port"]
                    cam.camera_id   = info["camera_id"]
                else:
                    cam.camera_id   = self.config.camera_ids[cam.index]
                    cam.stream_port = self.config.stream_ports[cam.index]
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

        use_camera = self.use_video_overlay and cam.stream_port is not None

        cam_ratio = self.config.ratios[cam.index] if cam.index >= 0 else [1920, 1080]
        cam_w, cam_h = cam_ratio[0], cam_ratio[1]

        if use_camera:
            port = cam.stream_port

            pipeline = (
                f"udpsrc port={port} "
                f"! application/x-rtp,encoding-name=H265,payload=96 "
                f"! rtph265depay "
                f"! h265parse "
                f"! avdec_h265 "
                f"! videoconvert "
                f"! videoscale "
                f"! {self.video_sink} force-aspect-ratio=false"
            )
            print(f"[create_camera_widget] Stream pipeline for port {port}: {pipeline}")
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

            def on_widget_clicked(pos=cam.position, c=cam):
                if self._settings_panel is not None:
                    return
                if self._cam_select_panel is not None:
                    return
                if self.current_index == pos and c.active:
                    self.show_settings_panel(c)
                else:
                    self.select_camera(pos)
                    self.update_camera_borders()

            camera_feed_widget.clicked.connect(on_widget_clicked)

            if use_camera:
                QApplication.processEvents()
                camera_feed_widget.start()

                def on_video_loaded(c=cam):
                    def _reveal_border():
                        c.border_ready = True
                        self.update_camera_borders()
                    QTimer.singleShot(1000, _reveal_border)
                camera_feed_widget.thread.video_loaded.connect(on_video_loaded)

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

            if cam.active and cam.border_ready and existing is None:
                try:
                    cam_w = cam.widget.camera_width
                    cam_h = cam.widget.camera_height
                except AttributeError:
                    cam_w, cam_h = 1920, 1080

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
                existing = overlay

            if is_selected:
                if not cam.border_ready:
                    continue
                if existing is not None:
                    existing.notify_reselected()
                    if self.focus_mode and cam.position != self.focused_camera:
                        existing.notify_unfocused()
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
        print(f"{'Pos':>3} | {'Active':>6} | {'Index':>5} | {'Serial':>9} | {'Port':>5} | {'X':>4} | {'Y':>4} | {'W':>4} | {'H':>4}")
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
            port_str   = str(cam.stream_port) if cam.stream_port else "N/A"
            print(f"{cam.position:>3} | {active_str} | {cam.index:>5} | {serial_str:>9} | {port_str:>5} | {x:>4} | {y:>4} | {w:>4} | {h:>4}")


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
