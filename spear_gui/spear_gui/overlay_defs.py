from __future__ import annotations
from typing import Callable, List
from PySide6.QtCore import QEasingCurve
from PySide6.QtGui  import QColor

from spear_gui.overlay_system import (
    Rect, RectTween,
    Phase, TextDef, TextTween, Reset,
    TrackStyle, KnobStyle, MarkStyle, ButtonStyle,
    SliderTween, KnobTween, MarkTween, ButtonTween,
    SliderDef, ButtonDef,
    P, PolygonDef, PolygonTween
)

# ──────────────────────── LOADING OVERLAY ────────────────────────

LOADING_DEFS = [
    # Background T/B/L/R
    Rect(P(0.00,0.00), P(1.00,0.50), fill_color=QColor(10,10,14), phases={
        'loaded': Phase([RectTween(P(0.00,0.00), P(1.00,0.00), start=0.30, dur=1.00, ease=QEasingCurve.OutQuint)])}),
    Rect(P(0.00,0.50), P(1.00,1.00), fill_color=QColor(10,10,14), phases={
        'loaded': Phase([RectTween(P(0.00,1.00), P(1.00,1.00), start=0.30, dur=1.00, ease=QEasingCurve.OutQuint)])}),
    Rect(P(0.00,0.00), P(0.50,1.00), fill_color=QColor(10,10,14), phases={
        'loaded': Phase([RectTween(P(0.00,0.00), P(0.00,1.00), start=0.30, dur=1.00, ease=QEasingCurve.OutQuint)])}),
    Rect(P(0.50,0.00), P(1.00,1.00), fill_color=QColor(10,10,14), phases={
        'loaded': Phase([RectTween(P(1.00,0.00), P(1.00,1.00), start=0.30, dur=1.00, ease=QEasingCurve.OutQuint)])}),

    # Background Border T/B/L/R
    Rect(P(0.50,0.50), P(0.50,0.50), px1=P(0,-1), px2=P(0,0), fill_color=QColor(255,255,255), phases={
        'loaded': Phase([
            RectTween(P(0.00,0.00), P(1.00,0.00), px1=P(0,-1), px2=P(0,0),  fill_color=QColor(255,255,255),              start=0.30, dur=1.00, ease=QEasingCurve.OutQuint),
            RectTween(P(0.00,0.00), P(1.00,0.00), px1=P(0,-1), px2=P(0,0),  fill_color=QColor(255,255,255,0),             start=2.50, dur=1.00, ease=QEasingCurve.InQuint)])}),
    Rect(P(0.50,0.50), P(0.50,0.50), px1=P(0,0),  px2=P(0,1), fill_color=QColor(255,255,255), phases={
        'loaded': Phase([
            RectTween(P(0.00,1.00), P(1.00,1.00), px1=P(0,0),  px2=P(0,1),  fill_color=QColor(255,255,255),              start=0.30, dur=1.00, ease=QEasingCurve.OutQuint),
            RectTween(P(0.00,1.00), P(1.00,1.00), px1=P(0,0),  px2=P(0,1),  fill_color=QColor(255,255,255,0),             start=2.50, dur=1.00, ease=QEasingCurve.InQuint)])}),
    Rect(P(0.50,0.50), P(0.50,0.50), px1=P(-1,0), px2=P(0,0), fill_color=QColor(255,255,255), phases={
        'loaded': Phase([
            RectTween(P(0.00,0.00), P(0.00,1.00), px1=P(-1,0), px2=P(0,0),  fill_color=QColor(255,255,255),              start=0.30, dur=1.00, ease=QEasingCurve.OutQuint),
            RectTween(P(0.00,0.00), P(0.00,1.00), px1=P(-1,0), px2=P(0,0),  fill_color=QColor(255,255,255,0),             start=2.50, dur=1.00, ease=QEasingCurve.InQuint)])}),
    Rect(P(0.50,0.50), P(0.50,0.50), px1=P(0,0),  px2=P(1,0), fill_color=QColor(255,255,255), phases={
        'loaded': Phase([
            RectTween(P(1.00,0.00), P(1.00,1.00), px1=P(0,0),  px2=P(1,0),  fill_color=QColor(255,255,255),              start=0.30, dur=1.00, ease=QEasingCurve.OutQuint),
            RectTween(P(1.00,0.00), P(1.00,1.00), px1=P(0,0),  px2=P(1,0),  fill_color=QColor(255,255,255,0),             start=2.50, dur=1.00, ease=QEasingCurve.InQuint)])}),

    # Horizontal Corner TL/TR/BL/BR
    Rect(P(0.00,-0.01), P(0.50,-0.01), fill_color=QColor(255,255,255), uniform_scale=True, phases={
        'create': Phase([
            RectTween(P(0.30,0.47), P(0.50,0.48),                                                                         start=0.30, dur=0.25, ease=QEasingCurve.OutCirc),
            RectTween(P(0.25,0.45), P(0.35,0.46), tr=(P(0,0), P(0,0)),                                                    start=0.55, dur=0.50, ease=QEasingCurve.InOutCirc)]),
        'loaded': Phase([
            RectTween(P(0.25,0.45), P(0.25,0.46),                                                                         start=0.30, dur=0.30, ease=QEasingCurve.OutCirc)])}),
    Rect(P(0.50,-0.01), P(1.00,-0.01), fill_color=QColor(255,255,255), uniform_scale=True, phases={
        'create': Phase([
            RectTween(P(0.50,0.47), P(0.70,0.48),                                                                         start=0.30, dur=0.25, ease=QEasingCurve.OutCirc),
            RectTween(P(0.65,0.45), P(0.75,0.46), tl=(P(0,0), P(0,0)),                                                    start=0.55, dur=0.50, ease=QEasingCurve.InOutCirc)]),
        'loaded': Phase([
            RectTween(P(0.75,0.45), P(0.75,0.46),                                                                         start=0.30, dur=0.30, ease=QEasingCurve.OutCirc)])}),
    Rect(P(0.00,1.00), P(0.50,1.00), fill_color=QColor(255,255,255), uniform_scale=True, phases={
        'create': Phase([
            RectTween(P(0.30,0.52), P(0.50,0.53),                                                                         start=0.30, dur=0.25, ease=QEasingCurve.OutCirc),
            RectTween(P(0.25,0.54), P(0.35,0.55), br=(P(0,0), P(0,0)),                                                    start=0.55, dur=0.50, ease=QEasingCurve.InOutCirc)]),
        'loaded': Phase([
            RectTween(P(0.25,0.54), P(0.25,0.55),                                                                         start=0.30, dur=0.30, ease=QEasingCurve.OutCirc)])}),
    Rect(P(0.50,1.00), P(1.00,1.00), fill_color=QColor(255,255,255), uniform_scale=True, phases={
        'create': Phase([
            RectTween(P(0.50,0.52), P(0.70,0.53),                                                                         start=0.30, dur=0.25, ease=QEasingCurve.OutCirc),
            RectTween(P(0.65,0.54), P(0.75,0.55), bl=(P(0,0), P(0,0)),                                                    start=0.55, dur=0.50, ease=QEasingCurve.InOutCirc)]),
        'loaded': Phase([
            RectTween(P(0.75,0.54), P(0.75,0.55),                                                                         start=0.30, dur=0.30, ease=QEasingCurve.OutCirc)])}),

    # Horizontal Thin Corner TL/TR/BL/BR
    Rect(P(0.30,0.475), P(0.50,0.480), fill_color=QColor(255,255,255), uniform_scale=True, phases={
        'create': Phase([
            RectTween(P(0.30,0.475),  P(0.50,0.480),                                                                      start=0.55, dur=0.00, ease=QEasingCurve.InOutCirc),
            RectTween(P(0.345,0.455), P(0.445,0.460), tr=(P(0,0), P(0,0)),                                                start=0.55, dur=0.50, ease=QEasingCurve.InOutCirc),
            RectTween(P(0.345,0.455), P(0.395,0.460), tr=(P(0,0), P(0,0)),                                                start=1.05, dur=1.75, ease=QEasingCurve.InCirc)]),
        'loaded': Phase([
            RectTween(P(0.345,0.455), P(0.345,0.460),                                                                     start=0.00, dur=0.30, ease=QEasingCurve.OutCirc)])}),
    Rect(P(0.50,0.475), P(0.70,0.480), fill_color=QColor(255,255,255), uniform_scale=True, phases={
        'create': Phase([
            RectTween(P(0.50,0.475),  P(0.70,0.480),                                                                      start=0.55, dur=0.00, ease=QEasingCurve.InOutCirc),
            RectTween(P(0.555,0.455), P(0.655,0.460), tl=(P(0,0), P(0,0)),                                                start=0.55, dur=0.50, ease=QEasingCurve.InOutCirc),
            RectTween(P(0.605,0.455), P(0.655,0.460), tl=(P(0,0), P(0,0)),                                                start=1.05, dur=1.75, ease=QEasingCurve.InCirc)]),
        'loaded': Phase([
            RectTween(P(0.655,0.455), P(0.655,0.460),                                                                     start=0.00, dur=0.30, ease=QEasingCurve.OutCirc)])}),
    Rect(P(0.30,0.52), P(0.50,0.525), fill_color=QColor(255,255,255), uniform_scale=True, phases={
        'create': Phase([
            RectTween(P(0.30,0.52),   P(0.50,0.525),                                                                      start=0.55, dur=0.00, ease=QEasingCurve.InOutCirc),
            RectTween(P(0.345,0.54),  P(0.445,0.545), br=(P(0,0), P(0,0)),                                                start=0.55, dur=0.50, ease=QEasingCurve.InOutCirc),
            RectTween(P(0.345,0.54),  P(0.395,0.545), br=(P(0,0), P(0,0)),                                                start=1.05, dur=1.75, ease=QEasingCurve.InCirc)]),
        'loaded': Phase([
            RectTween(P(0.345,0.54),  P(0.345,0.545),                                                                     start=0.00, dur=0.30, ease=QEasingCurve.OutCirc)])}),
    Rect(P(0.50,0.52), P(0.70,0.525), fill_color=QColor(255,255,255), uniform_scale=True, phases={
        'create': Phase([
            RectTween(P(0.50,0.52),   P(0.70,0.525),                                                                      start=0.55, dur=0.00, ease=QEasingCurve.InOutCirc),
            RectTween(P(0.555,0.54),  P(0.655,0.545), bl=(P(0,0), P(0,0)),                                                start=0.55, dur=0.50, ease=QEasingCurve.InOutCirc),
            RectTween(P(0.605,0.54),  P(0.655,0.545), bl=(P(0,0), P(0,0)),                                                start=1.05, dur=1.75, ease=QEasingCurve.InCirc)]),
        'loaded': Phase([
            RectTween(P(0.655,0.54),  P(0.655,0.545),                                                                     start=0.00, dur=0.30, ease=QEasingCurve.OutCirc)])}),

    # Vertical Corner TL/BL/TR/BR
    Rect(P(0.00,0.00), P(0.005625,0.50), fill_color=QColor(255,255,255), uniform_scale=True, phases={
        'create': Phase([
            RectTween(P(0.30,0.47),  P(0.305625,0.50),                                                                    start=0.30, dur=0.25, ease=QEasingCurve.OutCirc),
            RectTween(P(0.25,0.45),  P(0.255625,0.47),                                                                    start=0.55, dur=0.50, ease=QEasingCurve.InOutCirc)]),
        'loaded': Phase([
            RectTween(P(0.25,0.47),  P(0.255625,0.47),                                                                    start=0.60, dur=0.30, ease=QEasingCurve.OutCirc)])}),
    Rect(P(0.00,0.50), P(0.005625,1.00), fill_color=QColor(255,255,255), uniform_scale=True, phases={
        'create': Phase([
            RectTween(P(0.30,0.50),  P(0.305625,0.53),                                                                    start=0.30, dur=0.25, ease=QEasingCurve.OutCirc),
            RectTween(P(0.25,0.53),  P(0.255625,0.55),                                                                    start=0.55, dur=0.50, ease=QEasingCurve.InOutCirc)]),
        'loaded': Phase([
            RectTween(P(0.25,0.53),  P(0.255625,0.53),                                                                    start=0.60, dur=0.30, ease=QEasingCurve.OutCirc)])}),
    Rect(P(1.00,0.00), P(1.005625,0.50), fill_color=QColor(255,255,255), uniform_scale=True, phases={
        'create': Phase([
            RectTween(P(0.694375,0.47), P(0.70,0.50),                                                                     start=0.30, dur=0.25, ease=QEasingCurve.OutCirc),
            RectTween(P(0.744375,0.45), P(0.75,0.47),                                                                     start=0.55, dur=0.50, ease=QEasingCurve.InOutCirc)]),
        'loaded': Phase([
            RectTween(P(0.744375,0.47), P(0.75,0.47),                                                                     start=0.60, dur=0.30, ease=QEasingCurve.OutCirc)])}),
    Rect(P(1.00,0.00), P(1.005625,0.50), fill_color=QColor(255,255,255), uniform_scale=True, phases={
        'create': Phase([
            RectTween(P(0.694375,0.50), P(0.70,0.53),                                                                     start=0.30, dur=0.25, ease=QEasingCurve.OutCirc),
            RectTween(P(0.744375,0.53), P(0.75,0.55),                                                                     start=0.55, dur=0.50, ease=QEasingCurve.InOutCirc)]),
        'loaded': Phase([
            RectTween(P(0.744375,0.53), P(0.75,0.53),                                                                     start=0.60, dur=0.30, ease=QEasingCurve.OutCirc)])}),

    # Large Square L/R
    Rect(P(0.50,0.50), P(0.50,0.50), fill_color=QColor(180,180,180), uniform_scale=True, phases={
        'create': Phase([
            RectTween(P(0.50-10/1920,0.50-10/1080), P(0.50+10/1920,0.50+10/1080),                                        start=0.00, dur=0.30, ease=QEasingCurve.OutCirc),
            RectTween(P(0.23,        0.50-10/1080), P(0.23+20/1920,0.50+10/1080),                                        start=0.30, dur=1.00, ease=QEasingCurve.OutBack)]),
        'loaded': Phase([
            RectTween(P(0.25,        0.50-10/1080), P(0.255625,    0.50+10/1080), fill_color=QColor(255,255,255),        start=0.30, dur=0.30, ease=QEasingCurve.OutCirc),
            RectTween(P(0.25,        0.50),          P(0.255625,    0.50),                                                start=0.90, dur=0.30, ease=QEasingCurve.OutCirc)])}),
    Rect(P(0.50,0.50), P(0.50,0.50), fill_color=QColor(180,180,180), uniform_scale=True, phases={
        'create': Phase([
            RectTween(P(0.50-10/1920,0.50-10/1080), P(0.50+10/1920,0.50+10/1080),                                        start=0.00, dur=0.30, ease=QEasingCurve.OutCirc),
            RectTween(P(0.77-20/1920,0.50-10/1080), P(0.77,        0.50+10/1080),                                        start=0.30, dur=1.00, ease=QEasingCurve.OutBack)]),
        'loaded': Phase([
            RectTween(P(0.75-0.005625,0.50-10/1080), P(0.75,       0.50+10/1080), fill_color=QColor(255,255,255),        start=0.30, dur=0.30, ease=QEasingCurve.OutCirc),
            RectTween(P(0.75-0.005625,0.50),          P(0.75,       0.50),                                                start=0.90, dur=0.30, ease=QEasingCurve.OutCirc)])}),

    # Small Square TL/TR/BL/BR
    Rect(P(0.50,0.50), P(0.50,0.50), fill_color=QColor(180,180,180), uniform_scale=True, phases={
        'create': Phase([
            RectTween(P(0.50-5/1920, 0.50-5/1080),  P(0.50+5/1920, 0.50+5/1080),                                        start=0.00, dur=0.30, ease=QEasingCurve.OutCirc),
            RectTween(P(0.50-70/1920,0.50-70/1080), P(0.50-60/1920,0.50-60/1080),                                        start=0.30, dur=1.00, ease=QEasingCurve.OutBack)]),
        'loaded': Phase([
            RectTween(P(0.50-5/1920, 0.50-70/1080), P(0.50+5/1920, 0.50-60/1080), fill_color=QColor(255,255,255),       start=0.30, dur=0.30, ease=QEasingCurve.OutCirc),
            RectTween(P(0.50,        0.50),           P(0.50,        0.50),                                               start=0.60, dur=0.30, ease=QEasingCurve.OutCirc)])}),
    Rect(P(0.50,0.50), P(0.50,0.50), fill_color=QColor(180,180,180), uniform_scale=True, phases={
        'create': Phase([
            RectTween(P(0.50-5/1920, 0.50-5/1080),  P(0.50+5/1920, 0.50+5/1080),                                        start=0.00, dur=0.30, ease=QEasingCurve.OutCirc),
            RectTween(P(0.50+70/1920,0.50-70/1080), P(0.50+80/1920,0.50-60/1080),                                        start=0.30, dur=1.00, ease=QEasingCurve.OutBack)]),
        'loaded': Phase([
            RectTween(P(0.50-5/1920, 0.50-70/1080), P(0.50+5/1920, 0.50-60/1080), fill_color=QColor(255,255,255),       start=0.30, dur=0.30, ease=QEasingCurve.OutCirc),
            RectTween(P(0.50,        0.50),           P(0.50,        0.50),                                               start=0.60, dur=0.30, ease=QEasingCurve.OutCirc)])}),
    Rect(P(0.50,0.50), P(0.50,0.50), fill_color=QColor(180,180,180), uniform_scale=True, phases={
        'create': Phase([
            RectTween(P(0.50-5/1920, 0.50-5/1080),  P(0.50+5/1920, 0.50+5/1080),                                        start=0.00, dur=0.30, ease=QEasingCurve.OutCirc),
            RectTween(P(0.50-70/1920,0.50+70/1080), P(0.50-60/1920,0.50+80/1080),                                        start=0.30, dur=1.00, ease=QEasingCurve.OutBack)]),
        'loaded': Phase([
            RectTween(P(0.50-5/1920, 0.50+70/1080), P(0.50+5/1920, 0.50+80/1080), fill_color=QColor(255,255,255),       start=0.30, dur=0.30, ease=QEasingCurve.OutCirc),
            RectTween(P(0.50,        0.50),           P(0.50,        0.50),                                               start=0.60, dur=0.30, ease=QEasingCurve.OutCirc)])}),
    Rect(P(0.50,0.50), P(0.50,0.50), fill_color=QColor(180,180,180), uniform_scale=True, phases={
        'create': Phase([
            RectTween(P(0.50-5/1920, 0.50-5/1080),  P(0.50+5/1920, 0.50+5/1080),                                        start=0.00, dur=0.30, ease=QEasingCurve.OutCirc),
            RectTween(P(0.50+70/1920,0.50+70/1080), P(0.50+80/1920,0.50+80/1080),                                        start=0.30, dur=1.00, ease=QEasingCurve.OutBack)]),
        'loaded': Phase([
            RectTween(P(0.50-5/1920, 0.50+70/1080), P(0.50+5/1920, 0.50+80/1080), fill_color=QColor(255,255,255),       start=0.30, dur=0.30, ease=QEasingCurve.OutCirc),
            RectTween(P(0.50,        0.50),           P(0.50,        0.50),                                               start=0.60, dur=0.30, ease=QEasingCurve.OutCirc)])}),

    # Progress Bar Outline T/B/L/R
    Rect(P(0.50,0.50), P(0.50,0.50), fill_color=QColor(120,120,120), uniform_scale=True, phases={
        'create': Phase([
            RectTween(P(0.25+0.005625*2,0.45+0.01*2), P(0.25+0.005625*2+0.05625-0.005625*2*2, 0.45+0.01*2+0.0025),      start=0.30, dur=0.70, ease=QEasingCurve.InOutQuad),
            RectTween(P(0.25+0.005625*2,0.45+0.01*2), P(0.75-0.005625*2,                       0.45+0.01*2+0.0025),      start=1.00, dur=1.00, ease=QEasingCurve.InOutQuad)]),
        'loaded': Phase([
            RectTween(P(0.25+0.005625*2,0.45+0.01*2), P(0.75-0.005625*2,                       0.45+0.01*2+0.0025), fill_color=QColor(255,255,255), start=0.30, dur=0.30, ease=QEasingCurve.InOutQuad),
            RectTween(P(0.05+0.005625*2,0.45+0.01*2), P(0.05+0.005625*2,                       0.45+0.01*2+0.0025),                                 start=0.60, dur=1.20, ease=QEasingCurve.OutQuint)])}),
    Rect(P(0.50,0.50), P(0.50,0.50), fill_color=QColor(120,120,120), uniform_scale=True, phases={
        'create': Phase([
            RectTween(P(0.25+0.005625*2,0.55-0.01*2-0.0025), P(0.25+0.005625*2+0.05625-0.005625*2*2, 0.55-0.01*2),      start=0.30, dur=0.70, ease=QEasingCurve.InOutQuad),
            RectTween(P(0.25+0.005625*2,0.55-0.01*2-0.0025), P(0.75-0.005625*2,                       0.55-0.01*2),      start=1.00, dur=1.00, ease=QEasingCurve.InOutQuad)]),
        'loaded': Phase([
            RectTween(P(0.25+0.005625*2,0.55-0.01*2-0.0025), P(0.75-0.005625*2,                       0.55-0.01*2), fill_color=QColor(255,255,255), start=0.30, dur=0.30, ease=QEasingCurve.InOutQuad),
            RectTween(P(0.95+0.005625*2,0.55-0.01*2-0.0025), P(0.95+0.005625*2,                       0.55-0.01*2),                                 start=0.60, dur=1.20, ease=QEasingCurve.OutQuint)])}),
    Rect(P(0.50,0.50), P(0.50,0.50), fill_color=QColor(120,120,120), uniform_scale=True, phases={
        'create': Phase([
            RectTween(P(0.25+0.005625*2,0.45+0.01*2), P(0.25+0.005625*2+0.00140625, 0.55-0.01*2),                        start=0.30, dur=0.70, ease=QEasingCurve.InOutQuad)]),
        'loaded': Phase([
            RectTween(P(0.25+0.005625*2,0.55-0.01*2), P(0.25+0.005625*2+0.00140625, 0.55-0.01*2), fill_color=QColor(255,255,255), start=0.30, dur=0.30, ease=QEasingCurve.OutCirc)])}),
    Rect(P(0.50,0.50), P(0.50,0.50), fill_color=QColor(120,120,120), uniform_scale=True, phases={
        'create': Phase([
            RectTween(P(0.25+0.005625*2+0.05625-0.005625*2*2,0.45+0.01*2), P(0.25+0.005625*2+0.05625-0.005625*2*2+0.00140625, 0.55-0.01*2), start=0.30, dur=0.70, ease=QEasingCurve.InOutQuad),
            RectTween(P(0.75-0.005625*2-0.00140625,           0.45+0.01*2), P(0.75-0.005625*2,                               0.55-0.01*2), start=1.00, dur=1.00, ease=QEasingCurve.InOutQuad)]),
        'loaded': Phase([
            RectTween(P(0.75-0.005625*2-0.00140625,0.45+0.01*2), P(0.75-0.005625*2, 0.45+0.01*2), fill_color=QColor(255,255,255), start=0.30, dur=0.30, ease=QEasingCurve.OutCirc)])}),

    # Progress Bar
    Rect(P(0.50,0.45+0.01*3), P(0.50,0.55-0.01*3), fill_color=QColor(255,255,255), uniform_scale=True, phases={
        'create': Phase([
            RectTween(P(0.25+0.005625*3,0.45+0.01*3), P(0.25+0.005625*3+0.05625-0.005625*3*2, 0.55-0.01*3),              start=0.30, dur=0.70, ease=QEasingCurve.InOutQuad),
            RectTween(P(0.25+0.005625*3,0.45+0.01*3), P(0.75-0.005625*3,                       0.55-0.01*3),              start=1.00, dur=1.80, ease=QEasingCurve.InOutCirc)]),
        'loaded': Phase([
            RectTween(P(0.25+0.005625*3,0.45+0.01*3), P(0.75-0.005625*3, 0.55-0.01*3),                                   start=0.00, dur=0.30, ease=QEasingCurve.OutCirc),
            RectTween(P(0.50,          0.45+0.01*3), P(0.50,             0.55-0.01*3),                                    start=0.30, dur=0.25, ease=QEasingCurve.OutCirc)])}),
]

