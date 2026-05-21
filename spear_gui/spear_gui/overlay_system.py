from __future__ import annotations
from typing import Optional, Dict, List, Tuple, Callable, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore    import Qt, QTimer, QElapsedTimer, QEasingCurve, QPointF, QRectF, QEvent, QObject
from PySide6.QtGui     import QColor, QPainter, QFont, QFontMetrics, QPolygonF, QPen, QRegion, QPainterPath, QLinearGradient
import time
import collections
import statistics
import threading
import math as _math

@dataclass(frozen=True)
class P:
    x: float = 0.0
    y: float = 0.0

@dataclass
class GradientStop:
    position: float
    color:    QColor

def Rect(
    p1:            P                          = P(), 
    p2:            P                          = P(), 
    px1:           P                          = P(), 
    px2:           P                          = P(),
    tl:            Optional[Tuple[P, P]]      = None, 
    tr:            Optional[Tuple[P, P]]      = None,
    br:            Optional[Tuple[P, P]]      = None, 
    bl:            Optional[Tuple[P, P]]      = None,
    fill_color:    Optional[QColor]           = QColor(255, 255, 255, 255), 
    outline_color: Optional[QColor]           = None,
    line_width:    float                      = 0.0, 
    draw_progress: Optional[float]            = None,
    uniform_scale: bool                       = False,
    closed:        bool                       = True,
    h_flip:        bool                       = False, 
    v_flip:        bool                       = False, 
    d_flip:        bool                       = False,
    phases:        Optional[Dict[str, Phase]] = None,
    gradient:      Optional['GradientDef']    = None,
    gradient_p1:   P  = P(),
    gradient_px1:  P  = P(),
    gradient_p2:   P  = P(),
    gradient_px2:  P  = P(),
) -> 'PolygonDef':
    def _split(offset):
        if offset is None:
            return P(), P()
        return offset[0], offset[1]

    tl_r, tl_p = _split(tl)
    tr_r, tr_p = _split(tr)
    br_r, br_p = _split(br)
    bl_r, bl_p = _split(bl)

    points = [P(p1.x + tl_r.x, p1.y + tl_r.y), P(p2.x + tr_r.x, p1.y + tr_r.y), P(p2.x + br_r.x, p2.y + br_r.y), P(p1.x + bl_r.x, p2.y + bl_r.y)]
    px = [P(px1.x + tl_p.x, px1.y + tl_p.y), P(px2.x + tr_p.x, px1.y + tr_p.y), P(px2.x + br_p.x, px2.y + br_p.y), P(px1.x + bl_p.x, px2.y + bl_p.y)]

    return PolygonDef(
        points        = points,
        px            = px,
        fill_color    = fill_color    or QColor(0, 0, 0, 0),
        outline_color = outline_color or QColor(0, 0, 0, 0),
        line_width    = line_width,
        draw_progress = draw_progress,
        uniform_scale = uniform_scale,
        closed        = closed,
        phases        = phases or {},
        h_flip        = h_flip,
        v_flip        = v_flip,
        d_flip        = d_flip,
        gradient      = gradient,
        gradient_p1   = gradient_p1,
        gradient_px1  = gradient_px1,
        gradient_p2   = gradient_p2,
        gradient_px2  = gradient_px2
    )

def RectTween(
    p1:            P                     = P(), 
    p2:            P                     = P(), 
    px1:           P                     = P(), 
    px2:           P                     = P(),
    tl:            Optional[Tuple[P, P]] = None, 
    tr:            Optional[Tuple[P, P]] = None,
    br:            Optional[Tuple[P, P]] = None, 
    bl:            Optional[Tuple[P, P]] = None,
    fill_color:    Optional[QColor]      = None, 
    outline_color: Optional[QColor]      = None,
    line_width:    Optional[float]       = None, 
    draw_progress: Optional[float]       = None,
    span:          Tuple[float, float]   = (0, 1),
    start:         float                 = 0.0,             
    dur:           float                 = 0.5,
    ease:          QEasingCurve.Type     = QEasingCurve.OutQuint,
    blend:         bool                  = False,
    prev_phase:    Optional[str]         = None,
    gradient_p1:   Optional[P]           = None,
    gradient_px1:  Optional[P]           = None,
    gradient_p2:   Optional[P]           = None,
    gradient_px2:  Optional[P]           = None
) -> PolygonTween:
    def _split(offset):
        if offset is None:
            return P(), P()
        return offset[0], offset[1]

    tl_r, tl_p = _split(tl)
    tr_r, tr_p = _split(tr)
    br_r, br_p = _split(br)
    bl_r, bl_p = _split(bl)

    points = [P(p1.x + tl_r.x, p1.y + tl_r.y), P(p2.x + tr_r.x, p1.y + tr_r.y), P(p2.x + br_r.x, p2.y + br_r.y), P(p1.x + bl_r.x, p2.y + bl_r.y)]
    px = [P(px1.x + tl_p.x, px1.y + tl_p.y), P(px2.x + tr_p.x, px1.y + tr_p.y), P(px2.x + br_p.x, px2.y + br_p.y), P(px1.x + bl_p.x, px2.y + bl_p.y)]

    return PolygonTween(
        points        = points,
        px            = px,
        fill_color    = fill_color,
        outline_color = outline_color,
        line_width    = line_width,
        draw_progress = draw_progress,
        start         = start,
        dur           = dur,
        span          = span,
        ease          = ease,
        blend         = blend,
        prev_phase    = prev_phase,
        gradient_p1   = gradient_p1,
        gradient_px1  = gradient_px1,
        gradient_p2   = gradient_p2,
        gradient_px2  = gradient_px2
    )

        
# ──────────────────────── Polygon ────────────────────────────────

@dataclass
class PolygonDef:
    points:        List[P]                    = field(default_factory=lambda: [P(0, 0), P(0, 0)])
    phases:        Optional[Dict[str, Phase]] = None
    closed:        bool                       = True
    line_width:    float                      = 0.0
    uniform_scale: bool                       = False
    px:            Optional[List[P]]          = None
    fill_color:    Optional[QColor]           = None
    outline_color: Optional[QColor]           = None
    draw_progress: float                      = 1.0
    h_flip:        bool                       = False
    v_flip:        bool                       = False
    d_flip:        bool                       = False
    gradient:      Optional['GradientDef']    = None
    gradient_p1:   P                          = P()
    gradient_px1:  P                          = P()
    gradient_p2:   P                          = P()
    gradient_px2:  P                          = P()

@dataclass
class PolygonTween:
    # Properties
    points:        Optional[List[P]]        = None
    px:            Optional[List[P]]        = None
    fill_color:    Optional[QColor]         = None
    outline_color: Optional[QColor]         = None
    line_width:    Optional[float]          = None
    draw_progress: Optional[float]          = None
    _blend_anchor: Optional[float]          = None
    gradient_p1:   Optional[P]              = None
    gradient_px1:  Optional[P]              = None
    gradient_p2:   Optional[P]              = None
    gradient_px2:  Optional[P]              = None
    # Tween Values
    span:          Tuple[float, float]      = (0, 1)
    start:         float                    = 0.0
    dur:           float                    = 0.5
    ease:          QEasingCurve.Type        = QEasingCurve.OutQuint
    prev_phase:    Optional[str]            = None
    blend:         bool                     = False

@dataclass
class GradientDef:
    stops:  List[GradientStop]
    phases: Dict[str, Phase] = field(default_factory=dict)

@dataclass
class GradientTween:
    stops:      Optional[List[GradientStop]] = None
    start:      float                        = 0.0
    dur:        float                        = 0.5
    ease:       QEasingCurve.Type            = QEasingCurve.OutQuint
    prev_phase: Optional[str]               = None
    span:       Tuple[float, float]          = (0, 1)
    blend:      bool                         = False

@dataclass
class TextDef:
    x:              float                          = 0.0
    y:              float                          = 0.0
    text:           str                            = 'Sample Text'
    font_size:      float                          = 10.0
    color:          QColor                         = QColor(255, 255, 255, 255)
    phases:         Optional[Dict[str, Phase]]     = None
    bold:           bool                           = False
    italic:         bool                           = False
    font_family:    str                            = 'Oxanium SemiBold'
    h_align:        float                          = 0.5
    v_align:        float                          = 0.5
    uniform_scale:  bool                           = False
    px:             float                          = 0.0
    py:             float                          = 0.0
    text_fn:        Optional[Callable[[Any], str]] = None
    always_visible: bool                           = True
    char_display:   float                          = 1.0
    sub_char_clip:  bool                           = False
    backward:       bool                           = False

# ──────────────────────── Tween dataclasses ──────────────────────

@dataclass
class Tween: # todo for later: Format this better 
    rect:       Rect; 
    start:      float             = 0.0; 
    dur:        float             = 0.5; 
    ease:       QEasingCurve.Type = QEasingCurve.OutQuint
    color:      Optional[QColor]  = None; 
    px:         Rect              = field(default_factory=Rect)
    prev_phase: Optional[str]     = None

@dataclass
class TextTween:
    # Properties
    x:            Optional[float]      = None
    y:            Optional[float]      = None
    px:           Optional[float]      = None
    py:           Optional[float]      = None
    color:        Optional[QColor]     = None
    h_align:      Optional[float]      = None
    v_align:      Optional[float]      = None
    font_size:    Optional[float]      = None
    char_display: Optional[float]      = None
    # Tween Values
    span:         Tuple[float, float]  = (0, 1)
    start:        float                = 0.0
    dur:          float                = 0.5
    ease:         QEasingCurve.Type    = QEasingCurve.OutQuint
    prev_phase:   Optional[str]        = None
    blend:        bool                 = False

@dataclass
class Reset:
    prev_phase: Optional[str] = None; start: float = 0

@dataclass
class Phase:
    tweens:      list
    line_delay:  float      = 0.0
    loop:        bool       = False
    stop_phases: List[str]  = field(default_factory=lambda: ['close'])

def TextBlock(
    x:           float                      = 0.0,
    y:           float                      = 0.0,
    text:        str                        = 'Sample Text',
    font_size:   float                      = 10.0,
    color:       QColor                     = QColor(255, 255, 255, 255),
    phases:      Optional[Dict[str, Phase]] = None,
    bold:        bool                       = False,
    italic:      bool                       = False,
    font_family: str                        = '',
    h_align:     float                      = 0.0,
    v_align:     float                      = 0.0,
    uniform_scale: bool                     = False,
    px:          float                      = 0.0,
    py:          float                      = 0.0,
    text_fn:     Optional[Callable]         = None,
    always_visible: bool                    = True,
    line_offset: Optional[float]            = None,
) -> List['TextDef']:

    lines = text.split('\n')
    n     = len(lines)

    effective_line_offset = font_size if line_offset is None else line_offset

    if n == 1:
        return [TextDef(
            x=x, y=y, text=text, font_size=font_size, color=color,
            phases=phases, bold=bold, italic=italic,
            font_family=font_family, h_align=h_align, v_align=v_align,
            uniform_scale=uniform_scale, px=px, py=py,
            text_fn=text_fn, always_visible=always_visible,
        )]

    result: List[TextDef] = []

    for i, line_text in enumerate(lines):
        line_py = py + effective_line_offset * i
        adjusted_phases: Optional[Dict[str, Phase]] = None
        if phases:
            adjusted_phases = {}
            for phase_name, phase in phases.items():
                new_tweens = []
                for tw in phase.tweens:
                    if isinstance(tw, TextTween):
                        new_tweens.append(TextTween(
                            x          = tw.x,
                            y          = tw.y,
                            start      = tw.start,
                            dur        = tw.dur,
                            ease       = tw.ease,
                            color      = tw.color,
                            h_align    = tw.h_align,
                            v_align    = tw.v_align,
                            font_size  = tw.font_size,
                            px         = tw.px,
                            py         = tw.py + effective_line_offset * i,
                            prev_phase = tw.prev_phase,
                            span       = tw.span,
                        ))
                    else:
                        new_tweens.append(tw)
                adjusted_phases[phase_name] = Phase(new_tweens)

        if text_fn is not None:
            def _make_line_fn(line_index: int, fallback: str):
                def _fn(ctx):
                    try:
                        full  = str(text_fn(ctx))
                        parts = full.split('\n')
                        return parts[line_index] if line_index < len(parts) else ''
                    except Exception:
                        return fallback
                return _fn
            resolved_text_fn = _make_line_fn(i, line_text)
            resolved_text    = ''
        else:
            resolved_text_fn = None
            resolved_text    = line_text

        result.append(TextDef(
            x             = x,
            y             = y,
            text          = resolved_text,
            font_size     = font_size,
            color         = color,
            phases        = adjusted_phases,
            bold          = bold,
            italic        = italic,
            font_family   = font_family,
            h_align       = h_align,
            v_align       = v_align,
            uniform_scale = uniform_scale,
            px            = px,
            py            = line_py,
            text_fn       = resolved_text_fn,
            always_visible= always_visible,
        ))

    return result

def DataTable(
    x:              float,
    y:              float,
    px:             float                                  = 0.0,
    py:             float                                  = 0.0,
    value_x:        float                                  = 0.5,
    value_px:       float                                  = 0.0,
    row_height:     float                                  = 18.0, # pixels
    value_names:    List[str]                              = None,
    values:         List[Union[str, Callable[[Any], Any]]] = None,
    value_units:    List[str]                              = None,
    fallbacks:      Optional[List[str]]                    = None,
    formats:        Optional[List[Optional[str]]]          = None,
    unit_gap:       float                                  = 4.0,  # pixels
    color:          QColor                                 = None,
    font_size:      float                                  = 10.0,
    font_family:    str                                    = 'Oxanium SemiBold',
    bold:           bool                                   = False,
    italic:         bool                                   = False,
    phases:         Dict[str, Phase]                       = None,
    char_display:   float                                  = 1.0,
    sub_char_clip:  bool                                   = False,
    backward:       bool                                   = False,
    always_visible: bool                                   = True,
) -> List[TextDef]:
    value_names = value_names or []
    values      = values      or []
    value_units = value_units or []
 
    n = len(value_names)
    assert len(values) == n and len(value_units) == n, ("DataTable: value_names, values, and value_units must have the same length")
    col = color or QColor(255, 255, 255, 200)
    ph  = phases or {}
    fallbacks = fallbacks if fallbacks is not None else ['-'] * n
    formats   = formats   if formats   is not None else [None] * n
    assert len(fallbacks) == n, "DataTable: fallbacks must have the same length as values"
    assert len(formats)   == n, "DataTable: formats must have the same length as values"
    result: List[TextDef] = []
 
    for i in range(n):
        row_py = py + row_height * i
        row_phases: Dict[str, Phase] = {}
        for phase_name, phase in ph.items():
            delay = phase.line_delay * i
            if delay == 0.0:
                row_phases[phase_name] = phase
            else:
                new_tweens = []
                for tw in phase.tweens:
                    if isinstance(tw, Reset):
                        new_tweens.append(tw)
                    elif isinstance(tw, TextTween):
                        new_tweens.append(TextTween(
                            start       = tw.start + delay,
                            dur         = tw.dur,
                            ease        = tw.ease,
                            color       = tw.color,
                            x           = tw.x,
                            y           = tw.y,
                            px          = tw.px,
                            py          = tw.py,
                            h_align     = tw.h_align,
                            v_align     = tw.v_align,
                            font_size   = tw.font_size,
                            char_display= tw.char_display,
                            prev_phase  = tw.prev_phase,
                            span        = tw.span,
                            blend       = tw.blend,
                        ))
                    else:
                        new_tweens.append(tw)
                row_phases[phase_name] = Phase(
                    new_tweens,
                    line_delay  = 0.0,
                    loop        = phase.loop,
                    stop_phases = phase.stop_phases,
                )
 
        # Common TextDef kwargs
        common = dict(
            font_size     = font_size,
            color         = QColor(col),
            phases        = row_phases,
            bold          = bold,
            italic        = italic,
            font_family   = font_family,
            uniform_scale = False,
            always_visible= always_visible,
            char_display  = char_display,
            sub_char_clip = sub_char_clip,
            backward      = backward,
        )
        # Name TextDef
        result.append(TextDef(
            x       = x,
            y       = y,
            px      = px,
            py      = row_py,
            text    = value_names[i],
            h_align = 0.0,
            v_align = 0.0,
            **common,
        ))
 
        # Value TextDef
        raw_value  = values[i]
        fmt_spec   = formats[i]
        fallback   = fallbacks[i]
 
        if callable(raw_value): # Dynamic string
            def _make_value_fn(fn, spec, fb):
                def _fn(ctx):
                    try:
                        v = fn(ctx)
                    except Exception:
                        v = None
                    if v is None:
                        return fb
                    try:
                        return format(v, spec) if spec else str(v)
                    except Exception:
                        return str(v)
                return _fn
            value_text_fn = _make_value_fn(raw_value, fmt_spec, fallback)
            value_text    = ''
        else: # Static string
            value_text_fn = None
            if fmt_spec:
                try:
                    value_text = format(raw_value, fmt_spec)
                except Exception:
                    value_text = str(raw_value)
            else:
                value_text = str(raw_value)
 
        result.append(TextDef(
            x       = value_x,
            y       = y,
            px      = value_px,
            py      = row_py,
            text    = value_text,
            text_fn = value_text_fn,
            h_align = 1.0,
            v_align = 0.0,
            **common,
        ))
 
        # Unit TextDef
        result.append(TextDef(
            x       = value_x,
            y       = y,
            px      = value_px + unit_gap,
            py      = row_py,
            text    = value_units[i],
            h_align = 0.0,
            v_align = 0.0,
            **common,
        ))
 
    return result


