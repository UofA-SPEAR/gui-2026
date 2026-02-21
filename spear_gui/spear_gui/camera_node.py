import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo, GLib
import sys
import rclpy
from rclpy.node import Node
from PySide6.QtWidgets import QApplication, QWidget, QLabel
from PySide6.QtCore import QThread, Signal, QTimer, QVariantAnimation, QEasingCurve, Qt, QObject, QEvent
from PySide6.QtGui import QColor, QPainter, QPen
from std_msgs.msg import String
from collections import deque

import os
font_path = os.path.join(os.path.dirname(__file__), "Oxanium-VariableFont.ttf")
QFontDatabase.addApplicationFont(font_path)

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

        return True

class GStreamerVideoWidget(QWidget):
    def __init__(self, pipeline_str, camera_name="", camera_serial="", use_overlay=True, parent=None):
        super().__init__(parent)

        self.pipeline_str = pipeline_str
        self.use_overlay = use_overlay
        self.thread = None
        self.placeholder_label = None
        self.video_resize_enabled = True

        self.setStyleSheet("background-color: black;")
        self.border_color = QColor("red")
        self.border_width = 3

        self.video_surface = QWidget(self)
        self.video_surface.setAttribute(Qt.WA_NativeWindow)
        self.video_surface.setStyleSheet("background:black;")

        self.name_label = QLabel(camera_name, self)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet("""
            color: white;
            font-size: 14px;
            font-weight: bold;
            font-family: 'Oxanium';
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

    def resizeEvent(self, event):
        super().resizeEvent(event)

        w, h = self.width(), self.height()

        bw = self.border_width
        self.video_surface.setGeometry(
            bw, bw,
            w - 2 * bw,
            h - 2 * bw
        )

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

        self.update_video_render_rectangle(
            w - 2 * bw,
            h - 2 * bw
        )

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
        self.thread.start()

    def stop(self):
        if self.thread:
            self.thread.stop()
            self.thread.wait(1000)

    def update_video_render_rectangle(self, w, h):
        if not self.thread or not self.thread.pipeline:
            return

        sink = self.thread.pipeline.get_by_interface(
            GstVideo.VideoOverlay.__gtype__
        )

        if sink:
            try:
                sink.set_render_rectangle(0, 0, w, h)
                sink.expose()
            except Exception:
                pass

    def on_error(self, error_msg):
        print("GStreamer error:", error_msg)

    def on_finished(self):
        print("Pipeline finished.")

    def update_labels(self, camera_name, camera_serial):
        self.name_label.setText(camera_name)
        self.id_label.setText(f"SN: {camera_serial}")
    
    def update_stats(self, exposure, gain, gamma):
        self.stats_label.setText(
            f"Exposure: {exposure} µs\n"
            f"Gain: {gain}\n"
            f"Gamma: {gamma}"
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
        self.serial = None  # The actual serial number (8+ digits)
        self.camera_id = 0  # The GStreamer camera-id (0, 1, 2, etc.)
        self.index = -1     # Index into config arrays
        self.position = position
        self.active = False
        self.widget = None
        self.pipeline = None
        self.source_type = None
        self.resolution = default_resolution
        self.exposure = 5000
        self.gain = 40
        self.gamma = 2
    
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

        # Manual mapping: serial number -> (camera type, gstreamer source, camera-id)
        # camera-id is the index that the ZED SDK assigns to each camera
        self.camera_info = {
            309256978: {"type": "ZED X One", "source": "zedxonesrc", "camera_id": 0,
                        "exposure": 10000, "gain": 30000, "gamma": 2},   # exposure in microseconds
            305325257: {"type": "ZED X One", "source": "zedxonesrc", "camera_id": 1,
                        "exposure": 10000, "gain": 30000, "gamma": 2},
            58896881:  {"type": "ZED X Mini", "source": "zedsrc",    "camera_id": 0,
                        "exposure": 50,   "gain": 30000, "gamma": 2},   # exposure as percentage 0-100
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
                self.restart_current_camera()
            case 'l':  # decrease exposure
                self.adjust_current_camera('exposure', -10000 if self.cameras[self.camera_current].source_type == 'zedxonesrc' else -30)
                self.restart_current_camera()
            case 'i':  # increase gain
                self.adjust_current_camera('gain', +5000)
                self.restart_current_camera()
            case 'k':  # decrease gain
                self.adjust_current_camera('gain', -5000)
                self.restart_current_camera()
            case 'u':  # increase gamma
                self.adjust_current_camera('gamma', +7)
                self.restart_current_camera()
            case 'j':  # decrease gamma
                self.adjust_current_camera('gamma', -7)
                self.restart_current_camera()
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
        if not cam.active: return
        current = getattr(cam, attr, 0)
        setattr(cam, attr, max(0, current + delta))
        print(f"  {attr} -> {getattr(cam, attr)}")
        if cam.widget and hasattr(cam.widget, 'update_stats'):
            cam.widget.update_stats(cam.exposure, cam.gain, cam.gamma)

    def restart_current_camera(self):
        cam = self.cameras[self.camera_current]
        if not cam.active or not cam.widget: return
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
            # Fallback for unconfigured cameras
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
                f"! {self.video_sink} force-aspect-ratio=true"
            )
        else:
            pipeline = None

        try:
            camera_feed_widget = GStreamerVideoWidget(
                pipeline if pipeline else "", 
                camera_name=self.config.names[cam.index],
                camera_serial=str(cam.serial),
                use_overlay=use_camera, 
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
        # Remove widget from camera
        if cam.widget:
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