LOADING_TEXT_DEFS = []

# ──────────────────────── SELECTION OVERLAY ────────────────────────

SELECTION_DEFS = [
    # Outline T/B/L/R
    Rect(P(0.00,0.00), P(0.00,0.00), px1=P(0,0),  px2=P(0,2),  fill_color=QColor(255,255,255), phases={
        'selected':   Phase([RectTween(P(0.00,0.00), P(1.00,0.00), px1=P(0,0),  px2=P(0,2),  fill_color=QColor(255,255,255), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)]),
        'unselected': Phase([RectTween(P(0.00,0.00), P(1.00,0.00), px1=P(0,0),  px2=P(0,2),  fill_color=QColor(127,127,127), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)]),
        'unfocused':  Phase([RectTween(P(0.00,0.00), P(0.00,0.00), px1=P(0,0),  px2=P(0,2),  fill_color=QColor(127,127,127), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)])}),
    Rect(P(1.00,1.00), P(1.00,1.00), px1=P(0,-2), px2=P(0,0),  fill_color=QColor(255,255,255), phases={
        'selected':   Phase([RectTween(P(0.00,1.00), P(1.00,1.00), px1=P(0,-2), px2=P(0,0),  fill_color=QColor(255,255,255), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)]),
        'unselected': Phase([RectTween(P(0.00,1.00), P(1.00,1.00), px1=P(0,-2), px2=P(0,0),  fill_color=QColor(127,127,127), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)]),
        'unfocused':  Phase([RectTween(P(0.00,1.00), P(1.00,1.00), px1=P(0,-2), px2=P(0,0),  fill_color=QColor(127,127,127), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)])}),
    Rect(P(0.00,0.00), P(0.00,0.00), px1=P(0,0),  px2=P(2,0),  fill_color=QColor(255,255,255), phases={
        'selected':   Phase([RectTween(P(0.00,0.00), P(0.00,1.00), px1=P(0,0),  px2=P(2,0),  fill_color=QColor(255,255,255), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)]),
        'unselected': Phase([RectTween(P(0.00,0.00), P(0.00,1.00), px1=P(0,0),  px2=P(2,0),  fill_color=QColor(127,127,127), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)]),
        'unfocused':  Phase([RectTween(P(0.00,0.00), P(0.00,0.00), px1=P(0,0),  px2=P(2,0),  fill_color=QColor(127,127,127), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)])}),
    Rect(P(1.00,1.00), P(1.00,1.00), px1=P(-2,0), px2=P(0,0),  fill_color=QColor(255,255,255), phases={
        'selected':   Phase([RectTween(P(1.00,0.00), P(1.00,1.00), px1=P(-2,0), px2=P(0,0),  fill_color=QColor(255,255,255), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)]),
        'unselected': Phase([RectTween(P(1.00,0.00), P(1.00,1.00), px1=P(-2,0), px2=P(0,0),  fill_color=QColor(127,127,127), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)]),
        'unfocused':  Phase([RectTween(P(1.00,1.00), P(1.00,1.00), px1=P(-2,0), px2=P(0,0),  fill_color=QColor(127,127,127), start=0.00, dur=1.00, ease=QEasingCurve.OutQuint)])}),

    # Corner HTR/VTR/HBL/VBL
    Rect(P(-0.75,0.00), P(0.00,0.00), px1=P(0,10), px2=P(0,15), fill_color=QColor(255,255,255), phases={
        'selected':   Phase([Reset(),
                             RectTween(P(0.50,0.00), P(1.00,0.00), px1=P(-10,10), px2=P(0,15),                            start=0.00, dur=0.50, ease=QEasingCurve.InQuint),
                             RectTween(P(1.00,0.00), P(1.00,0.00), px1=P(-30,10), px2=P(20,15), bl=(P(0,0),P(-20,0)),     start=0.50, dur=1.00, ease=QEasingCurve.OutQuint)]),
        'unselected': Phase([RectTween(P(1.00,0.00), P(1.00,0.00), px1=P(-10,10), px2=P(0,15),                            start=0.00, dur=0.50, ease=QEasingCurve.InQuint)])}),
    Rect(P(1.00,0.00), P(1.00,0.00), px1=P(-15,10), px2=P(5,10), fill_color=QColor(255,255,255), phases={
        'selected':   Phase([Reset(),
                             RectTween(P(1.00,0.00), P(1.00,0.00), px1=P(-15,10), px2=P(5,80),  bl=(P(0,0),P(-20,0)),     start=0.50, dur=0.50, ease=QEasingCurve.OutQuint)]),
        'unselected': Phase([RectTween(P(1.00,0.00), P(1.00,1.00), px1=P(-15,10), px2=P(5,10),                            start=0.00, dur=0.50, ease=QEasingCurve.InQuint),
                             RectTween(P(1.00,1.00), P(1.00,1.00), px1=P(-15,0),  px2=P(5,10),                            start=0.50, dur=0.50, ease=QEasingCurve.OutQuint)])}),
    Rect(P(1.00,1.00), P(1.00,1.00), px1=P(10,-15), px2=P(10,-10), fill_color=QColor(255,255,255), phases={
        'selected':   Phase([Reset(),
                             RectTween(P(0.00,1.00), P(0.50,1.00), px1=P(10,-15), px2=P(10,-10),                          start=0.00, dur=0.50, ease=QEasingCurve.InQuint),
                             RectTween(P(0.00,1.00), P(0.00,1.00), px1=P(10,-15), px2=P(30,-10), tr=(P(0,0),P(20,0)),     start=0.50, dur=1.00, ease=QEasingCurve.OutQuint)]),
        'unselected': Phase([RectTween(P(0.00,1.00), P(0.00,1.00), px1=P(10,-15), px2=P(10,-10),                          start=0.00, dur=0.50, ease=QEasingCurve.InQuint)])}),
    Rect(P(0.00,1.00), P(0.00,1.00), px1=P(10,-15), px2=P(15,-15), fill_color=QColor(255,255,255), phases={
        'selected':   Phase([Reset(),
                             RectTween(P(0.00,1.00), P(0.00,1.00), px1=P(10,-80), px2=P(15,-10), tr=(P(0,0),P(20,0)),     start=0.50, dur=0.50, ease=QEasingCurve.OutQuint)]),
        'unselected': Phase([RectTween(P(0.00,0.00), P(0.00,1.00), px1=P(10,-15), px2=P(15,-15),                          start=0.00, dur=0.50, ease=QEasingCurve.InQuint),
                             RectTween(P(0.00,0.00), P(0.00,0.00), px1=P(10,0),   px2=P(15,-15),                          start=0.50, dur=0.50, ease=QEasingCurve.OutQuint)])}),
]

