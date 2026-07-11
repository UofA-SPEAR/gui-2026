from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Tuple
import math

from PySide6.QtCore import Qt, QEasingCurve
from PySide6.QtGui  import QColor

from spear_gui.overlay_system import (
    P, Reset, Phase, expand_defs,
    PolygonDef, PolygonTween, RectDef, RectTween,                              # PolygonDef
    ArcDef,                                                                    # ArcDef
    TextDef, TextTween, TextBlock, DataTable,                                  # TextDef
    SliderDef,                                                                 # SliderDef
    ButtonDef, SegmentedButtons, Segment, SevenSegmentDisplay,                 # ButtonDef
    TextboxDef,                                                                # TextboxDef
    GraphDef, SeriesDef,                                                       # GraphDef
    PieDef,                                                                    # PieDef
    WindowDef, WindowTween, register_windows,                                  # WindowDef
    EventDef, EventListener, register_event, get_event,                        # EventDef
    GradientDef, GradientStop, GradientTween, register_gradient, get_gradient, # GradientDef

    P_OPEN, P_CLOSE, P_HOVER, P_UNHOVER, P_CLICK, P_RELEASE, P_SET, P_ALWAYS,
    SYS_FPS, SYS_FRAME_TIME, SYS_MOUSE, SYS_MOUSE_X, SYS_MOUSE_Y,
    get_spawn_event, GROUP_EVENT, STATIC, get_spawn_mouse_norm
)

WINDOW_LAYER = 1

WINDOW_DEFS = [
    WindowDef(
        p1=P(1.1, 0.0), p2=P(1.6, 1.0),
        phase_event=get_event('main_page'),
        phases={
            'open': Phase([WindowTween(p1=P(0.5, 0.0), p2=P(1.0, 1.0), start=0.0, dur=1.0, ease=QEasingCurve.OutQuint)])
        },
        polygon_defs=[
            # RectDef(p1=P(0, 0), p2=P(1, 1), fill_color=QColor(255, 255, 255, 0), outline_width=5, gradient=get_gradient('alt_color_outline'))
            PolygonDef(p=[P(0, 0), P(0, 0), P(0, 0), P(0, 1), P(0, 1), P(0, 1)], px=[P(0, 50), P(5, 50 - 5), P(10, 50), P(10, -50), P(5, -50 + 5), P(0, -50)], gradient=get_gradient('alt_color_fill'))
        ],
        text_defs=[
            # TextDef(p=P(0, 0), px=P(1, 1), text='TASKS', font_size=100, bold=True, italic=True, h_align=0.0, v_align=0.0, fill_color=QColor(255, 255, 255, 150), outline_color=QColor(255, 255, 255, 255), outline_width=2, uniform_scale=False),
            TextDef(p=P(0.5, 0.1), px=P(0, 60), font_size=15, h_align=0, v_align=0, text='Roll:   <#> °', text_fn= lambda ctx: f"{ctx['test_value4']['push_count']:.2f}", uniform_scale=False),
        ]
    )
]

register_windows(WINDOW_LAYER, WINDOW_DEFS)
