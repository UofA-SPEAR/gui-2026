from __future__ import annotations
from typing import Optional, Dict, List, Tuple, Callable, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore    import Qt, QTimer, QElapsedTimer, QEasingCurve, QPointF, QRectF, QEvent, QObject
from PySide6.QtGui     import QColor, QPainter, QFont, QFontMetrics, QPolygonF, QPen, QBrush, QRegion, QPainterPath, QLinearGradient, QRadialGradient
import time
import collections
import statistics
import threading
import math as _math
import uuid

from spear_gui.gui_vars import MONITOR_RESOLUTIONS

_window_layer_registry: List[Tuple[int, List['WindowDef']]] = []

def register_windows(layer: int, windows: List['WindowDef']) -> None:
    _window_layer_registry.append((layer, windows))

def get_ordered_windows() -> List['WindowDef']:
    result = []
    for _, windows in sorted(_window_layer_registry, key=lambda x: x[0]):
        result.extend(windows)
    return result

_events: Dict[str, 'EventDef'] = {}

def register_event(defn: 'EventDef') -> 'EventDef':
    _events[defn.name] = defn
    return defn

def get_event(name: str) -> 'EventDef':
    return _events[name]

_gradients: Dict[str, GradientDef] = {}

def register_gradient(defn: GradientDef) -> GradientDef:
    defn._animated = _AnimatedGradient(defn)
    _gradients[defn.name] = defn
    return defn

def get_gradient(name: str) -> GradientDef:
    return _gradients[name]

@dataclass(frozen=True)
class P:
    x: float = 0.0
    y: float = 0.0

@dataclass
class GradientStop:
    position: float
    color:    QColor