SELECTION_TEXT_DEFS = [
    TextDef(1.00, 0.00, '', 14.0, QColor(255,255,255,0), {
        'selected':   Phase([TextTween(1.00, 0.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255,255,255,220), 1.00, 0.00, 14.0, -20, 15)]),
        'unselected': Phase([TextTween(1.00, 0.00, 0.00, 0.30, QEasingCurve.OutQuint, QColor(255,255,255,80),  1.00, 0.00, 14.0, -20, 15)]),
        'unfocused':  Phase([TextTween(1.00, 0.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255,255,255,0),   1.00, 0.00, 14.0, -20, 15)]),
    }, True, False, 'Oxanium SemiBold', 1.00, 0.00, False, 0, 15, lambda cam: cam.name, True),
    TextDef(1.00, 0.00, '', 14.0, QColor(255,255,255,0), {
        'selected':   Phase([TextTween(1.00, 0.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255,255,255,220), 1.00, 0.00, 14.0, -20, 35)]),
        'unselected': Phase([TextTween(1.00, 0.00, 0.00, 0.30, QEasingCurve.OutQuint, QColor(255,255,255,80),  1.00, 0.00, 14.0, -20, 35)]),
        'unfocused':  Phase([TextTween(1.00, 0.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255,255,255,0),   1.00, 0.00, 14.0, -20, 35)]),
    }, True, False, 'Oxanium SemiBold', 1.00, 0.00, False, 0, 15, lambda cam: cam.serial, True),
    TextDef(0.00, 0.00, 'CAMERA #<#>', 14.0, QColor(255,255,255,0), {
        'selected':   Phase([TextTween(0.00, 0.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255,255,255,220), 0.00, 0.00, 14.0, 20, 15)]),
        'unselected': Phase([TextTween(0.00, 0.00, 0.00, 0.30, QEasingCurve.OutQuint, QColor(255,255,255,80),  0.00, 0.00, 14.0, 20, 15)]),
        'unfocused':  Phase([TextTween(0.00, 0.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255,255,255,0),   0.00, 0.00, 14.0, 20, 15)]),
    }, True, False, 'Oxanium SemiBold', 1.00, 0.00, False, 0, 15, lambda cam: cam.position, True),
    TextDef(0.00, 1.00, 'EXPOSURE: <#>', 9.0, QColor(255,255,255,0), {
        'selected':   Phase([TextTween(0.00, 1.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255,255,255,220), 0.00, 1.00, 9.0, 20, -15)]),
        'unselected': Phase([TextTween(0.00, 1.00, 0.00, 0.30, QEasingCurve.OutQuint, QColor(255,255,255,80),  0.00, 1.00, 9.0, 20, -15)]),
        'unfocused':  Phase([TextTween(0.00, 1.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255,255,255,0),   0.00, 1.00, 9.0, 20, -15)]),
    }, False, False, 'Oxanium SemiBold', 1.00, 1.00, False, 0, -15, lambda cam: cam.exposure, True),
    TextDef(0.00, 1.00, 'GAIN: <#>', 9.0, QColor(255,255,255,0), {
        'selected':   Phase([TextTween(0.00, 1.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255,255,255,220), 0.00, 1.00, 9.0, 20, -30)]),
        'unselected': Phase([TextTween(0.00, 1.00, 0.00, 0.30, QEasingCurve.OutQuint, QColor(255,255,255,80),  0.00, 1.00, 9.0, 20, -30)]),
        'unfocused':  Phase([TextTween(0.00, 1.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255,255,255,0),   0.00, 1.00, 9.0, 20, -30)]),
    }, False, False, 'Oxanium SemiBold', 1.00, 1.00, False, 0, -15, lambda cam: cam.gain, True),
    TextDef(0.00, 1.00, 'GAMMA: <#>', 9.0, QColor(255,255,255,0), {
        'selected':   Phase([TextTween(0.00, 1.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255,255,255,220), 0.00, 1.00, 9.0, 20, -45)]),
        'unselected': Phase([TextTween(0.00, 1.00, 0.00, 0.30, QEasingCurve.OutQuint, QColor(255,255,255,80),  0.00, 1.00, 9.0, 20, -45)]),
        'unfocused':  Phase([TextTween(0.00, 1.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255,255,255,0),   0.00, 1.00, 9.0, 20, -45)]),
    }, False, False, 'Oxanium SemiBold', 1.00, 1.00, False, 0, -15, lambda cam: cam.gamma, True),
]