# ──────────────────────── _TweenDriver ───────────────────────────

class _TweenDriver:
    def __init__(self):
        self.hidden          = False
        self._phase: str     = ''
        self._prev:  str     = ''
        self._idx:   int     = 0
        self._tweens: list   = []
        self._timer          = QElapsedTimer()

    def _active_tweens(self, phase: str, prev: str, phases: dict) -> list:
        p = phases.get(phase)
        return [tw for tw in (p.tweens if p else [])
                if tw.prev_phase is None or tw.prev_phase == prev]

    @property
    def _cur(self): return self._tweens[self._idx] if self._idx < len(self._tweens) else None

    def set_phase(self, phase: str, phases: dict):
        if not phases:
            self.hidden = False
            return
        self._prev   = self._phase; self._phase = phase
        self._idx    = 0
        self._tweens = self._active_tweens(phase, self._prev, phases)
        if self._tweens or phase in phases:
            self.hidden = False
        while self._idx < len(self._tweens) and isinstance(self._tweens[self._idx], Reset):
            self._reset_to_def()
            self._idx += 1
        self._save_start(); self._timer.restart()

    def _is_done(self): return self._idx >= len(self._tweens)
    def phase_done(self): return self._is_done()

    def _drive(self, hide_when_done=False):
        if self.hidden:
            return

        elapsed = self._timer.elapsed() / 1000.0
        tweens = self._tweens
        n = len(tweens)

        def _ease_inverse(y: float, curve) -> float:
            if y <= 0.0: return 0.0
            if y >= 1.0: return 1.0
            if curve == QEasingCurve.Linear:    return y
            if curve == QEasingCurve.OutQuint:  return 1.0 - (1.0 - y) ** 0.2
            if curve == QEasingCurve.InQuint:   return y ** 0.2
            if curve == QEasingCurve.OutCubic:  return 1.0 - (1.0 - y) ** (1/3)
            if curve == QEasingCurve.InCubic:   return y ** (1/3)
            if curve == QEasingCurve.OutQuad:   return 1.0 - _math.sqrt(1.0 - y)
            if curve == QEasingCurve.InQuad:    return _math.sqrt(y)
            if curve == QEasingCurve.OutCirc:   return _math.sqrt(1.0 - (1.0 - y)**2)
            if curve == QEasingCurve.InCirc:    return _math.sqrt(1.0 - (1.0 - y*y))  # close approx
            lo, hi = 0.0, 1.0
            for _ in range(24):
                mid = (lo + hi) * 0.5
                if _ease(mid, curve) < y: lo = mid
                else: hi = mid
            return (lo + hi) * 0.5

        i = self._idx
        while i < n:
            tw = tweens[i]
            group = [tw]
            if len(group) == 1 and getattr(tw, 'span', (0,1)) == (0,1):
                if elapsed < tw.start:
                    return
                end = tw.start + tw.dur
                if elapsed <= end:
                    local = elapsed - tw.start
                    t = min(1.0, local / tw.dur) if tw.dur > 0 else 1.0
                    v = _ease(t, tw.ease)
                    self._apply(tw, v)
                    self._idx = i
                    return
                else:
                    self._snap_to(tw)
                    self._save_start()
                    self._idx = i + 1
                    i += 1
                    continue
            if isinstance(tw, Reset):
                self._reset_to_def()
                i += 1
                continue

            if getattr(tw, "blend", False):
                j = i + 1
                while j < n:
                    group.append(tweens[j])
                    if not getattr(tweens[j], "blend", False):
                        j += 1
                        break
                    j += 1
            else:
                j = i + 1

            group_start = min(t.start for t in group)
            def _eff_end(tw):
                span = getattr(tw, 'span')
                t1   = _ease_inverse(span[1], tw.ease)
                return tw.start + t1 * tw.dur
            group_end      = max(_eff_end(tw) for tw in group)
            base_eff_end   = _eff_end(group[0])

            # Case A: not started yet
            if elapsed < group_start:
                return

            # Case B: active
            if elapsed <= group_end:
                base      = group[0]
                span      = getattr(base, 'span')
                s0, s1    = span
                t0        = _ease_inverse(s0, base.ease)
                t1        = _ease_inverse(s1, base.ease)
                eff_start = base.start + t0 * base.dur
                eff_dur   = (t1 - t0) * base.dur
                local     = elapsed - eff_start
                t         = min(1.0, max(0.0, local / eff_dur)) if eff_dur > 0 else 1.0
                v         = (_ease(t0 + t * (t1 - t0), base.ease) - s0) / (s1 - s0) if s1 > s0 else 1.0
                # Only apply base if we're within its window
                if elapsed >= eff_start:
                    self._apply(base, v)
                for btw in group[1:]:
                    # Each blend tween uses its own independent timing
                    span_b      = getattr(btw, 'span')
                    s0b, s1b    = span_b
                    t0b         = _ease_inverse(s0b, btw.ease)
                    t1b         = _ease_inverse(s1b, btw.ease)
                    eff_start_b = btw.start + t0b * btw.dur
                    eff_dur_b   = (t1b - t0b) * btw.dur
                    local_b     = elapsed - eff_start_b
                    if local_b < 0: continue
                    tb  = min(1.0, max(0.0, local_b / eff_dur_b)) if eff_dur_b > 0 else 1.0
                    vb  = (_ease(t0b + tb * (t1b - t0b), btw.ease) - s0b) / (s1b - s0b) if s1b > s0b else 1.0
                    self._apply_blend(btw, vb)
                self._idx = i
                return

            # Case C: finished
            else:
                self._snap_to(group[0])
                for btw in group[1:]:
                    span_b      = getattr(btw, 'span')
                    s0b, s1b    = span_b
                    t0b         = _ease_inverse(s0b, btw.ease)
                    t1b         = _ease_inverse(s1b, btw.ease)
                    eff_start_b = btw.start + t0b * btw.dur
                    eff_dur_b   = (t1b - t0b) * btw.dur
                    local_b     = group_end - eff_start_b
                    if local_b <= 0: continue
                    tb  = min(1.0, max(0.0, local_b / eff_dur_b)) if eff_dur_b > 0 else 1.0
                    vb  = (_ease(t0b + tb * (t1b - t0b), btw.ease) - s0b) / (s1b - s0b) if s1b > s0b else 1.0
                    self._apply_blend(btw, vb)
                self._save_start()
                if j <= i: j = i + 1
                self._idx = j
                i = j
                continue

        self._idx = n
        if hide_when_done:
            self.hidden = True
    
    def _save_start(self): pass
    def _snap_to(self, tw): pass
    def _reset_to_def(self): pass
    def _apply(self, tw, v): pass

_ALWAYS_PHASE_ORIGINS: Dict[str, float] = {}

class _AlwaysDriver:
    def __init__(self, phase_name: str, phase: Phase, n_points: int) -> None:
        self._phase_name = phase_name
        self._phase      = phase
        self._n          = n_points
        self._stopped    = False
        self._started    = False
 
        self.offset_points:       List[P]           = [P(0.0, 0.0)] * n_points
        self.offset_px:           List[P]           = [P(0.0, 0.0)] * n_points
        self.offset_fill_color:   Optional[QColor]  = None
        self.offset_outline_color:Optional[QColor]  = None
 
        self._s_pts:    List[P]           = [P(0.0, 0.0)] * n_points
        self._s_px:     List[P]           = [P(0.0, 0.0)] * n_points
        self._s_fill:   Optional[QColor]  = None
        self._s_outline:Optional[QColor]  = None
 
        self._idx:      int   = 0
        self._loop_origin: float = 0.0

        self._stop_phases_set: set = set(self._phase.stop_phases)
 
    def _global_origin(self) -> float:
        if self._phase_name not in _ALWAYS_PHASE_ORIGINS:
            _ALWAYS_PHASE_ORIGINS[self._phase_name] = time.monotonic()
        return _ALWAYS_PHASE_ORIGINS[self._phase_name]
 
    def _elapsed(self) -> float:
        return time.monotonic() - self._loop_origin
 
    def _reset(self) -> None:
        self._stopped = False
        self._idx     = 0
        self.offset_points        = [P(0.0, 0.0)] * self._n
        self.offset_px            = [P(0.0, 0.0)] * self._n
        self.offset_fill_color    = None
        self.offset_outline_color = None
        self._s_pts     = [P(0.0, 0.0)] * self._n
        self._s_px      = [P(0.0, 0.0)] * self._n
        self._s_fill    = None
        self._s_outline = None
        origin  = self._global_origin()
        now     = time.monotonic()
        elapsed = now - origin
 
        if self._phase.loop:
            loop_dur = self._total_loop_dur()
            if loop_dur > 0.0:
                phase_in_loop = elapsed % loop_dur
                self._loop_origin = now - phase_in_loop
                self._fast_forward(phase_in_loop)
            else:
                self._loop_origin = now
        else:
            self._loop_origin = origin
        self._started = True
 
    def _total_loop_dur(self) -> float:
        total = 0.0
        for tw in self._phase.tweens:
            if isinstance(tw, (PolygonTween, TextTween)):
                total = max(total, tw.start + tw.dur)
        return total
 
    def _fast_forward(self, target_elapsed: float) -> None:
        tweens = self._phase.tweens
        n      = len(tweens)
        i      = 0
        while i < n:
            tw = tweens[i]
            if isinstance(tw, Reset):
                self._do_reset_offsets()
                i += 1
                continue
            if not isinstance(tw, (PolygonTween, TextTween)):
                i += 1
                continue
            end = tw.start + tw.dur
            if target_elapsed >= end:
                self._snap_tw(tw)
                self._save_start()
                i += 1
            else:
                self._idx = i
                return
        self._idx = n
 
    def _do_reset_offsets(self) -> None:
        self.offset_points        = [P(0.0, 0.0)] * self._n
        self.offset_px            = [P(0.0, 0.0)] * self._n
        self.offset_fill_color    = None
        self.offset_outline_color = None
        self._s_pts     = [P(0.0, 0.0)] * self._n
        self._s_px      = [P(0.0, 0.0)] * self._n
        self._s_fill    = None
        self._s_outline = None
 
    def _snap_tw(self, tw) -> None:
        if isinstance(tw, PolygonTween):
            if tw.points        is not None: self.offset_points = [P(p.x, p.y) for p in tw.points]
            if tw.px            is not None: self.offset_px = [P(p.x, p.y) for p in tw.px]
            if tw.fill_color    is not None: self.offset_fill_color    = QColor(tw.fill_color)
            if tw.outline_color is not None: self.offset_outline_color = QColor(tw.outline_color)
        elif isinstance(tw, TextTween):
            if tw.x     is not None: self.offset_points = [P(tw.x, self.offset_points[0].y)]
            if tw.y     is not None: self.offset_points = [P(self.offset_points[0].x, tw.y)]
            if tw.px    is not None: self.offset_px = [P(tw.px, self.offset_px[0].y)]
            if tw.py    is not None: self.offset_px = [P(self.offset_px[0].x, tw.py)]
            if tw.color is not None: self.offset_fill_color = QColor(tw.color)
 
    def _save_start(self) -> None:
        self._s_pts     = [P(p.x, p.y) for p in self.offset_points]
        self._s_px      = [P(p.x, p.y) for p in self.offset_px]
        self._s_fill    = QColor(self.offset_fill_color) if self.offset_fill_color    else None
        self._s_outline = QColor(self.offset_outline_color) if self.offset_outline_color else None
 
    def notify_phase(self, phase_name: str, base_phase_done: bool) -> None:
        in_stop = phase_name in self._phase.stop_phases
        if in_stop and base_phase_done:
            if not self._stopped:
                self._stopped = True
                self._do_reset_offsets()
        elif not in_stop:
            self._reset()
 
    def update(self, base_phase_name: str, base_phase_done: bool) -> None:
        if not self._started:
            self._reset()
 
        if base_phase_done and base_phase_name in self._phase.stop_phases:
            if not self._stopped:
                self._stopped = True
                self._do_reset_offsets()
            return
 
        if self._stopped:
            return
 
        elapsed = self._elapsed()
        tweens  = self._phase.tweens
        n       = len(tweens)
        i       = self._idx
 
        while i < n:
            tw = tweens[i]
 
            if isinstance(tw, Reset):
                self._do_reset_offsets()
                self._save_start()
                i += 1
                continue
 
            if not isinstance(tw, (PolygonTween, TextTween)):
                i += 1
                continue
 
            if elapsed < tw.start:
                self._idx = i
                return
 
            end = tw.start + tw.dur
            if elapsed <= end:
                local = elapsed - tw.start
                t = min(1.0, max(0.0, local / tw.dur)) if tw.dur > 0 else 1.0
                v = _ease(t, tw.ease)
                self._apply_tw(tw, v)
                self._idx = i
                return
            else:
                self._snap_tw(tw)
                self._save_start()
                i += 1
 
        self._idx = n
        if self._phase.loop:
            loop_dur = self._total_loop_dur()
            if loop_dur > 0.0:
                self._loop_origin += loop_dur
            self._idx = 0
            self._do_reset_offsets()
            self._s_pts     = [P(0.0, 0.0)] * self._n
            self._s_px      = [P(0.0, 0.0)] * self._n
            self._s_fill    = None
            self._s_outline = None
 
    def _apply_tw(self, tw, v: float) -> None:
        if isinstance(tw, PolygonTween):
            if tw.points is not None:
                for j, (sp, tp) in enumerate(zip(self._s_pts, tw.points)):
                    self.offset_points[j] = P(sp.x + (tp.x - sp.x) * v, sp.y + (tp.y - sp.y) * v)
            if tw.px is not None:
                for j, (sp, tp) in enumerate(zip(self._s_px, tw.px)):
                    self.offset_px[j] = P(sp.x + (tp.x - sp.x) * v, sp.y + (tp.y - sp.y) * v)
            if tw.fill_color is not None:
                src = self._s_fill or QColor(0, 0, 0, 0)
                self.offset_fill_color = lerp_color(src, tw.fill_color, v)
            if tw.outline_color is not None:
                src = self._s_outline or QColor(0, 0, 0, 0)
                self.offset_outline_color = lerp_color(src, tw.outline_color, v)
 
        elif isinstance(tw, TextTween):
            spx = self._s_px[0].x if self._s_px else 0.0
            spy = self._s_px[0].y if self._s_px else 0.0

            sp_x = self._s_pts[0].x if self._s_pts else 0.0
            sp_y = self._s_pts[0].y if self._s_pts else 0.0
            tp_x = tw.x if tw.x is not None else sp_x
            tp_y = tw.y if tw.y is not None else sp_y
            tpx  = tw.px if tw.px is not None else spx
            tpy  = tw.py if tw.py is not None else spy

            new_x  = sp_x + (tp_x - sp_x) * v
            new_y  = sp_y + (tp_y - sp_y) * v
            new_px = spx  + (tpx  - spx)  * v
            new_py = spy  + (tpy  - spy)   * v

            if tw.x  is not None: self.offset_points = [P(new_x,  self.offset_points[0].y)]
            if tw.y  is not None: self.offset_points = [P(self.offset_points[0].x, new_y)]
            if tw.px is not None: self.offset_px = [P(new_px, self.offset_px[0].y)]
            if tw.py is not None: self.offset_px = [P(self.offset_px[0].x, new_py)]

            if tw.color is not None:
                src = self._s_fill or QColor(0, 0, 0, 0)
                self.offset_fill_color = lerp_color(src, tw.color, v)

 

class _AnimatedGradient(_TweenDriver):
    def __init__(self, defn: GradientDef) -> None:
        super().__init__()
        self.defn      = defn
        self.cur_stops = [GradientStop(s.position, QColor(s.color)) for s in defn.stops]
        self._s_stops  = [GradientStop(s.position, QColor(s.color)) for s in defn.stops]
 
    def _save_start(self) -> None:
        self._s_stops = [GradientStop(s.position, QColor(s.color)) for s in self.cur_stops]
 
    def _reset_to_def(self) -> None:
        self.cur_stops = [GradientStop(s.position, QColor(s.color)) for s in self.defn.stops]
 
    def _snap_to(self, tw: GradientTween) -> None:
        if tw.stops is None or len(tw.stops) != len(self.cur_stops):
            return
        self.cur_stops = [GradientStop(s.position, QColor(s.color)) for s in tw.stops]
 
    def _apply(self, tw: GradientTween, v: float) -> None:
        if tw.stops is None or len(tw.stops) != len(self.cur_stops):
            return
        for i, (src, tgt) in enumerate(zip(self._s_stops, tw.stops)):
            new_pos   = src.position + (tgt.position - src.position) * v
            new_color = lerp_color(src.color, tgt.color, v)
            self.cur_stops[i] = GradientStop(new_pos, new_color)
 
    def _apply_blend(self, tw: GradientTween, v: float) -> None:
        if tw.stops is None or len(tw.stops) != len(self.cur_stops):
            return
        for i, tgt in enumerate(tw.stops):
            cur = self.cur_stops[i]
            new_pos   = cur.position + tgt.position * v
            new_color = lerp_color(cur.color, tgt.color, v)
            self.cur_stops[i] = GradientStop(new_pos, new_color)
 
    def set_phase(self, phase: str) -> None:
        super().set_phase(phase, self.defn.phases)
 
    def update(self) -> None:
        self._drive(hide_when_done=False)
 
    def build_gradient(self, x1: float, y1: float, x2: float, y2: float) -> QLinearGradient:
        g = QLinearGradient(x1, y1, x2, y2)
        g.setSpread(QLinearGradient.PadSpread)
        for stop in self.cur_stops:
            g.setColorAt(max(0.0, min(1.0, stop.position)), stop.color)
        return g

