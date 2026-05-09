from __future__ import annotations

import random
import sys
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt, QTimer, QEasingCurve
from PySide6.QtGui import QColor, QPainter, QFontDatabase, QFont

import collections
import statistics
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
import time


from spear_gui.overlay_system import (
    AnimatedPolygon, AnimatedText,
    PolygonDef, PolygonTween, TextDef, TextTween,
    Phase, Reset, P, Rect, RectTween,
    expand_defs,
    GraphDef, SeriesDef, AnimatedGraph, PieDef, AnimatedPie, WindowDef, AnimatedWindow
)

class DataChannel:
    def __init__(self, name: str, max_samples: int = 100, unit: str = '') -> None:
        self.name        = name
        self.max_samples = max_samples
        self.unit        = unit
        self._lock   = threading.Lock()
        self._buffer: collections.deque[float] = collections.deque(maxlen=max_samples)

    def push(self, value: float) -> None:
        with self._lock:
            self._buffer.append(value)

    @property
    def latest(self) -> Optional[float]:
        with self._lock:
            return self._buffer[-1] if self._buffer else None

    @property
    def samples(self) -> List[float]:
        with self._lock:
            return list(self._buffer)

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._buffer)

    def average(self) -> Optional[float]:
        with self._lock:
            data = list(self._buffer)
        return statistics.mean(data) if data else None

    def minimum(self) -> Optional[float]:
        with self._lock:
            return min(self._buffer) if self._buffer else None

    def maximum(self) -> Optional[float]:
        with self._lock:
            return max(self._buffer) if self._buffer else None

    def delta(self) -> Optional[float]:
        with self._lock:
            if len(self._buffer) < 2:
                return None
            return self._buffer[-1] - self._buffer[-2]

    def trend(self) -> Optional[float]: # Linear-regression slope
        with self._lock:
            data = list(self._buffer)
        n = len(data)
        if n < 2:
            return None
        xs    = range(n)
        x_bar = (n - 1) / 2.0
        y_bar = sum(data) / n
        num   = sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, data))
        den   = sum((x - x_bar) ** 2 for x in xs)
        return num / den if den else 0.0

    def snapshot(self) -> Dict[str, Any]:
        data = self.samples
        n    = len(data)

        avg = statistics.mean(data) if data else None
        mn  = min(data)             if data else None
        mx  = max(data)             if data else None
        dlt = (data[-1] - data[-2]) if n >= 2 else None
        lat = data[-1]              if data else None

        if n >= 2:
            x_bar = (n - 1) / 2.0
            y_bar = avg
            num   = sum((x - x_bar) * (y - y_bar) for x, y in enumerate(data))
            den   = sum((x - x_bar) ** 2 for x in range(n))
            slope = num / den if den else 0.0
        else:
            slope = None

        return {
            'latest':  lat,
            'average': avg,
            'minimum': mn,
            'maximum': mx,
            'delta':   dlt,
            'trend':   slope,
            'samples': data,
            'count':   n,
            'unit':    self.unit,
        }

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

            def _make_callback(ch: DataChannel, ex: Callable) -> Callable:
                def _cb(msg):
                    try:
                        ch.push(ex(msg))
                    except Exception as e:
                        node.get_logger().warn(f'[SubscriptionManager] extractor error on {ch.name}: {e}')
                return _cb

            sub = node.create_subscription(
                cfg.msg_type,
                cfg.topic,
                _make_callback(channel, cfg.extractor),
                cfg.qos,
            )
            self._subs.append(sub)

    def channel(self, name: str) -> Optional[DataChannel]:
        return self._channels.get(name)

    def context(self) -> Dict[str, Dict[str, Any]]:
        return {name: ch.snapshot() for name, ch in self._channels.items()}

    def all_channels(self) -> Dict[str, DataChannel]:
        return dict(self._channels)

LOG_CAPACITY = 50
 