# ──────────────────────── SETTING OVERLAY ────────────────────────

DEFAULT_TRACK        = TrackStyle(color=QColor(255,255,255,40), filled_color=QColor(255,255,255,255), thickness=8.0)
DEFAULT_KNOB         = KnobStyle(color=QColor(255,255,255), size=8.0, shape='diamond')
DEFAULT_MARK         = MarkStyle(tick_color=QColor(255,255,255,255), fill_color=QColor(255,255,255,255), tick_width=4, tick_height=18.0, rect_height=8.0)

def _val_text(unit: str) -> Callable[[float, float], str]:
    def fn(val: float, delta: float) -> str:
        s = f"{int(val)}{unit}"
        if delta != 0: s += f"  ({int(delta):+})"
        return s
    return fn

SETTING_DEFS = [
    Rect(P(0.10,0.50), P(0.90,0.50), fill_color=QColor(8,8,8,127), phases={
        'open':  Phase([RectTween(P(0.10,0.10), P(0.90,0.90),                                                             start=0.30, dur=0.50, ease=QEasingCurve.OutQuint)]),
        'close': Phase([RectTween(P(0.10,0.50), P(0.90,0.50),                                                             start=0.00, dur=0.50, ease=QEasingCurve.OutQuint)])}),
    Rect(P(0.10,0.50), P(0.90,0.50), px1=P(0,-1), px2=P(0,1), fill_color=QColor(255,255,255,0), phases={
        'open':  Phase([Reset(), RectTween(P(0.10,0.10), P(0.90,0.10), px1=P(0,-1), px2=P(0,1), fill_color=QColor(255,255,255,255), start=0.00, dur=0.75, ease=QEasingCurve.OutQuint)]),
        'close': Phase([         RectTween(P(0.10,0.50), P(0.90,0.50), px1=P(0,-1), px2=P(0,1), fill_color=QColor(255,255,255,0),   start=0.00, dur=0.75, ease=QEasingCurve.OutQuint)])}),
    Rect(P(0.10,0.50), P(0.90,0.50), px1=P(0,0),  px2=P(0,2), fill_color=QColor(255,255,255,0), phases={
        'open':  Phase([Reset(), RectTween(P(0.10,0.90), P(0.90,0.90), px1=P(0,0),  px2=P(0,2), fill_color=QColor(255,255,255,255), start=0.00, dur=0.75, ease=QEasingCurve.OutQuint)]),
        'close': Phase([         RectTween(P(0.10,0.50), P(0.90,0.50), px1=P(0,0),  px2=P(0,2), fill_color=QColor(255,255,255,0),   start=0.00, dur=0.75, ease=QEasingCurve.OutQuint)])}),
    Rect(P(0.10,0.10), P(0.10,0.10), px1=P(0,-8), px2=P(0,100), fill_color=QColor(255,255,255,0), tr=(P(0,0),P(100,0)), phases={
        'open':  Phase([Reset(), RectTween(P(0.10,0.10), P(0.10,0.10), px1=P(0,-8), px2=P(100,100), tr=(P(0,0),P(-100,0)), fill_color=QColor(255,255,255,255), start=0.00, dur=0.75, ease=QEasingCurve.OutQuint)]),
        'close': Phase([         RectTween(P(0.10,0.50), P(0.10,0.50), px1=P(0,-8), px2=P(0,8),                            fill_color=QColor(255,255,255,0),   start=0.00, dur=0.75, ease=QEasingCurve.OutQuint)])}),
    Rect(P(0.90,0.90), P(0.90,0.90), px1=P(-100,0), px2=P(100,8), fill_color=QColor(255,255,255,0), bl=(P(0,0),P(-100,0)), phases={
        'open':  Phase([Reset(), RectTween(P(0.90,0.90), P(0.90,0.90), px1=P(-100,0), px2=P(100,8), bl=(P(0,0),P(-100,0)), fill_color=QColor(255,255,255,255), start=0.00, dur=0.75, ease=QEasingCurve.OutQuint)]),
        'close': Phase([         RectTween(P(0.90,0.50), P(0.90,0.50), px1=P(0,0),    px2=P(0,8),                           fill_color=QColor(255,255,255,0),   start=0.00, dur=0.75, ease=QEasingCurve.OutQuint)])}),
    Rect(P(0.10,0.10), P(0.10,0.10), px1=P(-8,-8), px2=P(8,0),  fill_color=QColor(255,255,255,0), bl=(P(0,0),P(0,100)), phases={
        'open':  Phase([Reset(), RectTween(P(0.10,0.10), P(0.10,0.10), px1=P(-8,-8), px2=P(8,100), bl=(P(0,0),P(0,100)),  fill_color=QColor(255,255,255,255), start=0.00, dur=0.75, ease=QEasingCurve.OutQuint)]),
        'close': Phase([         RectTween(P(0.10,0.50), P(0.10,0.50), px1=P(-8,-8), px2=P(8,0),                           fill_color=QColor(255,255,255,0),   start=0.00, dur=0.75, ease=QEasingCurve.OutQuint)])}),
]

