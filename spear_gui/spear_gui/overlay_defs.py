from __future__ import annotations
from typing import Callable, List
from PySide6.QtCore import QEasingCurve
from PySide6.QtGui  import QColor

from spear_gui.overlay_system import (
    Rect, Slant, SlantType, SlantCorner, SlantAngle, SlantPair,
    Phase, RectDef, TextDef, LineDef, LinePt, LineTween,
    Tween, TextTween, Reset,
    TrackStyle, KnobStyle, MarkStyle, ButtonStyle,
    SliderTween, KnobTween, MarkTween, ButtonTween,
    SliderDef, ButtonDef,
)

# ──────────────────────── LOADING OVERLAY ────────────────────────

LOADING_RECT_DEFS = [
    # Background T/B/L/R
    RectDef(Rect(0.00, 0.00, 1.00, 0.50), QColor(10, 10, 14), False, {
        'loaded': Phase([Tween(Rect(0.00, 0.00, 1.00, 0.00), 0.30, 1.00, QEasingCurve.OutQuint)])}),
    RectDef(Rect(0.00, 0.50, 1.00, 0.50), QColor(10, 10, 14), False, {
        'loaded': Phase([Tween(Rect(0.00, 1.00, 1.00, 0.00), 0.30, 1.00, QEasingCurve.OutQuint)])}),
    RectDef(Rect(0.00, 0.00, 0.50, 1.00), QColor(10, 10, 14), False, {
        'loaded': Phase([Tween(Rect(0.00, 0.00, 0.00, 1.00), 0.30, 1.00, QEasingCurve.OutQuint)])}),
    RectDef(Rect(0.50, 0.00, 0.50, 1.00), QColor(10, 10, 14), False, {
        'loaded': Phase([Tween(Rect(1.00, 0.00, 0.00, 1.00), 0.30, 1.00, QEasingCurve.OutQuint)])}),

    #Background Border T/B/L/R
    RectDef(Rect(0.50, 0.50), QColor(255, 255, 255), False, {
        'loaded': Phase([Tween(Rect(0.00, 0.00, 1.00), 0.30, 1.00, QEasingCurve.OutQuint, px=Rect(0, -1, 0, 1)),
                         Tween(Rect(0.00, 0.00, 1.00), 2.50, 1.00, QEasingCurve.InQuint,  QColor(255, 255, 255, 0), Rect(0, -1, 0, 1))])}, px=Rect(0, -1, 0, 1)),
    RectDef(Rect(0.50, 0.50), QColor(255, 255, 255), False, {
        'loaded': Phase([Tween(Rect(0.00, 1.00, 1.00), 0.30, 1.00, QEasingCurve.OutQuint, px=Rect(0, 0, 0, 1)),
                         Tween(Rect(0.00, 1.00, 1.00), 2.50, 1.00, QEasingCurve.InQuint,  QColor(255, 255, 255, 0), Rect(0, 0, 0, 1))])}, px=Rect(0, 0, 0, 1)),
    RectDef(Rect(0.50, 0.50), QColor(255, 255, 255), False, {
        'loaded': Phase([Tween(Rect(0.00, 0.00, 0.00, 1.00), 0.30, 1.00, QEasingCurve.OutQuint, px=Rect(-1, 0, 1)),
                         Tween(Rect(0.00, 0.00, 0.00, 1.00), 2.50, 1.00, QEasingCurve.InQuint,  QColor(255, 255, 255, 0), Rect(-1, 0, 1))])}, px=Rect(-1, 0, 1)),
    RectDef(Rect(0.50, 0.50), QColor(255, 255, 255), False, {
        'loaded': Phase([Tween(Rect(1.00, 0.00, 0.00, 1.00), 0.30, 1.00, QEasingCurve.OutQuint, px=Rect(0, 0, 1)),
                         Tween(Rect(1.00, 0.00, 0.00, 1.00), 2.50, 1.00, QEasingCurve.InQuint,  QColor(255, 255, 255, 0), Rect(0, 0, 1))])}, px=Rect(0, 0, 1)),

    # Horizontal Corner TL/TR/BL/BR
    RectDef(Rect(0.00, -0.01, 0.50), QColor(255, 255, 255), True, {
        'create': Phase([Tween(Rect(0.30, 0.47, 0.20, 0.01), 0.30, 0.25, QEasingCurve.OutCirc),
                         Tween(Rect(0.25, 0.45, 0.10, 0.01), 0.55, 0.50, QEasingCurve.InOutCirc, slant=Slant(SlantCorner.TOP_RIGHT))]),
        'loaded': Phase([Tween(Rect(0.25, 0.45, 0.00, 0.01), 0.30, 0.30, QEasingCurve.OutCirc)])}),
    RectDef(Rect(0.50, -0.01, 0.50), QColor(255, 255, 255), True, {
        'create': Phase([Tween(Rect(0.50, 0.47, 0.20, 0.01), 0.30, 0.25, QEasingCurve.OutCirc),
                         Tween(Rect(0.65, 0.45, 0.10, 0.01), 0.55, 0.50, QEasingCurve.InOutCirc, slant=Slant(SlantCorner.TOP_LEFT))]),
        'loaded': Phase([Tween(Rect(0.75, 0.45, 0.00, 0.01), 0.30, 0.30, QEasingCurve.OutCirc)])}),
    RectDef(Rect(0.00, 1.00, 0.50), QColor(255, 255, 255), True, {
        'create': Phase([Tween(Rect(0.30, 0.53 - 0.01, 0.20, 0.01), 0.30, 0.25, QEasingCurve.OutCirc),
                         Tween(Rect(0.25, 0.55 - 0.01, 0.10, 0.01), 0.55, 0.50, QEasingCurve.InOutCirc, slant=Slant(SlantCorner.BOTTOM_RIGHT))]),
        'loaded': Phase([Tween(Rect(0.25, 0.55 - 0.01, 0.00, 0.01), 0.30, 0.30, QEasingCurve.OutCirc)])}),
    RectDef(Rect(0.50, 1.00, 0.50), QColor(255, 255, 255), True, {
        'create': Phase([Tween(Rect(0.50, 0.53 - 0.01, 0.20, 0.01), 0.30, 0.25, QEasingCurve.OutCirc),
                         Tween(Rect(0.65, 0.55 - 0.01, 0.10, 0.01), 0.55, 0.50, QEasingCurve.InOutCirc, slant=Slant(SlantCorner.BOTTOM_LEFT))]),
        'loaded': Phase([Tween(Rect(0.75, 0.55 - 0.01, 0.00, 0.01), 0.30, 0.30, QEasingCurve.OutCirc)])}),

    # Horizontal Thin Corner TL/TR/BL/BR
    RectDef(Rect(0.30, 0.47 + 0.005, 0.20), QColor(255, 255, 255), True, {
        'create': Phase([Tween(Rect(0.30,  0.47 + 0.005, 0.20, 0.005), 0.55, 0.00, QEasingCurve.InOutCirc),
                         Tween(Rect(0.345, 0.45 + 0.005, 0.10, 0.005), 0.55, 0.50, QEasingCurve.InOutCirc, slant=Slant(SlantCorner.TOP_RIGHT)),
                         Tween(Rect(0.345, 0.45 + 0.005, 0.05, 0.005), 1.05, 1.75, QEasingCurve.InCirc,    slant=Slant(SlantCorner.TOP_RIGHT))]),
        'loaded': Phase([Tween(Rect(0.345, 0.45 + 0.005, 0.00, 0.005), 0.00, 0.30, QEasingCurve.OutCirc)])}),
    RectDef(Rect(0.50, 0.47 + 0.005, 0.20), QColor(255, 255, 255), True, {
        'create': Phase([Tween(Rect(0.50,  0.47 + 0.005, 0.20, 0.005), 0.55, 0.00, QEasingCurve.InOutCirc),
                         Tween(Rect(0.555, 0.45 + 0.005, 0.10, 0.005), 0.55, 0.50, QEasingCurve.InOutCirc, slant=Slant(SlantCorner.TOP_LEFT)),
                         Tween(Rect(0.605, 0.45 + 0.005, 0.05, 0.005), 1.05, 1.75, QEasingCurve.InCirc,    slant=Slant(SlantCorner.TOP_LEFT))]),
        'loaded': Phase([Tween(Rect(0.655, 0.45 + 0.005, 0.00, 0.005), 0.00, 0.30, QEasingCurve.OutCirc)])}),
    RectDef(Rect(0.30, 0.53 - 0.01, 0.20), QColor(255, 255, 255), True, {
        'create': Phase([Tween(Rect(0.30,  0.53 - 0.01, 0.20, 0.005), 0.55, 0.00, QEasingCurve.InOutCirc),
                         Tween(Rect(0.345, 0.55 - 0.01, 0.10, 0.005), 0.55, 0.50, QEasingCurve.InOutCirc, slant=Slant(SlantCorner.BOTTOM_RIGHT)),
                         Tween(Rect(0.345, 0.55 - 0.01, 0.05, 0.005), 1.05, 1.75, QEasingCurve.InCirc,    slant=Slant(SlantCorner.BOTTOM_RIGHT))]),
        'loaded': Phase([Tween(Rect(0.345, 0.55 - 0.01, 0.00, 0.005), 0.00, 0.30, QEasingCurve.OutCirc)])}),
    RectDef(Rect(0.50, 0.53 - 0.01, 0.20), QColor(255, 255, 255), True, {
        'create': Phase([Tween(Rect(0.50,  0.53 - 0.01, 0.20, 0.005), 0.55, 0.00, QEasingCurve.InOutCirc),
                         Tween(Rect(0.555, 0.55 - 0.01, 0.10, 0.005), 0.55, 0.50, QEasingCurve.InOutCirc, slant=Slant(SlantCorner.BOTTOM_LEFT)),
                         Tween(Rect(0.605, 0.55 - 0.01, 0.05, 0.005), 1.05, 1.75, QEasingCurve.InCirc,    slant=Slant(SlantCorner.BOTTOM_LEFT))]),
        'loaded': Phase([Tween(Rect(0.655, 0.55 - 0.01, 0.00, 0.005), 0.00, 0.30, QEasingCurve.OutCirc)])}),

    # Vertical Corner TL/BL/TR/BR
    RectDef(Rect(0.00, 0.00, 0.00, 0.50), QColor(255, 255, 255), True, {
        'create': Phase([Tween(Rect(0.30, 0.47, 0.005625, 0.03), 0.30, 0.25, QEasingCurve.OutCirc),
                         Tween(Rect(0.25, 0.45, 0.005625, 0.02), 0.55, 0.50, QEasingCurve.InOutCirc)]),
        'loaded': Phase([Tween(Rect(0.25, 0.47, 0.005625, 0.00), 0.60, 0.30, QEasingCurve.OutCirc)])}),
    RectDef(Rect(0.00, 0.50, 0.00, 0.50), QColor(255, 255, 255), True, {
        'create': Phase([Tween(Rect(0.30, 0.50, 0.005625, 0.03), 0.30, 0.25, QEasingCurve.OutCirc),
                         Tween(Rect(0.25, 0.53, 0.005625, 0.02), 0.55, 0.50, QEasingCurve.InOutCirc)]),
        'loaded': Phase([Tween(Rect(0.25, 0.53, 0.005625, 0.00), 0.60, 0.30, QEasingCurve.OutCirc)])}),
    RectDef(Rect(1.00, 0.00, 0.00, 0.50), QColor(255, 255, 255), True, {
        'create': Phase([Tween(Rect(0.70 - 0.005625, 0.47, 0.005625, 0.03), 0.30, 0.25, QEasingCurve.OutCirc),
                         Tween(Rect(0.75 - 0.005625, 0.45, 0.005625, 0.02), 0.55, 0.50, QEasingCurve.InOutCirc)]),
        'loaded': Phase([Tween(Rect(0.75 - 0.005625, 0.47, 0.005625, 0.00), 0.60, 0.30, QEasingCurve.OutCirc)])}),
    RectDef(Rect(1.00, 0.00, 0.00, 0.50), QColor(255, 255, 255), True, {
        'create': Phase([Tween(Rect(0.70 - 0.005625, 0.50, 0.005625, 0.03), 0.30, 0.25, QEasingCurve.OutCirc),
                         Tween(Rect(0.75 - 0.005625, 0.53, 0.005625, 0.02), 0.55, 0.50, QEasingCurve.InOutCirc)]),
        'loaded': Phase([Tween(Rect(0.75 - 0.005625, 0.53, 0.005625, 0.00), 0.60, 0.30, QEasingCurve.OutCirc)])}),

    # Large Square L/R
    RectDef(Rect(0.50, 0.50), QColor(180, 180, 180), True, {
        'create': Phase([Tween(Rect(0.50 - 10/1920, 0.50 - 10/1080, 20/1920, 20/1080), 0.00, 0.30, QEasingCurve.OutCirc),
                         Tween(Rect(0.23,           0.50 - 10/1080, 20/1920, 20/1080), 0.30, 1.00, QEasingCurve.OutBack)]),
        'loaded': Phase([Tween(Rect(0.25,           0.50 - 10/1080, 0.005625, 20/1080), 0.30, 0.30, QEasingCurve.OutCirc, QColor(255, 255, 255)),
                         Tween(Rect(0.25,           0.50,            0.005625, 0),       0.90, 0.30, QEasingCurve.OutCirc)])}),
    RectDef(Rect(0.50, 0.50), QColor(180, 180, 180), True, {
        'create': Phase([Tween(Rect(0.50 - 10/1920,      0.50 - 10/1080, 20/1920, 20/1080), 0.00, 0.30, QEasingCurve.OutCirc),
                         Tween(Rect(0.77 - 20/1920,      0.50 - 10/1080, 20/1920, 20/1080), 0.30, 1.00, QEasingCurve.OutBack)]),
        'loaded': Phase([Tween(Rect(0.75 - 0.005625,     0.50 - 10/1080, 0.005625, 20/1080), 0.30, 0.30, QEasingCurve.OutCirc, QColor(255, 255, 255)),
                         Tween(Rect(0.75 - 0.005625,     0.50,            0.005625, 0),       0.90, 0.30, QEasingCurve.OutCirc)])}),

    # Small Square TL/TR/BL/BR
    RectDef(Rect(0.50, 0.50), QColor(180, 180, 180), True, {
        'create': Phase([Tween(Rect(0.50 - 5/1920,  0.50 - 5/1080,  10/1920, 10/1080), 0.00, 0.30, QEasingCurve.OutCirc),
                         Tween(Rect(0.50 - 70/1920, 0.50 - 70/1080, 10/1920, 10/1080), 0.30, 1.00, QEasingCurve.OutBack)]),
        'loaded': Phase([Tween(Rect(0.50 - 5/1920,  0.50 - 70/1080, 10/1920, 10/1080), 0.30, 0.30, QEasingCurve.OutCirc, QColor(255, 255, 255)),
                         Tween(Rect(0.50,           0.50),                              0.60, 0.30, QEasingCurve.OutCirc)])}),
    RectDef(Rect(0.50, 0.50), QColor(180, 180, 180), True, {
        'create': Phase([Tween(Rect(0.50 - 5/1920,  0.50 - 5/1080,  10/1920, 10/1080), 0.00, 0.30, QEasingCurve.OutCirc),
                         Tween(Rect(0.50 + 70/1920, 0.50 - 70/1080, 10/1920, 10/1080), 0.30, 1.00, QEasingCurve.OutBack)]),
        'loaded': Phase([Tween(Rect(0.50 - 5/1920,  0.50 - 70/1080, 10/1920, 10/1080), 0.30, 0.30, QEasingCurve.OutCirc, QColor(255, 255, 255)),
                         Tween(Rect(0.50,           0.50),                              0.60, 0.30, QEasingCurve.OutCirc)])}),
    RectDef(Rect(0.50, 0.50), QColor(180, 180, 180), True, {
        'create': Phase([Tween(Rect(0.50 - 5/1920,  0.50 - 5/1080,  10/1920, 10/1080), 0.00, 0.30, QEasingCurve.OutCirc),
                         Tween(Rect(0.50 - 70/1920, 0.50 + 70/1080, 10/1920, 10/1080), 0.30, 1.00, QEasingCurve.OutBack)]),
        'loaded': Phase([Tween(Rect(0.50 - 5/1920,  0.50 + 70/1080, 10/1920, 10/1080), 0.30, 0.30, QEasingCurve.OutCirc, QColor(255, 255, 255)),
                         Tween(Rect(0.50,           0.50),                              0.60, 0.30, QEasingCurve.OutCirc)])}),
    RectDef(Rect(0.50, 0.50), QColor(180, 180, 180), True, {
        'create': Phase([Tween(Rect(0.50 - 5/1920,  0.50 - 5/1080,  10/1920, 10/1080), 0.00, 0.30, QEasingCurve.OutCirc),
                         Tween(Rect(0.50 + 70/1920, 0.50 + 70/1080, 10/1920, 10/1080), 0.30, 1.00, QEasingCurve.OutBack)]),
        'loaded': Phase([Tween(Rect(0.50 - 5/1920,  0.50 + 70/1080, 10/1920, 10/1080), 0.30, 0.30, QEasingCurve.OutCirc, QColor(255, 255, 255)),
                         Tween(Rect(0.50,           0.50),                              0.60, 0.30, QEasingCurve.OutCirc)])}),

    # Progress Bar Outline T/B/L/R
    RectDef(Rect(0.50, 0.50), QColor(120, 120, 120), True, {
        'create': Phase([Tween(Rect(0.25 + 0.005625*2, 0.45 + 0.01*2, 0.05625 - 0.005625*2*2, 0.0025), 0.30, 0.70, QEasingCurve.InOutQuad),
                         Tween(Rect(0.25 + 0.005625*2, 0.45 + 0.01*2, 0.50    - 0.005625*2*2, 0.0025), 1.00, 1.00, QEasingCurve.InOutQuad)]),
        'loaded': Phase([Tween(Rect(0.25 + 0.005625*2, 0.45 + 0.01*2, 0.50 - 0.005625*2*2, 0.0025),          0.30, 0.30, QEasingCurve.InOutQuad, QColor(255, 255, 255)),
                         Tween(Rect(-0.2 + 0.25 + 0.005625*2, 0.45 + 0.01*2, 0.00, 0.0025),                  0.60, 1.20, QEasingCurve.OutQuint)])}),
    RectDef(Rect(0.50, 0.50), QColor(120, 120, 120), True, {
        'create': Phase([Tween(Rect(0.25 + 0.005625*2, 0.55 - 0.01*2 - 0.0025, 0.05625 - 0.005625*2*2, 0.0025), 0.30, 0.70, QEasingCurve.InOutQuad),
                         Tween(Rect(0.25 + 0.005625*2, 0.55 - 0.01*2 - 0.0025, 0.50    - 0.005625*2*2, 0.0025), 1.00, 1.00, QEasingCurve.InOutQuad)]),
        'loaded': Phase([Tween(Rect(0.25 + 0.005625*2, 0.55 - 0.01*2 - 0.0025, 0.50 - 0.005625*2*2, 0.0025),                                0.30, 0.30, QEasingCurve.InOutQuad, QColor(255, 255, 255)),
                         Tween(Rect(0.2 + 0.25 + 0.005625*2 + 0.50 - 0.005625*2*2, 0.55 - 0.01*2 - 0.0025, 0, 0.0025), 0.60, 1.20, QEasingCurve.OutQuint)])}),
    RectDef(Rect(0.50, 0.50), QColor(120, 120, 120), True, {
        'create': Phase([Tween(Rect(0.25 + 0.005625*2, 0.45 + 0.01*2, 0.00140625, 0.10 - 0.01*2*2), 0.30, 0.70, QEasingCurve.InOutQuad)]),
        'loaded': Phase([Tween(Rect(0.25 + 0.005625*2, 0.45 + 0.01*2 + 0.10 - 0.01*2*2, 0.00140625, 0.00), 0.30, 0.30, QEasingCurve.OutCirc, QColor(255, 255, 255))])}),
    RectDef(Rect(0.50, 0.50), QColor(120, 120, 120), True, {
        'create': Phase([Tween(Rect(0.25 + 0.005625*2 + 0.05625 - 0.005625*2*2, 0.45 + 0.01*2, 0.00140625, 0.10 - 0.01*2*2),           0.30, 0.70, QEasingCurve.InOutQuad),
                         Tween(Rect(0.25 + 0.005625*2 + 0.50 - 0.005625*2*2 - 0.00140625, 0.45 + 0.01*2, 0.00140625, 0.10 - 0.01*2*2), 1.00, 1.00, QEasingCurve.InOutQuad)]),
        'loaded': Phase([Tween(Rect(0.25 + 0.005625*2 + 0.50 - 0.005625*2*2 - 0.00140625, 0.45 + 0.01*2, 0.00140625, 0.00), 0.30, 0.30, QEasingCurve.OutCirc, QColor(255, 255, 255))])}),

    # Progress Bar
    RectDef(Rect(0.50, 0.45 + 0.01*3, 0.00, 0.10 - 0.01*3*2), QColor(255, 255, 255), True, {
        'create': Phase([Tween(Rect(0.25 + 0.005625*3, 0.45 + 0.01*3, 0.05625 - 0.005625*3*2, 0.10 - 0.01*3*2), 0.30, 0.70, QEasingCurve.InOutQuad),
                         Tween(Rect(0.25 + 0.005625*3, 0.45 + 0.01*3, 0.50    - 0.005625*3*2, 0.10 - 0.01*3*2), 1.00, 1.80, QEasingCurve.InOutCirc)]),
        'loaded': Phase([Tween(Rect(0.25 + 0.005625*3, 0.45 + 0.01*3, 0.50 - 0.005625*3*2, 0.10 - 0.01*3*2), 0.00, 0.30, QEasingCurve.OutCirc),
                         Tween(Rect(0.50,              0.45 + 0.01*3, 0.00,                 0.10 - 0.01*3*2), 0.30, 0.25, QEasingCurve.OutCirc)])}),
]

