from __future__ import annotations

import random
import sys
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QFontDatabase

from dataclasses import dataclass, field

import time
from typing import Dict, Any

from spear_gui.overlay_system import (
    AnimatedPolygon, AnimatedText, AnimatedGraph, AnimatedPie, AnimatedWindow, DataChannel,
    SYS_MOUSE_ABS_X, SYS_MOUSE_ABS_Y
)
from spear_gui.main_gui_defs import (
    MAIN_POLYGON_DEFS, MAIN_TEXT_DEFS, MAIN_GRAPH_DEFS,
    MAIN_PIE_DEFS, MAIN_WINDOW_DEFS,
)




# ──────────────────────── Subscriptions ──────────────────────────
@dataclass
class SubscriptionConfig:
    topic:        str
    channel_name: str
    msg_type:     Any                         = Float64
    extractor:    Callable[[Any], float]      = field(default=lambda msg: float(msg.data))
    max_samples:  int                         = 100
    unit:         str                         = ''
    qos:          int                         = 10


class SubscriptionManager:
    def __init__(self, node, configs: List[SubscriptionConfig]) -> None:
        self._channels: Dict[str, DataChannel] = {}
        self._subs = []
        for cfg in configs:
            channel = DataChannel(cfg.channel_name, cfg.max_samples, cfg.unit)
            self._channels[cfg.channel_name] = channel
            def _make_callback(ch, ex):
                def _cb(msg):
                    try:    ch.push(ex(msg))
                    except Exception as e:
                        node.get_logger().warn(f'extractor error on "{ch.name}": {e}')
                return _cb
            sub = node.create_subscription(
                cfg.msg_type, cfg.topic,
                _make_callback(channel, cfg.extractor), cfg.qos,
            )
            self._subs.append(sub)

    def channel(self, name: str) -> Optional[DataChannel]:
        return self._channels.get(name)

    def context(self) -> Dict[str, Dict[str, Any]]:
        return {name: ch.snapshot() for name, ch in self._channels.items()}

SUBSCRIPTION_CONFIGS = [
    SubscriptionConfig(topic=f'main/test_value{i}', channel_name=f'test_value{i}', max_samples=50)
    for i in range(1, 10)
]


class MainNode(Node):
    def __init__(self):
        super().__init__('main_overlay_node')
        self.test_publishers = [
            self.create_publisher(Float64, f'main/test_value{i+1}', 10)
            for i in range(9)
        ]
        self.create_timer(0.5, self._publish_demo)
        self.sub_manager = SubscriptionManager(self, SUBSCRIPTION_CONFIGS)

    def _publish_demo(self):
        import random
        values = [
            random.uniform(1.0,  10.0),
            random.uniform(2.0,  20.0),
            random.uniform(5.0,  10.0),
            random.uniform(9.0,  11.0),
            random.uniform(1.0,  10.0) + random.uniform(0.1, 1.1) ** 50,
            random.uniform(20.0, 70.0),
            round(random.uniform(0, 1)) * 10.0 + 10.0,
            random.uniform(12.0, 55.0),
            random.uniform(24.0, 77.0),
        ]
        for pub, val in zip(self.test_publishers, values):
            msg = Float64()
            msg.data = val
            pub.publish(msg)