SETTING_TEXT_DEFS = [
    TextDef(0.10,0.50,'CAMERA SETTINGS',14.0,QColor(255,255,255,0), {
        'open':  Phase([Reset(), TextTween(0.10,0.10,0.00,0.75,QEasingCurve.OutQuint,QColor(255,255,255,255),0.00,1.00,14.0,0,-5)]),
        'close': Phase([         TextTween(0.10,0.50,0.00,0.75,QEasingCurve.OutQuint,QColor(255,255,255,0),  0.00,1.00,14.0,0,-5)]),
    }, True, False, 'Oxanium SemiBold', 0.00, 1.00, False, 0, -5, None, True),
]

_TRACK_PHASES = {
    'open':     Phase([SliderTween(thickness_scale=1.0, length_scale=1.0, color_alpha=40, filled_color=QColor(255,255,255,255), start=0.20, dur=0.50, ease=QEasingCurve.OutQuint)]),
    'changed':  Phase([SliderTween(thickness_scale=1.0, length_scale=1.0, color_alpha=40, filled_color=QColor(255,255,255,127), start=0.00, dur=0.50, ease=QEasingCurve.OutQuint)]),
    'reverted': Phase([SliderTween(thickness_scale=1.0, length_scale=1.0, color_alpha=40, filled_color=QColor(255,255,255,255), start=0.00, dur=0.50, ease=QEasingCurve.OutQuint)]),
    'close':    Phase([SliderTween(thickness_scale=0.0, length_scale=0.0, color_alpha=40, filled_color=QColor(255,255,255,255), start=0.00, dur=0.50, ease=QEasingCurve.InQuint)]),
}
_KNOB_PHASES = {
    'open':      Phase([KnobTween(size_scale=1.0,  color=QColor(255,255,255),   start=0.20, dur=0.30, ease=QEasingCurve.OutBack)]),
    'hovered':   Phase([KnobTween(size_scale=1.35, color=QColor(255,255,255),   start=0.00, dur=0.15, ease=QEasingCurve.OutQuint)]),
    'unhovered': Phase([KnobTween(size_scale=1.0,  color=QColor(255,255,255),   start=0.00, dur=0.15, ease=QEasingCurve.OutQuint)]),
    'pressed':   Phase([KnobTween(size_scale=0.85, color=QColor(180,180,180),   start=0.00, dur=0.08, ease=QEasingCurve.OutQuint)]),
    'released':  Phase([KnobTween(size_scale=1.35, color=QColor(255,255,255),   start=0.00, dur=0.12, ease=QEasingCurve.OutBack)]),
    'close':     Phase([KnobTween(size_scale=0.0,  color=QColor(255,255,255,0), start=0.00, dur=0.20, ease=QEasingCurve.InQuint)]),
}
_MARK_PHASES = {
    'visible': Phase([MarkTween(height_scale=1.0, tick_color=QColor(255,255,255,127), fill_color=QColor(255,255,255), start=0.00, dur=0.50, ease=QEasingCurve.OutQuint)]),
    'hidden':  Phase([MarkTween(height_scale=0.0, tick_color=QColor(255,255,255,127), fill_color=QColor(255,255,255), start=0.00, dur=0.50, ease=QEasingCurve.OutQuint)]),
    'close':   Phase([MarkTween(height_scale=0.0, tick_color=QColor(255,255,255,127), fill_color=QColor(255,255,255), start=0.00, dur=0.50, ease=QEasingCurve.OutQuint)]),
}