LOADING_TEXT_DEFS = []
LOADING_LINE_DEFS = []

# ──────────────────────── SELECTION OVERLAY ────────────────────────

SELECTION_RECT_DEFS = [
    # Outline T/B/L/R
    RectDef(Rect(), QColor(255, 255, 255), False, {
        'selected':   Phase([Tween(Rect(0.00, 0.00, 1.00), 0.00, 1.00, QEasingCurve.OutQuint, QColor(255, 255, 255), Rect(0, 0, 0, 2))]),
        'unselected': Phase([Tween(Rect(0.00, 0.00, 1.00), 0.00, 1.00, QEasingCurve.OutQuint, QColor(127, 127, 127), Rect(0, 0, 0, 2))]),
        'unfocused':  Phase([Tween(Rect(),                 0.00, 1.00, QEasingCurve.OutQuint, QColor(127, 127, 127), Rect(0, 0, 0, 2))])}, px=Rect(0, 0, 0, 2)),
    RectDef(Rect(1.00, 1.00), QColor(255, 255, 255), False, {
        'selected':   Phase([Tween(Rect(0.00, 1.00, 1.00), 0.00, 1.00, QEasingCurve.OutQuint, QColor(255, 255, 255), Rect(0, -2, 0, 2))]),
        'unselected': Phase([Tween(Rect(0.00, 1.00, 1.00), 0.00, 1.00, QEasingCurve.OutQuint, QColor(127, 127, 127), Rect(0, -2, 0, 2))]),
        'unfocused':  Phase([Tween(Rect(0.00, 1.00),       0.00, 1.00, QEasingCurve.OutQuint, QColor(127, 127, 127), Rect(0, -2, 0, 2))])}, px=Rect(0, -2, 0, 2)),
    RectDef(Rect(), QColor(255, 255, 255), False, {
        'selected':   Phase([Tween(Rect(0.00, 0.00, 0.00, 1.00), 0.00, 1.00, QEasingCurve.OutQuint, QColor(255, 255, 255), Rect(0, 0, 2))]),
        'unselected': Phase([Tween(Rect(0.00, 0.00, 0.00, 1.00), 0.00, 1.00, QEasingCurve.OutQuint, QColor(127, 127, 127), Rect(0, 0, 2))]),
        'unfocused':  Phase([Tween(Rect(),                       0.00, 1.00, QEasingCurve.OutQuint, QColor(127, 127, 127), Rect(0, 0, 2))])}, px=Rect(0, 0, 2)),
    RectDef(Rect(1.00, 1.00), QColor(255, 255, 255), False, {
        'selected':   Phase([Tween(Rect(1.00, 0.00, 0.00, 1.00), 0.00, 1.00, QEasingCurve.OutQuint, QColor(255, 255, 255), Rect(-2, 0, 2))]),
        'unselected': Phase([Tween(Rect(1.00, 0.00, 0.00, 1.00), 0.00, 1.00, QEasingCurve.OutQuint, QColor(127, 127, 127), Rect(-2, 0, 2))]),
        'unfocused':  Phase([Tween(Rect(1.00, 1.00),             0.00, 1.00, QEasingCurve.OutQuint, QColor(127, 127, 127), Rect(-2, 0, 2))])}, px=Rect(-2, 0, 2)),

    # Corner HTR/VTR/HBL/VBL
    RectDef(Rect(-0.75, 0.00, 0.75), QColor(255, 255, 255), False, {
        'selected':   Phase([Reset(),
                             Tween(Rect(0.50, 0.00, 0.50), 0.00, 0.50, QEasingCurve.InQuint,  px=Rect(-10, 10, 0, 5)),
                             Tween(Rect(1.00, 0.00),       0.50, 1.00, QEasingCurve.OutQuint, px=Rect(-30, 10, 20, 5), slant=Slant(SlantCorner.BOTTOM_LEFT))]),
        'unselected': Phase([Tween(Rect(1.00, 0.00),       0.00, 0.50, QEasingCurve.InQuint,  px=Rect(-10, 10, 0, 5))])}, px=Rect(0, 10, 0, 5)),
    RectDef(Rect(1.00, 0.00), QColor(255, 255, 255), False, {
        'selected':   Phase([Reset(),
                             Tween(Rect(1.00, 0.00), 0.50, 0.50, QEasingCurve.OutQuint, px=Rect(-15, 10, 5, 70), slant=Slant(SlantCorner.BOTTOM_LEFT))]),
        'unselected': Phase([Tween(Rect(1.00, 0.00, 0.00, 1.00), 0.00, 0.50, QEasingCurve.InQuint,  px=Rect(-15, 10, 5)),
                             Tween(Rect(1.00, 1.00, 0.00, 1.00), 0.50, 0.50, QEasingCurve.OutQuint, px=Rect(-15, 0,  5))])}, px=Rect(-15, 10, 5)),
    RectDef(Rect(1.00, 1.00, 0.75), QColor(255, 255, 255), False, {
        'selected':   Phase([Reset(),
                             Tween(Rect(0.00, 1.00, 0.50), 0.00, 0.50, QEasingCurve.InQuint,  px=Rect(10, -15, 0, 5)),
                             Tween(Rect(0.00, 1.00),       0.50, 1.00, QEasingCurve.OutQuint, px=Rect(10, -15, 20, 5), slant=Slant(SlantCorner.TOP_RIGHT))]),
        'unselected': Phase([Tween(Rect(0.00, 1.00),       0.00, 0.50, QEasingCurve.InQuint,  px=Rect(10, -15, 0, 5))])}, px=Rect(0, -15, 0, 5)),
    RectDef(Rect(0.00, 1.00), QColor(255, 255, 255), False, {
        'selected':   Phase([Reset(),
                             Tween(Rect(0.00, 1.00), 0.50, 0.50, QEasingCurve.OutQuint, px=Rect(10, -80, 5, 70), slant=Slant(SlantCorner.TOP_RIGHT))]),
        'unselected': Phase([Tween(Rect(0.00, 0.00, 0.00, 1.00), 0.00, 0.50, QEasingCurve.InQuint,  px=Rect(10, -15, 5)),
                             Tween(Rect(0.00, 0.00),              0.50, 0.50, QEasingCurve.OutQuint, px=Rect(10, 0,   5))])}, px=Rect(10, -15, 5)),
]