# ──────────────────────── AnimatedPolygon ────────────────────────
class AnimatedPolygon(_TweenDriver):
    def __init__(self, defn: PolygonDef):
        super().__init__()
        self.defn = defn
        n = len(defn.points)
        _zero_px = [P() for _ in range(n)]

        self._screen_offset = P(0.0, 0.0)
        self.cur_points       = [P(p.x, p.y) for p in defn.points]
        self.cur_px           = [P(p.x, p.y) for p in (defn.px or _zero_px)]
        self.cur_fill_color   = QColor(defn.fill_color)   if defn.fill_color   else QColor(0,0,0,0)
        self.cur_outline_color= QColor(defn.outline_color)if defn.outline_color else QColor(0,0,0,0)
        self.cur_line_width   = defn.line_width
        self.cur_draw_progress= defn.draw_progress
        self.cur_gradient_p1  = P(defn.gradient_p1.x,  defn.gradient_p1.y)
        self.cur_gradient_px1 = P(defn.gradient_px1.x, defn.gradient_px1.y)
        self.cur_gradient_p2  = P(defn.gradient_p2.x,  defn.gradient_p2.y)
        self.cur_gradient_px2 = P(defn.gradient_px2.x, defn.gradient_px2.y)

        self._sp  = [P(p.x, p.y) for p in self.cur_points]
        self._spx = [P(p.x, p.y) for p in self.cur_px]
        self._sf  = QColor(self.cur_fill_color)
        self._so  = QColor(self.cur_outline_color)
        self._slw = self.cur_line_width
        self._sdp = self.cur_draw_progress
        self._sgp1  = P(defn.gradient_p1.x,  defn.gradient_p1.y)
        self._sgpx1 = P(defn.gradient_px1.x, defn.gradient_px1.y)
        self._sgp2  = P(defn.gradient_p2.x,  defn.gradient_p2.y)
        self._sgpx2 = P(defn.gradient_px2.x, defn.gradient_px2.y)

        self._dirty      = True
        self._cached_poly= QPolygonF()
        self._cached_w   = 0
        self._cached_h   = 0
        self._always_drivers: Dict[str, _AlwaysDriver] = {
            name: _AlwaysDriver(name, phase, len(defn.points))
            for name, phase in (defn.phases or {}).items()
            if name.startswith('always')
        }
        self._always_offset_points: List[P] = [P(0.0, 0.0)] * len(defn.points)
        self._always_offset_px:     List[P] = [P(0.0, 0.0)] * len(defn.points)
        self._always_fill_color:    Optional[QColor] = None
        self._always_outline_color: Optional[QColor] = None

    # ── _TweenDriver hooks ───────────────────────────────────────

    def _save_start(self):
        self._sp  = [P(p.x, p.y) for p in self.cur_points]
        self._spx = [P(p.x, p.y) for p in self.cur_px]
        self._sf  = QColor(self.cur_fill_color)
        self._so  = QColor(self.cur_outline_color)
        self._slw = self.cur_line_width
        self._sdp = self.cur_draw_progress
        self._sgp1  = P(self.cur_gradient_p1.x,  self.cur_gradient_p1.y)
        self._sgpx1 = P(self.cur_gradient_px1.x, self.cur_gradient_px1.y)
        self._sgp2  = P(self.cur_gradient_p2.x,  self.cur_gradient_p2.y)
        self._sgpx2 = P(self.cur_gradient_px2.x, self.cur_gradient_px2.y)

    def _apply(self, tw: PolygonTween, v: float):
        if tw.points is not None:
            for i, (sp, tp) in enumerate(zip(self._sp, tw.points)):
                self.cur_points[i] = P(sp.x + (tp.x - sp.x) * v, sp.y + (tp.y - sp.y) * v)
        if tw.px is not None:
            for i, (spx, tpx) in enumerate(zip(self._spx, tw.px)):
                self.cur_px[i] = P(spx.x + (tpx.x - spx.x) * v, spx.y + (tpx.y - spx.y) * v)
        if tw.fill_color    is not None: self.cur_fill_color    = lerp_color(self._sf, tw.fill_color,    v)
        if tw.outline_color is not None: self.cur_outline_color = lerp_color(self._so, tw.outline_color, v)
        if tw.line_width    is not None: self.cur_line_width    = self._slw + (tw.line_width - self._slw) * v
        if tw.draw_progress is not None: self.cur_draw_progress = self._sdp + (tw.draw_progress - self._sdp) * v
        if tw.gradient_p1   is not None: self.cur_gradient_p1   = P(self._sgp1.x  + (tw.gradient_p1.x  - self._sgp1.x)  * v, self._sgp1.y  + (tw.gradient_p1.y  - self._sgp1.y)  * v)
        if tw.gradient_px1  is not None: self.cur_gradient_px1  = P(self._sgpx1.x + (tw.gradient_px1.x - self._sgpx1.x) * v, self._sgpx1.y + (tw.gradient_px1.y - self._sgpx1.y) * v)
        if tw.gradient_p2   is not None: self.cur_gradient_p2   = P(self._sgp2.x  + (tw.gradient_p2.x  - self._sgp2.x)  * v, self._sgp2.y  + (tw.gradient_p2.y  - self._sgp2.y)  * v)
        if tw.gradient_px2  is not None: self.cur_gradient_px2  = P(self._sgpx2.x + (tw.gradient_px2.x - self._sgpx2.x) * v, self._sgpx2.y + (tw.gradient_px2.y - self._sgpx2.y) * v)
        self._dirty = True

    def _apply_blend(self, tw: PolygonTween, v: float):
        if tw.points is not None:
            for i, tp in enumerate(tw.points):
                cp = self.cur_points[i]
                self.cur_points[i] = P(cp.x + tp.x * v, cp.y + tp.y * v)
        if tw.px is not None:
            for i, tpx in enumerate(tw.px):
                cpx = self.cur_px[i]
                self.cur_px[i] = P(cpx.x + tpx.x * v, cpx.y + tpx.y * v)
        if tw.fill_color    is not None: self.cur_fill_color    = lerp_color(self.cur_fill_color,    tw.fill_color,    v)
        if tw.outline_color is not None: self.cur_outline_color = lerp_color(self.cur_outline_color, tw.outline_color, v)
        if tw.line_width    is not None: self.cur_line_width    = self.cur_line_width + (tw.line_width - self.cur_line_width) * v
        if tw.draw_progress is not None: self.cur_draw_progress = self.cur_draw_progress + (tw.draw_progress - self.cur_draw_progress) * v
        self._dirty = True

    def _snap_to(self, tw: PolygonTween):
        if tw.points        is not None: self.cur_points        = [P(p.x, p.y) for p in tw.points]
        if tw.px            is not None: self.cur_px            = [P(p.x, p.y) for p in tw.px]
        if tw.fill_color    is not None: self.cur_fill_color    = QColor(tw.fill_color)
        if tw.outline_color is not None: self.cur_outline_color = QColor(tw.outline_color)
        if tw.line_width    is not None: self.cur_line_width    = tw.line_width
        if tw.draw_progress is not None: self.cur_draw_progress = tw.draw_progress
        if tw.gradient_p1   is not None: self.cur_gradient_p1   = tw.gradient_p1
        if tw.gradient_px1  is not None: self.cur_gradient_px1  = tw.gradient_px1
        if tw.gradient_p2   is not None: self.cur_gradient_p2   = tw.gradient_p2
        if tw.gradient_px2  is not None: self.cur_gradient_px2  = tw.gradient_px2
        self._dirty = True

    def _reset_to_def(self):
        d = self.defn
        n = len(d.points)
        self.cur_points        = [P(p.x, p.y) for p in d.points]
        self.cur_px            = [P(p.x, p.y) for p in (d.px or [P()]*n)]
        self.cur_fill_color    = QColor(d.fill_color)    if d.fill_color    else QColor(0,0,0,0)
        self.cur_outline_color = QColor(d.outline_color) if d.outline_color else QColor(0,0,0,0)
        self.cur_line_width    = d.line_width
        self.cur_draw_progress = d.draw_progress
        self.cur_gradient_p1  = P(d.gradient_p1.x,  d.gradient_p1.y)
        self.cur_gradient_px1 = P(d.gradient_px1.x, d.gradient_px1.y)
        self.cur_gradient_p2  = P(d.gradient_p2.x,  d.gradient_p2.y)
        self.cur_gradient_px2 = P(d.gradient_px2.x, d.gradient_px2.y)
        self._dirty = True

    def set_phase(self, phase: str):
        super().set_phase(phase, self.defn.phases)
        self._dirty = True
        for driver in self._always_drivers.values():
            driver.notify_phase(phase, False)

    def update(self) -> None:
        self._drive(hide_when_done=False)
 
        n = len(self.defn.points)
        sum_pts = [P(0.0, 0.0)] * n
        sum_px  = [P(0.0, 0.0)] * n
        fill_override    = None
        outline_override = None
 
        base_done = self.phase_done()
 
        for driver in self._always_drivers.values():
            driver.update(self._phase, base_done)
 
            for j in range(n):
                op = driver.offset_points[j]
                ox = driver.offset_px[j]
                sum_pts[j] = P(sum_pts[j].x + op.x, sum_pts[j].y + op.y)
                sum_px[j]  = P(sum_px[j].x  + ox.x, sum_px[j].y  + ox.y)
 
            if driver.offset_fill_color is not None:
                fill_override = driver.offset_fill_color
            if driver.offset_outline_color is not None:
                outline_override = driver.offset_outline_color
 
        self._always_offset_points = sum_pts
        self._always_offset_px     = sum_px
        self._always_fill_color    = fill_override
        self._always_outline_color = outline_override
 
        if any(p.x != 0 or p.y != 0 for p in sum_pts + sum_px):
            self._dirty = True

    def phase_done(self) -> bool:
        return self._is_done()

    # ── Geometry ─────────────────────────────────────────────────

    def _to_screen_pts(self, w: int, h: int, cam_w=1920, cam_h=1080) -> List[QPointF]:
        pts = []
        for p, px in zip(self.cur_points, self.cur_px):
            if self.defn.uniform_scale:
                s  = min(w / cam_w, h / cam_h)
                cx = s / (w / cam_w)
                cy = s / (h / cam_h)
                sx = (0.5 + (p.x - 0.5) * cx) * w + px.x
                sy = (0.5 + (p.y - 0.5) * cy) * h + px.y
            else:
                sx = p.x * w + px.x
                sy = p.y * h + px.y
            pts.append(QPointF(sx, sy))
        return pts

    def get_polygon(self, widget_w: int, widget_h: int, cam_w: int = 1920, cam_h: int = 1080) -> QPolygonF:
        if not self._dirty and self._cached_w == widget_w and self._cached_h == widget_h:
            has_always = any(p.x != 0 or p.y != 0 for p in self._always_offset_points + self._always_offset_px)
            if not has_always:
                return self._cached_poly
            pts = []
            ox, oy = self._screen_offset.x, self._screen_offset.y
            for j, qp in enumerate(self._cached_poly):
                ap  = self._always_offset_points[j]
                apx = self._always_offset_px[j]
                if self.defn.uniform_scale:
                    s  = min(widget_w / cam_w, widget_h / cam_h)
                    cx = s / (widget_w / cam_w)
                    cy = s / (widget_h / cam_h)
                    pts.append(QPointF(qp.x() + ap.x * cx * widget_w + apx.x, qp.y() + ap.y * cy * widget_h + apx.y))
                else:
                    pts.append(QPointF(qp.x() + ap.x * widget_w + apx.x, qp.y() + ap.y * widget_h + apx.y))
            return QPolygonF(pts)

        pts = []
        ox, oy = self._screen_offset.x, self._screen_offset.y
        base_pts = []
        for j, (p, px) in enumerate(zip(self.cur_points, self.cur_px)):
            ap  = self._always_offset_points[j]
            apx = self._always_offset_px[j]
            if self.defn.uniform_scale:
                s  = min(widget_w / cam_w, widget_h / cam_h)
                cx = s / (widget_w / cam_w)
                cy = s / (widget_h / cam_h)
                sx = (0.5 + (p.x - 0.5) * cx) * widget_w + px.x + ox
                sy = (0.5 + (p.y - 0.5) * cy) * widget_h + px.y + oy
                pts.append(QPointF(sx + ap.x * cx * widget_w + apx.x, sy + ap.y * cy * widget_h + apx.y))
                base_pts.append(QPointF(sx, sy))
            else:
                sx = p.x * widget_w + px.x + ox
                sy = p.y * widget_h + px.y + oy
                pts.append(QPointF(sx + ap.x * widget_w + apx.x, sy + ap.y * widget_h + apx.y))
                base_pts.append(QPointF(sx, sy))

        self._cached_poly = QPolygonF(base_pts)
        self._cached_w    = widget_w
        self._cached_h    = widget_h
        self._dirty       = False
        return QPolygonF(pts)

    # ── Draw ─────────────────────────────────────────────────────

    def draw(self, painter: QPainter, w: int, h: int, cam_w: int = 1920, cam_h: int = 1080):
        if self.hidden:
            return
        pts = list(self.get_polygon(w, h, cam_w, cam_h))
 
        effective_fill    = (self._always_fill_color if self._always_fill_color is not None else self.cur_fill_color)
        effective_outline = (self._always_outline_color if self._always_outline_color is not None else self.cur_outline_color)
        has_fill    = self.defn.closed and (effective_fill.alpha() > 0 or self.defn.gradient is not None)
        has_outline = self.cur_line_width > 0 and effective_outline.alpha()
        is_open     = not self.defn.closed
 
        if is_open:
            if not has_outline:
                return
            pen = QPen(self.cur_outline_color)
            pen.setWidthF(self.cur_line_width)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            _draw_partial_polyline(painter, pts, self.cur_draw_progress)
            painter.setPen(Qt.NoPen)
            return
 
        def _fill_brush():
            fill = (self._always_fill_color if self._always_fill_color is not None else self.cur_fill_color)
            gd = self.defn.gradient
            if gd is None:
                return fill
            x1 = self.cur_gradient_p1.x  * w + self.cur_gradient_px1.x
            y1 = self.cur_gradient_p1.y  * h + self.cur_gradient_px1.y
            x2 = self.cur_gradient_p2.x  * w + self.cur_gradient_px2.x
            y2 = self.cur_gradient_p2.y  * h + self.cur_gradient_px2.y
            return gd._animated.build_gradient(x1, y1, x2, y2)
 
        poly = QPolygonF(pts)
 
        if has_fill and not has_outline:
            painter.setPen(Qt.NoPen)
            painter.setBrush(_fill_brush())
            painter.drawPolygon(poly)
 
        elif has_outline and not has_fill:
            pen = QPen(self.cur_outline_color)
            pen.setWidthF(self.cur_line_width)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawPolygon(poly)
            painter.setPen(Qt.NoPen)
 
        elif has_fill and has_outline:
            pen = QPen(self.cur_outline_color)
            pen.setWidthF(self.cur_line_width)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(_fill_brush())
            painter.drawPolygon(poly)
            painter.setPen(Qt.NoPen)