SETTING_SLIDER_DEFS = [
    # SliderDef(x=0.25, y=0.30, length=0.50, min_val=5000,  max_val=60000, step=1000, value_fn=lambda ctx: ctx.exposure, set_fn=lambda ctx,v: setattr(ctx,'pending_exposure',int(v)), track=DEFAULT_TRACK, knob=DEFAULT_KNOB, mark=DEFAULT_MARK, track_phases=_TRACK_PHASES, knob_phases=_KNOB_PHASES, mark_phases=_MARK_PHASES, label='EXPOSURE', value_text_fn=lambda v,d: f"{int(v)} µs", delta_text_fn=lambda d: f"{int(d):+} µs" if d!=0 else '', vertical=False),
    # SliderDef(x=0.25, y=0.40, length=0.50, min_val=5000,  max_val=30000, step=1000, value_fn=lambda ctx: ctx.gain,     set_fn=lambda ctx,v: setattr(ctx,'pending_gain',    int(v)), track=DEFAULT_TRACK, knob=DEFAULT_KNOB, mark=DEFAULT_MARK, track_phases=_TRACK_PHASES, knob_phases=_KNOB_PHASES, mark_phases=_MARK_PHASES, label='GAIN',     value_text_fn=lambda v,d: f"{int(v)} µs", delta_text_fn=lambda d: f"{int(d):+} µs" if d!=0 else '', vertical=False),
    # SliderDef(x=0.25, y=0.50, length=0.50, min_val=2,     max_val=9,     step=1,    value_fn=lambda ctx: ctx.gamma,    set_fn=lambda ctx,v: setattr(ctx,'pending_gamma',   int(v)), track=DEFAULT_TRACK, knob=DEFAULT_KNOB, mark=DEFAULT_MARK, track_phases=_TRACK_PHASES, knob_phases=_KNOB_PHASES, mark_phases=_MARK_PHASES, label='GAMMA',    value_text_fn=lambda v,d: f"{int(v)} µs", delta_text_fn=lambda d: f"{int(d):+} µs" if d!=0 else '', vertical=False),
]