SELECTION_TEXT_DEFS = [
    TextDef(1.00, 0.00, '', 14.0, QColor(255, 255, 255, 0), {
        'selected':   Phase([TextTween(1.00, 0.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255, 255, 255, 220), 1.00, 0.00, 14.0, -20, 15)]),
        'unselected': Phase([TextTween(1.00, 0.00, 0.00, 0.30, QEasingCurve.OutQuint, QColor(255, 255, 255, 80),  1.00, 0.00, 14.0, -20, 15)]),
        'unfocused':  Phase([TextTween(1.00, 0.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255, 255, 255, 0),   1.00, 0.00, 14.0, -20, 15)]),
    }, True, False, 'Oxanium SemiBold', 1.00, 0.00, False, 0, 15, lambda cam: cam.name, True),
    TextDef(1.00, 0.00, '', 14.0, QColor(255, 255, 255, 0), {
        'selected':   Phase([TextTween(1.00, 0.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255, 255, 255, 220), 1.00, 0.00, 14.0, -20, 35)]),
        'unselected': Phase([TextTween(1.00, 0.00, 0.00, 0.30, QEasingCurve.OutQuint, QColor(255, 255, 255, 80),  1.00, 0.00, 14.0, -20, 35)]),
        'unfocused':  Phase([TextTween(1.00, 0.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255, 255, 255, 0),   1.00, 0.00, 14.0, -20, 35)]),
    }, True, False, 'Oxanium SemiBold', 1.00, 0.00, False, 0, 15, lambda cam: cam.serial, True),
    TextDef(0.00, 0.00, 'CAMERA #<#>', 14.0, QColor(255, 255, 255, 0), {
        'selected':   Phase([TextTween(0.00, 0.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255, 255, 255, 220), 0.00, 0.00, 14.0, 20, 15)]),
        'unselected': Phase([TextTween(0.00, 0.00, 0.00, 0.30, QEasingCurve.OutQuint, QColor(255, 255, 255, 80),  0.00, 0.00, 14.0, 20, 15)]),
        'unfocused':  Phase([TextTween(0.00, 0.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255, 255, 255, 0),   0.00, 0.00, 14.0, 20, 15)]),
    }, True, False, 'Oxanium SemiBold', 1.00, 0.00, False, 0, 15, lambda cam: cam.position, True),
    TextDef(0.00, 1.00, 'EXPOSURE: <#>', 9.0, QColor(255, 255, 255, 0), {
        'selected':   Phase([TextTween(0.00, 1.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255, 255, 255, 220), 0.00, 1.00, 9.0, 20, -15)]),
        'unselected': Phase([TextTween(0.00, 1.00, 0.00, 0.30, QEasingCurve.OutQuint, QColor(255, 255, 255, 80),  0.00, 1.00, 9.0, 20, -15)]),
        'unfocused':  Phase([TextTween(0.00, 1.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255, 255, 255, 0),   0.00, 1.00, 9.0, 20, -15)]),
    }, False, False, 'Oxanium SemiBold', 1.00, 1.00, False, 0, -15, lambda cam: cam.exposure, True),
    TextDef(0.00, 1.00, 'GAIN: <#>', 9.0, QColor(255, 255, 255, 0), {
        'selected':   Phase([TextTween(0.00, 1.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255, 255, 255, 220), 0.00, 1.00, 9.0, 20, -30)]),
        'unselected': Phase([TextTween(0.00, 1.00, 0.00, 0.30, QEasingCurve.OutQuint, QColor(255, 255, 255, 80),  0.00, 1.00, 9.0, 20, -30)]),
        'unfocused':  Phase([TextTween(0.00, 1.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255, 255, 255, 0),   0.00, 1.00, 9.0, 20, -30)]),
    }, False, False, 'Oxanium SemiBold', 1.00, 1.00, False, 0, -15, lambda cam: cam.gain, True),
    TextDef(0.00, 1.00, 'GAMMA: <#>', 9.0, QColor(255, 255, 255, 0), {
        'selected':   Phase([TextTween(0.00, 1.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255, 255, 255, 220), 0.00, 1.00, 9.0, 20, -45)]),
        'unselected': Phase([TextTween(0.00, 1.00, 0.00, 0.30, QEasingCurve.OutQuint, QColor(255, 255, 255, 80),  0.00, 1.00, 9.0, 20, -45)]),
        'unfocused':  Phase([TextTween(0.00, 1.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255, 255, 255, 0),   0.00, 1.00, 9.0, 20, -45)]),
    }, False, False, 'Oxanium SemiBold', 1.00, 1.00, False, 0, -15, lambda cam: cam.gamma, True),
]

