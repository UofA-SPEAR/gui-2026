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
    get_spawn_event, GROUP_EVENT, STATIC, get_spawn_mouse_norm, get_spawn_mouse_offset_px
)

register_event(EventDef(name="graph_time", value=10.0))
register_event(EventDef(name="graph_steps", value=4))

WINDOW_LAYER = 0

info_window = WindowDef(
    p1=P(0.0, 0.6), p2=P(0.5, 1.0), px1=P(0, 0), px2=P(-157, 0),
    phase_event=get_event('main_page'),
    phases={
        'open': Phase([WindowTween(p1=get_event('info_window_p1'), p2=get_event('info_window_p2'), px1=get_event('info_window_px1'), px2=get_event('info_window_px2'), start=0.0, dur=1.0, ease=QEasingCurve.OutQuint)], update_retrigger=True)
    },
    polygon_defs=[
        PolygonDef(p=[P(1, 1), P(1, 1)], px=[P(0, 0), P(0, 0)], fill_color=QColor(255, 255, 255, 0), outline_width=2, closed=False, gradient=get_gradient('alt_color_outline'), phase_override=get_event('main_page'), phases={
            'open': Phase([PolygonTween(p=[P(0, 0), P(1, 0)], px=[P(0, 0), P(0, 0)], start=1.0, dur=0.5, ease=QEasingCurve.OutQuint)])
        },)
    ],
    graph_defs=[
        GraphDef(
            p1=P(0.00, 0.05), p2=P(1.00, 0.85),
            series=[
                SeriesDef(value_fn=lambda ctx: ctx['test_value1']['latest'], color=QColor(255, 106, 106, 255), outline_width=1.0, fill_opacity=0.08),
                SeriesDef(value_fn=lambda ctx: ctx['test_value2']['latest'], color=QColor(255, 111, 151, 255), outline_width=1.0, fill_opacity=0.08),
                SeriesDef(value_fn=lambda ctx: ctx['test_value3']['latest'], color=QColor(255, 126, 192, 255), outline_width=1.0, fill_opacity=0.08),
                SeriesDef(value_fn=lambda ctx: ctx['test_value4']['latest'], color=QColor(238, 145, 227, 255), outline_width=1.0, fill_opacity=0.08),
                SeriesDef(value_fn=lambda ctx: ctx['test_value5']['latest'], color=QColor(214, 165, 252, 255), outline_width=1.0, fill_opacity=0.08),
                SeriesDef(value_fn=lambda ctx: ctx['test_value6']['latest'], color=QColor(187, 184, 255, 255), outline_width=1.0, fill_opacity=0.08),
                SeriesDef(value_fn=lambda ctx: ctx['test_value7']['latest'], color=QColor(164, 200, 255, 255), outline_width=1.0, fill_opacity=0.08),
                SeriesDef(value_fn=lambda ctx: ctx['test_value8']['latest'], color=QColor(150, 213, 255, 255), outline_width=1.0, fill_opacity=0.08),
                SeriesDef(value_fn=lambda ctx: ctx['test_value9']['latest'], color=QColor(149, 224, 255, 255), outline_width=1.0, fill_opacity=0.08),
            ],
            max_time=lambda: float(get_event('graph_time').value),
            value_range=(0.0, 100.0),
            value_color=QColor(255, 255, 255, 255),
            ease_dur=0.3,
            ease_type=QEasingCurve.OutQuint,
            dynamic_scale=5.0,
            show_minmax = True,
            show_step = True,
            step_count = lambda: int(get_event('graph_steps').value),
            label_align='left',
            stack=True,
            update_interval=1,
        ),
    ],
)

WINDOW_DEFS = []
WINDOW_DEFS.append(info_window)

register_windows(WINDOW_LAYER, WINDOW_DEFS)