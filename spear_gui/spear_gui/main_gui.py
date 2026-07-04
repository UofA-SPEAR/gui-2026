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
    expand_defs,
    AnimatedPolygon, AnimatedText, AnimatedGraph, AnimatedPie, AnimatedWindow, DataChannel,
    SYS_MOUSE_ABS_X, SYS_MOUSE_ABS_Y,
)

# main_gui_defs imports
import spear_gui.defs_02_shared_events
import spear_gui.defs_03_shared_gradients
import spear_gui.defs_04_startup
import spear_gui.defs_05_map
import spear_gui.defs_06_logger
import spear_gui.defs_07_info_display
import spear_gui.defs_08_arm_visual
import spear_gui.defs_09_tasks
import spear_gui.defs_99_test


from spear_gui.overlay_system import get_ordered_windows

MAIN_WINDOW_DEFS = get_ordered_windows()



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

        self._windows  = [AnimatedWindow(d) for d in MAIN_WINDOW_DEFS]
        self._win_cache: Dict[int, QPixmap] = {}

        for win in self._windows:
            win._broadcast('open')

        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(self.TICK_MS)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start()

    def _context(self) -> Dict[str, Any]:
        return self._node.sub_manager.context()

    def _tick(self):
        ctx = self._context()
        now = time.monotonic()
        for win in self._windows:
            win.tick(now)
            win.update(ctx, self.width(), self.height())
        self.update()

    def _is_fully_static(self, win) -> bool:
        return (win._cur_phase not in ('', 'close') and
                win._is_done() and
                not win._graphs and
                not win._spawned)

    def _draw_with_cache(self, painter, win, w, h, ctx):
        from PySide6.QtGui import QPixmap
        wid = id(win.defn)
        if self._is_fully_static(win):
            if wid not in self._win_cache:
                pix = QPixmap(w, h)
                pix.fill(Qt.transparent)
                p2 = QPainter(pix)
                p2.setRenderHint(QPainter.RenderHint.Antialiasing)
                win.draw(p2, w, h, ctx)
                p2.end()
                self._win_cache[wid] = pix
            painter.drawPixmap(0, 0, self._win_cache[wid])
        else:
            self._win_cache.pop(wid, None)
            win.draw(painter, w, h, ctx)

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
        mx, my = event.position().x(), event.position().y()
        for win in self._windows:
            win.mouse_move(mx, my, self.width(), self.height())

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton: return
        mx, my = event.position().x(), event.position().y()
        for win in self._windows:
            if win.mouse_release(mx, my, self.width(), self.height()): break

    def leaveEvent(self, event):
        for win in self._windows: win.mouse_leave()

    def resizeEvent(self, event):
        self._win_cache.clear()
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        if not painter.isActive():
            painter.end()
            return
        painter.setClipRegion(event.region())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.NoPen)

        w, h = self.width(), self.height()
        ctx  = self._context()

        for win in self._windows:
            self._draw_with_cache(painter, win, w, h, ctx)

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