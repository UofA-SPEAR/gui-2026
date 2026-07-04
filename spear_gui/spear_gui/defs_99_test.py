# from __future__ import annotations
# from typing import Any, Callable, Dict, List, Optional, Tuple
# import math

# from PySide6.QtCore import Qt, QEasingCurve
# from PySide6.QtGui  import QColor

# from spear_gui.overlay_system import (
#     P, Reset, Phase, expand_defs,
#     PolygonDef, PolygonTween, RectDef, RectTween,                              # PolygonDef
#     ArcDef,                                                                    # ArcDef
#     TextDef, TextTween, TextBlock, DataTable,                                  # TextDef
#     SliderDef,                                                                 # SliderDef
#     ButtonDef, SegmentedButtons, Segment, SevenSegmentDisplay,                 # ButtonDef
#     TextboxDef,                                                                # TextboxDef
#     GraphDef, SeriesDef,                                                       # GraphDef
#     PieDef,                                                                    # PieDef
#     WindowDef, WindowTween, register_windows,                                  # WindowDef
#     EventDef, EventListener, register_event, get_event,                        # EventDef
#     GradientDef, GradientStop, GradientTween, register_gradient, get_gradient, # GradientDef

#     P_OPEN, P_CLOSE, P_HOVER, P_UNHOVER, P_CLICK, P_RELEASE, P_SET, P_ALWAYS,
#     SYS_FPS, SYS_FRAME_TIME, SYS_MOUSE, SYS_MOUSE_X, SYS_MOUSE_Y,
#     get_spawn_event, GROUP_EVENT, STATIC, get_spawn_mouse_norm
# )

# WINDOW_LAYER = 0

# subscription_list = ['test_value1', 'test_value2', 'test_value3', 'test_value4', 'test_value5', 'test_value6', 'test_value7', 'test_value8', 'test_value9', 'test_value10']
# subscription_columns = 2
# subscription_listeners = []
# subscription_polygons = []
# subscription_texts = []
# for i in range(len(subscription_list)):
#     print(subscription_list[i])
#     x = i % subscription_columns
#     y = math.floor(i / subscription_columns)
#     target_x = x / 10 + 0.7
#     target_y = y / 10 + 0.25
#     name = f'sub_sample_pulse{i}'
#     register_event(EventDef(name=name, value=None))
#     register_gradient(GradientDef(
#         name=name, p1=P(target_x, target_y), p2=P(target_x, target_y), px1=P(0, 0), px2=P(-60, 0), target='fill', phase_event=get_event(name),
#         stops=[GradientStop(0.0, QColor(255, 0, 0, 255)), GradientStop(1.0, QColor(255, 0, 0, 0))], 
#         phases={'pulse': Phase([
#             GradientTween(stops=[GradientStop(0.0, QColor(0, 100, 0, 255)), GradientStop(1.0, QColor(0, 255, 0, 0))], start=0, dur=0, ease=QEasingCurve.OutQuint),
#             GradientTween(stops=[GradientStop(0.0, QColor(0, 0, 0, 0)), GradientStop(1.0, QColor(0, 0, 0, 0))], start=0, dur=1, ease=QEasingCurve.OutQuint),
#             ])
#         }
#     ))
#     subscription_listeners += [
#         EventListener(value_fn='pulse', targets=[get_event(name)], passthrough=True, wait_for_updates=lambda ctx: ctx[subscription_list[i]]['push_count']),
#     ]
#     subscription_polygons += [
#         PolygonDef(p=[P(target_x, target_y)]*4, px=[P(0, -15), P(0, 15), P(-60, 15), P(-60, -15)], gradient=get_gradient(name), phase_override=lambda: get_event(name).value),
#         PolygonDef(p=[P(target_x, target_y)]*6, px=[P(-3, 12), P(-3, -12), P(0, -15), P(3, -12), P(3, 12), P(0, 15)], fill_color=QColor(255, 0, 0, 255), phase_override=lambda: get_event(name).value, phases={
#             'pulse': Phase([
#                     PolygonTween(fill_color=QColor(0, 255, 0, 255), start=0, dur=0.0, ease=QEasingCurve.OutQuint),
#                     PolygonTween(fill_color=QColor(0, 100, 0, 255), start=0, dur=1.0, ease=QEasingCurve.OutQuint),
#                 ])
#             }
#         ),
#     ]
#     subscription_texts += [
#         TextDef(p=P(target_x, target_y), px=P(7, 0), h_align=0, text = subscription_list[i], uniform_scale=False),
#         TextDef(p=P(target_x, target_y), px=P(-7, 0), h_align=1, text_fn = lambda ctx: ctx[subscription_list[i]]['push_count'], uniform_scale=False),
#     ]
# subscription_window = WindowDef(p1=P(0.0, 0.0), p2=P(1.0, 1.0), listener_defs = subscription_listeners, polygon_defs = subscription_polygons, text_defs = subscription_texts)