SELECTION_LINE_DEFS = []

# ──────────────────────── SETTING OVERLAY ────────────────────────

DEFAULT_TRACK        = TrackStyle(color=QColor(255,255,255,40), filled_color=QColor(255,255,255,255), thickness=8.0)
DEFAULT_KNOB         = KnobStyle(color=QColor(255,255,255), size=8.0, shape='diamond')
DEFAULT_MARK         = MarkStyle(tick_color=QColor(255,255,255,255), fill_color=QColor(255,255,255,255), tick_width=4, tick_height=18.0, rect_height=8.0)
DEFAULT_APPLY_STYLE  = ButtonStyle(color=QColor(255,255,255),    text_color=QColor(10,10,14))
DEFAULT_CANCEL_STYLE = ButtonStyle(color=QColor(255,255,255,20), text_color=QColor(255,255,255,160))

def _val_text(unit: str) -> Callable[[float, float], str]:
    def fn(val: float, delta: float) -> str:
        s = f"{int(val)}{unit}"
        if delta != 0: s += f"  ({int(delta):+})"
        return s
    return fn

SETTING_RECT_DEFS = [
    RectDef(Rect(0.10,0.50,0.80,0.00), QColor(8,8,8,127), False, {
        'open':  Phase([Tween(Rect(0.10,0.10,0.80,0.80), 0.30,0.50, QEasingCurve.OutQuint, None)]),
        'close': Phase([Tween(Rect(0.10,0.50,0.80,0.00), 0.00,0.50, QEasingCurve.OutQuint, None)])}),
    RectDef(Rect(0.10,0.50,0.80,0.00), QColor(255,255,255,0), False, {
        'open':  Phase([Reset(), Tween(Rect(0.10,0.10,0.80,0.00), 0.00,0.75, QEasingCurve.OutQuint, QColor(255,255,255,255), px=Rect(0,-2,0,2))]),
        'close': Phase([Tween(Rect(0.10,0.50,0.80,0.00), 0.00,0.75, QEasingCurve.OutQuint, QColor(255,255,255,0), px=Rect(0,-1,0,2))]),
    }, px=Rect(0,-1,0,2)),
    RectDef(Rect(0.10,0.50,0.80,0.00), QColor(255,255,255,0), False, {
        'open':  Phase([Reset(), Tween(Rect(0.10,0.90,0.80,0.00), 0.00,0.75, QEasingCurve.OutQuint, QColor(255,255,255,255), px=Rect(0,0,0,2))]),
        'close': Phase([Tween(Rect(0.10,0.50,0.80,0.00), 0.00,0.75, QEasingCurve.OutQuint, QColor(255,255,255,0), px=Rect(0,-1,0,2))]),
    }, px=Rect(0,-1,0,2)),
    RectDef(Rect(0.10,0.50,0.00,0.00), QColor(255,255,255,0), False, {
        'open':  Phase([Reset(), Tween(Rect(0.10,0.10,0.00,0.00), 0.00,0.75, QEasingCurve.OutQuint, QColor(255,255,255,255), px=Rect(0,-8,100,8), slant=Slant(SlantCorner.TOP_RIGHT))]),
        'close': Phase([Tween(Rect(0.10,0.50,0.00,0.00), 0.00,0.75, QEasingCurve.OutQuint, QColor(255,255,255,0), px=Rect(0,-8,0,8))]),
    }, px=Rect(0,-8,0,8), slant=Slant(SlantCorner.TOP_RIGHT)),
    RectDef(Rect(0.90,0.50,0.00,0.00), QColor(255,255,255,0), False, {
        'open':  Phase([Reset(), Tween(Rect(0.90,0.90,0.00,0.00), 0.00,0.75, QEasingCurve.OutQuint, QColor(255,255,255,255), px=Rect(-100,0,100,8), slant=Slant(SlantCorner.BOTTOM_LEFT))]),
        'close': Phase([Tween(Rect(0.90,0.50,0.00,0.00), 0.00,0.75, QEasingCurve.OutQuint, QColor(255,255,255,0), px=Rect(0,0,0,8))]),
    }, px=Rect(0,0,0,8), slant=Slant(SlantCorner.BOTTOM_LEFT)),
    RectDef(Rect(0.10,0.50,0.00,0.00), QColor(255,255,255,0), False, {
        'open':  Phase([Reset(), Tween(Rect(0.10,0.10,0.00,0.00), 0.00,0.75, QEasingCurve.OutQuint, QColor(255,255,255,255), px=Rect(-8,-8,8,100), slant=Slant(SlantCorner.BOTTOM_LEFT))]),
        'close': Phase([Tween(Rect(0.10,0.50,0.00,0.00), 0.00,0.75, QEasingCurve.OutQuint, QColor(255,255,255,0), px=Rect(-8,-8,8,0))]),
    }, px=Rect(-8,-8,8,0), slant=Slant(SlantCorner.BOTTOM_LEFT)),
]

