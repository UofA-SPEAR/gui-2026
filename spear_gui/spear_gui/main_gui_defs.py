from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, QEasingCurve
from PySide6.QtGui  import QColor

from spear_gui.overlay_system import (
    AnimatedPolygon, AnimatedText,
    PolygonDef, PolygonTween, TextDef, TextTween, TextBlock, DataTable,
    Phase, Reset, P, Rect, RectTween,
    expand_defs,
    GraphDef, SeriesDef, AnimatedGraph, PieDef, AnimatedPie,
    AttributeDef, SliderGroupDef, SliderDef, SliderGroup,
    make_track_def, make_knob_def, make_mark_fill_def, make_mark_tick_def,
    SliderTextDefs,
    ButtonDef, AnimatedButton, ButtonDiamond,
    WindowDef, WindowPhase, WindowTween, AnimatedWindow,
    EventDef, EventListener,
    GradientDef, GradientStop, GradientTween,
)

# ──────────────────────── EVENT DEFS ────────────────────────

MAIN_EVENT_DEFS = [
    EventDef(name='graph_steps', value=4),
    EventDef(name='graph_stack', value=True),
    EventDef(name='graph_time',  value=10.0),
    EventDef(name='window1_phase', value='open'),
    EventDef(name='window2_phase', value='open'),
    EventDef(name='window3_phase', value='open'),
    EventDef(name='window4_phase', value='open'),
    EventDef(name='window5_phase', value='close'),


    EventDef(name='random_phase', value='big'),

    EventDef(name='test_event', value='test_value4'),

]

_ev = {e.name: e for e in MAIN_EVENT_DEFS}

MAIN_POLYGON_DEFS = expand_defs([])
MAIN_GRAPH_DEFS   = []
MAIN_PIE_DEFS     = []
MAIN_TEXT_DEFS    = []

# ──────────────────────── WINDOW DEFS ────────────────────────

RED_ORANGE = GradientDef(
    stops=[
        GradientStop(0.0, QColor(255, 255, 255, 50)),
        GradientStop(1.0, QColor(255, 255, 255, 0)),
    ],
    # phases={
    #     'open':  Phase([GradientTween(
    #         stops=[
    #             GradientStop(0.0, QColor(255, 255, 255, 255)),
    #             GradientStop(1.0, QColor(255, 255, 255, 0)),
    #         ],
    #         start=0.0, dur=0.4, ease=QEasingCurve.OutQuint,
    #     )]),
    # },
)

