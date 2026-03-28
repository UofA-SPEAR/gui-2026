"""overlay_system.py — Overlay engine, settings panel, camera select: all classes.
Def tables live in overlay_defs.py.
"""
from __future__ import annotations
from typing import Optional, Dict, List, Tuple, Callable, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore    import Qt, QTimer, QElapsedTimer, QEasingCurve, QPointF, QRectF, QEvent, QObject
from PySide6.QtGui     import QColor, QPainter, QFont, QFontMetrics, QPolygonF, QPen, QRegion


# ──────────────────────── Slant ──────────────────────────────────

class SlantCorner(Enum):
    TOP_LEFT = 'TL'; TOP_RIGHT = 'TR'; BOTTOM_LEFT = 'BL'; BOTTOM_RIGHT = 'BR'

class SlantAngle(Enum):
    DEG_45 = 45; DEG_22 = 22

class SlantPair(Enum):
    NONE = 'none'; PARALLELOGRAM = 'para'; TRAPEZOID = 'trap'

class SlantType(Enum):
    STANDARD    = 'standard'
    POINT       = 'point'
    POINT_LEFT  = 'point_left'
    POINT_RIGHT = 'point_right'

@dataclass(frozen=True)
class Slant:
    corner: SlantCorner
    angle:  SlantAngle = SlantAngle.DEG_45
    pair:   SlantPair  = SlantPair.NONE
    type:   SlantType  = SlantType.STANDARD


# ──────────────────────── Rect ───────────────────────────────────

@dataclass(frozen=True)
class Rect:
    x: float = 0.0; y: float = 0.0; w: float = 0.0; h: float = 0.0

_ZERO_RECT = Rect()


# ──────────────────────── Easing cache ───────────────────────────

# Pre-import math once at module level for easing functions
import math as _math
_HALF_PI = _math.pi / 2

def _ease(t: float, curve) -> float:
    """Pure Python easing — no C++ boundary crossing."""
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
    if curve == QEasingCurve.OutSine:   return _math.sin(t * _HALF_PI)
    if curve == QEasingCurve.InSine:    return 1.0 - _math.cos(t * _HALF_PI)
    # Fallback for any unlisted curve
    c = QEasingCurve(curve); return c.valueForProgress(t)


# ──────────────────────── Geometry helpers ───────────────────────

_PARA_OPPOSITE = {
    SlantCorner.TOP_LEFT: SlantCorner.BOTTOM_RIGHT, SlantCorner.TOP_RIGHT: SlantCorner.BOTTOM_LEFT,
    SlantCorner.BOTTOM_RIGHT: SlantCorner.TOP_LEFT, SlantCorner.BOTTOM_LEFT: SlantCorner.TOP_RIGHT,
}
_TRAP_OPPOSITE = {
    SlantCorner.TOP_LEFT: SlantCorner.TOP_RIGHT,    SlantCorner.TOP_RIGHT: SlantCorner.TOP_LEFT,
    SlantCorner.BOTTOM_LEFT: SlantCorner.BOTTOM_RIGHT, SlantCorner.BOTTOM_RIGHT: SlantCorner.BOTTOM_LEFT,
}
_SLANT_ORDER = {
    SlantCorner.TOP_LEFT:     lambda hp, vp: [vp, hp],
    SlantCorner.TOP_RIGHT:    lambda hp, vp: [hp, vp],
    SlantCorner.BOTTOM_RIGHT: lambda hp, vp: [vp, hp],
    SlantCorner.BOTTOM_LEFT:  lambda hp, vp: [hp, vp],
}
_CORNER_IDX = {
    SlantCorner.TOP_LEFT: 0, SlantCorner.TOP_RIGHT: 1,
    SlantCorner.BOTTOM_RIGHT: 2, SlantCorner.BOTTOM_LEFT: 3,
}
_CW_CORNERS = [SlantCorner.TOP_LEFT, SlantCorner.TOP_RIGHT,
               SlantCorner.BOTTOM_RIGHT, SlantCorner.BOTTOM_LEFT]
_CW_BASE    = lambda x,y,w,h: [QPointF(x,y), QPointF(x+w,y), QPointF(x+w,y+h), QPointF(x,y+h)]


def compute_slant_pts(x, y, w, h, slant):
    d = min(w, h); eps = 1e-4
    hd = min(d if slant.angle == SlantAngle.DEG_45 else d/2, w-eps)
    vd = min(d, h-eps)
    def cut(c):
        if c == SlantCorner.TOP_LEFT:     return QPointF(x+hd,y),   QPointF(x,y+vd)
        if c == SlantCorner.TOP_RIGHT:    return QPointF(x+w-hd,y), QPointF(x+w,y+vd)
        if c == SlantCorner.BOTTOM_RIGHT: return QPointF(x+w-hd,y+h), QPointF(x+w,y+h-vd)
        return                                   QPointF(x+hd,y+h),   QPointF(x,y+h-vd)
    cuts = {slant.corner: cut(slant.corner)}
    if slant.pair == SlantPair.PARALLELOGRAM: cuts[_PARA_OPPOSITE[slant.corner]] = cut(_PARA_OPPOSITE[slant.corner])
    elif slant.pair == SlantPair.TRAPEZOID:   cuts[_TRAP_OPPOSITE[slant.corner]] = cut(_TRAP_OPPOSITE[slant.corner])
    pts = []
    for c, base in zip(_CW_CORNERS, _CW_BASE(x,y,w,h)):
        if c in cuts: hp,vp = cuts[c]; pts.extend(_SLANT_ORDER[c](hp,vp))
        else:         pts.append(base)
    return pts


def compute_point_pts(x, y, w, h, slant):
    d = min(w,h); off_pt = d/2 if slant.angle==SlantAngle.DEG_45 else d/4
    off_sl = d if slant.angle==SlantAngle.DEG_45 else d/2
    def spike(c):
        if c in (SlantCorner.TOP_LEFT, SlantCorner.BOTTOM_LEFT):
            return QPointF(x+off_pt,y), QPointF(x,y+d/2), QPointF(x+off_pt,y+h)
        return QPointF(x+w-off_pt,y), QPointF(x+w,y+d/2), QPointF(x+w-off_pt,y+h)
    def cut(c):
        if c==SlantCorner.TOP_LEFT:     return QPointF(x,y+off_sl),     QPointF(x+off_sl,y)
        if c==SlantCorner.TOP_RIGHT:    return QPointF(x+w-off_sl,y),   QPointF(x+w,y+off_sl)
        if c==SlantCorner.BOTTOM_RIGHT: return QPointF(x+w-off_sl,y+h), QPointF(x+w,y+h-off_sl)
        return                                 QPointF(x+off_sl,y+h),   QPointF(x,y+h-off_sl)
    spike_set = {slant.corner: spike(slant.corner)}
    cut_set   = {}
    if slant.pair==SlantPair.PARALLELOGRAM: cut_set[_PARA_OPPOSITE[slant.corner]] = cut(_PARA_OPPOSITE[slant.corner])
    elif slant.pair==SlantPair.TRAPEZOID:   cut_set[_TRAP_OPPOSITE[slant.corner]] = cut(_TRAP_OPPOSITE[slant.corner])
    n = 4; pts = []
    for i,(c,base) in enumerate(zip(_CW_CORNERS, _CW_BASE(x,y,w,h))):
        next_c = _CW_CORNERS[(i+1)%n]
        if c in spike_set:   pts.extend(spike_set[c])
        elif c in cut_set:   pts.extend(cut_set[c])
        elif next_c in spike_set or next_c in cut_set: pass
        else: pts.append(base)
    return pts


def compute_point_left_pts(x, y, w, h, slant):
    off = h/2 if slant.angle==SlantAngle.DEG_45 else h/4
    return [QPointF(x,y), QPointF(x+w,y), QPointF(x+w,y+h-off), QPointF(x+w-off,y+h), QPointF(x-off,y+h/2)]

def compute_point_right_pts(x, y, w, h, slant):
    off = h/2 if slant.angle==SlantAngle.DEG_45 else h/4
    return [QPointF(x+off,y), QPointF(x+w+off,y+h/2), QPointF(x+w,y+h), QPointF(x,y+h), QPointF(x,y+off)]

def rect_pts(x, y, w, h): return [QPointF(x,y), QPointF(x+w,y), QPointF(x+w,y+h), QPointF(x,y+h)]

def make_pts(x, y, w, h, slant):
    if slant is None:                       return rect_pts(x,y,w,h)
    if slant.type==SlantType.POINT:         return compute_point_pts(x,y,w,h,slant)
    if slant.type==SlantType.POINT_LEFT:    return compute_point_left_pts(x,y,w,h,slant)
    if slant.type==SlantType.POINT_RIGHT:   return compute_point_right_pts(x,y,w,h,slant)
    return compute_slant_pts(x,y,w,h,slant)


def lerp_pts(a, b, v, insert_idx=0):
    if   len(a) < len(b): a = a[:insert_idx] + [a[insert_idx]] + a[insert_idx:]
    elif len(b) < len(a): b = b[:insert_idx] + [b[insert_idx]] + b[insert_idx:]
    return [QPointF(pa.x()+(pb.x()-pa.x())*v, pa.y()+(pb.y()-pa.y())*v) for pa,pb in zip(a,b)]

def lerp_color(src, dst, v):
    sr=src.red();   dr=dst.red()
    sg=src.green(); dg=dst.green()
    sb=src.blue();  db=dst.blue()
    sa=src.alpha(); da=dst.alpha()
    return QColor(int(sr+(dr-sr)*v), int(sg+(dg-sg)*v),
                  int(sb+(db-sb)*v), int(sa+(da-sa)*v))

def _lerp_rect(a, b, v):
    return Rect(a.x+(b.x-a.x)*v, a.y+(b.y-a.y)*v, a.w+(b.w-a.w)*v, a.h+(b.h-a.h)*v)


# ──────────────────────── Tween dataclasses ──────────────────────

@dataclass
class Tween:
    rect: Rect; start: float; dur: float; ease: QEasingCurve.Type
    color: Optional[QColor] = None; px: Rect = field(default_factory=Rect)
    slant: Optional[Slant] = None;  prev_phase: Optional[str] = None

@dataclass
class TextTween:
    x: float; y: float; start: float; dur: float; ease: QEasingCurve.Type
    color: Optional[QColor] = None; h_align: float = 0.0; v_align: float = 0.0
    font_size: Optional[float] = None; px: float = 0.0; py: float = 0.0
    prev_phase: Optional[str] = None

@dataclass
class Reset:
    prev_phase: Optional[str] = None; start: float = 0

@dataclass
class Phase:
    tweens: list


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
        self._prev   = self._phase; self._phase = phase
        self._idx    = 0
        self._tweens = self._active_tweens(phase, self._prev, phases)
        # Only unhide if this phase has tweens or the phase is explicitly defined.
        # If no tweens match (filtered by prev_phase), keep current hidden state
        # so elements don't bleed through from an incompatible previous phase.
        if self._tweens or phase in phases:
            self.hidden = False
        self._save_start(); self._timer.restart()

    def _is_done(self): return self._idx >= len(self._tweens)
    def phase_done(self): return self._is_done()

    def _drive(self, hide_when_done=False):
        if self.hidden: return
        elapsed = self._timer.elapsed() / 1000.0
        tweens = self._tweens
        idx    = self._idx
        n      = len(tweens)
        while True:
            if idx >= n:
                self._idx = idx
                if hide_when_done: self.hidden = True
                return
            tw    = tweens[idx]
            local = elapsed - tw.start
            if local < 0: self._idx = idx; return
            if isinstance(tw, Reset):
                self._reset_to_def(); idx += 1; continue
            dur = tw.dur
            t   = (local / dur) if dur > 0 else 1.0
            if t > 1.0: t = 1.0
            v   = _ease(t, tw.ease)
            self._apply(tw, v)
            if t < 1.0: self._idx = idx; return
            self._snap_to(tw); self._save_start(); idx += 1
        self._idx = idx

    def _save_start(self): pass
    def _snap_to(self, tw): pass
    def _reset_to_def(self): pass
    def _apply(self, tw, v): pass


# ──────────────────────── Def dataclasses ────────────────────────

@dataclass
class RectDef:
    rect: Rect; color: QColor; uniform_scale: bool; phases: Dict[str, Phase]
    px: Rect = field(default_factory=Rect); slant: Optional[Slant] = None

@dataclass
class TextDef:
    x: float; y: float; text: str; font_size: float; color: QColor
    phases: Dict[str, Phase]; bold: bool; italic: bool; font_family: str
    h_align: float; v_align: float; uniform_scale: bool
    px: float = 0.0; py: float = 0.0
    text_fn: Optional[Callable[[Any], str]] = None; always_visible: bool = False


# ──────────────────────── AnimatedRect ───────────────────────────