def RectDef(
    p1:                  P                             = P(), 
    p2:                  P                             = P(), 
    px1:                 P                             = P(), 
    px2:                 P                             = P(),
    tl:                  Optional[Tuple[P, P]]         = None, 
    tr:                  Optional[Tuple[P, P]]         = None,
    br:                  Optional[Tuple[P, P]]         = None, 
    bl:                  Optional[Tuple[P, P]]         = None,
    fill_color:          Optional[QColor]              = QColor(255, 255, 255, 255), 
    outline_color:       Optional[QColor]              = None,
    outline_width:          float                         = 0.0, 
    draw_progress:       Optional[float]               = None,
    uniform_scale:       bool                          = False,
    closed:              bool                          = True,
    h_flip:              bool                          = False, 
    v_flip:              bool                          = False, 
    d_flip:              bool                          = False,
    phases:              Optional[Dict[str, Phase]]    = None,
    gradient:            Optional['GradientDef']       = None,
    gradient_p1:         P                             = P(),
    gradient_px1:        P                             = P(),
    gradient_p2:         P                             = P(),
    gradient_px2:        P                             = P(),
    visible_threshold_x: float                         = 0.0,
    visible_threshold_y: float                         = 0.0,
    phase_override:      Optional[Any]                 = None,
    pos_fn:              Optional[Callable[[], Union[P, List[P]]]] = None
) -> 'PolygonDef':
    def _split(offset):
        if offset is None:
            return P(), P()
        return offset[0], offset[1]

    tl_r, tl_p = _split(tl)
    tr_r, tr_p = _split(tr)
    br_r, br_p = _split(br)
    bl_r, bl_p = _split(bl)

    p  = [P(p1.x + tl_r.x, p1.y + tl_r.y), P(p2.x + tr_r.x, p1.y + tr_r.y), P(p2.x + br_r.x, p2.y + br_r.y), P(p1.x + bl_r.x, p2.y + bl_r.y)]
    px = [P(px1.x + tl_p.x, px1.y + tl_p.y), P(px2.x + tr_p.x, px1.y + tr_p.y), P(px2.x + br_p.x, px2.y + br_p.y), P(px1.x + bl_p.x, px2.y + bl_p.y)]

    return PolygonDef(
        p                   = p,
        px                  = px,
        fill_color          = fill_color    or QColor(0, 0, 0, 0),
        outline_color       = outline_color or QColor(0, 0, 0, 0),
        outline_width          = outline_width,
        draw_progress       = draw_progress,
        uniform_scale       = uniform_scale,
        closed              = closed,
        phases              = phases or {},
        h_flip              = h_flip,
        v_flip              = v_flip,
        d_flip              = d_flip,
        gradient            = gradient,
        gradient_p1         = gradient_p1,
        gradient_px1        = gradient_px1,
        gradient_p2         = gradient_p2,
        gradient_px2        = gradient_px2,
        visible_threshold_x = visible_threshold_x,
        visible_threshold_y = visible_threshold_y,
        phase_override      = phase_override,
        pos_fn              = pos_fn,
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
    outline_width:    Optional[float]       = None, 
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

    p  = [P(p1.x + tl_r.x, p1.y + tl_r.y), P(p2.x + tr_r.x, p1.y + tr_r.y), P(p2.x + br_r.x, p2.y + br_r.y), P(p1.x + bl_r.x, p2.y + bl_r.y)]
    px = [P(px1.x + tl_p.x, px1.y + tl_p.y), P(px2.x + tr_p.x, px1.y + tr_p.y), P(px2.x + br_p.x, px2.y + br_p.y), P(px1.x + bl_p.x, px2.y + bl_p.y)]

    return PolygonTween(
        p             = p,
        px            = px,
        fill_color    = fill_color,
        outline_color = outline_color,
        outline_width    = outline_width,
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
    p:                   List[P]                               = field(default_factory=lambda: [P(0, 0), P(0, 0)])
    px:                  Optional[List[P]]                     = None
    phases:              Optional[Dict[str, Phase]]            = None
    closed:              bool                                  = True
    outline_width:          float                                 = 0.0
    uniform_scale:       bool                                  = False
    fill_color:          Optional[QColor]                      = None
    outline_color:       Optional[QColor]                      = None
    draw_progress:       float                                 = 1.0
    h_flip:              bool                                  = False
    v_flip:              bool                                  = False
    d_flip:              bool                                  = False
    gradient:            Optional['GradientDef']               = None
    gradient_p1:         P                                     = P()
    gradient_px1:        P                                     = P()
    gradient_p2:         P                                     = P()
    gradient_px2:        P                                     = P()
    rot_center_p:        P                                     = field(default_factory=P)
    rot_center_px:       P                                     = field(default_factory=P)
    rot_target_p:        P                                     = field(default_factory=P)
    rot_target_px:       P                                     = field(default_factory=P)
    rot_angle_initial:   float                                 = 0.0
    rot_angle:           float                                 = 0.0
    dynamic_px:          Optional[Callable[[int,int],List[P]]] = None
    visible_threshold_x: float                                 = 0.0
    visible_threshold_y: float                                 = 0.0
    phase_override:      Optional[Any]                         = None
    pos_fn:              Optional[Callable[[], Union[P, List[P]]]] = None

@dataclass
class PolygonTween:
    # Properties
    p:                 Optional[List[P]]   = None
    px:                Optional[List[P]]   = None
    fill_color:        Optional[QColor]    = None
    outline_color:     Optional[QColor]    = None
    outline_width:        Optional[float]     = None
    draw_progress:     Optional[float]     = None
    _blend_anchor:     Optional[float]     = None
    gradient_p1:       Optional[P]         = None
    gradient_px1:      Optional[P]         = None
    gradient_p2:       Optional[P]         = None
    gradient_px2:      Optional[P]         = None
    rot_center_p:      Optional[P]         = None
    rot_center_px:     Optional[P]         = None
    rot_target_p:      Optional[P]         = None
    rot_target_px:     Optional[P]         = None
    rot_angle_initial: Optional[float]     = None
    rot_angle:         Optional[float]     = None
    # Tween Values
    span:              Tuple[float, float] = (0, 1)
    start:             float               = 0.0
    dur:               float               = 0.5
    ease:              QEasingCurve.Type   = QEasingCurve.OutQuint
    prev_phase:        Optional[str]       = None
    blend:             bool                = False

@dataclass
class GradientDef:
    name:        str
    stops:       List[GradientStop]
    phases:      Dict[str, Phase]   = field(default_factory=dict)
    p1:          P                  = field(default_factory=P)
    px1:         P                  = field(default_factory=P)
    p2:          P                  = field(default_factory=P)
    px2:         P                  = field(default_factory=P)
    radial:      bool               = False
    target:      str                = 'fill'
    phase_event: Optional[EventDef] = None

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
    p:                   P                              = field(default_factory=P)
    px:                  P                              = field(default_factory=P)
    text:                str                            = 'Sample Text'
    font_size:           float                          = 10.0
    fill_color:          QColor                         = QColor(255, 255, 255, 255)
    outline_color:       Optional[QColor]               = None
    outline_width:       float                          = 0.0
    gradient:            Optional['GradientDef']        = None
    gradient_p1:         P                              = field(default_factory=P)
    gradient_px1:        P                              = field(default_factory=P)
    gradient_p2:         P                              = field(default_factory=P)
    gradient_px2:        P                              = field(default_factory=P)
    rot_center_p:        P                              = field(default_factory=P)
    rot_center_px:       P                              = field(default_factory=P)
    rot_target_p:        P                              = field(default_factory=P)
    rot_target_px:       P                              = field(default_factory=P)
    rot_angle_initial:   float                          = 0.0
    rot_angle:           float                          = 0.0
    phases:              Optional[Dict[str, Phase]]     = None
    bold:                bool                           = False
    italic:              bool                           = False
    font_family:         str                            = 'Oxanium SemiBold'
    h_align:             float                          = 0.5
    v_align:             float                          = 0.5
    uniform_scale:       bool                           = True
    text_fn:             Optional[Callable[[Any], str]] = None
    char_display:        float                          = 1.0
    sub_char_clip:       bool                           = False
    backward:            bool                           = False
    phase_override:      Optional[Any]                  = None
    pos_fn:              Optional[Callable[[], P]]      = None
    visible_threshold_x: float                          = 0.0
    visible_threshold_y: float                          = 0.0

# ──────────────────────── Tween dataclasses ──────────────────────

@dataclass
class TextTween:
    # Properties
    p:                 Optional[P]         = None
    px:                Optional[P]         = None
    fill_color:        Optional[QColor]    = None
    outline_color:     Optional[QColor]    = None
    outline_width:     Optional[float]     = None
    gradient_p1:       Optional[P]         = None
    gradient_px1:      Optional[P]         = None
    gradient_p2:       Optional[P]         = None
    gradient_px2:      Optional[P]         = None
    h_align:           Optional[float]     = None
    v_align:           Optional[float]     = None
    font_size:         Optional[float]     = None
    char_display:      Optional[float]     = None
    rot_center_p:      Optional[P]         = None
    rot_center_px:     Optional[P]         = None
    rot_target_p:      Optional[P]         = None
    rot_target_px:     Optional[P]         = None
    rot_angle_initial: Optional[float]     = None
    rot_angle:         Optional[float]     = None
    # Tween Values
    span:              Tuple[float, float] = (0, 1)
    start:             float               = 0.0
    dur:               float               = 0.5
    ease:              QEasingCurve.Type   = QEasingCurve.OutQuint
    prev_phase:        Optional[str]       = None
    blend:             bool                = False

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
    p:           P                          = field(default_factory=P),
    px:          P                          = field(default_factory=P),
    text:        str                        = 'Sample Text',
    font_size:   float                      = 10.0,
    fill_color:  QColor                     = QColor(255, 255, 255, 255),
    phases:      Optional[Dict[str, Phase]] = None,
    bold:        bool                       = False,
    italic:      bool                       = False,
    font_family: str                        = '',
    h_align:     float                      = 0.0,
    v_align:     float                      = 0.0,
    uniform_scale: bool                     = True,
    text_fn:     Optional[Callable]         = None,
    line_offset: Optional[float]            = None,
    pos_fn:      Optional[Callable[[], P]]  = None,
) -> List['TextDef']:

    lines = text.split('\n')
    n     = len(lines)

    effective_line_offset = font_size if line_offset is None else line_offset

    if n == 1:
        return [TextDef(
            p=p, px=px, text=text, font_size=font_size, fill_color=fill_color,
            phases=phases, bold=bold, italic=italic,
            font_family=font_family, h_align=h_align, v_align=v_align,
            uniform_scale=uniform_scale,
            text_fn=text_fn, pos_fn=pos_fn,
        )]

    result: List[TextDef] = []

    for i, line_text in enumerate(lines):
        line_px = P(px.x, px.y + effective_line_offset * i)
        adjusted_phases: Optional[Dict[str, Phase]] = None
        if phases:
            adjusted_phases = {}
            for phase_name, phase in phases.items():
                new_tweens = []
                for tw in phase.tweens:
                    if isinstance(tw, TextTween):
                        new_tweens.append(TextTween(
                            p          = tw.p,
                            px         = P(tw.px.x, tw.px.y + effective_line_offset * i) if tw.px is not None else None,
                            start      = tw.start,
                            dur        = tw.dur,
                            ease       = tw.ease,
                            fill_color = tw.fill_color,
                            h_align    = tw.h_align,
                            v_align    = tw.v_align,
                            font_size  = tw.font_size,
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
            p             = p,
            px            = line_px,
            text          = resolved_text,
            font_size     = font_size,
            fill_color    = fill_color,
            phases        = adjusted_phases,
            bold          = bold,
            italic        = italic,
            font_family   = font_family,
            h_align       = h_align,
            v_align       = v_align,
            uniform_scale = uniform_scale,
            text_fn       = resolved_text_fn,
            pos_fn        = pos_fn,
        ))

    return result

def DataTable(
    x:              float,
    y:              float,
    px:             float                    = 0.0,
    py:             float                    = 0.0,
    value_x:        float                    = 0.5,
    value_px:       float                    = 0.0,
    row_height:     float                    = 18.0,
    values:         List[Tuple]              = None,
    unit_gap:       float                    = 4.0,
    fill_color:     QColor                   = None,
    font_size:      float                    = 10.0,
    font_family:    str                      = 'Oxanium SemiBold',
    bold:           bool                     = False,
    italic:         bool                     = False,
    uniform_scale:  bool                     = True,
    phases:         Dict[str, Phase]         = None,
    char_display:   float                    = 1.0,
    sub_char_clip:  bool                     = False,
    backward:       bool                     = False,
    title:          str                      = '',
    title_font_size: float                   = 12.0,
) -> List[TextDef]:
    values = values or []
    n      = len(values)

    names       = []
    raw_values  = []
    value_units = []
    formats     = []
    for entry in values:
        if isinstance(entry, tuple):
            name = entry[0]
            val  = entry[1] if len(entry) > 1 else ''
            unit = entry[2] if len(entry) > 2 else ''
            fmt  = entry[3] if len(entry) > 3 else None
        else:
            raise ValueError("DataTable: each entry must be a tuple (name, value, unit='', format=None)")
        names.append(name)
        raw_values.append(val)
        value_units.append(unit)
        formats.append(fmt)

    col = fill_color or QColor(255, 255, 255, 200)
    ph  = phases or {}
    result: List[TextDef] = []

    if title:
        title_phases = {}
        for phase_name, phase in ph.items():
            delay = phase.line_delay * 0
            title_phases[phase_name] = Phase(
                [_tw_replace(tw, start=tw.start + delay) if isinstance(tw, TextTween) else tw
                 for tw in phase.tweens],
                line_delay  = 0.0,
                loop        = phase.loop,
                stop_phases = phase.stop_phases,
            )
        result.append(TextDef(
            x             = x,
            y             = y,
            px            = px,
            py            = py,
            text          = title,
            font_size     = title_font_size,
            fill_color    = QColor(col),
            phases        = title_phases,
            bold          = True,
            italic        = True,
            font_family   = font_family,
            h_align       = 0.0,
            v_align       = 1.0,
            uniform_scale = uniform_scale,
            char_display  = char_display,
            sub_char_clip = sub_char_clip,
            backward      = backward,
        ))

    title_offset = 1 if title else 0

    for i in range(n):
        row_py = py + row_height * i
        row_phases: Dict[str, Phase] = {}
        for phase_name, phase in ph.items():
            delay = phase.line_delay * (i + title_offset)
            if delay == 0.0:
                row_phases[phase_name] = phase
            else:
                row_phases[phase_name] = Phase(
                    [_tw_replace(tw, start=tw.start + delay) if isinstance(tw, TextTween) else tw
                     for tw in phase.tweens],
                    line_delay  = 0.0,
                    loop        = phase.loop,
                    stop_phases = phase.stop_phases,
                )

        common = dict(
            font_size     = font_size,
            fill_color    = QColor(col),
            phases        = row_phases,
            bold          = bold,
            italic        = italic,
            font_family   = font_family,
            uniform_scale = uniform_scale,
            char_display  = char_display,
            sub_char_clip = sub_char_clip,
            backward      = backward,
        )

        result.append(TextDef(x=x, y=y, px=px, py=row_py,
            text=names[i], h_align=0.0, v_align=0.0, **common))

        raw_value = raw_values[i]
        fmt_spec  = formats[i]
        unit      = value_units[i]

        if callable(raw_value):
            def _make_value_fn(fn, spec):
                def _fn(ctx):
                    try:    v = fn(ctx)
                    except: v = None
                    if v is None: return '-'
                    try:    return format(v, spec) if spec else str(v)
                    except: return str(v)
                return _fn
            value_text_fn = _make_value_fn(raw_value, fmt_spec)
            value_text    = ''
        else:
            value_text_fn = None
            try:    value_text = format(raw_value, fmt_spec) if fmt_spec else str(raw_value)
            except: value_text = str(raw_value)

        result.append(TextDef(x=value_x, y=y, px=value_px, py=row_py,
            text=value_text, text_fn=value_text_fn,
            h_align=1.0, v_align=0.0, **common))

        result.append(TextDef(x=value_x, y=y, px=value_px + unit_gap, py=row_py,
            text=unit, h_align=0.0, v_align=0.0, **common))

    return result

# ──────────────────────── _TweenDriver ───────────────────────────

class _TweenDriver:
    def __init__(self):
        self.hidden          = False
        self._phase: str     = ''
        self._phase_groups: Dict[str, str] = {}
        self._prev:  str     = ''
        self._idx:   int     = 0
        self._tweens: list   = []
        self._timer          = QElapsedTimer()

    def _active_tweens(self, phase, prev, phases: dict) -> list:
        if phase in phases:
            p = phases[phase]
            return [tw for tw in p.tweens if tw.prev_phase is None or tw.prev_phase == prev]
        for key, p in phases.items():
            if isinstance(key, tuple) and phase in key:
                return [tw for tw in p.tweens if tw.prev_phase is None or tw.prev_phase == prev]
        return []

    @property
    def _cur(self): return self._tweens[self._idx] if self._idx < len(self._tweens) else None

    def set_phase(self, phase: str, phases: dict):
        if not phases:
            self.hidden = False
            return
        resolved_phases = {}
        phase_groups = {}
        for key, val in phases.items():
            if isinstance(key, tuple):
                canonical = key[0]
                for k in key:
                    phase_groups[k] = canonical
                    resolved_phases[canonical] = val
            else:
                phase_groups[key] = key
                resolved_phases[key] = val
        canonical = phase_groups.get(phase, phase)
        cur_canonical = phase_groups.get(self._phase, self._phase)

        if canonical not in resolved_phases:
            return

        if canonical == cur_canonical and self._phase != '' and canonical != 'pulse':
            return

        self._prev  = self._phase
        self._phase = phase
        self._idx   = 0
        self._tweens = self._active_tweens(canonical, self._prev, resolved_phases)
        if self._tweens or canonical in resolved_phases:
            self.hidden = False
        while self._idx < len(self._tweens) and isinstance(self._tweens[self._idx], Reset):
            self._reset_to_def()
            self._idx += 1
        self._save_start()
        self._timer.restart()

    def _is_done(self): return self._idx >= len(self._tweens)
    def phase_done(self): return self._is_done()

    def _drive(self):
        if self.hidden:
            return
        if self._idx >= len(self._tweens):
            return

        elapsed = self._timer.elapsed() / 1000.0
        tweens = self._tweens
        n = len(tweens)

        if n > 0 and elapsed < tweens[self._idx].start if not isinstance(tweens[self._idx], Reset) else False:
            return

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
            if curve == QEasingCurve.InCirc:    return _math.sqrt(1.0 - (1.0 - y*y))
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
            if len(group) == 1 and getattr(tw, 'span', (0,1)) == (0,1) and not getattr(tw, 'blend', False):
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

            if elapsed < group_start:
                return

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
                if elapsed >= eff_start:
                    self._apply(base, v)
                for btw in group[1:]:
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

    def _save_start(self): pass
    def _snap_to(self, tw): pass
    def _reset_to_def(self): pass
    def _apply(self, tw, v): pass

_ALWAYS_PHASE_ORIGINS: Dict[str, float] = {}

class _AlwaysDriver:
    def __init__(self, phase_name: str, phase: Phase, n_p: int) -> None:
        self._phase_name = phase_name
        self._phase      = phase
        self._n          = n_p
        self._stopped    = False
        self._started    = False
 
        self.offset_p:             List[P]          = [P(0.0, 0.0)] * n_p
        self.offset_px:            List[P]          = [P(0.0, 0.0)] * n_p
        self.offset_fill_color:    Optional[QColor] = None
        self.offset_outline_color: Optional[QColor] = None
 
        self._s_pts:     List[P]          = [P(0.0, 0.0)] * n_p
        self._s_px:      List[P]          = [P(0.0, 0.0)] * n_p
        self._s_fill:    Optional[QColor] = None
        self._s_outline: Optional[QColor] = None
 
        self._idx:      int   = 0
        self._loop_origin: float = 0.0

        self._stop_phases_set: set = set()
        for entry in self._phase.stop_phases:
            if isinstance(entry, tuple):
                self._stop_phases_set.update(entry)
            else:
                self._stop_phases_set.add(entry)
 
    def _global_origin(self) -> float:
        if self._phase_name not in _ALWAYS_PHASE_ORIGINS:
            _ALWAYS_PHASE_ORIGINS[self._phase_name] = time.monotonic()
        return _ALWAYS_PHASE_ORIGINS[self._phase_name]
 
    def _elapsed(self) -> float:
        return time.monotonic() - self._loop_origin
 
    def _reset(self) -> None:
        self._stopped = False
        self._idx     = 0
        self.offset_p             = [P(0.0, 0.0)] * self._n
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
        self.offset_p             = [P(0.0, 0.0)] * self._n
        self.offset_px            = [P(0.0, 0.0)] * self._n
        self.offset_fill_color    = None
        self.offset_outline_color = None
        self._s_pts     = [P(0.0, 0.0)] * self._n
        self._s_px      = [P(0.0, 0.0)] * self._n
        self._s_fill    = None
        self._s_outline = None
 
    def _snap_tw(self, tw) -> None:
        if isinstance(tw, PolygonTween):
            if tw.p             is not None: self.offset_p = [P(p.x, p.y) for p in tw.p]
            if tw.px            is not None: self.offset_px = [P(p.x, p.y) for p in tw.px]
            if tw.fill_color    is not None: self.offset_fill_color    = QColor(tw.fill_color)
            if tw.outline_color is not None: self.offset_outline_color = QColor(tw.outline_color)
        elif isinstance(tw, TextTween):
            if tw.x          is not None: self.offset_p = [P(tw.x, self.offset_p[0].y)]
            if tw.y          is not None: self.offset_p = [P(self.offset_p[0].x, tw.y)]
            if tw.px         is not None: self.offset_px = [P(tw.px, self.offset_px[0].y)]
            if tw.py         is not None: self.offset_px = [P(self.offset_px[0].x, tw.py)]
            if tw.fill_color is not None: self.offset_fill_color = QColor(tw.fill_color)
 
    def _save_start(self) -> None:
        self._s_pts     = [P(p.x, p.y) for p in self.offset_p]
        self._s_px      = [P(p.x, p.y) for p in self.offset_px]
        self._s_fill    = QColor(self.offset_fill_color) if self.offset_fill_color    else None
        self._s_outline = QColor(self.offset_outline_color) if self.offset_outline_color else None
 
    def notify_phase(self, phase_name: str, base_phase_done: bool) -> None:
        in_stop = phase_name in self._stop_phases_set
        if in_stop and base_phase_done:
            if not self._stopped:
                self._stopped = True
                self._do_reset_offsets()
        elif not in_stop and not self._started:
            self._reset()
        elif not in_stop and self._stopped:
            self._stopped = False
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
            self._s_pts = [P(0.0, 0.0)] * self._n
            self._s_px = [P(0.0, 0.0)] * self._n
            self._s_fill = None
            self._s_outline = None
 
    def _apply_tw(self, tw, v: float) -> None:
        if isinstance(tw, PolygonTween):
            if tw.p is not None:
                for j, (sp, tp) in enumerate(zip(self._s_pts, tw.p)):
                    self.offset_p[j] = P(sp.x + (tp.x - sp.x) * v, sp.y + (tp.y - sp.y) * v)
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

            if tw.x  is not None: self.offset_p  = [P(new_x, self.offset_p[0].y)]
            if tw.y  is not None: self.offset_p  = [P(self.offset_p[0].x, new_y)]
            if tw.px is not None: self.offset_px = [P(new_px, self.offset_px[0].y)]
            if tw.py is not None: self.offset_px = [P(self.offset_px[0].x, new_py)]

            if tw.fill_color is not None:
                src = self._s_fill or QColor(0, 0, 0, 0)
                self.offset_fill_color = lerp_color(src, tw.fill_color, v)

 

class _AnimatedGradient(_TweenDriver):
    def __init__(self, defn: GradientDef) -> None:
        super().__init__()
        self.defn      = defn
        self.cur_stops = [GradientStop(s.position, QColor(s.color)) for s in defn.stops]
        self._s_stops  = [GradientStop(s.position, QColor(s.color)) for s in defn.stops]
        self._cur_phase: str = ''

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
 
    def _poll_phase_event(self) -> None:
        ev = self.defn.phase_event
        if ev is None:
            return
        val = str(ev.value) if ev.value is not None else ''
        if val and val != self._cur_phase:
            self._cur_phase = val
            self.set_phase(val)

    def update(self) -> None:
        self._poll_phase_event()
        self._drive()
 
    def build_gradient(self, x1: float, y1: float, x2: float, y2: float, radial: bool = False):
        if radial:
            cx, cy   = x1, y1
            ex, ey   = x2, y2
            radius   = _math.sqrt((ex - cx) ** 2 + (ey - cy) ** 2)
            g = QRadialGradient(cx, cy, radius)
            g.setSpread(QRadialGradient.PadSpread)
        else:
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
        n = len(defn.p)
        _zero_px = [P() for _ in range(n)]

        self._screen_offset = P(0.0, 0.0)
        self.cur_p            = [P(p.x, p.y) for p in defn.p]
        self.cur_px           = [P(p.x, p.y) for p in (defn.px or _zero_px)]
        self.cur_fill_color   = QColor(defn.fill_color)   if defn.fill_color   else QColor(0,0,0,0)
        self.cur_outline_color= QColor(defn.outline_color)if defn.outline_color else QColor(0,0,0,0)
        self.cur_line_width   = defn.outline_width
        self.cur_draw_progress= defn.draw_progress
        self.cur_gradient_p1  = P(defn.gradient_p1.x,  defn.gradient_p1.y)
        self.cur_gradient_px1 = P(defn.gradient_px1.x, defn.gradient_px1.y)
        self.cur_gradient_p2  = P(defn.gradient_p2.x,  defn.gradient_p2.y)
        self.cur_gradient_px2 = P(defn.gradient_px2.x, defn.gradient_px2.y)

        self._sp  = [P(p.x, p.y) for p in self.cur_p]
        self._spx = [P(p.x, p.y) for p in self.cur_px]
        self._sf  = QColor(self.cur_fill_color)
        self._so  = QColor(self.cur_outline_color)
        self._slw = self.cur_line_width
        self._sdp = self.cur_draw_progress
        self._sgp1  = P(defn.gradient_p1.x,  defn.gradient_p1.y)
        self._sgpx1 = P(defn.gradient_px1.x, defn.gradient_px1.y)
        self._sgp2  = P(defn.gradient_p2.x,  defn.gradient_p2.y)
        self._sgpx2 = P(defn.gradient_px2.x, defn.gradient_px2.y)

        self.cur_rot_center_p:      P     = P(defn.rot_center_p.x,  defn.rot_center_p.y)
        self.cur_rot_center_px:     P     = P(defn.rot_center_px.x, defn.rot_center_px.y)
        self.cur_rot_target_p:      P     = P(defn.rot_target_p.x,  defn.rot_target_p.y)
        self.cur_rot_target_px:     P     = P(defn.rot_target_px.x, defn.rot_target_px.y)
        self.cur_rot_angle_initial: float = defn.rot_angle_initial
        self.cur_rot_angle:         float = defn.rot_angle

        self._s_rot_center_p:      P     = P(defn.rot_center_p.x,  defn.rot_center_p.y)
        self._s_rot_center_px:     P     = P(defn.rot_center_px.x, defn.rot_center_px.y)
        self._s_rot_target_p:      P     = P(defn.rot_target_p.x,  defn.rot_target_p.y)
        self._s_rot_target_px:     P     = P(defn.rot_target_px.x, defn.rot_target_px.y)
        self._s_rot_angle_initial: float = defn.rot_angle_initial
        self._s_rot_angle:         float = defn.rot_angle

        self._dirty      = True
        self._cached_poly= QPolygonF()
        self._cached_w   = 0
        self._cached_h   = 0
        self._always_drivers: Dict[str, _AlwaysDriver] = {
            name: _AlwaysDriver(name, phase, len(defn.p))
            for name, phase in (defn.phases or {}).items()
            if _phase_key_name(name).startswith('always')
        }
        self._always_offset_p:      List[P] = [P(0.0, 0.0)] * len(defn.p)
        self._always_offset_px:     List[P] = [P(0.0, 0.0)] * len(defn.p)
        self._always_fill_color:    Optional[QColor] = None
        self._always_outline_color: Optional[QColor] = None
        
        self._dynamic_px_w: int = 0
        self._dynamic_px_h: int = 0
        self._pos_offset: List[P] = [P(0.0, 0.0)] * len(defn.p)


    # ── _TweenDriver hooks ───────────────────────────────────────

    def _save_start(self):
        self._sp  = [P(p.x, p.y) for p in self.cur_p]
        self._spx = [P(p.x, p.y) for p in self.cur_px]
        self._sf  = QColor(self.cur_fill_color)
        self._so  = QColor(self.cur_outline_color)
        self._slw = self.cur_line_width
        self._sdp = self.cur_draw_progress
        self._sgp1  = P(self.cur_gradient_p1.x,  self.cur_gradient_p1.y)
        self._sgpx1 = P(self.cur_gradient_px1.x, self.cur_gradient_px1.y)
        self._sgp2  = P(self.cur_gradient_p2.x,  self.cur_gradient_p2.y)
        self._sgpx2 = P(self.cur_gradient_px2.x, self.cur_gradient_px2.y)
        self._s_rot_center_p      = P(self.cur_rot_center_p.x,  self.cur_rot_center_p.y)
        self._s_rot_center_px     = P(self.cur_rot_center_px.x, self.cur_rot_center_px.y)
        self._s_rot_target_p      = P(self.cur_rot_target_p.x,  self.cur_rot_target_p.y)
        self._s_rot_target_px     = P(self.cur_rot_target_px.x, self.cur_rot_target_px.y)
        self._s_rot_angle_initial = self.cur_rot_angle_initial
        self._s_rot_angle         = self.cur_rot_angle

    def _apply(self, tw: PolygonTween, v: float):
        if tw.p is not None:
            for i, (sp, tp) in enumerate(zip(self._sp, tw.p)):
                nx = sp.x + (tp.x - sp.x) * v if tp.x is not None else sp.x
                ny = sp.y + (tp.y - sp.y) * v if tp.y is not None else sp.y
                self.cur_p[i] = P(nx, ny)
        if tw.px is not None:
            for i, (spx, tpx) in enumerate(zip(self._spx, tw.px)):
                nx = spx.x + (tpx.x - spx.x) * v if tpx.x is not None else spx.x
                ny = spx.y + (tpx.y - spx.y) * v if tpx.y is not None else spx.y
                self.cur_px[i] = P(nx, ny)
        if tw.fill_color    is not None: self.cur_fill_color    = lerp_color(self._sf, tw.fill_color,    v)
        if tw.outline_color is not None: self.cur_outline_color = lerp_color(self._so, tw.outline_color, v)
        if tw.outline_width    is not None: self.cur_line_width    = self._slw + (tw.outline_width - self._slw) * v
        if tw.draw_progress is not None: self.cur_draw_progress = self._sdp + (tw.draw_progress - self._sdp) * v
        if tw.gradient_p1   is not None: self.cur_gradient_p1   = P(self._sgp1.x  + (tw.gradient_p1.x  - self._sgp1.x)  * v, self._sgp1.y  + (tw.gradient_p1.y  - self._sgp1.y)  * v)
        if tw.gradient_px1  is not None: self.cur_gradient_px1  = P(self._sgpx1.x + (tw.gradient_px1.x - self._sgpx1.x) * v, self._sgpx1.y + (tw.gradient_px1.y - self._sgpx1.y) * v)
        if tw.gradient_p2   is not None: self.cur_gradient_p2   = P(self._sgp2.x  + (tw.gradient_p2.x  - self._sgp2.x)  * v, self._sgp2.y  + (tw.gradient_p2.y  - self._sgp2.y)  * v)
        if tw.gradient_px2  is not None: self.cur_gradient_px2  = P(self._sgpx2.x + (tw.gradient_px2.x - self._sgpx2.x) * v, self._sgpx2.y + (tw.gradient_px2.y - self._sgpx2.y) * v)
        if tw.rot_center_p      is not None: self.cur_rot_center_p      = P(self._s_rot_center_p.x  + (tw.rot_center_p.x  - self._s_rot_center_p.x)  * v, self._s_rot_center_p.y  + (tw.rot_center_p.y  - self._s_rot_center_p.y)  * v)
        if tw.rot_center_px     is not None: self.cur_rot_center_px     = P(self._s_rot_center_px.x + (tw.rot_center_px.x - self._s_rot_center_px.x) * v, self._s_rot_center_px.y + (tw.rot_center_px.y - self._s_rot_center_px.y) * v)
        if tw.rot_target_p      is not None: self.cur_rot_target_p      = P(self._s_rot_target_p.x  + (tw.rot_target_p.x  - self._s_rot_target_p.x)  * v, self._s_rot_target_p.y  + (tw.rot_target_p.y  - self._s_rot_target_p.y)  * v)
        if tw.rot_target_px     is not None: self.cur_rot_target_px     = P(self._s_rot_target_px.x + (tw.rot_target_px.x - self._s_rot_target_px.x) * v, self._s_rot_target_px.y + (tw.rot_target_px.y - self._s_rot_target_px.y) * v)
        if tw.rot_angle_initial is not None: self.cur_rot_angle_initial = self._s_rot_angle_initial + (tw.rot_angle_initial - self._s_rot_angle_initial) * v
        if tw.rot_angle         is not None: self.cur_rot_angle         = self._s_rot_angle         + (tw.rot_angle         - self._s_rot_angle)         * v
        self._dirty = True

    def _apply_blend(self, tw: PolygonTween, v: float):
        if tw.p is not None:
            for i, tp in enumerate(tw.p):
                cp = self.cur_p[i]
                self.cur_p[i] = P(cp.x + tp.x * v, cp.y + tp.y * v)
        if tw.px is not None:
            for i, tpx in enumerate(tw.px):
                cpx = self.cur_px[i]
                self.cur_px[i] = P(cpx.x + tpx.x * v, cpx.y + tpx.y * v)
        if tw.fill_color    is not None: self.cur_fill_color    = lerp_color(self.cur_fill_color,    tw.fill_color,    v)
        if tw.outline_color is not None: self.cur_outline_color = lerp_color(self.cur_outline_color, tw.outline_color, v)
        if tw.outline_width    is not None: self.cur_line_width    = self.cur_line_width + (tw.outline_width - self.cur_line_width) * v
        if tw.draw_progress is not None: self.cur_draw_progress = self.cur_draw_progress + (tw.draw_progress - self.cur_draw_progress) * v
        self._dirty = True

    def _snap_to(self, tw: PolygonTween):
        if tw.p             is not None: self.cur_p             = [P(tp.x if tp.x is not None else cp.x, tp.y if tp.y is not None else cp.y) for cp, tp in zip(self.cur_p, tw.p)]
        if tw.px            is not None: self.cur_px            = [P(tpx.x if tpx.x is not None else cpx.x, tpx.y if tpx.y is not None else cpx.y) for cpx, tpx in zip(self.cur_px, tw.px)]
        if tw.fill_color    is not None: self.cur_fill_color    = QColor(tw.fill_color)
        if tw.outline_color is not None: self.cur_outline_color = QColor(tw.outline_color)
        if tw.outline_width    is not None: self.cur_line_width    = tw.outline_width
        if tw.draw_progress is not None: self.cur_draw_progress = tw.draw_progress
        if tw.gradient_p1   is not None: self.cur_gradient_p1   = tw.gradient_p1
        if tw.gradient_px1  is not None: self.cur_gradient_px1  = tw.gradient_px1
        if tw.gradient_p2   is not None: self.cur_gradient_p2   = tw.gradient_p2
        if tw.gradient_px2  is not None: self.cur_gradient_px2  = tw.gradient_px2
        if tw.rot_center_p      is not None: self.cur_rot_center_p      = tw.rot_center_p
        if tw.rot_center_px     is not None: self.cur_rot_center_px     = tw.rot_center_px
        if tw.rot_target_p      is not None: self.cur_rot_target_p      = tw.rot_target_p
        if tw.rot_target_px     is not None: self.cur_rot_target_px     = tw.rot_target_px
        if tw.rot_angle_initial is not None: self.cur_rot_angle_initial = tw.rot_angle_initial
        if tw.rot_angle         is not None: self.cur_rot_angle         = tw.rot_angle
        self._dirty = True

    def _reset_to_def(self):
        d = self.defn
        n = len(d.p)
        self.cur_p             = [P(p.x, p.y) for p in d.p]
        self.cur_px            = [P(p.x, p.y) for p in (d.px or [P()]*n)]
        self.cur_fill_color    = QColor(d.fill_color)    if d.fill_color    else QColor(0,0,0,0)
        self.cur_outline_color = QColor(d.outline_color) if d.outline_color else QColor(0,0,0,0)
        self.cur_line_width    = d.outline_width
        self.cur_draw_progress = d.draw_progress
        self.cur_gradient_p1  = P(d.gradient_p1.x,  d.gradient_p1.y)
        self.cur_gradient_px1 = P(d.gradient_px1.x, d.gradient_px1.y)
        self.cur_gradient_p2  = P(d.gradient_p2.x,  d.gradient_p2.y)
        self.cur_gradient_px2 = P(d.gradient_px2.x, d.gradient_px2.y)
        self.cur_rot_center_p      = P(d.rot_center_p.x,  d.rot_center_p.y)
        self.cur_rot_center_px     = P(d.rot_center_px.x, d.rot_center_px.y)
        self.cur_rot_target_p      = P(d.rot_target_p.x,  d.rot_target_p.y)
        self.cur_rot_target_px     = P(d.rot_target_px.x, d.rot_target_px.y)
        self.cur_rot_angle_initial = d.rot_angle_initial
        self.cur_rot_angle         = d.rot_angle
        self._dirty = True

    def set_phase(self, phase: str):
        super().set_phase(phase, self.defn.phases)
        self._dirty = True
        for driver in self._always_drivers.values():
            driver.notify_phase(phase, False)

    def update(self) -> None:
        pos_fn = self.defn.pos_fn
        if pos_fn is not None:
            try:
                result = pos_fn()
                if result is not None:
                    n = len(self.defn.p)
                    if isinstance(result, P):
                        self._pos_offset = [result] * n
                    else:
                        self._pos_offset = result
                    self._dirty = True
            except Exception:
                pass
        self._drive()

        n = len(self.defn.p)
        sum_pts = [P(0.0, 0.0)] * n
        sum_px  = [P(0.0, 0.0)] * n
        fill_override    = None
        outline_override = None
 
        base_done = self.phase_done()
 
        for driver in self._always_drivers.values():
            driver.update(self._phase, base_done)
 
            for j in range(n):
                op = driver.offset_p[j]
                ox = driver.offset_px[j]
                sum_pts[j] = P(sum_pts[j].x + op.x, sum_pts[j].y + op.y)
                sum_px[j]  = P(sum_px[j].x  + ox.x, sum_px[j].y  + ox.y)
 
            if driver.offset_fill_color is not None:
                fill_override = driver.offset_fill_color
            if driver.offset_outline_color is not None:
                outline_override = driver.offset_outline_color
 
        self._always_offset_p      = sum_pts
        self._always_offset_px     = sum_px
        self._always_fill_color    = fill_override
        self._always_outline_color = outline_override
 
        if any(p.x != 0 or p.y != 0 for p in sum_pts + sum_px):
            self._dirty = True

    def phase_done(self) -> bool:
        return self._is_done()

    # ── Geometry ─────────────────────────────────────────────────

    def _to_screen_pts(self, w: int, h: int, cam_w=MONITOR_RESOLUTIONS[0][0], cam_h=MONITOR_RESOLUTIONS[0][1]) -> List[QPointF]:
        pts = []
        for p, px in zip(self.cur_p, self.cur_px):
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

    def get_polygon(self, widget_w: int, widget_h: int, cam_w: int = MONITOR_RESOLUTIONS[0][0], cam_h: int = MONITOR_RESOLUTIONS[0][1]) -> QPolygonF:
        dynamic_px = self.defn.dynamic_px
        if dynamic_px is not None:
            if widget_w != self._dynamic_px_w or widget_h != self._dynamic_px_h:
                self.cur_px        = dynamic_px(widget_w, widget_h)
                self._spx          = list(self.cur_px)
                self._dynamic_px_w = widget_w
                self._dynamic_px_h = widget_h
                self._dirty        = True

        always_pts = self._always_offset_p
        always_px  = self._always_offset_px
        pos        = self._pos_offset
        has_always = False
        for p in always_pts:
            if p.x or p.y:
                has_always = True
                break
        if not has_always:
            for p in always_px:
                if p.x or p.y:
                    has_always = True
                    break
        has_pos = False
        for p in pos:
            if p.x or p.y:
                has_pos = True
                break

        if not self._dirty and self._cached_w == widget_w and self._cached_h == widget_h:
            if not has_always and not has_pos:
                return self._cached_poly
            pts = []
            if self.defn.uniform_scale:
                s  = min(widget_w / cam_w, widget_h / cam_h)
                cx = s / (widget_w / cam_w)
                cy = s / (widget_h / cam_h)
                for j, qp in enumerate(self._cached_poly):
                    ap  = always_pts[j]
                    apx = always_px[j]
                    po  = pos[j]
                    pts.append(QPointF(qp.x() + ap.x * cx * widget_w + apx.x + po.x,
                                       qp.y() + ap.y * cy * widget_h + apx.y + po.y))
            else:
                for j, qp in enumerate(self._cached_poly):
                    ap  = always_pts[j]
                    apx = always_px[j]
                    po  = pos[j]
                    pts.append(QPointF(qp.x() + ap.x * widget_w + apx.x + po.x,
                                       qp.y() + ap.y * widget_h + apx.y + po.y))
            return QPolygonF(pts)

        pts      = []
        base_pts = []
        if self.defn.uniform_scale:
            s  = min(widget_w / cam_w, widget_h / cam_h)
            cx = s / (widget_w / cam_w)
            cy = s / (widget_h / cam_h)
            for j, (p, px) in enumerate(zip(self.cur_p, self.cur_px)):
                ap  = always_pts[j]
                apx = always_px[j]
                po  = pos[j]
                sx  = (0.5 + (p.x - 0.5) * cx) * widget_w + px.x + po.x
                sy  = (0.5 + (p.y - 0.5) * cy) * widget_h + px.y + po.y
                pts.append(QPointF(sx + ap.x * cx * widget_w + apx.x,
                                   sy + ap.y * cy * widget_h + apx.y))
                base_pts.append(QPointF(sx, sy))
        else:
            for j, (p, px) in enumerate(zip(self.cur_p, self.cur_px)):
                ap  = always_pts[j]
                apx = always_px[j]
                po  = pos[j]
                sx  = p.x * widget_w + px.x + po.x
                sy  = p.y * widget_h + px.y + po.y
                pts.append(QPointF(sx + ap.x * widget_w + apx.x,
                                   sy + ap.y * widget_h + apx.y))
                base_pts.append(QPointF(sx, sy))

        self._cached_poly = QPolygonF(base_pts)
        self._cached_w    = widget_w
        self._cached_h    = widget_h
        self._dirty       = False
        return QPolygonF(pts)

    # ── Draw ─────────────────────────────────────────────────────
    
    def draw(self, painter: QPainter, w: int, h: int, cam_w: int = MONITOR_RESOLUTIONS[0][0], cam_h: int = MONITOR_RESOLUTIONS[0][1]):
        if self.hidden:
            return

        effective_fill    = self._always_fill_color    if self._always_fill_color    is not None else self.cur_fill_color
        effective_outline = self._always_outline_color if self._always_outline_color is not None else self.cur_outline_color
        lw         = self.cur_line_width
        has_fill    = self.defn.closed and (effective_fill.alpha() > 0 or self.defn.gradient is not None)
        gd = self.defn.gradient
        has_gradient_outline = gd is not None and gd.target == 'outline'
        has_outline = lw > 0 and (effective_outline.alpha() > 0 or has_gradient_outline)
        is_open     = not self.defn.closed

        if not has_fill and not has_outline:
            return

        rot = _resolve_rotation(
            self.cur_rot_center_p, self.cur_rot_center_px,
            self.cur_rot_target_p, self.cur_rot_target_px,
            self.cur_rot_angle_initial, self.cur_rot_angle,
            w, h
        )
        if rot is not None:
            cx, cy, angle = rot
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(angle)
            painter.translate(-cx, -cy)

        pts = list(self.get_polygon(w, h, cam_w, cam_h))

        if is_open:
            if not has_outline:
                if rot is not None: painter.restore()
                return
            pen = QPen(self.cur_outline_color)
            pen.setWidthF(lw)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            _draw_partial_polyline(painter, pts, self.cur_draw_progress)
            painter.setPen(Qt.NoPen)
            if rot is not None: painter.restore()
            return

        def _fill_brush():
            fill = (self._always_fill_color if self._always_fill_color is not None else self.cur_fill_color)
            gd = self.defn.gradient
            if gd is None:
                return fill
            def _has_point(p, px):
                return p.x != 0 or p.y != 0 or px.x != 0 or px.y != 0
            if _has_point(self.cur_gradient_p1, self.cur_gradient_px1) or _has_point(self.cur_gradient_p2, self.cur_gradient_px2):
                x1 = self.cur_gradient_p1.x  * w + self.cur_gradient_px1.x
                y1 = self.cur_gradient_p1.y  * h + self.cur_gradient_px1.y
                x2 = self.cur_gradient_p2.x  * w + self.cur_gradient_px2.x
                y2 = self.cur_gradient_p2.y  * h + self.cur_gradient_px2.y
            else:
                x1 = gd.p1.x  * w + gd.px1.x
                y1 = gd.p1.y  * h + gd.px1.y
                x2 = gd.p2.x  * w + gd.px2.x
                y2 = gd.p2.y  * h + gd.px2.y
            return gd._animated.build_gradient(x1, y1, x2, y2, radial=gd.radial)
        
        def _outline_brush():
            gd = self.defn.gradient
            if gd is not None and gd.target == 'outline':
                def _has_point(p, px):
                    return p.x != 0 or p.y != 0 or px.x != 0 or px.y != 0
                if _has_point(self.cur_gradient_p1, self.cur_gradient_px1) or _has_point(self.cur_gradient_p2, self.cur_gradient_px2):
                    x1 = self.cur_gradient_p1.x * w + self.cur_gradient_px1.x
                    y1 = self.cur_gradient_p1.y * h + self.cur_gradient_px1.y
                    x2 = self.cur_gradient_p2.x * w + self.cur_gradient_px2.x
                    y2 = self.cur_gradient_p2.y * h + self.cur_gradient_px2.y
                else:
                    x1 = gd.p1.x * w + gd.px1.x
                    y1 = gd.p1.y * h + gd.px1.y
                    x2 = gd.p2.x * w + gd.px2.x
                    y2 = gd.p2.y * h + gd.px2.y
                return gd._animated.build_gradient(x1, y1, x2, y2, radial=gd.radial)
            return None

        gradient_outline = _outline_brush()
        poly = QPolygonF(pts)

        if has_fill and not has_outline:
            painter.setPen(Qt.NoPen)
            painter.setBrush(_fill_brush())
            painter.drawPolygon(poly)
            painter.setBrush(Qt.NoBrush)
        elif has_outline and not has_fill:
            if gradient_outline is not None:
                from PySide6.QtGui import QBrush
                pen = QPen(QBrush(gradient_outline), lw)
                pen.setCapStyle(Qt.RoundCap)
                pen.setJoinStyle(Qt.RoundJoin)
            else:
                pen = QPen(effective_outline)
                pen.setWidthF(lw)
                pen.setCapStyle(Qt.RoundCap)
                pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawPolygon(poly)
            painter.setPen(Qt.NoPen)
        else:
            if gradient_outline is not None:
                from PySide6.QtGui import QBrush
                pen = QPen(QBrush(gradient_outline), lw)
                pen.setCapStyle(Qt.RoundCap)
                pen.setJoinStyle(Qt.RoundJoin)
            else:
                pen = QPen(effective_outline)
                pen.setWidthF(lw)
                pen.setCapStyle(Qt.RoundCap)
                pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(_fill_brush())
            painter.drawPolygon(poly)
            painter.setPen(Qt.NoPen)
            painter.setBrush(Qt.NoBrush)

        if rot is not None:
            painter.restore()

class AnimatedText(_TweenDriver):
    def __init__(self, defn: TextDef):
        super().__init__()
        self.defn = defn
        d = defn
        self.cur_p:         P      = P(d.p.x, d.p.y)
        self.cur_px:        P      = P(d.px.x, d.px.y)

        self.cur_color      = QColor(d.fill_color)
        self.cur_font_size  = d.font_size
        self.cur_h_align    = d.h_align
        self.cur_v_align    = d.v_align
        self.cur_char_display = d.char_display
 
        self._sp:           P      = P(d.p.x, d.p.y)
        self._spx:          P      = P(d.px.x, d.px.y)
        self._sc   = QColor(d.fill_color)
        self._sfs  = d.font_size
        self._sha  = d.h_align
        self._sva  = d.v_align
        self._scd  = d.char_display
 
        self._dirty        = True
        self._cached_font  = None
        self._cached_x:  float = -1.0
        self._cached_y:  float = -1.0
        self._cached_px: float = -999.0
        self._cached_py: float = -999.0
        self._cached_dx    = 0
        self._cached_dy    = 0
        self._cached_label = ''
        self._cached_tw    = 0
        selfF_cached_th    = 0
        self._cached_fm: Optional[QFontMetrics] = None
 
        self._always_drivers_t: Dict[str, _AlwaysDriver] = {
            name: _AlwaysDriver(name, phase, 1)
            for name, phase in (defn.phases or {}).items()
            if _phase_key_name(name).startswith('always')
        }
        self._always_x_offset:  float = 0.0
        self._always_y_offset:  float = 0.0
        self._always_px_offset:  float           = 0.0
        self._always_py_offset:  float           = 0.0
        self._always_text_color: Optional[QColor] = None

        self._pos_offset: P = P(0.0, 0.0)

        self.cur_gradient_p1:  P = P(defn.gradient_p1.x,  defn.gradient_p1.y)
        self.cur_gradient_px1: P = P(defn.gradient_px1.x, defn.gradient_px1.y)
        self.cur_gradient_p2:  P = P(defn.gradient_p2.x,  defn.gradient_p2.y)
        self.cur_gradient_px2: P = P(defn.gradient_px2.x, defn.gradient_px2.y)
        self.cur_outline_color: QColor = QColor(defn.outline_color) if defn.outline_color else QColor(0,0,0,0)
        self.cur_outline_width: float  = defn.outline_width

        self._so:   QColor = QColor(defn.outline_color) if defn.outline_color else QColor(0,0,0,0)
        self._slow: float  = defn.outline_width
        self._sgp1:  P = P(defn.gradient_p1.x,  defn.gradient_p1.y)
        self._sgpx1: P = P(defn.gradient_px1.x, defn.gradient_px1.y)
        self._sgp2:  P = P(defn.gradient_p2.x,  defn.gradient_p2.y)
        self._sgpx2: P = P(defn.gradient_px2.x, defn.gradient_px2.y)

        self.cur_rot_center_p:      P     = P(defn.rot_center_p.x,  defn.rot_center_p.y)
        self.cur_rot_center_px:     P     = P(defn.rot_center_px.x, defn.rot_center_px.y)
        self.cur_rot_target_p:      P     = P(defn.rot_target_p.x,  defn.rot_target_p.y)
        self.cur_rot_target_px:     P     = P(defn.rot_target_px.x, defn.rot_target_px.y)
        self.cur_rot_angle_initial: float = defn.rot_angle_initial
        self.cur_rot_angle:         float = defn.rot_angle

        self._s_rot_center_p:      P     = P(defn.rot_center_p.x,  defn.rot_center_p.y)
        self._s_rot_center_px:     P     = P(defn.rot_center_px.x, defn.rot_center_px.y)
        self._s_rot_target_p:      P     = P(defn.rot_target_p.x,  defn.rot_target_p.y)
        self._s_rot_target_px:     P     = P(defn.rot_target_px.x, defn.rot_target_px.y)
        self._s_rot_angle_initial: float = defn.rot_angle_initial
        self._s_rot_angle:         float = defn.rot_angle

    def _save_start(self):
        self._sp    = P(self.cur_p.x,  self.cur_p.y)
        self._spx   = P(self.cur_px.x, self.cur_px.y)
        self._sc    = QColor(self.cur_color)
        self._so    = QColor(self.cur_outline_color)
        self._slow  = self.cur_outline_width
        self._sfs   = self.cur_font_size
        self._sha   = self.cur_h_align
        self._sva   = self.cur_v_align
        self._scd   = self.cur_char_display
        self._sgp1  = P(self.cur_gradient_p1.x,  self.cur_gradient_p1.y)
        self._sgpx1 = P(self.cur_gradient_px1.x, self.cur_gradient_px1.y)
        self._sgp2  = P(self.cur_gradient_p2.x,  self.cur_gradient_p2.y)
        self._sgpx2 = P(self.cur_gradient_px2.x, self.cur_gradient_px2.y)

    def _snap_to(self, tw: TextTween):
        self.cur_p             = P(self._sp.x,  self._sp.y)
        self.cur_px            = P(self._spx.x, self._spx.y)
        self.cur_color         = QColor(self._sc)
        self.cur_outline_color = QColor(self._so)
        self.cur_outline_width = self._slow
        self.cur_h_align       = self._sha
        self.cur_v_align       = self._sva
        self.cur_font_size     = self._sfs
        self.cur_char_display  = self._scd
        self.cur_gradient_p1   = P(self._sgp1.x,  self._sgp1.y)
        self.cur_gradient_px1  = P(self._sgpx1.x, self._sgpx1.y)
        self.cur_gradient_p2   = P(self._sgp2.x,  self._sgp2.y)
        self.cur_gradient_px2  = P(self._sgpx2.x, self._sgpx2.y)
        if tw.p is not None:
            if tw.p.x is not None: self.cur_p  = P(tw.p.x,  self.cur_p.y)
            if tw.p.y is not None: self.cur_p  = P(self.cur_p.x, tw.p.y)
        if tw.px is not None:
            if tw.px.x is not None: self.cur_px = P(tw.px.x, self.cur_px.y)
            if tw.px.y is not None: self.cur_px = P(self.cur_px.x, tw.px.y)
        if tw.fill_color    is not None: self.cur_color         = QColor(tw.fill_color)
        if tw.outline_color is not None: self.cur_outline_color = QColor(tw.outline_color)
        if tw.outline_width is not None: self.cur_outline_width = tw.outline_width
        if tw.h_align       is not None: self.cur_h_align       = tw.h_align
        if tw.v_align       is not None: self.cur_v_align       = tw.v_align
        if tw.font_size     is not None: self.cur_font_size     = tw.font_size
        if tw.char_display  is not None: self.cur_char_display  = tw.char_display
        if tw.gradient_p1   is not None: self.cur_gradient_p1   = tw.gradient_p1
        if tw.gradient_px1  is not None: self.cur_gradient_px1  = tw.gradient_px1
        if tw.gradient_p2   is not None: self.cur_gradient_p2   = tw.gradient_p2
        if tw.gradient_px2  is not None: self.cur_gradient_px2  = tw.gradient_px2
        if tw.rot_center_p      is not None: self.cur_rot_center_p      = tw.rot_center_p
        if tw.rot_center_px     is not None: self.cur_rot_center_px     = tw.rot_center_px
        if tw.rot_target_p      is not None: self.cur_rot_target_p      = tw.rot_target_p
        if tw.rot_target_px     is not None: self.cur_rot_target_px     = tw.rot_target_px
        if tw.rot_angle_initial is not None: self.cur_rot_angle_initial = tw.rot_angle_initial
        if tw.rot_angle         is not None: self.cur_rot_angle         = tw.rot_angle
        self._dirty = True

    def _reset_to_def(self):
        d = self.defn
        self.cur_p             = P(d.p.x, d.p.y)
        self.cur_px            = P(d.px.x, d.px.y)
        self.cur_color         = QColor(d.fill_color)
        self.cur_outline_color = QColor(d.outline_color) if d.outline_color else QColor(0,0,0,0)
        self.cur_outline_width = d.outline_width
        self.cur_font_size     = d.font_size
        self.cur_h_align       = d.h_align
        self.cur_v_align       = d.v_align
        self.cur_char_display  = d.char_display
        self.cur_gradient_p1   = P(d.gradient_p1.x,  d.gradient_p1.y)
        self.cur_gradient_px1  = P(d.gradient_px1.x, d.gradient_px1.y)
        self.cur_gradient_p2   = P(d.gradient_p2.x,  d.gradient_p2.y)
        self.cur_gradient_px2  = P(d.gradient_px2.x, d.gradient_px2.y)
        self.cur_rot_center_p      = P(d.rot_center_p.x,  d.rot_center_p.y)
        self.cur_rot_center_px     = P(d.rot_center_px.x, d.rot_center_px.y)
        self.cur_rot_target_p      = P(d.rot_target_p.x,  d.rot_target_p.y)
        self.cur_rot_target_px     = P(d.rot_target_px.x, d.rot_target_px.y)
        self.cur_rot_angle_initial = d.rot_angle_initial
        self.cur_rot_angle         = d.rot_angle
        self._dirty = True

    def _apply(self, tw: TextTween, v: float):
        if tw.p is not None:
            tx = self._sp.x + (tw.p.x - self._sp.x) * v if tw.p.x is not None else self._sp.x
            ty = self._sp.y + (tw.p.y - self._sp.y) * v if tw.p.y is not None else self._sp.y
            self.cur_p = P(tx, ty)
        if tw.px is not None:
            tx = self._spx.x + (tw.px.x - self._spx.x) * v if tw.px.x is not None else self._spx.x
            ty = self._spx.y + (tw.px.y - self._spx.y) * v if tw.px.y is not None else self._spx.y
            self.cur_px = P(tx, ty)
        if tw.fill_color    is not None: self.cur_color         = lerp_color(self._sc,  tw.fill_color,    v)
        if tw.outline_color is not None: self.cur_outline_color = lerp_color(self._so,  tw.outline_color, v)
        if tw.outline_width is not None: self.cur_outline_width = self._slow + (tw.outline_width - self._slow) * v
        if tw.h_align       is not None: self.cur_h_align       = self._sha  + (tw.h_align       - self._sha)  * v
        if tw.v_align       is not None: self.cur_v_align       = self._sva  + (tw.v_align       - self._sva)  * v
        if tw.font_size     is not None: self.cur_font_size     = self._sfs  + (tw.font_size     - self._sfs)  * v
        if tw.char_display  is not None: self.cur_char_display  = self._scd  + (tw.char_display  - self._scd)  * v
        if tw.gradient_p1   is not None: self.cur_gradient_p1   = P(self._sgp1.x  + (tw.gradient_p1.x  - self._sgp1.x)  * v, self._sgp1.y  + (tw.gradient_p1.y  - self._sgp1.y)  * v)
        if tw.gradient_px1  is not None: self.cur_gradient_px1  = P(self._sgpx1.x + (tw.gradient_px1.x - self._sgpx1.x) * v, self._sgpx1.y + (tw.gradient_px1.y - self._sgpx1.y) * v)
        if tw.gradient_p2   is not None: self.cur_gradient_p2   = P(self._sgp2.x  + (tw.gradient_p2.x  - self._sgp2.x)  * v, self._sgp2.y  + (tw.gradient_p2.y  - self._sgp2.y)  * v)
        if tw.gradient_px2  is not None: self.cur_gradient_px2  = P(self._sgpx2.x + (tw.gradient_px2.x - self._sgpx2.x) * v, self._sgpx2.y + (tw.gradient_px2.y - self._sgpx2.y) * v)
        if tw.rot_center_p      is not None: self.cur_rot_center_p      = P(self._s_rot_center_p.x  + (tw.rot_center_p.x  - self._s_rot_center_p.x)  * v, self._s_rot_center_p.y  + (tw.rot_center_p.y  - self._s_rot_center_p.y)  * v)
        if tw.rot_center_px     is not None: self.cur_rot_center_px     = P(self._s_rot_center_px.x + (tw.rot_center_px.x - self._s_rot_center_px.x) * v, self._s_rot_center_px.y + (tw.rot_center_px.y - self._s_rot_center_px.y) * v)
        if tw.rot_target_p      is not None: self.cur_rot_target_p      = P(self._s_rot_target_p.x  + (tw.rot_target_p.x  - self._s_rot_target_p.x)  * v, self._s_rot_target_p.y  + (tw.rot_target_p.y  - self._s_rot_target_p.y)  * v)
        if tw.rot_target_px     is not None: self.cur_rot_target_px     = P(self._s_rot_target_px.x + (tw.rot_target_px.x - self._s_rot_target_px.x) * v, self._s_rot_target_px.y + (tw.rot_target_px.y - self._s_rot_target_px.y) * v)
        if tw.rot_angle_initial is not None: self.cur_rot_angle_initial = self._s_rot_angle_initial + (tw.rot_angle_initial - self._s_rot_angle_initial) * v
        if tw.rot_angle         is not None: self.cur_rot_angle         = self._s_rot_angle         + (tw.rot_angle         - self._s_rot_angle)         * v
        self._dirty = True
    
    def _apply_blend(self, tw: TextTween, v: float):
        if tw.p is not None:
            nx = self.cur_p.x  + tw.p.x  * v if tw.p.x  is not None else self.cur_p.x
            ny = self.cur_p.y  + tw.p.y  * v if tw.p.y  is not None else self.cur_p.y
            self.cur_p = P(nx, ny)
        if tw.px is not None:
            nx = self.cur_px.x + tw.px.x * v if tw.px.x is not None else self.cur_px.x
            ny = self.cur_px.y + tw.px.y * v if tw.px.y is not None else self.cur_px.y
            self.cur_px = P(nx, ny)
        if tw.fill_color    is not None: self.cur_color         = lerp_color(self.cur_color,         tw.fill_color,    v)
        if tw.outline_color is not None: self.cur_outline_color = lerp_color(self.cur_outline_color, tw.outline_color, v)
        if tw.outline_width is not None: self.cur_outline_width += tw.outline_width * v
        if tw.h_align       is not None: self.cur_h_align       += tw.h_align       * v
        if tw.v_align       is not None: self.cur_v_align       += tw.v_align       * v
        if tw.font_size     is not None: self.cur_font_size     += tw.font_size     * v
        if tw.char_display  is not None: self.cur_char_display  += tw.char_display  * v
        if tw.gradient_p1   is not None: self.cur_gradient_p1   = P(self.cur_gradient_p1.x  + tw.gradient_p1.x  * v, self.cur_gradient_p1.y  + tw.gradient_p1.y  * v)
        if tw.gradient_px1  is not None: self.cur_gradient_px1  = P(self.cur_gradient_px1.x + tw.gradient_px1.x * v, self.cur_gradient_px1.y + tw.gradient_px1.y * v)
        if tw.gradient_p2   is not None: self.cur_gradient_p2   = P(self.cur_gradient_p2.x  + tw.gradient_p2.x  * v, self.cur_gradient_p2.y  + tw.gradient_p2.y  * v)
        if tw.gradient_px2  is not None: self.cur_gradient_px2  = P(self.cur_gradient_px2.x + tw.gradient_px2.x * v, self.cur_gradient_px2.y + tw.gradient_px2.y * v)
        self._dirty = True

    def set_phase(self, phase):
        super().set_phase(phase, self.defn.phases)
        self._dirty = True
        for driver in self._always_drivers_t.values():
            driver.notify_phase(phase, False)
        

    def update(self) -> None:
        pos_fn = self.defn.pos_fn
        if pos_fn is not None:
            try:
                offset = pos_fn()
                if offset is not None:
                    self._pos_offset = offset
                    self._dirty = True
            except Exception:
                pass
        self._drive()
 
        sum_px         = 0.0
        sum_py         = 0.0
        sum_x          = 0.0
        sum_y          = 0.0
        color_override = None
        base_done      = self.phase_done()

        for driver in self._always_drivers_t.values():
            driver.update(self._phase, base_done)
            sum_x  += driver.offset_p[0].x
            sum_y  += driver.offset_p[0].y
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
        fn = self.defn.text_fn

        if fn is None:
            return template

        if isinstance(fn, EventDef):
            return str(fn.value)

        if callable(fn):
            try:    raw = fn(context)
            except: raw = ''
            if isinstance(raw, list):
                result = template
                for item in raw:
                    if '<#>' not in result:
                        break
                    result = result.replace('<#>', str(item), 1)
                return result
            value = str(raw)
            return template.replace('<#>', value) if '<#>' in template else value

        if isinstance(fn, list):
            result = template
            for item in fn:
                if '<#>' not in result:
                    break
                if isinstance(item, EventDef):
                    value = str(item.value)
                elif callable(item):
                    try:    value = str(item(context))
                    except: value = ''
                else:
                    value = str(item)
                result = result.replace('<#>', value, 1)
            return result

        return template

    def build_font(self, scale: float = 1.0):
        scaled_size = max(0.5, self.cur_font_size * scale)
        if self._cached_font is None or self._cached_font.pointSizeF() != scaled_size:
            f = QFont()
            if self.defn.font_family: f.setFamily(self.defn.font_family)
            f.setPointSizeF(scaled_size)
            f.setBold(self.defn.bold)
            f.setItalic(self.defn.italic)
            self._cached_font = f
            self._cached_fm   = None
        return self._cached_font

    def resolve_pos(self, widget_w, widget_h, cam_w, cam_h, label, font, scale=1.0):
        if (self._cached_label == label
                and self._cached_tw == widget_w
                and self._cached_th == widget_h
                and self._cached_x  == self.cur_p.x
                and self._cached_y  == self.cur_p.y
                and self._cached_px == self.cur_px.x + self._always_px_offset
                and self._cached_py == self.cur_px.y + self._always_py_offset):
            return self._cached_dx, self._cached_dy
        if self._cached_fm is None or self._dirty:
            self._cached_fm = QFontMetrics(font)
        fm = self._cached_fm
        if self.defn.uniform_scale:
            s  = min(widget_w/cam_w, widget_h/cam_h)
            bx = (0.5+(self.cur_p.x-0.5)*s/(widget_w/cam_w))*widget_w
            by = (0.5+(self.cur_p.y-0.5)*s/(widget_h/cam_h))*widget_h
        else:
            bx = self.cur_p.x*widget_w
            by = self.cur_p.y*widget_h
        bx += self.cur_px.x * scale
        by += self.cur_px.y * scale
        dx = int(bx - self.cur_h_align * fm.horizontalAdvance(label) + self._always_px_offset * scale)
        dy = int(by + fm.ascent() - self.cur_v_align * fm.height()   + self._always_py_offset * scale)
        self._cached_x  = self.cur_p.x
        self._cached_y  = self.cur_p.y
        self._cached_px = self.cur_px.x + self._always_px_offset
        self._cached_py = self.cur_px.y + self._always_py_offset
        self._cached_dx    = dx
        self._cached_dy    = dy
        self._cached_label = label
        self._cached_tw    = widget_w
        self._cached_th    = widget_h
        self._dirty        = False
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
    
    def draw_text(self, painter: QPainter, widget_w: int, widget_h: int, cam_w: int, cam_h: int, ctx: Any, scale: float = 1.0) -> None:
        if self.hidden:
            return

        full_label = self.resolve_text(ctx)
        if not full_label:
            return

        cd = self.cur_char_display
        if cd <= 0.0:
            return

        scale      = 1.0 if not self.defn.uniform_scale else scale
        font       = self.build_font(scale)
        fm         = QFontMetrics(font)
        use_path   = (self.defn.outline_width > 0.0 or self.defn.outline_color is not None or self.defn.gradient is not None)

        orig_p  = self.cur_p
        orig_px = self.cur_px
        self.cur_p  = P(self.cur_p.x  + self._always_x_offset, self.cur_p.y  + self._always_y_offset)
        self.cur_px = P(self.cur_px.x + self._always_px_offset, self.cur_px.y + self._always_py_offset)
        dx, dy = self.resolve_pos(widget_w, widget_h, cam_w, cam_h, full_label, font, scale)
        self.cur_p  = orig_p
        self.cur_px = orig_px

        dx += int(self._pos_offset.x)
        dy += int(self._pos_offset.y)

        fill_color = self._always_text_color if self._always_text_color is not None else self.cur_color

        # apply char_display clipping
        if cd < 1.0 and not self.defn.sub_char_clip:
            display_label = self.resolve_display_text(full_label)
            if not display_label:
                return
            if self.defn.backward:
                disp_w = fm.horizontalAdvance(display_label)
                full_w = fm.horizontalAdvance(full_label)
                dx     = dx + full_w - disp_w
            full_label = display_label

        rot = _resolve_rotation(
            self.cur_rot_center_p, self.cur_rot_center_px,
            self.cur_rot_target_p, self.cur_rot_target_px,
            self.cur_rot_angle_initial, self.cur_rot_angle,
            widget_w, widget_h
        )
        if rot is not None:
            rcx, rcy, angle = rot
            painter.save()
            painter.translate(rcx, rcy)
            painter.rotate(angle)
            painter.translate(-rcx, -rcy)

        painter.setFont(font)

        if not use_path:
            # fast path — solid color text
            if cd >= 1.0 or self.defn.sub_char_clip:
                painter.setPen(fill_color)
                if self.defn.sub_char_clip and cd < 1.0:
                    full_w  = fm.horizontalAdvance(full_label)
                    clip_w  = full_w * cd
                    ascent  = fm.ascent()
                    descent = fm.descent()
                    clip_x  = (dx + full_w - clip_w) if self.defn.backward else dx
                    painter.save()
                    painter.setClipRect(QRectF(clip_x, dy - ascent, clip_w, ascent + descent))
                    painter.drawText(int(dx), int(dy), full_label)
                    painter.restore()
                else:
                    painter.drawText(int(dx), int(dy), full_label)
                painter.setPen(Qt.NoPen)
            return

        path = QPainterPath()
        path.addText(dx, dy, font, full_label)

        if self.defn.sub_char_clip and cd < 1.0:
            full_w  = fm.horizontalAdvance(full_label)
            clip_w  = full_w * cd
            ascent  = fm.ascent()
            descent = fm.descent()
            clip_x  = (dx + full_w - clip_w) if self.defn.backward else dx
            painter.save()
            painter.setClipRect(QRectF(clip_x, dy - ascent, clip_w, ascent + descent))

        gd = self.defn.gradient

        def _gradient_brush():
            def _has(p, px): return p.x!=0 or p.y!=0 or px.x!=0 or px.y!=0
            if _has(self.cur_gradient_p1, self.cur_gradient_px1) or \
            _has(self.cur_gradient_p2, self.cur_gradient_px2):
                x1 = self.cur_gradient_p1.x  * widget_w + self.cur_gradient_px1.x
                y1 = self.cur_gradient_p1.y  * widget_h + self.cur_gradient_px1.y
                x2 = self.cur_gradient_p2.x  * widget_w + self.cur_gradient_px2.x
                y2 = self.cur_gradient_p2.y  * widget_h + self.cur_gradient_px2.y
            else:
                x1 = gd.p1.x  * widget_w + gd.px1.x
                y1 = gd.p1.y  * widget_h + gd.px1.y
                x2 = gd.p2.x  * widget_w + gd.px2.x
                y2 = gd.p2.y  * widget_h + gd.px2.y
            return gd._animated.build_gradient(x1, y1, x2, y2, radial=gd.radial)

        # fill
        if gd is not None and gd.target == 'fill':
            painter.setPen(Qt.NoPen)
            painter.fillPath(path, _gradient_brush())
        else:
            painter.setPen(Qt.NoPen)
            painter.fillPath(path, fill_color)

        # outline
        if self.cur_outline_width > 0.0 or self.cur_outline_color.alpha() > 0:
            if gd is not None and gd.target == 'outline':
                pen = QPen(_gradient_brush(), self.cur_outline_width)
            else:
                oc = self.cur_outline_color if self.cur_outline_color.alpha() > 0 else fill_color
                pen = QPen(oc, self.cur_outline_width)
            pen.setJoinStyle(Qt.RoundJoin)
            pen.setCapStyle(Qt.RoundCap)
            painter.strokePath(path, pen)

        if self.defn.sub_char_clip and cd < 1.0:
            painter.restore()
        
        if rot is not None:
            painter.restore()

        painter.setPen(Qt.NoPen)

# ──────────────────────── ARC DEF ────────────────────────

@dataclass
class ArcDef:
    center_p:            P                = field(default_factory=P)
    center_px:           P                = field(default_factory=P)
    outer_p:             P                = field(default_factory=P)
    outer_px:            P                = field(default_factory=P)
    inner_p:             Optional[P]      = None
    inner_px:            Optional[P]      = None
    angle_start:         Optional[float]  = None
    angle_end:           Optional[float]  = None
    circle:              bool             = False
    fill_color:          QColor           = field(default_factory=lambda: QColor(255, 255, 255, 255))
    outline_color:       Optional[QColor] = None
    outline_width:       float            = 0.0
    rot_center_p:        P                = field(default_factory=P)
    rot_center_px:       P                = field(default_factory=P)
    rot_target_p:        P                = field(default_factory=P)
    rot_target_px:       P                = field(default_factory=P)
    rot_angle_initial:   float            = 0.0
    rot_angle:           float            = 0.0
    hidden:              bool             = False
    visible_threshold_x: float            = 0.0
    visible_threshold_y: float            = 0.0

    def __post_init__(self):
        if not self.circle and self.angle_start is None and self.angle_end is None:
            self.circle = True


class AnimatedArc:
    def __init__(self, defn: ArcDef) -> None:
        self.defn   = defn
        self.hidden = defn.hidden

    def _resolve(self, ww: int, wh: int) -> Tuple[float, float, float, float, Optional[float]]:
        d  = self.defn
        cx = d.center_p.x * ww + d.center_px.x
        cy = d.center_p.y * wh + d.center_px.y

        # outer radius — use distance from center to outer point
        ox = d.outer_p.x * ww + d.outer_px.x
        oy = d.outer_p.y * wh + d.outer_px.y
        outer_r = _math.sqrt((ox - cx) ** 2 + (oy - cy) ** 2)

        # inner radius
        inner_r = None
        if d.inner_p is not None:
            ipx = d.inner_px or P()
            ix = d.inner_p.x * ww + ipx.x
            iy = d.inner_p.y * wh + ipx.y
            r  = _math.sqrt((ix - cx) ** 2 + (iy - cy) ** 2)
            if r > 0.0 and (d.inner_p.x != d.center_p.x or d.inner_p.y != d.center_p.y or
                             ipx.x != d.center_px.x or ipx.y != d.center_px.y):
                inner_r = r

        return cx, cy, outer_r, inner_r

    def draw(self, painter: QPainter, ww: int, wh: int) -> None:
        if self.hidden:
            return

        d = self.defn
        if d.fill_color.alpha() == 0 and (d.outline_width <= 0 or d.outline_color is None or d.outline_color.alpha() == 0):
            return

        cx, cy, outer_r, inner_r = self._resolve(ww, wh)
        if outer_r <= 0:
            return

        rot = _resolve_rotation(
            d.rot_center_p, d.rot_center_px,
            d.rot_target_p, d.rot_target_px,
            d.rot_angle_initial, d.rot_angle,
            ww, wh
        )
        if rot is not None:
            rcx, rcy, angle = rot
            painter.save()
            painter.translate(rcx, rcy)
            painter.rotate(angle)
            painter.translate(-rcx, -rcy)

        # determine if full circle
        is_circle = d.circle
        if not is_circle:
            if d.angle_start is None or d.angle_end is None:
                is_circle = True
            else:
                diff = abs(d.angle_end - d.angle_start)
                if diff == 0.0:
                    return
                elif diff >= 360.0:
                    is_circle = True

        def _build_path() -> QPainterPath:
            path = QPainterPath()
            rect_outer = QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2)

            if is_circle:
                if inner_r is not None and inner_r > 0:
                    path.addEllipse(rect_outer)
                    inner_path = QPainterPath()
                    rect_inner = QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2)
                    inner_path.addEllipse(rect_inner)
                    path = path.subtracted(inner_path)
                else:
                    path.addEllipse(rect_outer)
                return path

            # Our convention: 0 = North, clockwise
            # Qt convention:  0 = East (3 o'clock), counter-clockwise, units = 1/16th degree
            # Convert: qt_angle = 90 - our_angle
            start_our = d.angle_start if d.angle_start is not None else 0.0
            end_our   = d.angle_end   if d.angle_end   is not None else 0.0

            # span is always positive, direction is clockwise in our system
            # which means negative span in Qt
            span = end_our - start_our
            # normalise so span is in (-360, 360), preserve sign
            span = span % 360.0
            if span == 0.0:
                return path  # nothing to draw

            # Convert start to Qt: 0=North,CW -> Qt 0=East,CCW
            qt_start = 90.0 - start_our
            qt_span  = -span   # clockwise in our system = negative in Qt

            # Qt works in 1/16th degrees internally via arcTo which takes degrees directly
            rect_inner = QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2) if (inner_r is not None and inner_r > 0) else None

            if rect_inner is not None:
                # donut arc
                start_rad = _math.radians(start_our - 90.0)  # convert to standard math angle
                end_rad   = _math.radians(end_our   - 90.0)

                # start point on outer arc
                path.moveTo(cx + outer_r * _math.cos(start_rad),
                            cy + outer_r * _math.sin(start_rad))
                path.arcTo(rect_outer, qt_start, qt_span)
                # connect to inner arc end point
                path.lineTo(cx + inner_r * _math.cos(end_rad),
                            cy + inner_r * _math.sin(end_rad))
                path.arcTo(rect_inner, qt_start + qt_span, -qt_span)
                path.closeSubpath()
            else:
                # pie slice
                start_rad = _math.radians(start_our - 90.0)
                path.moveTo(cx, cy)
                path.lineTo(cx + outer_r * _math.cos(start_rad),
                            cy + outer_r * _math.sin(start_rad))
                path.arcTo(rect_outer, qt_start, qt_span)
                path.closeSubpath()

            return path

        path = _build_path()

        painter.setPen(Qt.NoPen)
        painter.setBrush(d.fill_color)
        painter.drawPath(path)
        painter.setBrush(Qt.NoBrush)

        if d.outline_width > 0.0 and d.outline_color is not None and d.outline_color.alpha() > 0:
            pen = QPen(d.outline_color)
            pen.setWidthF(d.outline_width)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.drawPath(path)
            painter.setPen(Qt.NoPen)
        
        if rot is not None:
            painter.restore()