MAIN_POLYGON_DEFS = expand_defs([
    PolygonDef(
        points=[P(0.50,0.50), P(0.50,0.50), P(0.50,0.50), P(0.50,0.50)],
        px=    [P(0,0),  P(0,0),   P(0,0),    P(0,0)],
        fill_color=QColor(50,50,50,255), outline_color=QColor(255,255,255,255),
        closed=True, line_width=2, d_flip=True,
        phases={
            # 'open':  Phase([Reset(),
            #                 PolygonTween(
            #                     points=[P(0.50,0.50), P(0.50,0.50), P(0.50,0.50), P(0.50,0.50)],
            #                     px=[P(-250,-50), P(250,-50), P(250,0), P(-250,0)],
            #                     fill_color=QColor(50,50,50,255),
            #                     outline_color=QColor(255,255,255,255),
            #                     start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)]),
            # 'close': Phase([Reset()]),
        }
    ),
])


MAIN_GRAPH_DEFS = [
    GraphDef(
        p1=P(0.00, 0.00), p2=P(1.00, 0.80),
        series=[
            SeriesDef(
                value_fn=lambda ctx: ctx['test_value1']['latest'],
                color=QColor(255, 106, 106, 255),
                line_width=1.0,
                fill_opacity=0.08,
            ),
            SeriesDef(
                value_fn=lambda ctx: ctx['test_value2']['latest'],
                color=QColor(255, 111, 151, 255),
                line_width=1.0,
                fill_opacity=0.08,
            ),
            SeriesDef(
                value_fn=lambda ctx: ctx['test_value3']['latest'],
                color=QColor(255, 126, 192, 255),
                line_width=1.0,
                fill_opacity=0.08,
            ),
            SeriesDef(
                value_fn=lambda ctx: ctx['test_value4']['latest'],
                color=QColor(238, 145, 227, 255),
                line_width=1.0,
                fill_opacity=0.08,
            ),
            SeriesDef(
                value_fn=lambda ctx: ctx['test_value5']['latest'],
                color=QColor(214, 165, 252, 255),
                line_width=1.0,
                fill_opacity=0.08,
            ),
            SeriesDef(
                value_fn=lambda ctx: ctx['test_value6']['latest'],
                color=QColor(187, 184, 255, 255),
                line_width=1.0,
                fill_opacity=0.08,
            ),
            SeriesDef(
                value_fn=lambda ctx: ctx['test_value7']['latest'],
                color=QColor(164, 200, 255, 255),
                line_width=1.0,
                fill_opacity=0.08,
            ),
            SeriesDef(
                value_fn=lambda ctx: ctx['test_value8']['latest'],
                color=QColor(150, 213, 255, 255),
                line_width=1.0,
                fill_opacity=0.08,
            ),
            SeriesDef(
                value_fn=lambda ctx: ctx['test_value9']['latest'],
                color=QColor(149, 224, 255, 255),
                line_width=1.0,
                fill_opacity=0.08,
            ),
        ],
        max_time=10.0,
        value_range=(0.0, 100.0),
        value_color=QColor(255, 255, 255, 255),
        ease_dur=0.3,
        ease_type=QEasingCurve.OutQuint,
        dynamic_scale=5.0,
        range_labels=(True, True, 4),
        label_sizes=(10.0, 9.0),
        label_align='left',
        stack=False,
        update_interval=0.5
    ),
]

