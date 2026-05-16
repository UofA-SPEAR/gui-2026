from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QEasingCurve
from PySide6.QtGui  import QColor

from spear_gui.overlay_system import (
    AnimatedPolygon, AnimatedText,
    PolygonDef, PolygonTween, TextDef, TextTween, TextBlock,
    Phase, Reset, P, Rect, RectTween,
    expand_defs,
    GraphDef, SeriesDef, AnimatedGraph, PieDef, AnimatedPie,
    AttributeDef, SliderGroupDef, SliderDef, SliderGroup,
    make_track_def, make_knob_def, make_mark_fill_def, make_mark_tick_def,
    SliderTextDefs,
    ButtonDef, AnimatedButton, ButtonDiamond,
    WindowDef, WindowPhase, WindowTween, AnimatedWindow,
    EventDef,
)

# ──────────────────────── EVENT DEFS ────────────────────────

MAIN_EVENT_DEFS = [
    EventDef(name='graph_steps', value=4),
    EventDef(name='graph_stack', value=True),
    EventDef(name='graph_time',  value=10.0),
    EventDef(name='window1_phase', value='open'),
    EventDef(name='window2_phase', value='open'),
    EventDef(name='window3_phase', value='open'),
]

_ev = {e.name: e for e in MAIN_EVENT_DEFS}

MAIN_POLYGON_DEFS = expand_defs([])
MAIN_GRAPH_DEFS   = []
MAIN_PIE_DEFS     = []
MAIN_TEXT_DEFS    = []

# ──────────────────────── WINDOW DEFS ────────────────────────