class AnimatedText(_TweenDriver):
    def __init__(self, defn: TextDef):
        super().__init__()
        self.defn = defn
        d = defn
        self.cur_x          = d.x
        self.cur_y          = d.y
        self.cur_px         = d.px
        self.cur_py         = d.py
        self.cur_color      = QColor(d.color)
        self.cur_font_size  = d.font_size
        self.cur_h_align    = d.h_align
        self.cur_v_align    = d.v_align
        self.cur_char_display = d.char_display
 
        self._sx   = d.x
        self._sy   = d.y
        self._spx  = d.px
        self._spy  = d.py
        self._sc   = QColor(d.color)
        self._sfs  = d.font_size
        self._sha  = d.h_align
        self._sva  = d.v_align
        self._scd  = d.char_display
 
        self._dirty        = True
        self._cached_font  = None
        self._cached_dx    = 0
        self._cached_dy    = 0
        self._cached_label = ''
        self._cached_tw    = 0
        self._cached_th    = 0
        self._cached_fm: Optional[QFontMetrics] = None
 
        self._always_drivers_t: Dict[str, _AlwaysDriver] = {
            name: _AlwaysDriver(name, phase, 1)
            for name, phase in (defn.phases or {}).items()
            if name.startswith('always')
        }
        self._always_x_offset:  float = 0.0
        self._always_y_offset:  float = 0.0
        self._always_px_offset:  float           = 0.0
        self._always_py_offset:  float           = 0.0
        self._always_text_color: Optional[QColor] = None

    def _save_start(self):
        self._sx  = self.cur_x
        self._sy  = self.cur_y
        self._spx = self.cur_px
        self._spy = self.cur_py
        self._sc  = QColor(self.cur_color)
        self._sfs = self.cur_font_size
        self._sha = self.cur_h_align
        self._sva = self.cur_v_align
        self._scd = self.cur_char_display

    def _snap_to(self, tw: TextTween):
        self.cur_x            = self._sx
        self.cur_y            = self._sy
        self.cur_px           = self._spx
        self.cur_py           = self._spy
        self.cur_h_align      = self._sha
        self.cur_v_align      = self._sva
        self.cur_font_size    = self._sfs
        self.cur_char_display = self._scd
        self.cur_color        = QColor(self._sc)
        if tw.x            is not None: self.cur_x            = tw.x
        if tw.y            is not None: self.cur_y            = tw.y
        if tw.px           is not None: self.cur_px           = tw.px
        if tw.py           is not None: self.cur_py           = tw.py
        if tw.h_align      is not None: self.cur_h_align      = tw.h_align
        if tw.v_align      is not None: self.cur_v_align      = tw.v_align
        if tw.font_size    is not None: self.cur_font_size    = tw.font_size
        if tw.char_display is not None: self.cur_char_display = tw.char_display
        if tw.color        is not None: self.cur_color        = QColor(tw.color)
        self._dirty = True

    def _reset_to_def(self):
        d = self.defn
        self.cur_x            = d.x;   
        self.cur_y            = d.y
        self.cur_px           = d.px;  
        self.cur_py           = d.py
        self.cur_color        = QColor(d.color)
        self.cur_font_size    = d.font_size
        self.cur_h_align      = d.h_align
        self.cur_v_align      = d.v_align
        self.cur_char_display = d.char_display
        self._dirty = True

    def _apply(self, tw: TextTween, v: float):
        self.cur_x            = self._sx
        self.cur_y            = self._sy
        self.cur_px           = self._spx
        self.cur_py           = self._spy
        self.cur_h_align      = self._sha
        self.cur_v_align      = self._sva
        self.cur_font_size    = self._sfs
        self.cur_char_display = self._scd
        self.cur_color        = QColor(self._sc)
        if tw.x            is not None: self.cur_x            = self._sx  + (tw.x        - self._sx)  * v
        if tw.y            is not None: self.cur_y            = self._sy  + (tw.y        - self._sy)  * v
        if tw.px           is not None: self.cur_px           = self._spx + (tw.px       - self._spx) * v
        if tw.py           is not None: self.cur_py           = self._spy + (tw.py       - self._spy) * v
        if tw.h_align      is not None: self.cur_h_align      = self._sha + (tw.h_align  - self._sha) * v
        if tw.v_align      is not None: self.cur_v_align      = self._sva + (tw.v_align  - self._sva) * v
        if tw.font_size    is not None: self.cur_font_size    = self._sfs + (tw.font_size    - self._sfs) * v
        if tw.char_display is not None: self.cur_char_display = self._scd + (tw.char_display - self._scd) * v
        if tw.color        is not None: self.cur_color        = lerp_color(self._sc, tw.color, v)
        self._dirty = True
    
    def _apply_blend(self, tw: TextTween, v: float):
        if tw.x            is not None: self.cur_x            += tw.x        * v
        if tw.y            is not None: self.cur_y            += tw.y        * v
        if tw.px           is not None: self.cur_px           += tw.px       * v
        if tw.py           is not None: self.cur_py           += tw.py       * v
        if tw.h_align      is not None: self.cur_h_align      += tw.h_align  * v
        if tw.v_align      is not None: self.cur_v_align      += tw.v_align  * v
        if tw.font_size    is not None: self.cur_font_size    += tw.font_size    * v
        if tw.char_display is not None: self.cur_char_display += tw.char_display * v
        if tw.color        is not None: self.cur_color         = lerp_color(self.cur_color, tw.color, v)
        self._dirty = True

    def set_phase(self, phase):
        super().set_phase(phase, self.defn.phases)
        self._dirty = True
        for driver in self._always_drivers_t.values():
            driver.notify_phase(phase, False)
        

    def update(self) -> None:
        self._drive(hide_when_done=not self.defn.always_visible)
 
        sum_px         = 0.0
        sum_py         = 0.0
        sum_x          = 0.0
        sum_y          = 0.0
        color_override = None
        base_done      = self.phase_done()

        for driver in self._always_drivers_t.values():
            driver.update(self._phase, base_done)
            sum_x  += driver.offset_points[0].x
            sum_y  += driver.offset_points[0].y
            sum_px += driver.offset_px[0].x
            sum_py += driver.offset_px[0].y
            if driver.offset_fill_color is not None:
                color_override = driver.offset_fill_color

        self._always_x_offset   = sum_x
        self._always_y_offset   = sum_y
        self._always_px_offset  = sum_px
        self._always_py_offset  = sum_py
        self._always_text_color = color_override
        if sum_px != 0.0 or sum_py != 0.0 or sum_x != 0.0 or sum_y != 0.0:
            self._dirty = True


    def resolve_text(self, context):
        template = self.defn.text or ''
        if self.defn.text_fn is not None and context is not None:
            try:    value = str(self.defn.text_fn(context))
            except: value = ''
            return template.replace('<#>', value) if '<#>' in template else value
        return template

    def build_font(self):
        if (self._cached_font is None or self._dirty):
            f = QFont()
            if self.defn.font_family: f.setFamily(self.defn.font_family)
            f.setPointSizeF(max(0.5, self.cur_font_size))
            f.setBold(self.defn.bold); f.setItalic(self.defn.italic)
            self._cached_font = f
        return self._cached_font

    def resolve_pos(self, widget_w, widget_h, cam_w, cam_h, label, font):
        if (not self._dirty and self._cached_label == label and self._cached_tw == widget_w and self._cached_th == widget_h):
            return self._cached_dx, self._cached_dy
        if self._cached_fm is None or self._dirty:
            self._cached_fm = QFontMetrics(font)
        fm = self._cached_fm
        if self.defn.uniform_scale:
            s  = min(widget_w/cam_w, widget_h/cam_h)
            bx = (0.5+(self.cur_x-0.5)*s/(widget_w/cam_w))*widget_w
            by = (0.5+(self.cur_y-0.5)*s/(widget_h/cam_h))*widget_h
        else:
            bx = self.cur_x*widget_w; by = self.cur_y*widget_h
        bx += self.cur_px; by += self.cur_py
        dx = int(bx - self.cur_h_align * fm.horizontalAdvance(label) + self._always_px_offset)
        dy = int(by + fm.ascent() - self.cur_v_align * fm.height() + self._always_py_offset)
        self._cached_dx = dx; self._cached_dy = dy
        self._cached_label = label
        self._cached_tw = widget_w; self._cached_th = widget_h
        self._dirty = False
        
        return dx, dy
    
    def resolve_display_text(self, full_label: str) -> str:
        cd = self.cur_char_display
        if cd <= 0.0:
            return ''
        if cd >= 1.0:
            return full_label
        n = len(full_label)
        if n == 0:
            return ''
        count = round(cd * n)
        count = max(0, min(n, count))
        if count == 0:
            return ''
        if self.defn.backward:
            return full_label[n - count:]
        return full_label[:count]
    
    def draw_text(self, painter: QPainter, widget_w: int, widget_h: int, cam_w: int, cam_h: int, ctx: Any) -> None:
        if self.hidden:
            return
 
        full_label = self.resolve_text(ctx)
        if not full_label:
            return
 
        cd = self.cur_char_display
        if cd <= 0.0:
            return
 
        font = self.build_font()
        fm   = QFontMetrics(font)
 
        orig_x, orig_y = self.cur_x, self.cur_y
        self.cur_x += self._always_x_offset
        self.cur_y += self._always_y_offset
        dx, dy = self.resolve_pos(widget_w, widget_h, cam_w, cam_h, full_label, font)
        self.cur_x, self.cur_y = orig_x, orig_y
        dx += int(self._always_px_offset)
        dy += int(self._always_py_offset)
 
        color = (self._always_text_color if self._always_text_color is not None else self.cur_color)
 
        painter.setFont(font)
        painter.setPen(color)
 
        if cd >= 1.0:
            painter.drawText(int(dx), int(dy), full_label)
            painter.setPen(Qt.NoPen)
            return
 
        n = len(full_label)
 
        if self.defn.sub_char_clip:
            full_w  = fm.horizontalAdvance(full_label)
            clip_w  = full_w * cd
            ascent  = fm.ascent()
            descent = fm.descent()
            height  = ascent + descent
 
            if self.defn.backward:
                clip_x = dx + full_w - clip_w
                painter.save()
                painter.setClipRect(QRectF(clip_x, dy - ascent, clip_w, height))
                painter.drawText(int(dx), int(dy), full_label)
                painter.restore()
            else:
                painter.save()
                painter.setClipRect(QRectF(dx, dy - ascent, clip_w, height))
                painter.drawText(int(dx), int(dy), full_label)
                painter.restore()
 
        else:
            display_label = self.resolve_display_text(full_label)
            if not display_label:
                painter.setPen(Qt.NoPen)
                return
 
            if self.defn.backward:
                disp_w  = fm.horizontalAdvance(display_label)
                full_w  = fm.horizontalAdvance(full_label)
                dx_disp = dx + full_w - disp_w
                painter.drawText(int(dx_disp), int(dy), display_label)
            else:
                painter.drawText(int(dx), int(dy), display_label)
 
        painter.setPen(Qt.NoPen)




# ──────────────────────── SLIDER DEF ────────────────────────

@dataclass
class AttributeDef:
    value_fn: Callable[[Any], float]
    set_fn:   Callable[[Any, float], None]
    min_val:  float = 0.0
    max_val:  float = 0.0
    step:     float = 0.0
    label:    str = ''
    unit:     str = ''
    delay:    float = 0.0

def make_track_def(
    x: float, y: float, px: float, py: float,
    lx: float, lpx: float,
    h_px: float = 4.0,
    fill_color:    QColor = None,
    outline_color: QColor = None,
    phases: Dict[str, Phase] = None,
) -> PolygonDef:
    half = h_px / 2.0
    fc = fill_color    or QColor(255, 255, 255, 40)
    oc = outline_color or QColor(0, 0, 0, 0)
    return PolygonDef(
        points        = [P(x,      y), P(x + lx, y), P(x + lx, y), P(x,      y)],
        px            = [P(px, py - half), P(px + lpx, py - half),
                         P(px + lpx, py + half), P(px, py + half)],
        fill_color    = fc,
        outline_color = oc,
        closed        = True,
        phases        = phases or {},
    )


def make_knob_def(
    fill_color: QColor = None,
    phases: Dict[str, Phase] = None,
) -> PolygonDef:
    fc = fill_color or QColor(255, 255, 255)
    return PolygonDef(
        points        = [P(0, 0), P(0, 0), P(0, 0), P(0, 0)],
        px            = [P(0, 0), P(0, 0), P(0, 0), P(0, 0)],
        fill_color    = fc,
        outline_color = QColor(0, 0, 0, 0),
        closed        = True,
        phases        = phases or {},
    )


def make_mark_fill_def(
    x: float, y: float, px: float, py: float,
    h_px: float = 8.0,
    fill_color: QColor = None,
    phases: Dict[str, Phase] = None,
) -> PolygonDef:
    half = h_px / 2.0
    fc   = fill_color or QColor(255, 255, 255, 60)
    return PolygonDef(
        points        = [P(x, y), P(x, y), P(x, y), P(x, y)],
        px            = [P(px, py - half), P(px, py - half),
                         P(px, py + half), P(px, py + half)],
        fill_color    = fc,
        outline_color = QColor(0, 0, 0, 0),
        closed        = True,
        phases        = phases or {},
    )


def make_mark_tick_def(
    x: float, y: float, px: float, py: float,
    w_px: float = 3.0,
    h_px: float = 14.0,
    fill_color: QColor = None,
    phases: Dict[str, Phase] = None,
) -> PolygonDef:
    hw = w_px / 2.0
    hh = h_px / 2.0
    fc = fill_color or QColor(255, 255, 255, 200)
    return PolygonDef(
        points        = [P(x, y), P(x, y), P(x, y), P(x, y)],
        px            = [P(px - hw, py - hh), P(px + hw, py - hh),
                         P(px + hw, py + hh), P(px - hw, py + hh)],
        fill_color    = fc,
        outline_color = QColor(0, 0, 0, 0),
        closed        = True,
        phases        = phases or {},
    )


@dataclass
class SliderTextDefs:
    label:   Optional[TextDef] = None   # anchored near track P1, static
    min_val: Optional[TextDef] = None   # anchored at track P1
    max_val: Optional[TextDef] = None   # anchored at track P2
    current: Optional[TextDef] = None   # follows knob (px injected each frame)


@dataclass
class SliderGroupDef:
    x:         float                = 0.0
    y:         float                = 0.0
    px:        float                = 0.0
    py:        float                = 0.0
    lx:        float                = 0.0
    lpx:       float                = 0.0
    attr:      AttributeDef         = None
    track:     PolygonDef           = None
    knob:      PolygonDef           = None
    mark_fill: PolygonDef           = None
    mark_tick: PolygonDef           = None
    texts:     SliderTextDefs       = field(default_factory=SliderTextDefs)
    phases:    Dict[str, Phase]     = field(default_factory=dict)
    delay:     float                = 0.0
    event_out: Optional['EventDef'] = None
    knob_hit_px: float              = 10.0

class SliderDef(SliderGroupDef):
    def __new__(
        cls,
        x:   float = 0.0,
        y:   float = 0.0,
        lx:  float = 0.0,
        attr: AttributeDef = None,       # AttributeDef or EventDef
        event_out          = None,       # Optional EventDef
        px:  float = 0.0,
        py:  float = 0.0,
        lpx: float = 0.0,
        delay:       float = 0.0,
        font_family: str   = 'Oxanium SemiBold',
        track_h:   float = 4.0,
        knob_size: int   = 10,
        mark_h:    float = 6.0,
        tick_h:    float = 12.0,
        track_idle:    QColor = QColor(255, 255, 255,  40),
        track_press:   QColor = QColor(200, 220, 255,  80),
        fill_idle:     QColor = QColor(200, 220, 255,  60),
        fill_press:    QColor = QColor(200, 220, 255, 120),
        tick_idle:     QColor = QColor(255, 255, 255, 200),
        tick_press:    QColor = QColor(200, 220, 255, 255),
        knob_idle:     QColor = QColor(255, 255, 255, 220),
        knob_hover:    QColor = QColor(255, 255, 255, 255),
        knob_press:    QColor = QColor(180, 210, 255, 255),
        text_dim:      QColor = QColor(200, 220, 255, 160),
        text_bright:   QColor = QColor(200, 220, 255, 255),
        zero_white:    QColor = QColor(255, 255, 255,   0),
        zero_color:    QColor = QColor(200, 220, 255,   0),
        **kwargs,
    ):
        fam        = font_family
        label_text = attr.label if attr and attr.label else ''
        unit_text  = attr.unit  if attr and attr.unit  else ''

        def _track_phases():
            pts_full = [P(x, y), P(x+lx, y), P(x+lx, y), P(x, y)]
            pts_zero = [P(x, y), P(x,    y), P(x,    y), P(x, y)]
            return {
                'open':     Phase([PolygonTween(points=pts_zero, fill_color=zero_white, start=0.00, dur=0.00, ease=QEasingCurve.Linear),
                                   PolygonTween(points=pts_full, fill_color=track_idle, start=0.05, dur=0.40, ease=QEasingCurve.OutQuint)]),
                'close':    Phase([PolygonTween(points=pts_zero, fill_color=zero_white,  start=0.00, dur=0.25, ease=QEasingCurve.InQuint)]),
                'pressed':  Phase([PolygonTween(points=pts_full, fill_color=track_press, start=0.00, dur=0.10, ease=QEasingCurve.OutQuint)]),
                'released': Phase([PolygonTween(points=pts_full, fill_color=track_idle,  start=0.00, dur=0.20, ease=QEasingCurve.OutQuint)]),
            }

        def _knob_phases():
            s  = knob_size
            sh = int(knob_size * 1.3)
            sp = int(knob_size * 0.8)
            def _px(e): return [P(0, -e), P(e, 0), P(0, e), P(-e, 0)]
            pts = [P(0, 0)] * 4
            return {
                'open':      Phase([PolygonTween(points=pts, px=_px(0),  fill_color=zero_white, start=0.00, dur=0.00, ease=QEasingCurve.Linear),
                                    PolygonTween(points=pts, px=_px(s),  fill_color=knob_idle,  start=0.10, dur=0.40, ease=QEasingCurve.OutBack)]),
                'close':     Phase([PolygonTween(points=pts, px=_px(0),  fill_color=zero_white, start=0.00, dur=0.20, ease=QEasingCurve.InQuint)]),
                'hovered':   Phase([PolygonTween(points=pts, px=_px(sh), fill_color=knob_hover, start=0.00, dur=0.12, ease=QEasingCurve.OutQuint)]),
                'unhovered': Phase([PolygonTween(points=pts, px=_px(s),  fill_color=knob_idle,  start=0.00, dur=0.15, ease=QEasingCurve.OutQuint)]),
                'pressed':   Phase([PolygonTween(points=pts, px=_px(sp), fill_color=knob_press, start=0.00, dur=0.08, ease=QEasingCurve.OutQuint)]),
                'released':  Phase([PolygonTween(points=pts, px=_px(sh), fill_color=knob_hover, start=0.00, dur=0.12, ease=QEasingCurve.OutBack)]),
            }

        def _mark_phases(idle_col, press_col):
            pts = [P(0, 0)] * 4
            return {
                'open':     Phase([PolygonTween(points=pts, fill_color=zero_color, start=0.00, dur=0.00, ease=QEasingCurve.Linear),
                                   PolygonTween(points=pts, fill_color=idle_col,   start=0.10, dur=0.40, ease=QEasingCurve.OutQuint)]),
                'close':    Phase([PolygonTween(points=pts, fill_color=zero_color, start=0.00, dur=0.20, ease=QEasingCurve.InQuint)]),
                'pressed':  Phase([PolygonTween(points=pts, fill_color=press_col,  start=0.00, dur=0.10, ease=QEasingCurve.OutQuint)]),
                'released': Phase([PolygonTween(points=pts, fill_color=idle_col,   start=0.00, dur=0.20, ease=QEasingCurve.OutQuint)]),
            }

        def _text_phases(tx, ty, tpx=0.0, tpy=0.0, h_align=0.5, v_align=0.5):
            return {
                'open':     Phase([TextTween(x=tx, y=ty, start=0.05, dur=0.40, ease=QEasingCurve.OutQuint, color=text_dim,    h_align=h_align, v_align=v_align, px=tpx, py=tpy)]),
                'close':    Phase([TextTween(x=tx, y=ty, start=0.00, dur=0.20, ease=QEasingCurve.InQuint,  color=zero_color,  h_align=h_align, v_align=v_align, px=tpx, py=tpy)]),
                'pressed':  Phase([TextTween(x=tx, y=ty, start=0.00, dur=0.10, ease=QEasingCurve.OutQuint, color=text_bright, h_align=h_align, v_align=v_align, px=tpx, py=tpy)]),
                'released': Phase([TextTween(x=tx, y=ty, start=0.00, dur=0.20, ease=QEasingCurve.OutQuint, color=text_dim,    h_align=h_align, v_align=v_align, px=tpx, py=tpy)]),
            }

        def _group_phases():
            return {
                'open':  Phase([PolygonTween(points=[P(0, 0)], px=[P(0, 0)], start=0.00, dur=0.40, ease=QEasingCurve.OutQuint)]),
                'close': Phase([PolygonTween(points=[P(0, 0)], px=[P(0, 20)], start=0.00, dur=0.25, ease=QEasingCurve.InQuint)]),
            }

        instance = super().__new__(cls)
        SliderGroupDef.__init__(
            instance,
            x=x, y=y, px=px, py=py,
            lx=lx, lpx=lpx,
            attr=attr,
            event_out=event_out,
            delay=delay,
            knob_hit_px=knob_size,

            track=make_track_def(
                x=x, y=y, px=px, py=py,
                lx=lx, lpx=lpx,
                h_px=track_h,
                fill_color=zero_white,
                phases=_track_phases(),
            ),

            knob=make_knob_def(
                fill_color=zero_white,
                phases=_knob_phases(),
            ),

            mark_fill=make_mark_fill_def(
                x=x, y=y, px=px, py=py,
                h_px=mark_h,
                fill_color=zero_color,
                phases=_mark_phases(fill_idle, fill_press),
            ),

            mark_tick=make_mark_tick_def(
                x=x, y=y, px=px, py=py,
                w_px=2.0, h_px=tick_h,
                fill_color=zero_white,
                phases=_mark_phases(tick_idle, tick_press),
            ),

            texts=SliderTextDefs(
                label=TextDef(
                    x=x, y=y, px=px - 8, py=py,
                    text=label_text, font_size=11.0,
                    color=zero_color,
                    phases=_text_phases(x, y, tpx=px - 8, tpy=py, h_align=1.0, v_align=0.5),
                    bold=False, italic=False, font_family=fam,
                    h_align=1.0, v_align=0.5, uniform_scale=False,
                    always_visible=True,
                ) if label_text else None,

                min_val=TextDef(
                    x=0.0, y=0.0, px=0.0, py=14.0,
                    text='', font_size=9.0,
                    color=zero_color,
                    phases=_text_phases(0.0, 0.0, tpy=14.0, h_align=0.0, v_align=0.0),
                    bold=False, italic=False, font_family=fam,
                    h_align=0.0, v_align=0.0, uniform_scale=False,
                    always_visible=True,
                    text_fn=lambda ctx: (f"{int(ctx.defn.attr.min_val)}{unit_text}" if ctx else ''),
                ) if (attr and attr.min_val is not None) else None,

                max_val=TextDef(
                    x=0.0, y=0.0, px=0.0, py=14.0,
                    text='', font_size=9.0,
                    color=zero_color,
                    phases=_text_phases(0.0, 0.0, tpy=14.0, h_align=1.0, v_align=0.0),
                    bold=False, italic=False, font_family=fam,
                    h_align=1.0, v_align=0.0, uniform_scale=False,
                    always_visible=True,
                    text_fn=lambda ctx: (f"{int(ctx.defn.attr.max_val)}{unit_text}" if ctx else ''),
                ) if (attr and attr.max_val is not None) else None,

                current=TextDef(
                    x=0.0, y=0.0, px=0.0, py=-12.0,
                    text='', font_size=10.0,
                    color=zero_color,
                    phases=_text_phases(0.0, 0.0, tpy=-12.0, h_align=0.5, v_align=1.0),
                    bold=False, italic=False, font_family=fam,
                    h_align=0.5, v_align=1.0, uniform_scale=False,
                    always_visible=True,
                    text_fn=lambda ctx: (f"{int(ctx._cur_value)}{unit_text}" + (f"  ({int(ctx._cur_value - ctx._initial_value):+})" if ctx.has_change else '')) if ctx else '',
                ),
            ),

            phases=_group_phases(),
        )
        return instance

    def __init__(self, *args, **kwargs):
        pass