class AnimatedRect(_TweenDriver):
    def __init__(self, defn: RectDef):
        super().__init__()
        self.defn      = defn
        self.cur_rect  = defn.rect;  self.cur_px    = defn.px
        self.cur_color = QColor(defn.color); self.cur_slant = defn.slant
        self._sr = defn.rect; self._sp = defn.px
        self._sc = QColor(defn.color); self._ss = defn.slant
        # Cached polygon — recomputed only when tween advances (_dirty=True)
        self._dirty         = True
        self._cached_brush  = None
        self._cached_w      = 0
        self._cached_h      = 0
        self._cached_poly   = QPolygonF()
        self._cached_is_rect = True

    def _save_start(self):
        self._sr = self.cur_rect; self._sp = self.cur_px
        self._sc = QColor(self.cur_color); self._ss = self.cur_slant

    def _apply(self, tw, v):
        self.cur_rect  = _lerp_rect(self._sr, tw.rect, v)
        self.cur_px    = _lerp_rect(self._sp, tw.px,   v)
        if tw.color is not None: self.cur_color = lerp_color(self._sc, tw.color, v)
        self.cur_slant = tw.slant if v >= 1.0 else self._ss
        self._dirty = True; self._cached_brush = None

    def _snap_to(self, tw):
        self.cur_rect = tw.rect; self.cur_px = tw.px; self.cur_slant = tw.slant
        if tw.color is not None: self.cur_color = QColor(tw.color)
        self._dirty = True; self._cached_brush = None

    def _reset_to_def(self):
        d = self.defn
        self.cur_rect = d.rect; self.cur_px = d.px
        self.cur_color = QColor(d.color); self.cur_slant = d.slant
        self._dirty = True; self._cached_brush = None

    def set_phase(self, phase):
        super().set_phase(phase, self.defn.phases)
        self._dirty = True; self._cached_brush = None

    def update(self): self._drive(hide_when_done=False)

    def _scale(self, uniform_scale, widget_w, widget_h, cam_w, cam_h):
        if uniform_scale:
            s = min(widget_w/cam_w, widget_h/cam_h)
            return s/(widget_w/cam_w), s/(widget_h/cam_h)
        return 1.0, 1.0

    def _to_screen(self, r, p, cx, cy, ww, wh, us):
        if us:
            sx,sy,sw,sh = (0.5+(r.x-0.5)*cx)*ww, (0.5+(r.y-0.5)*cy)*wh, r.w*cx*ww, r.h*cy*wh
        else:
            sx,sy,sw,sh = r.x*ww, r.y*wh, r.w*ww, r.h*wh
        return sx+p.x, sy+p.y, sw+p.w, sh+p.h

    def get_polygon(self, widget_w, widget_h, uniform_scale, cam_w, cam_h):
        if (not self._dirty and self._cached_w == widget_w
                and self._cached_h == widget_h):
            return self._cached_poly, self._cached_is_rect

        # Compute screen rect for current state
        if uniform_scale:
            s  = min(widget_w / cam_w, widget_h / cam_h)
            cx = s / (widget_w / cam_w); cy = s / (widget_h / cam_h)
            r  = self.cur_rect; p = self.cur_px
            sx = (0.5 + (r.x - 0.5) * cx) * widget_w + p.x
            sy = (0.5 + (r.y - 0.5) * cy) * widget_h + p.y
            sw = r.w * cx * widget_w + p.w
            sh = r.h * cy * widget_h + p.h
        else:
            r  = self.cur_rect; p = self.cur_px
            sx = r.x * widget_w + p.x
            sy = r.y * widget_h + p.y
            sw = r.w * widget_w + p.w
            sh = r.h * widget_h + p.h

        pts      = make_pts(sx, sy, sw, sh, self.cur_slant)
        is_rect  = (self.cur_slant is None or
                    (len(pts) == 4
                     and pts[0].x() == pts[3].x() and pts[1].x() == pts[2].x()
                     and pts[0].y() == pts[1].y() and pts[2].y() == pts[3].y()))
        self._cached_poly    = QPolygonF(pts)
        self._cached_is_rect = is_rect
        self._cached_w       = widget_w
        self._cached_h       = widget_h
        self._dirty          = False
        return self._cached_poly, self._cached_is_rect

    def to_rect(self, w, h):
        r = self.cur_rect; p = self.cur_px
        return int(r.x*w+p.x), int(r.y*h+p.y), int(r.w*w+p.w), int(r.h*h+p.h)


# ──────────────────────── AnimatedText ───────────────────────────

class AnimatedText(_TweenDriver):
    def __init__(self, defn: TextDef):
        super().__init__()
        self.defn = defn; d = defn
        self.cur_x=d.x; self.cur_y=d.y; self.cur_px=d.px; self.cur_py=d.py
        self.cur_color=QColor(d.color); self.cur_font_size=d.font_size
        self.cur_h_align=d.h_align; self.cur_v_align=d.v_align
        self._sx=d.x; self._sy=d.y; self._spx=d.px; self._spy=d.py
        self._sc=QColor(d.color); self._sfs=d.font_size
        self._sha=d.h_align; self._sva=d.v_align
        self._dirty = True
        self._cached_font = None
        self._cached_dx = 0; self._cached_dy = 0
        self._cached_label = ''
        self._cached_tw = 0; self._cached_th = 0

    def _save_start(self):
        self._sx=self.cur_x; self._sy=self.cur_y
        self._spx=self.cur_px; self._spy=self.cur_py
        self._sc=QColor(self.cur_color); self._sfs=self.cur_font_size
        self._sha=self.cur_h_align; self._sva=self.cur_v_align

    def _snap_to(self, tw):
        self.cur_x=tw.x; self.cur_y=tw.y; self.cur_px=tw.px; self.cur_py=tw.py
        self.cur_h_align=tw.h_align; self.cur_v_align=tw.v_align
        if tw.color is not None:     self.cur_color     = QColor(tw.color)
        if tw.font_size is not None: self.cur_font_size = tw.font_size
        self._dirty = True

    def _reset_to_def(self):
        d = self.defn
        self.cur_x=d.x; self.cur_y=d.y; self.cur_px=d.px; self.cur_py=d.py
        self.cur_color=QColor(d.color); self.cur_font_size=d.font_size
        self.cur_h_align=d.h_align; self.cur_v_align=d.v_align
        self._dirty = True

    def _apply(self, tw, v):
        self.cur_x       = self._sx  + (tw.x       - self._sx)  * v
        self.cur_y       = self._sy  + (tw.y       - self._sy)  * v
        self.cur_px      = self._spx + (tw.px      - self._spx) * v
        self.cur_py      = self._spy + (tw.py      - self._spy) * v
        self.cur_h_align = self._sha + (tw.h_align - self._sha) * v
        self.cur_v_align = self._sva + (tw.v_align - self._sva) * v
        if tw.font_size is not None: self.cur_font_size = self._sfs + (tw.font_size - self._sfs) * v
        if tw.color is not None:     self.cur_color = lerp_color(self._sc, tw.color, v)
        self._dirty = True

    def set_phase(self, phase):
        super().set_phase(phase, self.defn.phases)
        self._dirty = True

    def update(self): self._drive(hide_when_done=not self.defn.always_visible)

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
        if (not self._dirty and self._cached_label == label
                and self._cached_tw == widget_w and self._cached_th == widget_h):
            return self._cached_dx, self._cached_dy
        fm = QFontMetrics(font)
        if self.defn.uniform_scale:
            s  = min(widget_w/cam_w, widget_h/cam_h)
            bx = (0.5+(self.cur_x-0.5)*s/(widget_w/cam_w))*widget_w
            by = (0.5+(self.cur_y-0.5)*s/(widget_h/cam_h))*widget_h
        else:
            bx = self.cur_x*widget_w; by = self.cur_y*widget_h
        bx += self.cur_px; by += self.cur_py
        dx = int(bx - self.cur_h_align*fm.horizontalAdvance(label))
        dy = int(by + fm.ascent() - self.cur_v_align*fm.height())
        self._cached_dx = dx; self._cached_dy = dy
        self._cached_label = label
        self._cached_tw = widget_w; self._cached_th = widget_h
        self._dirty = False
        return dx, dy


# ──────────────────────── Line ───────────────────────────────────

@dataclass(frozen=True)
class LinePt:
    x: float=0.0; y: float=0.0; px: float=0.0; py: float=0.0

@dataclass
class LineTween:
    target:       Union[str,int,List[int]] = 'create'
    collapse_pts: List[int]                = field(default_factory=list)
    collapse_to:  int                      = 0
    color:        Optional[QColor]         = None
    line_width:   Optional[float]          = None
    start:        float                    = 0.0
    dur:          float                    = 0.5
    ease:         QEasingCurve.Type        = QEasingCurve.Linear
    prev_phase:   Optional[str]            = None

@dataclass
class LineDef:
    color: QColor; points: List[LinePt]
    closed: bool=False; phases: Dict[str,Phase]=field(default_factory=dict); line_width: float=1.0


def _resolve_pt(pt, w, h): return QPointF(pt.x*w+pt.px, pt.y*h+pt.py)

def _draw_partial_polyline(painter, pts, t):
    if len(pts) < 2 or t <= 0: return
    lengths = [((pts[i+1].x()-pts[i].x())**2+(pts[i+1].y()-pts[i].y())**2)**0.5 for i in range(len(pts)-1)]
    total = sum(lengths)
    if total == 0: return
    target = total * min(t, 1.0); acc = 0.0
    for i, sl in enumerate(lengths):
        if acc >= target: break
        rem = target - acc
        if rem >= sl:
            painter.drawLine(pts[i], pts[i+1]); acc += sl
        else:
            frac = rem/sl if sl > 0 else 1.0
            painter.drawLine(pts[i], QPointF(pts[i].x()+(pts[i+1].x()-pts[i].x())*frac,
                                             pts[i].y()+(pts[i+1].y()-pts[i].y())*frac)); break


class _LineSegment:
    __slots__ = ('pt_indices','t','_s_t','_tgt_t','_start','_dur','_ease','_elapsed','_active')
    def __init__(self, pt_indices):
        self.pt_indices=pt_indices; self.t=0.0; self._s_t=0.0; self._tgt_t=1.0
        self._start=0.0; self._dur=0.5; self._ease=QEasingCurve.Linear
        self._elapsed=QElapsedTimer(); self._active=False

    def start_tween(self, from_t, to_t, start, dur, ease):
        self.t=from_t; self._s_t=from_t; self._tgt_t=to_t
        self._start=start; self._dur=dur; self._ease=ease
        self._elapsed.restart(); self._active=True

    def update(self):
        if not self._active: return True
        el = self._elapsed.elapsed()/1000.0; loc = el - self._start
        if loc < 0: return False
        raw = min(1.0, loc/self._dur) if self._dur > 0 else 1.0
        self.t = self._s_t + (self._tgt_t-self._s_t)*_ease(raw, self._ease)
        if raw >= 1.0: self.t=self._tgt_t; self._active=False; return True
        return False

    def done(self): return not self._active


class AnimatedLine:
    def __init__(self, defn: LineDef):
        self.defn=defn; self.cur_color=QColor(defn.color); self.cur_width=defn.line_width
        self._s_color=QColor(defn.color); self._s_width=defn.line_width
        self._phase=''; self._prev=''; self._idx=0
        self._tweens: List[LineTween]=[]; self._timer=QElapsedTimer(); self._started=False
        self._segments: List[_LineSegment]=[]
        self._rebuild_segments(list(range(len(defn.points)))); self.hidden=True

    def _rebuild_segments(self, visible):
        n=len(self.defn.points)
        if not visible: self._segments=[]; return
        if not self.defn.closed or len(visible)==n:
            segs=[visible[:]]
        else:
            all_set=set(visible); segs=[]; cur=[]
            start_i=next((i for i,idx in enumerate(visible) if (idx-1)%n not in all_set), 0)
            for idx in visible[start_i:]+visible[:start_i]:
                if cur and (idx-cur[-1])%n!=1: segs.append(cur); cur=[]
                cur.append(idx)
            if cur:
                if segs and self.defn.closed and (segs[0][0]-cur[-1])%n==1: segs[0]=cur+segs[0]
                else: segs.append(cur)
        self._segments=[_LineSegment(s) for s in segs]
        for s in self._segments: s.t=0.0

    def set_phase(self, phase):
        self._prev=self._phase; self._phase=phase; self._idx=0; self._started=False; self.hidden=False
        p=self.defn.phases.get(phase)
        self._tweens=[tw for tw in (p.tweens if p else []) if tw.prev_phase is None or tw.prev_phase==self._prev]
        self._timer.restart()

    def update(self):
        if self.hidden: return
        for seg in self._segments: seg.update()
        elapsed=self._timer.elapsed()/1000.0
        while self._idx < len(self._tweens):
            tw=self._tweens[self._idx]; local=elapsed-tw.start
            if local < 0: break
            raw=min(1.0, local/tw.dur) if tw.dur > 0 else 1.0
            v=_ease(raw, tw.ease)
            if not self._started:
                self._started=True
                if tw.target=='create':
                    for s in self._segments: s.start_tween(0.0,1.0,0.0,tw.dur,tw.ease)
                elif tw.target=='collapse': self._apply_collapse(tw, elapsed)
            if tw.color is not None:     self.cur_color=lerp_color(self._s_color, tw.color, v)
            if tw.line_width is not None: self.cur_width=self._s_width+(tw.line_width-self._s_width)*v
            if raw>=1.0 and all(s.done() for s in self._segments):
                self._s_color=QColor(self.cur_color); self._s_width=self.cur_width
                self._started=False; self._idx+=1
            else: break

    def _apply_collapse(self, tw, elapsed):
        n=len(self.defn.points); remove=set(tw.collapse_pts)
        if not remove: return
        self._rebuild_segments([i for i in range(n) if i not in remove])
        for s in self._segments: s.t=1.0; s._active=False
        for run in self._contiguous_runs(sorted(remove), n):
            cs=_LineSegment([(run[0]-1)%n]+run+[(run[-1]+1)%n])
            cs.start_tween(1.0, 0.0, tw.start, tw.dur, tw.ease)
            self._segments.append(cs)

    @staticmethod
    def _contiguous_runs(indices, n):
        if not indices: return []
        runs=[]; cur=[indices[0]]
        for idx in indices[1:]:
            if (idx-cur[-1])%n==1: cur.append(idx)
            else: runs.append(cur); cur=[idx]
        runs.append(cur); return runs

    def phase_done(self):
        return self._idx>=len(self._tweens) and all(s.done() for s in self._segments)

    def draw(self, painter, w, h):
        if self.hidden: return
        pts=[_resolve_pt(p,w,h) for p in self.defn.points]
        pen=QPen(self.cur_color); pen.setWidthF(self.cur_width)
        pen.setCapStyle(Qt.RoundCap); pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen); painter.setBrush(Qt.NoBrush)
        for seg in self._segments:
            if seg.t<=0: continue
            sp=[pts[i] for i in seg.pt_indices]
            if self.defn.closed and len(seg.pt_indices)==len(self.defn.points): sp=sp+[sp[0]]
            _draw_partial_polyline(painter, sp, seg.t)
        painter.setPen(Qt.NoPen)


