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

WINDOW_LAYER = 0

# ──────────────────────── BACKGROUND ────────────────────────
background_polygons = [
    PolygonDef(p=[P(0, 0), P(1, 1)], fill_color=QColor(0, 0, 0, 255))
]

register_gradient(GradientDef(
    name='startup_grid', p1=P(0.5, 0.5), p2=P(1, 1), radial=True, target='outline', stops=[
        GradientStop(0.0, QColor(255, 255, 255, 10)),
        GradientStop(1.0, QColor(255, 255, 255, 0)),
    ],
))

for i in range(19):
    px = (i - 9) * 120
    background_polygons += [
        PolygonDef(p=[P(0.5, 0), P(0.5, 1)], px=[P(px, 0), P(px, 0)], outline_color=QColor(255, 255, 255, 10), gradient=get_gradient('startup_grid'), outline_width=1),
    ]
for i in range(11):
    py = (i - 5) * 120
    background_polygons += [
        PolygonDef(p=[P(0, 0.5), P(1, 0.5)], px=[P(0, py), P(0, py)], outline_color=QColor(255, 255, 255, 10), gradient=get_gradient('startup_grid'), outline_width=1),
    ]

background_window = WindowDef(p1=P(0.0, 0.0), p2=P(1.0, 1.0), polygon_defs = background_polygons)





# ──────────────────────── SUBSCRIPTION VALUES ────────────────────────

register_event(EventDef(name='startup_subscription_phase', value='waiting'))

subscription_list = ['test_value1', 'test_value2', 'test_value3', 'test_value4', 'test_value5', 'test_value6', 'test_value7', 'test_value8', 'test_value9', 'test_value10']
subscription_columns = 2
subscription_listeners = []
subscription_polygons = []
subscription_texts = []
for i in range(len(subscription_list)):
    x = i % subscription_columns
    y = math.floor(i / subscription_columns)
    target_x = (x / (subscription_columns - 1)) / 15 + 0.85
    target_y = y / 20 + 0.1
    name = f'sub_sample_pulse{i}'
    delay = 0.05 * i
    register_event(EventDef(name=name, value=None))
    register_gradient(GradientDef(
        name=name, p1=P(target_x, target_y), p2=P(target_x, target_y), px1=P(0, 0), px2=P(-60, 0), target='fill', phase_event=get_event(name),
        stops=[GradientStop(0.0, QColor(255, 0, 0, 255)), GradientStop(1.0, QColor(255, 0, 0, 0))], 
        phases={'pulse': Phase([
            GradientTween(stops=[GradientStop(0.0, QColor(0, 100, 0, 255)), GradientStop(1.0, QColor(0, 255, 0, 0))], start=0, dur=0, ease=QEasingCurve.OutQuint),
            GradientTween(stops=[GradientStop(0.0, QColor(0, 0, 0, 0)), GradientStop(1.0, QColor(0, 0, 0, 0))], start=0, dur=1, ease=QEasingCurve.OutQuint),
            ])
        }
    ))
    subscription_listeners += [
        EventListener(value_fn='pulse', targets=[get_event(name)], passthrough=True, wait_for_updates=lambda ctx, s=subscription_list[i]: ctx[s]['push_count']),
    ]
    subscription_polygons += [
        PolygonDef(p=[P(target_x + 0.5, target_y)]*4, px=[P(0, -15), P(0, 15), P(-60, 15), P(-60, -15)], gradient=get_gradient(name), 
        # phase_override=lambda n=name: get_event(n).value, 
        phases={
            'open': Phase([PolygonTween(p=[P(target_x, target_y)]*4, start=delay, dur=2.0, ease=QEasingCurve.OutQuint)]),
        }),
        PolygonDef(p=[P(target_x + 0.5, target_y)]*6, px=[P(-3, 12), P(-3, -12), P(0, -15), P(3, -12), P(3, 12), P(0, 15)], fill_color=QColor(255, 0, 0, 255), 
        # phase_override=lambda n=name: get_event(n).value, 
        phases={
            'open': Phase([PolygonTween(p=[P(target_x, target_y)]*6, start=delay, dur=2.0, ease=QEasingCurve.OutQuint)]),
            'pulse': Phase([
                    PolygonTween(fill_color=QColor(0, 255, 0, 255), start=0, dur=0.0, ease=QEasingCurve.OutQuint),
                    PolygonTween(fill_color=QColor(0, 100, 0, 255), start=0, dur=1.0, ease=QEasingCurve.OutQuint),
                ])
            }
        ),
    ]
    subscription_texts += [
        TextDef(p=P(target_x + 0.5, target_y), px=P(7, 0), h_align=0, text=subscription_list[i], uniform_scale=False, phases={
            'open': Phase([TextTween(p=P(target_x, target_y), start=delay, dur=2.0, ease=QEasingCurve.OutQuint)]),
        }),
        TextDef(p=P(target_x + 0.5, target_y), px=P(-7, 0), h_align=1, text_fn=lambda ctx, s=subscription_list[i]: ctx[s]['push_count'], uniform_scale=False, phases={
            'open': Phase([TextTween(p=P(target_x, target_y), start=delay, dur=2.0, ease=QEasingCurve.OutQuint)]),
        }),
    ]