class SliderGroup:
    def __init__(self, defn: SliderGroupDef, cam_w: int = 1920, cam_h: int = 1080):
        self.defn  = defn
        self.cam_w = cam_w
        self.cam_h = cam_h

        self._cur_value:     float = 0.0
        self._initial_value: float = 0.0
        self._dragging:      bool  = False
        self._hovered:       bool  = False

        self._track      = AnimatedPolygon(defn.track)     if defn.track     else None
        self._knob       = AnimatedPolygon(defn.knob)      if defn.knob      else None
        self._mark_fill  = AnimatedPolygon(defn.mark_fill) if defn.mark_fill else None
        self._mark_tick  = AnimatedPolygon(defn.mark_tick) if defn.mark_tick else None

        self._text_label   = AnimatedText(defn.texts.label)   if defn.texts.label   else None
        self._text_min     = AnimatedText(defn.texts.min_val) if defn.texts.min_val else None
        self._text_max     = AnimatedText(defn.texts.max_val) if defn.texts.max_val else None
        self._text_current = AnimatedText(defn.texts.current) if defn.texts.current else None

        _group_def = PolygonDef(
            points=[P(0, 0)], px=[P(0, 30)],   # <-- start offset, tween brings it to (0,0)
            fill_color=QColor(0, 0, 0, 0),
            outline_color=QColor(0, 0, 0, 0),
            closed=True,
            phases=defn.phases,
        )
        self._group = AnimatedPolygon(_group_def)

        self._track_x1: float = 0.0
        self._track_y1: float = 0.0
        self._track_x2: float = 0.0
        self._track_y2: float = 0.0
        self._knob_sx:  float = 0.0
        self._knob_sy:  float = 0.0
        self._knob_base_px: Optional[List[P]] = None
        self._last_knob_sx: float = 0.0
        self._last_knob_sy: float = 0.0
        self._last_text_min_x:  float = 0.0
        self._last_text_min_y:  float = 0.0
        self._last_text_max_x:  float = 0.0
        self._last_text_max_y:  float = 0.0
        self._last_text_cur_x:  float = 0.0
        self._last_text_cur_y:  float = 0.0
        self._snap_knob_to_start: bool = False
        self._snap_knob_to_start: bool  = False
 
        self._tick_display_sx:    float = 0.0 
        self._tick_target_sx:     float = 0.0
        self._tick_ease_start_sx: float = 0.0
        self._tick_ease_t0:       float = 0.0
        self._tick_easing:        bool  = False
        self._tick_frozen:        bool  = False

    def init_value(self, ctx):
        attr = self.defn.attr
        if attr is None:
            return
        if isinstance(attr, EventDef):
            if attr._is_numeric:
                self._cur_value = self._initial_value = float(attr.value)
        else:
            self._cur_value = self._initial_value = attr.value_fn(ctx)
    
    def commit(self, ctx):
        if self.defn.attr:
            self.defn.attr.set_fn(ctx, self._cur_value)
            self._initial_value = self._cur_value
        if self.defn.event_out is not None:
            self.defn.event_out.value = self._cur_value
 
        self._tick_ease_start_sx = self._tick_display_sx
        self._tick_target_sx     = self._knob_sx   # knob is already at cur_value
        self._tick_ease_t0       = time.monotonic()
        self._tick_easing        = True
        self._tick_frozen        = False
 

    def revert(self):
        self._cur_value = self._initial_value

    @property
    def has_change(self) -> bool:
        return self._cur_value != self._initial_value

    def set_phase(self, phase: str):
        for comp in (self._track, self._knob, self._mark_fill,
                    self._mark_tick, self._group):
            if comp is not None:
                comp.set_phase(phase)
        for text in (self._text_label, self._text_min,
                    self._text_max, self._text_current):
            if text is not None:
                text.set_phase(phase)
        if phase == 'open':
            self._snap_knob_to_start = True
        if phase == 'open' and self.defn.delay != 0.0:
            delay = self.defn.delay
            for comp in (self._track, self._knob, self._mark_fill,
                        self._mark_tick, self._group):
                if comp is not None:
                    comp._tweens = [
                        type(tw)(**{**tw.__dict__, 'start': tw.start + delay})
                        if not isinstance(tw, Reset) else tw
                        for tw in comp._tweens
                    ]
            for text in (self._text_label, self._text_min,
                        self._text_max, self._text_current):
                if text is not None:
                    text._tweens = [
                        type(tw)(**{**tw.__dict__, 'start': tw.start + delay})
                        if not isinstance(tw, Reset) else tw
                        for tw in text._tweens
                    ]
        if phase == 'open' and self._knob is not None:
            self._knob_sx = self._track_x1
            self._last_knob_sx = self._track_x1
            self._last_knob_sy = self._track_y1
        if self._knob is not None:
            self._knob._spx = [
                P(p.x - self._last_knob_sx, p.y - self._last_knob_sy)
                for p in self._knob._spx
            ]
        if self._text_min is not None:
            self._text_min._spx -= self._last_text_min_x
            self._text_min._spy -= self._last_text_min_y
        if self._text_max is not None:
            self._text_max._spx -= self._last_text_max_x
            self._text_max._spy -= self._last_text_max_y
        if self._text_current is not None:
            self._text_current._spx -= self._last_text_cur_x
            self._text_current._spy -= self._last_text_cur_y

    def phase_done(self) -> bool:
        comps = [self._track, self._knob, self._mark_fill,
                 self._mark_tick, self._group,
                 self._text_label, self._text_min,
                 self._text_max,   self._text_current]
        return all(c.phase_done() for c in comps if c is not None)

    def hit_test_knob(self, mx: float, my: float, w: int, h: int) -> bool:
        return (abs(mx - self._knob_sx) <= self.defn.knob_hit_px and
                abs(my - self._knob_sy) <= self.defn.knob_hit_px)

    def drag_to(self, mx: float, my: float, w: int, h: int):
        span = self._track_x2 - self._track_x1
        if span == 0:
            return
        ratio = max(0.0, min(1.0, (mx - self._track_x1) / span))
        attr  = self.defn.attr
        if attr is None:
            return
        if isinstance(attr, EventDef):
            if not attr._is_numeric:
                return
            lo   = float(attr.min_val) if attr.min_val is not None else 0.0
            hi   = float(attr.max_val) if attr.max_val is not None else 1.0
            step = float(attr.step)    if attr.step    else 0.0
        else:
            lo, hi, step = attr.min_val, attr.max_val, attr.step
        raw = lo + ratio * (hi - lo)
        if step > 0:
            raw = round(raw / step) * step
        self._cur_value = max(lo, min(hi, raw))
    

    def update(self, widget_w: int, widget_h: int):
        if not self._tick_frozen and not self._tick_easing and self._tick_display_sx == 0.0:
            _attr = self.defn.attr
            if _attr and (_attr.max_val - _attr.min_val) != 0:
                init_ratio = (self._initial_value - _attr.min_val) / (_attr.max_val - _attr.min_val)
            else:
                init_ratio = 0.0
            init_ratio = max(0.0, min(1.0, init_ratio))
            
        # 1. Tick group
        self._group.update()
        gp  = self._group.cur_points[0]
        gpx = self._group.cur_px[0]
        g_dx = gp.x * widget_w + gpx.x
        g_dy = gp.y * widget_h + gpx.y

        # 2. Track End Points
        d = self.defn
        self._track_x1 = d.x * widget_w + d.px + g_dx
        self._track_y1 = d.y * widget_h + d.py + g_dy
        self._track_x2 = (d.x + d.lx) * widget_w + d.px + d.lpx + g_dx
        self._track_y2 = self._track_y1

        # 3. Track Screen Position
        if self._track is not None:
            self._track._screen_offset = P(g_dx, g_dy)
            self._track._dirty = True
            self._track.update()

        # 4. Knob Position
        attr = d.attr
        if attr and (attr.max_val - attr.min_val) != 0:
            ratio = (self._cur_value - attr.min_val) / (attr.max_val - attr.min_val)
        else:
            ratio = 0.0
        ratio = max(0.0, min(1.0, ratio))
        self._knob_sx = self._track_x1 + ratio * (self._track_x2 - self._track_x1)
        self._knob_sy = self._track_y1
        if self._snap_knob_to_start:
            print(f'{self._knob_sx} + {self._track_x1}')
            self._knob._spx = [
                P(self._track_x1 - self._knob_sx, self._track_y1 - self._knob_sy)
                for p in self._knob.cur_px
            ]
            self._last_knob_sx = self._track_x1
            self._last_knob_sy = self._track_y1
            self._snap_knob_to_start = False

        # 5. Initial Mark Position
        if self._dragging:
            self._tick_frozen = True
        else:
            if self._tick_easing:
                elapsed = time.monotonic() - self._tick_ease_t0
                dur = 0.5
                if elapsed >= dur:
                    self._tick_display_sx = self._tick_target_sx
                    self._tick_easing     = False
                else:
                    t = elapsed / dur
                    v = 1.0 - (1.0 - t) ** 5
                    self._tick_display_sx = (
                        self._tick_ease_start_sx
                        + (self._tick_target_sx - self._tick_ease_start_sx) * v
                    )
            elif not self._tick_frozen:
                if attr and (attr.max_val - attr.min_val) != 0:
                    init_ratio = (self._initial_value - attr.min_val) / (attr.max_val - attr.min_val)
                else:
                    init_ratio = 0.0
                init_ratio = max(0.0, min(1.0, init_ratio))
                self._tick_display_sx = self._track_x1 + init_ratio * (self._track_x2 - self._track_x1)
 
        self._init_sx = self._tick_display_sx

        # 6. Knob
        if self._knob is not None:
            self._knob.cur_px = [
                P(p.x - self._last_knob_sx, p.y - self._last_knob_sy)
                for p in self._knob.cur_px
            ]
            self._knob.update()
            self._knob.cur_px = [
                P(p.x + self._knob_sx, p.y + self._knob_sy)
                for p in self._knob.cur_px
            ]
            self._last_knob_sx = self._knob_sx
            self._last_knob_sy = self._knob_sy
            self._knob._dirty = True

        # 7. Mark Fill
        if self._mark_fill is not None:
            self._mark_fill.update()
            left_x  = min(self._knob_sx, self._tick_display_sx)
            right_x = max(self._knob_sx, self._tick_display_sx)
            half = (self.defn.mark_fill.px[2].y - self.defn.mark_fill.px[0].y) / 2
            self._mark_fill.cur_points = [P(0, 0)] * 4
            self._mark_fill.cur_px = [
                P(left_x,  self._knob_sy - half),
                P(right_x, self._knob_sy - half),
                P(right_x, self._knob_sy + half),
                P(left_x,  self._knob_sy + half),
            ]
            self._mark_fill._dirty = True

        # 8. Mark Tick
        if self._mark_tick is not None:
            self._mark_tick.update()
            base_px = self.defn.mark_tick.px or [P(0, 0)] * 4
            self._mark_tick.cur_points = [P(0, 0)] * 4
            self._mark_tick.cur_px = [
                P(base_px[0].x + self._tick_display_sx, base_px[0].y + self._knob_sy),
                P(base_px[1].x + self._tick_display_sx, base_px[1].y + self._knob_sy),
                P(base_px[2].x + self._tick_display_sx, base_px[2].y + self._knob_sy),
                P(base_px[3].x + self._tick_display_sx, base_px[3].y + self._knob_sy),
            ]
            self._mark_tick._dirty = True

        # 9. Label text
        if self._text_label is not None:
            self._text_label.update()

        if self._text_min is not None:
            self._text_min.cur_px -= self._last_text_min_x
            self._text_min.cur_py -= self._last_text_min_y
            self._text_min.update()
            self._text_min.cur_x   = 0.0
            self._text_min.cur_y   = 0.0
            self._text_min.cur_px  = self._track_x1 + self._text_min.cur_px
            self._text_min.cur_py  = self._track_y1 + self._text_min.cur_py
            self._last_text_min_x  = self._track_x1
            self._last_text_min_y  = self._track_y1
            self._text_min._dirty  = True

        if self._text_max is not None:
            self._text_max.cur_px -= self._last_text_max_x
            self._text_max.cur_py -= self._last_text_max_y
            self._text_max.update()
            self._text_max.cur_x   = 0.0
            self._text_max.cur_y   = 0.0
            self._text_max.cur_px  = self._track_x2 + self._text_max.cur_px
            self._text_max.cur_py  = self._track_y1 + self._text_max.cur_py
            self._last_text_max_x  = self._track_x2
            self._last_text_max_y  = self._track_y1
            self._text_max._dirty  = True

        if self._text_current is not None:
            self._text_current.cur_px -= self._last_text_cur_x
            self._text_current.cur_py -= self._last_text_cur_y
            self._text_current.update()
            self._text_current.cur_x   = 0.0
            self._text_current.cur_y   = 0.0
            self._text_current.cur_px  = self._knob_sx + self._text_current.cur_px
            self._text_current.cur_py  = self._knob_sy + self._text_current.cur_py
            self._last_text_cur_x      = self._knob_sx
            self._last_text_cur_y      = self._knob_sy
            self._text_current._dirty  = True
        
            
    def draw(self, painter: QPainter, w: int, h: int):
        cam_w, cam_h = self.cam_w, self.cam_h
        if self._track     is not None: self._track.draw(painter, w, h, cam_w, cam_h)
        if self._mark_fill is not None: self._mark_fill.draw(painter, w, h, cam_w, cam_h)
        if self._mark_tick is not None: self._mark_tick.draw(painter, w, h, cam_w, cam_h)
        if self._knob      is not None: self._knob.draw(painter, w, h, cam_w, cam_h)
        for text in (self._text_label, self._text_min,
                    self._text_max, self._text_current):
            if text is None or text.hidden:
                continue
            text.draw_text(painter, w, h, cam_w, cam_h, self)