SETTING_TEXT_DEFS = [
    TextDef(0.10,0.50,'CAMERA SETTINGS',14.0,QColor(255,255,255,0), {
        'open':  Phase([Reset(), TextTween(0.10,0.10,0.00,0.75,QEasingCurve.OutQuint,QColor(255,255,255,255),0.00,1.00,14.0,0,-5)]),
        'close': Phase([TextTween(0.10,0.50,0.00,0.75,QEasingCurve.OutQuint,QColor(255,255,255,0),0.00,1.00,14.0,0,-5)]),
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
    SliderDef(
        x=0.25, y=0.30, length=0.50, min_val=5000, max_val=60000, step=1000,
        value_fn=lambda ctx: ctx.exposure,
        set_fn=lambda ctx, v: setattr(ctx, 'pending_exposure', int(v)),
        track=DEFAULT_TRACK, knob=DEFAULT_KNOB, mark=DEFAULT_MARK,
        track_phases=_TRACK_PHASES, knob_phases=_KNOB_PHASES, mark_phases=_MARK_PHASES,
        label='EXPOSURE',
        value_text_fn=lambda v, d: f"{int(v)} µs",
        delta_text_fn=lambda d: f"{int(d):+} µs" if d != 0 else '',
        vertical=False,
    ),
]

_PT_APPLY  = Slant(SlantCorner.BOTTOM_RIGHT, SlantAngle.DEG_45, SlantPair.PARALLELOGRAM, SlantType.POINT)
_PT_CANCEL = Slant(SlantCorner.TOP_LEFT,     SlantAngle.DEG_45, SlantPair.PARALLELOGRAM, SlantType.POINT)

_APPLY_PHASES = {
    'open':      Phase([ButtonTween(QColor(255,255,255), w_scale=1.0,  h_scale=1.0, start=0.25, dur=0.25, ease=QEasingCurve.OutQuint, slant=_PT_APPLY)]),
    'hovered':   Phase([ButtonTween(QColor(220,220,220), w_scale=1.0,  h_scale=1.0, start=0.00, dur=0.12, ease=QEasingCurve.OutQuint, slant=_PT_APPLY)]),
    'unhovered': Phase([ButtonTween(QColor(255,255,255), w_scale=1.0,  h_scale=1.0, start=0.00, dur=0.15, ease=QEasingCurve.OutQuint, slant=_PT_APPLY)]),
    'pressed':   Phase([ButtonTween(QColor(160,160,160), w_scale=1.0,  h_scale=1.0, start=0.00, dur=0.06, ease=QEasingCurve.OutQuint, slant=_PT_APPLY)]),
    'released':  Phase([ButtonTween(QColor(220,220,220), w_scale=1.0,  h_scale=1.0, start=0.00, dur=0.10, ease=QEasingCurve.OutBack,  slant=_PT_APPLY)]),
    'close':     Phase([ButtonTween(QColor(255,255,255), w_scale=0.0,  h_scale=1.0, start=0.00, dur=0.20, ease=QEasingCurve.InQuint,  slant=None)]),
}
_CANCEL_PHASES = {
    'open':      Phase([ButtonTween(QColor(10,10,10),  w_scale=1.0,  h_scale=1.0, start=0.25, dur=1.50, ease=QEasingCurve.OutQuint, slant=_PT_CANCEL)]),
    'hovered':   Phase([ButtonTween(QColor(35,35,35),  w_scale=1.0,  h_scale=1.0, start=0.00, dur=0.12, ease=QEasingCurve.OutQuint, slant=_PT_CANCEL)]),
    'unhovered': Phase([ButtonTween(QColor(10,10,10),  w_scale=1.0,  h_scale=1.0, start=0.00, dur=0.15, ease=QEasingCurve.OutQuint, slant=_PT_CANCEL)]),
    'pressed':   Phase([ButtonTween(QColor(95,95,95),  w_scale=1.0,  h_scale=1.0, start=0.00, dur=0.06, ease=QEasingCurve.OutQuint, slant=_PT_CANCEL)]),
    'released':  Phase([ButtonTween(QColor(35,35,35),  w_scale=1.0,  h_scale=1.0, start=0.00, dur=0.10, ease=QEasingCurve.OutBack,  slant=_PT_CANCEL)]),
    'close':     Phase([ButtonTween(QColor(10,10,10),  w_scale=0.0,  h_scale=1.0, start=0.00, dur=0.75, ease=QEasingCurve.OutQuint, slant=None)]),
}

SETTING_BUTTON_DEFS = [
    ButtonDef(
        rect=Rect(0.50,0.90,0.00,0.00), px=Rect(-200,-60,200,40),
        label='CANCEL', action='cancel',
        style=ButtonStyle(color=QColor(10,10,10,0), text_color=QColor(255,255,255)),
        phases=_CANCEL_PHASES,
    ),
    ButtonDef(
        rect=Rect(0.50,0.90,0.00,0.00), px=Rect(0,-60,200,40),
        label='APPLY', action='apply',
        style=ButtonStyle(color=QColor(255,255,255,0), text_color=QColor(10,10,14)),
        phases=_APPLY_PHASES,
    ),
]

_LINE_PHASES = {
    'open':  Phase([LineTween(target='create',   dur=1.10, ease=QEasingCurve.OutQuint)]),
    'close': Phase([LineTween(target='collapse', collapse_pts=[0,1,2,3,4],
                               collapse_to=0,    dur=1.10, ease=QEasingCurve.OutQuint)]),
}

SETTING_LINE_DEFS: List[LineDef] = [
    LineDef(
        color=QColor(255,255,255,255), closed=True, line_width=4,
        points=[LinePt(0.50,0.90,  0,-60), LinePt(0.50,0.90,-40,-20),
                LinePt(0.50,0.90,-180,-20), LinePt(0.50,0.90,-200,-40),
                LinePt(0.50,0.90,-180,-60)],
        phases=_LINE_PHASES,
    ),
    LineDef(
        color=QColor(127,127,127,255), closed=True, line_width=4,
        points=[LinePt(0.50,0.90,  0,-20), LinePt(0.50,0.90, 40,-60),
                LinePt(0.50,0.90,180,-60), LinePt(0.50,0.90,200,-40),
                LinePt(0.50,0.90,180,-20)],
        phases=_LINE_PHASES,
    ),
]


# ──────────────────────── CAMERA SELECT OVERLAY ──────────────────

_PT_APPLY  = Slant(SlantCorner.BOTTOM_RIGHT, SlantAngle.DEG_45, SlantPair.PARALLELOGRAM, SlantType.POINT)
_PT_CANCEL = Slant(SlantCorner.TOP_LEFT,     SlantAngle.DEG_45, SlantPair.PARALLELOGRAM, SlantType.POINT)
_PT_UP     = Slant(SlantCorner.TOP_RIGHT,    SlantAngle.DEG_22, SlantPair.TRAPEZOID,     SlantType.STANDARD)
_PT_DOWN   = Slant(SlantCorner.BOTTOM_RIGHT, SlantAngle.DEG_22, SlantPair.TRAPEZOID,     SlantType.STANDARD)
_PT_LEFT   = Slant(SlantCorner.TOP_LEFT,     SlantAngle.DEG_22, SlantPair.TRAPEZOID,     SlantType.STANDARD)
_PT_RIGHT  = Slant(SlantCorner.TOP_RIGHT,    SlantAngle.DEG_22, SlantPair.TRAPEZOID,     SlantType.STANDARD)


def _btn_phases(idle_col, hover_col, press_col, slant,
                open_start=0.20, open_dur=0.30, close_dur=0.20):
    return {
        'open':      Phase([ButtonTween(idle_col,  w_scale=1.0, h_scale=1.0, start=open_start, dur=open_dur,  ease=QEasingCurve.OutQuint, slant=slant)]),
        'hovered':   Phase([ButtonTween(hover_col, w_scale=1.0, h_scale=1.0, start=0.00, dur=0.12, ease=QEasingCurve.OutQuint, slant=slant)]),
        'unhovered': Phase([ButtonTween(idle_col,  w_scale=1.0, h_scale=1.0, start=0.00, dur=0.15, ease=QEasingCurve.OutQuint, slant=slant)]),
        'pressed':   Phase([ButtonTween(press_col, w_scale=0.95,h_scale=0.95,start=0.00, dur=0.06, ease=QEasingCurve.OutQuint, slant=slant)]),
        'released':  Phase([ButtonTween(hover_col, w_scale=1.0, h_scale=1.0, start=0.00, dur=0.10, ease=QEasingCurve.OutBack,  slant=slant)]),
        'close':     Phase([ButtonTween(idle_col,  w_scale=0.0, h_scale=1.0, start=0.00, dur=close_dur, ease=QEasingCurve.InQuint, slant=None)]),
    }


_BTN_H = 40
_BTN_W = 200

CS_RECT_DEFS = [
    RectDef(Rect(0.10,0.50,0.80,0.00), QColor(8,8,8,127), False, {
        'open':  Phase([Tween(Rect(0.10,0.10,0.80,0.80), 0.30,0.50, QEasingCurve.OutQuint, None)]),
        'close': Phase([Tween(Rect(0.10,0.50,0.80,0.00), 0.00,0.50, QEasingCurve.OutQuint, None)])}),
    RectDef(Rect(0.10,0.50,0.80,0.00), QColor(255,255,255,0), False, {
        'open':  Phase([Reset(), Tween(Rect(0.10,0.10,0.80,0.00), 0.00,0.75, QEasingCurve.OutQuint, QColor(255,255,255,255), px=Rect(0,-2,0,2))]),
        'close': Phase([Tween(Rect(0.10,0.50,0.80,0.00), 0.00,0.75, QEasingCurve.OutQuint, QColor(255,255,255,0), px=Rect(0,-1,0,2))]),
    }, px=Rect(0,-1,0,2)),
    RectDef(Rect(0.10,0.50,0.80,0.00), QColor(255,255,255,0), False, {
        'open':  Phase([Reset(), Tween(Rect(0.10,0.90,0.80,0.00), 0.00,0.75, QEasingCurve.OutQuint, QColor(255,255,255,255), px=Rect(0,0,0,2))]),
        'close': Phase([Tween(Rect(0.10,0.50,0.80,0.00), 0.00,0.75, QEasingCurve.OutQuint, QColor(255,255,255,0), px=Rect(0,-1,0,2))]),
    }, px=Rect(0,-1,0,2)),
    # RectDef(Rect(0.0, 0.0, 1.0, 1.0), QColor(0, 0, 0, 0), False, {
    #     'open':  Phase([Tween(Rect(0.0, 0.0, 1.0, 1.0), 0.00, 0.30, QEasingCurve.OutQuint, QColor(0,0,0,160))]),
    #     'close': Phase([Tween(Rect(0.0, 0.0, 1.0, 1.0), 0.00, 0.25, QEasingCurve.InQuint,  QColor(0,0,0,0))]),
    # }),
    # RectDef(Rect(0.10, 0.22, 0.80, 0.00), QColor(255,255,255,0), False, {
    #     'open':  Phase([Reset(), Tween(Rect(0.10,0.22,0.80,0.00), 0.10,0.40, QEasingCurve.OutQuint, QColor(255,255,255,255), px=Rect(0,0,0,1))]),
    #     'close': Phase([Tween(Rect(0.10,0.22,0.80,0.00), 0.00,0.25, QEasingCurve.InQuint, QColor(255,255,255,0), px=Rect(0,0,0,1))]),
    # }, px=Rect(0,0,0,1)),
    # RectDef(Rect(0.10, 0.72, 0.80, 0.00), QColor(255,255,255,0), False, {
    #     'open':  Phase([Reset(), Tween(Rect(0.10,0.72,0.80,0.00), 0.10,0.40, QEasingCurve.OutQuint, QColor(255,255,255,255), px=Rect(0,0,0,1))]),
    #     'close': Phase([Tween(Rect(0.10,0.72,0.80,0.00), 0.00,0.25, QEasingCurve.InQuint, QColor(255,255,255,0), px=Rect(0,0,0,1))]),
    # }, px=Rect(0,0,0,1)),
    # RectDef(Rect(0.82, 0.35, 0.00, 0.00), QColor(255,255,255,0), False, {
    #     'open':  Phase([Reset(), Tween(Rect(0.82,0.35,0.00,0.00), 0.15,0.35, QEasingCurve.OutQuint, QColor(255,255,255,20), px=Rect(0,0,60,140))]),
    #     'close': Phase([Tween(Rect(0.82,0.35,0.00,0.00), 0.00,0.20, QEasingCurve.InQuint, QColor(255,255,255,0), px=Rect(0,0,60,140))]),
    # }, px=Rect(0,0,0,0)),
    # RectDef(Rect(0.02, 0.35, 0.00, 0.00), QColor(255,255,255,0), False, {
    #     'open':  Phase([Reset(), Tween(Rect(0.02,0.35,0.00,0.00), 0.15,0.35, QEasingCurve.OutQuint, QColor(255,255,255,20), px=Rect(0,0,60,140))]),
    #     'close': Phase([Tween(Rect(0.02,0.35,0.00,0.00), 0.00,0.20, QEasingCurve.InQuint, QColor(255,255,255,0), px=Rect(0,0,60,140))]),
    # }, px=Rect(0,0,0,0)),
]

CS_TEXT_DEFS = [
    # Title
    TextDef(0.50, 0.18, 'DISPLAY MODE', 13.0, QColor(255,255,255,0), {
        'open':  Phase([Reset(), TextTween(0.50,0.18, 0.05,0.40, QEasingCurve.OutQuint, QColor(255,255,255,255), 0.5,1.0, 13.0)]),
        'close': Phase([TextTween(0.50,0.18, 0.00,0.25, QEasingCurve.InQuint, QColor(255,255,255,0), 0.5,1.0, 13.0)]),
    }, bold=False, italic=False, font_family='Oxanium SemiBold',
       h_align=0.5, v_align=1.0, uniform_scale=False, always_visible=True),

    # Layout index: uses display_mode from ctx  ← FIXED (was ctx['layout'])
    TextDef(0.50, 0.74, '', 14.0, QColor(255,255,255,0), {
        'open':  Phase([Reset(), TextTween(0.50,0.76, 0.10,0.30, QEasingCurve.OutQuint, QColor(255,255,255,180), 0.5,1.0, 9.0)]),
        'close': Phase([TextTween(0.50,0.76, 0.00,0.20, QEasingCurve.InQuint, QColor(255,255,255,0), 0.5,1.0, 9.0)]),
    }, bold=False, italic=False, font_family='Oxanium SemiBold',
       h_align=0.5, v_align=1.0, uniform_scale=False, always_visible=True,
       text_fn=lambda ctx: f"LAYOUT  {ctx['display_mode']+1} / {ctx['num_modes']}"),

    # Camera count
    TextDef(0.50, 0.84, '', 14.0, QColor(255,255,255,0), {
        'open':  Phase([Reset(), TextTween(0.50,0.84, 0.10,0.30, QEasingCurve.OutQuint, QColor(255,255,255,200), 0.5,0.0, 9.0)]),
        'close': Phase([TextTween(0.50,0.84, 0.00,0.20, QEasingCurve.InQuint, QColor(255,255,255,0), 0.5,0.0, 9.0)]),
    }, bold=False, italic=False, font_family='Oxanium SemiBold',
       h_align=0.5, v_align=0.0, uniform_scale=False, always_visible=True,
       text_fn=lambda ctx: f"CAM  {ctx['num_cams']} / {ctx['max_cams']}"),

    # Left arrow label
    # TextDef(0.50, 0.90, '◀', 14.0, QColor(255,255,255,0), {
    #     'open':  Phase([Reset(), TextTween(0.04,0.455, 0.10,0.30, QEasingCurve.OutQuint, QColor(255,255,255,200), 0.5,0.5, 14.0)]),
    #     'close': Phase([TextTween(0.04,0.455, 0.00,0.20, QEasingCurve.InQuint, QColor(255,255,255,0), 0.5,0.5, 14.0)]),
    # }, bold=False, italic=False, font_family='Oxanium SemiBold',
    #    h_align=0.5, v_align=0.5, uniform_scale=False, px=-62, py=10, always_visible=True),

    # # Right arrow label
    # TextDef(0.96, 0.455, '▶', 14.0, QColor(255,255,255,0), {
    #     'open':  Phase([Reset(), TextTween(0.96,0.455, 0.10,0.30, QEasingCurve.OutQuint, QColor(255,255,255,200), 0.5,0.5, 14.0)]),
    #     'close': Phase([TextTween(0.96,0.455, 0.00,0.20, QEasingCurve.InQuint, QColor(255,255,255,0), 0.5,0.5, 14.0)]),
    # }, bold=False, italic=False, font_family='Oxanium SemiBold',
    #    h_align=0.5, v_align=0.5, uniform_scale=False, px=47, py=10, always_visible=True),
]

CS_BUTTON_DEFS = [
    ButtonDef(
        rect=Rect(0.50,0.90,0.00,0.00), px=Rect(0,-_BTN_H,_BTN_W,_BTN_H),
        label='APPLY', action='apply',
        style=ButtonStyle(color=QColor(255,255,255,0), text_color=QColor(10,10,14)),
        phases=_btn_phases(QColor(255,255,255), QColor(220,220,220), QColor(160,160,160),
                           _PT_APPLY, open_start=0.25, open_dur=0.25, close_dur=0.20),
    ),
    ButtonDef(
        rect=Rect(0.50,0.90,0.00,0.00), px=Rect(-_BTN_W,-_BTN_H,_BTN_W,_BTN_H),
        label='CANCEL', action='cancel',
        style=ButtonStyle(color=QColor(10,10,10,0), text_color=QColor(255,255,255)),
        phases=_btn_phases(QColor(10,10,10), QColor(35,35,35), QColor(80,80,80),
                           _PT_CANCEL, open_start=0.25, open_dur=0.50, close_dur=0.35),
    ),
    ButtonDef(
        rect=Rect(0.50,0.80,0.00,0.00), px=Rect(-60,-42,120,40),
        label='+', action='cam_up',
        style=ButtonStyle(color=QColor(255,255,255,0), text_color=QColor(255,255,255)),
        phases=_btn_phases(QColor(255,255,255,30), QColor(255,255,255,60), QColor(255,255,255,100),
                           _PT_UP, open_start=0.15, open_dur=0.30, close_dur=0.20),
    ),
    ButtonDef(
        rect=Rect(0.50,0.80,0.00,0.00), px=Rect(-60,0,120,40),
        label='−', action='cam_down',
        style=ButtonStyle(color=QColor(255,255,255,0), text_color=QColor(255,255,255)),
        phases=_btn_phases(QColor(255,255,255,30), QColor(255,255,255,60), QColor(255,255,255,100),
                           _PT_DOWN, open_start=0.15, open_dur=0.30, close_dur=0.20),
    ),
    ButtonDef(
        rect=Rect(0.50,0.80,0.00,0.00), px=Rect(-182,0,120,40),
        label='◀', action='scroll_left',
        style=ButtonStyle(color=QColor(255,255,255,0), text_color=QColor(255,255,255,0)),
        phases=_btn_phases(QColor(255,255,255,30), QColor(255,255,255,60), QColor(255,255,255,100),
                           _PT_LEFT, open_start=0.10, open_dur=0.30, close_dur=0.20),
    ),
    ButtonDef(
        rect=Rect(0.50,0.80,0.00,0.00), px=Rect(62,0,120,40),
        label='▶', action='scroll_right',
        style=ButtonStyle(color=QColor(255,255,255,0), text_color=QColor(255,255,255,0)),
        phases=_btn_phases(QColor(255,255,255,30), QColor(255,255,255,60), QColor(255,255,255,100),
                           _PT_RIGHT, open_start=0.10, open_dur=0.30, close_dur=0.20),
    ),
]