# ──────────────────────── SLIDER DEF ────────────────────────

def make_track_def(
    p:         P     = P(),
    px:        P     = P(),
    length:    float = 0.0,
    length_px: float = 0.0,
    h_px:      float = 4.0,
    fill_color:    QColor = None,
    outline_color: QColor = None,
    phases: Dict[str, Phase] = None,
) -> PolygonDef:
    half = h_px / 2.0
    fc = fill_color    or QColor(255, 255, 255, 40)
    oc = outline_color or QColor(0, 0, 0, 0)
    return PolygonDef(
        p  = [P(p.x, p.y), P(p.x+length, p.y), P(p.x+length, p.y), P(p.x, p.y)],
        px = [P(px.x, px.y-half), P(px.x+length_px, px.y-half),
              P(px.x+length_px, px.y+half), P(px.x, px.y+half)],
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
        p             = [P(0, 0), P(0, 0), P(0, 0), P(0, 0)],
        px            = [P(0, 0), P(0, 0), P(0, 0), P(0, 0)],
        fill_color    = fc,
        outline_color = QColor(0, 0, 0, 0),
        closed        = True,
        phases        = phases or {},
    )

def make_mark_fill_def(
    p:      P     = P(),
    px:     P     = P(),
    h_px:   float = 8.0,
    fill_color: QColor = None,
    phases: Dict[str, Phase] = None,
) -> PolygonDef:
    half = h_px / 2.0
    fc   = fill_color or QColor(255, 255, 255, 60)
    return PolygonDef(
        p  = [P(p.x, p.y)] * 4,
        px = [P(px.x, px.y-half), P(px.x, px.y-half),
              P(px.x, px.y+half), P(px.x, px.y+half)],
        fill_color    = fc,
        outline_color = QColor(0, 0, 0, 0),
        closed        = True,
        phases        = phases or {},
    )