# ──────────────────────── BUTTON DEF ────────────────────────

@dataclass
class ButtonDef:
    poly:   PolygonDef = PolygonDef()
    label:  str = ''
    hx1:    P = field(default_factory=P)
    hx2:    P = field(default_factory=P)
    hpx1:   P = field(default_factory=P)
    hpx2:   P = field(default_factory=P)
    text:   Optional[TextDef] = None
    font_family: str   = 'Oxanium SemiBold'
    font_size:   float = 10.0
    text_color:  QColor = field(default_factory=lambda: QColor(255, 255, 255))
    key:         Optional[int] = None 
    action:      str = 'set'
    event_out:   Any = None
    event_delta: Any = None

class ButtonDiamond(PolygonDef):
    def __new__(
        cls,
        p:    P   = P(0.5, 0.5),
        px:   P   = P(0.0, 0.0),
        size: int = 16,
        fill_idle:     QColor = QColor(255, 255, 255, 120),
        fill_hover:    QColor = QColor(255, 255, 255, 200),
        fill_press:    QColor = QColor(255, 255, 255, 240),
        fill_zero:     QColor = QColor(255, 255, 255,   0),
        outline_color: QColor = QColor(255, 255, 255, 255),
        line_width:    float  = 1.0,
        open_start:    float = 0.10,
        open_dur:      float = 0.30,
        close_dur:     float = 0.20,
        phase_open:     Phase = None,
        phase_close:    Phase = None,
        phase_hovered:  Phase = None,
        phase_unhovered:Phase = None,
        phase_pressed:  Phase = None,
        phase_released: Phase = None,
        **kwargs,
    ):
        pts = [p] * 4
        def _px(s): return [P(px.x, px.y-s), P(px.x+s, px.y), P(px.x, px.y+s), P(px.x-s, px.y)]
        phases = {
            'open':      phase_open      or Phase([PolygonTween(points=pts, px=_px(0),             fill_color=fill_zero,  outline_color=QColor(outline_color.red(), outline_color.green(), outline_color.blue(), 0), start=0.00, dur=0.00, ease=QEasingCurve.Linear),
                                                   PolygonTween(points=pts, px=_px(size),          fill_color=fill_idle,  outline_color=outline_color,start=open_start, dur=open_dur,ease=QEasingCurve.OutBack)]),
            'close':     phase_close     or Phase([PolygonTween(points=pts, px=_px(0),             fill_color=fill_zero,  outline_color=QColor(outline_color.red(), outline_color.green(), outline_color.blue(), 0),start=0.00, dur=close_dur,ease=QEasingCurve.InQuint)]),
            'hovered':   phase_hovered   or Phase([PolygonTween(points=pts, px=_px(int(size*1.3)), fill_color=fill_hover, outline_color=outline_color,start=0.00, dur=0.12, ease=QEasingCurve.OutQuint)]),
            'unhovered': phase_unhovered or Phase([PolygonTween(points=pts, px=_px(size),          fill_color=fill_idle,  outline_color=outline_color,start=0.00, dur=0.15, ease=QEasingCurve.OutQuint)]),
            'pressed':   phase_pressed   or Phase([PolygonTween(points=pts, px=_px(int(size*0.8)), fill_color=fill_press, outline_color=outline_color,start=0.00, dur=0.08, ease=QEasingCurve.OutQuint)]),
            'released':  phase_released  or Phase([PolygonTween(points=pts, px=_px(int(size*1.3)), fill_color=fill_hover, outline_color=outline_color,start=0.00, dur=0.12, ease=QEasingCurve.OutBack)]),
        }

        instance = super().__new__(cls)
        PolygonDef.__init__(
            instance,
            points        = pts,
            px            = _px(size),
            fill_color    = fill_zero,
            outline_color = QColor(outline_color.red(), outline_color.green(), outline_color.blue(), 0),
            line_width    = line_width,
            closed        = True,
            phases        = phases,
        )
        return instance

    def __init__(self, *args, **kwargs):
        pass

class AnimatedButton:
    def __init__(self, defn: ButtonDef, cam_w: int = 1920, cam_h: int = 1080):
        self.defn       = defn
        self.cam_w      = cam_w
        self.cam_h      = cam_h
        self._hovered   = False
        self._pressed   = False
        self._key_held  = False
        self._polygon   = AnimatedPolygon(defn.poly)
        self._text      = AnimatedText(defn.text) if defn.text else None
        self._locked    = False
        self._cur_phase = ''
        self._last_poly:  QPolygonF = QPolygonF()
        self._press_poly: QPolygonF = QPolygonF()

    def _set_phase(self, phase: str):
        # Always allow open to interrupt close, always allow open/close to set
        if self._locked and phase not in ('open', 'close'):
            return
        self._cur_phase = phase
        self._locked = phase in ('open', 'close')
        self._polygon.set_phase(phase)
        if self._text is not None:
            self._text.set_phase(phase)
    
    def key_press(self, key: int) -> bool:
        if (self.defn.key is None or self.defn.key != key or self._cur_phase == 'close' or self._key_held):
            return False
        self._key_held  = True
        self._pressed   = True
        self._press_poly = QPolygonF(self._last_poly)
        self._set_phase('pressed')
        return True

    def key_release(self, key: int) -> bool:
        if self.defn.key is None or self.defn.key != key or not self._key_held:
            return False
        self._key_held = False
        self._pressed  = False
        self._set_phase('released')
        self.fire_event()
        QTimer.singleShot(150, lambda: (self._set_phase('hovered' if self._hovered else 'unhovered')))
        return True

    def _hit_rect(self, w: int, h: int) -> Tuple[float, float, float, float]:
        d  = self.defn
        x1 = d.hx1.x * w + d.hpx1.x
        y1 = d.hx1.y * h + d.hpx1.y
        x2 = d.hx2.x * w + d.hpx2.x
        y2 = d.hx2.y * h + d.hpx2.y
        return x1, y1, x2, y2

    def hit_test(self, mx: float, my: float, w: int, h: int) -> bool:
        if not self._last_poly.isEmpty():
            return self._last_poly.containsPoint(QPointF(mx, my), Qt.OddEvenFill)
        return self._polygon.get_polygon(w, h, self.cam_w, self.cam_h).containsPoint(QPointF(mx, my), Qt.OddEvenFill)

    def _hit_test_press_poly(self, mx: float, my: float) -> bool:
        if not self._press_poly.isEmpty():
            return self._press_poly.containsPoint(QPointF(mx, my), Qt.OddEvenFill)
        return False

    def hit_test_global(self, gx: float, gy: float, panel) -> bool:
        return self.hit_test(gx - panel.x(), gy - panel.y(), panel.width(), panel.height())

    def update(self, widget_w: int = 0, widget_h: int = 0):
        self._polygon.update()
        if self._text is not None:
            self._text.update()
        if self._locked and self._polygon.phase_done():
            self._locked = False
        # w = widget_w if widget_w > 0 else self._draw_w
        # h = widget_h if widget_h > 0 else self._draw_h
        w = max(0, widget_w) 
        h = max(0, widget_h)
        if w > 0 and h > 0:
            self._polygon._dirty = True
            self._last_poly = self._polygon.get_polygon(w, h, self.cam_w, self.cam_h)

    def phase_done(self) -> bool:
        text_done = self._text.phase_done() if self._text is not None else True
        return self._polygon.phase_done() and text_done
    
    def fire_event(self) -> None:
        ev = self.defn.event_out
        if ev is None:
            return
        delta  = self.defn.event_delta
        action = self.defn.action

        if action == 'increment':
            if delta is not None and isinstance(ev.value, (int, float)) and not isinstance(ev.value, bool):
                new_val = ev.value + delta
                lo = getattr(ev, 'min_val', None)
                hi = getattr(ev, 'max_val', None)
                if lo is not None: new_val = max(float(lo), new_val)
                if hi is not None: new_val = min(float(hi), new_val)
                ev.value = int(round(new_val)) if isinstance(ev.value, int) else new_val
            return

        if action == 'set':
            if delta is not None:
                ev.value = delta
            return

        if isinstance(ev.value, bool):
            ev.value = (not ev.value) if delta is None else bool(delta)
        elif isinstance(ev.value, (int, float)):
            if delta is None:
                return
            new_val = ev.value + delta
            lo = getattr(ev, 'min_val', None)
            hi = getattr(ev, 'max_val', None)
            if lo is not None: new_val = max(float(lo), new_val)
            if hi is not None: new_val = min(float(hi), new_val)
            ev.value = int(round(new_val)) if isinstance(ev.value, int) else new_val
        elif isinstance(ev.value, str):
            if delta is not None:
                ev.value = str(delta)
 

    def draw(self, painter: QPainter, w: int, h: int):
        self._draw_w    = w
        self._draw_h    = h
        self._last_poly = self._polygon.get_polygon(w, h, self.cam_w, self.cam_h)
        self._polygon.draw(painter, w, h, self.cam_w, self.cam_h)
        if self._text is not None and not self._text.hidden:
            label = self._text.resolve_text(None)
            if label:
                font = self._text.build_font()
                painter.setFont(font)
                painter.setPen(self._text.cur_color)
                dx, dy = self._text.resolve_pos(w, h, self.cam_w, self.cam_h, label, font)
                painter.drawText(dx, dy, label)
                painter.setPen(Qt.NoPen)
        elif self.defn.label:
            # fallback: center label in polygon bounding rect
            poly = self._polygon.get_polygon(w, h, self.cam_w, self.cam_h)
            r    = poly.boundingRect()
            f    = _make_font(self.defn.font_family, self.defn.font_size)
            fm   = QFontMetrics(f)
            painter.setFont(f)
            painter.setPen(self.defn.text_color)
            painter.drawText(
                int(r.x() + (r.width()  - fm.horizontalAdvance(self.defn.label)) / 2),
                int(r.y() + (r.height() + fm.ascent()) / 2 - fm.descent()),
                self.defn.label,
            )
            painter.setPen(Qt.NoPen)

# ──────────────────────── GRAPH DEF ────────────────────────
 
@dataclass
class GraphDef:
    p1:              P
    p2:              P
    px1:             P                       = field(default_factory=P)
    px2:             P                       = field(default_factory=P)
    series:          List[SeriesDef]         = field(default_factory=list)
    max_time:        Any                     = 10.0
    value_range:     Tuple[float, float]     = (0.0, 0.0)
    value_color:     QColor                  = QColor(255, 255, 255, 255)
    ease_dur:        float                   = 0.3
    ease_type:       QEasingCurve.Type       = QEasingCurve.OutQuint
    dynamic_scale:   float                   = 0.0
    show_minmax:     bool                    = False
    show_step:      bool                    = False
    step_count:      Any                     = 0
    size_minmax:     float                   = 10.0
    size_step:      float                   = 9.0
    label_align:     str                     = 'right'
    stack:           bool                    = False
    update_interval: float                   = 0.0
    hidden:          bool                    = False
 
@dataclass
class SeriesDef:
    value_fn:     Optional[Callable[[Any], Optional[float]]] = None
    data_fn:      Optional[Callable[[Any], List[float]]]     = None
    color:        QColor  = field(default_factory=lambda: QColor(255, 255, 255, 255))
    line_width:   float   = 1.5
    fill_opacity: float   = 0.0
    smooth:       bool    = False

class _SeriesState: 
    def __init__(self) -> None:
        self.waypoints: List[Tuple[float, float]] = []
        self.tip_committed: Optional[float] = None
        self.tip_display:   Optional[float] = None
        self.tip_start:     float           = 0.0
        self.tip_t0:        float           = 0.0
        self.pending_values:      List[float] = []
        self.last_data_fn_result: List[float] = []
 