# ──────────────────────── lerp_button_slant_pts ──────────────────

def lerp_button_slant_pts(sx, sy, sw, sh, slant_a, slant_b, v):
    if v <= 0.0: return make_pts(sx,sy,sw,sh,slant_a)
    if v >= 1.0: return make_pts(sx,sy,sw,sh,slant_b)
    ta = slant_a.type if slant_a else None
    tb = slant_b.type if slant_b else None
    def _lp(a,b,t): return [QPointF(pa.x()+(pb.x()-pa.x())*t, pa.y()+(pb.y()-pa.y())*t) for pa,pb in zip(a,b)]
    if ta==tb: return _lp(make_pts(sx,sy,sw,sh,slant_a), make_pts(sx,sy,sw,sh,slant_b), v)
    cx=sx+sw/2.0
    def _point_to_none(s,t):
        a=make_pts(sx,sy,sw,sh,s); return _lp(a, [QPointF(cx,p.y()) for p in a], t)
    def _pl_to_none(sa,t):
        return _lp(make_pts(sx,sy,sw,sh,sa),
                   [QPointF(sx,sy),QPointF(sx+sw,sy),QPointF(sx+sw,sy+sh),QPointF(sx+sw,sy+sh),QPointF(sx,sy+sh/2)], t)
    def _pr_to_none(sa,t):
        return _lp(make_pts(sx,sy,sw,sh,sa),
                   [QPointF(sx,sy),QPointF(sx+sw,sy+sh/2),QPointF(sx+sw,sy+sh),QPointF(sx,sy+sh),QPointF(sx,sy)], t)
    if ta==SlantType.POINT      and tb is None: return _point_to_none(slant_a, v)
    if ta is None and tb==SlantType.POINT:      return _point_to_none(slant_b, 1-v)
    if ta==SlantType.POINT_LEFT and tb is None: return _pl_to_none(slant_a, v)
    if ta is None and tb==SlantType.POINT_LEFT: return _pl_to_none(slant_b, 1-v)
    if ta==SlantType.POINT_RIGHT and tb is None: return _pr_to_none(slant_a, v)
    if ta is None and tb==SlantType.POINT_RIGHT: return _pr_to_none(slant_b, 1-v)
    if ta in (SlantType.POINT,SlantType.STANDARD) and tb in (SlantType.POINT,SlantType.STANDARD) \
            and slant_a and slant_b and slant_a.corner==slant_b.corner:
        return lerp_pts(make_pts(sx,sy,sw,sh,slant_a), make_pts(sx,sy,sw,sh,slant_b), v,
                        insert_idx=_CORNER_IDX.get(slant_b.corner,0))
    return make_pts(sx,sy,sw,sh, slant_b if v>=0.5 else slant_a)


# ──────────────────────── AnimatedOverlay ────────────────────────

class AnimatedOverlay(QWidget):
    TICK_MS = 16

    def __init__(self, rect_defs, parent=None, cam_w=1920, cam_h=1080,
                 text_defs=None, line_defs=None):
        super().__init__(parent)
        if parent is None:
            self.setWindowFlags(Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.Window)
            self.setAttribute(Qt.WA_TranslucentBackground)
        else:
            # Child overlay — sits directly inside the parent container.
            # WA_NoSystemBackground + no auto-fill lets our painter draw
            # transparent content over whatever is below.
            self.setAttribute(Qt.WA_NoSystemBackground)
            self.setAttribute(Qt.WA_OpaquePaintEvent, False)
            self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.cam_w=cam_w; self.cam_h=cam_h
        self._rects=[AnimatedRect(d) for d in rect_defs]
        self._texts=[AnimatedText(d) for d in (text_defs or [])]
        self._lines=[AnimatedLine(d) for d in (line_defs or [])]
        self._context=None; self._click_target=None; self._closing=False; self._inline=False
        self._cleaned_up=False
        self._tick_timer=QTimer(self); self._tick_timer.setInterval(self.TICK_MS)
        self._tick_timer.timeout.connect(self._tick)

    def set_context(self, ctx): self._context=ctx
    def set_inline(self): self._inline=True

    def _broadcast(self, phase):
        for r in self._rects: r.set_phase(phase)
        for t in self._texts: t.set_phase(phase)
        for l in self._lines: l.set_phase(phase)

    def _tick(self):
        any_active = False
        for r in self._rects:
            r.update()
            if not r.hidden: any_active = True
        for t in self._texts:
            t.update()
            if not t.hidden or t.defn.always_visible: any_active = True
        for l in self._lines:
            l.update()
            if not l.hidden: any_active = True
        if self._closing:
            if (all(r.phase_done() for r in self._rects) and
                    all(t.phase_done() for t in self._texts) and
                    all(l.phase_done() for l in self._lines)):
                self._cleanup(); return
        else:
            if not any_active:
                self._cleanup(); return
        if not self._inline: self.update()

    def close(self):
        if not self._closing:
            self._closing=True; self._broadcast('close')

    def _cleanup(self):
        self._cleaned_up=True
        self._tick_timer.stop()
        if self.parent() is not None or not self._inline:
            self.hide()
        try:
            app=QApplication.instance()
            if app:
                for w in app.allWidgets():
                    for attr in ('loading_overlay','selection_overlay'):
                        if getattr(w,attr,None) is self: setattr(w,attr,None); break
        except Exception: pass
        self.deleteLater()

    def _tick_externally(self):
        """Called by CameraNode._tick_overlays instead of the internal timer.
        Runs the same logic as _tick but does NOT call self.update()."""
        any_active = False
        for r in self._rects:
            r.update()
            if not r.hidden: any_active = True
        for t in self._texts:
            t.update()
            if not t.hidden or t.defn.always_visible: any_active = True
        for l in self._lines:
            l.update()
            if not l.hidden: any_active = True
        if self._closing:
            if (all(r.phase_done() for r in self._rects) and
                    all(t.phase_done() for t in self._texts) and
                    all(l.phase_done() for l in self._lines)):
                self._cleanup()
        else:
            if not any_active:
                self._cleanup()

    def mousePressEvent(self, event):
        if event.button()==Qt.LeftButton and self._click_target is not None:
            try: self._click_target.clicked.emit()
            except RuntimeError: self._click_target=None
        super().mousePressEvent(event)

    def draw_into(self, painter, x, y, w, h):
        """Draw this overlay at (x,y,w,h) using an existing painter.
        Called from the container's paintEvent — no child widget repaint needed."""
        painter.save()
        painter.translate(x, y)
        painter.setClipRect(QRectF(0, 0, w, h))
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        for rect in self._rects:
            if rect.hidden: continue
            painter.setBrush(rect.cur_color)
            poly, is_r = rect.get_polygon(w, h, rect.defn.uniform_scale, self.cam_w, self.cam_h)
            if is_r: painter.fillRect(poly.boundingRect(), rect.cur_color)
            else:    painter.drawPolygon(poly)
        painter.setPen(Qt.NoPen)
        for text in self._texts:
            if text.hidden: continue
            label = text.resolve_text(self._context)
            if not label: continue
            font = text.build_font()
            painter.setFont(font)
            painter.setPen(text.cur_color)
            dx, dy = text.resolve_pos(w, h, self.cam_w, self.cam_h, label, font)
            painter.drawText(dx, dy, label)
            painter.setPen(Qt.NoPen)
        for line in self._lines:
            line.draw(painter, w, h)
        painter.restore()

    def paintEvent(self, event):
        # Only used when overlay is a top-level window (SettingsOverlay path).
        # When parented to the container, draw_into() is called instead.
        painter=QPainter(self)
        if not painter.isActive(): return
        if self.parent() is None:
            painter.setCompositionMode(QPainter.CompositionMode_Source)
            painter.fillRect(self.rect(), Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        else:
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        self.draw_into(painter, 0, 0, self.width(), self.height())
        painter.end()


# ──────────────────────── Loading / Selection Overlays ───────────

class LoadingOverlay(AnimatedOverlay):
    def __init__(self, parent=None, cam_w=1920, cam_h=1080):
        from spear_gui.overlay_defs import LOADING_RECT_DEFS, LOADING_TEXT_DEFS, LOADING_LINE_DEFS
        super().__init__(LOADING_RECT_DEFS, parent=parent, cam_w=cam_w, cam_h=cam_h,
                         text_defs=LOADING_TEXT_DEFS, line_defs=LOADING_LINE_DEFS)

    def start(self):
        self._broadcast('create'); self.show(); self._tick_timer.start()

    def notify_loaded(self):
        if any(r._phase=='loaded' for r in self._rects): return
        QTimer.singleShot(50, lambda: self._broadcast('loaded'))


class SelectionOverlay(AnimatedOverlay):
    def __init__(self, parent=None, cam_w=1920, cam_h=1080):
        from spear_gui.overlay_defs import SELECTION_RECT_DEFS, SELECTION_TEXT_DEFS, SELECTION_LINE_DEFS
        super().__init__(SELECTION_RECT_DEFS, parent=parent, cam_w=cam_w, cam_h=cam_h,
                         text_defs=SELECTION_TEXT_DEFS, line_defs=SELECTION_LINE_DEFS)
        self._pending_unfocus: Optional[QTimer]=None
        self._last_selection_phase='selected'

    def start(self):
        self._last_selection_phase='selected'
        self._broadcast('selected'); self.show(); self._tick_timer.start()

    def notify_reselected(self):
        if self._pending_unfocus is not None:
            self._pending_unfocus.stop(); self._pending_unfocus=None
        self._last_selection_phase='selected'; self._broadcast('selected')

    def notify_deselected(self):
        if self._last_selection_phase=='unselected': return
        self._last_selection_phase='unselected'; self._broadcast('unselected')

    def notify_focused(self):
        if self._pending_unfocus is not None:
            self._pending_unfocus.stop(); self._pending_unfocus=None; return
        self._broadcast(self._last_selection_phase)

    def notify_unfocused(self):
        if self._pending_unfocus is not None: return
        t=QTimer(); t.setSingleShot(True); t.setInterval(0)
        t.timeout.connect(self._do_notify_unfocused); t.start(); self._pending_unfocus=t

    def _do_notify_unfocused(self):
        self._pending_unfocus=None; self._broadcast('unfocused')



# ──────────────────────── InlineOverlay ──────────────────────────

class InlineOverlay(QObject):
    """Non-widget overlay for use with OverlayCanvas.
    No QWidget, no native window, no compositing overhead.
    The OverlayCanvas ticks it and calls _draw() directly.
    """
    def __init__(self, rect_defs, cam_w=1920, cam_h=1080,
                 text_defs=None, line_defs=None):
        super().__init__()
        self.cam_w = cam_w; self.cam_h = cam_h
        self._rects  = [AnimatedRect(d)  for d in rect_defs]
        self._texts  = [AnimatedText(d)  for d in (text_defs  or [])]
        self._lines  = [AnimatedLine(d)  for d in (line_defs  or [])]
        self._context      = None
        self._click_target = None
        self._closing      = False
        self._done         = False
        self._static_pixmap = None
        self._needs_bake    = False
        self._baked_w       = 0
        self._baked_h       = 0

    def set_context(self, ctx): self._context = ctx

    def _broadcast(self, phase):
        self._static_pixmap = None
        self._needs_bake    = False
        for r in self._rects: r.set_phase(phase)
        for t in self._texts: t.set_phase(phase)
        for l in self._lines: l.set_phase(phase)

    def close(self):
        if not self._closing:
            self._closing = True
            self._broadcast('close')

    def tick(self):
        """Advance tweens. Returns True if still animating, False when static/done."""
        if self._done:
            return False
        if self._static_pixmap is not None:
            return False
        any_visible = False
        any_animating = False
        for r in self._rects:
            r.update()
            if not r.hidden:
                any_visible = True
                if not r.phase_done(): any_animating = True
        for t in self._texts:
            t.update()
            if not t.hidden or t.defn.always_visible:
                any_visible = True
                if not t.phase_done(): any_animating = True
        for l in self._lines:
            l.update()
            if not l.hidden:
                any_visible = True
                if not l.phase_done(): any_animating = True
        if self._closing:
            if not any_animating:
                self._done = True
                return False
            return True
        if not any_visible:
            self._done = True
            return False
        if not any_animating:
            self._needs_bake = True
            return True
        return True

    def _paint_elements(self, painter, w, h):
        from PySide6.QtGui import QBrush
        painter.setPen(Qt.NoPen)
        for rect in self._rects:
            if rect.hidden: continue
            if rect._cached_brush is None:
                rect._cached_brush = QBrush(rect.cur_color)
            painter.setBrush(rect._cached_brush)
            poly, is_r = rect.get_polygon(w, h, rect.defn.uniform_scale,
                                           self.cam_w, self.cam_h)
            if is_r: painter.fillRect(poly.boundingRect(), rect._cached_brush.color())
            else:    painter.drawPolygon(poly)
        painter.setPen(Qt.NoPen)
        for text in self._texts:
            if text.hidden: continue
            label = text.resolve_text(self._context)
            if not label: continue
            font = text.build_font()
            painter.setFont(font); painter.setPen(text.cur_color)
            dx, dy = text.resolve_pos(w, h, self.cam_w, self.cam_h, label, font)
            painter.drawText(dx, dy, label)
            painter.setPen(Qt.NoPen)
        for line in self._lines:
            line.draw(painter, w, h)

    def _draw(self, painter, w, h):
        """Draw at widget size (w, h) into an already-translated painter."""
        if self._needs_bake and not self._closing:
            from PySide6.QtGui import QPixmap
            px = QPixmap(w, h)
            px.fill(Qt.transparent)
            p2 = QPainter(px)
            p2.setRenderHint(QPainter.Antialiasing)
            self._paint_elements(p2, w, h)
            p2.end()
            self._static_pixmap = px
            self._baked_w = w; self._baked_h = h
            self._needs_bake = False
        if (self._static_pixmap is not None
                and self._baked_w == w and self._baked_h == h):
            painter.drawPixmap(0, 0, self._static_pixmap)
            return
        self._paint_elements(painter, w, h)

    def draw_into(self, painter, x, y, w, h):
        painter.save()
        painter.translate(x, y)
        painter.setClipRect(0, 0, w, h)
        self._draw(painter, w, h)
        painter.restore()


class InlineLoadingOverlay(InlineOverlay):
    def __init__(self, cam_w=1920, cam_h=1080):
        from spear_gui.overlay_defs import LOADING_RECT_DEFS, LOADING_TEXT_DEFS, LOADING_LINE_DEFS
        super().__init__(LOADING_RECT_DEFS, cam_w=cam_w, cam_h=cam_h,
                         text_defs=LOADING_TEXT_DEFS, line_defs=LOADING_LINE_DEFS)

    def start(self):
        self._broadcast('create')

    def notify_loaded(self):
        if any(r._phase == 'loaded' for r in self._rects): return
        QTimer.singleShot(50, lambda: self._broadcast('loaded'))


class InlineSelectionOverlay(InlineOverlay):
    def __init__(self, cam_w=1920, cam_h=1080):
        from spear_gui.overlay_defs import SELECTION_RECT_DEFS, SELECTION_TEXT_DEFS, SELECTION_LINE_DEFS
        super().__init__(SELECTION_RECT_DEFS, cam_w=cam_w, cam_h=cam_h,
                         text_defs=SELECTION_TEXT_DEFS, line_defs=SELECTION_LINE_DEFS)
        self._pending_unfocus = None
        self._last_selection_phase = 'selected'

    def start(self):
        self._last_selection_phase = 'selected'
        self._broadcast('selected')

    def notify_reselected(self):
        if self._pending_unfocus is not None:
            self._pending_unfocus.stop(); self._pending_unfocus = None
        self._last_selection_phase = 'selected'
        self._broadcast('selected')

    def notify_deselected(self):
        if self._last_selection_phase == 'unselected': return
        self._last_selection_phase = 'unselected'
        self._broadcast('unselected')

    def notify_focused(self):
        if self._pending_unfocus is not None:
            self._pending_unfocus.stop(); self._pending_unfocus = None; return
        self._broadcast(self._last_selection_phase)

    def notify_unfocused(self):
        if self._pending_unfocus is not None: return
        t = QTimer(); t.setSingleShot(True); t.setInterval(0)
        t.timeout.connect(self._do_notify_unfocused)
        t.start(); self._pending_unfocus = t

    def _do_notify_unfocused(self):
        self._pending_unfocus = None
        self._broadcast('unfocused')

# ──────────────────────── OverlayCanvas ─────────────────────────

class OverlayCanvas(QWidget):
    """Single top-level Tool window covering the container.
    Draws all loading/selection overlays in one paintEvent pass.
    Being a top-level window (not a child) means it paints OVER native
    X11 windows (GStreamer video surfaces) without being composited into
    the backing store — so the video feed shows through correctly.
    """
    TICK_MS = 16

    def __init__(self, parent, external_tick=False):
        # Top-level Tool window — not a child widget
        super().__init__(None)
        self._container = parent
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        # Position over the container
        g = parent.geometry()
        try:
            gp = parent.mapToGlobal(parent.rect().topLeft())
            self.setGeometry(gp.x(), gp.y(), g.width(), g.height())
        except Exception:
            self.setGeometry(g)
        self._entries: dict = {}
        self._external_tick = external_tick
        if not external_tick:
            self._tick_timer = QTimer(self)
            self._tick_timer.setInterval(self.TICK_MS)
            self._tick_timer.timeout.connect(self._tick)

    def resizeToParent(self):
        if self._container:
            try:
                gp = self._container.mapToGlobal(self._container.rect().topLeft())
                self.setGeometry(gp.x(), gp.y(),
                                 self._container.width(), self._container.height())
                self.raise_()
            except RuntimeError:
                pass

    def register(self, cam_widget, loading_ov=None, selection_ov=None):
        entry = self._entries.setdefault(cam_widget, [None, None])
        if loading_ov   is not None: entry[0] = loading_ov
        if selection_ov is not None: entry[1] = selection_ov
        if not self._external_tick and not self._tick_timer.isActive():
            self._tick_timer.start()
        self.raise_()

    def unregister(self, cam_widget):
        self._entries.pop(cam_widget, None)

    def get_loading(self, cam_widget):
        return self._entries.get(cam_widget, [None, None])[0]

    def get_selection(self, cam_widget):
        return self._entries.get(cam_widget, [None, None])[1]

    def _tick(self):
        dead = []
        dirty_region = QRegion()
        for cw, (lo, so) in list(self._entries.items()):
            try:
                g = cw.geometry()
            except RuntimeError:
                dead.append(cw); continue
            lo_active = lo is not None and lo.tick()
            so_active = so is not None and so.tick()
            if lo is not None and lo._done:
                self._entries[cw][0] = None
            if so is not None and so._done:
                self._entries[cw][1] = None
            if lo_active or so_active:
                dirty_region |= QRegion(g)
        for cw in dead:
            self.unregister(cw)
        if not dirty_region.isEmpty():
            self.update()
        elif not self._external_tick:
            self._tick_timer.stop()

    def external_tick(self):
        """Called by CameraNode master timer instead of internal QTimer."""
        if self._container:
            try:
                gp = self._container.mapToGlobal(self._container.rect().topLeft())
                cw = self._container.width(); ch = self._container.height()
                if (self.x() != gp.x() or self.y() != gp.y()
                        or self.width() != cw or self.height() != ch):
                    self.setGeometry(gp.x(), gp.y(), cw, ch)
            except RuntimeError: pass
        self._tick()

    def has_active(self) -> bool:
        """True if any overlay still has active tweens."""
        for lo, so in self._entries.values():
            if lo is not None and not lo._done: return True
            if so is not None and not so._done: return True
        return False

    def paintEvent(self, event):
        painter = QPainter(self)
        if not painter.isActive():
            return
        # Clear to transparent — as a top-level Tool window with
        # WA_TranslucentBackground this correctly shows through to whatever
        # is below (including native X11 GStreamer video windows).
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.transparent)
        if not self._entries:
            painter.end()
            return
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.setRenderHint(QPainter.Antialiasing)
        clip = event.region()
        for cw, (lo, so) in self._entries.items():
            if lo is None and so is None:
                continue
            try:
                g = cw.geometry()
            except RuntimeError:
                continue
            if not clip.intersects(g):
                continue
            x, y, w, h = g.x(), g.y(), g.width(), g.height()
            painter.save()
            painter.translate(x, y)
            painter.setClipRect(0, 0, w, h)
            if lo is not None and not lo._done:
                lo._draw(painter, w, h)
            if so is not None and not so._done:
                so._draw(painter, w, h)
            painter.restore()
        painter.end()