subscription_window = WindowDef(p1=P(0.0, 0.0), p2=P(1.0, 1.0), force_open=True, phase_event=get_event('startup_subscription_phase'), listener_defs = subscription_listeners, polygon_defs = subscription_polygons, text_defs = subscription_texts)

# ──────────────────────── SUBSCRIPTION VALUES ────────────────────────

#

register_event(EventDef(name='startup_phase', value='close'))
register_event(EventDef(name='startup_phase_flip', value='open'))


register_gradient(GradientDef(
    name='launch_text_outline1', p1=P(0.5, 0.5), p2=P(0.5, 0.5), px1=P(-300, -150), px2=P(300, 150), target='outline', phase_event=get_event('startup_phase_flip'), stops=[
        GradientStop(0.0, QColor(50, 50, 50, 255)),
        GradientStop(0.5, QColor(50, 50, 50, 255)),
        GradientStop(0.5001, QColor(50, 50, 50, 0)),
    ],
    phases={'close': Phase([GradientTween(stops=[
        GradientStop(0.0, QColor(50, 50, 50, 0)),
        GradientStop(0.5, QColor(50, 50, 50, 0)),
        GradientStop(0.5001, QColor(50, 50, 50, 0)),
        ], start=0, dur=1, ease=QEasingCurve.OutQuint)])
    }
))
register_gradient(GradientDef(
    name='launch_text_outline2', p1=P(0.5, 0.5), p2=P(0.5, 0.5), px1=P(-300, -150), px2=P(300, 150), target='outline', phase_event=get_event('startup_phase_flip'), stops=[
        GradientStop(0.0, QColor(50, 50, 50, 0)),
        GradientStop(0.5, QColor(50, 50, 50, 0)),
        GradientStop(0.5001, QColor(50, 50, 50, 255)),
    ],
    phases={'close': Phase([GradientTween(stops=[
        GradientStop(0.0, QColor(50, 50, 50, 0)),
        GradientStop(0.5, QColor(50, 50, 50, 0)),
        GradientStop(0.5001, QColor(50, 50, 50, 0)),
        ], start=0, dur=1, ease=QEasingCurve.OutQuint)])
    }
))

register_gradient(GradientDef(
    name='startup_border_top', p1=P(0, 0), p2=P(0, 0.1), target='fill', phase_event=get_event('startup_phase'), stops=[
        GradientStop(0.0, QColor(171, 151, 247, 0)),
        GradientStop(1.0, QColor(171, 151, 247, 0)),
    ],
    phases={'open': Phase([GradientTween(stops=[
        GradientStop(0.0, QColor(171, 151, 247, 20)),
        GradientStop(1.0, QColor(171, 151, 247, 0)),
        ], start=0, dur=1, ease=QEasingCurve.OutQuint)])
    }
))

register_gradient(GradientDef(
    name='startup_border_bottom', p1=P(0, 0.9), p2=P(0, 1), target='fill', phase_event=get_event('startup_phase'), stops=[
        GradientStop(0.0, QColor(171, 151, 247, 0)),
        GradientStop(1.0, QColor(171, 151, 247, 0)),
    ],
    phases={'open': Phase([GradientTween(stops=[
        GradientStop(0.0, QColor(171, 151, 247, 0)),
        GradientStop(1.0, QColor(171, 151, 247, 20)),
        ], start=0, dur=1, ease=QEasingCurve.OutQuint)])
    }
))

register_gradient(GradientDef(
    name='alt_color_fill', p1=P(0, 0), p2=P(1, 1), target='fill', phase_event=get_event('startup_phase'), stops=[
        GradientStop(0.0, QColor(171, 151, 247, 255)),
        GradientStop(1.0, QColor(242, 179, 249, 255)),
    ],
))

register_gradient(GradientDef(
    name='alt_color_outline', p1=P(0, 0), p2=P(1, 1), target='outline', phase_event=get_event('startup_phase'), stops=[
        GradientStop(0.0, QColor(171, 151, 247, 255)),
        GradientStop(1.0, QColor(242, 179, 249, 255)),
    ],
))

alt_color = QColor(171, 151, 247, 255)