class AnimatedGraph:
    def __init__(self, defn: GraphDef) -> None:
        self.defn   = defn
        self.hidden = defn.hidden
        self._series: List[_SeriesState] = [_SeriesState() for _ in defn.series]
        self._range_lo_tgt:   float = defn.value_range[0]
        self._range_hi_tgt:   float = defn.value_range[1]
        self._range_lo:       float = defn.value_range[0]
        self._range_hi:       float = defn.value_range[1]
        self._range_lo_start: float = defn.value_range[0]
        self._range_hi_start: float = defn.value_range[1]
        self._range_ease_t0:  float = 0.0
        self._range_easing:   bool  = False
        self._last_update_time: float = 0.0
 
    def _screen_rect(self, ww: int, wh: int) -> Tuple[float, float, float, float]:
        d  = self.defn
        x1 = d.p1.x * ww + d.px1.x
        y1 = d.p1.y * wh + d.px1.y
        x2 = d.p2.x * ww + d.px2.x
        y2 = d.p2.y * wh + d.px2.y
        return x1, y1, x2 - x1, y2 - y1
 
    def _time_to_x(self, abs_t: float, now: float, left: float, width: float) -> float:
        return left + (1.0 - (now - abs_t) / self._max_time) * width

    def _value_to_y(self, value: float, top: float, height: float, lo: float, hi: float) -> float:
        ratio = (value - lo) / (hi - lo) if hi != lo else 0.5
        return top + height * (1.0 - max(0.0, min(1.0, ratio)))

    @property
    def _max_time(self) -> float:
        mt = self.defn.max_time
        return float(mt()) if callable(mt) else float(mt)
 
 
    def _tip_display_value(self, st: _SeriesState, now: float) -> Optional[float]:
        if st.tip_committed is None:
            return None
        if st.tip_display is None:
            return st.tip_committed
        elapsed = now - st.tip_t0
        dur     = self.defn.ease_dur
        if dur <= 0.0 or elapsed >= dur:
            return st.tip_committed
        v = _ease(elapsed / dur, self.defn.ease_type)
        return st.tip_start + (st.tip_committed - st.tip_start) * v
 
    def _push_value(self, st: _SeriesState, value: float, now: float) -> None:
        if st.tip_committed is None:
            st.tip_committed = value
            st.tip_display   = value
            st.tip_start     = value
            st.tip_t0        = now
            st.waypoints.append((now, value))
            return
 
        cur = self._tip_display_value(st, now)
        st.tip_start     = cur if cur is not None else st.tip_committed
        st.tip_display   = st.tip_start
        st.tip_committed = value
        st.tip_t0        = now
 
        st.waypoints.append((now, value))
 
        self._prune(st, now)
 
    def _prune(self, st: _SeriesState, now: float) -> None:
        cutoff  = now - self._max_time
        outside = [i for i, (t, _) in enumerate(st.waypoints) if t < cutoff]
        if len(outside) > 1:
            st.waypoints = st.waypoints[outside[-1]:]
 
    def _step_value_at_time(self, st: _SeriesState,
                             query_t: float, now: float) -> float:
        if st.tip_committed is None:
            return 0.0
        wps = st.waypoints
        if not wps:
            return st.tip_committed
        if query_t >= wps[-1][0]:
            return st.tip_committed
        if query_t <= wps[0][0]:
            return wps[0][1]
        for i in range(len(wps) - 1):
            if wps[i][0] <= query_t < wps[i + 1][0]:
                return wps[i][1]
 
        return wps[-1][1]
 
    def _step_value_at_x(self, st, now, rx, rw, x):
        if rw <= 0:
            return 0.0
        query_t = now - self._max_time * (1.0 - (x - rx) / rw)
        return max(0.0, self._step_value_at_time(st, query_t, now))
 
    def _compute_target_range(self, now: float) -> Tuple[float, float]: # Dynamic Range = True
        d            = self.defn
        base_lo, base_hi = d.value_range
        step         = d.dynamic_scale
 
        if d.stack:
            all_times: set = {now}
            for st in self._series:
                for abs_t, _ in st.waypoints:
                    all_times.add(abs_t)
            sums = [
                sum(max(0.0, self._step_value_at_time(st, t, now))
                    for st in self._series)
                for t in all_times
            ]
            raw_lo = min(sums) if sums else base_lo
            raw_hi = max(sums) if sums else base_hi
        else:
            values: List[float] = []
            for st in self._series:
                values.extend(v for _, v in st.waypoints)
                if st.tip_committed is not None:
                    values.append(st.tip_committed)
            raw_lo = min(values) if values else base_lo
            raw_hi = max(values) if values else base_hi
 
        if step > 0:
            new_lo = _math.floor(raw_lo / step) * step
            new_hi = _math.ceil(raw_hi  / step) * step
        else:
            new_lo, new_hi = raw_lo, raw_hi
 
        return (min(new_lo, base_lo), max(new_hi, base_hi))
 
    def _update_dynamic_range(self, now: float) -> None:
        lo, hi = self._compute_target_range(now)
        if lo == self._range_lo_tgt and hi == self._range_hi_tgt:
            return
        cur_lo, cur_hi       = self._effective_range_eased(now)
        self._range_lo_start = cur_lo
        self._range_hi_start = cur_hi
        self._range_lo_tgt   = lo
        self._range_hi_tgt   = hi
        self._range_ease_t0  = now
        self._range_easing   = True
 
    def _effective_range_eased(self, now: float) -> Tuple[float, float]:
        if self.defn.dynamic_scale == 0.0:
            return self.defn.value_range
        if not self._range_easing:
            return (self._range_lo, self._range_hi)
        elapsed = now - self._range_ease_t0
        dur     = self.defn.ease_dur
        if dur <= 0.0 or elapsed >= dur:
            self._range_lo     = self._range_lo_tgt
            self._range_hi     = self._range_hi_tgt
            self._range_easing = False
            return (self._range_lo, self._range_hi)
        v  = _ease(elapsed / dur, self.defn.ease_type)
        lo = self._range_lo_start + (self._range_lo_tgt - self._range_lo_start) * v
        hi = self._range_hi_start + (self._range_hi_tgt - self._range_hi_start) * v
        self._range_lo = lo
        self._range_hi = hi
        return (lo, hi)
 
    def _build_pts(self, st: _SeriesState, now: float, rx: float, ry: float, rw: float, rh: float, lo: float, hi: float) -> List[QPointF]:
        if st.tip_committed is None:
            return []
        cutoff = now - self._max_time
 
        def to_pt(abs_t: float, val: float) -> QPointF:
            return QPointF(self._time_to_x(abs_t, now, rx, rw), self._value_to_y(val, ry, rh, lo, hi))
 
        wps = st.waypoints
        first_inside = next((i for i, (t, _) in enumerate(wps) if t >= cutoff), len(wps))
 
        pts: List[QPointF] = []
 
        if first_inside > 0:
            anchor_t, anchor_v = wps[first_inside - 1]
            pts.append(to_pt(anchor_t, anchor_v))

        for abs_t, val in wps[first_inside:]:
            pts.append(to_pt(abs_t, val))
 
        tip_val = self._tip_display_value(st, now)
        if tip_val is None:
            tip_val = st.tip_committed
        pts.append(QPointF(rx + rw, self._value_to_y(tip_val, ry, rh, lo, hi)))
 
        return pts
 
    def _collect_x_boundaries(self, now: float,
                                rx: float, rw: float) -> List[float]:
        xs: set = {rx, rx + rw}
        for st in self._series:
            for abs_t, _ in st.waypoints:
                xs.add(self._time_to_x(abs_t, now, rx, rw))
        return sorted(xs)
 
    def _build_stacked_pts(self, now: float, rx: float, ry: float, rw: float, rh: float, lo: float, hi: float) -> List[List[QPointF]]:
        xs       = self._collect_x_boundaries(now, rx, rw)
        n_ser    = len(self._series)
        bottom_y = ry + rh
        span     = hi - lo
        ppu      = rh / span if span != 0 else 0.0
 
        tops: List[List[float]] = [[] for _ in range(n_ser)]
        for x in xs:
            cum_px = 0.0
            for si, st in enumerate(self._series):
                v = self._step_value_at_x(st, now, rx, rw, x)
                cum_px += v * ppu
                tops[si].append(bottom_y - cum_px)
 
        return [
            [QPointF(xs[xi], tops[si][xi]) for xi in range(len(xs))]
            for si in range(n_ser)
        ]
 
    def tick(self, now: float) -> None:
        d = self.defn
        for st in self._series:
            self._prune(st, now)
        if d.dynamic_scale != 0.0:
            self._update_dynamic_range(now)
        if d.update_interval > 0.0 and now - self._last_update_time >= d.update_interval:
            self._last_update_time = now
            for sd, st in zip(d.series, self._series):
                if st.pending_values:
                    val = sum(st.pending_values) / len(st.pending_values)
                    st.pending_values.clear()
                elif st.tip_committed is not None:
                    val = st.tip_committed
                else:
                    continue
                self._push_value(st, val, now)
 
    def _ingest(self, ctx: Any, now: float) -> None:
        d = self.defn
        for sd, st in zip(d.series, self._series):
            if sd.value_fn is not None:
                try:    raw = sd.value_fn(ctx)
                except: raw = None
                if raw is not None:
                    if d.update_interval > 0.0:
                        st.pending_values.append(float(raw))
                    else:
                        self._push_value(st, float(raw), now)
            elif sd.data_fn is not None:
                try:    samples = sd.data_fn(ctx) or []
                except: samples = []
                if samples != st.last_data_fn_result:
                    if not st.last_data_fn_result and samples:
                        n = len(samples)
                        for i, val in enumerate(samples):
                            fake_t = now - self._max_time * (1.0 - (i + 1) / n)
                            st.waypoints.append((fake_t, float(val)))
                        last = float(samples[-1])
                        st.tip_committed = last
                        st.tip_display   = last
                        st.tip_start     = last
                        st.tip_t0        = now
                    else:
                        new_vals = samples[len(st.last_data_fn_result):]
                        if d.update_interval > 0.0:
                            st.pending_values.extend(float(v) for v in new_vals)
                        else:
                            for val in new_vals:
                                self._push_value(st, float(val), now)
                    st.last_data_fn_result = list(samples)
    
    def _draw_labels(self, painter: QPainter,
                     rx: float, ry: float, rw: float, rh: float) -> None:
        d = self.defn
 
        show_minmax = d.show_minmax
        show_step  = d.show_step
        step_count  = int(d.step_count() if callable(d.step_count) else d.step_count)
        size_minmax = d.size_minmax
        size_step   = d.size_step
 
        if not show_minmax and (not show_step or step_count <= 0):
            return
 
        if d.dynamic_scale != 0.0:
            lo = self._range_lo_tgt
            hi = self._range_hi_tgt
        else:
            lo, hi = d.value_range
 
        base_color = d.value_color
 
        def _fmt(v: float) -> str:
            if v == int(v):
                return str(int(v))
            mag = abs(v)
            if mag == 0:
                return '0'
            decimals = max(0, 2 - int(_math.floor(_math.log10(mag)))) if mag >= 1 else 3
            return f'{v:.{decimals}f}'.rstrip('0').rstrip('.')
 
        def _label_color():
            return QColor(base_color.red(), base_color.green(),
                          base_color.blue(), 180)
 
        def _make_label_font(font_size: float):
            f = QFont()
            f.setPointSizeF(max(0.5, font_size))
            return f, QFontMetrics(f)
 
        def _draw_right(text: str, font_size: float, y_center: float) -> None:
            f, fm = _make_label_font(font_size)
            x = int(rx - 4 - fm.horizontalAdvance(text))
            y = int(y_center + fm.ascent() * 0.5 - fm.descent() * 0.5)
            painter.setFont(f)
            painter.setPen(_label_color())
            painter.drawText(x, y, text)
            painter.setPen(Qt.NoPen)
 
        def _draw_left(text: str, font_size: float, y_center: float) -> None:
            f, fm = _make_label_font(font_size)
            x = int(rx + 4)
            y = int(y_center + fm.ascent() * 0.5 - fm.descent() * 0.5)
            painter.setFont(f)
            painter.setPen(_label_color())
            painter.drawText(x, y, text)
            painter.setPen(Qt.NoPen)
 
        _draw = _draw_right if d.label_align == 'right' else _draw_left
 
        if show_minmax:
            _draw(_fmt(hi), size_minmax, ry)
            _draw(_fmt(lo), size_minmax, ry + rh)
 
        if show_step and step_count > 0:
            for i in range(1, step_count + 1):
                ratio = i / (step_count + 1)
                _draw(_fmt(lo + ratio * (hi - lo)), size_step,
                      ry + rh * (1.0 - ratio))

    def draw(self, painter: QPainter, widget_w: int, widget_h: int, ctx: Any = None, cam_w: int = 1920, cam_h: int = 1080) -> None:
        if self.hidden:
            return
 
        now = time.monotonic()
        d   = self.defn
 
        self._ingest(ctx, now)
 
        rx, ry, rw, rh = self._screen_rect(widget_w, widget_h)
        if rw <= 0 or rh <= 0:
            return
 
        lo, hi   = self._effective_range_eased(now)
        bottom_y = ry + rh
 
        if d.stack:
            all_pts = self._build_stacked_pts(now, rx, ry, rw, rh, lo, hi)
        else:
            all_pts = [self._build_pts(st, now, rx, ry, rw, rh, lo, hi) for st in self._series]
 
        painter.save()
        painter.setClipRect(int(rx), int(ry), int(rw + 1), int(rh + 1))
 
        for si, (sd, st) in enumerate(zip(d.series, self._series)):
            pts = all_pts[si]
            if not pts:
                continue
 
            if sd.fill_opacity > 0.0:
                fill_color = QColor(sd.color)
                fill_color.setAlphaF(sd.fill_opacity)
                fill_poly  = QPolygonF()
                if d.stack and si > 0:
                    for pt in pts:
                        fill_poly.append(pt)
                    for pt in reversed(all_pts[si - 1]):
                        fill_poly.append(pt)
                else:
                    fill_poly.append(QPointF(pts[0].x(), bottom_y))
                    for pt in pts:
                        fill_poly.append(pt)
                    fill_poly.append(QPointF(pts[-1].x(), bottom_y))
                painter.setPen(Qt.NoPen)
                painter.setBrush(fill_color)
                painter.drawPolygon(fill_poly)
                painter.setBrush(Qt.NoBrush)
 
            if sd.line_width > 0.0:
                pen = QPen(sd.color)
                pen.setWidthF(sd.line_width)
                pen.setCapStyle(Qt.RoundCap)
                pen.setJoinStyle(Qt.RoundJoin)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                for i in range(len(pts) - 1):
                    painter.drawLine(pts[i], pts[i + 1])
                painter.setPen(Qt.NoPen)
 
        painter.restore()
        self._draw_labels(painter, rx, ry, rw, rh)

# ──────────────────────── PIE DEF ────────────────────────

@dataclass
class PieDef:
    p1:         P
    p2:         P
    px1:        P                    = field(default_factory=P)
    px2:        P                    = field(default_factory=P)
    names:      List[str]            = field(default_factory=list)
    value_fns:  List[Callable[[Any], Optional[float]]] = field(default_factory=list)
    colors:     List[QColor]         = field(default_factory=list)
    border_width:  float             = 0.0
    fill_opacity:  float             = 1.0
    direction:  str                  = 'horizontal'   # 'horizontal' or 'vertical'
    size_label: float                = 9.0
    size_name:  float                = 9.0
    ease_dur:   float                = 0.3
    ease_type:  QEasingCurve.Type    = QEasingCurve.OutQuint
    hidden:     bool                 = False

class AnimatedPie:
    def __init__(self, defn: PieDef) -> None:
        self.defn   = defn
        self.hidden = defn.hidden
        
        n           = len(defn.names)
        self._raw_values:  List[Optional[float]] = [None] * n
        self._cur_ratios:  List[float]           = [1.0 / n] * n
        self._tgt_ratios:  List[float]           = [1.0 / n] * n
        self._start_ratios: List[float]          = [1.0 / n] * n
        self._ease_t0:      float                = 0.0
        self._easing:       bool                 = False

    def _screen_rect(self, ww: int, wh: int) -> Tuple[float, float, float, float]:
        d  = self.defn
        x1 = d.p1.x * ww + d.px1.x
        y1 = d.p1.y * wh + d.px1.y
        x2 = d.p2.x * ww + d.px2.x
        y2 = d.p2.y * wh + d.px2.y
        return x1, y1, x2 - x1, y2 - y1

    def _recompute_targets(self) -> None:
        vals   = [v for v in self._raw_values if v is not None and v > 0]
        n      = len(self.defn.names)
        total  = sum(v for v in self._raw_values if v is not None and v > 0)

        if total <= 0:
            new_tgt = [1.0 / n] * n
        else:
            new_tgt = []
            for v in self._raw_values:
                if v is not None and v > 0:
                    new_tgt.append(v / total)
                else:
                    new_tgt.append(0.0)

        if new_tgt == self._tgt_ratios:
            return

        now = time.monotonic()
        if self._easing:
            elapsed = now - self._ease_t0
            dur     = self.defn.ease_dur
            t       = min(1.0, elapsed / dur) if dur > 0 else 1.0
            v       = _ease(t, self.defn.ease_type)
            self._start_ratios = [s + (tgt - s) * v for s, tgt in zip(self._start_ratios, self._tgt_ratios)]
        else:
            self._start_ratios = list(self._cur_ratios)

        self._tgt_ratios = new_tgt
        self._ease_t0    = now
        self._easing     = True

    def update(self, ctx: Any) -> None:
        changed = False
        for i, fn in enumerate(self.defn.value_fns):
            try:
                raw = fn(ctx)
            except Exception:
                raw = None
            if raw != self._raw_values[i]:
                self._raw_values[i] = raw
                changed = True
        if changed:
            self._recompute_targets()

    def _advance_ease(self, now: float) -> None:
        if not self._easing:
            return
        elapsed = now - self._ease_t0
        dur     = self.defn.ease_dur
        if dur <= 0.0 or elapsed >= dur:
            self._cur_ratios = list(self._tgt_ratios)
            self._easing     = False
            return
        t = elapsed / dur
        v = _ease(t, self.defn.ease_type)
        self._cur_ratios = [s + (tgt - s) * v for s, tgt in zip(self._start_ratios, self._tgt_ratios)]

    def draw(self, painter: QPainter, widget_w: int, widget_h: int, cam_w: int = 1920, cam_h: int = 1080) -> None:
        if self.hidden:
            return

        now = time.monotonic()
        self._advance_ease(now)

        d = self.defn
        rx, ry, rw, rh = self._screen_rect(widget_w, widget_h)
        if rw <= 0 or rh <= 0:
            return

        n          = len(d.names)
        ratios     = self._cur_ratios
        horizontal = d.direction == 'horizontal'
        total_span = rw if horizontal else rh

        cursor = 0.0
        segments: List[Tuple[float, float, float, float, int]] = []
        for i, ratio in enumerate(ratios):
            span = total_span * ratio
            if horizontal:
                segments.append((rx + cursor, ry, span, rh, i))
            else:
                segments.append((rx, ry + cursor, rw, span, i))
            cursor += span

        painter.setPen(Qt.NoPen)
        for x, y, w, h, i in segments:
            if w < 0.5 or h < 0.5:
                continue
            color = QColor(d.colors[i] if i < len(d.colors) else QColor(255, 255, 255))
            color.setAlphaF(d.fill_opacity)
            painter.setBrush(color)
            painter.drawRect(QRectF(x, y, w, h))
        painter.setBrush(Qt.NoBrush)

        pct_font = QFont()
        pct_font.setPointSizeF(max(0.5, d.size_label))
        pct_fm = QFontMetrics(pct_font)
        painter.setFont(pct_font)

        for x, y, w, h, i in segments:
            if w < 0.5 or h < 0.5:
                continue
            pct   = ratios[i] * 100.0
            label = f'{pct:.1f}%'
            tw    = pct_fm.horizontalAdvance(label)
            th    = pct_fm.height()

            fits  = (tw + 8 <= w) if horizontal else (th + 4 <= h)
            if not fits:
                continue

            lx = int(x + (w - tw) / 2)
            ly = int(y + h / 2 + pct_fm.ascent() * 0.5 - pct_fm.descent() * 0.5)

            color = d.colors[i] if i < len(d.colors) else QColor(255, 255, 255)
            painter.setPen(color)
            painter.drawText(lx, ly, label)

        name_font = QFont()
        name_font.setPointSizeF(max(0.5, d.size_name))
        name_fm = QFontMetrics(name_font)
        painter.setFont(name_font)

        for x, y, w, h, i in segments:
            if w < 0.5 or h < 0.5:
                continue
            name = d.names[i] if i < len(d.names) else ''
            if not name:
                continue

            color = d.colors[i] if i < len(d.colors) else QColor(255, 255, 255)
            painter.setPen(color)

            nx = int(x)
            ny = int(y - name_fm.descent() - 2)
            painter.drawText(nx, ny, name)

        painter.setPen(Qt.NoPen)

        if d.border_width > 0.0:
            half = d.border_width / 2.0
            for x, y, w, h, i in segments:
                if w < 0.5 or h < 0.5:
                    continue
                color = d.colors[i] if i < len(d.colors) else QColor(255, 255, 255)
                pen = QPen(color)
                pen.setWidthF(d.border_width * 2.0)
                pen.setJoinStyle(Qt.MiterJoin)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.save()
                painter.setClipRect(QRectF(x, y, w, h))
                painter.drawRect(QRectF(x, y, w, h))
                painter.restore()
            painter.setPen(Qt.NoPen)

# ──────────────────────── WINDOW DEF ────────────────────────
@dataclass
class WindowDef:
    p1:            P
    p2:            P
    px1:           P                          = field(default_factory=P)
    px2:           P                          = field(default_factory=P)
    phase_event:   Any                        = None
    phases:        Dict[str, WindowPhase]     = field(default_factory=dict)
    polygon_defs:  List[PolygonDef]           = field(default_factory=list)
    text_defs:     List[TextDef]              = field(default_factory=list)
    graph_defs:    List[GraphDef]             = field(default_factory=list)
    pie_defs:      List[PieDef]               = field(default_factory=list)
    slider_defs:   List[SliderGroupDef]       = field(default_factory=list)
    button_defs:   List[ButtonDef]            = field(default_factory=list)
    gradient_defs: List[GradientDef]          = field(default_factory=list)
    listener_defs: List[EventListener]        = field(default_factory=list)

@dataclass
class WindowTween:
    p1:   P
    p2:   P
    px1:  P                    = field(default_factory=P)
    px2:  P                    = field(default_factory=P)
    start: float               = 0.0
    dur:   float               = 0.5
    ease:  QEasingCurve.Type   = QEasingCurve.OutQuint
    prev_phase: Optional[str]  = None

@dataclass
class WindowPhase:
    tweens: List[WindowTween]