# ──────────────────────── Sentinel ───────────────────────────────

_KEEP_SLANT = object()


# ──────────────────────── Helpers ────────────────────────────────

def _with_alpha(color, alpha):
    c=QColor(color); c.setAlpha(alpha); return c

def _make_font(family, size):
    f=QFont(); f.setFamily(family); f.setPointSizeF(max(0.5,size)); return f

def _hbar(bx, by, bw, bt, both_ends=True):
    bp=bt/2.0
    if both_ends:
        return QPolygonF([QPointF(bx,by),QPointF(bx+bw,by),QPointF(bx+bw+bp,by+bp),
                          QPointF(bx+bw,by+bt),QPointF(bx,by+bt),QPointF(bx-bp,by+bp)])
    return QPolygonF([QPointF(bx,by),QPointF(bx+bw,by),QPointF(bx+bw,by+bt),
                      QPointF(bx,by+bt),QPointF(bx-bp,by+bp)])

def _vbar(bx, by, bt, bh, both_ends=True):
    bp=bt/2.0
    if both_ends:
        return QPolygonF([QPointF(bx,by),QPointF(bx+bp,by-bp),QPointF(bx+bt,by),
                          QPointF(bx+bt,by+bh),QPointF(bx+bp,by+bh+bp),QPointF(bx,by+bh)])
    return QPolygonF([QPointF(bx,by),QPointF(bx+bp,by-bp),QPointF(bx+bt,by),
                      QPointF(bx+bt,by+bh),QPointF(bx,by+bh)])

def _draw_knob(painter, cx, cy, sz, shape):
    if shape=='diamond':
        painter.drawPolygon(QPolygonF([QPointF(cx,cy-sz),QPointF(cx+sz,cy),QPointF(cx,cy+sz),QPointF(cx-sz,cy)]))
    elif shape=='circle': painter.drawEllipse(QPointF(cx,cy),sz,sz)
    else: painter.drawRect(QRectF(cx-sz,cy-sz,sz*2,sz*2))


# ──────────────────────── Style + Tween dataclasses ──────────────

@dataclass(frozen=True)
class TrackStyle:
    color:        QColor=field(default_factory=lambda:QColor(255,255,255,40))
    filled_color: QColor=field(default_factory=lambda:QColor(255,255,255,160))
    thickness:    float=2.0

@dataclass(frozen=True)
class KnobStyle:
    color: QColor=field(default_factory=lambda:QColor(255,255,255))
    size:  float=8.0; shape: str='diamond'

@dataclass(frozen=True)
class MarkStyle:
    tick_color:  QColor=field(default_factory=lambda:QColor(255,255,255,200))
    fill_color:  QColor=field(default_factory=lambda:QColor(255,255,255,35))
    tick_width:  float=3.0; tick_height: float=12.0; tick_gap: float=4.0; rect_height: float=3.0

@dataclass(frozen=True)
class ButtonStyle:
    color:      QColor=field(default_factory=lambda:QColor(255,255,255))
    text_color: QColor=field(default_factory=lambda:QColor(0,0,0))
    font_family: str='Oxanium SemiBold'; font_size: float=10.0
    slant: Optional[Slant]=None

@dataclass
class SliderTween:
    thickness_scale: float=1.0; length_scale: float=1.0
    color: Optional[QColor]=None; filled_color: Optional[QColor]=None
    color_alpha: int=255; filled_alpha: int=255
    start: float=0.0; dur: float=0.3; ease: QEasingCurve.Type=QEasingCurve.Linear
    prev_phase: Optional[str]=None

@dataclass
class KnobTween:
    size_scale: float=1.0; color: Optional[QColor]=None
    start: float=0.0; dur: float=0.3; ease: QEasingCurve.Type=QEasingCurve.Linear
    prev_phase: Optional[str]=None

@dataclass
class MarkTween:
    tick_color: Optional[QColor]=None; fill_color: Optional[QColor]=None; height_scale: float=1.0
    start: float=0.0; dur: float=0.3; ease: QEasingCurve.Type=QEasingCurve.Linear
    prev_phase: Optional[str]=None

@dataclass
class ButtonTween:
    color: QColor=field(default_factory=lambda:QColor(255,255,255))
    w_scale: float=1.0; h_scale: float=1.0
    slant: Any=field(default_factory=lambda:_KEEP_SLANT)
    start: float=0.0; dur: float=0.3; ease: QEasingCurve.Type=QEasingCurve.Linear
    prev_phase: Optional[str]=None


# ──────────────────────── Def dataclasses ────────────────────────

@dataclass
class SliderDef:
    x: float; y: float; length: float; min_val: float; max_val: float; step: float
    value_fn: Callable[[Any],float]; set_fn: Callable[[Any,float],None]
    track: TrackStyle=field(default_factory=TrackStyle)
    knob:  KnobStyle=field(default_factory=KnobStyle)
    mark:  MarkStyle=field(default_factory=MarkStyle)
    track_phases: Dict[str,Phase]=field(default_factory=dict)
    knob_phases:  Dict[str,Phase]=field(default_factory=dict)
    mark_phases:  Dict[str,Phase]=field(default_factory=dict)
    label: str=''; px: Rect=field(default_factory=Rect)
    label_font: str='Oxanium SemiBold'; label_size: float=9.0
    label_color: QColor=field(default_factory=lambda:QColor(255,255,255,130))
    value_text_fn: Optional[Callable[[float,float],str]]=None
    delta_text_fn: Optional[Callable[[float],str]]=None
    vertical: bool=False