startup_window = WindowDef(
    p1=P(0.0, 0.0), p2=P(1.0, 1.0),
    polygon_defs=[
        RectDef(p1=P(0.5, 0.75), p2=P(0.5, 0.75), px1=P(-200, -5), px2=P(200, 5), phase_override=get_event('startup_phase'), phases={
            'open': Phase([RectTween(p1=P(1, 0.75), p2=P(0.6, 0.75), px1=P(-500, -5), px2=P(0, 5), start=0.0, dur=3.0, ease=QEasingCurve.OutQuint, blend=True),
                           RectTween(p1=P(0, -0.25), p2=P(0.4, -0.25), px2=P(-100, 0), start=0.0, dur=1.0, ease=QEasingCurve.OutQuint)])
        }),

        RectDef(p1=P(0, 0), p2=P(1, 0.1), phase_override=get_event('startup_phase'), gradient=get_gradient('startup_border_top')),
        RectDef(p1=P(0, 0.9), p2=P(1, 1), phase_override=get_event('startup_phase'), gradient=get_gradient('startup_border_bottom')),
        RectDef(p1=P(0, 0), p2=P(1, 0), gradient=get_gradient('alt_color_fill'), phase_override=get_event('startup_phase'), phases={
            'open': Phase([RectTween(p1=P(0, 0), p2=P(1, 0), px2=P(0, 10), start=0, dur=1.0, ease=QEasingCurve.OutQuint)])
        }),
        RectDef(p1=P(0, 1), p2=P(1, 1), gradient=get_gradient('alt_color_fill'), phase_override=get_event('startup_phase'), phases={
            'open': Phase([RectTween(p1=P(0, 1), p2=P(1, 1), px1=P(0, -10), start=0, dur=1.0, ease=QEasingCurve.OutQuint)])
        }),
        PolygonDef(p=[P(0, 0), P(0, 0.4), P(0, 0.4), P(0, 1)], px=[P(30, 30), P(30, -15), P(60, 15), P(60, -30)], fill_color=QColor(255, 255, 255, 0), outline_color=QColor(255, 255, 255, 255), outline_width=2, draw_progress=0, closed=False, phase_override=get_event('startup_phase'), phases={
            'open': Phase([PolygonTween(draw_progress=1, start=0, dur=2.5, ease=QEasingCurve.OutExpo)])
        }),
        PolygonDef(p=[P(1, 1), P(1, 0.6), P(1, 0.6), P(1, 0)], px=[P(-30, -30), P(-30, 15), P(-60, -15), P(-60, 30)], fill_color=QColor(255, 255, 255, 0), outline_color=QColor(255, 255, 255, 255), outline_width=2, draw_progress=0, closed=False, phase_override=get_event('startup_phase'), phases={
            'open': Phase([PolygonTween(draw_progress=1, start=0, dur=2.5, ease=QEasingCurve.OutExpo)])
        }),

        # PolygonDef(p=[P(0, 1)]*4, px=[P(5, -90), P(25, -70), P(25, -30), P(5, -50)], gradient=get_gradient('alt_color_fill'), phase_override=get_event('startup_phase'), phases={
        #     'open': Phase([PolygonTween(px=[P(5, -90), P(25, -70), P(25, -30), P(5, -50)], start=0, dur=1.0, ease=QEasingCurve.OutQuint)]),
        #     'always': Phase([PolygonTween(px=[P(5, -90 - 200), P(25, -70 - 200), P(25, -30 - 200), P(5, -50 - 200)], start=0.0, dur=5.0, ease=QEasingCurve.InOutQuint),
        #                      PolygonTween(px=[P(5, -90), P(25, -70), P(25, -30), P(5, -50)], start=5.0, dur=5.0, ease=QEasingCurve.InOutQuint)], loop=True, stop_phases=['close']),
        # }),
        # PolygonDef(
        #         p=[P(0.5, 0.5), P(0.5, 0.5), P(0.5, 0.5), P(0.5, 0.5)],
        #         px=[P(-35, -35), P(-15, -35), P(-15, -15), P(-35, -15)],
        #         closed=True,
        #         fill_color=QColor(100, 150, 255, 180),
        #         phases={
        #             P_OPEN: Phase([PolygonTween(fill_color=QColor(100, 150, 255, 180), start=0.0, dur=2, ease=QEasingCurve.OutQuint),
        #             PolygonTween(fill_color=QColor(255, 0, 0, 180), start=2.0, dur=2, ease=QEasingCurve.OutQuint)
        #             ]),
        #             P_CLOSE: Phase([PolygonTween(fill_color=QColor(100, 150, 255, 0), start=0.0, dur=0.3, ease=QEasingCurve.InQuint)]),
        #             'always': Phase(
        #                 tweens=[
        #                     PolygonTween(px=[P(50, 0), P(50, 0), P(50, 0), P(50, 0)], start=0.0, dur=0.5, ease=QEasingCurve.OutQuint),
        #                     PolygonTween(px=[P(50, 50), P(50, 50), P(50, 50), P(50, 50)], start=0.5, dur=0.5, ease=QEasingCurve.OutQuint),
        #                     PolygonTween(px=[P(0, 50), P(0, 50), P(0, 50), P(0, 50)], start=1.0, dur=0.5, ease=QEasingCurve.OutQuint),
        #                     PolygonTween(px=[P(0, 0), P(0, 0), P(0, 0), P(0, 0)], start=1.5, dur=0.5, ease=QEasingCurve.OutQuint),
        #                 ],
        #                 loop=True,
        #                 stop_phases=['close'],
        #             ),
        #         },
        #     ),
    ],
    text_defs=[
        TextDef(
            p=P(0.5, 0.5), px=P(0, 0), text='SPEAR', bold=True, italic=True, font_size=400, fill_color=QColor(255,255,255,0), outline_width=4,
            gradient=get_gradient('launch_text_outline1'), phase_override=get_event('startup_phase_flip'), phases={
                'close': Phase([TextTween(px=P(-50, 100), start=0, dur=1.0, ease=QEasingCurve.OutQuint)])
            }
        ),
        TextDef(
            p=P(0.5, 0.5), px=P(0, 0), text='SPEAR', bold=True, italic=True, font_size=400, fill_color=QColor(255,255,255,0), outline_width=4,
            gradient=get_gradient('launch_text_outline2'), phase_override=get_event('startup_phase_flip'), phases={
                'close': Phase([TextTween(px=P(50, -100), start=0, dur=1.0, ease=QEasingCurve.OutQuint)])
            }
        ),
        TextDef(
            p=P(0.5, 0.75), px=P(0, -7), text='AWAITING INPUTS', font_size=20, h_align=0.5, v_align=1.0, fill_color=QColor(255,255,255,255),
            phase_override=get_event('startup_phase'), phases={
                'open': Phase([TextTween(p=P(1, 0.5), px=P(-500, -5), h_align=0.0, start=0, dur=1.0, ease=QEasingCurve.OutQuint)])
            }
        ),
        TextDef(
            p=P(0.5, 0.75), px=P(0, 7), text='0%', font_size=20, h_align=0.5, v_align=0.0, fill_color=QColor(255,255,255,255),
            phase_override=get_event('startup_phase'), phases={
                'open': Phase([TextTween(p=P(1, 0.5), px=P(-100, -5), h_align=1.0, v_align=1.0, start=0, dur=1.0, ease=QEasingCurve.OutQuint)])
            }
        ),
        TextDef(
            p=P(0, 0), px=P(50, 15), text='PREVIEW', bold=True, font_size=70, h_align=0.0, v_align=0.0, char_display=0, sub_char_clip=True, fill_color=QColor(255,255,255,0), gradient=get_gradient('alt_color_outline'), outline_width=2,
            phase_override=get_event('startup_phase'), phases={
                'open': Phase([TextTween(char_display=1, start=0, dur=1.0, ease=QEasingCurve.OutQuint)])
            }
        ),
        TextDef(
            p=P(1, 0), px=P(-70, 15), text='SUBSCRIPTIONS', bold=True, font_size=70, h_align=1.0, v_align=0.0, char_display=0, sub_char_clip=True, backward=True, fill_color=QColor(255,255,255,0), gradient=get_gradient('alt_color_outline'), outline_width=2,
            phase_override=get_event('startup_phase'), phases={
                'open': Phase([TextTween(char_display=1, start=0, dur=1.0, ease=QEasingCurve.OutQuint)])
            }
        ),
    ],
    button_defs=[
        ButtonDef(key=Qt.Key_Space, event_out=get_event('startup_phase_flip'), event_delta='close'),
        ButtonDef(key=Qt.Key_Space, event_out=get_event('startup_phase'), event_delta='open'),
        ButtonDef(key=Qt.Key_Space, event_out=get_event('startup_subscription_phase'), event_delta='open'),
    ],
    # pie_defs=[
    #     PieDef(
    #         p1=P(0.4, 0.6), p2=P(0.6, 0.7),
    #         names=[''] * 9,
    #         value_fns=[lambda ctx, i=i: ctx[f'test_value{i+1}']['latest'] for i in range(9)],
    #         colors=[QColor(255,106,106), QColor(255,111,151), QColor(255,126,192),
    #                 QColor(238,145,227), QColor(214,165,252), QColor(187,184,255),
    #                 QColor(164,200,255), QColor(150,213,255), QColor(149,224,255)],
    #         border_width=1.0, fill_opacity=0.1, direction='horizontal',
    #         size_label=0.0, size_name=9.0, ease_dur=0.4, ease_type=QEasingCurve.OutQuint,
    #     ),
    # ]
)

WINDOW_DEFS = []
WINDOW_DEFS.append(background_window)
WINDOW_DEFS.append(subscription_window)
WINDOW_DEFS.append(startup_window)

register_windows(WINDOW_LAYER, WINDOW_DEFS)