class AnimatedWindow:
    def __init__(self, defn: WindowDef, cam_w: int = 1920, cam_h: int = 1080) -> None:
        self.defn   = defn
        self.cam_w  = cam_w
        self.cam_h  = cam_h

        self._polygons = [AnimatedPolygon(d) for d in defn.polygon_defs]
        self._texts    = [AnimatedText(d)    for d in defn.text_defs]
        self._graphs   = [AnimatedGraph(d)   for d in defn.graph_defs]
        self._pies     = [AnimatedPie(d)     for d in defn.pie_defs]
        self._sliders  = [SliderGroup(d, cam_w, cam_h) for d in defn.slider_defs]
        self._buttons  = [AnimatedButton(d, cam_w, cam_h) for d in defn.button_defs]
        for gd in defn.gradient_defs:
            gd._animated = _AnimatedGradient(gd)
        self._listeners = list(defn.listener_defs)

        self._dragging_slider: Optional[SliderGroup] = None
        self._cur_phase: str = ''

        self._cur_p1  = P(defn.p1.x,  defn.p1.y)
        self._cur_p2  = P(defn.p2.x,  defn.p2.y)
        self._cur_px1 = P(defn.px1.x, defn.px1.y)
        self._cur_px2 = P(defn.px2.x, defn.px2.y)
        self._s_p1    = self._cur_p1
        self._s_p2    = self._cur_p2
        self._s_px1   = self._cur_px1
        self._s_px2   = self._cur_px2
        self._win_tweens: List[WindowTween] = []
        self._win_timer   = QElapsedTimer()
        self._win_timer.restart()
        self._win_idx: int = 0
        self._win_prev_phase: str = ''

        for sl in self._sliders:
            sl.init_value(None)
        self._broadcast('open')

        if defn.phase_event is not None:
            defn.phase_event.value = 'open'

    def _screen_rect(self, ww: int, wh: int) -> Tuple[float, float, float, float]:
        x1 = self._cur_p1.x  * ww + self._cur_px1.x
        y1 = self._cur_p1.y  * wh + self._cur_px1.y
        x2 = self._cur_p2.x  * ww + self._cur_px2.x
        y2 = self._cur_p2.y  * wh + self._cur_px2.y
        return x1, y1, x2 - x1, y2 - y1

    def _broadcast(self, phase: str) -> None:
        prev = self._cur_phase
        self._cur_phase = phase
        for gd in self.defn.gradient_defs:
            gd._animated.set_phase(phase)
        for p   in self._polygons: p.set_phase(phase)
        for t   in self._texts:    t.set_phase(phase)
        for sl  in self._sliders:  sl.set_phase(phase)
        for btn in self._buttons:  btn._set_phase(phase)
        wp = self.defn.phases.get(phase)
        if wp:
            self._win_tweens = [tw for tw in wp.tweens if tw.prev_phase is None or tw.prev_phase == prev]
        else:
            self._win_tweens = []
        self._win_idx        = 0
        self._win_prev_phase = prev
        self._s_p1  = self._cur_p1
        self._s_p2  = self._cur_p2
        self._s_px1 = self._cur_px1
        self._s_px2 = self._cur_px2
        self._win_timer.restart()

    def _poll_phase_event(self) -> None:
        ev = self.defn.phase_event
        if ev is None:
            return
        val = str(ev.value)
        if val != self._cur_phase:
            self._broadcast(val)

    def _tick_win_tweens(self) -> None:
        tweens = self._win_tweens
        if not tweens or self._win_idx >= len(tweens):
            return
        elapsed = self._win_timer.elapsed() / 1000.0
        tw = tweens[self._win_idx]
        if elapsed < tw.start:
            return
        t = min(1.0, (elapsed - tw.start) / tw.dur) if tw.dur > 0 else 1.0
        v = _ease(t, tw.ease)
        self._cur_p1  = P(self._s_p1.x  + (tw.p1.x  - self._s_p1.x)  * v, self._s_p1.y  + (tw.p1.y  - self._s_p1.y)  * v)
        self._cur_p2  = P(self._s_p2.x  + (tw.p2.x  - self._s_p2.x)  * v, self._s_p2.y  + (tw.p2.y  - self._s_p2.y)  * v)
        self._cur_px1 = P(self._s_px1.x + (tw.px1.x - self._s_px1.x) * v, self._s_px1.y + (tw.px1.y - self._s_px1.y) * v)
        self._cur_px2 = P(self._s_px2.x + (tw.px2.x - self._s_px2.x) * v, self._s_px2.y + (tw.px2.y - self._s_px2.y) * v)
        if t >= 1.0:
            self._s_p1  = self._cur_p1
            self._s_p2  = self._cur_p2
            self._s_px1 = self._cur_px1
            self._s_px2 = self._cur_px2
            self._win_idx += 1

    def tick(self, now: float) -> None:
        self._poll_phase_event()
        self._tick_win_tweens()
        for g in self._graphs:
            g.tick(now)

    def update(self, ctx: Any, widget_w: int, widget_h: int) -> None:
        for gl in self._listeners:
            gl.tick(ctx)
        wx, wy, ww, wh = self._screen_rect(widget_w, widget_h)
        for gd in self.defn.gradient_defs:
            gd._animated.update()
        for p   in self._polygons: p.update()
        for t   in self._texts:    t.update()
        for pie in self._pies:     pie.update(ctx)
        for sl  in self._sliders:  sl.update(int(ww), int(wh))
        for btn in self._buttons:  btn.update(int(ww), int(wh))

    def _to_local(self, mx: float, my: float, widget_w: int, widget_h: int) -> Tuple[float, float, float, float]:
        wx, wy, ww, wh = self._screen_rect(widget_w, widget_h)
        return mx - wx, my - wy, ww, wh
    
    def key_press(self, key: int) -> bool:
        for btn in self._buttons:
            if btn.key_press(key):
                return True
        return False

    def key_release(self, key: int) -> bool:
        for btn in self._buttons:
            if btn.key_release(key):
                return True
        return False

    def mouse_press(self, mx: float, my: float, widget_w: int, widget_h: int) -> bool:
        lx, ly, ww, wh = self._to_local(mx, my, widget_w, widget_h)
        for sl in self._sliders:
            if sl.hit_test_knob(lx, ly, int(ww), int(wh)):
                self._dragging_slider = sl
                sl._dragging = True
                sl.drag_to(lx, ly, int(ww), int(wh))
                sl.commit(None)
                sl.set_phase('pressed')
                return True
        for btn in self._buttons:
            if btn.hit_test(lx, ly, int(ww), int(wh)):
                btn._pressed      = True
                btn._press_poly   = QPolygonF(btn._last_poly)
                btn._set_phase('pressed')
                return True
        return False

    def mouse_move(self, mx: float, my: float, widget_w: int, widget_h: int) -> bool:
        lx, ly, ww, wh = self._to_local(mx, my, widget_w, widget_h)
        if self._dragging_slider is not None:
            self._dragging_slider.drag_to(lx, ly, int(ww), int(wh))
            self._dragging_slider.commit(None)
            return True
        for sl in self._sliders:
            hit = sl.hit_test_knob(lx, ly, int(ww), int(wh))
            if hit != sl._hovered:
                sl._hovered = hit
                sl.set_phase('hovered' if hit else 'unhovered')
        for btn in self._buttons:
            hit = btn.hit_test(lx, ly, int(ww), int(wh))
            if hit != btn._hovered:
                btn._hovered = hit
                btn._set_phase('hovered' if hit else 'unhovered')
        return False

    def mouse_release(self, mx: float, my: float, widget_w: int, widget_h: int) -> bool:
        lx, ly, ww, wh = self._to_local(mx, my, widget_w, widget_h)
        sl = self._dragging_slider
        if sl is not None:
            sl._dragging = sl._pressed = False
            sl.set_phase('released')
            sl.commit(None)
            self._dragging_slider = None
            hovered = sl._hovered
            QTimer.singleShot(150, lambda: sl.set_phase('hovered' if hovered else 'unhovered'))
            return True
        for btn in self._buttons:
            if btn._pressed:
                btn._pressed = False
                btn._set_phase('released')
                if btn._hit_test_press_poly(lx, ly):
                    btn.fire_event()
                QTimer.singleShot(150, lambda b=btn: (b._set_phase('hovered' if b._hovered else 'unhovered')))
                return True
        return False

    def mouse_leave(self) -> None:
        for sl in self._sliders:
            if sl._hovered:
                sl._hovered = False
                sl.set_phase('unhovered')
        for btn in self._buttons:
            if btn._hovered:
                btn._hovered = False
                btn._set_phase('unhovered')

    def draw(self, painter: QPainter, widget_w: int, widget_h: int, ctx: Any = None) -> None:
        wx, wy, ww, wh = self._screen_rect(widget_w, widget_h)
        if ww <= 0 or wh <= 0:
            return

        painter.save()
        painter.translate(wx, wy)
        painter.setClipRect(QRectF(0, 0, ww, wh))

        iww, iwh = int(ww), int(wh)

        for poly in self._polygons:
            poly.draw(painter, iww, iwh, self.cam_w, self.cam_h)

        for text in self._texts:
            if text.hidden:
                continue
            text.draw_text(painter, iww, iwh, self.cam_w, self.cam_h, ctx)

        for g in self._graphs:
            g.draw(painter, iww, iwh, ctx, self.cam_w, self.cam_h)

        for pie in self._pies:
            pie.draw(painter, iww, iwh, self.cam_w, self.cam_h)

        for sl in self._sliders:
            sl.draw(painter, iww, iwh)

        for btn in self._buttons:
            btn.draw(painter, iww, iwh)

        painter.restore()

# ──────────────────────── EVENT DEF ────────────────────────

@dataclass
class EventDef:
    name:    str
    value:   Any                             = None
    min_val: Optional[Union[int, float]]     = None
    max_val: Optional[Union[int, float]]     = None
    step:    Optional[Union[int, float]]     = None
    label:   str                             = ''
    unit:    str                             = ''
    delay:   float                           = 0.0

    @property
    def _is_numeric(self) -> bool:
        return isinstance(self.value, (int, float)) and not isinstance(self.value, bool)

    def _clamp(self, v: float) -> Union[int, float]:
        if self.min_val is not None: v = max(float(self.min_val), v)
        if self.max_val is not None: v = min(float(self.max_val), v)
        if self.step:                v = round(v / self.step) * self.step
        return int(round(v)) if isinstance(self.value, int) else float(v)

    def set_numeric(self, v: float) -> None:
        if self._is_numeric:
            self.value = self._clamp(v)

# ──────────────────────── EVENT LISTENER ────────────────────────

@dataclass
class EventListener:
    value_fn:    Callable[[Any], Any]
    targets:     List[EventDef]                   = field(default_factory=list)
    passthrough: bool                             = False
    conditions:  List[Callable[[Any], bool]]      = field(default_factory=list)
    values:      List[Any]                        = field(default_factory=list)

    def _validate(self) -> bool:
        if self.passthrough:
            return True
        return len(self.values) == len(self.conditions) + 1

    def tick(self, ctx: Any) -> None:
        try:
            raw = self.value_fn(ctx)
        except Exception:
            raw = None

        if raw is None:
            return

        if self.passthrough:
            output = raw
        else:
            if not self._validate():
                return
            output = self.values[-1]
            for condition, value in zip(self.conditions, self.values):
                try:
                    if condition(raw):
                        output = value
                        break
                except Exception:
                    continue

        for target in self.targets:
            target.value = output


# ──────────────────────── DATA CHANNEL ────────────────────────

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

    def trend(self) -> Optional[float]:
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
        avg  = statistics.mean(data) if data else None
        mn   = min(data)             if data else None
        mx   = max(data)             if data else None
        dlt  = (data[-1] - data[-2]) if n >= 2 else None
        lat  = data[-1]              if data else None
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

# ──────────────────────── Helpers ────────────────────────

def _ease(t: float, curve) -> float:
    if curve == QEasingCurve.OutQuint:  return 1.0 - (1.0 - t) ** 5
    if curve == QEasingCurve.OutCirc:
        t2 = t - 1.0; return _math.sqrt(1.0 - t2 * t2)
    if curve == QEasingCurve.InQuint:   return t ** 5
    if curve == QEasingCurve.InOutCirc:
        if t < 0.5:
            return 0.5 * (1.0 - _math.sqrt(1.0 - 4.0 * t * t))
        t2 = 2.0 * t - 2.0; return 0.5 * (_math.sqrt(1.0 - t2 * t2) + 1.0)
    if curve == QEasingCurve.OutBack:
        c = 1.70158; t2 = t - 1.0
        return 1.0 + (c + 1.0) * t2 ** 3 + c * t2 ** 2
    if curve == QEasingCurve.InOutQuad:
        if t < 0.5: return 2.0 * t * t
        return 1.0 - (-2.0 * t + 2.0) ** 2 / 2.0
    if curve == QEasingCurve.InCirc:    return 1.0 - _math.sqrt(1.0 - t * t)
    if curve == QEasingCurve.Linear:    return t
    if curve == QEasingCurve.OutCubic:  return 1.0 - (1.0 - t) ** 3
    if curve == QEasingCurve.InCubic:   return t ** 3
    if curve == QEasingCurve.OutQuad:   return 1.0 - (1.0 - t) ** 2
    if curve == QEasingCurve.InQuad:    return t * t
    if curve == QEasingCurve.OutSine:   return _math.sin(t * _math.pi / 2)
    if curve == QEasingCurve.InSine:    return 1.0 - _math.cos(t * _math.pi / 2)
    # Fallback for any unlisted curve
    c = QEasingCurve(curve); return c.valueForProgress(t)

def lerp_color(src: QColor, dst: QColor, v: float) -> QColor:
    iv = 1.0 - v
    return QColor(
        int(src.red()   * iv + dst.red()   * v),
        int(src.green() * iv + dst.green() * v),
        int(src.blue()  * iv + dst.blue()  * v),
        int(src.alpha() * iv + dst.alpha() * v),
    )

def _with_alpha(color, alpha):
    c=QColor(color); c.setAlpha(alpha); return c

def _make_font(family, size):
    f=QFont(); f.setFamily(family); f.setPointSizeF(max(0.5,size)); return f

def _flip_p(p: P, h: bool, v: bool, blended: bool = False) -> P:
    if blended:
        return P(-p.x if h else p.x, -p.y if v else p.y)
    return P(1.0 - p.x if h else p.x, 1.0 - p.y if v else p.y)

def _flip_px(p: P, h: bool, v: bool) -> P:
    return P(-p.x if h else p.x, -p.y if v else p.y)

def _flip_polygon_def(defn: PolygonDef, h: bool, v: bool) -> PolygonDef:
    def _pts(pts, blended: bool = False):
        return [_flip_p(p, h, v, blended) for p in pts]
    def _pxs(pts):
        return [_flip_px(p, h, v) for p in pts]
    def _flip_tween(tw, prev_blended: bool):
        if isinstance(tw, Reset):
            return tw
        if isinstance(tw, PolygonTween):
            return PolygonTween(
                points        = _pts(tw.points, prev_blended) if tw.points is not None else None,
                px            = _pxs(tw.px) if tw.px is not None else None,
                fill_color    = tw.fill_color,
                outline_color = tw.outline_color,
                line_width    = tw.line_width,
                draw_progress = tw.draw_progress,
                start         = tw.start,
                dur           = tw.dur,
                ease          = tw.ease,
                blend         = tw.blend,
                prev_phase    = tw.prev_phase,
                span          = tw.span,
            )
        return tw
    def _flip_phase(phase):
        tweens = []
        prev_blended = False
        for tw in phase.tweens:
            tweens.append(_flip_tween(tw, prev_blended))
            prev_blended = isinstance(tw, PolygonTween) and bool(tw.blend)
        return Phase(tweens)

    return PolygonDef(
        points        = _pts(defn.points),
        px            = _pxs(defn.px) if defn.px is not None else None,
        fill_color    = defn.fill_color,
        outline_color = defn.outline_color,
        line_width    = defn.line_width,
        uniform_scale = defn.uniform_scale,
        closed        = defn.closed,
        draw_progress = defn.draw_progress,
        phases        = {k: _flip_phase(v) for k, v in defn.phases.items()},
    )

def expand_defs(defs: List[PolygonDef]) -> List[PolygonDef]:
    result = []
    for defn in defs:
        result.append(defn)
        h = getattr(defn, 'h_flip', False)
        v = getattr(defn, 'v_flip', False)
        d = getattr(defn, 'd_flip', False)
        if h: result.append(_flip_polygon_def(defn, h=True,  v=False))
        if v: result.append(_flip_polygon_def(defn, h=False, v=True))
        if d: result.append(_flip_polygon_def(defn, h=True,  v=True))
    return result

def _draw_partial_polyline(painter: QPainter, pts: List[QPointF], t: float) -> None:
    if len(pts) < 2 or t <= 0:
        return
    if t >= 1.0:
        for i in range(len(pts) - 1):
            painter.drawLine(pts[i], pts[i + 1])
        return
    lengths = [_math.sqrt((pts[i+1].x()-pts[i].x())**2 + (pts[i+1].y()-pts[i].y())**2) for i in range(len(pts) - 1)]
    total = sum(lengths)
    if total == 0:
        return
    target = total * t
    acc = 0.0
    for i, seg_len in enumerate(lengths):
        if acc >= target:
            break
        rem = target - acc
        if rem >= seg_len:
            painter.drawLine(pts[i], pts[i + 1])
            acc += seg_len
        else:
            frac = rem / seg_len if seg_len > 0 else 1.0
            painter.drawLine(pts[i], QPointF(pts[i].x() + (pts[i+1].x() - pts[i].x()) * frac, pts[i].y() + (pts[i+1].y() - pts[i].y()) * frac))
            break