@dataclass
class ButtonDef:
    rect: Rect; label: str; action: str
    style:  ButtonStyle=field(default_factory=ButtonStyle)
    phases: Dict[str,Phase]=field(default_factory=dict)
    px:     Rect=field(default_factory=Rect)


# ──────────────────────── _TweenRunner / _Channel ────────────────

class _TweenRunner:
    def __init__(self):
        self._tweens=[]; self._idx=0; self._elapsed=QElapsedTimer()

    def set_phase(self, phase, phases, prev):
        self._idx=0
        p=phases.get(phase)
        self._tweens=[tw for tw in (p.tweens if p else [])
                      if tw.prev_phase is None or tw.prev_phase==prev]
        self._elapsed.restart()

    def progress(self, reset_fn=None):
        while True:
            tw=self._tweens[self._idx] if self._idx<len(self._tweens) else None
            if tw is None: return None,1.0
            if isinstance(tw,Reset):
                if reset_fn: reset_fn()
                self._idx+=1; continue
            el=self._elapsed.elapsed()/1000.0; loc=el-tw.start
            if loc<0: return tw,0.0
            t=min(1.0,loc/tw.dur) if tw.dur>0 else 1.0
            v=_ease(t,tw.ease)
            if t>=1.0: self._idx+=1
            return tw,v

    def done(self): return self._idx>=len(self._tweens)


class _Channel:
    __slots__=('runner','_prev')
    def __init__(self): self.runner=_TweenRunner(); self._prev=''
    def set_phase(self,phase,phases): self.runner.set_phase(phase,phases,self._prev); self._prev=phase
    def progress(self,reset_fn=None): return self.runner.progress(reset_fn)
    def done(self): return self.runner.done()


# ──────────────────────── AnimatedSlider ─────────────────────────

class AnimatedSlider:
    def __init__(self, defn: SliderDef, cam_w=1920, cam_h=1080):
        self.defn=defn; self.cam_w=cam_w; self.cam_h=cam_h
        d=defn
        self._initial_value=self._current_value=0.0
        self._dragging=self._hovered=self._pressed=self._had_change=False
        self.cur_thickness_scale=1.0;  self.cur_length_scale=1.0
        self.cur_track_color=QColor(d.track.color); self.cur_filled_color=QColor(d.track.filled_color)
        self.cur_knob_scale=1.0;       self.cur_knob_color=QColor(d.knob.color)
        self.cur_mark_tick_color=QColor(d.mark.tick_color); self.cur_mark_fill_color=QColor(d.mark.fill_color)
        self.cur_mark_height_scale=1.0
        self._s_thick=1.0; self._s_len=1.0
        self._s_track=QColor(d.track.color); self._s_filled=QColor(d.track.filled_color)
        self._s_kscale=1.0; self._s_kcolor=QColor(d.knob.color)
        self._s_mtick=QColor(d.mark.tick_color); self._s_mfill=QColor(d.mark.fill_color); self._s_mscale=1.0
        self._track_ch=_Channel(); self._knob_ch=_Channel(); self._mark_ch=_Channel()

    def init_value(self,ctx):
        self._initial_value=self._current_value=self.defn.value_fn(ctx); self._had_change=False

    @property
    def has_change(self): return self._current_value!=self._initial_value
    @property
    def delta(self): return self._current_value-self._initial_value
    @property
    def cur_knob_size(self): return self.defn.knob.size*self.cur_knob_scale
    def revert(self): self._current_value=self._initial_value
    def commit(self,ctx): self.defn.set_fn(ctx,self._current_value); self._initial_value=self._current_value

    def _track_screen(self,w,h):
        d=self.defn; tl=d.length*(h if d.vertical else w)+d.px.w
        return d.x*w+d.px.x, d.y*h+d.px.y, tl

    def _v2r(self,v):
        span=self.defn.max_val-self.defn.min_val
        return 0.0 if span==0 else max(0.0,min(1.0,(v-self.defn.min_val)/span))

    def _r2v(self,r):
        d=self.defn; raw=d.min_val+r*(d.max_val-d.min_val)
        if d.step>0: raw=round(raw/d.step)*d.step
        return max(d.min_val,min(d.max_val,raw))

    def hit_test_knob(self,mx,my,w,h):
        tx,ty,tl=self._track_screen(w,h); hs=self.cur_knob_size+6
        if self.defn.vertical: return abs(mx-tx)<=hs and abs(my-(ty+self._v2r(self._current_value)*tl))<=hs
        return abs(mx-(tx+self._v2r(self._current_value)*tl))<=hs and abs(my-ty)<=hs

    def hit_test_knob_global(self,gx,gy,panel):
        return self.hit_test_knob(gx-panel.x(),gy-panel.y(),panel.width(),panel.height())

    def drag_to(self,mx,my,w,h):
        tx,ty,tl=self._track_screen(w,h)
        if tl<=0: return
        r=(my-ty)/tl if self.defn.vertical else (mx-tx)/tl
        self._current_value=self._r2v(max(0.0,min(1.0,r)))

    def drag_to_global(self,gx,gy,panel):
        self.drag_to(gx-panel.x(),gy-panel.y(),panel.width(),panel.height())

    def _set_phase(self,which,phase):
        if which=='track':
            self._s_thick=self.cur_thickness_scale; self._s_len=self.cur_length_scale
            self._s_track=QColor(self.cur_track_color); self._s_filled=QColor(self.cur_filled_color)
            self._track_ch.set_phase(phase,self.defn.track_phases)
        elif which=='knob':
            self._s_kscale=self.cur_knob_scale; self._s_kcolor=QColor(self.cur_knob_color)
            self._knob_ch.set_phase(phase,self.defn.knob_phases)
        else:
            self._s_mtick=QColor(self.cur_mark_tick_color); self._s_mfill=QColor(self.cur_mark_fill_color)
            self._s_mscale=self.cur_mark_height_scale; self._mark_ch.set_phase(phase,self.defn.mark_phases)

    def update(self):
        if self.has_change and not self._had_change:
            self._set_phase('track','changed'); self._set_phase('mark','visible'); self._had_change=True
        elif not self.has_change and self._had_change:
            self._set_phase('track','reverted'); self._set_phase('mark','hidden'); self._had_change=False
        def _rst_t():
            self.cur_thickness_scale=self._s_thick=1.0; self.cur_length_scale=self._s_len=1.0
            self.cur_track_color=self._s_track=QColor(self.defn.track.color)
            self.cur_filled_color=self._s_filled=QColor(self.defn.track.filled_color)
        tw,v=self._track_ch.progress(_rst_t)
        if tw is not None:
            self.cur_thickness_scale=self._s_thick+(tw.thickness_scale-self._s_thick)*v
            self.cur_length_scale   =self._s_len  +(tw.length_scale  -self._s_len  )*v
            self.cur_track_color  =lerp_color(self._s_track,tw.color,v) if tw.color is not None else _with_alpha(self._s_track,int(self._s_track.alpha()+(tw.color_alpha-self._s_track.alpha())*v))
            self.cur_filled_color =lerp_color(self._s_filled,tw.filled_color,v) if tw.filled_color is not None else _with_alpha(self._s_filled,int(self._s_filled.alpha()+(tw.filled_alpha-self._s_filled.alpha())*v))
        def _rst_k():
            self.cur_knob_scale=self._s_kscale=1.0; self.cur_knob_color=self._s_kcolor=QColor(self.defn.knob.color)
        tw,v=self._knob_ch.progress(_rst_k)
        if tw is not None:
            self.cur_knob_scale=self._s_kscale+(tw.size_scale-self._s_kscale)*v
            if tw.color is not None: self.cur_knob_color=lerp_color(self._s_kcolor,tw.color,v)
        def _rst_m():
            self.cur_mark_tick_color=self._s_mtick=QColor(self.defn.mark.tick_color)
            self.cur_mark_fill_color=self._s_mfill=QColor(self.defn.mark.fill_color)
            self.cur_mark_height_scale=self._s_mscale=1.0
        tw,v=self._mark_ch.progress(_rst_m)
        if tw is not None:
            if tw.tick_color is not None: self.cur_mark_tick_color=lerp_color(self._s_mtick,tw.tick_color,v)
            if tw.fill_color is not None: self.cur_mark_fill_color=lerp_color(self._s_mfill,tw.fill_color,v)
            self.cur_mark_height_scale=self._s_mscale+(tw.height_scale-self._s_mscale)*v

    def draw(self,painter,w,h):
        d=self.defn; vert=d.vertical
        tx,ty,tl_base=self._track_screen(w,h)
        tl=tl_base*self.cur_length_scale; tx=tx+(tl_base-tl)/2
        t=d.track.thickness*self.cur_thickness_scale; half=t/2.0
        ratio=self._v2r(self._current_value); init_rat=self._v2r(self._initial_value)
        painter.setPen(Qt.NoPen)
        if vert:
            kpos=ty+ratio*tl; ipos=ty+init_rat*tl
            painter.setBrush(self.cur_track_color); painter.drawPolygon(_vbar(tx-half,ty,t,tl))
            fl=ratio*tl
            if fl>0: painter.setBrush(self.cur_filled_color); painter.drawPolygon(_vbar(tx-half,ty,t,fl,both_ends=(fl>=t)))
            self._draw_mark_v(painter,d.mark,tx,kpos,ipos)
            painter.setBrush(self.cur_knob_color); _draw_knob(painter,tx,kpos,self.cur_knob_size,d.knob.shape)
            self._draw_labels_v(painter,d,tx,ty,tl,kpos)
        else:
            kpos=tx+ratio*tl; ipos=tx+init_rat*tl
            painter.setBrush(self.cur_track_color); painter.drawPolygon(_hbar(tx,ty-half,tl,t))
            fl=ratio*tl
            if fl>0: painter.setBrush(self.cur_filled_color); painter.drawPolygon(_hbar(tx,ty-half,fl,t,both_ends=(fl>=t)))
            self._draw_mark_h(painter,d.mark,ty,kpos,ipos,half)
            painter.setBrush(self.cur_knob_color); _draw_knob(painter,kpos,ty,self.cur_knob_size,d.knob.shape)
            self._draw_labels_h(painter,d,tx,ty,tl,kpos)

    def _draw_mark_v(self,painter,mk,tx,ky,iy):
        if self.cur_mark_tick_color.alpha()==0 and self.cur_mark_fill_color.alpha()==0: return
        fl=abs(ky-iy); my=min(iy,ky); mh=mk.rect_height*self.cur_mark_height_scale
        painter.setBrush(self.cur_mark_fill_color)
        if fl>0: painter.drawPolygon(_vbar(tx-mh/2,my,mh,fl,both_ends=(fl>=mh)))
        th=mk.tick_height*self.cur_mark_height_scale
        painter.setBrush(self.cur_mark_tick_color); painter.drawPolygon(_hbar(tx-th/2,iy-mk.tick_width/2,th,mk.tick_width))

    def _draw_mark_h(self,painter,mk,ty,kx,ix,half):
        if self.cur_mark_tick_color.alpha()==0 and self.cur_mark_fill_color.alpha()==0: return
        fl=abs(kx-ix); mx=min(ix,kx); mh=mk.rect_height*self.cur_mark_height_scale
        painter.setBrush(self.cur_mark_fill_color)
        if fl>0: painter.drawPolygon(_hbar(mx,ty-mh/2,fl,mh,both_ends=(fl>=mh)))
        th=mk.tick_height*self.cur_mark_height_scale
        painter.setBrush(self.cur_mark_tick_color); painter.drawPolygon(_vbar(ix-mk.tick_width/2,ty-th/2,mk.tick_width,th))

    def _draw_labels_v(self,painter,d,tx,ty,tl,kpos):
        if not(d.label or d.value_text_fn or d.delta_text_fn): return
        f=_make_font(d.label_font,d.label_size); fm=QFontMetrics(f)
        lx=int(tx+d.knob.size+6); painter.setFont(f); painter.setPen(d.label_color)
        if d.label: painter.drawText(lx,int(ty+fm.ascent()),d.label)
        if d.value_text_fn:
            txt=d.value_text_fn(self._current_value,self.delta)
            if txt: painter.drawText(lx,int(ty+tl),txt)
        if d.delta_text_fn and self.has_change:
            dt=d.delta_text_fn(self.delta)
            if dt: painter.drawText(int(tx+d.knob.size+6),int(kpos+d.knob.size+6+fm.ascent()),dt)
        painter.setPen(Qt.NoPen)

    def _draw_labels_h(self,painter,d,tx,ty,tl,kpos):
        if not(d.label or d.value_text_fn or d.delta_text_fn): return
        f=_make_font(d.label_font,d.label_size); fm=QFontMetrics(f)
        ly=int(ty-d.knob.size-6); painter.setFont(f); painter.setPen(d.label_color)
        if d.label: painter.drawText(int(tx),ly,d.label)
        if d.value_text_fn:
            txt=d.value_text_fn(self._current_value,self.delta)
            if txt: painter.drawText(int(tx+tl-fm.horizontalAdvance(txt)),ly,txt)
        if d.delta_text_fn and self.has_change:
            dt=d.delta_text_fn(self.delta)
            if dt: painter.drawText(int(kpos-fm.horizontalAdvance(dt)/2),int(ty+d.knob.size+6+fm.ascent()),dt)
        painter.setPen(Qt.NoPen)