def make_mark_tick_def(
    p:      P     = P(),
    px:     P     = P(),
    w_px:   float = 3.0,
    h_px:   float = 14.0,
    fill_color: QColor = None,
    phases: Dict[str, Phase] = None,
) -> PolygonDef:
    hw = w_px / 2.0
    hh = h_px / 2.0
    fc = fill_color or QColor(255, 255, 255, 200)
    return PolygonDef(
        p  = [P(p.x, p.y)] * 4,
        px = [P(px.x-hw, px.y-hh), P(px.x+hw, px.y-hh),
              P(px.x+hw, px.y+hh), P(px.x-hw, px.y+hh)],
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
    p:          P                                        = field(default_factory=P)
    px:         P                                        = field(default_factory=P)
    length:     float                                    = 0.0
    length_px:  float                                    = 0.0
    min_val:      float                                  = 0.0
    max_val:      float                                  = 1.0
    event_out:    Optional[EventDef]                     = None
    step:         float                                  = 0.0
    label:        str                                    = ''
    unit:         str                                    = ''
    decimals:     int                                    = 0
    track:        Optional[PolygonDef]                   = None
    knob:         Optional[PolygonDef]                   = None
    mark_fill:    Optional[PolygonDef]                   = None
    mark_tick:    Optional[PolygonDef]                   = None
    text_label:   Optional[TextDef]                      = None
    text_min:     Optional[TextDef]                      = None
    text_max:     Optional[TextDef]                      = None
    text_current: Optional[TextDef]                      = None
    phases:       Dict[str, Phase]                       = field(default_factory=dict)
    event_out:    Optional[EventDef]                     = None
    knob_hit_px:  float                                  = 10.0
    visible_threshold_x: float = 0.0
    visible_threshold_y: float = 0.0


def SliderDef(
    p:           P     = P(),
    px:          P     = P(),
    length:      float = 0.0,
    length_px:   float = 0.0,
    event_out:   Optional[EventDef] = None,
    min_val:     float = 0.0,
    max_val:     float = 1.0,
    step:        float = 0.0,
    label:       str   = '',
    unit:        str   = '',
    decimals:    int   = 0,
    font_family: str   = 'Oxanium SemiBold',
    track_h:     float = 4.0,
    knob_size:   int   = 10,
    mark_h:      float = 6.0,
    tick_h:      float = 12.0,
    track_idle:  QColor = QColor(255, 255, 255,  40),
    track_press: QColor = QColor(200, 220, 255,  80),
    fill_idle:   QColor = QColor(200, 220, 255,  60),
    fill_press:  QColor = QColor(200, 220, 255, 120),
    tick_idle:   QColor = QColor(255, 255, 255, 200),
    tick_press:  QColor = QColor(200, 220, 255, 255),
    knob_idle:   QColor = QColor(255, 255, 255, 220),
    knob_hover:  QColor = QColor(255, 255, 255, 255),
    knob_press:  QColor = QColor(180, 210, 255, 255),
    text_dim:    QColor = QColor(200, 220, 255, 160),
    text_bright: QColor = QColor(200, 220, 255, 255),
    zero_white:  QColor = QColor(255, 255, 255,   0),
    zero_color:  QColor = QColor(200, 220, 255,   0),
    visible_threshold_x: float = 0.0,
    visible_threshold_y: float = 0.0,
) -> SliderGroupDef:
    fam       = font_family
    unit_text = unit

    def _track_phases():
        pts_full = [P(p.x, p.y), P(p.x+length, p.y), P(p.x+length, p.y), P(p.x, p.y)]
        pts_zero = [P(p.x, p.y), P(p.x,        p.y), P(p.x,        p.y), P(p.x, p.y)]
        return {
            'open':     Phase([PolygonTween(p=pts_zero, fill_color=zero_white, start=0.00, dur=0.00, ease=QEasingCurve.Linear),
                               PolygonTween(p=pts_full, fill_color=track_idle, start=0.05, dur=0.40, ease=QEasingCurve.OutQuint)]),
            'close':    Phase([PolygonTween(p=pts_zero, fill_color=zero_white,  start=0.00, dur=0.25, ease=QEasingCurve.InQuint)]),
            'pressed':  Phase([PolygonTween(p=pts_full, fill_color=track_press, start=0.00, dur=0.10, ease=QEasingCurve.OutQuint)]),
            'released': Phase([PolygonTween(p=pts_full, fill_color=track_idle,  start=0.00, dur=0.20, ease=QEasingCurve.OutQuint)]),
        }

    def _knob_phases():
        s  = knob_size
        sh = int(knob_size * 1.3)
        sp = int(knob_size * 0.8)
        def _px(e): return [P(0, -e), P(e, 0), P(0, e), P(-e, 0)]
        pts = [P(0, 0)] * 4
        return {
            'open':      Phase([PolygonTween(p=pts, px=_px(0),  fill_color=zero_white, start=0.00, dur=0.00, ease=QEasingCurve.Linear),
                                PolygonTween(p=pts, px=_px(s),  fill_color=knob_idle,  start=0.10, dur=0.40, ease=QEasingCurve.OutBack)]),
            'close':     Phase([PolygonTween(p=pts, px=_px(0),  fill_color=zero_white, start=0.00, dur=0.20, ease=QEasingCurve.InQuint)]),
            'hovered':   Phase([PolygonTween(p=pts, px=_px(sh), fill_color=knob_hover, start=0.00, dur=0.12, ease=QEasingCurve.OutQuint)]),
            'unhovered': Phase([PolygonTween(p=pts, px=_px(s),  fill_color=knob_idle,  start=0.00, dur=0.15, ease=QEasingCurve.OutQuint)]),
            'pressed':   Phase([PolygonTween(p=pts, px=_px(sp), fill_color=knob_press, start=0.00, dur=0.08, ease=QEasingCurve.OutQuint)]),
            'released':  Phase([PolygonTween(p=pts, px=_px(sh), fill_color=knob_hover, start=0.00, dur=0.12, ease=QEasingCurve.OutBack)]),
        }

    def _mark_phases(idle_col, press_col):
        pts = [P(0, 0)] * 4
        return {
            'open':     Phase([PolygonTween(p=pts, fill_color=zero_color, start=0.00, dur=0.00, ease=QEasingCurve.Linear),
                               PolygonTween(p=pts, fill_color=idle_col,   start=0.10, dur=0.40, ease=QEasingCurve.OutQuint)]),
            'close':    Phase([PolygonTween(p=pts, fill_color=zero_color, start=0.00, dur=0.20, ease=QEasingCurve.InQuint)]),
            'pressed':  Phase([PolygonTween(p=pts, fill_color=press_col,  start=0.00, dur=0.10, ease=QEasingCurve.OutQuint)]),
            'released': Phase([PolygonTween(p=pts, fill_color=idle_col,   start=0.00, dur=0.20, ease=QEasingCurve.OutQuint)]),
        }

    def _text_phases(tp, tpx, h_align=0.5, v_align=0.5):
        return {
            'open':     Phase([TextTween(p=tp, px=tpx, start=0.05, dur=0.40, ease=QEasingCurve.OutQuint, fill_color=text_dim,    h_align=h_align, v_align=v_align)]),
            'close':    Phase([TextTween(p=tp, px=tpx, start=0.00, dur=0.20, ease=QEasingCurve.InQuint,  fill_color=zero_color,  h_align=h_align, v_align=v_align)]),
            'pressed':  Phase([TextTween(p=tp, px=tpx, start=0.00, dur=0.10, ease=QEasingCurve.OutQuint, fill_color=text_bright, h_align=h_align, v_align=v_align)]),
            'released': Phase([TextTween(p=tp, px=tpx, start=0.00, dur=0.20, ease=QEasingCurve.OutQuint, fill_color=text_dim,    h_align=h_align, v_align=v_align)]),
        }

    def _group_phases():
        return {
            'open':  Phase([PolygonTween(p=[P(0, 0)], px=[P(0, 0)],  start=0.00, dur=0.40, ease=QEasingCurve.OutQuint)]),
            'close': Phase([PolygonTween(p=[P(0, 0)], px=[P(0, 20)], start=0.00, dur=0.25, ease=QEasingCurve.InQuint)]),
        }

    return SliderGroupDef(
        p=p, px=px,
        length=length,
        length_px=length_px,
        min_val=min_val,
        max_val=max_val,
        step=step,
        label=label,
        unit=unit,
        decimals=decimals,
        event_out=event_out,
        knob_hit_px=knob_size,

        track=make_track_def(
            p=p, px=px,
            length=length, length_px=length_px,
            h_px=track_h,
            fill_color=zero_white,
            phases=_track_phases(),
        ),

        knob=make_knob_def(
            fill_color=zero_white,
            phases=_knob_phases(),
        ),

        mark_fill=make_mark_fill_def(
            p=p, px=px,
            h_px=mark_h,
            fill_color=zero_color,
            phases=_mark_phases(fill_idle, fill_press),
        ),

        mark_tick=make_mark_tick_def(
            p=p, px=px,
            w_px=2.0, h_px=tick_h,
            fill_color=zero_white,
            phases=_mark_phases(tick_idle, tick_press),
        ),

        text_label=TextDef(
            p=P(p.x, p.y), px=P(px.x - 8, px.y),
            text=label, font_size=7.0,
            fill_color=zero_color,
            phases=_text_phases(P(p.x, p.y), P(px.x - 8, px.y), h_align=1.0, v_align=0.5),
            bold=True, italic=False, font_family=fam,
            h_align=1.0, v_align=0.5, uniform_scale=False,
        ) if label else None,

        text_min=TextDef(
            p=P(0.0, 0.0), px=P(0.0, 14.0),
            text='', font_size=9.0,
            fill_color=zero_color,
            phases=_text_phases(P(p.x, p.y), P(px.x, px.y + 14.0), h_align=0.0, v_align=0.0),
            bold=False, italic=False, font_family=fam,
            h_align=0.0, v_align=0.0, uniform_scale=False,
            text_fn=lambda ctx, u=unit_text, dec=decimals: (
                f"{ctx.defn.min_val:.{dec}f}{u}" if ctx else ''
            ) if dec > 0 else (
                f"{int(ctx.defn.min_val)}{u}" if ctx else ''
            ),
        ) if min_val is not None else None,

        text_max=TextDef(
            p=P(0.0, 0.0), px=P(0.0, 14.0),
            text='', font_size=9.0,
            fill_color=zero_color,
            phases=_text_phases(P(0.0, 0.0), P(0.0, 14.0), h_align=1.0, v_align=0.0),
            bold=False, italic=False, font_family=fam,
            h_align=1.0, v_align=0.0, uniform_scale=False,
            text_fn=lambda ctx, u=unit_text, dec=decimals: (
                f"{ctx.defn.max_val:.{dec}f}{u}" if ctx else ''
            ) if dec > 0 else (
                f"{int(ctx.defn.max_val)}{u}" if ctx else ''
            ),
        ) if max_val is not None else None,

        text_current=TextDef(
            p=P(0.0, 0.0), px=P(0.0, -12.0),
            text='', font_size=10.0,
            fill_color=zero_color,
            phases=_text_phases(P(0.0, 0.0), P(0.0, -12.0), h_align=0.5, v_align=1.0),
            bold=False, italic=False, font_family=fam,
            h_align=0.5, v_align=1.0, uniform_scale=False,
            text_fn=lambda ctx, u=unit_text, dec=decimals: (
                f"{ctx._cur_value:.{dec}f}{u}" +
                (f"  ({ctx._cur_value - ctx._initial_value:+.{dec}f})" if ctx.has_change else '')
            ) if ctx and dec > 0 else (
                f"{int(ctx._cur_value)}{u}" +
                (f"  ({int(ctx._cur_value - ctx._initial_value):+})" if ctx.has_change else '')
            ) if ctx else '',
        ),

        phases=_group_phases(),
    )

class SliderGroup:
    def __init__(self, defn: SliderGroupDef, cam_w=MONITOR_RESOLUTIONS[0][0], cam_h=MONITOR_RESOLUTIONS[0][1]):
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

        self._text_label   = AnimatedText(defn.text_label)   if defn.text_label   else None
        self._text_min     = AnimatedText(defn.text_min)     if defn.text_min     else None
        self._text_max     = AnimatedText(defn.text_max)     if defn.text_max     else None
        self._text_current = AnimatedText(defn.text_current) if defn.text_current else None

        _group_def = PolygonDef(p=[P(0, 0)], px=[P(0, 30)], fill_color=QColor(0, 0, 0, 0), outline_color=QColor(0, 0, 0, 0), closed=True, phases=defn.phases)
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

        self.hidden: bool = False

    def init_value(self, ctx):
        if self.defn.event_out is not None and self.defn.event_out._is_numeric:
            self._cur_value = self._initial_value = float(self.defn.event_out.value)
    
    def commit(self, ctx):
        self._initial_value = self._cur_value
        if self.defn.event_out is not None:
            self.defn.event_out.value = self._cur_value
 
        self._tick_ease_start_sx = self._tick_display_sx
        self._tick_target_sx     = self._knob_sx
        self._tick_ease_t0       = time.monotonic()
        self._tick_easing        = True
        self._tick_frozen        = False

    def revert(self):
        self._cur_value = self._initial_value

    @property
    def has_change(self) -> bool:
        return self._cur_value != self._initial_value

    def set_phase(self, phase: str):
        for comp in (self._track, self._knob, self._mark_fill, self._mark_tick, self._group):
            if comp is not None:
                comp.set_phase(phase)
        for text in (self._text_label, self._text_min, self._text_max, self._text_current):
            if text is not None:
                text.set_phase(phase)
        if phase == 'open':
            self._snap_knob_to_start = True
        if self._knob is not None:
            self._knob._spx = [P(p.x - self._last_knob_sx, p.y - self._last_knob_sy) for p in self._knob._spx]
        if self._text_min is not None and (self._last_text_min_x != 0.0 or self._last_text_min_y != 0.0):
            self._text_min.cur_px = P(self._text_min.cur_px.x - self._last_text_min_x, self._text_min.cur_px.y - self._last_text_min_y)
            self._text_min._spx   = P(self._text_min._spx.x   - self._last_text_min_x, self._text_min._spx.y   - self._last_text_min_y)
        if self._text_max is not None and (self._last_text_max_x != 0.0 or self._last_text_max_y != 0.0):
            self._text_max.cur_px = P(self._text_max.cur_px.x - self._last_text_max_x, self._text_max.cur_px.y - self._last_text_max_y)
            self._text_max._spx   = P(self._text_max._spx.x   - self._last_text_max_x, self._text_max._spx.y   - self._last_text_max_y)
        if self._text_current is not None and (self._last_text_cur_x != 0.0 or self._last_text_cur_y != 0.0):
            self._text_current.cur_px = P(self._text_current.cur_px.x - self._last_text_cur_x, self._text_current.cur_px.y - self._last_text_cur_y)
            self._text_current._spx   = P(self._text_current._spx.x   - self._last_text_cur_x, self._text_current._spx.y   - self._last_text_cur_y)

    def phase_done(self) -> bool:
        comps = [self._track, self._knob, self._mark_fill, self._mark_tick, self._group, self._text_label, self._text_min, self._text_max,   self._text_current]
        return all(c.phase_done() for c in comps if c is not None)

    def hit_test_knob(self, mx: float, my: float, w: int, h: int) -> bool:
        return (abs(mx - self._knob_sx) <= self.defn.knob_hit_px and abs(my - self._knob_sy) <= self.defn.knob_hit_px)

    def drag_to(self, mx, my, w, h):
        span = self._track_x2 - self._track_x1
        if span == 0:
            return
        ratio = max(0.0, min(1.0, (mx - self._track_x1) / span))
        d     = self.defn
        lo, hi, step = d.min_val, d.max_val, d.step
        raw = lo + ratio * (hi - lo)
        if step > 0:
            raw = round(raw / step) * step
        self._cur_value = max(lo, min(hi, raw))
    
    def update(self, widget_w: int, widget_h: int):
        if not self._tick_frozen and not self._tick_easing and self._tick_display_sx == 0.0:
            d = self.defn
            if (d.max_val - d.min_val) != 0:
                init_ratio = (self._initial_value - d.min_val) / (d.max_val - d.min_val)
            else:
                init_ratio = 0.0
            init_ratio = max(0.0, min(1.0, init_ratio))
            
        # 1. Tick group
        self._group.update()
        gp  = self._group.cur_p[0]
        gpx = self._group.cur_px[0]
        g_dx = gp.x * widget_w + gpx.x
        g_dy = gp.y * widget_h + gpx.y

        # 2. Track End Points
        d = self.defn
        self._track_x1 = d.p.x * widget_w + d.px.x + g_dx
        self._track_y1 = d.p.y * widget_h + d.px.y + g_dy
        self._track_x2 = (d.p.x + d.length) * widget_w + d.px.x + d.length_px + g_dx
        self._track_y2 = self._track_y1

        # 3. Track Screen Position
        if self._track is not None:
            self._track._screen_offset = P(g_dx, g_dy)
            self._track._dirty = True
            self._track.update()

        # 4. Knob Position
        if self._snap_knob_to_start:
            self._knob._spx = [P(self._track_x1 - self._knob_sx, self._track_y1 - self._knob_sy) for p in self._knob.cur_px]
            self._last_knob_sx = self._track_x1
            self._last_knob_sy = self._track_y1
            self._snap_knob_to_start = False

        ratio = 0.0 if d.max_val - d.min_val == 0 else max(0.0, min(1.0, (self._cur_value - d.min_val) / (d.max_val - d.min_val)))
        self._knob_sx = self._track_x1 + ratio * (self._track_x2 - self._track_x1)
        self._knob_sy = self._track_y1

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
                    self._tick_display_sx = (self._tick_ease_start_sx + (self._tick_target_sx - self._tick_ease_start_sx) * v)
            elif not self._tick_frozen:
                d = self.defn
                if (d.max_val - d.min_val) != 0:
                    init_ratio = (self._initial_value - d.min_val) / (d.max_val - d.min_val)
                else:
                    init_ratio = 0.0
                init_ratio = max(0.0, min(1.0, init_ratio))
                self._tick_display_sx = self._track_x1 + init_ratio * (self._track_x2 - self._track_x1)

        self._init_sx = self._tick_display_sx

        # 6. Knob
        if self._knob is not None:
            self._knob.cur_px = [P(p.x - self._last_knob_sx, p.y - self._last_knob_sy) for p in self._knob.cur_px]
            self._knob.update()
            self._knob.cur_px = [P(p.x + self._knob_sx, p.y + self._knob_sy) for p in self._knob.cur_px]
            self._last_knob_sx = self._knob_sx
            self._last_knob_sy = self._knob_sy
            self._knob._dirty = True

        # 7. Mark Fill
        if self._mark_fill is not None:
            self._mark_fill.update()
            left_x  = min(self._knob_sx, self._tick_display_sx)
            right_x = max(self._knob_sx, self._tick_display_sx)
            half = (self.defn.mark_fill.px[2].y - self.defn.mark_fill.px[0].y) / 2
            self._mark_fill.cur_p = [P(0, 0)] * 4
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
            hw = (self.defn.mark_tick.px[1].x - self.defn.mark_tick.px[0].x) / 2.0
            hh = (self.defn.mark_tick.px[2].y - self.defn.mark_tick.px[0].y) / 2.0
            self._mark_tick.cur_p = [P(0, 0)] * 4
            self._mark_tick.cur_px = [
                P(self._tick_display_sx - hw, self._knob_sy - hh),
                P(self._tick_display_sx + hw, self._knob_sy - hh),
                P(self._tick_display_sx + hw, self._knob_sy + hh),
                P(self._tick_display_sx - hw, self._knob_sy + hh),
            ]
            self._mark_tick._dirty = True

        # 9. Label text
        if self._text_label is not None:
            self._text_label.update()

        if self._text_min is not None:
            self._text_min.cur_px = P(self._text_min.cur_px.x - self._last_text_min_x, self._text_min.cur_px.y - self._last_text_min_y)
            self._text_min.update()
            self._text_min.cur_p  = P(0.0, 0.0)
            self._text_min.cur_px = P(self._track_x1 + self._text_min.cur_px.x, self._track_y1 + self._text_min.cur_px.y)
            self._last_text_min_x = self._track_x1
            self._last_text_min_y = self._track_y1
            self._text_min._dirty = True

        if self._text_max is not None:
            self._text_max.cur_px = P(self._text_max.cur_px.x - self._last_text_max_x, self._text_max.cur_px.y - self._last_text_max_y)
            self._text_max.update()
            self._text_max.cur_p  = P(0.0, 0.0)
            self._text_max.cur_px = P(self._track_x2 + self._text_max.cur_px.x, self._track_y1  + self._text_max.cur_px.y)
            self._last_text_max_x = self._track_x2
            self._last_text_max_y = self._track_y1
            self._text_max._dirty = True

        if self._text_current is not None:
            self._text_current.cur_px = P(self._text_current.cur_px.x - self._last_text_cur_x, self._text_current.cur_px.y - self._last_text_cur_y)
            self._text_current.update()
            self._text_current.cur_p  = P(0.0, 0.0)
            self._text_current.cur_px = P(self._knob_sx + self._text_current.cur_px.x, self._knob_sy + self._text_current.cur_px.y)
            self._last_text_cur_x     = self._knob_sx
            self._last_text_cur_y     = self._knob_sy
            self._text_current._dirty = True
            
    def draw(self, painter: QPainter, w: int, h: int, scale: float = 1.0):
        if self.hidden:
            return
        cam_w, cam_h = self.cam_w, self.cam_h
        if self._track     is not None: self._track.draw(painter, w, h, cam_w, cam_h)
        if self._mark_fill is not None: self._mark_fill.draw(painter, w, h, cam_w, cam_h)
        if self._mark_tick is not None: self._mark_tick.draw(painter, w, h, cam_w, cam_h)
        if self._knob      is not None: self._knob.draw(painter, w, h, cam_w, cam_h)
        for text in (self._text_label, self._text_min, self._text_max, self._text_current):
            if text is None or text.hidden:
                continue
            text.draw_text(painter, w, h, cam_w, cam_h, self, scale=scale)

# ──────────────────────── BUTTON DEF ────────────────────────

@dataclass
class ButtonDef:
    poly_def:          PolygonDef         = field(default_factory=PolygonDef)
    text_def:          Optional[TextDef]  = None
    key:               Optional[int]      = None
    mandatory_keys:    Any                = None
    action:            str                = 'set'
    event_out:         Any                = None
    event_delta:       Any                = None
    hold_when_set:     bool               = False
    phase_override:    Optional[Any]      = None
    on_fire:           Optional[Callable] = None
    continuous_update: bool               = False
    invisible:         bool               = False
    visible_threshold_x: float = 0.0
    visible_threshold_y: float = 0.0

    def __post_init__(self):
        if self.action not in ('set', 'cycle'): self.hold_when_set = False
        if self.action != 'increment': self.continuous_update = False
        self._build_phases()

    def _build_phases(self):
        _dur  = 0.25
        _ease = QEasingCurve.OutQuint

        poly_phases  = dict(self.poly_def.phases or {})
        base_fill    = self.poly_def.fill_color    or QColor(101,  81, 176, 120)
        base_outline = self.poly_def.outline_color or QColor(171, 151, 247, 255)
        base_lw      = self.poly_def.outline_width    if self.poly_def.outline_width > 0 else 1.0
        fill_zero    = QColor(base_fill.red(),    base_fill.green(),    base_fill.blue(),    0)
        outline_zero = QColor(base_outline.red(), base_outline.green(), base_outline.blue(), 0)
        set_outline  = QColor(255, 255, 255, 255)
        hover_fill, click_fill = _derive_button_colors(base_fill)

        pts = self.poly_def.p
        px  = self.poly_def.px or [P()] * len(pts)

        poly_defaults = {
            'open':    Phase([
                PolygonTween(fill_color=fill_zero,    outline_color=outline_zero, outline_width=base_lw, start=0, dur=0,    ease=QEasingCurve.Linear),
                PolygonTween(fill_color=base_fill,    outline_color=base_outline, outline_width=base_lw, start=0, dur=_dur, ease=_ease),
            ]),
            'close':   Phase([PolygonTween(fill_color=fill_zero,   outline_color=outline_zero, outline_width=base_lw, start=0, dur=_dur, ease=_ease)]),
            'hover':   Phase([PolygonTween(fill_color=hover_fill,  outline_color=base_outline, outline_width=base_lw, start=0, dur=_dur, ease=_ease)]),
            'unhover': Phase([PolygonTween(fill_color=base_fill,   outline_color=base_outline, outline_width=base_lw, start=0, dur=_dur, ease=_ease)]),
            'click':   Phase([PolygonTween(fill_color=click_fill,  outline_color=base_outline, outline_width=base_lw, start=0, dur=_dur, ease=_ease)]),
            'release': Phase([PolygonTween(fill_color=hover_fill,  outline_color=base_outline, outline_width=base_lw, start=0, dur=_dur, ease=_ease)]),
            'set':     Phase([PolygonTween(fill_color=click_fill,  outline_color=set_outline,  outline_width=2.0,     start=0, dur=_dur, ease=_ease)]),
        }

        for phase_name, phase in poly_defaults.items():
            if not _phase_key_exists(poly_phases, phase_name):
                poly_phases[phase_name] = phase

        self.poly_def = _tw_replace(self.poly_def,
            fill_color    = fill_zero,
            outline_color = outline_zero,
            phases        = poly_phases,
        )

        if self.text_def is not None:
            text_phases = dict(self.text_def.phases or {})
            base_color  = self.text_def.fill_color or QColor(255, 255, 255, 255)
            text_zero   = QColor(base_color.red(), base_color.green(), base_color.blue(), 0)

            text_defaults = {
                'open':  Phase([TextTween(fill_color=text_zero,  start=0, dur=0,    ease=QEasingCurve.Linear),
                                TextTween(fill_color=base_color, start=0, dur=_dur, ease=_ease)]),
                'close': Phase([TextTween(fill_color=text_zero,  start=0, dur=_dur, ease=_ease)]),
            }

            for phase_name, phase in text_defaults.items():
                if not _phase_key_exists(text_phases, phase_name):
                    text_phases[phase_name] = phase

            self.text_def = _tw_replace(self.text_def,
                fill_color  = base_color,
                phases = text_phases,
            )

class AnimatedButton:
    def __init__(self, defn: ButtonDef, cam_w: int = MONITOR_RESOLUTIONS[0][0], cam_h: int = MONITOR_RESOLUTIONS[0][1]):
        self.defn       = defn
        self.cam_w      = cam_w
        self.cam_h      = cam_h
        self._hovered   = False
        self._pressed   = False
        self._key_held  = False
        self._held      = False
        self._polygon   = AnimatedPolygon(defn.poly_def)
        self._text      = AnimatedText(defn.text_def) if defn.text_def else None
        self._locked    = False
        self._cur_phase = ''
        self._last_poly: QPolygonF = QPolygonF()
        self._last_w:     int = 0
        self._last_h:     int = 0
        self._last_phase: str = ''
        self._press_poly:QPolygonF = QPolygonF()
        self._last_override_phase: str = ''
        self._pending_set_check: bool = False
        self._last_continuous_time: float = 0.0
        self._continuous_accum: float = 0.0

    def _set_phase(self, phase: str):
        if self._locked and phase not in ('open', 'close'):
            return
        if self._held and phase in ('hover', 'unhover', 'release'):
            return
        if self._held and phase == 'click' and self.defn.action != 'cycle':
            return
        if self._pressed and phase in ('hover', 'unhover'):
            return
        if self._is_closed and phase not in ('open', 'close'):
            return
        if phase == 'close':
            self._held = False
        self._cur_phase = phase
        self._locked = phase in ('open', 'close')
        if phase == 'open':
            self._pending_set_check = True
        self._polygon.set_phase(phase)
        if self._text is not None:
            self._text.set_phase(phase)

    def _check_held(self):
        if not self.defn.hold_when_set:
            return
        ev    = self.defn.event_out
        delta = self.defn.event_delta
        if ev is None:
            return
        if self._cur_phase == 'close':
            if self._held:
                self._held = False
            return
        if self._locked and self.defn.action != 'cycle':
            return
        if self.defn.action == 'cycle':
            last = delta[-1] if isinstance(delta, list) and delta else delta
            should_hold = ev.value == last
        elif self.defn.action == 'set':
            should_hold = ev.value == delta
        else:
            return
        if should_hold and not self._held:
            self._held = True
            self._cur_phase = 'set'
            self._polygon.set_phase('set')
            if self._text is not None:
                self._text.set_phase('set')
        elif not should_hold and self._held:
            self._held = False
            self._set_phase('unhover' if not self._hovered else 'hover')
            
    def hit_test(self, mx: float, my: float, w: int, h: int) -> bool:
        if self._is_closed:
            return False
        if not self.defn.invisible:
            fill_alpha    = self._polygon.cur_fill_color.alpha()
            outline_alpha = self._polygon.cur_outline_color.alpha()
            if fill_alpha == 0 and outline_alpha == 0:
                return False
        poly = self._last_poly if not self._last_poly.isEmpty() else self._polygon.get_polygon(w, h, self.cam_w, self.cam_h)
        return poly.containsPoint(QPointF(mx, my), Qt.OddEvenFill)

    def _hit_test_press_poly(self, mx: float, my: float) -> bool:
        return self._press_poly.containsPoint(QPointF(mx, my), Qt.OddEvenFill) if not self._press_poly.isEmpty() else False

    def hit_test_global(self, gx: float, gy: float, panel) -> bool:
        return self.hit_test(gx - panel.x(), gy - panel.y(), panel.width(), panel.height())
    
    def mouse_left_hitbox(self):
        if self._pressed and not self._key_held:
            self._pressed = False
            self._set_phase('unhover')

    def key_press(self, key: int, held_keys: set = None) -> bool:
        if self._is_closed:
            return False
        if self.defn.key is None or self.defn.key != key or self._key_held:
            return False
        if held_keys is not None and not self._mandatory_keys_held(held_keys):
            return False
        self._key_held  = True
        self._pressed   = True
        self._press_poly = QPolygonF(self._last_poly)
        self._set_phase('click')
        return True

    def key_release(self, key: int, held_keys: set = None) -> bool:
        if self.defn.key is None or self.defn.key != key or not self._key_held:
            return False
        self._key_held = False
        self._pressed  = False
        if not self.defn.continuous_update:
            self.fire_event()
        self._check_held()
        if not self._held:
            self._set_phase('release')
            QTimer.singleShot(250, lambda: self._set_phase('hover' if self._hovered else 'unhover'))
        return True
    
    def _mandatory_keys_held(self, held_keys: set) -> bool:
        mk = self.defn.mandatory_keys
        if mk is None:
            return True
        keys = mk if isinstance(mk, list) else [mk]
        for k in keys:
            if isinstance(k, tuple):
                key, must_held = k
                if must_held and key not in held_keys:
                    return False
                if not must_held and key in held_keys:
                    return False
            else:
                if k not in held_keys:
                    return False
        return True
    
    @property
    def _is_closed(self) -> bool:
        return self._cur_phase == 'close' or self._last_override_phase == 'close'

    def update(self, widget_w: int = 0, widget_h: int = 0):
        self._polygon.update()
        if self._text is not None:
            self._text.update()
        if self._locked and self._polygon.phase_done():
            self._locked = False
            if self._pending_set_check:
                self._pending_set_check = False
                ev    = self.defn.event_out
                delta = self.defn.event_delta
                if self.defn.hold_when_set and self.defn.action == 'set' and ev is not None and ev.value == delta:
                    self._held = True
                    self._cur_phase = 'set'
                    self._polygon.set_phase('set')
                    if self._text is not None:
                        self._text.set_phase('set')
        self._check_held()

        if self.defn.continuous_update:
            is_held = self._key_held or self._pressed
            if is_held:
                ev    = self.defn.event_out
                delta = self.defn.event_delta
                if ev is not None and delta is not None and isinstance(ev.value, (int, float)) and not isinstance(ev.value, bool):
                    now = time.monotonic()
                    if self._last_continuous_time == 0.0:
                        self._last_continuous_time = now
                    dt = now - self._last_continuous_time
                    self._last_continuous_time = now
                    new_val = ev.value + delta * dt
                    lo, hi  = getattr(ev, 'min_val', None), getattr(ev, 'max_val', None)
                    if lo is not None: new_val = max(float(lo), new_val)
                    if hi is not None: new_val = min(float(hi), new_val)
                    ev.value = new_val
            else:
                self._last_continuous_time = 0.0
                self._continuous_accum     = 0.0

        w, h = max(0, widget_w), max(0, widget_h)
        if w > 0 and h > 0:
            if (self._polygon._dirty
                    or w != self._last_w
                    or h != self._last_h
                    or self._cur_phase != self._last_phase):
                self._polygon._dirty = True
                self._last_poly  = self._polygon.get_polygon(w, h, self.cam_w, self.cam_h)
                self._last_w     = w
                self._last_h     = h
                self._last_phase = self._cur_phase

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
                lo, hi  = getattr(ev, 'min_val', None), getattr(ev, 'max_val', None)
                if lo is not None: new_val = max(float(lo), new_val)
                if hi is not None: new_val = min(float(hi), new_val)
                ev.value = int(round(new_val)) if isinstance(ev.value, int) else new_val
        elif action == 'set':
            if delta is not None:
                ev.value = delta
        elif action == 'cycle':
            if delta is not None and isinstance(delta, list) and len(delta) > 0:
                try:    idx = delta.index(ev.value)
                except: idx = -1
                ev.value = delta[(idx + 1) % len(delta)]
            return
        elif isinstance(ev.value, bool):
            ev.value = (not ev.value) if delta is None else bool(delta)
        elif isinstance(ev.value, (int, float)):
            if delta is None: return
            new_val = ev.value + delta
            lo, hi  = getattr(ev, 'min_val', None), getattr(ev, 'max_val', None)
            if lo is not None: new_val = max(float(lo), new_val)
            if hi is not None: new_val = min(float(hi), new_val)
            ev.value = int(round(new_val)) if isinstance(ev.value, int) else new_val
        elif isinstance(ev.value, str):
            if delta is not None: ev.value = str(delta)
        if self.defn.on_fire is not None:
            self.defn.on_fire()

    def draw(self, painter: QPainter, w: int, h: int, scale: float = 1.0):
        self._last_poly = self._polygon.get_polygon(w, h, self.cam_w, self.cam_h)
        if self.defn.invisible:
            return

        fill    = self._polygon.cur_fill_color
        outline = self._polygon.cur_outline_color
        lw      = self._polygon.cur_line_width
        if fill.alpha() == 0 and (lw == 0 or outline.alpha() == 0):
            return

        self._last_poly = self._polygon.get_polygon(w, h, self.cam_w, self.cam_h)
        self._polygon.draw(painter, w, h, self.cam_w, self.cam_h)
        if self._text is not None and not self._text.hidden:
            label = self._text.resolve_text(None)
            if label:
                text_scale = scale if self._text.defn.uniform_scale else 1.0
                font = self._text.build_font(text_scale)
                painter.setFont(font)
                painter.setPen(self._text.cur_color)
                dx, dy = self._text.resolve_pos(w, h, self.cam_w, self.cam_h, label, font, text_scale)
                painter.drawText(dx, dy, label)
                painter.setPen(Qt.NoPen)

@dataclass
class Segment:
    key:           Optional[int]   = None
    event_delta:   Any             = None
    weight:        float           = 1.0
    label:         str             = ''
    text_color:    Optional[QColor]= None
    hold_when_set: bool            = True
    color:         Optional[QColor]= None

def SegmentedButtons(
    p1:             P                    = P(),
    p2:             P                    = P(),
    px1:            P                    = P(),
    px2:            P                    = P(),
    poly_def:       Optional[PolygonDef] = PolygonDef(fill_color=QColor(101, 81, 176, 120), outline_color=QColor(171, 151, 247, 255), outline_width=1.0),
    text_def:       Optional[TextDef]    = TextDef(font_size=18.0, fill_color=QColor(255, 255, 255, 255), bold=True),
    segments:       List[Segment]        = None,
    event_out:      Any                  = None,
    gap_px:         float                = 6.0,
    vertical:       bool                 = False,
    reverse_slant:  bool                 = False,
    line_delay:     float                = 0.05,
    cam_w:          int                  = 1920,
    cam_h:          int                  = 1080,
    phase_override: Any                  = None
) -> List[ButtonDef]:
    segments  = segments or []
    n         = len(segments)
    if n == 0:
        return []

    base_poly     = poly_def or PolygonDef()
    fill_color    = base_poly.fill_color    or QColor(101,  81, 176, 120)
    outline_color = base_poly.outline_color or QColor(171, 151, 247, 255)
    outline_width    = base_poly.outline_width    if base_poly.outline_width > 0 else 1.0

    total_weight = sum(s.weight for s in segments)
    half_gap     = gap_px / 2.0

    if not vertical:
        full_cross_px = (p2.y - p1.y) * cam_h + (px2.y - px1.y)
    else:
        full_cross_px = (p2.x - p1.x) * cam_w + (px2.x - px1.x)
    slant = abs(full_cross_px) / 2.0
    s_top = +slant if not reverse_slant else -slant
    s_bot = -slant if not reverse_slant else +slant

    def _norm_split(weight_before, weight_this):
        r0 = weight_before / total_weight
        r1 = (weight_before + weight_this) / total_weight
        return r0, r1

    def _make_poly(i: int, seg: Segment, weight_before: float) -> PolygonDef:
        r0, r1 = _norm_split(weight_before, seg.weight)
        is_first = i == 0
        is_last  = i == n - 1
        base_col = seg.color or fill_color

        if not vertical:
            main_n0 = p1.x + (p2.x - p1.x) * r0
            main_n1 = p1.x + (p2.x - p1.x) * r1
            main_px0 = px1.x + (px2.x - px1.x) * r0
            main_px1 = px1.x + (px2.x - px1.x) * r1

            top_n  = p1.y;  bot_n  = p2.y
            mid_n  = (p1.y + p2.y) / 2.0
            top_px = px1.y; bot_px = px2.y
            mid_px = (px1.y + px2.y) / 2.0

            left_gap  = 0.0 if is_first else +half_gap
            right_gap = 0.0 if is_last  else -half_gap

            if is_first:
                p = [
                    P(main_n0, top_n),
                    P(main_n1, top_n),
                    P(main_n1, bot_n),
                    P(main_n0, bot_n),
                    P(main_n0, mid_n),
                ]
                px_pts = [
                    P(main_px0 + slant,            top_px),
                    P(main_px1 + right_gap + s_top, top_px),
                    P(main_px1 + right_gap + s_bot, bot_px),
                    P(main_px0 + slant,            bot_px),
                    P(main_px0,                    mid_px),
                ]

            elif is_last:
                p = [
                    P(main_n0, top_n),
                    P(main_n1, top_n),
                    P(main_n1, mid_n),
                    P(main_n1, bot_n),
                    P(main_n0, bot_n),
                ]
                px_pts = [
                    P(main_px0 + left_gap + s_top, top_px),
                    P(main_px1 - slant,            top_px),
                    P(main_px1,                    mid_px),
                    P(main_px1 - slant,            bot_px),
                    P(main_px0 + left_gap + s_bot, bot_px),
                ]
            else:
                p = [P(main_n0, top_n),  P(main_n1, top_n),  P(main_n1, bot_n),  P(main_n0, bot_n)]
                px_pts = [
                    P(main_px0 + left_gap  + s_top, top_px),
                    P(main_px1 + right_gap + s_top, top_px),
                    P(main_px1 + right_gap + s_bot, bot_px),
                    P(main_px0 + left_gap  + s_bot, bot_px),
                ]
        else:
            main_n0  = p1.y + (p2.y - p1.y) * r0
            main_n1  = p1.y + (p2.y - p1.y) * r1
            main_px0 = px1.y + (px2.y - px1.y) * r0
            main_px1 = px1.y + (px2.y - px1.y) * r1

            left_n   = p1.x;           right_n  = p2.x
            mid_n    = (p1.x + p2.x) / 2.0
            left_px  = px1.x;          right_px = px2.x
            mid_px   = (px1.x + px2.x) / 2.0

            top_gap  = 0.0 if is_first else +half_gap
            bot_gap  = 0.0 if is_last  else -half_gap

            if is_first:
                p = [
                    P(mid_n,   main_n0),
                    P(right_n, main_n0),
                    P(right_n, main_n1),
                    P(left_n,  main_n1),
                    P(left_n,  main_n0),
                ]
                px_pts = [
                    P(mid_px,            main_px0), 
                    P(right_px,          main_px0 + slant),
                    P(right_px + s_top,  main_px1 + bot_gap),
                    P(left_px  + s_bot,  main_px1 + bot_gap),
                    P(left_px,           main_px0 + slant),
                ]
            elif is_last:
                p = [
                    P(left_n,  main_n0),
                    P(right_n, main_n0),
                    P(right_n, main_n1),
                    P(mid_n,   main_n1),
                    P(left_n,  main_n1),
                ]
                px_pts = [
                    P(left_px  + s_top,  main_px0 + top_gap),
                    P(right_px + s_top,  main_px0 + top_gap),
                    P(right_px,          main_px1 - slant),
                    P(mid_px,            main_px1),
                    P(left_px,           main_px1 - slant),
                ]
            else:
                p = [
                    P(left_n,  main_n0),
                    P(right_n, main_n0),
                    P(right_n, main_n1),
                    P(left_n,  main_n1),
                ]
                px_pts = [
                    P(left_px  + s_top,  main_px0 + top_gap),
                    P(right_px + s_top,  main_px0 + top_gap),
                    P(right_px + s_bot,  main_px1 + bot_gap),
                    P(left_px  + s_bot,  main_px1 + bot_gap),
                ]

        def _make_dynamic_px(
            is_first=is_first, is_last=is_last,
            main_px0=main_px0, main_px1=main_px1,
            p1=p1, p2=p2, px1=px1, px2=px2,
            vertical=vertical,
            reverse_slant=reverse_slant,
            top_px=px1.y    if not vertical else 0.0,
            bot_px=px2.y    if not vertical else 0.0,
            left_gap=left_gap  if not vertical else 0.0,
            right_gap=right_gap if not vertical else 0.0,
            left_px=px1.x   if vertical else 0.0,
            right_px=px2.x  if vertical else 0.0,
            mid_px=(px1.x+px2.x)/2.0 if vertical else 0.0,
            top_gap=top_gap if vertical else 0.0,
            bot_gap=bot_gap if vertical else 0.0,
        ):
            def _dynamic(ww: int, wh: int) -> List[P]:
                if not vertical:
                    cross_px = (p2.y - p1.y) * wh + (px2.y - px1.y)
                    sl       = abs(cross_px) / 2.0
                    st       = +sl if not reverse_slant else -sl
                    sb       = -sl if not reverse_slant else +sl
                    mid_px_  = (px1.y + px2.y) / 2.0
                    if is_first:
                        return [
                            P(main_px0 + sl,               top_px),
                            P(main_px1 + right_gap + st,   top_px),
                            P(main_px1 + right_gap + sb,   bot_px),
                            P(main_px0 + sl,               bot_px),
                            P(main_px0,                    mid_px_),
                        ]
                    elif is_last:
                        return [
                            P(main_px0 + left_gap + st,    top_px),
                            P(main_px1 - sl,               top_px),
                            P(main_px1,                    mid_px_),
                            P(main_px1 - sl,               bot_px),
                            P(main_px0 + left_gap + sb,    bot_px),
                        ]
                    else:
                        return [
                            P(main_px0 + left_gap  + st,   top_px),
                            P(main_px1 + right_gap + st,   top_px),
                            P(main_px1 + right_gap + sb,   bot_px),
                            P(main_px0 + left_gap  + sb,   bot_px),
                        ]
                else:
                    cross_px = (p2.x - p1.x) * ww + (px2.x - px1.x)
                    sl       = abs(cross_px) / 2.0
                    st       = +sl if not reverse_slant else -sl
                    sb       = -sl if not reverse_slant else +sl
                    if is_first:
                        return [
                            P(mid_px,            main_px0),
                            P(right_px,          main_px0 + sl),
                            P(right_px,          main_px1 + bot_gap + sb),
                            P(left_px,           main_px1 + bot_gap + st),
                            P(left_px,           main_px0 + sl),
                        ]
                    elif is_last:
                        return [
                            P(left_px,           main_px0 + top_gap + st),
                            P(right_px,          main_px0 + top_gap + sb),
                            P(right_px,          main_px1 - sl),
                            P(mid_px,            main_px1),
                            P(left_px,           main_px1 - sl),
                        ]
                    else:
                        return [
                            P(left_px ,     main_px0 + top_gap + st),
                            P(right_px,     main_px0 + top_gap + sb),
                            P(right_px,     main_px1 + bot_gap + sb),
                            P(left_px ,     main_px1 + bot_gap + st),
                        ]
            return _dynamic
        
        return PolygonDef(
            p             = p,
            px            = px_pts,
            fill_color    = base_col,
            outline_color = outline_color,
            outline_width    = outline_width,
            closed        = True,
            phases        = {},
            dynamic_px    = _make_dynamic_px(),
        )

    def _make_text(i: int, seg: Segment, weight_before: float) -> Optional[TextDef]:
        if text_def is None and not seg.label:
            return None
        r0, r1   = _norm_split(weight_before, seg.weight)
        r_center = (r0 + r1) / 2.0
        if not vertical:
            cx_n  = p1.x + (p2.x - p1.x) * r_center
            cy_n  = (p1.y + p2.y) / 2.0
            cx_px = px1.x + (px2.x - px1.x) * r_center
            cy_px = (px1.y + px2.y) / 2.0
        else:
            cx_n  = (p1.x + p2.x) / 2.0
            cy_n  = p1.y + (p2.y - p1.y) * r_center
            cx_px = (px1.x + px2.x) / 2.0
            cy_px = px1.y + (px2.y - px1.y) * r_center

        base  = text_def if text_def is not None else TextDef()
        label = seg.label or (text_def.text if text_def else '')
        return _tw_replace(base,
            x       = cx_n,
            y       = cy_n,
            px      = cx_px + base.px,
            py      = cy_px + base.py,
            text    = label,
            h_align = 0.5,
            v_align = 0.5,
            phases  = {},
        )

    result: List[ButtonDef] = []
    weight_before = 0.0
    for i, seg in enumerate(segments):
        result.append(ButtonDef(
            poly_def      = _make_poly(i, seg, weight_before),
            text_def      = _make_text(i, seg, weight_before),
            key           = seg.key,
            action        = 'set',
            event_out     = event_out,
            event_delta   = seg.event_delta,
            hold_when_set = seg.hold_when_set,
            phase_override= phase_override,
        ))
        weight_before += seg.weight

    return result


def SevenSegmentDisplay(
    p1:            P                    = P(),
    p2:            P                    = P(),
    px1:           P                    = P(),
    px2:           P                    = P(),
    event_out:     Any                  = None,
    poly_def:      Optional[PolygonDef] = None,
    gap_px:        float                = 2.0,
) -> List[ButtonDef]:

    base_poly     = poly_def or PolygonDef()
    fill_color    = base_poly.fill_color    or QColor(101,  81, 176, 120)
    outline_color = base_poly.outline_color or QColor(133, 119, 186, 255)
    outline_width    = base_poly.outline_width    if base_poly.outline_width > 0 else 1.0
    fill_zero     = QColor(fill_color.red(),    fill_color.green(),    fill_color.blue(),    0)
    out_zero      = QColor(outline_color.red(), outline_color.green(), outline_color.blue(), 0)
    set_color     = QColor(255, 0, 0, 100)
    set_outline   = QColor(255, 0, 0, 255)

    seg_events: Dict[str, EventDef] = {}
    for letter in ('a','b','c','d','e','f','g'):
        seg_events[letter] = EventDef(name=f'seg_{letter}', value=False)

    def _update_output():
        bits = ''.join('1' if seg_events[k].value else '0'
                       for k in ('g','f','e','d','c','b','a'))
        if event_out is not None:
            event_out.value = f'0b0{bits}'

    for letter in ('a','b','c','d','e','f','g'):
        seg_events[letter]._watchers.append(lambda v: _update_output())

    seg_gaps = {
        'a': ( 0, -2), 'b': (+1, -1), 'c': (+1, +1),
        'd': ( 0, +2), 'e': (-1, +1), 'f': (-1, -1),
        'g': ( 0,  0),
    }
    vertical_segs = {'b', 'c', 'e', 'f'}

    def _h_pts(cx, cy, hl, ht, gx, gy):
        g = gap_px
        return [
            P(cx - hl       + gx*g, cy          + gy*g),  # left point
            P(cx - hl + ht  + gx*g, cy - ht     + gy*g),  # top-left
            P(cx + hl - ht  + gx*g, cy - ht     + gy*g),  # top-right
            P(cx + hl       + gx*g, cy          + gy*g),  # right point
            P(cx + hl - ht  + gx*g, cy + ht     + gy*g),  # bottom-right
            P(cx - hl + ht  + gx*g, cy + ht     + gy*g),  # bottom-left
        ]

    def _v_pts(cx, cy, hl, ht, gx, gy):
        g = gap_px
        return [
            P(cx          + gx*g, cy - hl       + gy*g),  # top point
            P(cx + ht     + gx*g, cy - hl + ht  + gy*g),  # top-right
            P(cx + ht     + gx*g, cy + hl - ht  + gy*g),  # bottom-right
            P(cx          + gx*g, cy + hl        + gy*g),  # bottom point
            P(cx - ht     + gx*g, cy + hl - ht  + gy*g),  # bottom-left
            P(cx - ht     + gx*g, cy - hl + ht  + gy*g),  # top-left
        ]

    mc_xn  = (p1.x + p2.x) / 2.0
    mc_yn  = (p1.y + p2.y) / 2.0

    def _make_dynamic(letter: str):
        gx, gy  = seg_gaps[letter]
        is_vert = letter in vertical_segs

        def _dynamic(ww: int, wh: int) -> List[P]:
            x1 = p1.x * ww + px1.x
            y1 = p1.y * wh + px1.y
            x2 = p2.x * ww + px2.x
            y2 = p2.y * wh + px2.y

            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0

            hl_h = (x2 - x1) / 2.0
            ht   = (y2 - y1) / 2.0

            hl_v = hl_h

            cx_r = cx + hl_h
            cx_l = cx - hl_h

            cy_a = cy - 2.0 * hl_v
            cy_d = cy + 2.0 * hl_v
            cy_g = cy

            cy_upper = cy - hl_v   # center of b, f
            cy_lower = cy + hl_v   # center of c, e

            if letter == 'a':
                return _h_pts(cx,   cy_a,    hl_h, ht, gx, gy)
            elif letter == 'g':
                return _h_pts(cx,   cy_g,    hl_h, ht, gx, gy)
            elif letter == 'd':
                return _h_pts(cx,   cy_d,    hl_h, ht, gx, gy)
            elif letter == 'b':
                return _v_pts(cx_r, cy_upper, hl_v, ht, gx, gy)
            elif letter == 'c':
                return _v_pts(cx_r, cy_lower, hl_v, ht, gx, gy)
            elif letter == 'f':
                return _v_pts(cx_l, cy_upper, hl_v, ht, gx, gy)
            elif letter == 'e':
                return _v_pts(cx_l, cy_lower, hl_v, ht, gx, gy)
            return pts

        return _dynamic
    
    def _make_seg_poly(letter: str) -> PolygonDef:
        hover_fill, click_fill = _derive_button_colors(fill_color)
        active_fill = QColor(220, 60, 60, 255)

        p      = [P(0.0, 0.0)] * 6
        px_pts = [P(0.0, 0.0)] * 6

        merged_phases = {
            'open':    Phase([PolygonTween(fill_color=fill_zero,   outline_color=out_zero,      outline_width=outline_width, start=0, dur=0,    ease=QEasingCurve.Linear),
                              PolygonTween(fill_color=fill_color,  outline_color=outline_color, outline_width=outline_width, start=0, dur=0.25, ease=QEasingCurve.OutQuint)]),
            'close':   Phase([PolygonTween(fill_color=fill_zero,   outline_color=out_zero,      outline_width=outline_width, start=0, dur=0.25, ease=QEasingCurve.OutQuint)]),
            'hover':   Phase([PolygonTween(fill_color=hover_fill,  outline_color=outline_color, outline_width=outline_width, start=0, dur=0.25, ease=QEasingCurve.OutQuint)]),
            'unhover': Phase([PolygonTween(fill_color=fill_color,  outline_color=outline_color, outline_width=outline_width, start=0, dur=0.25, ease=QEasingCurve.OutQuint)]),
            'click':   Phase([PolygonTween(fill_color=click_fill,  outline_color=outline_color, outline_width=outline_width, start=0, dur=0.25, ease=QEasingCurve.OutQuint)]),
            'release': Phase([PolygonTween(fill_color=hover_fill,  outline_color=outline_color, outline_width=outline_width, start=0, dur=0.25, ease=QEasingCurve.OutQuint)]),
            'set':     Phase([PolygonTween(fill_color=set_color,   outline_color=set_outline,   outline_width=2.0,        start=0, dur=0.25, ease=QEasingCurve.OutQuint)]),
            **(base_poly.phases or {}),
        }

        return _tw_replace(base_poly,
            p             = p,
            px            = px_pts,
            fill_color    = fill_color,
            outline_color = outline_color,
            outline_width    = outline_width,
            closed        = True,
            phases        = merged_phases,
            dynamic_px    = _make_dynamic(letter),
        )

    result: List[ButtonDef] = []
    for letter in ('a','b','c','d','e','f','g'):
        result.append(ButtonDef(
            poly_def      = _make_seg_poly(letter),
            text_def      = None,
            key           = None,
            action        = 'cycle',
            event_out     = seg_events[letter],
            event_delta   = [False, True],
            hold_when_set = True,
        ))

    return result


# ──────────────────────── TEXTBOX DEF ────────────────────────

@dataclass
class TextboxDef:
    poly_def:         PolygonDef         = field(default_factory=PolygonDef)
    text_def:         Optional[TextDef]  = None
    event_out:        Optional[EventDef] = None
    max_length:       float              = 1.0
    max_length_px:    float              = 0.0
    clear_when_sent:  bool               = True
    exit_when_sent:   bool               = True
    override_inputs:  bool               = True
    visible_threshold_x: float = 0.0
    visible_threshold_y: float = 0.0

    def __post_init__(self):
        self._build_phases()

    def _build_phases(self):
        _dur  = 0.25
        _ease = QEasingCurve.OutQuint

        poly_phases   = dict(self.poly_def.phases or {})
        base_fill     = self.poly_def.fill_color    or QColor(101,  81, 176, 120)
        base_outline  = self.poly_def.outline_color or QColor(171, 151, 247, 255)
        base_lw       = self.poly_def.outline_width    if self.poly_def.outline_width > 0 else 1.0
        fill_zero     = QColor(base_fill.red(),    base_fill.green(),    base_fill.blue(),    0)
        outline_zero  = QColor(base_outline.red(), base_outline.green(), base_outline.blue(), 0)
        hover_fill, click_fill = _derive_button_colors(base_fill)
        click_outline = QColor(255, 255, 255, 255)

        poly_defaults = {
            'open':    Phase([
                PolygonTween(fill_color=fill_zero,   outline_color=outline_zero,  outline_width=base_lw, start=0, dur=0,    ease=QEasingCurve.Linear),
                PolygonTween(fill_color=base_fill,   outline_color=base_outline,  outline_width=base_lw, start=0, dur=_dur, ease=_ease),
            ]),
            'close':   Phase([PolygonTween(fill_color=fill_zero,   outline_color=outline_zero,  outline_width=base_lw, start=0, dur=_dur, ease=_ease)]),
            'hover':   Phase([PolygonTween(fill_color=hover_fill,  outline_color=base_outline,  outline_width=base_lw, start=0, dur=_dur, ease=_ease)]),
            'unhover': Phase([PolygonTween(fill_color=base_fill,   outline_color=base_outline,  outline_width=base_lw, start=0, dur=_dur, ease=_ease)]),
            'click': Phase([PolygonTween(fill_color=click_fill,  outline_color=click_outline, outline_width=2.0,     start=0, dur=_dur, ease=_ease)]),
        }
        for phase_name, phase in poly_defaults.items():
            if not _phase_key_exists(poly_phases, phase_name):
                poly_phases[phase_name] = phase

        self.poly_def = _tw_replace(self.poly_def,
            fill_color    = fill_zero,
            outline_color = outline_zero,
            phases        = poly_phases,
        )

        if self.text_def is not None:
            text_phases  = dict(self.text_def.phases or {})
            base_color   = self.text_def.fill_color or QColor(255, 255, 255, 255)
            text_zero    = QColor(base_color.red(), base_color.green(), base_color.blue(), 0)
            dim_color    = QColor(base_color.red(), base_color.green(), base_color.blue(), 160)

            text_defaults = {
                'open':    Phase([TextTween(fill_color=text_zero,  start=0, dur=0,    ease=QEasingCurve.Linear),
                                  TextTween(fill_color=dim_color,  start=0, dur=_dur, ease=_ease)]),
                'close':   Phase([TextTween(fill_color=text_zero,  start=0, dur=_dur, ease=_ease)]),
                'hover':   Phase([TextTween(fill_color=base_color, start=0, dur=_dur, ease=_ease)]),
                'unhover': Phase([TextTween(fill_color=dim_color,  start=0, dur=_dur, ease=_ease)]),
                'click': Phase([TextTween(fill_color=base_color, start=0, dur=_dur, ease=_ease)]),
            }
            for phase_name, phase in text_defaults.items():
                if not _phase_key_exists(text_phases, phase_name):
                    text_phases[phase_name] = phase

            self.text_def = _tw_replace(self.text_def,
                fill_color  = text_zero,
                phases = text_phases,
            )


_SHIFT_MAP: Dict[int, str] = {
    Qt.Key_1: '!', Qt.Key_2: '@', Qt.Key_3: '#', Qt.Key_4: '$', Qt.Key_5: '%',
    Qt.Key_6: '^', Qt.Key_7: '&', Qt.Key_8: '*', Qt.Key_9: '(', Qt.Key_0: ')',
    Qt.Key_Minus:        '_', Qt.Key_Equal:     '+',
    Qt.Key_BracketLeft:  '{', Qt.Key_BracketRight: '}',
    Qt.Key_Backslash:    '|', Qt.Key_Semicolon:    ':',
    Qt.Key_Apostrophe:   '"', Qt.Key_Comma:        '<',
    Qt.Key_Period:       '>', Qt.Key_Slash:         '?',
    Qt.Key_QuoteLeft:    '~',
}
_NOSHIFT_MAP: Dict[int, str] = {
    Qt.Key_Minus:        '-', Qt.Key_Equal:        '=',
    Qt.Key_BracketLeft:  '[', Qt.Key_BracketRight: ']',
    Qt.Key_Backslash:    '\\',Qt.Key_Semicolon:    ';',
    Qt.Key_Apostrophe:   "'", Qt.Key_Comma:        ',',
    Qt.Key_Period:       '.', Qt.Key_Slash:         '/',
    Qt.Key_QuoteLeft:    '`', Qt.Key_Space:         ' ',
}


class AnimatedTextbox:
    def __init__(self, defn: TextboxDef,
                 cam_w: int = MONITOR_RESOLUTIONS[0][0],
                 cam_h: int = MONITOR_RESOLUTIONS[0][1]) -> None:
        self.defn    = defn
        self.cam_w   = cam_w
        self.cam_h   = cam_h

        self._polygon    = AnimatedPolygon(defn.poly_def)
        self._text       = AnimatedText(defn.text_def) if defn.text_def else None

        self._buffer:    str  = ''
        self._active:    bool = False
        self._hovered:   bool = False
        self._cur_phase: str  = ''
        self._locked:    bool = False
        self._last_poly: QPolygonF = QPolygonF()
        self._ctrl_held: bool = False

        self._set_phase('open')

        self.hidden: bool = False

    # ── Phase ────────────────────────────────────────────────────

    def _set_phase(self, phase: str) -> None:
        if self._locked and phase not in ('open', 'close'):
            return
        self._cur_phase = phase
        self._locked    = phase in ('open', 'close')
        self._polygon.set_phase(phase)
        if self._text is not None:
            self._text.set_phase(phase)

    # ── Hit test ─────────────────────────────────────────────────

    def hit_test(self, mx: float, my: float, w: int, h: int) -> bool:
        if not self._last_poly.isEmpty():
            return self._last_poly.containsPoint(QPointF(mx, my), Qt.OddEvenFill)
        return False

    # ── Input handling ───────────────────────────────────────────

    def _send(self) -> None:
        if self.defn.event_out is not None:
            self.defn.event_out.value = self._buffer
        if self.defn.clear_when_sent:
            self._buffer = ''
        if self.defn.exit_when_sent:
            self._deactivate()

    def _deactivate(self) -> None:
        self._active = False
        self._set_phase('hover' if self._hovered else 'unhover')

    def _activate(self) -> None:
        self._active = True
        self._set_phase('click')

    def key_press(self, key: int, shift: bool = False, ctrl: bool = False) -> bool:
        if key in (Qt.Key_Control, Qt.Key_Meta):
            self._ctrl_held = True
            return self._active and self.defn.override_inputs

        if not self._active:
            return False

        if key in (Qt.Key_Return, Qt.Key_Enter):
            self._send()
            return True

        if key == Qt.Key_Escape:
            self._deactivate()
            return True

        if key == Qt.Key_Backspace:
            if ctrl or self._ctrl_held:
                s = self._buffer.rstrip(' ')
                idx = len(s)
                while idx > 0 and s[idx - 1] != ' ':
                    idx -= 1
                self._buffer = s[:idx]
            else:
                self._buffer = self._buffer[:-1]
            return True

        ch = self._resolve_char(key, shift)
        if ch is not None:
            self._buffer += ch
            return True

        return self.defn.override_inputs

    def key_release(self, key: int) -> bool:
        if key in (Qt.Key_Control, Qt.Key_Meta):
            self._ctrl_held = False
        return self._active and self.defn.override_inputs

    def _resolve_char(self, key: int, shift: bool) -> Optional[str]:
        if Qt.Key_A <= key <= Qt.Key_Z:
            ch = chr(key)
            return ch if shift else ch.lower()
        if Qt.Key_0 <= key <= Qt.Key_9:
            if shift:
                return _SHIFT_MAP.get(key)
            return chr(key)
        if 32 <= key <= 126:
            return chr(key)
        if shift and key in _SHIFT_MAP:
            return _SHIFT_MAP[key]
        if not shift and key in _NOSHIFT_MAP:
            return _NOSHIFT_MAP[key]
        return None

    # ── Mouse ────────────────────────────────────────────────────

    def mouse_press(self, mx: float, my: float, w: int, h: int) -> bool:
        if self.hit_test(mx, my, w, h):
            self._activate()
            return True
        if self._active:
            self._deactivate()
        return False

    def mouse_move(self, mx: float, my: float, w: int, h: int) -> None:
        hit = self.hit_test(mx, my, w, h)
        if hit != self._hovered:
            self._hovered = hit
            if not self._active:
                self._set_phase('hover' if hit else 'unhover')

    def mouse_release(self, mx: float, my: float, w: int, h: int) -> None:
        pass

    def _resolve_display_text(self, w: int, h: int) -> str:
        if self._text is None:
            return self._buffer
        d    = self.defn
        td   = self._text
        clip_w_n  = d.max_length  * w + d.max_length_px
        font = self._text.build_font(1.0)
        fm   = QFontMetrics(font)
        text = self._buffer
        while text and fm.horizontalAdvance(text) > clip_w_n:
            text = text[:-1]
        return text

    def update(self, widget_w: int = 0, widget_h: int = 0) -> None:
        self._polygon.update()
        if self._text is not None:
            buf = self._buffer
            self._text.defn = _tw_replace(self._text.defn, text_fn=lambda ctx, b=buf: b)
            self._text.update()
        if self._locked and self._polygon.phase_done():
            self._locked = False
        w, h = max(1, widget_w), max(1, widget_h)
        self._polygon._dirty = True
        self._last_poly = self._polygon.get_polygon(w, h, self.cam_w, self.cam_h)

    def phase_done(self) -> bool:
        text_done = self._text.phase_done() if self._text is not None else True
        return self._polygon.phase_done() and text_done

    def draw(self, painter: QPainter, w: int, h: int, scale: float = 1.0) -> None:
        if self.hidden:
            return
        self._polygon.draw(painter, w, h, self.cam_w, self.cam_h)
        if self._text is not None and not self._text.hidden:
            display = self._resolve_display_text(w, h)
            text_scale = scale if self._text.defn.uniform_scale else 1.0
            font    = self._text.build_font(text_scale)
            fm      = QFontMetrics(font)
            painter.setFont(font)
            painter.setPen(self._text.cur_color)
            dx, dy = self._text.resolve_pos(w, h, self.cam_w, self.cam_h, display, font, text_scale)
            painter.drawText(dx, dy, display)
            if self._active and int(time.monotonic() * 2) % 2 == 0:
                cursor_x = dx + fm.horizontalAdvance(display)
                cursor_y_top = dy - fm.ascent()
                cursor_y_bot = dy + fm.descent()
                pen = QPen(self._text.cur_color)
                pen.setWidthF(1.5)
                painter.setPen(pen)
                painter.drawLine(QPointF(cursor_x, cursor_y_top),
                                 QPointF(cursor_x, cursor_y_bot))
            painter.setPen(Qt.NoPen)











# ──────────────────────── GRAPH DEF ────────────────────────
 
@dataclass
class GraphDef:
    p1:              P                       = field(default_factory=P)
    p2:              P                       = field(default_factory=P)
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
    show_step:       bool                    = False
    step_count:      Any                     = 0
    size_minmax:     float                   = 10.0
    size_step:       float                   = 9.0
    label_align:     str                     = 'right'
    stack:           bool                    = False
    update_interval: float                   = 0.0
    hidden:          bool                    = False
    visible_threshold_x: float = 0.0
    visible_threshold_y: float = 0.0
 
@dataclass
class SeriesDef:
    value_fn:     Optional[Callable[[Any], Optional[float]]] = None
    data_fn:      Optional[Callable[[Any], List[float]]]     = None
    color:        QColor  = field(default_factory=lambda: QColor(255, 255, 255, 255))
    outline_width:   float   = 1.5
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
 
    def _compute_target_range(self, now: float) -> Tuple[float, float]:
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
    
    def _draw_labels(self, painter: QPainter, rx: float, ry: float, rw: float, rh: float) -> None:
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

    def draw(self, painter: QPainter, widget_w: int, widget_h: int, ctx: Any = None, cam_w: int = MONITOR_RESOLUTIONS[0][0], cam_h: int = MONITOR_RESOLUTIONS[0][1]) -> None:
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
 
            if sd.outline_width > 0.0:
                pen = QPen(sd.color)
                pen.setWidthF(sd.outline_width)
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
    p1:         P                    = field(default_factory=P)
    p2:         P                    = field(default_factory=P)
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
    visible_threshold_x: float = 0.0
    visible_threshold_y: float = 0.0

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

    def draw(self, painter: QPainter, widget_w: int, widget_h: int, cam_w: int = MONITOR_RESOLUTIONS[0][0], cam_h: int = MONITOR_RESOLUTIONS[0][1]) -> None:
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
    p1:                     P                       = field(default_factory=P)
    p2:                     P                       = field(default_factory=P)
    px1:                    P                       = field(default_factory=P)
    px2:                    P                       = field(default_factory=P)
    force_open:             bool                    = False
    force_close:            bool                    = False
    phase_event:            Any                     = None
    phase_fn:               Optional[Callable[str]] = None
    phases:                 Dict[str, Phase]        = field(default_factory=dict)
    listener_defs:          List[EventListener]     = field(default_factory=list)
    polygon_defs:           List[PolygonDef]        = field(default_factory=list)
    arc_defs:               List[ArcDef]            = field(default_factory=list)
    text_defs:              List[TextDef]           = field(default_factory=list)
    graph_defs:             List[GraphDef]          = field(default_factory=list)
    pie_defs:               List[PieDef]            = field(default_factory=list)
    slider_defs:            List[SliderGroupDef]    = field(default_factory=list)
    button_defs:            List[ButtonDef]         = field(default_factory=list)
    textbox_defs:           List[TextboxDef]        = field(default_factory=list)
    sub_windows:            List['WindowDef']       = field(default_factory=list)
    use_parent_close_phase: bool                    = True
    draggable:              bool                    = False
    drag_boundary_p1:       P                       = field(default_factory=P)
    drag_boundary_p2:       P                       = field(default_factory=lambda: P(1.0, 1.0))
    scalable:               bool                    = False
    min_scale_w:            float                   = 0.05
    min_scale_h:            float                   = 0.05
    scale_edge_px:          float                   = 8.0
    grid_snap:              bool                    = True
    grid_snap_x:            int                     = 19
    grid_snap_y:            int                     = 11
    spawn_event:            Optional[EventDef]      = None
    spawn_static_values:    List[Any]               = field(default_factory=list)
    spawn_event_group:      Optional[str]           = None
    spawn_tick_increment:   bool                    = False
    spawn_delete_threshold: int                     = 1
    spawn_limit:            int                     = 100

@dataclass
class WindowTween:
    p1:   Optional[P]          = None
    p2:   Optional[P]          = None
    px1:  P                    = field(default_factory=P)
    px2:  P                    = field(default_factory=P)
    start: float               = 0.0
    dur:   float               = 0.5
    ease:  QEasingCurve.Type   = QEasingCurve.OutQuint
    prev_phase: Optional[str]  = None

class AnimatedWindow:
    def __init__(self, defn: WindowDef, cam_w: int = MONITOR_RESOLUTIONS[0][0], cam_h: int = MONITOR_RESOLUTIONS[0][1]) -> None:
        self.defn   = defn
        self.cam_w  = cam_w
        self.cam_h  = cam_h

        self._sub_windows: List[AnimatedWindow] = [AnimatedWindow(d, cam_w, cam_h) for d in defn.sub_windows]
        self._polygons  = [AnimatedPolygon(d) for d in defn.polygon_defs]
        self._arcs      = [AnimatedArc(d)     for d in defn.arc_defs]
        self._texts     = [AnimatedText(d)    for d in defn.text_defs]
        self._graphs    = [AnimatedGraph(d)   for d in defn.graph_defs]
        self._pies      = [AnimatedPie(d)     for d in defn.pie_defs]
        self._sliders   = [SliderGroup(d, cam_w, cam_h) for d in defn.slider_defs]
        self._buttons   = [AnimatedButton(d, cam_w, cam_h) for d in defn.button_defs]
        self._textboxes = [AnimatedTextbox(d, cam_w, cam_h) for d in defn.textbox_defs]
        self._listeners = list(defn.listener_defs)

        self._btn_grid: Dict[tuple, List[int]] = {}
        self._btn_bounds: List[Optional[tuple]] = [None] * len(self._buttons)
        self._grid_cell_size: int = 64
        self._grid_w: int = 0
        self._grid_h: int = 0
        self._last_mouse_lx: float = -1.0
        self._last_mouse_ly: float = -1.0

        self._held_keys: set = set()

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
        self._parent_w: int = 0
        self._parent_h: int = 0

        for sl in self._sliders:
            sl.init_value(None)
        self._broadcast('open')

        if defn.phase_event is not None and defn.phase_event is not GROUP_EVENT:
            if isinstance(defn.phase_event, (list, tuple)):
                if not defn.phase_event[0].value:
                    defn.phase_event[0].value = 'open'
            else:
                if not defn.phase_event.value:
                    defn.phase_event.value = 'open'

        self._last_mouse_lx: float = -1.0
        self._last_mouse_ly: float = -1.0

        self._sys_fps_event:        Optional[EventDef] = None
        self._sys_mouse_event:      Optional[EventDef] = None
        self._sys_frame_time_event: Optional[EventDef] = None

        self._fps_samples:    collections.deque = collections.deque(maxlen=60)
        self._last_frame_time: float = 0.0

        self._dragging_window:  bool  = False
        self._drag_start_mx:    float = 0.0
        self._drag_start_my:    float = 0.0
        self._drag_start_p1x:   float = 0.0
        self._drag_start_p1y:   float = 0.0
        self._drag_start_px1x:  float = 0.0
        self._drag_start_px1y:  float = 0.0
        self._drag_start_p2x:   float = 0.0
        self._drag_start_p2y:   float = 0.0
        self._drag_start_px2x:  float = 0.0
        self._drag_start_px2y:  float = 0.0
        self._drag_parent_w: int = 0
        self._drag_parent_h: int = 0

        self._scaling_window:   bool  = False
        self._scale_edge:       str   = ''   # 'l', 'r', 't', 'b', 'tl', 'tr', 'bl', 'br'
        self._scale_start_mx:   float = 0.0
        self._scale_start_my:   float = 0.0
        self._scale_start_p1x:  float = 0.0
        self._scale_start_p1y:  float = 0.0
        self._scale_start_px1x: float = 0.0
        self._scale_start_px1y: float = 0.0
        self._scale_start_p2x:  float = 0.0
        self._scale_start_p2y:  float = 0.0
        self._scale_start_px2x: float = 0.0
        self._scale_start_px2y: float = 0.0

        self._snap_tween_active:  bool  = False
        self._snap_tween_t0:      float = 0.0
        self._snap_tween_dur:     float = 0.5
        self._snap_from_p1x:      float = 0.0
        self._snap_from_p1y:      float = 0.0
        self._snap_from_p2x:      float = 0.0
        self._snap_from_p2y:      float = 0.0
        self._snap_to_p1x:        float = 0.0
        self._snap_to_p1y:        float = 0.0
        self._snap_to_p2x:        float = 0.0
        self._snap_to_p2y:        float = 0.0

        self._spawned:          List[_SpawnedInstance] = []
        self._last_ipw:         int   = 0
        self._last_iph:         int   = 0
        self._spawn_watched:    bool  = False

        if defn.spawn_event is not None:
            self.hidden = True
        else:
            self.hidden = False

        if defn.spawn_event is not None:
            defn.spawn_event._watchers.append(self._on_spawn_trigger)

        self._group_event:          Optional[EventDef] = None
        self._instance_phase_event: Optional[EventDef] = None
        self._statics: List[Any] = []

        self._last_screen_wx: float = 0.0
        self._last_screen_wy: float = 0.0
        self._last_screen_ww: float = 0.0
        self._last_screen_wh: float = 0.0

        self._force_open_active:  bool = False
        self._force_close_active: bool = False
        self._prev_force_phase:   str  = ''

        if defn.spawn_event is None:
            self._broadcast('open')
        else:
            self.hidden = True

    def _screen_rect(self, ww: int, wh: int) -> Tuple[float, float, float, float]:
        x1 = self._cur_p1.x  * ww + self._cur_px1.x
        y1 = self._cur_p1.y  * wh + self._cur_px1.y
        x2 = self._cur_p2.x  * ww + self._cur_px2.x
        y2 = self._cur_p2.y  * wh + self._cur_px2.y
        return x1, y1, x2 - x1, y2 - y1

    def _broadcast(self, phase: str) -> None:
        prev = self._cur_phase
        self._cur_phase = phase
        for p, pd in zip(self._polygons, self.defn.polygon_defs):
            if pd.phase_override is None:
                p.set_phase(phase)
        for t, td in zip(self._texts, self.defn.text_defs):
            if td.phase_override is None:
                t.set_phase(phase)
        for sl  in self._sliders:  sl.set_phase(phase)
        for btn, bd in zip(self._buttons, self.defn.button_defs):
            if bd.phase_override is None:
                btn._set_phase(phase)
        for tb in self._textboxes:
            tb._set_phase(phase)
        for gd in _gradients.values():
            if gd.phase_event is None:
                gd._animated.set_phase(phase)
        for sw in self._sub_windows:
            if sw.defn.spawn_event is not None:
                continue
            if not _phase_key_exists(sw.defn.phases, phase):
                sw._broadcast(phase)
        wp = self.defn.phases.get(phase)
        if wp:
            self._win_tweens = [tw for tw in wp.tweens
                                if tw.prev_phase is None or tw.prev_phase == prev]
        else:
            self._win_tweens = []
        self._win_idx        = 0
        self._win_prev_phase = prev
        self._s_p1  = self._cur_p1;  self._s_p2  = self._cur_p2
        self._s_px1 = self._cur_px1; self._s_px2 = self._cur_px2
        self._win_timer.restart()
    
    def _rebuild_btn_grid(self, ww: int, wh: int) -> None:
        cell = self._grid_cell_size
        self._btn_grid.clear()
        self._grid_w = ww
        self._grid_h = wh

        for i, btn in enumerate(self._buttons):
            poly = btn._last_poly
            if poly is None or poly.isEmpty():
                self._btn_bounds[i] = None
                continue

            xs = [pt.x() for pt in poly]
            ys = [pt.y() for pt in poly]
            x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
            self._btn_bounds[i] = (x1, y1, x2, y2)

            cx0 = int(x1 // cell)
            cy0 = int(y1 // cell)
            cx1 = int(x2 // cell)
            cy1 = int(y2 // cell)
            for cx in range(cx0, cx1 + 1):
                for cy in range(cy0, cy1 + 1):
                    key = (cx, cy)
                    if key not in self._btn_grid:
                        self._btn_grid[key] = []
                    if i not in self._btn_grid[key]:
                        self._btn_grid[key].append(i)
    
    def _btn_candidates(self, lx: float, ly: float) -> List[int]:
        cell = self._grid_cell_size
        key  = (int(lx // cell), int(ly // cell))
        return self._btn_grid.get(key, [])

    def _poll_phase_event(self) -> None:
        ev = self._instance_phase_event or self.defn.phase_event
        if ev is None:
            return
        fn = self.defn.phase_fn
        if isinstance(ev, (list, tuple)):
            result = fn(*[e.value for e in ev]) if fn else str(ev[0].value)
        else:
            result = fn(ev.value) if fn else str(ev.value)
        if result is None:
            result = str(ev.value) if not isinstance(ev, (list,tuple)) else str(ev[0].value)
        if result != self._cur_phase:
            self._broadcast(result)
    
    def _poll_force_phases(self) -> None:
        d = self.defn
        phase = self._cur_phase

        if d.force_open and phase == 'open' and not self._force_open_active and self._prev_force_phase != 'open':
            self._force_open_active = True
            for p in self._polygons: p.set_phase('open')
            for t in self._texts:    t.set_phase('open')
            for a in self._arcs:     a.set_phase('open')

        if d.force_close and phase == 'close' and not self._force_close_active and self._prev_force_phase != 'close':
            self._force_close_active = True
            for p in self._polygons: p.set_phase('close')
            for t in self._texts:    t.set_phase('close')
            for a in self._arcs:     a.set_phase('close')

        self._prev_force_phase = phase

        if self._force_open_active:
            if all(p.phase_done() for p in self._polygons) and all(t.phase_done() for t in self._texts):
                self._force_open_active = False

        if self._force_close_active:
            if all(p.phase_done() for p in self._polygons) and all(t.phase_done() for t in self._texts):
                self._force_close_active = False

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
        if tw.p1 is not None:
            self._cur_p1  = P(self._s_p1.x  + (tw.p1.x  - self._s_p1.x)  * v, self._s_p1.y  + (tw.p1.y  - self._s_p1.y)  * v)
        if tw.p2 is not None:
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
        if self.hidden: return
        self._poll_phase_event()
        if self._snap_tween_active:
            elapsed = now - self._snap_tween_t0
            dur     = self._snap_tween_dur
            if elapsed >= dur:
                self._cur_p1  = P(self._snap_to_p1x, self._snap_to_p1y)
                self._cur_p2  = P(self._snap_to_p2x, self._snap_to_p2y)
                self._snap_tween_active = False
            else:
                v = 1.0 - (1.0 - elapsed / dur) ** 5
                self._cur_p1 = P(
                    self._snap_from_p1x + (self._snap_to_p1x - self._snap_from_p1x) * v,
                    self._snap_from_p1y + (self._snap_to_p1y - self._snap_from_p1y) * v,
                )
                self._cur_p2 = P(
                    self._snap_from_p2x + (self._snap_to_p2x - self._snap_from_p2x) * v,
                    self._snap_from_p2y + (self._snap_to_p2y - self._snap_from_p2y) * v,
                )
        if self._cur_phase == 'close' and self._is_done():
            self._last_frame_time = now
            return
        self._tick_win_tweens()
        self._tick_spawn(None, 
                        self._last_ipw if self._last_ipw > 0 else self.cam_w,
                        self._last_iph if self._last_iph > 0 else self.cam_h,
                        now)
        for g in self._graphs:
            g.tick(now)
        for sw in self._sub_windows:
            if sw.defn.spawn_event is None:
                sw.tick(now)
        if self._last_frame_time > 0.0:
            dt = now - self._last_frame_time
            self._fps_samples.append(dt)
            avg_dt = sum(self._fps_samples) / len(self._fps_samples)
            SYS_FPS.value        = round(1.0 / avg_dt if avg_dt > 0 else 0.0, 1)
            SYS_FRAME_TIME.value = round(avg_dt * 1000.0, 2)
        self._last_frame_time = now

    def update(self, ctx, widget_w, widget_h, _parent_abs_x=0.0, _parent_abs_y=0.0):
        if self.hidden: return
        for ev in _pending_pulse_resets:
            ev.value = 'ignore'
        _pending_pulse_resets.clear()
        wx, wy, ww, wh = self._screen_rect(widget_w, widget_h)
        self._abs_wx = _parent_abs_x + wx
        self._abs_wy = _parent_abs_y + wy
        self._abs_ww = ww
        self._abs_wh = wh
        ipw, iph = int(ww), int(wh)
        self._last_ipw = ipw
        self._last_iph = iph

        if self._cur_phase == 'close' and self._is_done():
            return

        if ww > 0 and wh > 0:
            mx = SYS_MOUSE_X.value
            my = SYS_MOUSE_Y.value
            _window_mouse_norm[id(self.defn)] = P(
                (mx - wx) / ww,
                (my - wy) / wh,
            )

        _pulse_resets: List[EventDef] = []
        
        # Listeners
        for gl in self._listeners:
            for target in gl.targets:
                if isinstance(target, EventDef) and target.value == 'ignore':
                    target.value = 'ignore'
        for gl in self._listeners:
            gl.tick(ctx)

        # Polygons
        for p, pd in zip(self._polygons, self.defn.polygon_defs):
            visible = _check_visible_threshold(pd, ww, wh, self.cam_w, self.cam_h)
            p.hidden = not visible
            if not visible:
                continue
            ov = pd.phase_override
            if ov is not None:
                phase = ov() if callable(ov) else str(ov.value) if hasattr(ov, 'value') else str(ov)
                phase = str(phase) if phase is not None else ''
                if phase == 'pulse':
                    if _phase_key_exists(pd.phases or {}, 'pulse'):
                        p.set_phase('pulse')
                    if hasattr(ov, 'value') and ov not in _pulse_resets:
                        _pulse_resets.append(ov)
                elif phase and phase != p._phase:
                    if _phase_key_exists(pd.phases or {}, phase):
                        p.set_phase(phase)
            p.update()

        # Arc
        for arc, ad in zip(self._arcs, self.defn.arc_defs):
            arc.hidden = not _check_visible_threshold(ad, ww, wh, self.cam_w, self.cam_h)
        
        # Text
        for t, td in zip(self._texts, self.defn.text_defs):
            visible = _check_visible_threshold(td, ww, wh, self.cam_w, self.cam_h)
            t.hidden = not visible
            if not visible:
                continue
            ov = td.phase_override
            if ov is not None:
                phase = ov() if callable(ov) else str(ov.value) if hasattr(ov, 'value') else str(ov)
                phase = str(phase) if phase is not None else ''
                if phase == 'pulse':
                    if _phase_key_exists(td.phases or {}, 'pulse'):
                        t.set_phase('pulse')
                    if hasattr(ov, 'value') and ov not in _pulse_resets:
                        _pulse_resets.append(ov)
                elif phase and phase != t._phase:
                    if _phase_key_exists(td.phases or {}, phase):
                        t.set_phase(phase)
            t.update()
        
        # Pie
        for pie, pd in zip(self._pies, self.defn.pie_defs):
            pie.hidden = not _check_visible_threshold(pd, ww, wh, self.cam_w, self.cam_h)

        # Graphs
        for g, gd in zip(self._graphs, self.defn.graph_defs):
            g.hidden = not _check_visible_threshold(gd, ww, wh, self.cam_w, self.cam_h)

        # Slider        
        wx, wy, ww, wh = self._screen_rect(widget_w, widget_h)
        for sl, sd in zip(self._sliders, self.defn.slider_defs):
            sl.hidden = not _check_visible_threshold(sd, ww, wh, self.cam_w, self.cam_h)
            sl.update(int(ww), int(wh))
        
        # Button
        for btn, bd in zip(self._buttons, self.defn.button_defs):
            btn._polygon.hidden = not _check_visible_threshold(bd, ww, wh, self.cam_w, self.cam_h)
            ov = bd.phase_override
            if ov is not None:
                phase = ov() if callable(ov) else str(ov.value) if hasattr(ov, 'value') else str(ov)
                phase = str(phase) if phase is not None else ''
                if phase == 'pulse':
                    if _phase_key_exists(bd.poly_def.phases or {}, 'pulse'):
                        btn._set_phase('pulse')
                    if hasattr(ov, 'value') and ov not in _pulse_resets:
                        _pulse_resets.append(ov)
                elif phase != btn._last_override_phase:
                    if _phase_key_exists(bd.poly_def.phases or {}, phase):
                        btn._last_override_phase = phase
                        btn._set_phase(phase)
            btn.update(int(ww), int(wh))
        
        # Textbox
        for tb, tbd in zip(self._textboxes, self.defn.textbox_defs):
            tb.hidden = not _check_visible_threshold(tbd, ww, wh, self.cam_w, self.cam_h)
            tb.update(int(ww), int(wh))
        wx, wy, ww, wh = self._screen_rect(widget_w, widget_h)
        ipw, iph = int(ww), int(wh)

        # Gradient
        for gd in _gradients.values():
            gd._animated.update()

        # Window
        for sw in self._sub_windows:
            if sw.defn.spawn_event is not None: continue
            sw.update(ctx, ipw, iph, _parent_abs_x=self._abs_wx, _parent_abs_y=self._abs_wy)
        
        wx, wy, ww, wh = self._screen_rect(widget_w, widget_h)
        ipw, iph = int(ww), int(wh)
        self._last_ipw = ipw
        self._last_iph = iph

        for inst in self._spawned:
            inst.window.update(ctx, ipw, iph, _parent_abs_x=self._abs_wx, _parent_abs_y=self._abs_wy)

        
        # for ev in _pulse_resets:
        #     print(f'resetting {ev.name}, id={id(ev)}, was={ev.value}')
        #     ev.value = 'ignore'
        # _pulse_resets.clear()
    
    def draw(self, painter, widget_w, widget_h, ctx=None):
        if self._cur_phase == 'close' and self._is_done():
            return
        wx, wy, ww, wh = self._screen_rect(widget_w, widget_h)
        if ww <= 0 or wh <= 0:
            return
        scale = min(ww / self.cam_w, wh / self.cam_h)
        painter.save()
        painter.translate(wx, wy)
        painter.setClipRect(QRectF(0, 0, ww, wh))
        iww, iwh = int(ww), int(wh)

        for poly in self._polygons:
            poly.draw(painter, iww, iwh, self.cam_w, self.cam_h)
        for arc in self._arcs:
            arc.draw(painter, iww, iwh)
        for text in self._texts:
            if text.hidden: continue
            text.draw_text(painter, iww, iwh, self.cam_w, self.cam_h, ctx, scale=scale)
        for g in self._graphs:
            g.draw(painter, iww, iwh, ctx, self.cam_w, self.cam_h)
        for pie in self._pies:
            pie.draw(painter, iww, iwh, self.cam_w, self.cam_h)
        for sl in self._sliders:
            sl.draw(painter, iww, iwh, scale=scale)
        for btn in self._buttons:
            btn.draw(painter, iww, iwh, scale=scale)
        for tb in self._textboxes:
            tb.draw(painter, iww, iwh, scale=scale)

        for sw in self._sub_windows:
            if sw.defn.spawn_event is not None:
                continue
            sw.draw(painter, iww, iwh, ctx)
        for inst in self._spawned:
            inst.window.draw(painter, iww, iwh, ctx)

        painter.restore()

    def _to_local(self, mx: float, my: float, widget_w: int, widget_h: int) -> Tuple[float, float, float, float]:
        wx, wy, ww, wh = self._screen_rect(widget_w, widget_h)
        return mx - wx, my - wy, ww, wh
    
    def mouse_press(self, mx: float, my: float, widget_w: int, widget_h: int) -> bool:
        wx, wy, ww, wh = self._screen_rect(widget_w, widget_h)
        ipw, iph = int(ww), int(wh)
        for inst in reversed(self._spawned):
            if inst.window.mouse_press(mx - wx, my - wy, ipw, iph):
                return True
        for sw in self._sub_windows:
            sw._parent_w = ipw
            sw._parent_h = iph
        for sw in reversed(self._sub_windows):
            if sw.mouse_press(mx - wx, my - wy, ipw, iph):
                return True

        lx = mx - wx
        ly = my - wy

        hit_interactive = False
        for tb in self._textboxes:
            if tb.hit_test(lx, ly, ipw, iph):
                hit_interactive = True; break
        if not hit_interactive:
            for sl in self._sliders:
                if sl.hit_test_knob(lx, ly, ipw, iph):
                    hit_interactive = True; break
        if not hit_interactive:
            for btn in self._buttons:
                if btn.hit_test(lx, ly, ipw, iph):
                    hit_interactive = True; break

        inside = (0 <= lx <= ipw and 0 <= ly <= iph)

        if self.defn.scalable and not hit_interactive and inside:
            edge = self._detect_edge(lx, ly, ipw, iph)
            if edge:
                self._scaling_window    = True
                self._scale_edge        = edge
                self._scale_start_mx    = mx
                self._scale_start_my    = my
                self._scale_start_p1x   = self._cur_p1.x
                self._scale_start_p1y   = self._cur_p1.y
                self._scale_start_px1x  = self._cur_px1.x
                self._scale_start_px1y  = self._cur_px1.y
                self._scale_start_p2x   = self._cur_p2.x
                self._scale_start_p2y   = self._cur_p2.y
                self._scale_start_px2x  = self._cur_px2.x
                self._scale_start_px2y  = self._cur_px2.y
                self._cancel_active_phases()
                return True

        if self.defn.draggable and not hit_interactive and inside:
            self._dragging_window    = True
            self._drag_start_mx      = mx
            self._drag_start_my      = my
            self._drag_start_p1x     = self._cur_p1.x
            self._drag_start_p1y     = self._cur_p1.y
            self._drag_start_px1x    = self._cur_px1.x
            self._drag_start_px1y    = self._cur_px1.y
            self._drag_start_p2x     = self._cur_p2.x
            self._drag_start_p2y     = self._cur_p2.y
            self._drag_start_px2x    = self._cur_px2.x
            self._drag_start_px2y    = self._cur_px2.y
            self._cancel_active_phases()
            return True

        for tb in self._textboxes:
            tb.mouse_press(lx, ly, ipw, iph)
        for sl in self._sliders:
            if sl.hit_test_knob(lx, ly, ipw, iph):
                self._dragging_slider = sl
                sl._dragging = True
                sl.drag_to(lx, ly, ipw, iph)
                sl.commit(None)
                sl.set_phase('pressed')
                return True
        for btn in self._buttons:
            if btn.hit_test(lx, ly, ipw, iph):
                if not btn._mandatory_keys_held(self._held_keys):
                    continue
                btn._pressed    = True
                btn._press_poly = QPolygonF(btn._last_poly)
                btn._set_phase('click')
                return True
        return False

    def mouse_move(self, mx, my, widget_w, widget_h):
        SYS_MOUSE.value   = (mx, my)
        SYS_MOUSE_X.value = mx
        SYS_MOUSE_Y.value = my

        pw = self._parent_w if self._parent_w > 0 else widget_w
        ph = self._parent_h if self._parent_h > 0 else widget_h

        if self._scaling_window:
            dx_n = (mx - self._scale_start_mx) / pw
            dy_n = (my - self._scale_start_my) / ph
            e    = self._scale_edge
            d    = self.defn

            new_p1x  = self._scale_start_p1x
            new_p1y  = self._scale_start_p1y
            new_p2x  = self._scale_start_p2x
            new_p2y  = self._scale_start_p2y

            if 'l' in e:
                new_p1x = min(self._scale_start_p1x + dx_n,
                            self._scale_start_p2x - d.min_scale_w)
            if 'r' in e:
                new_p2x = max(self._scale_start_p2x + dx_n,
                            self._scale_start_p1x + d.min_scale_w)
            if 't' in e:
                new_p1y = min(self._scale_start_p1y + dy_n,
                            self._scale_start_p2y - d.min_scale_h)
            if 'b' in e:
                new_p2y = max(self._scale_start_p2y + dy_n,
                            self._scale_start_p1y + d.min_scale_h)

            bx1 = d.drag_boundary_p1.x
            by1 = d.drag_boundary_p1.y
            bx2 = d.drag_boundary_p2.x
            by2 = d.drag_boundary_p2.y
            new_p1x = max(bx1, new_p1x)
            new_p1y = max(by1, new_p1y)
            new_p2x = min(bx2, new_p2x)
            new_p2y = min(by2, new_p2y)

            if new_p2x - new_p1x < d.min_scale_w:
                if 'l' in e: new_p1x = new_p2x - d.min_scale_w
                else:         new_p2x = new_p1x + d.min_scale_w
            if new_p2y - new_p1y < d.min_scale_h:
                if 't' in e: new_p1y = new_p2y - d.min_scale_h
                else:         new_p2y = new_p1y + d.min_scale_h

            self._cur_p1  = P(new_p1x, new_p1y)
            self._cur_p2  = P(new_p2x, new_p2y)
            self._cur_px1 = P(self._scale_start_px1x, self._scale_start_px1y)
            self._cur_px2 = P(self._scale_start_px2x, self._scale_start_px2y)
            return True

        if self._dragging_window:
            dx_n = (mx - self._drag_start_mx) / pw
            dy_n = (my - self._drag_start_my) / ph
            self._cur_p1  = P(self._drag_start_p1x  + dx_n, self._drag_start_p1y  + dy_n)
            self._cur_p2  = P(self._drag_start_p2x  + dx_n, self._drag_start_p2y  + dy_n)
            self._cur_px1 = P(self._drag_start_px1x,         self._drag_start_px1y)
            self._cur_px2 = P(self._drag_start_px2x,         self._drag_start_px2y)
            self._clamp_to_boundary(pw, ph)
            return True

        wx, wy, ww, wh = self._screen_rect(widget_w, widget_h)
        ipw, iph = int(ww), int(wh)
        for inst in reversed(self._spawned):
            inst.window.mouse_move(mx - wx, my - wy, ipw, iph)
        for sw in self._sub_windows:
            sw._parent_w = ipw
            sw._parent_h = iph
        for sw in reversed(self._sub_windows):
            sw.mouse_move(mx - wx, my - wy, ipw, iph)

        lx = mx - wx
        ly = my - wy
        if self._dragging_slider is not None:
            self._dragging_slider.drag_to(lx, ly, ipw, iph)
            self._dragging_slider.commit(None)
            return True
        for tb in self._textboxes:
            tb.mouse_move(lx, ly, ipw, iph)
        for sl in self._sliders:
            hit = sl.hit_test_knob(lx, ly, ipw, iph)
            if hit != sl._hovered:
                sl._hovered = hit
                sl.set_phase('hovered' if hit else 'unhovered')
        for btn in self._buttons:
            hit = btn.hit_test(lx, ly, ipw, iph)
            if hit != btn._hovered:
                btn._hovered = hit
                btn._set_phase('hover' if hit else 'unhover')
            if not hit and btn._pressed and not btn._key_held:
                btn.mouse_left_hitbox()
        return False

    def mouse_release(self, mx: float, my: float, widget_w: int, widget_h: int) -> bool:
        if self._scaling_window:
            self._scaling_window = False
            self._scale_edge     = ''
            self._start_snap_tween(time.monotonic())
            return True

        if self._dragging_window:
            self._dragging_window = False
            self._start_snap_tween(time.monotonic())
            return True

        wx, wy, ww, wh = self._screen_rect(widget_w, widget_h)
        ipw, iph = int(ww), int(wh)
        for inst in reversed(self._spawned):
            if inst.window.mouse_release(mx - wx, my - wy, ipw, iph):
                return True
        for sw in reversed(self._sub_windows):
            if sw.mouse_release(mx - wx, my - wy, ipw, iph):
                return True

        lx, ly, _, _ = self._to_local(mx, my, widget_w, widget_h)
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
                btn._set_phase('release')
                if not btn.defn.continuous_update:
                    if btn._hit_test_press_poly(lx, ly):
                        btn.fire_event()
                        btn._check_held()
                if not btn._held:
                    QTimer.singleShot(250, lambda b=btn: b._set_phase('hover' if b._hovered else 'unhover'))
                return True
        return False
        
    def key_press(self, key: int) -> bool:
        self._held_keys.add(key)
        mods  = QApplication.keyboardModifiers()
        shift = bool(mods & Qt.ShiftModifier)
        ctrl  = bool(mods & Qt.ControlModifier)
        consumed = False
        for inst in reversed(self._spawned):
            if inst.window.key_press(key):
                consumed = True
        for sw in reversed(self._sub_windows):
            if sw.defn.spawn_event is not None: continue
            if sw.key_press(key):
                consumed = True
        for tb in self._textboxes:
            if tb._active:
                if tb.key_press(key, shift=shift, ctrl=ctrl):
                    if tb.defn.override_inputs:
                        return True
                    consumed = True
        for btn in self._buttons:
            if btn.key_press(key, self._held_keys):
                consumed = True
        return consumed

    def key_release(self, key: int) -> bool:
        self._held_keys.discard(key)
        consumed = False
        for inst in reversed(self._spawned):
            if inst.window.key_release(key):
                consumed = True
        for sw in reversed(self._sub_windows):
            if sw.defn.spawn_event is not None: continue
            if sw.key_release(key):
                consumed = True
        for tb in self._textboxes:
            if tb.key_release(key):
                if tb.defn.override_inputs:
                    return True
                consumed = True
        for btn in self._buttons:
            if btn.key_release(key, self._held_keys):
                consumed = True
        return consumed
            
    def mouse_leave(self) -> None:
        for sl in self._sliders:
            if sl._hovered:
                sl._hovered = False
                sl.set_phase('unhover')
        for btn in self._buttons:
            if btn._hovered:
                btn._hovered = False
                btn._set_phase('unhover')
    
    def _snap_to_grid(self, p1x: float, p1y: float, p2x: float, p2y: float) -> Tuple[float, float, float, float]:
        d = self.defn
        gx, gy = max(1, d.grid_snap_x), max(1, d.grid_snap_y)
        step_x = 1.0 / gx
        step_y = 1.0 / gy
        s_p1x = round(p1x / step_x) * step_x
        s_p1y = round(p1y / step_y) * step_y
        s_p2x = round(p2x / step_x) * step_x
        s_p2y = round(p2y / step_y) * step_y
        if s_p2x <= s_p1x: s_p2x = s_p1x + step_x
        if s_p2y <= s_p1y: s_p2y = s_p1y + step_y
        return s_p1x, s_p1y, s_p2x, s_p2y
    
    def _start_snap_tween(self, now: float) -> None:
        d = self.defn
        if not d.grid_snap or (d.grid_snap_x <= 1 and d.grid_snap_y <= 1):
            return
        s_p1x, s_p1y, s_p2x, s_p2y = self._snap_to_grid(self._cur_p1.x, self._cur_p1.y, self._cur_p2.x, self._cur_p2.y)
        if (s_p1x == self._cur_p1.x and s_p1y == self._cur_p1.y and s_p2x == self._cur_p2.x and s_p2y == self._cur_p2.y):
            return
        self._snap_from_p1x = self._cur_p1.x
        self._snap_from_p1y = self._cur_p1.y
        self._snap_from_p2x = self._cur_p2.x
        self._snap_from_p2y = self._cur_p2.y
        self._snap_to_p1x   = s_p1x
        self._snap_to_p1y   = s_p1y
        self._snap_to_p2x   = s_p2x
        self._snap_to_p2y   = s_p2y
        self._snap_tween_t0     = now
        self._snap_tween_active = True

    def _on_spawn_trigger(self, value) -> None:
        pass

    def _tick_spawn(self, ctx: Any, widget_w: int, widget_h: int, now: float) -> None:
        d = self.defn

        for wdef in d.sub_windows:
            if wdef.spawn_event is None:
                continue
            ev = wdef.spawn_event
            if ev.value is True or ev.value == True:
                ev.value = False
                active = [s for s in self._spawned
                        if s.window.defn is wdef]
                if len(active) >= wdef.spawn_limit:
                    continue
                self._do_spawn(wdef, widget_w, widget_h)

        wx, wy, ww, wh = self._screen_rect(widget_w, widget_h)
        ipw, iph = int(ww), int(wh)
        to_remove = []
        for inst in self._spawned:
            sw   = inst.window
            dev  = inst.group_event
            wdef = sw.defn

            if wdef.use_parent_close_phase and self._cur_phase == 'close':
                if sw._cur_phase != 'close':
                    sw._broadcast('close')
                    inst.closing = True

            if not inst.closing:
                try:
                    cur_val = int(float(dev.value))
                except (TypeError, ValueError):
                    cur_val = 0
                if cur_val >= wdef.spawn_delete_threshold:
                    inst.closing = True
                    if _phase_key_exists(wdef.phases, 'close'):
                        sw._broadcast('close')
                    else:
                        to_remove.append(inst)
            else:
                if sw._cur_phase == 'close' and sw._is_done():
                    to_remove.append(inst)
                elif sw._cur_phase != 'close':
                    to_remove.append(inst)

            sw.tick(now)

        for inst in to_remove:
            self._remove_spawn(inst)

    def _do_spawn(self, wdef: WindowDef, widget_w: int, widget_h: int) -> _SpawnedInstance:
        global _current_spawn_window
        _current_spawn_window = self

        group = wdef.spawn_event_group or ''

        if wdef.spawn_tick_increment and group:
            for inst in self._spawned:
                if inst.window.defn is wdef:
                    inst.group_event.value = int(inst.group_event.value) + 1

        group_ev = _alloc_group_event(group) if group else EventDef(name='_anon', value=0)

        statics: List[Any] = []
        for entry in wdef.spawn_static_values:
            if isinstance(entry, EventDef):
                statics.append(entry.value)
            elif callable(entry):
                try:    statics.append(entry())
                except: statics.append(None)
            else:
                statics.append(entry)

        _current_spawn_window = None

        sw        = AnimatedWindow(wdef, self.cam_w, self.cam_h)
        sw.hidden = False
        sw._group_event = group_ev
        sw._statics     = statics

        if wdef.phase_event is GROUP_EVENT:
            sw._instance_phase_event = group_ev

        def _resolve(val):
            if isinstance(val, _StaticRef):
                idx = val.index
                return statics[idx] if idx < len(statics) else None
            if val is GROUP_EVENT:
                return group_ev
            return val

        def _resolve_p(p: P) -> P:
            if not isinstance(p, P):
                return p
            x = statics[p.x.index] if isinstance(p.x, _StaticRef) else p.x
            y = statics[p.y.index] if isinstance(p.y, _StaticRef) else p.y
            return P(x if x is not None else 0.0,
                    y if y is not None else 0.0)

        def _patch_pos_fn(fn):
            if fn is None:
                return None
            try:
                defaults = fn.__defaults__ or ()
                if any(isinstance(df, _StaticRef) for df in defaults):
                    resolved = tuple(
                        statics[df.index] if isinstance(df, _StaticRef) else df
                        for df in defaults
                    )
                    return _patch_fn_defaults(fn, resolved)
            except Exception as e:
                print(f'[pos_fn] error: {e}')
            return fn

        for poly in sw._polygons:
            d = poly.defn

            new_pts     = [_resolve_p(p) for p in d.p]
            new_px      = [_resolve_p(p) for p in d.px] if d.px else None
            new_fill    = _resolve(d.fill_color)
            new_outline = _resolve(d.outline_color)
            new_pos_fn  = _patch_pos_fn(d.pos_fn)

            changed = (
                new_pts != d.p  or
                new_px  != d.px or
                new_fill    is not d.fill_color    or
                new_outline is not d.outline_color or
                new_pos_fn  is not d.pos_fn
            )

            if changed:
                poly.defn = _tw_replace(poly.defn,
                    p             = new_pts,
                    px            = new_px,
                    fill_color    = new_fill,
                    outline_color = new_outline,
                    pos_fn        = new_pos_fn,
                )
                poly.cur_p      = list(new_pts)
                poly._sp        = list(new_pts)
                if new_px:
                    poly.cur_px = list(new_px)
                    poly._spx   = list(new_px)
                if new_fill is not None and new_fill is not d.fill_color:
                    poly.cur_fill_color = QColor(new_fill)
                    poly._sf            = QColor(new_fill)
                if new_outline is not None and new_outline is not d.outline_color:
                    poly.cur_outline_color = QColor(new_outline)
                    poly._so               = QColor(new_outline)
                poly._dirty = True

        for text in sw._texts:
            d  = text.defn
            fn = d.text_fn

            if fn is GROUP_EVENT:
                text.defn = _tw_replace(text.defn,
                    text_fn=lambda ctx, e=group_ev: str(e.value))
            elif isinstance(fn, EventDef):
                snapped = str(fn.value)
                text.defn = _tw_replace(text.defn,
                    text_fn=lambda ctx, s=snapped: s)
            elif isinstance(fn, _StaticRef):
                idx     = fn.index
                snapped = str(statics[idx]) if idx < len(statics) else ''
                text.defn = _tw_replace(text.defn,
                    text_fn=lambda ctx, s=snapped: s)

            d      = text.defn
            new_p  = P(
                statics[d.p.x.index] if isinstance(d.p.x, _StaticRef) else d.p.x,
                statics[d.p.y.index] if isinstance(d.p.y, _StaticRef) else d.p.y,
            )
            new_px = P(
                statics[d.px.x.index] if isinstance(d.px.x, _StaticRef) else d.px.x,
                statics[d.px.y.index] if isinstance(d.px.y, _StaticRef) else d.px.y,
            )
            new_color  = _resolve(d.fill_color)
            new_pos_fn = _patch_pos_fn(d.pos_fn)

            pos_changed = any(isinstance(v, _StaticRef) for v in (d.p.x, d.p.y, d.px.x, d.px.y))
            col_changed = new_color is not d.fill_color
            pfn_changed = new_pos_fn is not d.pos_fn

            if pos_changed or col_changed or pfn_changed:
                text.defn = _tw_replace(text.defn,
                    p      = new_p,
                    px     = new_px,
                    fill_color  = new_color  if col_changed else d.fill_color,
                    pos_fn = new_pos_fn if pfn_changed else d.pos_fn,
                )
            if pos_changed:
                text.cur_p  = new_p
                text.cur_px = new_px
                text._sp    = new_p
                text._spx   = new_px
                text._dirty = True
            if col_changed:
                text.cur_color = QColor(new_color)
                text._sc       = QColor(new_color)
                
        for btn in sw._buttons:
            d = btn.defn

            new_out   = _resolve(d.event_out)
            if d.event_delta is GROUP_EVENT:
                new_delta = wdef.spawn_delete_threshold
            else:
                new_delta = _resolve(d.event_delta)

            pd          = d.poly_def
            new_pts     = [_resolve_p(p) for p in pd.p]
            new_px      = [_resolve_p(p) for p in pd.px] if pd.px else None
            new_fill    = _resolve(pd.fill_color)
            new_outline = _resolve(pd.outline_color)
            new_pos_fn  = _patch_pos_fn(pd.pos_fn)

            new_poly = _tw_replace(pd,
                p             = new_pts,
                px            = new_px,
                fill_color    = new_fill    if new_fill    is not pd.fill_color    else pd.fill_color,
                outline_color = new_outline if new_outline is not pd.outline_color else pd.outline_color,
                pos_fn        = new_pos_fn,
            )

            btn.defn     = _tw_replace(d,
                poly_def    = new_poly,
                event_out   = new_out,
                event_delta = new_delta,
            )
            btn._polygon = AnimatedPolygon(new_poly)
            btn._polygon.set_phase(sw._cur_phase)

            if btn._text is not None:
                t  = btn._text
                td = t.defn
                tn_x  = statics[td.x.index]  if isinstance(td.x,  _StaticRef) else td.x
                tn_y  = statics[td.y.index]  if isinstance(td.y,  _StaticRef) else td.y
                tn_px = statics[td.px.index] if isinstance(td.px, _StaticRef) else td.px
                tn_py = statics[td.py.index] if isinstance(td.py, _StaticRef) else td.py
                tn_color  = _resolve(td.fill_color)
                tn_pos_fn = _patch_pos_fn(td.pos_fn)

                if any(isinstance(v, _StaticRef) for v in (td.x, td.y, td.px, td.py)):
                    t.defn  = _tw_replace(t.defn,
                        x=tn_x, y=tn_y, px=tn_px, py=tn_py)
                    t.cur_x  = tn_x;  t._sx  = tn_x
                    t.cur_y  = tn_y;  t._sy  = tn_y
                    t.cur_px = tn_px; t._spx = tn_px
                    t.cur_py = tn_py; t._spy = tn_py
                    t._dirty = True
                if tn_color is not td.fill_color:
                    t.defn     = _tw_replace(t.defn, fill_color=tn_color)
                    t.cur_color = QColor(tn_color)
                    t._sc       = QColor(tn_color)
                if tn_pos_fn is not td.pos_fn:
                    t.defn = _tw_replace(t.defn, pos_fn=tn_pos_fn)

        wx, wy, ww, wh = self._screen_rect(widget_w, widget_h)
        sw._parent_w = int(ww)
        sw._parent_h = int(wh)

        sw._broadcast('open')

        obj_id = self._make_id()
        inst   = _SpawnedInstance(obj_id=obj_id, window=sw, group_event=group_ev)
        self._spawned.append(inst)
        return inst

    def _make_id(self) -> str:
        return str(uuid.uuid4())

    def _remove_spawn(self, inst: _SpawnedInstance) -> None:
        wdef  = inst.window.defn
        group = wdef.spawn_event_group or ''
        if group:
            _free_group_event(group, inst.group_event)
        if inst in self._spawned:
            self._spawned.remove(inst)

    def _is_done(self) -> bool:
        """True when current phase animation has fully completed."""
        poly_done = all(p.phase_done() for p in self._polygons)
        text_done = all(t.phase_done() for t in self._texts)
        btn_done  = all(b.phase_done() for b in self._buttons)
        return poly_done and text_done and btn_done

    def _clamp_to_boundary(self, parent_w: int, parent_h: int) -> None:
        d = self.defn

        bx1 = d.drag_boundary_p1.x
        by1 = d.drag_boundary_p1.y
        bx2 = d.drag_boundary_p2.x
        by2 = d.drag_boundary_p2.y

        win_w_n = self._cur_p2.x - self._cur_p1.x
        win_h_n = self._cur_p2.y - self._cur_p1.y

        new_p1x = max(bx1, min(bx2 - win_w_n, self._cur_p1.x))
        new_p1y = max(by1, min(by2 - win_h_n, self._cur_p1.y))

        dx = new_p1x - self._cur_p1.x
        dy = new_p1y - self._cur_p1.y

        self._cur_p1 = P(self._cur_p1.x + dx, self._cur_p1.y + dy)
        self._cur_p2 = P(self._cur_p2.x + dx, self._cur_p2.y + dy)
    
    def _cancel_active_phases(self) -> None:
        for p in self._polygons:
            if p._phase not in ('open', 'close', ''):
                p.set_phase('open')
        for t in self._texts:
            if t._phase not in ('open', 'close', ''):
                t.set_phase('open')
        for btn in self._buttons:
            if btn._cur_phase not in ('open', 'close', ''):
                btn._pressed   = False
                btn._key_held  = False
                btn._hovered   = False
                btn._set_phase('unhover')
        for sl in self._sliders:
            if sl._dragging:
                sl._dragging = False
                sl.set_phase('released')
        for tb in self._textboxes:
            if tb._active:
                tb._deactivate()
        for sw in self._sub_windows:
            sw._cancel_active_phases()

    def _detect_edge(self, lx: float, ly: float, pw: int, ph: int) -> str:
        d     = self.defn.scale_edge_px
        left  = lx <= d
        right = lx >= pw - d
        top   = ly <= d
        bot   = ly >= ph - d

        if top    and left:  return 'tl'
        if top    and right: return 'tr'
        if bot    and left:  return 'bl'
        if bot    and right: return 'br'
        if left:             return 'l'
        if right:            return 'r'
        if top:              return 't'
        if bot:              return 'b'
        return ''

# ──────────────────────── EVENT DEF ────────────────────────

_pending_pulse_resets: List[EventDef] = []

@dataclass
class EventDef:
    name:      str
    value:     Any                          = None
    min_val:   Optional[Union[int, float]]  = None
    max_val:   Optional[Union[int, float]]  = None
    step:      Optional[Union[int, float]]  = None
    label:     str                          = ''
    unit:      str                          = ''
    delay:     float                        = 0.0
    _watchers: List[Callable]               = field(default_factory=list, repr=False, compare=False)

    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        if name == 'value':
            if value == 'pulse':
                if self not in _pending_pulse_resets:
                    _pending_pulse_resets.append(self)
            for w in self.__dict__.get('_watchers', []):
                try: w(value)
                except: pass

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
    value_fn:         Callable[[Any], Any]             = None
    targets:          List[EventDef]                   = field(default_factory=list)
    passthrough:      bool                             = False
    transform:        Optional[Callable[[Any], Any]]   = None
    conditions:       List[Callable[[Any], bool]]      = field(default_factory=list)
    values:           List[Any]                        = field(default_factory=list)
    wait_for_updates: Optional[Callable[Any]]          = None
    _last_value:      Any                              = field(default=None, init=False, repr=False, compare=False)

    def _validate(self) -> bool:
        if self.passthrough:
            return True
        return len(self.values) == len(self.conditions) + 1

    def tick(self, ctx: Any) -> None:
        try:
            raw = self.value_fn(ctx) if callable(self.value_fn) else self.value_fn
        except Exception:
            raw = None

        if raw is None:
            return

        if self.wait_for_updates is not None:
            if callable(self.wait_for_updates):
                try:
                    cur = self.wait_for_updates(ctx)
                except Exception:
                    return
            elif isinstance(self.wait_for_updates, EventDef):
                cur = self.wait_for_updates.value
            else:
                cur = self.wait_for_updates
            if cur == self._last_value:
                return
            if cur == 'ignore':   # skip reset-triggered firings
                self._last_value = cur
                return
            # print(self._last_value, cur)
            self._last_value = cur

        if self.passthrough:
            if self.transform is None:
                output = raw
            elif callable(self.transform):
                output = self.transform(raw)
            else:
                output = self.transform
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
            # print(output)
            target.value = output    








# I'll organise this later

@dataclass 
class _SpawnedInstance:
    obj_id:      str
    window:      'AnimatedWindow'
    group_event: EventDef
    closing:     bool = False


_spawn_group_events: Dict[str, List[EventDef]] = {}
GROUP_EVENT = '__group_event__'
SNAPSHOT_EVENT = '__snapshot_event__'

def _snap_phase(animated_obj):
    for tw in animated_obj._tweens:
        if not isinstance(tw, Reset):
            animated_obj._snap_to(tw)
    animated_obj._idx = len(animated_obj._tweens)
    if hasattr(animated_obj, '_dirty'):
        animated_obj._dirty = True

def _alloc_group_event(group: str) -> EventDef:
    existing = _spawn_group_events.setdefault(group, [])
    used = {int(e.name[len(group):]) for e in existing if e.name[len(group):].isdigit()}
    idx = 1
    while idx in used:
        idx += 1
    ev = EventDef(name=f'{group}{idx}', value=0)
    existing.append(ev)
    return ev

def _free_group_event(group: str, ev: EventDef) -> None:
    lst = _spawn_group_events.get(group, [])
    if ev in lst:
        lst.remove(ev)

def get_spawn_events(group: str) -> List[EventDef]:
    return list(_spawn_group_events.get(group, []))

def get_spawn_event(group: str, index: int) -> Optional[EventDef]:
    name = f'{group}{index}'
    for ev in _spawn_group_events.get(group, []):
        if ev.name == name:
            return ev
    return None

class _StaticRef:
    __slots__ = ('index',)
    def __init__(self, index: int):
        self.index = index

def STATIC(index: int) -> _StaticRef:
    return _StaticRef(index)

def _patch_fn_defaults(fn: Callable, new_defaults: tuple) -> Callable:
    import types
    try:
        return types.FunctionType(
            fn.__code__,
            fn.__globals__,
            fn.__name__,
            new_defaults,
            fn.__closure__,
        )
    except Exception as e:
        print(f'[_patch_fn_defaults] failed: {e}')
        return fn

_window_mouse_norm: Dict[int, P] = {}

def get_mouse_norm(wdef: 'WindowDef') -> P:
    return _window_mouse_norm.get(id(wdef), P(0.0, 0.0))

_current_spawn_window: Optional['AnimatedWindow'] = None

def get_spawn_mouse_norm() -> P:
    if _current_spawn_window is None:
        return P(0.0, 0.0)
    w = _current_spawn_window
    if w._abs_ww <= 0 or w._abs_wh <= 0:
        return P(0.0, 0.0)
    return P(
        (SYS_MOUSE_ABS_X.value - w._abs_wx) / w._abs_ww,
        (SYS_MOUSE_ABS_Y.value - w._abs_wy) / w._abs_wh,
    )

def _reset_phase_override_event(ov) -> None:
    if ov is None:
        return
    try:
        if callable(ov):
            import inspect
            src = inspect.getclosurevars(ov)
            for val in list(src.nonlocals.values()) + list(src.globals.values()):
                if isinstance(val, EventDef):
                    val.value = None
                    return
    except Exception:
        pass

def _check_visible_threshold(defn: Any, ww: float, wh: float, cam_w: int, cam_h: int) -> bool:
    tx = defn.visible_threshold_x
    ty = defn.visible_threshold_y
    if tx > 0.0:
        px_thresh = tx * cam_w if tx <= 1.0 else tx
        if ww < px_thresh:
            return False
    if ty > 0.0:
        py_thresh = ty * cam_h if ty <= 1.0 else ty
        if wh < py_thresh:
            return False
    return True






# ──────────────────────── DATA CHANNEL ────────────────────────

class DataChannel:
    def __init__(self, name: str, max_samples: int = 100, unit: str = '') -> None:
        self.name        = name
        self.max_samples = max_samples
        self.unit        = unit
        self._lock   = threading.Lock()
        self._buffer: collections.deque[float] = collections.deque(maxlen=max_samples)
        self._push_count = 0

    def push(self, value: float) -> None:
        with self._lock:
            self._buffer.append(value)
            self._push_count += 1

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
            'push_count': self._push_count,
            'unit':    self.unit,
        }

# ──────────────────────── Helpers ────────────────────────

def _ease(t: float, curve) -> float:
    # Common curves
    if curve == QEasingCurve.OutQuint:  return 1.0 - (1.0 - t) ** 5
    if curve == QEasingCurve.Linear:    return t
    if curve == QEasingCurve.OutCubic:  return 1.0 - (1.0 - t) ** 3
    if curve == QEasingCurve.OutQuad:   return 1.0 - (1.0 - t) ** 2
    # Less common curves
    if curve == QEasingCurve.OutCirc:
        t2 = t - 1.0; return _math.sqrt(max(0.0, 1.0 - t2 * t2))
    if curve == QEasingCurve.InQuint:   return t ** 5
    if curve == QEasingCurve.InOutCirc:
        if t < 0.5:
            return 0.5 * (1.0 - _math.sqrt(max(0.0, 1.0 - 4.0 * t * t)))
        t2 = 2.0 * t - 2.0; return 0.5 * (_math.sqrt(max(0.0, 1.0 - t2 * t2)) + 1.0)
    if curve == QEasingCurve.OutBack:
        c = 1.70158; t2 = t - 1.0
        return 1.0 + (c + 1.0) * t2 ** 3 + c * t2 ** 2
    if curve == QEasingCurve.InOutQuad:
        if t < 0.5: return 2.0 * t * t
        return 1.0 - (-2.0 * t + 2.0) ** 2 * 0.5
    if curve == QEasingCurve.InCirc:    return 1.0 - _math.sqrt(max(0.0, 1.0 - t * t))
    if curve == QEasingCurve.InCubic:   return t ** 3
    if curve == QEasingCurve.InQuad:    return t * t
    if curve == QEasingCurve.OutSine:   return _math.sin(t * _math.pi * 0.5)
    if curve == QEasingCurve.InSine:    return 1.0 - _math.cos(t * _math.pi * 0.5)
    c = QEasingCurve(curve); return c.valueForProgress(t)

def _tw_replace(tw, **kwargs):
    d = {**tw.__dict__, **kwargs}
    return type(tw)(**d)

def lerp_color(src: QColor, dst: QColor, v: float) -> QColor:
    if v <= 0.0: return QColor(src)
    if v >= 1.0: return QColor(dst)
    iv = 1.0 - v
    return QColor(
        int(src.red()   * iv + dst.red()   * v + 0.5),
        int(src.green() * iv + dst.green() * v + 0.5),
        int(src.blue()  * iv + dst.blue()  * v + 0.5),
        int(src.alpha() * iv + dst.alpha() * v + 0.5),
    )

def _with_alpha(color, alpha):
    c=QColor(color); c.setAlpha(alpha); return c

def _derive_button_colors(base: QColor):
    avg = (base.red() + base.green() + base.blue()) / 3 / 255
    is_light = avg >= 0.5
    factor_hover = 0.75 if is_light else 1.4
    factor_click = 0.55 if is_light else 1.7
    def _scale(c, f): return max(0, min(255, int(c * f)))
    hover = QColor(_scale(base.red(), factor_hover),_scale(base.green(), factor_hover),_scale(base.blue(),  factor_hover),base.alpha())
    click = QColor(_scale(base.red(), factor_click),_scale(base.green(), factor_click),_scale(base.blue(),  factor_click),base.alpha())
    return hover, click

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
                p             = _pts(tw.p, prev_blended) if tw.p is not None else None,
                px            = _pxs(tw.px) if tw.px is not None else None,
                fill_color    = tw.fill_color,
                outline_color = tw.outline_color,
                outline_width    = tw.outline_width,
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
        p             = _pts(defn.p),
        px            = _pxs(defn.px) if defn.px is not None else None,
        fill_color    = defn.fill_color,
        outline_color = defn.outline_color,
        outline_width    = defn.outline_width,
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


def _resolve_rotation(cur_rot_center_p, cur_rot_center_px, cur_rot_target_p, cur_rot_target_px, cur_rot_angle_initial, cur_rot_angle, ww: int, wh: int) -> Optional[Tuple[float, float, float]]:
    net = cur_rot_angle - cur_rot_angle_initial
    if net == 0.0:
        return None

    cx = cur_rot_center_p.x * ww + cur_rot_center_px.x
    cy = cur_rot_center_p.y * wh + cur_rot_center_px.y

    return cx, cy, net


# ──────────────────────── PHASE KEYS ────────────────────────

class PhaseKey:
    __slots__ = ('name',)
    def __init__(self, name: str) -> None:
        self.name = name
    def __repr__(self) -> str:
        return f'PhaseKey({self.name!r})'
    def __str__(self) -> str:
        return self.name
    def __hash__(self) -> int:
        return id(self)
    def __eq__(self, other) -> bool:
        if isinstance(other, PhaseKey):
            return self is other
        if isinstance(other, str):
            return self.name == other
        return NotImplemented

# Common phases
P_OPEN     = PhaseKey('open')
P_CLOSE    = PhaseKey('close')
P_HOVER    = PhaseKey('hover')
P_UNHOVER  = PhaseKey('unhover')
P_CLICK    = PhaseKey('click')
P_RELEASE  = PhaseKey('release')
P_SET      = PhaseKey('set')
P_ALWAYS   = PhaseKey('always')

def _phase_key_exists(phases: dict, name) -> bool:
    if name in phases:
        return True
    for key in phases:
        if isinstance(key, tuple) and name in key:
            return True
    return False

def _phase_key_name(key) -> str:
    if isinstance(key, PhaseKey): return key.name
    if isinstance(key, str):      return key
    if isinstance(key, tuple):    return _phase_key_name(key[0])
    return str(key)

SYS_FPS        = EventDef(name='__sys_fps__',        value=0.0)
SYS_FRAME_TIME = EventDef(name='__sys_frame_time__', value=0.0)   # ms per frame
SYS_MOUSE      = EventDef(name='__sys_mouse__',      value=(0.0, 0.0))
SYS_MOUSE_X    = EventDef(name='__sys_mouse_x__',    value=0.0)
SYS_MOUSE_Y    = EventDef(name='__sys_mouse_y__',    value=0.0)
SYS_MOUSE_ABS_X = EventDef(name='__sys_mouse_abs_x__', value=0.0)
SYS_MOUSE_ABS_Y = EventDef(name='__sys_mouse_abs_y__', value=0.0)