MAIN_WINDOW_DEFS = [
    WindowDef(
        p1=P(0.50, 0.00), p2=P(1.00, 0.50),
        phase_event=_ev['window3_phase'],
        phases={
            'phase1':  WindowPhase([WindowTween(p1=P(0.00, 0.50), p2=P(0.50, 1.00), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)]),
            'phase2': WindowPhase([WindowTween(p1=P(0.00, 0.00), p2=P(0.30, 0.30), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)]),
            'phase3':  WindowPhase([WindowTween(p1=P(0.00, 0.00), p2=P(1.00, 0.25), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)]),
        },
        polygon_defs=[
            Rect(p1=P(0.00, 0.00), p2=P(1.00, 1.00), fill_color=QColor(255, 255, 255, 50)),
            Rect(p1=P(0.50, 0.50), p2=P(0.50, 0.50), px1=P(-5, -5), px2=P(5, 5), fill_color=QColor(255, 0, 0, 255)),
            Rect(p1=P(0.20, 0.20), p2=P(0.40, 0.40), fill_color=QColor(0, 255, 0, 255)),
            Rect(p1=P(0.60, 0.20), p2=P(0.80, 0.40), fill_color=QColor(0, 0, 0, 0), outline_color=QColor(0, 0, 255, 255), line_width=2),
            PolygonDef(points=[P(0.50, 0.60), P(0.30, 0.80), P(0.70, 0.80)], fill_color=QColor(255, 255, 0, 255))
        ],
        text_defs=[
            TextDef(x=0.50, y=0.00, text='This is a single text', font_size=9.0, color=QColor(255, 255, 255, 255), h_align=0.5, v_align=0.0),
            TextDef(x=0.50, y=0.10, text='Test Value 1: <#>', font_size=9.0, color=QColor(255, 255, 255, 255), h_align=0.5, v_align=0.0,
            text_fn=lambda ctx: (f"{ctx['test_value1']['latest']:.4f}" if ctx and ctx['test_value1']['latest'] is not None else "-")),
            *TextBlock(x=0.00, y=0.90, text='This is a block of text\nThis appears in another line.\nThis appears on the last line.', font_size=9.0, color=QColor(255, 255, 255, 255), h_align=0.0, v_align=0.5)
        ],
    ),

    WindowDef(
        p1=P(0.00, 0.50), p2=P(0.50, 1.00),
        phase_event=_ev['window1_phase'],
        phases={
            'phase1':  WindowPhase([WindowTween(p1=P(0.00, 0.50), p2=P(0.50, 1.00), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)]),
            'phase2': WindowPhase([WindowTween(p1=P(0.00, 0.00), p2=P(0.30, 0.30), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)]),
            'phase3':  WindowPhase([WindowTween(p1=P(0.00, 0.00), p2=P(1.00, 0.25), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)]),
        },
        polygon_defs=[
            PolygonDef(
                points=[P(0.0, 0.0), P(1.0, 0.0), P(1.0, 1.0), P(0.0, 1.0)],
                fill_color=QColor(20, 20, 20, 255),
                phases={
                    'phase1':  Phase([PolygonTween(points=[P(0.0,0.0), P(1.0,0.0), P(1.0,1.0), P(0.0,1.0)],
                                    fill_color=QColor(20, 20, 20, 255),
                                    start=0.0, dur=1.0, ease=QEasingCurve.OutQuint)]),
                    'phase2': Phase([PolygonTween(points=[P(0.0,0.0), P(1.0,0.0), P(1.0,1.0), P(0.0,1.0)],
                                    fill_color=QColor(40, 0, 40, 255),
                                    start=0.0, dur=1.0, ease=QEasingCurve.InQuint)]),
                },
            ),
        ],
        text_defs=[
            TextDef(x=0.50, y=0.00, text='POWER CONSUMPTION', font_size=9.0,
                    color=QColor(255, 255, 255, 0),
                    phases={
                        'phase1':  Phase([TextTween(0.50, 0.00, 0.00, 1.00, QEasingCurve.OutQuint, QColor(255, 255, 255, 255), 0.5, 0.0, 9.0)]),
                        'phase2': Phase([TextTween(0.50, 0.00, 0.00, 1.00, QEasingCurve.OutQuint, QColor(255, 0, 255, 255), 0.5, 0.0, 9.0)]),
                    },
                    h_align=0.5, v_align=0.0),
            TextDef(x=0.50, y=0.90, text='kWh: <#>', font_size=9.0,
                    color=QColor(255, 255, 255, 255),
                    phases={
                        'phase1':  Phase([TextTween(0.50, 0.90, 0.00, 1.00, QEasingCurve.OutQuint, QColor(255, 255, 255, 255), 0.5, 1.0, 9.0)]),
                        'phase2': Phase([TextTween(0.50, 0.90, 0.00, 1.00, QEasingCurve.OutQuint, QColor(255, 0, 255, 255), 0.5, 1.0, 9.0)]),
                    },
                    h_align=0.5, v_align=1.0,
                    text_fn=lambda ctx: (
                        f"{sum(ctx[f'test_value{i}']['average'] for i in range(1, 10)):.4f}"
                        if ctx and ctx['test_value1']['average'] is not None else "-"
                    )),
        ],
        graph_defs=[
            GraphDef(
                p1=P(0.00, 0.05), p2=P(1.00, 0.85),
                series=[
                    SeriesDef(value_fn=lambda ctx: ctx['test_value1']['latest'], color=QColor(255, 106, 106, 255), line_width=1.0, fill_opacity=0.08),
                    SeriesDef(value_fn=lambda ctx: ctx['test_value2']['latest'], color=QColor(255, 111, 151, 255), line_width=1.0, fill_opacity=0.08),
                    SeriesDef(value_fn=lambda ctx: ctx['test_value3']['latest'], color=QColor(255, 126, 192, 255), line_width=1.0, fill_opacity=0.08),
                    SeriesDef(value_fn=lambda ctx: ctx['test_value4']['latest'], color=QColor(238, 145, 227, 255), line_width=1.0, fill_opacity=0.08),
                    SeriesDef(value_fn=lambda ctx: ctx['test_value5']['latest'], color=QColor(214, 165, 252, 255), line_width=1.0, fill_opacity=0.08),
                    SeriesDef(value_fn=lambda ctx: ctx['test_value6']['latest'], color=QColor(187, 184, 255, 255), line_width=1.0, fill_opacity=0.08),
                    SeriesDef(value_fn=lambda ctx: ctx['test_value7']['latest'], color=QColor(164, 200, 255, 255), line_width=1.0, fill_opacity=0.08),
                    SeriesDef(value_fn=lambda ctx: ctx['test_value8']['latest'], color=QColor(150, 213, 255, 255), line_width=1.0, fill_opacity=0.08),
                    SeriesDef(value_fn=lambda ctx: ctx['test_value9']['latest'], color=QColor(149, 224, 255, 255), line_width=1.0, fill_opacity=0.08),
                ],
                max_time=lambda: float(_ev['graph_time'].value),
                value_range=(0.0, 100.0),
                value_color=QColor(255, 255, 255, 255),
                ease_dur=0.3,
                ease_type=QEasingCurve.OutQuint,
                dynamic_scale=5.0,
                show_minmax = True,
                show_step = True,
                step_count = lambda: int(_ev['graph_steps'].value),
                label_align='left',
                stack=lambda: bool(_ev['graph_stack'].value),
                update_interval=1,
            ),
        ],
        pie_defs=[
            PieDef(
                p1=P(0.00, 0.93), p2=P(1.00, 0.95),
                names=[''] * 9,
                value_fns=[lambda ctx, i=i: ctx[f'test_value{i+1}']['latest'] for i in range(9)],
                colors=[QColor(255,106,106), QColor(255,111,151), QColor(255,126,192),
                        QColor(238,145,227), QColor(214,165,252), QColor(187,184,255),
                        QColor(164,200,255), QColor(150,213,255), QColor(149,224,255)],
                border_width=1.0, fill_opacity=0.1, direction='horizontal',
                size_label=0.0, size_name=9.0, ease_dur=0.4, ease_type=QEasingCurve.OutQuint,
            ),
            PieDef(
                p1=P(0.00, 0.95), p2=P(1.00, 1.00),
                names=[''] * 9,
                value_fns=[lambda ctx, i=i: ctx[f'test_value{i+1}']['average'] for i in range(9)],
                colors=[QColor(255,106,106), QColor(255,111,151), QColor(255,126,192),
                        QColor(238,145,227), QColor(214,165,252), QColor(187,184,255),
                        QColor(164,200,255), QColor(150,213,255), QColor(149,224,255)],
                border_width=1.0, fill_opacity=0.1, direction='horizontal',
                size_label=9.0, size_name=9.0, ease_dur=0.4, ease_type=QEasingCurve.OutQuint,
            ),
        ],
    ),

    WindowDef(
        p1=P(0.50, 0.50), p2=P(1.00, 1.00),
        phase_event=_ev['window2_phase'],
        slider_defs=[
            SliderDef(x=0.20, y=0.40, lx=0.60, attr=AttributeDef(value_fn=lambda ctx: _ev['graph_steps'].value, set_fn  =lambda ctx, v: None, min_val=0, max_val=10, step=1, label='GRAPH STEPS', unit=''), event_out=_ev['graph_steps']),
            SliderDef(x=0.20, y=0.60, lx=0.60, attr=AttributeDef(value_fn=lambda ctx: _ev['graph_time'].value, set_fn  =lambda ctx, v: None, min_val=1, max_val=60, step=1, label='GRAPH TIME', unit='s'), event_out=_ev['graph_time']),
        ],
        button_defs=[
            ButtonDef(
                poly=ButtonDiamond(p=P(0.25, 0.25), px=P(0, 0), size=40),
                label='+', text_color=QColor(160, 255, 160, 255),
                action='increment', event_out=_ev['graph_steps'], event_delta=1,
            ),
            ButtonDef(
                poly=ButtonDiamond(p=P(0.50, 0.25), px=P(0, 0), size=40),
                label='−', text_color=QColor(255, 160, 160, 255),
                action='increment', event_out=_ev['graph_steps'], event_delta=-1,
            ),
            ButtonDef(
                poly=ButtonDiamond(p=P(0.75, 0.25), px=P(0, 0), size=40),
                label='set', text_color=QColor(255, 255, 255, 220),
                action='set', event_out=_ev['graph_steps'], event_delta=4,
            ),
            ButtonDef(
                poly=ButtonDiamond(p=P(0.25, 0.75), px=P(0, 0), size=40),
                label='1', text_color=QColor(255, 255, 255, 220),
                action='set', event_out=_ev['window1_phase'], event_delta='phase1',
            ),
            ButtonDef(
                poly=ButtonDiamond(p=P(0.50, 0.75), px=P(0, 0), size=40),
                label='2', text_color=QColor(255, 255, 255, 220),
                action='set', event_out=_ev['window1_phase'], event_delta='phase2',
            ),
            ButtonDef(
                poly=ButtonDiamond(p=P(0.75, 0.75), px=P(0, 0), size=40),
                label='3', text_color=QColor(255, 255, 255, 220),
                action='set', event_out=_ev['window1_phase'], event_delta='phase3',
            ),
        ],
    ),
]