# # register_gradient(GradientDef(
# #     name='launch_text_outline1', p1=P(0.5, 0.5), p2=P(0.5, 0.5), px1=P(-300, -150), px2=P(300, 150), target='outline', stops=[
# #         GradientStop(0.0, QColor(50, 50, 50, 255)),
# #         GradientStop(0.5, QColor(50, 50, 50, 255)),
# #         GradientStop(0.5001, QColor(50, 50, 50, 0)),
# #     ],
# # ))
# # register_gradient(GradientDef(
# #     name='launch_text_outline2', p1=P(0.5, 0.5), p2=P(0.5, 0.5), px1=P(-300, -150), px2=P(300, 150), target='outline', stops=[
# #         GradientStop(0.0, QColor(50, 50, 50, 0)),
# #         GradientStop(0.5, QColor(50, 50, 50, 0)),
# #         GradientStop(0.5001, QColor(50, 50, 50, 255)),
# #     ],
# # ))

# # register_gradient(GradientDef(
# #     name='sub_sample_pulse', p1=P(0.9, 0.5), p2=P(0.9, 0.5), px1=P(0, 0), px2=P(-60, 0), target='fill', phase_event=get_event('sub_sample_pulse'),
# #     stops=[GradientStop(0.0, QColor(0, 255, 0, 255)), GradientStop(1.0, QColor(0, 0, 0, 255))], 
# #     phases={'pulse': Phase([
# #         GradientTween(stops=[GradientStop(0.0, QColor(0, 100, 0, 255)), GradientStop(1.0, QColor(0, 255, 0, 0))], start=0, dur=0, ease=QEasingCurve.OutQuint),
# #         GradientTween(stops=[GradientStop(0.0, QColor(0, 0, 0, 0)), GradientStop(1.0, QColor(0, 0, 0, 0))], start=0, dur=1, ease=QEasingCurve.OutQuint),
# #         ])
# #     }
# # ))

# # register_gradient(GradientDef(
# #     name='sub_sample_pulse2', p1=P(0.9, 0.7), p2=P(0.9, 0.7), px1=P(0, 0), px2=P(-60, 0), target='fill', phase_event=get_event('sub_sample_pulse'),
# #     stops=[GradientStop(0.0, QColor(0, 255, 0, 255)), GradientStop(1.0, QColor(0, 0, 0, 255))], 
# #     phases={'pulse': Phase([
# #         GradientTween(stops=[GradientStop(0.0, QColor(0, 100, 0, 255)), GradientStop(1.0, QColor(0, 255, 0, 0))], start=0, dur=0, ease=QEasingCurve.OutQuint),
# #         GradientTween(stops=[GradientStop(0.0, QColor(0, 0, 0, 0)), GradientStop(1.0, QColor(0, 0, 0, 0))], start=0, dur=1, ease=QEasingCurve.OutQuint),
# #         ])
# #     }
# # ))