MAIN_PIE_DEFS = [
    PieDef(
        p1=P(0.00, 0.85), p2=P(1.00, 0.90),
        names=['', '', '', '', '', '', '', '', ''],
        value_fns=[
            lambda ctx: ctx['test_value1']['latest'],
            lambda ctx: ctx['test_value2']['latest'],
            lambda ctx: ctx['test_value3']['latest'],
            lambda ctx: ctx['test_value4']['latest'],
            lambda ctx: ctx['test_value5']['latest'],
            lambda ctx: ctx['test_value6']['latest'],
            lambda ctx: ctx['test_value7']['latest'],
            lambda ctx: ctx['test_value8']['latest'],
            lambda ctx: ctx['test_value9']['latest'],
        ],
        colors=[QColor(255, 106, 106), QColor(255, 111, 151), QColor(255, 126, 192), QColor(238, 145, 227), QColor(214, 165, 252), QColor(187, 184, 255), QColor(164, 200, 255), QColor(150, 213, 255), QColor(149, 224, 255)],
        border_width=1.0,
        fill_opacity=0.1,
        direction='horizontal',
        label_size=9.0,
        name_size=9.0,
        ease_dur=0.4,
        ease_type=QEasingCurve.OutQuint,
    ),
    PieDef(
        p1=P(0.00, 0.95), p2=P(1.00, 1.00),
        names=['', '', '', '', '', '', '', '', ''],
        value_fns=[
            lambda ctx: ctx['test_value1']['average'],
            lambda ctx: ctx['test_value2']['average'],
            lambda ctx: ctx['test_value3']['average'],
            lambda ctx: ctx['test_value4']['average'],
            lambda ctx: ctx['test_value5']['average'],
            lambda ctx: ctx['test_value6']['average'],
            lambda ctx: ctx['test_value7']['average'],
            lambda ctx: ctx['test_value8']['average'],
            lambda ctx: ctx['test_value9']['average'],
        ],
        colors=[QColor(255, 106, 106), QColor(255, 111, 151), QColor(255, 126, 192), QColor(238, 145, 227), QColor(214, 165, 252), QColor(187, 184, 255), QColor(164, 200, 255), QColor(150, 213, 255), QColor(149, 224, 255)],
        border_width=1.0,
        fill_opacity=0.1,
        direction='horizontal',
        label_size=9.0,
        name_size=9.0,
        ease_dur=0.4,
        ease_type=QEasingCurve.OutQuint,
    ),
]
 
MAIN_TEXT_DEFS = [
    TextDef(0.50, 0.45, 'Value <#>', 24.0, QColor(255,255,255,255), {
        'open':  Phase([Reset()]),
        'close': Phase([Reset()]),
    }, True, False, 'Oxanium SemiBold', 0.50, 0.50, False, 0, 0,
        lambda ctx: (
            f"{ctx['test_value3']['latest']:.4f} {ctx['test_value3']['unit']}"
            if ctx and ctx['test_value3']['latest'] is not None else "-"
        ), True),
    
    TextDef(0.00, 0.50, 'Range <#>', 12.0, QColor(255,255,255,255), {
        'open':  Phase([Reset()]),
        'close': Phase([Reset()]),
    }, True, False, 'Oxanium SemiBold', 0.00, 0.50, False, 0, 0,
        lambda ctx: (
            f"{ctx['test_value1']['minimum']:.4f} {ctx['test_value1']['maximum']:.4f}"
            if ctx and ctx['test_value1']['minimum'] is not None and ctx['test_value1']['maximum'] is not None else "-"
        ), True),
 
    TextDef(0.00, 0.55, 'Average <#>', 12.0, QColor(255,255,255,255), {
        'open':  Phase([Reset()]),
        'close': Phase([Reset()]),
    }, True, False, 'Oxanium SemiBold', 0.00, 0.50, False, 0, 0,
        lambda ctx: (
            f"{ctx['test_value1']['average']:.4f}  [{ctx['test_value1']['count']}/{LOG_CAPACITY}]"
            if ctx and ctx['test_value1']['average'] is not None else "-"
        ), True),
 
    TextDef(0.00, 0.60, 'Delta <#>', 12.0, QColor(255,255,255,255), {
        'open':  Phase([Reset()]),
        'close': Phase([Reset()]),
    }, True, False, 'Oxanium SemiBold', 0.00, 0.50, False, 0, 0,
        lambda ctx: (
            f"{ctx['test_value1']['delta']:+.4f}"
            if ctx and ctx['test_value1']['delta'] is not None else "-"
        ), True),

    TextDef(0.00, 0.65, 'Trend <#>', 12.0, QColor(255,255,255,255), {
        'open':  Phase([Reset()]),
        'close': Phase([Reset()]),
    }, True, False, 'Oxanium SemiBold', 0.00, 0.50, False, 0, 0,
        lambda ctx: (
            f"{ctx['test_value1']['trend']:+.4f}"
            if ctx and ctx['test_value1']['trend'] is not None else "-"
        ), True),
 
    TextDef(0.50, 0.9, 'Power Usage <#>', 10.0, QColor(255,160,160,255), {
        'open':  Phase([Reset()]),
        'close': Phase([Reset()]),
    }, True, False, 'Oxanium SemiBold', 0.50, 0.50, False, 0, 0,
        lambda ctx: (
            f"{ctx['test_value2']['latest']:.2f} {ctx['test_value2']['unit']}"
            if ctx and ctx['test_value2']['latest'] is not None else "-"
        ), True),
]


