import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo, GLib
import sys
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'xcb')

# Add the spear_gui package to path
sys.path.insert(0, '/home/nathan/repos/spear/gui-2026/install/spear_gui/lib/python3.10/site-packages')

from PySide6.QtWidgets import QApplication, QWidget, QLabel
from PySide6.QtCore import Qt, QTimer, QThread
from PySide6.QtGui import QPainter

from spear_gui.overlay_system import OverlayCanvas, InlineLoadingOverlay, InlineSelectionOverlay

Gst.init(None)
app = QApplication(sys.argv)

PORTS = [5000, 5001, 5002, 5003]

container = QWidget()
container.resize(800, 450)
container.setStyleSheet("background-color: #2b2b2b;")
container.show()

# Real OverlayCanvas as Tool window - same as camera_node
overlay_canvas = OverlayCanvas(container, external_tick=False)
overlay_canvas.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowTransparentForInput | Qt.Tool)
overlay_canvas.setAttribute(Qt.WA_TranslucentBackground)
overlay_canvas.show()

def reposition_overlay():
    gp = container.mapToGlobal(container.rect().topLeft())
    overlay_canvas.setGeometry(gp.x(), gp.y(), container.width(), container.height())
    overlay_canvas.raise_()

QApplication.processEvents()
reposition_overlay()

class GstThread(QThread):
    def __init__(self, win_id, port):
        super().__init__()
        self.win_id = win_id
        self.port = port
        self.loop = GLib.MainLoop()
        self.pipeline = None

    def run(self):
        pipeline_str = (
            f"udpsrc port={self.port} "
            f"! application/x-rtp,encoding-name=H265,payload=96 "
            f"! rtph265depay ! h265parse ! avdec_h265 "
            f"! videoconvert ! videoscale "
            f"! ximagesink force-aspect-ratio=false"
        )
        self.pipeline = Gst.parse_launch(pipeline_str)
        sink = self.pipeline.get_by_interface(GstVideo.VideoOverlay.__gtype__)
        sink.set_window_handle(self.win_id)
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        def on_msg(bus, msg):
            if msg.type == Gst.MessageType.ERROR:
                err, _ = msg.parse_error()
                print(f"[port {self.port}] ERROR: {err}")
                self.loop.quit()
            elif msg.type == Gst.MessageType.ASYNC_DONE:
                print(f"[port {self.port}] ASYNC_DONE")
        bus.connect("message", on_msg)
        self.pipeline.set_state(Gst.State.PLAYING)
        self.loop.run()
        self.pipeline.set_state(Gst.State.NULL)

    def stop(self):
        if self.loop.is_running():
            self.loop.quit()

streams = []  # list of (widget, thread, loading_overlay)

def layout_widgets():
    n = len(streams)
    if n == 0:
        return
    w_each = container.width() // n
    for i, (widget, _, _) in enumerate(streams):
        widget.setGeometry(i * w_each, 0, w_each, container.height())
    reposition_overlay()

def add_stream():
    if len(streams) >= len(PORTS):
        print("Max streams reached")
        return
    port = PORTS[len(streams)]
    print(f"Adding stream on port {port}")

    video = QWidget(container)
    video.setAttribute(Qt.WA_NativeWindow)
    video.setAttribute(Qt.WA_NoSystemBackground)
    video.setAttribute(Qt.WA_OpaquePaintEvent)
    video.setAutoFillBackground(False)
    video.show()
    video.winId()
    QApplication.processEvents()

    # Register real InlineLoadingOverlay - same as camera_node
    lo = InlineLoadingOverlay(cam_w=1920, cam_h=1080)
    lo._click_target = video
    overlay_canvas.register(video, loading_ov=lo)
    lo.start()

    thread = GstThread(video.winId(), port)

    def on_async_done(captured_lo=lo, v=video):
        print(f"Notifying loaded for port {port}: lo._done={captured_lo._done} lo._closing={captured_lo._closing}")
        print(f"  polygons phases: {[p._phase for p in captured_lo._polygons]}")
        print(f"  canvas ticker active: {overlay_canvas._tick_timer.isActive() if hasattr(overlay_canvas, '_tick_timer') else 'external'}")
        print(f"  canvas entries: {list(overlay_canvas._entries.keys())}")
        print(f"  widget in entries: {v in overlay_canvas._entries}")
        captured_lo.notify_loaded()
        def restart_ticker():
            if hasattr(overlay_canvas, '_tick_timer') and not overlay_canvas._tick_timer.isActive():
                print(f"  restarting ticker after broadcast")
                overlay_canvas._tick_timer.start()
        QTimer.singleShot(100, restart_ticker)

    streams.append((video, thread, lo))
    layout_widgets()
    thread.start()

    # Simulate ASYNC_DONE -> notify_loaded after stream connects
    QTimer.singleShot(3000, on_async_done)

def remove_last_stream():
    if not streams:
        return
    widget, thread, lo = streams.pop()
    print(f"Removing stream winId={widget.winId()}")
    overlay_canvas.unregister(widget)
    thread.stop()
    thread.wait(3000)
    widget.hide()
    widget.deleteLater()
    container.update()
    layout_widgets()

container.keyPressEvent = lambda e: (
    add_stream() if e.text() == 'a' else
    remove_last_stream() if e.text() == 'r' else
    app.quit() if e.text() == 'q' else None
)
container.setFocusPolicy(Qt.StrongFocus)
container.setFocus()

label = QLabel("a=add  r=remove  q=quit", container)
label.setStyleSheet("color: white; background: rgba(0,0,0,120); padding: 4px;")
label.move(8, 8)
label.show()
label.raise_()

app.exec()
for widget, thread, _ in streams:
    thread.stop()
    thread.wait(2000)