# WINDOW_DEFS = [
    # WindowDef(
    #     p1=P(0.0, 0.0), p2=P(1.0, 1.0),
    #     polygon_defs=[
    #         # PolygonDef(p=[P(0, 0), P(0, 0), P(0, 1), P(0, 1)], px=[P(0, 0), P(50, 50), P(50, -50), P(0, 0)], fill_color=QColor(255, 255, 255, 255),
    #         # pos_fn=lambda: [P(0, 0), P(SYS_MOUSE_X.value / 10, SYS_MOUSE_Y.value / 10), P(SYS_MOUSE_X.value / 10, SYS_MOUSE_Y.value / 10), P(0, 0)]),
    #         PolygonDef(p=[P(0.5, 0.5)]*4, px=[P(-100, -5), P(100, -5), P(100, 5), P(-100, 5)], fill_color=QColor(255, 255, 255, 255), rot_center_p=P(0.5, 0.5), rot_target_p=P(0.5, 0.5), rot_angle_initial=0, phases={
    #             'open': Phase([PolygonTween(rot_angle=700, start=0, dur=5.0, ease=QEasingCurve.OutQuint)])
    #         }),
    #     ],
    #     text_defs=[
    #         # TextDef(
    #         #     p=P(0.5, 0.5), px=P(-100, -150), text='LAUNCHING', bold=True, italic=True, v_align=1, font_size=100, color=QColor(255,255,255,0), outline_width=2,
    #         #     gradient=get_gradient('launch_text_outline1'),
    #         # ),
    #         TextDef(
    #             p=P(0.5, 0.5), px=P(-50, 100), text='SPEAR', bold=True, italic=True, font_size=400, color=QColor(255,255,255,0), outline_width=4,
    #             gradient=get_gradient('launch_text_outline1'), phases={
    #                 'open': Phase([TextTween(px=P(0, 0), start=0, dur=1.0, ease=QEasingCurve.OutBack)])
    #             }
    #         ),
    #         TextDef(
    #             p=P(0.5, 0.5), px=P(50, -100), text='SPEAR', bold=True, italic=True, font_size=400, color=QColor(255,255,255,0), outline_width=4,
    #             gradient=get_gradient('launch_text_outline2'), phases={
    #                 'open': Phase([TextTween(px=P(0, 0), start=0, dur=1.0, ease=QEasingCurve.OutBack)])
    #             }
    #         ),
    #     ],
    # ),

#     WindowDef(
#         p1=P(0.0, 0.0), p2=P(1.0, 1.0),
#         listener_defs=[
#             EventListener(value_fn='pulse', targets=[get_event('sub_sample_pulse')], passthrough=True, wait_for_updates=lambda ctx: ctx['test_value1']['push_count']),
#             EventListener(value_fn='pulse', targets=[get_event('sub_sample_pulse2')], passthrough=True, wait_for_updates=lambda ctx: ctx['test_value8']['push_count']),
#         ],
#         polygon_defs=[
#             PolygonDef(p=[P(0.9, 0.5)]*4, px=[P(0, -15), P(0, 15), P(-60, 15), P(-60, -15)], gradient=get_gradient('sub_sample_pulse'), phase_override=lambda: get_event('sub_sample_pulse').value),

#             PolygonDef(p=[P(0.9, 0.5)]*6, px=[P(-3, 12), P(-3, -12), P(0, -15), P(3, -12), P(3, 12), P(0, 15)], fill_color=QColor(255, 0, 0, 255), phase_override=lambda: get_event('sub_sample_pulse').value, phases={
#                 'pulse': Phase([
#                         PolygonTween(fill_color=QColor(0, 255, 0, 255), start=0, dur=0.0, ease=QEasingCurve.OutQuint),
#                         PolygonTween(fill_color=QColor(0, 100, 0, 255), start=0, dur=1.0, ease=QEasingCurve.OutQuint),
#                     ])
#                 }
#             ),

#             PolygonDef(p=[P(0.9, 0.7)]*4, px=[P(0, -15), P(0, 15), P(-60, 15), P(-60, -15)], gradient=get_gradient('sub_sample_pulse2'), phase_override=lambda: get_event('sub_sample_pulse2').value),

#             PolygonDef(p=[P(0.9, 0.7)]*6, px=[P(-3, 12), P(-3, -12), P(0, -15), P(3, -12), P(3, 12), P(0, 15)], fill_color=QColor(255, 0, 0, 255), phase_override=lambda: get_event('sub_sample_pulse2').value, phases={
#                 'pulse': Phase([
#                         PolygonTween(fill_color=QColor(0, 255, 0, 255), start=0, dur=0.0, ease=QEasingCurve.OutQuint),
#                         PolygonTween(fill_color=QColor(0, 100, 0, 255), start=0, dur=1.0, ease=QEasingCurve.OutQuint),
#                     ])
#                 }
#             )
#         ],
#         text_defs=[
#             TextDef(p=P(0.9, 0.5), px=P(7, 0), h_align=0, text = 'test_value1', uniform_scale=False),
#             TextDef(p=P(0.9, 0.5), px=P(-7, 0), h_align=1, text_fn = lambda ctx: ctx['test_value1']['push_count'], uniform_scale=False),
#             TextDef(p=P(0.9, 0.7), px=P(7, 0), h_align=0, text = 'test_value8', uniform_scale=False),
#             TextDef(p=P(0.9, 0.7), px=P(-7, 0), h_align=1, text_fn = lambda ctx: ctx['test_value8']['push_count'], uniform_scale=False),
#         ]
#     ),

# ]

# WINDOW_DEFS.append(subscription_window)

# register_windows(WINDOW_LAYER, WINDOW_DEFS)