def _btn_phases(idle_col, hover_col, press_col, open_start=0.20, open_dur=0.30, close_dur=0.20):
    return {
        'open':      Phase([ButtonTween(fill_color=idle_col,  w_scale=1.0,  h_scale=1.0, start=open_start, dur=open_dur,  ease=QEasingCurve.OutQuint)]),
        'hovered':   Phase([ButtonTween(fill_color=hover_col, w_scale=1.0,  h_scale=1.0, start=0.00,       dur=0.12,      ease=QEasingCurve.OutQuint)]),
        'unhovered': Phase([ButtonTween(fill_color=idle_col,  w_scale=1.0,  h_scale=1.0, start=0.00,       dur=0.15,      ease=QEasingCurve.OutQuint)]),
        'pressed':   Phase([ButtonTween(fill_color=press_col, w_scale=0.95, h_scale=0.95,start=0.00,       dur=0.06,      ease=QEasingCurve.OutQuint)]),
        'released':  Phase([ButtonTween(fill_color=hover_col, w_scale=1.0,  h_scale=1.0, start=0.00,       dur=0.10,      ease=QEasingCurve.OutBack)]),
        'close':     Phase([ButtonTween(fill_color=idle_col,  w_scale=0.0,  h_scale=1.0, start=0.00,       dur=close_dur, ease=QEasingCurve.InQuint)]),
    }

_BTN_H = 40
_BTN_W = 200

SETTING_BUTTON_DEFS = [
    ButtonDef(p1=P(0.50,0.90), p2=P(0.50,0.90), px1=P(-200,-60), px2=P(0,40),   label='CANCEL', action='cancel',
              style=ButtonStyle(fill_color=QColor(10,10,10,0),   text_color=QColor(255,255,255)),
              phases=_btn_phases(QColor(10,10,10),  QColor(35,35,35),   QColor(95,95,95),  open_start=0.25, open_dur=1.50, close_dur=0.75)),
    ButtonDef(p1=P(0.50,0.90), p2=P(0.50,0.90), px1=P(0,-60),    px2=P(200,40), label='APPLY',  action='apply',
              style=ButtonStyle(fill_color=QColor(255,255,255,0), text_color=QColor(10,10,14)),
              phases=_btn_phases(QColor(255,255,255),QColor(220,220,220),QColor(160,160,160),open_start=0.25, open_dur=0.25, close_dur=0.20)),
]

# ──────────────────────── CAMERA SELECT OVERLAY ──────────────────

CS_DEFS = [
    Rect(P(0.00,0.00), P(1.00,1.00), fill_color=QColor(8,8,8,0), phases={
        'open':  Phase([RectTween(P(0.00,0.00), P(1.00,1.00), fill_color=QColor(8,8,8,120), start=0.00, dur=0.50, ease=QEasingCurve.OutQuint)]),
        'close': Phase([RectTween(P(0.00,0.00), P(1.00,1.00), fill_color=QColor(8,8,8,0),   start=0.00, dur=0.50, ease=QEasingCurve.OutQuint)])}),

    # Outer panel polygons unchanged — already in new format
    PolygonDef(
        points=[P(0.00,0.50), P(0.25,0.50), P(0.25,0.50), P(1.00,0.50), P(1.00,0.50), P(0.75,0.50), P(0.75,0.50), P(0.00,0.50)],
        px=    [P(0,0),       P(0,0),        P(0,0),        P(0,0),        P(0,0),        P(0,0),        P(0,0),        P(0,0)],
        fill_color=QColor(8,8,8,200), outline_color=QColor(255,255,255,0), closed=True, line_width=2.0, phases={
            'open':  Phase([Reset(),
                            PolygonTween(points=[P(0.00,0.10), P(0.25,0.10), P(0.25,0.10), P(1.00,0.10), P(1.00,0.90), P(0.75,0.90), P(0.75,0.90), P(0.00,0.90)],
                                         px=[P(0,30), P(0,30), P(30,0), P(0,0), P(0,-30), P(0,-30), P(-30,0), P(0,0)],
                                         fill_color=QColor(8,8,8,200), outline_color=QColor(255,255,255,255), start=0.00, dur=0.75, ease=QEasingCurve.OutQuint)]),
            'close': Phase([PolygonTween(points=[P(0.00,0.50), P(0.25,0.50), P(0.25,0.50), P(1.00,0.50), P(1.00,0.50), P(0.75,0.50), P(0.75,0.50), P(0.00,0.50)],
                                         px=[P(0,0), P(0,0), P(0,0), P(0,0), P(0,0), P(0,0), P(0,0), P(0,0)],
                                         fill_color=QColor(8,8,8,200), outline_color=QColor(255,255,255,0), start=0.00, dur=0.75, ease=QEasingCurve.OutQuint)]),
        }),
    PolygonDef(
        points=[P(0.25,0.50), P(0.25,0.50), P(0.25,0.50), P(0.25,0.50)],
        px=    [P(0,0),       P(0,0),        P(0,0),        P(0,0)],
        fill_color=QColor(255,255,255,0), outline_color=QColor(255,255,255,0), closed=True, line_width=2, phases={
            'open':  Phase([Reset(),
                            PolygonTween(points=[P(0.25,0.10), P(0.25,0.10), P(0.25,0.10), P(0.25,0.10)], px=[P(15,15), P(0,30), P(0,30), P(15,15)], fill_color=QColor(255,255,255,120), outline_color=QColor(255,255,255,255), start=0.00, dur=0.75, ease=QEasingCurve.OutQuint, blend=True),
                            PolygonTween(points=[P(0.00,0.00), P(0.00,0.00), P(-0.20,0.00), P(-0.20,0.00)], px=[P(0,0), P(0,0), P(0,0), P(0,0)],     fill_color=QColor(255,255,255,120), outline_color=QColor(255,255,255,255), start=0.00, dur=2.00, ease=QEasingCurve.OutQuint)]),
            'close': Phase([PolygonTween(points=[P(0.25,0.50), P(0.25,0.50), P(0.25,0.50), P(0.25,0.50)], px=[P(0,0), P(0,0), P(0,0), P(0,0)],       fill_color=QColor(255,255,255,0),   outline_color=QColor(255,255,255,0),   start=0.00, dur=0.75, ease=QEasingCurve.OutQuint)]),
        }),
    PolygonDef(
        points=[P(0.75,0.50), P(0.75,0.50), P(0.75,0.50), P(0.75,0.50)],
        px=    [P(0,0),       P(0,0),        P(0,0),        P(0,0)],
        fill_color=QColor(255,255,255,0), outline_color=QColor(255,255,255,0), closed=True, line_width=2, phases={
            'open':  Phase([Reset(),
                            PolygonTween(points=[P(0.75,0.90), P(0.75,0.90), P(0.75,0.90), P(0.75,0.90)], px=[P(-15,-15), P(0,-30), P(0,-30), P(-15,-15)], fill_color=QColor(255,255,255,120), outline_color=QColor(255,255,255,255), start=0.00, dur=0.75, ease=QEasingCurve.OutQuint, blend=True),
                            PolygonTween(points=[P(0.00,0.00), P(0.00,0.00), P(0.20,0.00), P(0.20,0.00)],  px=[P(0,0), P(0,0), P(0,0), P(0,0)],            fill_color=QColor(255,255,255,120), outline_color=QColor(255,255,255,255), start=0.00, dur=2.00, ease=QEasingCurve.OutQuint)]),
            'close': Phase([PolygonTween(points=[P(0.75,0.50), P(0.75,0.50), P(0.75,0.50), P(0.75,0.50)], px=[P(0,0), P(0,0), P(0,0), P(0,0)],             fill_color=QColor(255,255,255,0),   outline_color=QColor(255,255,255,0),   start=0.00, dur=0.75, ease=QEasingCurve.OutQuint)]),
        }),
]