# ──────────────────────── AnimatedButton ─────────────────────────

class AnimatedButton:
    def __init__(self,defn:ButtonDef,cam_w=1920,cam_h=1080):
        self.defn=defn; self.cam_w=cam_w; self.cam_h=cam_h
        self._hovered=self._pressed=False; self._prev=''
        self.cur_color=QColor(defn.style.color); self._s_color=QColor(defn.style.color)
        self.cur_w_scale=1.0; self._s_w_scale=1.0
        self.cur_h_scale=1.0; self._s_h_scale=1.0
        self.cur_slant=defn.style.slant; self._start_slant=defn.style.slant
        self._slant_v=1.0; self._runner=_TweenRunner()

    def _set_phase(self,phase):
        self._s_color=QColor(self.cur_color); self._s_w_scale=self.cur_w_scale
        self._s_h_scale=self.cur_h_scale; self._start_slant=self.cur_slant; self._slant_v=0.0
        self._runner.set_phase(phase,self.defn.phases,self._prev); self._prev=phase

    def _screen_rect(self,w,h):
        r=self.defn.rect; px=self.defn.px; bw=r.w*w+px.w; bh=r.h*h+px.h
        sw=bw*self.cur_w_scale; sh=bh*self.cur_h_scale
        return (r.x*w+px.x)+(bw-sw)/2, (r.y*h+px.y)+(bh-sh)/2, sw, sh

    def hit_test(self,mx,my,w,h):
        sx,sy,sw,sh=self._screen_rect(w,h); return sx<=mx<=sx+sw and sy<=my<=sy+sh

    def hit_test_global(self,gx,gy,panel):
        return self.hit_test(gx-panel.x(),gy-panel.y(),panel.width(),panel.height())

    def update(self):
        def _rst():
            self.cur_color=self._s_color=QColor(self.defn.style.color)
            self.cur_w_scale=self._s_w_scale=1.0; self.cur_h_scale=self._s_h_scale=1.0
            self._slant_v=1.0
        tw,v=self._runner.progress(_rst)
        if tw is not None:
            self.cur_color=lerp_color(self._s_color,tw.color,v)
            self.cur_w_scale=self._s_w_scale+(tw.w_scale-self._s_w_scale)*v
            self.cur_h_scale=self._s_h_scale+(tw.h_scale-self._s_h_scale)*v
            self.cur_slant=tw.slant if tw.slant is not _KEEP_SLANT else self._start_slant
            self._slant_v=v
        else: self._slant_v=1.0

    def draw(self,painter,w,h):
        sx,sy,sw,sh=self._screen_rect(w,h)
        painter.setPen(Qt.NoPen); painter.setBrush(self.cur_color)
        pts=lerp_button_slant_pts(sx,sy,sw,sh,self._start_slant,self.cur_slant,self._slant_v)
        if len(pts)==4: painter.drawRect(QRectF(pts[0].x(),pts[0].y(),pts[2].x()-pts[0].x(),pts[2].y()-pts[0].y()))
        else: painter.drawPolygon(QPolygonF(pts))
        st=self.defn.style; f=_make_font(st.font_family,st.font_size); fm=QFontMetrics(f)
        painter.setFont(f); painter.setPen(st.text_color)
        painter.drawText(int(sx+(sw-fm.horizontalAdvance(self.defn.label))/2),
                         int(sy+(sh+fm.ascent())/2-fm.descent()),self.defn.label)
        painter.setPen(Qt.NoPen)


# ──────────────────────── SettingsMouseFilter ────────────────────

class SettingsMouseFilter(QObject):
    def __init__(self,parent=None): super().__init__(parent); self._panel=None
    def set_panel(self,panel): self._panel=panel
    def clear_panel(self): self._panel=None

    def eventFilter(self,obj,event):
        panel=self._panel
        if panel is None or panel._closing: return False
        t=event.type()
        if t not in (QEvent.MouseButtonPress,QEvent.MouseButtonRelease,QEvent.MouseMove): return False
        gpos=event.globalPosition() if hasattr(event,'globalPosition') else event.globalPos()
        gx,gy=gpos.x(),gpos.y()
        g=panel.mapToGlobal(panel.rect().topLeft())
        lx,ly=gx-g.x(),gy-g.y(); pw,ph=float(panel.width()),float(panel.height())

        if t==QEvent.MouseButtonPress:
            if event.button()!=Qt.LeftButton: return False
            for sl in panel._sliders:
                if sl.hit_test_knob(lx,ly,pw,ph):
                    panel._dragging_slider=sl; sl._pressed=True; sl._set_phase('knob','pressed'); return True
            for btn in panel._buttons:
                if btn.hit_test(lx,ly,pw,ph): btn._pressed=True; btn._set_phase('pressed'); return True
            return False
        elif t==QEvent.MouseButtonRelease:
            if event.button()!=Qt.LeftButton: return False
            if panel._dragging_slider is not None:
                sl=panel._dragging_slider; sl._pressed=sl._dragging=False
                sl._set_phase('knob','hovered' if sl._hovered else 'unhovered')
                panel._dragging_slider=None; return True
            for btn in panel._buttons:
                if btn._pressed:
                    btn._pressed=False; btn._set_phase('released')
                    if btn.hit_test(lx,ly,pw,ph): panel._handle_button(btn)
                    return True
            return False
        else:
            if panel._dragging_slider is not None:
                panel._dragging_slider.drag_to(lx,ly,pw,ph); return True
            for sl in panel._sliders:
                now=sl.hit_test_knob(lx,ly,pw,ph)
                if now!=sl._hovered: sl._hovered=now; sl._set_phase('knob','hovered' if now else 'unhovered')
            for btn in panel._buttons:
                now=btn.hit_test(lx,ly,pw,ph)
                if now!=btn._hovered: btn._hovered=now; btn._set_phase('hovered' if now else 'unhovered')
            return False


# ──────────────────────── SettingsOverlay ────────────────────────

class SettingsOverlay(QWidget):
    TICK_MS=16

    def __init__(self,rect_defs,text_defs,slider_defs,button_defs,
                 cam_w=1920,cam_h=1080,line_defs=None):
        super().__init__(None)
        self.setWindowFlags(Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True); self.setFocusPolicy(Qt.StrongFocus)
        self.cam_w=cam_w; self.cam_h=cam_h
        self._rects=[AnimatedRect(d)            for d in rect_defs]
        self._texts=[AnimatedText(d)            for d in text_defs]
        self._sliders=[AnimatedSlider(d,cam_w,cam_h) for d in slider_defs]
        self._buttons=[AnimatedButton(d,cam_w,cam_h) for d in button_defs]
        self._line_defs_override=line_defs; self._lines=[]
        self._context=self._on_apply=self._on_cancel=self._dragging_slider=None
        self._closing=False; self._mouse_filter=None
        self._tick_timer=QTimer(self); self._tick_timer.setInterval(self.TICK_MS)
        self._tick_timer.timeout.connect(self._tick)

    def open(self,context,on_apply=None,on_cancel=None):
        self._context=context; self._on_apply=on_apply; self._on_cancel=on_cancel; self._closing=False
        if not self._lines:
            if self._line_defs_override is not None: defs=self._line_defs_override
            else:
                from spear_gui.overlay_defs import SETTING_LINE_DEFS; defs=SETTING_LINE_DEFS
            self._lines=[AnimatedLine(d) for d in defs]
        for sl in self._sliders:
            sl.init_value(context); sl._set_phase('track','open'); sl._set_phase('knob','open'); sl._set_phase('mark','hidden')
        for btn in self._buttons: btn._set_phase('open')
        self._broadcast('open')
        self.show(); self.raise_(); self.activateWindow(); self.clearMask()
        app=QApplication.instance()
        if app:
            f=SettingsMouseFilter(self); f.set_panel(self); app.installEventFilter(f); self._mouse_filter=f
        self._tick_timer.start()

    def close_panel(self):
        if not self._closing:
            self._closing=True; self._broadcast('close')
            for sl in self._sliders: sl._set_phase('track','close'); sl._set_phase('knob','close'); sl._set_phase('mark','close')
            for btn in self._buttons: btn._set_phase('close')

    def _broadcast(self,phase):
        for r in self._rects: r.set_phase(phase)
        for t in self._texts: t.set_phase(phase)
        for l in self._lines: l.set_phase(phase)

    def _tick(self):
        for r in self._rects: r.update()
        for t in self._texts: t.update()
        for sl in self._sliders: sl.update()
        for btn in self._buttons: btn.update()
        for l in self._lines: l.update()
        if self._closing:
            sl_done=all(sl._track_ch.done() and sl._knob_ch.done() and sl._mark_ch.done() for sl in self._sliders)
            if (all(r.phase_done() for r in self._rects) and all(t.phase_done() for t in self._texts)
                    and sl_done and all(b._runner.done() for b in self._buttons)
                    and all(l.phase_done() for l in self._lines)):
                self._tick_timer.stop(); self.hide()
                if self._mouse_filter:
                    app=QApplication.instance()
                    if app: app.removeEventFilter(self._mouse_filter)
                    self._mouse_filter=None
                self.deleteLater(); return
        self.update()

    def mousePressEvent(self,event):
        if event.button()!=Qt.LeftButton: return
        mx,my=event.position().x(),event.position().y(); w,h=self.width(),self.height()
        for sl in self._sliders:
            if sl.hit_test_knob(mx,my,w,h): self._dragging_slider=sl; sl._pressed=True; sl._set_phase('knob','pressed'); return
        for btn in self._buttons:
            if btn.hit_test(mx,my,w,h): btn._pressed=True; btn._set_phase('pressed'); return

    def mouseMoveEvent(self,event):
        mx,my=event.position().x(),event.position().y(); w,h=self.width(),self.height()
        if self._dragging_slider is not None: self._dragging_slider.drag_to(mx,my,w,h); return
        for sl in self._sliders:
            now=sl.hit_test_knob(mx,my,w,h)
            if now!=sl._hovered: sl._hovered=now; sl._set_phase('knob','hovered' if now else 'unhovered')
        for btn in self._buttons:
            now=btn.hit_test(mx,my,w,h)
            if now!=btn._hovered: btn._hovered=now; btn._set_phase('hovered' if now else 'unhovered')

    def mouseReleaseEvent(self,event):
        if event.button()!=Qt.LeftButton: return
        mx,my=event.position().x(),event.position().y(); w,h=self.width(),self.height()
        if self._dragging_slider is not None:
            sl=self._dragging_slider; sl._pressed=sl._dragging=False
            sl._set_phase('knob','hovered' if sl._hovered else 'unhovered'); self._dragging_slider=None; return
        for btn in self._buttons:
            if btn._pressed:
                btn._pressed=False; btn._set_phase('released')
                if btn.hit_test(mx,my,w,h): self._handle_button(btn); return

    def leaveEvent(self,event):
        for sl in self._sliders:
            if sl._hovered: sl._hovered=False; sl._set_phase('knob','unhovered')
        for btn in self._buttons:
            if btn._hovered: btn._hovered=False; btn._set_phase('unhovered')

    def resizeEvent(self,event): super().resizeEvent(event); self.clearMask()

    def _handle_button(self,btn):
        if btn.defn.action=='apply':
            if self._context:
                for sl in self._sliders: sl.commit(self._context)
            if self._on_apply: self._on_apply()
        else:
            for sl in self._sliders: sl.revert()
            if self._on_cancel: self._on_cancel()
        self.close_panel()

    def paintEvent(self,event):
        painter=QPainter(self)
        if not painter.isActive(): return
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(self.rect(),QColor(0,0,0,1))
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.setRenderHint(QPainter.Antialiasing); painter.setPen(Qt.NoPen)
        w,h=self.width(),self.height()
        for rect in self._rects:
            if rect.hidden: continue
            painter.setBrush(rect.cur_color)
            poly,is_r=rect.get_polygon(w,h,rect.defn.uniform_scale,self.cam_w,self.cam_h)
            if is_r: painter.fillRect(poly.boundingRect(),rect.cur_color)
            else:    painter.drawPolygon(poly)
        painter.setPen(Qt.NoPen)
        for text in self._texts:
            if text.hidden: continue
            label=text.resolve_text(self._context)
            if not label: continue
            font=text.build_font(); painter.setFont(font); painter.setPen(text.cur_color)
            dx,dy=text.resolve_pos(w,h,self.cam_w,self.cam_h,label,font)
            painter.drawText(dx,dy,label); painter.setPen(Qt.NoPen)
        for sl in self._sliders: sl.draw(painter,w,h)
        for btn in self._buttons: btn.draw(painter,w,h)
        for l in self._lines: l.draw(painter,w,h)
        painter.end()


# ──────────────────────── Layout data ────────────────────────────
#
# CAMERA_LAYOUT[cam_index][display_style][active_cams - cam_index]
#
#   cam_index    : 0-based camera slot
#   display_style: which layout style — Left/Right arrows cycle this (wraps)
#   lookup       : max(0, min(active_cams - cam_index, len(style) - 1))
#
# Left/Right arrows  → change display_style (wraps via modulo)
# +/- buttons        → change active camera count (clamped, no wrap)
# Side boxes         → show adjacent display_styles (-1 and +1)

from spear_gui.gui_vars import CAMERA_LAYOUT, CAMERA_LAYOUT_NAMES