class MainOverlayWidget(QWidget):
    TICK_MS = 16

    def __init__(self, node: MainNode, parent=None):
        super().__init__(parent)
        self._node = node

        self.setMinimumSize(640, 360)
        self.setStyleSheet('background-color: #0a0c12;')
        self.setWindowTitle('Main Overlay')
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()
        self.setWindowFlags(Qt.FramelessWindowHint)

        self._polygons = [AnimatedPolygon(d) for d in MAIN_POLYGON_DEFS]
        self._texts    = [AnimatedText(d)    for d in MAIN_TEXT_DEFS]
        self._graphs   = [AnimatedGraph(d)   for d in MAIN_GRAPH_DEFS]
        self._pies     = [AnimatedPie(d)     for d in MAIN_PIE_DEFS]
        self._windows  = [AnimatedWindow(d)  for d in MAIN_WINDOW_DEFS]

        self._broadcast('open')

        self._active_timer = QTimer(self)
        self._active_timer.setInterval(16)
        self._active_timer.timeout.connect(self._tick)
        self._active_timer.start()

        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(100)
        self._idle_timer.timeout.connect(self._tick)

        self._needs_repaint = True

    def _broadcast(self, phase: str):
        for p in self._polygons: p.set_phase(phase)
        for t in self._texts:    t.set_phase(phase)

    def _context(self) -> Dict[str, Any]:
        return self._node.sub_manager.context()

    def _tick(self):
        ctx = self._context()
        now = time.monotonic()
        for p in self._polygons: p.update()
        for t in self._texts:    t.update()
        for g in self._graphs:   g.tick(now)
        for pie in self._pies:   pie.update(ctx)
        for win in self._windows:
            win.tick(now)
            win.update(ctx, self.width(), self.height())

        needs = (
            any(not p.phase_done() or p._dirty for p in self._polygons) or
            any(not t.phase_done() or t._dirty for t in self._texts)    or
            any(not win._is_done() for win in self._windows)            or
            self._needs_repaint
        )
        self._needs_repaint = False

        if needs:
            self._active_timer.start()
            self._idle_timer.stop()
            self.update()
        else:
            self._active_timer.stop()
            self._idle_timer.start()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
                def _resize():
                    screen = self.screen()
                    sg = screen.geometry()
                    w = sg.width() // 2
                    h = sg.height() // 2
                    self.resize(w, h)
                    self.move(sg.center() - self.rect().center())
                QTimer.singleShot(50, _resize)
            else:
                screen = self.screen()
                self.setGeometry(screen.geometry())
                self.showFullScreen()
            return
        if event.isAutoRepeat():
            return
        for win in self._windows:
            if win.key_press(event.key()):
                return

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return
        for win in self._windows:
            if win.key_release(event.key()):
                return

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton: return
        mx, my = event.position().x(), event.position().y()
        for win in self._windows:
            if win.mouse_press(mx, my, self.width(), self.height()): break

    def mouseMoveEvent(self, event):
        SYS_MOUSE_ABS_X.value = event.x()
        SYS_MOUSE_ABS_Y.value = event.y()
        mx, my = event.position().x(), event.position().y()
        for win in self._windows:
            win.mouse_move(mx, my, self.width(), self.height())
        self._needs_repaint = True
        self._active_timer.start()
        self._idle_timer.stop()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton: return
        mx, my = event.position().x(), event.position().y()
        for win in self._windows:
            if win.mouse_release(mx, my, self.width(), self.height()): break

    def resizeEvent(self, event):
        self._needs_repaint = True
        super().resizeEvent(event)

    def leaveEvent(self, event):
        for win in self._windows: win.mouse_leave()

    def paintEvent(self, event):
        painter = QPainter(self)
        if not painter.isActive():
            painter.end()
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.NoPen)

        w, h = self.width(), self.height()
        ctx  = self._context()

        for poly in self._polygons:
            poly.draw(painter, w, h, cam_w=1920, cam_h=1080)
        for text in self._texts:
            if text.hidden: continue
            label = text.resolve_text(ctx)
            if not label: continue
            font = text.build_font()
            if text._cached_fm is None:
                text._cached_fm = QFontMetrics(font)
            painter.setFont(font)
            painter.setPen(text.cur_color)
            dx, dy = text.resolve_pos(w, h, 1920, 1080, label, font)
            painter.drawText(dx, dy, label)
            painter.setPen(Qt.NoPen)
        for g in self._graphs:
            g.draw(painter, w, h, ctx)
        for pie in self._pies:
            pie.draw(painter, w, h)
        for win in self._windows:
            win.draw(painter, w, h, ctx)

        painter.end()

def main():
    rclpy.init()
    node = MainNode()

    app = QApplication(sys.argv)

    from PySide6.QtGui import QFontDatabase

    def load_fonts(font_dir: str = '.'):
        import os
        for fname in os.listdir(font_dir):
            if fname.lower().endswith(('.ttf', '.otf')):
                path = os.path.join(font_dir, fname)
                fid  = QFontDatabase.addApplicationFont(path)
                if fid == -1:
                    print(f'[load_fonts] failed to load: {fname}')
                else:
                    families = QFontDatabase.applicationFontFamilies(fid)
                    print(f'[load_fonts] loaded: {fname} -> {families}')

    load_fonts('spear_gui')

    widget = MainOverlayWidget(node)
    screen = QApplication.screens()[0]
    sg = screen.geometry()
    w = sg.width() // 2
    h = sg.height() // 2
    widget.resize(w, h)
    widget.move(sg.center() - widget.rect().center())
    widget.show()

    spin_timer = QTimer()
    spin_timer.timeout.connect(lambda: rclpy.spin_once(node, timeout_sec=0))
    spin_timer.start(30)

    ret = app.exec()
    node.destroy_node()
    rclpy.shutdown()
    sys.exit(ret)


if __name__ == '__main__':
    main()