MAIN_WINDOW_DEFS = [
    # EventListener Test
    WindowDef(
        p1=P(0.0, 0.0), p2=P(1.0, 1.0),
        phase_event=_ev['random_phase'],
        listener_defs=[
            EventListener(value_fn=lambda ctx: ctx['test_value1']['latest'], targets=[_ev['random_phase']], conditions=[lambda v: v > 5], values=['big', 'small']),
        ],
        polygon_defs=[
            PolygonDef(points=[P(0.0, 0.0), P(0.1, 0.0), P(0.1, 0.1), P(0.0, 0.1)], fill_color=QColor(20, 20, 20, 255), phases={
                    'big':  Phase([PolygonTween(fill_color=QColor(20, 255, 20, 255), start=0.0, dur=0.5, ease=QEasingCurve.OutQuint)]),
                    'small':  Phase([PolygonTween(fill_color=QColor(255, 20, 20, 255), start=0.0, dur=0.5, ease=QEasingCurve.OutQuint)])}),
        ]
    ),

    # WindowDef(
    #     p1=P(0.50, 0.00), p2=P(1.00, 0.50),
    #     phase_event=_ev['window3_phase'],
    #     phases={
    #         'phase1':  WindowPhase([WindowTween(p1=P(0.00, 0.50), p2=P(0.50, 1.00), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)]),
    #         'phase2': WindowPhase([WindowTween(p1=P(0.00, 0.00), p2=P(0.30, 0.30), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)]),
    #         'phase3':  WindowPhase([WindowTween(p1=P(0.00, 0.00), p2=P(1.00, 0.25), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)]),
    #     },
    #     polygon_defs=[
    #         Rect(p1=P(0.00, 0.00), p2=P(1.00, 1.00), fill_color=QColor(255, 255, 255, 50)),
    #         Rect(p1=P(0.50, 0.50), p2=P(0.50, 0.50), px1=P(-5, -5), px2=P(5, 5), fill_color=QColor(255, 0, 0, 255)),
    #         Rect(p1=P(0.20, 0.20), p2=P(0.40, 0.40), fill_color=QColor(0, 255, 0, 255)),
    #         Rect(p1=P(0.60, 0.20), p2=P(0.80, 0.40), fill_color=QColor(0, 0, 0, 0), outline_color=QColor(0, 0, 255, 255), line_width=2),
    #         PolygonDef(points=[P(0.50, 0.60), P(0.30, 0.80), P(0.70, 0.80)], fill_color=QColor(255, 255, 0, 255))
    #     ],
    #     text_defs=[
    #         TextDef(x=0.50, y=0.00, text='This is a single text', font_size=9.0, color=QColor(255, 255, 255, 255), h_align=0.5, v_align=0.0),
    #         TextDef(x=0.50, y=0.10, text='Test Value 1: <#>', font_size=9.0, color=QColor(255, 255, 255, 255), h_align=0.5, v_align=0.0,
    #         text_fn=lambda ctx: (f"{ctx['test_value1']['latest']:.4f}" if ctx and ctx['test_value1']['latest'] is not None else "-")),
    #         *TextBlock(x=0.00, y=0.90, text='This is a block of text\nThis appears in another line.\nThis appears on the last line.', font_size=9.0, color=QColor(255, 255, 255, 255), h_align=0.0, v_align=0.5)
    #     ],
    # ),

    # WindowDef(
    #     p1=P(0.00, 0.50), p2=P(0.50, 1.00),
    #     phase_event=_ev['window1_phase'],
    #     phases={
    #         'phase1':  WindowPhase([WindowTween(p1=P(0.00, 0.50), p2=P(0.50, 1.00), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)]),
    #         'phase2': WindowPhase([WindowTween(p1=P(0.00, 0.00), p2=P(0.30, 0.30), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)]),
    #         'phase3':  WindowPhase([WindowTween(p1=P(0.00, 0.00), p2=P(1.00, 0.25), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)]),
    #     },
    #     polygon_defs=[
    #         PolygonDef(
    #             points=[P(0.0, 0.0), P(1.0, 0.0), P(1.0, 1.0), P(0.0, 1.0)],
    #             fill_color=QColor(20, 20, 20, 255),
    #             phases={
    #                 'phase1':  Phase([PolygonTween(points=[P(0.0,0.0), P(1.0,0.0), P(1.0,1.0), P(0.0,1.0)],
    #                                 fill_color=QColor(20, 20, 20, 255),
    #                                 start=0.0, dur=1.0, ease=QEasingCurve.OutQuint)]),
    #                 'phase2': Phase([PolygonTween(points=[P(0.0,0.0), P(1.0,0.0), P(1.0,1.0), P(0.0,1.0)],
    #                                 fill_color=QColor(40, 0, 40, 255),
    #                                 start=0.0, dur=1.0, ease=QEasingCurve.InQuint)]),
    #             },
    #         ),
    #     ],
    #     text_defs=[
    #         TextDef(x=0.50, y=0.00, text='POWER CONSUMPTION', font_size=9.0,
    #                 color=QColor(255, 255, 255, 0),
    #                 phases={
    #                     'phase1':  Phase([TextTween(0.50, 0.00, 0.00, 1.00, QEasingCurve.OutQuint, QColor(255, 255, 255, 255), 0.5, 0.0, 9.0)]),
    #                     'phase2': Phase([TextTween(0.50, 0.00, 0.00, 1.00, QEasingCurve.OutQuint, QColor(255, 0, 255, 255), 0.5, 0.0, 9.0)]),
    #                 },
    #                 h_align=0.5, v_align=0.0),
    #         TextDef(x=0.50, y=0.90, text='kWh: <#>', font_size=9.0,
    #                 color=QColor(255, 255, 255, 255),
    #                 phases={
    #                     'phase1':  Phase([TextTween(0.50, 0.90, 0.00, 1.00, QEasingCurve.OutQuint, QColor(255, 255, 255, 255), 0.5, 1.0, 9.0)]),
    #                     'phase2': Phase([TextTween(0.50, 0.90, 0.00, 1.00, QEasingCurve.OutQuint, QColor(255, 0, 255, 255), 0.5, 1.0, 9.0)]),
    #                 },
    #                 h_align=0.5, v_align=1.0,
    #                 text_fn=lambda ctx: (
    #                     f"{sum(ctx[f'test_value{i}']['average'] for i in range(1, 10)):.4f}"
    #                     if ctx and ctx['test_value1']['average'] is not None else "-"
    #                 )),
    #     ],
    #     graph_defs=[
    #         GraphDef(
    #             p1=P(0.00, 0.05), p2=P(1.00, 0.85),
    #             series=[
    #                 SeriesDef(value_fn=lambda ctx: ctx['test_value1']['latest'], color=QColor(255, 106, 106, 255), line_width=1.0, fill_opacity=0.08),
    #                 SeriesDef(value_fn=lambda ctx: ctx['test_value2']['latest'], color=QColor(255, 111, 151, 255), line_width=1.0, fill_opacity=0.08),
    #                 SeriesDef(value_fn=lambda ctx: ctx['test_value3']['latest'], color=QColor(255, 126, 192, 255), line_width=1.0, fill_opacity=0.08),
    #                 SeriesDef(value_fn=lambda ctx: ctx['test_value4']['latest'], color=QColor(238, 145, 227, 255), line_width=1.0, fill_opacity=0.08),
    #                 SeriesDef(value_fn=lambda ctx: ctx['test_value5']['latest'], color=QColor(214, 165, 252, 255), line_width=1.0, fill_opacity=0.08),
    #                 SeriesDef(value_fn=lambda ctx: ctx['test_value6']['latest'], color=QColor(187, 184, 255, 255), line_width=1.0, fill_opacity=0.08),
    #                 SeriesDef(value_fn=lambda ctx: ctx['test_value7']['latest'], color=QColor(164, 200, 255, 255), line_width=1.0, fill_opacity=0.08),
    #                 SeriesDef(value_fn=lambda ctx: ctx['test_value8']['latest'], color=QColor(150, 213, 255, 255), line_width=1.0, fill_opacity=0.08),
    #                 SeriesDef(value_fn=lambda ctx: ctx['test_value9']['latest'], color=QColor(149, 224, 255, 255), line_width=1.0, fill_opacity=0.08),
    #             ],
    #             max_time=lambda: float(_ev['graph_time'].value),
    #             value_range=(0.0, 100.0),
    #             value_color=QColor(255, 255, 255, 255),
    #             ease_dur=0.3,
    #             ease_type=QEasingCurve.OutQuint,
    #             dynamic_scale=5.0,
    #             show_minmax = True,
    #             show_step = True,
    #             step_count = lambda: int(_ev['graph_steps'].value),
    #             label_align='left',
    #             stack=lambda: bool(_ev['graph_stack'].value),
    #             update_interval=1,
    #         ),
    #     ],
    #     pie_defs=[
    #         PieDef(
    #             p1=P(0.00, 0.93), p2=P(1.00, 0.95),
    #             names=[''] * 9,
    #             value_fns=[lambda ctx, i=i: ctx[f'test_value{i+1}']['latest'] for i in range(9)],
    #             colors=[QColor(255,106,106), QColor(255,111,151), QColor(255,126,192),
    #                     QColor(238,145,227), QColor(214,165,252), QColor(187,184,255),
    #                     QColor(164,200,255), QColor(150,213,255), QColor(149,224,255)],
    #             border_width=1.0, fill_opacity=0.1, direction='horizontal',
    #             size_label=0.0, size_name=9.0, ease_dur=0.4, ease_type=QEasingCurve.OutQuint,
    #         ),
    #         PieDef(
    #             p1=P(0.00, 0.95), p2=P(1.00, 1.00),
    #             names=[''] * 9,
    #             value_fns=[lambda ctx, i=i: ctx[f'test_value{i+1}']['average'] for i in range(9)],
    #             colors=[QColor(255,106,106), QColor(255,111,151), QColor(255,126,192),
    #                     QColor(238,145,227), QColor(214,165,252), QColor(187,184,255),
    #                     QColor(164,200,255), QColor(150,213,255), QColor(149,224,255)],
    #             border_width=1.0, fill_opacity=0.1, direction='horizontal',
    #             size_label=9.0, size_name=9.0, ease_dur=0.4, ease_type=QEasingCurve.OutQuint,
    #         ),
    #     ],
    # ),
    
    WindowDef(
        p1=P(0.50, 0.50), p2=P(1.00, 1.00),
        phase_event=_ev['window2_phase'],
        text_defs=[
            TextDef(x=0.50, y=0.10, text='Number: <#>', font_size=9.0, color=QColor(255, 255, 255, 255), h_align=0.5, v_align=0.0,
            text_fn=lambda ctx: _ev['graph_steps'].value),
        ],
        slider_defs=[
            SliderDef(x=0.20, y=0.40, lx=0.60, attr=AttributeDef(value_fn=lambda ctx: _ev['graph_steps'].value, set_fn  =lambda ctx, v: None, min_val=0, max_val=10, step=1, label='GRAPH STEPS', unit=''), event_out=_ev['graph_steps']),
            SliderDef(x=0.20, y=0.60, lx=0.60, attr=AttributeDef(value_fn=lambda ctx: _ev['graph_time'].value, set_fn  =lambda ctx, v: None, min_val=1, max_val=60, step=1, label='GRAPH TIME', unit='s'), event_out=_ev['graph_time']),
        ],
        button_defs=[
            ButtonDef(key=Qt.Key_W, action='set', event_out=_ev['window5_phase'], event_delta='open'),
            ButtonDef(key=Qt.Key_S, action='set', event_out=_ev['window5_phase'], event_delta='close'),
            ButtonDef(key=Qt.Key_A, action='increment', event_out=_ev['graph_steps'], event_delta=10),
            ButtonDef(key=Qt.Key_Up, action='set', event_out=_ev['test_event'], event_delta='test_value9'),
            ButtonDef(key=Qt.Key_Down, action='set', event_out=_ev['test_event'], event_delta='test_value1'),


            ButtonDef(
                poly=ButtonDiamond(p=P(0.25, 0.25), px=P(0, 0), size=40),
                label='+', text_color=QColor(160, 255, 160, 255),
                key=Qt.Key_Up, action='increment', event_out=_ev['graph_steps'], event_delta=1,
            ),
            ButtonDef(
                poly=ButtonDiamond(p=P(0.50, 0.25), px=P(0, 0), size=40),
                label='−', text_color=QColor(255, 160, 160, 255),
                key=Qt.Key_Down, action='increment', event_out=_ev['graph_steps'], event_delta=-1,
            ),
            ButtonDef(
                poly=ButtonDiamond(p=P(0.75, 0.25), px=P(0, 0), size=40),
                label='set', text_color=QColor(255, 255, 255, 220),
                action='set', event_out=_ev['graph_steps'], event_delta=4,
            ),
            ButtonDef(
                poly=ButtonDiamond(p=P(0.25, 0.75), px=P(0, 0), size=40),
                label='1', text_color=QColor(255, 255, 255, 220),
                key=Qt.Key_Left, action='set', event_out=_ev['window4_phase'], event_delta='open',
            ),
            ButtonDef(
                poly=ButtonDiamond(p=P(0.50, 0.75), px=P(0, 0), size=40),
                label='2', text_color=QColor(255, 255, 255, 220),
                key=Qt.Key_Right, action='set', event_out=_ev['window4_phase'], event_delta='close',
            ),
            ButtonDef(
                poly=ButtonDiamond(p=P(0.75, 0.75), px=P(0, 0), size=40),
                label='3', text_color=QColor(255, 255, 255, 220),
                action='set', event_out=_ev['test_event'], event_delta='test_value9',
            ),
        ],
    ),

    WindowDef(
        p1=P(0.0, 0.0), p2=P(1.0, 1.0),
        phase_event=_ev['window4_phase'],
        gradient_defs=[RED_ORANGE],
        polygon_defs=[

            # BOTTOM LEFT BEVEL CORNER
            PolygonDef(
                points=[P(0, 1), P(0, 1), P(0, 1), P(0, 1)],
                px=[P(0, -90), P(10, -90), P(90, -10), P(90, 0)],
                fill_color = QColor(255, 255, 255, 0),
                outline_color = QColor(100, 100, 100, 255),
                line_width = 2,
                closed=False,
                draw_progress=0,
                d_flip=True,
                phases={
                    'open': Phase([PolygonTween(draw_progress=1, start=0.0, dur=1.0, ease=QEasingCurve.OutQuint)]),
                    'close': Phase([Reset()]),
                },
            ),
            PolygonDef(
                points=[P(0, 1), P(0, 1), P(0, 1), P(0, 1), P(0, 1), P(0, 1)],
                px=[P(3, -88), P(8, -88), P(18, -78), P(15, -78), P(7, -85), P(3, -85)],
                fill_color = QColor(255, 255, 255, 0),
                phases={
                    'open': Phase([PolygonTween(fill_color=QColor(255, 255, 255, 255), start=1.0, dur=0.5, ease=QEasingCurve.OutQuint)]),
                    'close': Phase([Reset()]),
                },
            ),
            PolygonDef(
                points=[P(0, 1), P(0, 1), P(0, 1), P(0, 1), P(0, 1), P(0, 1)],
                px=[P(88, -3), P(88, -8), P(78, -18), P(78, -15), P(85, -7), P(85, -3)],
                fill_color = QColor(255, 255, 255, 0),
                phases={
                    'open': Phase([PolygonTween(fill_color=QColor(255, 255, 255, 255), start=1.0, dur=0.5, ease=QEasingCurve.OutQuint)]),
                    'close': Phase([Reset()]),
                },
            ),
            PolygonDef(
                points=[P(0, 1), P(0, 1), P(0, 1), P(0, 1)],
                px=[P(16, -75), P(19, -75), P(75, -19), P(75, -16)],
                fill_color = QColor(255, 255, 255, 0),
                phases={
                    'open': Phase([PolygonTween(fill_color=QColor(255, 255, 255, 255), start=1.0, dur=0.5, ease=QEasingCurve.OutQuint)]),
                    'close': Phase([Reset()]),
                },
            ),
            PolygonDef(
                points=[P(0.0, 1.0), P(0.0, 1.0), P(0.0, 1.0), P(0.0, 1.0)],
                px=[P(19, -75), P(19, -100), P(100, -19), P(75, -19)],
                gradient=RED_ORANGE,
                gradient_p1=P(0.0, 1.0), gradient_px1=P(40, -40),
                gradient_p2=P(0.0, 1.0), gradient_px2=P(41, -41),
                phases={
                    'open': Phase([PolygonTween(gradient_px1=P(49, -49), gradient_px2=P(60, -60), start=1.0, dur=0.5, ease=QEasingCurve.OutQuint)]),
                    'close': Phase([Reset()]),
                },
            ),

            # BOTTOM LINE
            PolygonDef(
                points=[P(1, 1), P(0, 1), P(0, 1), P(0, 0)],
                px=[P(0, -15), P(95, -15), P(15, -95), P(15, 100)],
                fill_color = QColor(255, 255, 255, 0),
                outline_color = QColor(100, 100, 100, 255),
                line_width = 2,
                closed=False,
                draw_progress=0,
                d_flip=True,
                phases={
                    'open': Phase([PolygonTween(draw_progress=1, start=0.0, dur=1.0, ease=QEasingCurve.OutQuint)]),
                    'close': Phase([Reset()]),
                },
            ),

            Rect(P(0.40, 0.40), P(0.60, 0.60), fill_color=QColor(255, 255, 255, 255), phases={
                'open': Phase([Reset(),
                    RectTween(P(0.20, 0.40), P(0.40, 0.60), start=0.00, dur=2.00, ease=QEasingCurve.OutSine, blend=True),
                    RectTween(P(0.00, 0.20), P(0.00, 0.20), start=1.00, dur=0.70, ease=QEasingCurve.OutSine)])}),





            # Same gradient, different polygon shape and anchor direction (vertical)
            PolygonDef(
                points=[P(0.6, 0.2), P(0.9, 0.2), P(0.9, 0.5), P(0.6, 0.5)],
                closed=True,
                gradient=RED_ORANGE,
                gradient_p1=P(0.6, 0.2), gradient_px1=P(0, 0),
                gradient_p2=P(0.6, 0.5), gradient_px2=P(0, 0),
                phases={},
            ),

            PolygonDef(
                points=[P(0.5, 0.5), P(0.5, 0.5), P(0.5, 0.5), P(0.5, 0.5)],
                px=[P(-35, -35), P(-15, -35), P(-15, -15), P(-35, -15)],
                closed=True,
                fill_color=QColor(100, 150, 255, 180),
                phases={
                    'open': Phase([PolygonTween(fill_color=QColor(100, 150, 255, 180), start=0.0, dur=0.4, ease=QEasingCurve.OutQuint)]),
                    'close': Phase([PolygonTween(fill_color=QColor(100, 150, 255, 0), start=0.0, dur=0.3, ease=QEasingCurve.InQuint)]),
                    'always': Phase(
                        tweens=[
                            PolygonTween(px=[P(50, 0), P(50, 0), P(50, 0), P(50, 0)], start=0.0, dur=0.5, ease=QEasingCurve.OutQuint),
                            PolygonTween(px=[P(50, 50), P(50, 50), P(50, 50), P(50, 50)], start=0.5, dur=0.5, ease=QEasingCurve.OutQuint),
                            PolygonTween(px=[P(0, 50), P(0, 50), P(0, 50), P(0, 50)], start=1.0, dur=0.5, ease=QEasingCurve.OutQuint),
                            PolygonTween(px=[P(0, 0), P(0, 0), P(0, 0), P(0, 0)], start=1.5, dur=0.5, ease=QEasingCurve.OutQuint),
                        ],
                        loop=True,
                        stop_phases=['close'],
                    ),
                },
            ),
            # Fix desync for always phases
            PolygonDef(
                points=[P(0.5, 0.5), P(0.5, 0.5), P(0.5, 0.5), P(0.5, 0.5)],
                px=[P(15, 15), P(35, 15), P(35, 35), P(15, 35)],
                closed=True,
                fill_color=QColor(255, 150, 255, 180),
                phases={
                    'open': Phase([PolygonTween(fill_color=QColor(255, 150, 255, 180), start=0.0, dur=0.4, ease=QEasingCurve.OutQuint)]),
                    'close': Phase([PolygonTween(fill_color=QColor(255, 150, 255, 0), start=0.0, dur=0.3, ease=QEasingCurve.InQuint)]),
                    'always': Phase(
                        tweens=[
                            PolygonTween(px=[P(-50, 0), P(-50, 0), P(-50, 0), P(-50, 0)], start=0.0, dur=0.5, ease=QEasingCurve.OutQuint),
                            PolygonTween(px=[P(-50, -50), P(-50, -50), P(-50, -50), P(-50, -50)], start=0.5, dur=0.5, ease=QEasingCurve.OutQuint),
                            PolygonTween(px=[P(0, -50), P(0, -50), P(0, -50), P(0, -50)], start=1.0, dur=0.5, ease=QEasingCurve.OutQuint),
                            PolygonTween(px=[P(0, 0), P(0, 0), P(0, 0), P(0, 0)], start=1.5, dur=0.5, ease=QEasingCurve.OutQuint),
                        ],
                        loop=True,
                        stop_phases=['close'],
                    ),
                },
            ),
        ],
        text_defs=[
            TextDef(x=1.00, y=0.50, px=0, py=10, text='TEST TEST TEST TEST TEST TEST TEST TEST TEST', font_size=30.0, color=QColor(255, 255, 255, 127), bold=True, italic=True, h_align=0, v_align=0,
                phases={
                    'open': Phase([Reset(), TextTween(x=0.00, start=0, dur=1, ease=QEasingCurve.OutQuint)]),
                    'close': Phase([TextTween(x=-2.00, start=0, dur=1, ease=QEasingCurve.InQuint)]),
                    'always': Phase([
                        TextTween(px=-62.2, start=0.0, dur=1, ease=QEasingCurve.InOutQuad),
                        TextTween(px=0, start=1, dur=1, ease=QEasingCurve.InOutQuad),
                    ], loop=True, stop_phases=['close']),
                },
            ),
            # TextDef(x=0.00, y=0.50, px=0, py=10, text='TEST', font_size=30.0, color=QColor(255, 0, 0, 127), bold=True, italic=True, h_align=0, v_align=0,
            # ),
            # TextDef(x=0.30, y=0.00, px=0, py=10, text='LAUNCHING SPEAR_GUI', font_size=30.0, char_display=0.0, sub_char_clip=True, backward=True, color=QColor(255, 255, 255, 127), bold=True, italic=True, h_align=0, v_align=0,
            #     phases={
            #         'open': Phase([TextTween(x=0.00, px=10, char_display=1.0, color=QColor(255, 255, 255, 255), start=0.0, dur=1.0, ease=QEasingCurve.OutQuint)]),
            #         'close': Phase([Reset()]),
            #     },
            # ),
            #'AnimatedText' object has no attribute '_apply_blend'
            # Make text blending, then use this version
            TextDef(x=0.50, y=0.00, px=10, py=10, text='PLACEHOLDER TEXT', font_size=30.0, char_display=0.0, sub_char_clip=True, color=QColor(255, 255, 255, 127), bold=True, italic=True, h_align=0, v_align=0,
                phases={
                    'open': Phase([TextTween(char_display=1.0, color=QColor(255, 255, 255, 255), start=0.0, dur=2.5, ease=QEasingCurve.OutQuint, blend=True),
                                   TextTween(x=-0.50, start=0.0, dur=1.5, ease=QEasingCurve.OutQuint)]),
                    'close': Phase([Reset()]),
                },
            ),
        ],
    ),
    
    WindowDef(
        p1=P(0.5, 0.5), p2=P(0.5, 0.5),
        phase_event=_ev['window5_phase'],
        gradient_defs=[RED_ORANGE],
        phases={
            'open':  WindowPhase([WindowTween(p1=P(0.00, 0.00), p2=P(1.00, 1.00), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)]),
            'close': WindowPhase([WindowTween(p1=P(0.50, 0.50), p2=P(0.50, 0.50), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)]),
        },
        polygon_defs=[
            Rect(p1=P(0, 0), p2=P(1, 1), fill_color=QColor(0, 0, 0, 255)),

            Rect(p1=P(0, 0), p2=P(0, 1), px2=P(1, 0), fill_color=QColor(255, 255, 255, 255)),
            Rect(p1=P(1, 0), p2=P(1, 1), px1=P(-1, 0), fill_color=QColor(255, 255, 255, 255)),
            Rect(p1=P(0, 0), p2=P(1, 0), px2=P(0, 1), fill_color=QColor(255, 255, 255, 255)),
            Rect(p1=P(0, 1), p2=P(1, 1), px1=P(0, -1), fill_color=QColor(255, 255, 255, 255)),
        ],
        text_defs=[
            *DataTable(x=0.05, y=0.30, px=0, py=0, value_x=0.30, value_px=0, row_height=18.0, char_display=0.0, sub_char_clip=True, color=QColor(200, 220, 255, 220),
                value_names=['AMPS', 'VOLTS',   'RPM',  'RPM (REQ)'],
                values=[
                    lambda ctx: ctx['test_value1']['latest'],
                    lambda ctx: ctx['test_value2']['latest'],
                    lambda ctx: ctx['test_value3']['latest'],
                    lambda ctx: ctx[_ev['test_event'].value]['latest'],
                ],
                value_units=['A', 'V', 'r/m', 'r/m'],
                formats=['.2f', '.2f', '.1f', '.1f'],
                phases={
                    'open': Phase([TextTween(char_display=1.0, color=QColor(200, 220, 255, 220), start=0.6, dur=0.7, ease=QEasingCurve.OutQuint)], line_delay=0.05),
                    'close': Phase([TextTween(char_display=0.0, color=QColor(200, 220, 255, 0), start=0.0, dur=0.5, ease=QEasingCurve.OutQuint)], line_delay=0.00),
                },
            ),
            TextDef(x=0.05, y=0.30, px=0, py=0, text='FRONT LEFT', font_size=12.0, char_display=0.0, sub_char_clip=True, color=QColor(200, 220, 255, 220), bold=True, italic=True, h_align=0, v_align=1,
                phases={
                    'open': Phase([Reset(), TextTween(char_display=1.0, start=0.5, dur=1, ease=QEasingCurve.OutQuint)]),
                    'close': Phase([TextTween(char_display=0.0, start=0, dur=0.5, ease=QEasingCurve.OutQuint)]),
                },
            ),

            *DataTable(x=0.5, y=0.30, px=0, py=0, value_x=0.75, value_px=0, row_height=18.0, char_display=0.0, sub_char_clip=True, color=QColor(200, 220, 255, 220),
                value_names=['AMPS', 'VOLTS',   'RPM',  'RPM (REQ)'],
                values=[
                    lambda ctx: ctx['test_value4']['latest'],
                    lambda ctx: ctx['test_value5']['latest'],
                    lambda ctx: ctx['test_value6']['latest'],
                    lambda ctx: ctx['test_value7']['latest'],
                ],
                value_units=['A', 'V', 'r/m', 'r/m'],
                formats=['.2f', '.2f', '.1f', '.1f'],
                phases={
                    'open': Phase([TextTween(char_display=1.0, color=QColor(200, 220, 255, 220), start=0.7, dur=0.7, ease=QEasingCurve.OutQuint)], line_delay=0.05),
                    'close': Phase([TextTween(char_display=0.0, color=QColor(200, 220, 255, 0), start=0.0, dur=0.5, ease=QEasingCurve.OutQuint)], line_delay=0.00),
                },
            ),
            TextDef(x=0.5, y=0.30, px=0, py=0, text='FRONT RIGHT', font_size=12.0, char_display=0.0, sub_char_clip=True, color=QColor(200, 220, 255, 220), bold=True, italic=True, h_align=0, v_align=1,
                phases={
                    'open': Phase([Reset(), TextTween(char_display=1, start=0.6, dur=1, ease=QEasingCurve.OutQuint)]),
                    'close': Phase([TextTween(char_display=0.0, start=0, dur=0.5, ease=QEasingCurve.OutQuint)]),
                },
            ),
        ],
    ),

]