MAIN_WINDOW_DEFS = [
    AnimatedWindow(
        WindowDef(p1=P(0.0, 0.5), p2=P(0.5, 1.0)),
        graph_defs=MAIN_GRAPH_DEFS,
        pie_defs=MAIN_PIE_DEFS,
    )
]

 
SUBSCRIPTION_CONFIGS = [
    SubscriptionConfig(
        topic='main/test_value1',
        channel_name='test_value1',
        msg_type=Float64,
        extractor=lambda msg: float(msg.data),
        max_samples=LOG_CAPACITY,
        unit='',
    ),
    SubscriptionConfig(
        topic='main/test_value2',
        channel_name='test_value2',
        msg_type=Float64,
        extractor=lambda msg: float(msg.data),
        max_samples=LOG_CAPACITY,
        unit='',
    ),
    SubscriptionConfig(
        topic='main/test_value3',
        channel_name='test_value3',
        msg_type=Float64,
        extractor=lambda msg: float(msg.data),
        max_samples=LOG_CAPACITY,
        unit='',
    ),
    SubscriptionConfig(
        topic='main/test_value4',
        channel_name='test_value4',
        msg_type=Float64,
        extractor=lambda msg: float(msg.data),
        max_samples=LOG_CAPACITY,
        unit='',
    ),
    SubscriptionConfig(
        topic='main/test_value5',
        channel_name='test_value5',
        msg_type=Float64,
        extractor=lambda msg: float(msg.data),
        max_samples=LOG_CAPACITY,
        unit='',
    ),
    SubscriptionConfig(
        topic='main/test_value6',
        channel_name='test_value6',
        msg_type=Float64,
        extractor=lambda msg: float(msg.data),
        max_samples=LOG_CAPACITY,
        unit='',
    ),
    SubscriptionConfig(
        topic='main/test_value7',
        channel_name='test_value7',
        msg_type=Float64,
        extractor=lambda msg: float(msg.data),
        max_samples=LOG_CAPACITY,
        unit='',
    ),
    SubscriptionConfig(
        topic='main/test_value8',
        channel_name='test_value8',
        msg_type=Float64,
        extractor=lambda msg: float(msg.data),
        max_samples=LOG_CAPACITY,
        unit='',
    ),
    SubscriptionConfig(
        topic='main/test_value9',
        channel_name='test_value9',
        msg_type=Float64,
        extractor=lambda msg: float(msg.data),
        max_samples=LOG_CAPACITY,
        unit='',
    ),
]
 
 
class MainNode(Node):
    def __init__(self):
        super().__init__('main_overlay_node')
        self.test_publishers = [
            self.create_publisher(Float64, 'main/test_value1', 10),
            self.create_publisher(Float64, 'main/test_value2', 10),
            self.create_publisher(Float64, 'main/test_value3', 10),
            self.create_publisher(Float64, 'main/test_value4', 10),
            self.create_publisher(Float64, 'main/test_value5', 10),
            self.create_publisher(Float64, 'main/test_value6', 10),
            self.create_publisher(Float64, 'main/test_value7', 10),
            self.create_publisher(Float64, 'main/test_value8', 10),
            self.create_publisher(Float64, 'main/test_value9', 10),
        ]
 
        self.create_timer(0.1, self._publish_demo)
 
        self.sub_manager = SubscriptionManager(self, SUBSCRIPTION_CONFIGS)
 
    def _publish_demo(self):
        msg = Float64()
        msg.data = random.uniform(1.0, 10.0)
        self.test_publishers[0].publish(msg)

        msg.data = random.uniform(2.0, 20.0)
        self.test_publishers[1].publish(msg)

        msg.data = random.uniform(5.0, 10.0)
        self.test_publishers[2].publish(msg)

        msg.data = random.uniform(9.0, 11.0)
        self.test_publishers[3].publish(msg)

        msg.data = random.uniform(1, 10.0) + random.uniform(0.1, 1.1) ** 50
        self.test_publishers[4].publish(msg)

        msg.data = random.uniform(20, 70)
        self.test_publishers[5].publish(msg)

        msg.data = round(random.uniform(0, 1)) * 10.0 + 10.0
        self.test_publishers[6].publish(msg)

        msg.data = random.uniform(12, 55)
        self.test_publishers[7].publish(msg)

        msg.data = random.uniform(24, 77)
        self.test_publishers[8].publish(msg)
 
 