NUM_CAM_SLOTS     = len(CAMERA_LAYOUT)       # 8 camera slots
NUM_DISPLAY_MODES = len(CAMERA_LAYOUT[0])    # 3 display styles (0, 1, 2)
MAX_ACTIVE_CAMS   = NUM_CAM_SLOTS            # 8


def cam_pos(cam_index: int, display_style: int, active_cams: int):
    """Return (x, y, w, h) for camera slot cam_index (0-based) in the given
    display_style when active_cams cameras are active.

    lookup = active_cams - cam_index, clamped to [0, len(style)-1]
      >= 1  → visible on screen
      == 0  → staging (invisible)
      <  0  → slot not needed, returns None
    """
    if cam_index < 0 or cam_index >= NUM_CAM_SLOTS:
        return None
    display_style = display_style % NUM_DISPLAY_MODES
    style = CAMERA_LAYOUT[cam_index][display_style]
    lookup = active_cams - cam_index
    if lookup < 0:
        return None
    return style[max(0, min(lookup, len(style) - 1))]


# ──────────────────────── Preview geometry ───────────────────────

BOX_W  = 0.32
BOX_H  = 0.28
BOX_Y  = 0.38

# slot -2,-1,0,+1,+2  (±2 are pre-loaded just off-screen)
SLOT_CX = {-2: 0.50 - 0.72,
           -1: 0.50 - 0.36,
            0: 0.50,
            1: 0.50 + 0.36,
            2: 0.50 + 0.72}

SIDE_SCALE  = 0.72
SIDE_ALPHA  = 140

SCROLL_DUR  = 0.30   # display mode scroll animation
CAM_DUR     = 0.25   # camera count change animation
OPEN_DUR    = 0.40
CLOSE_DUR   = 0.30


# ──────────────────────── CamRect ────────────────────────────────

@dataclass
class CamRect:
    cx: float; cy: float; cw: float; ch: float
    index: int = 0        # 0-based camera slot index
    alpha: int = 255
    _sx: float = 0.0; _sy: float = 0.0; _sw: float = 0.0; _sh: float = 0.0
    _tx: float = 0.0; _ty: float = 0.0; _tw: float = 0.0; _th: float = 0.0
    _s_alpha: int = 255;  _t_alpha: int = 255
    _elapsed: QElapsedTimer = field(default_factory=QElapsedTimer)
    _dur: float = 0.0; _ease: QEasingCurve.Type = QEasingCurve.OutQuint
    _active: bool = False

    def snap(self, x, y, w, h, a=255):
        self.cx=x; self.cy=y; self.cw=w; self.ch=h; self.alpha=a
        self._active=False

    def tween_to(self, x, y, w, h, dur, ease=QEasingCurve.OutQuint, a=255):
        self._sx=self.cx; self._sy=self.cy; self._sw=self.cw; self._sh=self.ch
        self._s_alpha=self.alpha
        self._tx=x; self._ty=y; self._tw=w; self._th=h; self._t_alpha=a
        self._dur=dur; self._ease=ease; self._active=True
        self._elapsed.restart()

    def update(self):
        if not self._active: return
        t = min(1.0, self._elapsed.elapsed()/1000.0/self._dur) if self._dur>0 else 1.0
        v = _ease(t, self._ease)
        self.cx = self._sx+(self._tx-self._sx)*v
        self.cy = self._sy+(self._ty-self._sy)*v
        self.cw = self._sw+(self._tw-self._sw)*v
        self.ch = self._sh+(self._th-self._sh)*v
        self.alpha = int(self._s_alpha+(self._t_alpha-self._s_alpha)*v)
        if t >= 1.0:
            self.cx=self._tx; self.cy=self._ty; self.cw=self._tw; self.ch=self._th
            self.alpha=self._t_alpha; self._active=False

    def done(self): return not self._active


# ──────────────────────── PreviewBox ─────────────────────────────

class PreviewBox:
    """One preview box.
    slot -1 → shows (display_mode - 1) % NUM_DISPLAY_MODES
    slot  0 → shows current display_mode
    slot +1 → shows (display_mode + 1) % NUM_DISPLAY_MODES
    All boxes show the same num_cams; only their display_mode differs.
    """

    def __init__(self, slot: int, display_mode: int, num_cams: int):
        self.slot         = slot
        self.display_mode = (display_mode + slot) % NUM_DISPLAY_MODES
        self.num_cams     = num_cams

        self._scx       = SLOT_CX[slot]
        self._s_scx     = SLOT_CX[slot]; self._t_scx = SLOT_CX[slot]
        self._scx_dur   = 0.0; self._scx_ease = QEasingCurve.OutQuint
        self._scx_timer = QElapsedTimer(); self._scx_active = False

        self._scale   = 1.0 if slot == 0 else SIDE_SCALE
        self._s_scale = self._scale; self._t_scale = self._scale

        self.cams: List[CamRect] = [CamRect(0, 0, 0, 0, index=i) for i in range(NUM_CAM_SLOTS)]
        self._apply_positions(self.display_mode, num_cams, snap=True, alpha=-1)

    def _box_screen(self, sw: int, sh: int) -> Tuple[float, float, float, float]:
        s  = self._scale
        bw = BOX_W * sw * s;  bh = BOX_H * sh * s
        bx = self._scx * sw - bw / 2
        by = BOX_Y * sh + (BOX_H * sh - bh) / 2
        return bx, by, bw, bh

    def _base_alpha(self, override: int) -> int:
        if override >= 0: return override
        return 255 if self.slot == 0 else SIDE_ALPHA

    def _apply_positions(self, display_mode: int, num_cams: int,
                         snap: bool, alpha: int,
                         dur=CAM_DUR, ease=QEasingCurve.OutQuint):
        a = self._base_alpha(alpha)
        for cr in self.cams:
            pos = cam_pos(cr.index, display_mode, num_cams)
            if pos is None:
                cr.snap(cr.cx, cr.cy, 0, 0, 0)
            else:
                x, y, w, h = pos
                lookup = num_cams - cr.index
                tile_alpha = a if lookup >= 1 else 0
                if snap:
                    cr.snap(x, y, w, h, tile_alpha)
                else:
                    cr.tween_to(x, y, w, h, dur, ease, tile_alpha)

    def snap_to(self, display_mode: int, num_cams: int, alpha: int = -1):
        self.display_mode = display_mode; self.num_cams = num_cams
        self._apply_positions(display_mode, num_cams, snap=True, alpha=alpha)

    def tween_to(self, display_mode: int, num_cams: int, dur: float,
                 ease=QEasingCurve.OutQuint, alpha: int = -1):
        self.display_mode = display_mode; self.num_cams = num_cams
        self._apply_positions(display_mode, num_cams, snap=False, alpha=alpha, dur=dur, ease=ease)

    def tween_scx(self, target: float, dur: float, ease=QEasingCurve.OutQuint):
        self._s_scx = self._scx; self._t_scx = target
        self._scx_dur = dur; self._scx_ease = ease
        self._scx_active = True; self._scx_timer.restart()

    def tween_scale(self, target: float):
        self._s_scale = self._scale; self._t_scale = target

    def update(self):
        if self._scx_active:
            raw = self._scx_timer.elapsed() / 1000.0
            t   = min(1.0, raw / self._scx_dur) if self._scx_dur > 0 else 1.0
            v   = _ease(t, self._scx_ease)
            self._scx   = self._s_scx   + (self._t_scx   - self._s_scx)   * v
            self._scale = self._s_scale + (self._t_scale - self._s_scale) * v
            if t >= 1.0:
                self._scx = self._t_scx; self._scale = self._t_scale
                self._scx_active = False
        for cr in self.cams:
            cr.update()

    def all_done(self) -> bool:
        return not self._scx_active and all(c.done() for c in self.cams)

    def draw(self, painter: QPainter, sw: int, sh: int, label_font: QFont):
        bx, by, bw, bh = self._box_screen(sw, sh)
        is_centre = abs(self._scx - 0.5) < 0.08

        # Layout name above the box
        name = CAMERA_LAYOUT_NAMES[self.display_mode % len(CAMERA_LAYOUT_NAMES)]
        name_size  = 13.0 if is_centre else 9.0
        name_alpha = 255  if is_centre else SIDE_ALPHA
        name_font  = _make_font('Oxanium SemiBold', name_size)
        name_fm    = QFontMetrics(name_font)
        name_x     = int(bx + (bw - name_fm.horizontalAdvance(name)) / 2)
        name_y     = int(by - 8)   # 8px gap above the box
        painter.setFont(name_font)
        painter.setPen(QColor(255, 255, 255, name_alpha))
        painter.drawText(name_x, name_y, name)
        painter.setPen(Qt.NoPen)

        # Outer box border — fixed 2px regardless of box size
        pen = QPen(QColor(255, 255, 255, 255 if is_centre else SIDE_ALPHA))
        pen.setWidthF(2.0)
        painter.setPen(pen); painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRectF(bx, by, bw, bh))
        painter.setPen(Qt.NoPen)

        painter.save()
        painter.setClipRect(QRectF(bx, by, bw, bh))
        fm = QFontMetrics(label_font)

        for cr in self.cams:
            if cr.alpha <= 0 or cr.cw <= 0 or cr.ch <= 0:
                continue
            rx = bx + cr.cx * bw;  ry = by + cr.cy * bh
            rw = cr.cw * bw;       rh = cr.ch * bh
            cx1 = max(rx, bx);     cy1 = max(ry, by)
            cx2 = min(rx + rw, bx + bw); cy2 = min(ry + rh, by + bh)
            rw2 = cx2 - cx1;       rh2 = cy2 - cy1
            if rw2 < 1 or rh2 < 1: continue

            fill = QColor(255, 255, 255, max(0, min(255, int(cr.alpha * 0.10))))
            painter.setBrush(fill); painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(cx1, cy1, rw2, rh2))

            # Tile border — fixed 2px
            cam_pen = QPen(QColor(255, 255, 255, max(0, min(255, cr.alpha))))
            cam_pen.setWidthF(2.0)
            painter.setPen(cam_pen); painter.setBrush(Qt.NoBrush)
            painter.drawRect(QRectF(cx1, cy1, rw2, rh2))
            painter.setPen(Qt.NoPen)

            # Label — draw on all boxes (centre and sides), 14px font
            lbl = str(cr.index + 1)
            painter.setFont(label_font)
            painter.setPen(QColor(255, 255, 255, cr.alpha))
            tx = int(cx1 + (rw2 - fm.horizontalAdvance(lbl)) / 2)
            ty = int(cy1 + (rh2 + fm.ascent()) / 2 - fm.descent())
            painter.drawText(tx, ty, lbl)
            painter.setPen(Qt.NoPen)

        painter.restore()


# ──────────────────────── ScrollSystem ───────────────────────────

