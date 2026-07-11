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

WINDOW_LAYER = 2

register_event(EventDef(name='pos_x',     value=-112.710534))
register_event(EventDef(name='pos_y',     value=51.465185))
register_event(EventDef(name='map_pos_x',     value=0))
register_event(EventDef(name='map_pos_y',     value=0))
register_event(EventDef(name='spawn_marker',     value=False))
register_event(EventDef(name='map_prompt_phase', value='close'))
register_event(EventDef(name='map_zoom',     value=1))
register_event(EventDef(name='map_marker_x',     value=0))
register_event(EventDef(name='map_marker_y',     value=0))
register_event(EventDef(name='map_phase',     value='open'))

WINDOW_DEFS = [
    #   GREY BACKGROUND RECTANGLE
    WindowDef(
        p1=P(0.5, 0.5), p2=P(0.5, 0.5), px1=P(-940, -520), px2=P(940, 520),
        polygon_defs=[
            # RectDef(p1=P(0.71875, 0.5), p2=P(0.71875, 0.5), px1=P(-520, -520), px2=P(520, 520), fill_color=QColor(30, 30, 30)),
            RectDef(p1=P(0, 0.0), p2=P(1, 1), fill_color=QColor(30, 30, 30)),
        ],#0.4375
    ),
    # ------------------------------------------------
    #                       MAP
    # ------------------------------------------------
    WindowDef( #0.6875 for screen hight of 1200
        p1=P(0.71875, 0.5), p2=P(0.71875, 0.5), px1=P(-500, -500), px2=P(500, 500),
        phase_event=get_event('map_phase'),
        listener_defs=[
            EventListener(value_fn=lambda ctx: get_event('pos_x').value, targets=[get_event('map_pos_x')], passthrough=True, transform=lambda v: (v + 112.710534) / 0.0000001),
            EventListener(value_fn=lambda ctx: get_event('pos_y').value, targets=[get_event('map_pos_y')], passthrough=True, transform=lambda v: (v - 51.465185) / 0.0000001),
        ],
        polygon_defs=[
            RectDef(p1=P(0.0, 0.0), p2=P(1.0, 1.0), fill_color=QColor(255, 255, 255, 10), outline_color=QColor(255, 255, 255, 255), outline_width=1),
            PolygonDef(p=[P(0.5, 0.5)]*4, px=[P(-10, 0), P(0, -10), P(10, 0), P(0, 10)], fill_color=QColor(200, 200, 255, 255)),
        ],
        text_defs=[ #     x, y
            TextDef(p=P(0.5, 0), px=P(0, 2), font_size=20, v_align=0, text='N', uniform_scale=False),
            TextDef(p=P(0.5, 1), px=P(0, -2), font_size=20, v_align=1, text='S', uniform_scale=False),
            TextDef(p=P(0, 0.5), px=P(2, 0), font_size=20, h_align=0, text='W', uniform_scale=False),
            TextDef(p=P(1, 0.5), px=P(-2, 2), font_size=20, h_align=1, text='E', uniform_scale=False),
            TextDef(p=P(0, 1), px=P(2, -2), text='(<#>, <#>)', font_size=10, h_align=0, v_align=1, uniform_scale=False,
                text_fn=lambda ctx: [f"{get_event('map_pos_x').value:.7f}", f"{get_event('map_pos_y').value:.7f}"],
            ),
        ],
        button_defs=[
            ButtonDef(key=Qt.Key_Up, action='increment', continuous_update=True, event_out=get_event('pos_y'), event_delta=0.00001),
            ButtonDef(key=Qt.Key_Down, action='increment', continuous_update=True, event_out=get_event('pos_y'), event_delta=-0.00001),
            ButtonDef(key=Qt.Key_Left, action='increment', continuous_update=True, event_out=get_event('pos_x'), event_delta=0.00001),
            ButtonDef(key=Qt.Key_Right, action='increment', continuous_update=True, event_out=get_event('pos_x'), event_delta=-0.00001),
            ButtonDef(poly_def=RectDef(p1=P(0, 0), p2=P(1, 1)), key=Qt.Key_P, mandatory_keys=Qt.Key_Shift, action='set', event_out=get_event('spawn_marker'), event_delta=True, invisible=True),
        ],
        slider_defs=[
            SliderDef(p=P(0.5, 1), px=P(70, -15), length=0.5, length_px=-85, event_out=get_event('map_zoom'), min_val=0.1, max_val=2.9, step=0.1, label='ZOOM', unit='', decimals=1)
        ],
        sub_windows=[
            WindowDef(
                p1=P(0, 0), p2=P(1, 1),
                polygon_defs=[
                    PolygonDef(p=[P(STATIC(0), STATIC(1))]*4, px=[P(-10, 0), P(0, -10), P(10, 0), P(0, 10)], fill_color=QColor(255, 200, 200, 255),
                        pos_fn=lambda: P(get_event('map_pos_x').value, get_event('map_pos_y').value)
                    ),
                ],
                text_defs=[
                    TextDef(p=P(STATIC(0), STATIC(1)), px=P(0, -10), font_size=10, v_align=1, text='MARKER', uniform_scale=False, fill_color=QColor(255, 200, 200, 255),
                        pos_fn=lambda: P(get_event('map_pos_x').value, get_event('map_pos_y').value)
                    ),
                ],
                button_defs=[
                    ButtonDef(poly_def=PolygonDef(p=[P(STATIC(0), STATIC(1))]*4, px=[P(-10, 0), P(0, -10), P(10, 0), P(0, 10)], fill_color=QColor(255, 200, 200, 255),
                        pos_fn=lambda: P(get_event('map_pos_x').value / 2, get_event('map_pos_y').value / 2)
                    ),
                        action='set',
                        event_out=GROUP_EVENT,
                        event_delta=1,
                    )
                ],
                spawn_event=get_event('spawn_marker'),
                spawn_event_group='marker',
                phase_event=GROUP_EVENT,
                spawn_delete_threshold=1,
                spawn_static_values=[
                    lambda: get_spawn_mouse_norm().x - get_event('map_pos_x').value / 400,
                    lambda: get_spawn_mouse_norm().y - get_event('map_pos_y').value / 400,
                ],
            ),

        ]
    ),
    # -------------------------------------------
    #             values & measurments
    # -------------------------------------------
    WindowDef(
        p1=P(0, 0), p2=P(0.4375, 1), px1=P(40, 40), px2=P(0, -40),
        polygon_defs=[
            PolygonDef(p=[P(0, 0), P(0, 0), P(0, 0), P(0, 1), P(0, 1), P(0, 1)], px=[P(0, 50), P(5, 50 - 5), P(10, 50), P(10, -50), P(5, -50 + 5), P(0, -50)], gradient=get_gradient('alt_color_fill'))
        ],
        text_defs=[
            TextDef(p=P(0, 0), px=P(0, 0), font_size=25, h_align=0, v_align=0, text='Latitude:   <#> DD', text_fn= lambda ctx: f"{ctx['test_value1']['latest']:.7f}", uniform_scale=False),
            TextDef(p=P(0, 0), px=P(0, 30), font_size=25, h_align=0, v_align=0, text='Longitude:   <#> DD', text_fn= lambda ctx: f"{ctx['test_value2']['latest']:.7f}", uniform_scale=False),
            
            TextDef(p=P(0, 0.1), px=P(0, 0), font_size=15, h_align=0, v_align=0, text='Current Speed:   <#> km/h', text_fn= lambda ctx: f"{ctx['test_value3']['latest']:.2f}", uniform_scale=False),
            TextDef(p=P(0, 0.1), px=P(0, 30), font_size=15, h_align=0, v_align=0, text='Acceleration:   <#> m/s^2', text_fn= lambda ctx: f"{ctx['test_value4']['latest']:.2f}", uniform_scale=False),
            TextDef(p=P(0, 0.1), px=P(0, 60), font_size=15, h_align=0, v_align=0, text='Anglular Velocity:   <#> ω', text_fn= lambda ctx: f"{ctx['test_value4']['latest']:.2f}", uniform_scale=False),
            
            TextDef(p=P(0.5, 0.1), px=P(0, 0), font_size=15, h_align=0, v_align=0, text='Pitch:   <#> °', text_fn= lambda ctx: f"{ctx['test_value4']['latest']:.2f}", uniform_scale=False),
            TextDef(p=P(0.5, 0.1), px=P(0, 30), font_size=15, h_align=0, v_align=0, text='Yaw:   <#> °', text_fn= lambda ctx: f"{ctx['test_value4']['latest']:.2f}", uniform_scale=False),
            TextDef(p=P(0.5, 0.1), px=P(0, 60), font_size=15, h_align=0, v_align=0, text='Roll:   <#> °', text_fn= lambda ctx: f"{ctx['test_value4']['latest']:.2f}", uniform_scale=False),
            
            TextDef(p=P(0.75, 0.35), px=P(0, -105), font_size=10, h_align=0.5, v_align=1, text='N', uniform_scale=False),
            TextDef(p=P(0.75, 0.35), px=P(0, 105), font_size=10, h_align=0.5, v_align=0, text='S', uniform_scale=False),
            TextDef(p=P(0.75, 0.35), px=P(105, 0), font_size=10, h_align=0, v_align=0.5, text='E', uniform_scale=False),
            TextDef(p=P(0.75, 0.35), px=P(-105, 0), font_size=10, h_align=1, v_align=0.5, text='W', uniform_scale=False),
        ],
        arc_defs=[
            ArcDef(center_p=P(0.75, 0.35), inner_p=P(0.75, 0.3), inner_px=P(100, 0), outer_p= P(0.75, 0.3), outer_px=P(103, 0), fill_color=QColor(255, 255, 255, 255), outline_width=0)
        ],
    )

]

register_windows(WINDOW_LAYER, WINDOW_DEFS)