class MainOverlayWidget(QWidget):
    TICK_MS = 16
 
    def __init__(self, node: MainNode, parent=None):
        super().__init__(parent)
        self._node = node
 
        self.setMinimumSize(640, 400)
        self.resize(800, 500)
        self.setStyleSheet('background-color: #0a0c12;')
        self.setWindowTitle('Main Overlay')
 
        self._polygons = [AnimatedPolygon(d) for d in MAIN_POLYGON_DEFS]
        self._texts    = [AnimatedText(d)    for d in MAIN_TEXT_DEFS]
        self._graphs   = [AnimatedGraph(d)   for d in MAIN_GRAPH_DEFS]
        self._pies     = [AnimatedPie(d) for d in MAIN_PIE_DEFS]
 
        self._broadcast('open')
 
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(self.TICK_MS)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start()

        self._windows = MAIN_WINDOW_DEFS
 
    def _broadcast(self, phase: str):
        for p in self._polygons: p.set_phase(phase)
        for t in self._texts:    t.set_phase(phase)
 
    def _context(self) -> dict:
        return self._node.sub_manager.context()
 
    def _tick(self):
        now = time.monotonic()
        ctx = self._context()
        for w in self._windows:
            w.tick(now)
            w.update(ctx)
        for p in self._polygons: p.update()
        for t in self._texts:    t.update()
        self.update()
 
    def paintEvent(self, event):
        painter = QPainter(self)
        if not painter.isActive():
            painter.end()
            return
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        w, h = self.width(), self.height()
        ctx  = self._context()
        for poly in self._polygons:
            poly.draw(painter, w, h)
        for text in self._texts:
            if text.hidden: continue
            label = text.resolve_text(ctx)
            if not label: continue
            font = text.build_font()
            painter.setFont(font)
            painter.setPen(text.cur_color)
            dx, dy = text.resolve_pos(w, h, 1920, 1080, label, font)
            painter.drawText(dx, dy, label)
            painter.setPen(Qt.NoPen)
        for win in self._windows:
            win.draw(painter, w, h, ctx)
        painter.end()
 
def main():
    rclpy.init()
    node = MainNode()
 
    app = QApplication(sys.argv)
 
    import os
    font_path = os.path.join(os.path.dirname(__file__), 'Oxanium-VariableFont.ttf')
    if os.path.exists(font_path):
        QFontDatabase.addApplicationFont(font_path)
 
    widget = MainOverlayWidget(node)
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
 