CS_TEXT_DEFS = [
    TextDef(0.10, 0.00, 'DISPLAY MODE', 60.0, QColor(255,255,255,0), {
        'open':  Phase([Reset(), TextTween(0.00,0.00, 0.00,2.00, QEasingCurve.OutQuint, QColor(255,255,255,255), 0, 0, 60.0, 10, 0)]),
        'close': Phase([         TextTween(0.10,0.00, 0.00,0.50, QEasingCurve.OutQuint, QColor(255,255,255,0),   0, 0, 60.0, 10, 0)]),
    }, bold=True, italic=True, font_family='Oxanium SemiBold', h_align=0, v_align=0, uniform_scale=False, always_visible=True),
    TextDef(0.50, 0.90, '', 14.0, QColor(255,255,255,0), {
        'open':  Phase([Reset(), TextTween(0.50,0.90, 0.10,0.30, QEasingCurve.OutQuint, QColor(255,255,255,180), 0.5,1.0, 9.0, 0, -162)]),
        'close': Phase([         TextTween(0.50,0.90, 0.00,0.20, QEasingCurve.InQuint,  QColor(255,255,255,0),   0.5,1.0, 9.0, 0, -162)]),
    }, bold=False, italic=False, font_family='Oxanium SemiBold', h_align=0.5, v_align=1.0, uniform_scale=False, px=0, py=-162, always_visible=True,
       text_fn=lambda ctx: f"LAYOUT  {ctx['display_mode']+1} / {ctx['num_modes']}"),
    TextDef(0.50, 0.90, '', 14.0, QColor(255,255,255,0), {
        'open':  Phase([Reset(), TextTween(0.50,0.90, 0.10,0.30, QEasingCurve.OutQuint, QColor(255,255,255,200), 0.5,0.0, 9.0, 0, -78)]),
        'close': Phase([         TextTween(0.50,0.90, 0.00,0.20, QEasingCurve.InQuint,  QColor(255,255,255,0),   0.5,0.0, 9.0, 0, -78)]),
    }, bold=False, italic=False, font_family='Oxanium SemiBold', h_align=0.5, v_align=0.0, uniform_scale=False, px=0, py=-78, always_visible=True,
       text_fn=lambda ctx: f"CAM  {ctx['num_cams']} / {ctx['max_cams']}"),
]

CS_BUTTON_DEFS = [
    ButtonDef(p1=P(0.50,0.90), p2=P(0.50,0.90), px1=P(-200,-60), px2=P(0,40),    label='CANCEL',      action='cancel',
              style=ButtonStyle(fill_color=QColor(65,65,65,0),    text_color=QColor(255,255,255)),
              phases=_btn_phases(QColor(65,65,65),        QColor(100,100,100), QColor(160,160,160), open_start=0.25, open_dur=0.50, close_dur=0.35)),
    ButtonDef(p1=P(0.50,0.90), p2=P(0.50,0.90), px1=P(0,-60),    px2=P(200,40),  label='APPLY',       action='apply',
              style=ButtonStyle(fill_color=QColor(255,255,255,0), text_color=QColor(10,10,14)),
              phases=_btn_phases(QColor(255,255,255),     QColor(220,220,220), QColor(160,160,160), open_start=0.25, open_dur=0.25, close_dur=0.20)),
    ButtonDef(p1=P(0.50,0.90), p2=P(0.50,0.90), px1=P(-60,-162), px2=P(60,-122), label='+',           action='cam_up',
              style=ButtonStyle(fill_color=QColor(255,255,255,0), text_color=QColor(255,255,255)),
              phases=_btn_phases(QColor(255,255,255,30),  QColor(255,255,255,60),  QColor(255,255,255,100), open_start=0.15, open_dur=0.30, close_dur=0.20)),
    ButtonDef(p1=P(0.50,0.90), p2=P(0.50,0.90), px1=P(-60,-120), px2=P(60,-80),  label='−',           action='cam_down',
              style=ButtonStyle(fill_color=QColor(255,255,255,0), text_color=QColor(255,255,255)),
              phases=_btn_phases(QColor(255,255,255,30),  QColor(255,255,255,60),  QColor(255,255,255,100), open_start=0.15, open_dur=0.30, close_dur=0.20)),
    ButtonDef(p1=P(0.50,0.90), p2=P(0.50,0.90), px1=P(-182,-120),px2=P(-62,-80), label='◀',           action='scroll_left',
              style=ButtonStyle(fill_color=QColor(255,255,255,0), text_color=QColor(255,255,255)),
              phases=_btn_phases(QColor(255,255,255,30),  QColor(255,255,255,60),  QColor(255,255,255,100), open_start=0.10, open_dur=0.30, close_dur=0.20)),
    ButtonDef(p1=P(0.50,0.90), p2=P(0.50,0.90), px1=P(62,-120),  px2=P(182,-80), label='▶',           action='scroll_right',
              style=ButtonStyle(fill_color=QColor(255,255,255,0), text_color=QColor(255,255,255)),
              phases=_btn_phases(QColor(255,255,255,30),  QColor(255,255,255,60),  QColor(255,255,255,100), open_start=0.10, open_dur=0.30, close_dur=0.20)),
]