class ScrollSystem:
    """Five PreviewBoxes at slots -2,-1,0,+1,+2.
    Slots ±2 are pre-loaded just off-screen so the incoming side box is always
    ready before the scroll begins — solving the blank-side-on-first-press issue.

    Left/Right arrows → scroll(direction): cycles display_mode, wraps around.
    +/- buttons       → set_num_cams(n): changes active camera count in place.
    """

    def __init__(self, display_mode: int, num_cams: int):
        self._display_mode = display_mode % NUM_DISPLAY_MODES
        self._num_cams     = max(1, min(num_cams, MAX_ACTIVE_CAMS))
        self._scrolling    = False
        # 5 boxes: slots -2,-1,0,+1,+2
        # ±2 are pre-loaded off-screen so they're ready to slide in immediately
        self._boxes = [PreviewBox(s, self._display_mode, self._num_cams)
                       for s in (-2, -1, 0, 1, 2)]

    def _mode_for_slot(self, slot: int) -> int:
        """Mode that should appear at the given slot given the current _display_mode."""
        return (self._display_mode + slot) % NUM_DISPLAY_MODES

    def _snap_box(self, box, slot):
        """Snap a box's position, scale, content and alpha for the given slot instantly."""
        new_mode = self._mode_for_slot(slot)
        box.slot         = slot
        box._scx         = SLOT_CX[slot]
        box._s_scx       = SLOT_CX[slot]
        box._t_scx       = SLOT_CX[slot]
        box._scx_active  = False
        box._scale       = 1.0 if slot == 0 else SIDE_SCALE
        box._s_scale     = box._scale
        box._t_scale     = box._scale
        box.display_mode = new_mode
        box.num_cams     = self._num_cams
        target_alpha     = 255 if slot == 0 else (SIDE_ALPHA if abs(slot) == 1 else 0)
        for cr in box.cams:
            tgt_pos = cam_pos(cr.index, new_mode, self._num_cams)
            if tgt_pos is None:
                cr.snap(cr.cx, cr.cy, 0, 0, 0)
            else:
                tx, ty, tw, th = tgt_pos
                lookup = self._num_cams - cr.index
                ta = target_alpha if lookup >= 1 else 0
                cr.snap(tx, ty, tw, th, ta)

    def scroll(self, direction: int):
        """Cycle display_mode left (-1) or right (+1). Always wraps."""
        if self._scrolling: return
        self._scrolling = True

        slide = -direction  # boxes move opposite to scroll direction
        new_display_mode = (self._display_mode + direction) % NUM_DISPLAY_MODES

        for box in self._boxes:
            new_slot = box.slot + slide

            if new_slot in SLOT_CX:
                target_cx = SLOT_CX[new_slot]
            else:
                # Slot ±3: sliding fully off-screen, continue past the ±2 edge
                target_cx = SLOT_CX[2] + (new_slot - 2) * 0.36 if new_slot > 2                        else SLOT_CX[-2] + (new_slot + 2) * 0.36

            target_sc = 1.0 if new_slot == 0 else SIDE_SCALE
            box.tween_scx(target_cx, SCROLL_DUR)
            box.tween_scale(target_sc)

            if new_slot == 0:
                # Sliding into centre: positions already correct, brighten alpha
                box.display_mode = (new_display_mode + new_slot) % NUM_DISPLAY_MODES
                box.num_cams     = self._num_cams
                for cr in box.cams:
                    lookup = self._num_cams - cr.index
                    ta = 255 if lookup >= 1 else 0
                    cr.tween_to(cr.cx, cr.cy, cr.cw, cr.ch, SCROLL_DUR,
                                QEasingCurve.OutQuint, ta)
            elif new_slot == 1 or new_slot == -1:
                # Sliding to a visible side slot: already has correct content,
                # tween alpha toward SIDE_ALPHA
                box.display_mode = (new_display_mode + new_slot) % NUM_DISPLAY_MODES
                box.num_cams     = self._num_cams
                for cr in box.cams:
                    lookup = self._num_cams - cr.index
                    ta = SIDE_ALPHA if lookup >= 1 else 0
                    cr.tween_to(cr.cx, cr.cy, cr.cw, cr.ch, SCROLL_DUR,
                                QEasingCurve.OutQuint, ta)
            elif new_slot == 2 or new_slot == -2:
                # Sliding to pre-load slot: tween alpha to 0 (invisible)
                for cr in box.cams:
                    cr.tween_to(cr.cx, cr.cy, cr.cw, cr.ch, SCROLL_DUR,
                                QEasingCurve.OutQuint, 0)
            # new_slot ±3: fully off-screen, _finish_scroll handles recycling

            box.slot = new_slot

        self._display_mode = new_display_mode
        QTimer.singleShot(int(SCROLL_DUR * 1000) + 50, self._finish_scroll)

    def _finish_scroll(self):
        """Snap boxes that slid out of range to the correct pre-load slot."""
        for box in self._boxes:
            if box.slot not in (-2, -1, 0, 1, 2):
                # Slid fully off-screen — teleport to the opposite pre-load slot
                new_slot = -2 if box.slot > 2 else 2
                self._snap_box(box, new_slot)
        self._scrolling = False

    def set_num_cams(self, num_cams: int):
        """Change active camera count. Visible boxes tween; pre-load boxes snap."""
        self._num_cams = max(1, min(num_cams, MAX_ACTIVE_CAMS))
        for box in self._boxes:
            if abs(box.slot) == 2:
                box.snap_to(box.display_mode, self._num_cams, alpha=0)
            else:
                box.tween_to(box.display_mode, self._num_cams, CAM_DUR)

    def open_anim(self):
        for box in self._boxes:
            if abs(box.slot) == 2:
                # Pre-load slot: snap into position silently, stay invisible
                box.snap_to(box.display_mode, self._num_cams, alpha=0)
                continue
            box.snap_to(box.display_mode, self._num_cams, alpha=0)
            for cr in box.cams:
                tgt_pos = cam_pos(cr.index, box.display_mode, self._num_cams)
                if tgt_pos is not None:
                    sx, sy, sw, sh = CAMERA_LAYOUT[cr.index][box.display_mode][0]
                    cr.snap(sx, sy, sw, sh, 0)
                    tx, ty, tw, th = tgt_pos
                    lookup = self._num_cams - cr.index
                    ta = (255 if box.slot == 0 else SIDE_ALPHA) if lookup >= 1 else 0
                    cr.tween_to(tx, ty, tw, th, OPEN_DUR, QEasingCurve.OutQuint, ta)

    def close_anim(self):
        for box in self._boxes:
            for cr in box.cams:
                if cr.alpha > 0 or cr.cw > 0:
                    # Use each camera's own staging position (index 0), not cam 0's
                    sx, sy, sw, sh = CAMERA_LAYOUT[cr.index][box.display_mode][0]
                    cr.tween_to(sx, sy, sw, sh, CLOSE_DUR, QEasingCurve.InQuint, 0)

    def update(self):
        for box in self._boxes: box.update()

    def draw(self, painter: QPainter, sw: int, sh: int, label_font: QFont):
        # Draw in reverse slot-distance order so centre paints on top.
        # Skip ±2 boxes only when fully settled (not while sliding through).
        for box in sorted(self._boxes, key=lambda b: abs(b.slot), reverse=True):
            if abs(box.slot) == 2 and not box._scx_active: continue
            box.draw(painter, sw, sh, label_font)

    def all_done(self) -> bool:
        return all(b.all_done() for b in self._boxes)

    @property
    def display_mode(self) -> int: return self._display_mode
    @property
    def num_cams(self) -> int:     return self._num_cams
    @property
    def scrolling(self) -> bool:   return self._scrolling


# ──────────────────────── CameraSelectOverlay ────────────────────

class CameraSelectOverlay(QWidget):
    TICK_MS = 16

    def __init__(self, parent=None, cam_w=1920, cam_h=1080,
                 initial_display_mode=0, initial_cams=2):
        super().__init__(None)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True); self.setFocusPolicy(Qt.StrongFocus)
        self.cam_w = cam_w; self.cam_h = cam_h

        self._initial_display_mode = initial_display_mode % NUM_DISPLAY_MODES
        self._initial_cams         = max(1, min(initial_cams, MAX_ACTIVE_CAMS))
        self._closing  = False
        self._on_apply = self._on_cancel = None

        self._scroll = ScrollSystem(self._initial_display_mode, self._initial_cams)
        self._filter = None

        from spear_gui.overlay_defs import CS_RECT_DEFS, CS_TEXT_DEFS, CS_BUTTON_DEFS
        self._rects   = [AnimatedRect(d)               for d in CS_RECT_DEFS]
        self._texts   = [AnimatedText(d)               for d in CS_TEXT_DEFS]
        self._buttons = [AnimatedButton(d, cam_w, cam_h) for d in CS_BUTTON_DEFS]

        self._tile_font = _make_font('Oxanium SemiBold', 14.0)

        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(self.TICK_MS)
        self._tick_timer.timeout.connect(self._tick)

    # ── Public API ───────────────────────────────────────────────

    def open(self, on_apply: Callable[[int, int], None] = None,
                   on_cancel: Callable = None):
        """on_apply(display_mode, num_cams)"""
        self._on_apply  = on_apply
        self._on_cancel = on_cancel
        self._closing   = False

        self._scroll = ScrollSystem(self._initial_display_mode, self._initial_cams)
        self._broadcast('open')
        for btn in self._buttons: btn._set_phase('open')
        self._scroll.open_anim()

        self.show(); self.raise_(); self.activateWindow(); self.clearMask()
        f = _CSFilter(self); QApplication.instance().installEventFilter(f)
        self._filter = f
        self._tick_timer.start()

    def close_panel(self):
        if self._closing: return
        self._closing = True
        self._broadcast('close')
        for btn in self._buttons: btn._set_phase('close')
        self._scroll.close_anim()

    def _broadcast(self, phase: str):
        for r in self._rects: r.set_phase(phase)
        for t in self._texts: t.set_phase(phase)

    # ── Controls ─────────────────────────────────────────────────

    def scroll_display_mode(self, direction: int):
        """Left/Right arrows: cycle display mode, wraps around."""
        if self._closing: return
        self._scroll.scroll(direction)

    def change_cams(self, delta: int):
        """+/- buttons: add or remove a camera, clamped."""
        if self._closing: return
        new_n = max(1, min(MAX_ACTIVE_CAMS, self._scroll.num_cams + delta))
        if new_n == self._scroll.num_cams: return
        self._scroll.set_num_cams(new_n)

    # ── Handle buttons ───────────────────────────────────────────

    def _handle_button(self, btn: AnimatedButton):
        action = btn.defn.action
        if action == 'apply':
            if self._on_apply:
                self._on_apply(self._scroll.display_mode, self._scroll.num_cams)
        elif action == 'cancel':
            if self._on_cancel: self._on_cancel()
        elif action == 'scroll_left':
            self.scroll_display_mode(-1); return
        elif action == 'scroll_right':
            self.scroll_display_mode(+1); return
        elif action == 'cam_up':
            self.change_cams(+1); return
        elif action == 'cam_down':
            self.change_cams(-1); return
        if action in ('apply', 'cancel'):
            self.close_panel()

    # ── Tick ─────────────────────────────────────────────────────

    def _tick(self):
        for r   in self._rects:   r.update()
        for t   in self._texts:   t.update()
        for btn in self._buttons: btn.update()
        self._scroll.update()

        if self._closing:
            if (all(r.phase_done() for r in self._rects) and
                    all(t.phase_done() for t in self._texts) and
                    all(b._runner.done() for b in self._buttons) and
                    self._scroll.all_done()):
                self._tick_timer.stop(); self.hide()
                if self._filter:
                    QApplication.instance().removeEventFilter(self._filter)
                    self._filter = None
                self.deleteLater(); return
        self.update()

    # ── Input ────────────────────────────────────────────────────

    def keyPressEvent(self, event):
        k = event.key()
        if   k == Qt.Key_Left:  self.scroll_display_mode(-1)
        elif k == Qt.Key_Right: self.scroll_display_mode(+1)
        elif k == Qt.Key_Up:    self.change_cams(+1)
        elif k == Qt.Key_Down:  self.change_cams(-1)
        elif k in (Qt.Key_Return, Qt.Key_Enter):
            self._handle_button(next(b for b in self._buttons if b.defn.action == 'apply'))
        elif k == Qt.Key_Escape:
            self._handle_button(next(b for b in self._buttons if b.defn.action == 'cancel'))

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton: return
        mx, my = event.position().x(), event.position().y()
        w, h   = self.width(), self.height()
        for btn in self._buttons:
            if btn.hit_test(mx, my, w, h):
                btn._pressed = True; btn._set_phase('pressed'); return

    def mouseMoveEvent(self, event):
        mx, my = event.position().x(), event.position().y()
        w, h   = self.width(), self.height()
        for btn in self._buttons:
            now = btn.hit_test(mx, my, w, h)
            if now != btn._hovered:
                btn._hovered = now
                btn._set_phase('hovered' if now else 'unhovered')

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton: return
        mx, my = event.position().x(), event.position().y()
        w, h   = self.width(), self.height()
        for btn in self._buttons:
            if btn._pressed:
                btn._pressed = False; btn._set_phase('released')
                if btn.hit_test(mx, my, w, h): self._handle_button(btn)
                return

    def leaveEvent(self, event):
        for btn in self._buttons:
            if btn._hovered: btn._hovered = False; btn._set_phase('unhovered')

    def resizeEvent(self, event):
        super().resizeEvent(event); self.clearMask()

    # ── Paint ────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        if not painter.isActive(): return
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 1))
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        w, h = self.width(), self.height()

        for rect in self._rects:
            if rect.hidden: continue
            painter.setBrush(rect.cur_color)
            poly, is_r = rect.get_polygon(w, h, rect.defn.uniform_scale, self.cam_w, self.cam_h)
            if is_r: painter.fillRect(poly.boundingRect(), rect.cur_color)
            else:    painter.drawPolygon(poly)
        painter.setPen(Qt.NoPen)

        self._scroll.draw(painter, w, h, self._tile_font)

        ctx = {
            'display_mode': self._scroll.display_mode,
            'num_cams':     self._scroll.num_cams,
            'max_cams':     MAX_ACTIVE_CAMS,
            'num_modes':    NUM_DISPLAY_MODES,
        }
        for text in self._texts:
            if text.hidden: continue
            label = text.resolve_text(ctx)
            if not label: continue
            font = text.build_font(); painter.setFont(font); painter.setPen(text.cur_color)
            dx, dy = text.resolve_pos(w, h, self.cam_w, self.cam_h, label, font)
            painter.drawText(dx, dy, label); painter.setPen(Qt.NoPen)

        for btn in self._buttons: btn.draw(painter, w, h)
        painter.end()


# ──────────────────────── _CSFilter ──────────────────────────────

class _CSFilter(QObject):
    def __init__(self, panel: CameraSelectOverlay):
        super().__init__(panel); self._panel = panel

    def eventFilter(self, obj, event) -> bool:
        panel = self._panel
        if panel is None or panel._closing: return False
        t = event.type()
        if t not in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease, QEvent.MouseMove):
            return False
        gpos = event.globalPosition() if hasattr(event, 'globalPosition') else event.globalPos()
        gx, gy = gpos.x(), gpos.y()
        g = panel.mapToGlobal(panel.rect().topLeft())
        lx, ly = gx - g.x(), gy - g.y()
        pw, ph = float(panel.width()), float(panel.height())

        if t == QEvent.MouseButtonPress:
            if event.button() != Qt.LeftButton: return False
            for btn in panel._buttons:
                if btn.hit_test(lx, ly, pw, ph):
                    btn._pressed = True; btn._set_phase('pressed'); return True
            return False
        elif t == QEvent.MouseButtonRelease:
            if event.button() != Qt.LeftButton: return False
            for btn in panel._buttons:
                if btn._pressed:
                    btn._pressed = False; btn._set_phase('released')
                    if btn.hit_test(lx, ly, pw, ph): panel._handle_button(btn)
                    return True
            return False
        else:
            for btn in panel._buttons:
                now = btn.hit_test(lx, ly, pw, ph)
                if now != btn._hovered:
                    btn._hovered = now; btn._set_phase('hovered' if now else 'unhovered')
            return False