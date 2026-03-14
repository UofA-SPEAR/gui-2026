from typing import Optional, Dict, List, Tuple, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore  import Qt, QTimer, QElapsedTimer, QEasingCurve
from PySide6.QtGui   import QColor, QPainter, QFont, QFontMetrics, QPolygonF
from PySide6.QtCore  import QPointF


# ──────────────────────── Slant ────────────────────────

class SlantCorner(Enum):
    TOP_LEFT     = 'TL'
    TOP_RIGHT    = 'TR'
    BOTTOM_LEFT  = 'BL'
    BOTTOM_RIGHT = 'BR'

class SlantAngle(Enum):
    DEG_45 = 45
    DEG_22 = 22

class SlantPair(Enum):
    NONE          = 'none'
    PARALLELOGRAM = 'para'
    TRAPEZOID     = 'trap'


@dataclass(frozen=True)
class Slant:
    corner: SlantCorner
    angle:  SlantAngle = SlantAngle.DEG_45
    pair:   SlantPair  = SlantPair.NONE


# ──────────────────────── Rect ────────────────────────

@dataclass(frozen=True)
class Rect:
    x: float = 0.0
    y: float = 0.0
    w: float = 0.0
    h: float = 0.0

_ZERO_RECT = Rect()


# ──────────────────────── Easing cache ────────────────────────

_EASE_CACHE: Dict[QEasingCurve.Type, QEasingCurve] = {}

def _ease(t: float, curve: QEasingCurve.Type) -> float:
    c = _EASE_CACHE.get(curve)
    if c is None:
        c = QEasingCurve(curve)
        _EASE_CACHE[curve] = c
    return c.valueForProgress(t)


# ──────────────────────── Geometry helpers ────────────────────────

_PARA_OPPOSITE: Dict[SlantCorner, SlantCorner] = {
    SlantCorner.TOP_LEFT:     SlantCorner.BOTTOM_RIGHT,
    SlantCorner.TOP_RIGHT:    SlantCorner.BOTTOM_LEFT,
    SlantCorner.BOTTOM_RIGHT: SlantCorner.TOP_LEFT,
    SlantCorner.BOTTOM_LEFT:  SlantCorner.TOP_RIGHT,
}
_TRAP_OPPOSITE: Dict[SlantCorner, SlantCorner] = {
    SlantCorner.TOP_LEFT:     SlantCorner.TOP_RIGHT,
    SlantCorner.TOP_RIGHT:    SlantCorner.TOP_LEFT,
    SlantCorner.BOTTOM_LEFT:  SlantCorner.BOTTOM_RIGHT,
    SlantCorner.BOTTOM_RIGHT: SlantCorner.BOTTOM_LEFT,
}
_SLANT_ORDER: Dict[SlantCorner, Callable] = {
    SlantCorner.TOP_LEFT:     lambda hp, vp: [vp, hp],
    SlantCorner.TOP_RIGHT:    lambda hp, vp: [hp, vp],
    SlantCorner.BOTTOM_RIGHT: lambda hp, vp: [vp, hp],
    SlantCorner.BOTTOM_LEFT:  lambda hp, vp: [hp, vp],
}
_CORNER_IDX: Dict[SlantCorner, int] = {
    SlantCorner.TOP_LEFT:     0,
    SlantCorner.TOP_RIGHT:    1,
    SlantCorner.BOTTOM_RIGHT: 2,
    SlantCorner.BOTTOM_LEFT:  3,
}


def compute_slant_pts(x: float, y: float, w: float, h: float, slant: Slant) -> List[QPointF]:
    d   = min(w, h)
    hd  = d if slant.angle == SlantAngle.DEG_45 else d / 2
    vd  = d
    eps = 1e-4
    hd  = min(hd, w - eps)
    vd  = min(vd, h - eps)

    def cut(c: SlantCorner) -> Tuple[QPointF, QPointF]:
        if c == SlantCorner.TOP_LEFT:
            return QPointF(x + hd,     y    ), QPointF(x,     y + vd    )
        elif c == SlantCorner.TOP_RIGHT:
            return QPointF(x + w - hd, y    ), QPointF(x + w, y + vd    )
        elif c == SlantCorner.BOTTOM_RIGHT:
            return QPointF(x + w - hd, y + h), QPointF(x + w, y + h - vd)
        else:  # BOTTOM_LEFT
            return QPointF(x + hd,     y + h), QPointF(x,     y + h - vd)

    cuts: Dict[SlantCorner, Tuple[QPointF, QPointF]] = {slant.corner: cut(slant.corner)}
    if slant.pair == SlantPair.PARALLELOGRAM:
        c2 = _PARA_OPPOSITE[slant.corner];  cuts[c2] = cut(c2)
    elif slant.pair == SlantPair.TRAPEZOID:
        c2 = _TRAP_OPPOSITE[slant.corner];  cuts[c2] = cut(c2)

    corners_cw = [SlantCorner.TOP_LEFT, SlantCorner.TOP_RIGHT, SlantCorner.BOTTOM_RIGHT, SlantCorner.BOTTOM_LEFT]
    base_pts   = [QPointF(x, y), QPointF(x+w, y), QPointF(x+w, y+h), QPointF(x, y+h)]

    pts: List[QPointF] = []
    for c, base in zip(corners_cw, base_pts):
        if c in cuts:
            hp, vp = cuts[c]
            pts.extend(_SLANT_ORDER[c](hp, vp))
        else:
            pts.append(base)
    return pts


def rect_pts(x: float, y: float, w: float, h: float) -> List[QPointF]:
    return [QPointF(x, y), QPointF(x+w, y), QPointF(x+w, y+h), QPointF(x, y+h)]


def make_pts(x: float, y: float, w: float, h: float, slant: Optional[Slant]) -> List[QPointF]:
    if slant is None:
        return rect_pts(x, y, w, h)
    return compute_slant_pts(x, y, w, h, slant)


def lerp_pts(a: List[QPointF], b: List[QPointF], v: float, insert_idx: int = 0) -> List[QPointF]:
    if len(a) < len(b):
        a = a[:insert_idx] + [a[insert_idx]] + a[insert_idx:]
    elif len(b) < len(a):
        b = b[:insert_idx] + [b[insert_idx]] + b[insert_idx:]
    return [QPointF(pa.x() + (pb.x() - pa.x()) * v, pa.y() + (pb.y() - pa.y()) * v)
            for pa, pb in zip(a, b)]


def lerp_color(src: QColor, dst: QColor, v: float) -> QColor:
    return QColor(
        int(src.red()   + (dst.red()   - src.red())   * v),
        int(src.green() + (dst.green() - src.green()) * v),
        int(src.blue()  + (dst.blue()  - src.blue())  * v),
        int(src.alpha() + (dst.alpha() - src.alpha()) * v),
    )


# ──────────────────────── Tween ────────────────────────

@dataclass
class Tween:
    rect:       Rect
    start:      float
    dur:        float
    ease:       QEasingCurve.Type
    color:      Optional[QColor]  = None
    px:         Rect              = field(default_factory=Rect)
    slant:      Optional[Slant]   = None
    prev_phase: Optional[str]     = None


@dataclass
class TextTween:
    x:          float
    y:          float
    start:      float
    dur:        float
    ease:       QEasingCurve.Type
    color:      Optional[QColor]  = None
    h_align:    float             = 0.0
    v_align:    float             = 0.0
    font_size:  Optional[float]   = None
    px:         float             = 0.0
    py:         float             = 0.0
    prev_phase: Optional[str]     = None


# ──────────────────────── Reset ────────────────────────

@dataclass
class Reset:
    prev_phase:  Optional[str] = None
    start:       float = 0  # always fires immediately — never blocked by local < 0


# ──────────────────────── Phase ────────────────────────

@dataclass
class Phase:
    tweens: list


# ──────────────────────── Rect / Text Defs ────────────────────────

@dataclass
class RectDef:
    rect:          Rect
    color:         QColor
    uniform_scale: bool
    phases:        Dict[str, Phase]
    px:            Rect             = field(default_factory=Rect)
    slant:         Optional[Slant]  = None


@dataclass
class TextDef:
    x:             float
    y:             float
    text:          str
    font_size:     float
    color:         QColor
    phases:        Dict[str, Phase]
    bold:          bool
    italic:        bool
    font_family:   str
    h_align:       float
    v_align:       float
    uniform_scale: bool
    px:            float = 0.0
    py:            float = 0.0
    text_fn:        Optional[Callable[[Any], str]] = None
    always_visible: bool = False


# ──────────────────────── Animated Rect ────────────────────────

class AnimatedRect:
    def __init__(self, defn: RectDef):
        self.defn = defn
        d = defn

        self.cur_rect  = d.rect
        self.cur_px    = d.px
        self.cur_color = QColor(d.color)
        self.cur_slant = d.slant
        self.hidden    = False

        self._current_phase: str  = ''
        self._prev_phase:    str  = ''
        self._tween_idx:     int  = 0
        self._active_tweens: List[Tween] = []

        self._start_rect  = d.rect
        self._start_px    = d.px
        self._start_color = QColor(d.color)
        self._start_slant = d.slant
        self._elapsed_timer = QElapsedTimer()

    def _build_active_tweens(self, phase_name: str, prev: str) -> List[Tween]:
        phase = self.defn.phases.get(phase_name)
        if phase is None:
            return []
        return [tw for tw in phase.tweens if tw.prev_phase is None or tw.prev_phase == prev]

    @property
    def _current_tween(self) -> Optional[Tween]:
        return self._active_tweens[self._tween_idx] if self._tween_idx < len(self._active_tweens) else None

    def _save_start_state(self):
        self._start_rect  = self.cur_rect
        self._start_px    = self.cur_px
        self._start_color = QColor(self.cur_color)
        self._start_slant = self.cur_slant

    def _snap_and_advance(self):
        tw = self._current_tween
        if tw is None:
            return
        self.cur_rect  = tw.rect
        self.cur_px    = tw.px
        self.cur_slant = tw.slant
        if tw.color is not None:
            self.cur_color = QColor(tw.color)
        self._save_start_state()
        self._tween_idx += 1

    def _reset_to_def(self):
        d = self.defn
        self.cur_rect  = d.rect
        self.cur_px    = d.px
        self.cur_color = QColor(d.color)
        self.cur_slant = d.slant
        self._save_start_state()

    def set_phase(self, phase: str):
        prev = self._current_phase
        self._prev_phase    = prev
        self._current_phase = phase
        self._tween_idx     = 0
        self.hidden         = False
        self._active_tweens = self._build_active_tweens(phase, prev)
        self._save_start_state()
        self._elapsed_timer.restart()

    def _is_done(self) -> bool:
        return self._tween_idx >= len(self._active_tweens)

    def update(self):
        if self.hidden:
            return
        elapsed = self._elapsed_timer.elapsed() / 1000.0
        has_px  = self.defn.px != _ZERO_RECT
        while True:
            tw = self._current_tween
            if tw is None:
                return
            local = elapsed - tw.start
            if local < 0:
                return
            if isinstance(tw, Reset):
                self._reset_to_def()
                self._tween_idx += 1
                continue
            t = min(1.0, local / tw.dur) if tw.dur > 0 else 1.0
            v = _ease(t, tw.ease)
            sr, tr = self._start_rect, tw.rect
            self.cur_rect = Rect(
                sr.x + (tr.x - sr.x) * v,
                sr.y + (tr.y - sr.y) * v,
                sr.w + (tr.w - sr.w) * v,
                sr.h + (tr.h - sr.h) * v,
            )
            if has_px:
                sp, tp = self._start_px, tw.px
                self.cur_px = Rect(
                    sp.x + (tp.x - sp.x) * v,
                    sp.y + (tp.y - sp.y) * v,
                    sp.w + (tp.w - sp.w) * v,
                    sp.h + (tp.h - sp.h) * v,
                )
            if tw.color is not None:
                self.cur_color = lerp_color(self._start_color, tw.color, v)
            self.cur_slant = tw.slant if v >= 1.0 else self._start_slant
            if t < 1.0:
                return
            self._snap_and_advance()

    def phase_done(self) -> bool:
        return self._is_done()

    def _to_screen(self, r: Rect, p: Rect, cx: float, cy: float,
                   widget_w: int, widget_h: int, uniform_scale: bool) -> Tuple[float, float, float, float]:
        if uniform_scale:
            sx = (0.5 + (r.x - 0.5) * cx) * widget_w
            sy = (0.5 + (r.y - 0.5) * cy) * widget_h
            sw = r.w * cx * widget_w
            sh = r.h * cy * widget_h
        else:
            sx, sy, sw, sh = r.x * widget_w, r.y * widget_h, r.w * widget_w, r.h * widget_h
        if self.defn.px != _ZERO_RECT:
            sx += p.x;  sy += p.y;  sw += p.w;  sh += p.h
        return sx, sy, sw, sh

    def get_polygon(self, widget_w: int, widget_h: int, uniform_scale: bool,
                    cam_w: int, cam_h: int) -> Tuple[QPolygonF, bool]:

        if uniform_scale:
            scale = min(widget_w / cam_w, widget_h / cam_h)
            cx    = scale / (widget_w / cam_w)
            cy    = scale / (widget_h / cam_h)
        else:
            cx = cy = 1.0

        tw = self._current_tween
        v  = 0.0
        if tw is not None and not isinstance(tw, Reset):
            elapsed = self._elapsed_timer.elapsed() / 1000.0
            local   = elapsed - tw.start
            if local >= 0 and tw.dur > 0:
                v = _ease(min(1.0, local / tw.dur), tw.ease)

        start_pts  = make_pts(*self._to_screen(self._start_rect, self._start_px, cx, cy, widget_w, widget_h, uniform_scale), self._start_slant)
        if tw is not None and not isinstance(tw, Reset):
            target_pts = make_pts(*self._to_screen(tw.rect, tw.px, cx, cy, widget_w, widget_h, uniform_scale), tw.slant)
        else:
            target_pts = make_pts(*self._to_screen(self.cur_rect, self.cur_px, cx, cy, widget_w, widget_h, uniform_scale), self.cur_slant)

        active_slant  = (tw.slant if (tw is not None and not isinstance(tw, Reset) and tw.slant is not None) else self._start_slant)
        active_corner = active_slant.corner if active_slant is not None else None
        pts     = lerp_pts(start_pts, target_pts, v, insert_idx=_CORNER_IDX.get(active_corner, 0))
        is_rect = (len(pts) == 4
                   and pts[0].x() == pts[3].x() and pts[1].x() == pts[2].x()
                   and pts[0].y() == pts[1].y() and pts[2].y() == pts[3].y())
        return QPolygonF(pts), is_rect

    def to_rect(self, w: int, h: int):
        r  = self.cur_rect
        x  = int(r.x * w);   y  = int(r.y * h)
        rw = int(r.w * w);   rh = int(r.h * h)
        if self.defn.px != _ZERO_RECT:
            p   = self.cur_px
            x  += int(p.x);  y  += int(p.y)
            rw += int(p.w);  rh += int(p.h)
        return x, y, rw, rh


# ──────────────────────── Animated Text ────────────────────────

class AnimatedText:
    def __init__(self, defn: TextDef):
        self.defn = defn
        d = defn

        self.cur_x, self.cur_y   = d.x, d.y
        self.cur_px, self.cur_py = d.px, d.py
        self.cur_color           = QColor(d.color)
        self.cur_font_size       = d.font_size
        self.cur_h_align         = d.h_align
        self.cur_v_align         = d.v_align
        self.hidden              = False

        self._current_phase: str = ''
        self._prev_phase:    str = ''
        self._tween_idx:     int = 0
        self._active_tweens: List[TextTween] = []

        self._start_x, self._start_y   = d.x, d.y
        self._start_px, self._start_py = d.px, d.py
        self._start_color              = QColor(d.color)
        self._start_fs                 = d.font_size
        self._start_ha                 = d.h_align
        self._start_va                 = d.v_align
        self._elapsed_timer            = QElapsedTimer()

    def _build_active_tweens(self, phase_name: str, prev: str) -> List[TextTween]:
        phase = self.defn.phases.get(phase_name)
        if phase is None:
            return []
        return [tw for tw in phase.tweens if tw.prev_phase is None or tw.prev_phase == prev]

    @property
    def _current_tween(self) -> Optional[TextTween]:
        return self._active_tweens[self._tween_idx] if self._tween_idx < len(self._active_tweens) else None

    def _save_start_state(self):
        self._start_x,  self._start_y  = self.cur_x,  self.cur_y
        self._start_px, self._start_py = self.cur_px, self.cur_py
        self._start_color              = QColor(self.cur_color)
        self._start_fs                 = self.cur_font_size
        self._start_ha                 = self.cur_h_align
        self._start_va                 = self.cur_v_align

    def _snap_and_advance(self):
        tw = self._current_tween
        if tw is None:
            return
        self.cur_x, self.cur_y     = tw.x, tw.y
        self.cur_px, self.cur_py   = tw.px, tw.py
        self.cur_h_align           = tw.h_align
        self.cur_v_align           = tw.v_align
        if tw.color     is not None: self.cur_color     = QColor(tw.color)
        if tw.font_size is not None: self.cur_font_size = tw.font_size
        self._save_start_state()
        self._tween_idx += 1

    def _reset_to_def(self):
        d = self.defn
        self.cur_x, self.cur_y         = d.x, d.y
        self.cur_px, self.cur_py       = d.px, d.py
        self.cur_color                 = QColor(d.color)
        self.cur_font_size             = d.font_size
        self.cur_h_align               = d.h_align
        self.cur_v_align               = d.v_align
        self._save_start_state()

    def set_phase(self, phase: str):
        prev = self._current_phase
        self._prev_phase    = prev
        self._current_phase = phase
        self._tween_idx     = 0
        self.hidden         = False
        self._active_tweens = self._build_active_tweens(phase, prev)
        self._save_start_state()
        self._elapsed_timer.restart()

    def _is_done(self) -> bool:
        return self._tween_idx >= len(self._active_tweens)

    def update(self):
        if self.hidden:
            return
        elapsed = self._elapsed_timer.elapsed() / 1000.0
        while True:
            tw = self._current_tween
            if tw is None:
                if not self.defn.always_visible:
                    self.hidden = True
                return
            local = elapsed - tw.start
            if local < 0:
                return
            if isinstance(tw, Reset):
                self._reset_to_def()
                self._tween_idx += 1
                continue
            t = min(1.0, local / tw.dur) if tw.dur > 0 else 1.0
            v = _ease(t, tw.ease)
            self.cur_x       = self._start_x  + (tw.x       - self._start_x)  * v
            self.cur_y       = self._start_y  + (tw.y       - self._start_y)  * v
            self.cur_px      = self._start_px + (tw.px      - self._start_px) * v
            self.cur_py      = self._start_py + (tw.py      - self._start_py) * v
            self.cur_h_align = self._start_ha + (tw.h_align - self._start_ha) * v
            self.cur_v_align = self._start_va + (tw.v_align - self._start_va) * v
            if tw.font_size is not None:
                self.cur_font_size = self._start_fs + (tw.font_size - self._start_fs) * v
            if tw.color is not None:
                self.cur_color = lerp_color(self._start_color, tw.color, v)
            if t < 1.0:
                return
            self._snap_and_advance()

    def phase_done(self) -> bool:
        return self._is_done()

    def resolve_text(self, context: Any) -> str:
        template = self.defn.text or ''
        if self.defn.text_fn is not None and context is not None:
            try:
                value = str(self.defn.text_fn(context))
            except Exception:
                value = ''
            if '<#>' in template:
                return template.replace('<#>', value)
            return value
        return template

    def build_font(self) -> QFont:
        f = QFont()
        if self.defn.font_family:
            f.setFamily(self.defn.font_family)
        f.setPointSizeF(max(0.5, self.cur_font_size))
        f.setBold(self.defn.bold)
        f.setItalic(self.defn.italic)
        return f

    def resolve_pos(self, widget_w: int, widget_h: int,
                    cam_w: int, cam_h: int, label: str, font: QFont) -> Tuple[int, int]:
        fm     = QFontMetrics(font)
        text_w = fm.horizontalAdvance(label)
        text_h = fm.ascent()
        if self.defn.uniform_scale:
            scale  = min(widget_w / cam_w, widget_h / cam_h)
            cx     = scale / (widget_w / cam_w)
            cy     = scale / (widget_h / cam_h)
            base_x = (0.5 + (self.cur_x - 0.5) * cx) * widget_w
            base_y = (0.5 + (self.cur_y - 0.5) * cy) * widget_h
        else:
            base_x = self.cur_x * widget_w
            base_y = self.cur_y * widget_h
        base_x += self.cur_px
        base_y += self.cur_py
        draw_x  = base_x - self.cur_h_align * text_w
        draw_y  = base_y + text_h - self.cur_v_align * fm.height()
        return int(draw_x), int(draw_y)


# ──────────────────────── Animated Overlay ────────────────────────

class AnimatedOverlay(QWidget):
    TICK_MS = 16  # ~60 fps

    def __init__(self, rect_defs: List[RectDef], parent=None,
                 cam_w: int = 1920, cam_h: int = 1080,
                 text_defs: Optional[List[TextDef]] = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.cam_w = cam_w
        self.cam_h = cam_h
        self._rects:   List[AnimatedRect] = [AnimatedRect(d) for d in rect_defs]
        self._texts:   List[AnimatedText] = [AnimatedText(d) for d in (text_defs or [])]
        self._context: Any = None
        self._click_target = None  # QWidget whose clicked signal we forward to
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(self.TICK_MS)
        self._tick_timer.timeout.connect(self._tick)

    def set_context(self, context: Any):
        self._context = context

    def _set_phase(self, phase: str):
        for r in self._rects: r.set_phase(phase)
        for t in self._texts: t.set_phase(phase)

    def _tick(self):
        for r in self._rects: r.update()
        for t in self._texts: t.update()
        has_always = any(t.defn.always_visible for t in self._texts)
        all_done   = all(r.hidden for r in self._rects) and all(t.hidden for t in self._texts)
        if all_done and not has_always:
            self._cleanup()
            return
        self.update()

    def _cleanup(self):
        self._tick_timer.stop()
        self.hide()
        try:
            app = QApplication.instance()
            if app:
                for w in app.allWidgets():
                    for attr in ('loading_overlay', 'selection_overlay'):
                        if getattr(w, attr, None) is self:
                            setattr(w, attr, None)
                            break
        except Exception:
            pass
        self.deleteLater()

    def mousePressEvent(self, event):
        # WA_TransparentForMouseEvents is unreliable for top-level windows on
        # some compositors. Forward left-clicks to the camera widget manually.
        if event.button() == Qt.LeftButton and self._click_target is not None:
            try:
                self._click_target.clicked.emit()
            except RuntimeError:
                self._click_target = None
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        if not painter.isActive():
            return
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.transparent)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.setPen(Qt.NoPen)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        for rect in self._rects:
            if rect.hidden:
                continue
            painter.setBrush(rect.cur_color)
            poly, is_rect = rect.get_polygon(w, h, rect.defn.uniform_scale, self.cam_w, self.cam_h)
            if is_rect:
                painter.fillRect(poly.boundingRect(), rect.cur_color)
            else:
                painter.drawPolygon(poly)

        painter.setPen(Qt.NoPen)
        for text in self._texts:
            if text.hidden:
                continue
            label = text.resolve_text(self._context)
            if not label:
                continue
            font = text.build_font()
            painter.setFont(font)
            painter.setPen(text.cur_color)
            dx, dy = text.resolve_pos(w, h, self.cam_w, self.cam_h, label, font)
            painter.drawText(dx, dy, label)
            painter.setPen(Qt.NoPen)

        painter.end()


# ──────────────────────── Loading Overlay ────────────────────────

class LoadingOverlay(AnimatedOverlay):
    def __init__(self, parent=None, cam_w: int = 1920, cam_h: int = 1080):
        super().__init__(LOADING_RECT_DEFS, parent=parent, cam_w=cam_w, cam_h=cam_h,
                         text_defs=LOADING_TEXT_DEFS)

    def start(self):
        self._set_phase('create')
        self.show()
        self._tick_timer.start()

    def notify_loaded(self):
        if any(r._current_phase == 'loaded' for r in self._rects):
            return
        QTimer.singleShot(50, self._do_notify_loaded)

    def _do_notify_loaded(self):
        self._set_phase('loaded')


# ──────────────────────── Selection Overlay ────────────────────────

class SelectionOverlay(AnimatedOverlay):
    def __init__(self, parent=None, cam_w: int = 1920, cam_h: int = 1080):
        super().__init__(SELECTION_RECT_DEFS, parent=parent, cam_w=cam_w, cam_h=cam_h,
                         text_defs=SELECTION_TEXT_DEFS)
        self._pending_unfocus:       Optional[QTimer] = None
        self._last_selection_phase:  str = 'selected'

    def start(self):
        self._last_selection_phase = 'selected'
        self._set_phase('selected')
        self.show()
        self._tick_timer.start()

    def notify_reselected(self):
        if self._pending_unfocus is not None:
            self._pending_unfocus.stop()
            self._pending_unfocus = None
        self._last_selection_phase = 'selected'
        self._set_phase('selected')

    def notify_deselected(self):
        if self._last_selection_phase == 'unselected':
            return
        self._last_selection_phase = 'unselected'
        self._set_phase('unselected')

    def notify_focused(self):
        if self._pending_unfocus is not None:
            self._pending_unfocus.stop()
            self._pending_unfocus = None
            return
        self._set_phase(self._last_selection_phase)

    def notify_unfocused(self):
        if self._pending_unfocus is not None:
            return
        t = QTimer()
        t.setSingleShot(True)
        t.setInterval(0)
        t.timeout.connect(self._do_notify_unfocused)
        t.start()
        self._pending_unfocus = t

    def _do_notify_unfocused(self):
        self._pending_unfocus = None
        self._set_phase('unfocused')

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
        'create': Phase([
            Tween(Rect(0.30, 0.47, 0.20, 0.01), 0.30, 0.25, QEasingCurve.OutCirc),
            Tween(Rect(0.25, 0.45, 0.10, 0.01), 0.55, 0.50, QEasingCurve.InOutCirc, slant=Slant(SlantCorner.TOP_RIGHT)),
        ]),
        'loaded': Phase([
            Tween(Rect(0.25, 0.45, 0.00, 0.01), 0.30, 0.30, QEasingCurve.OutCirc),
        ]),
    }),
    RectDef(Rect(0.50, -0.01, 0.50), QColor(255, 255, 255), True, {
        'create': Phase([
            Tween(Rect(0.50, 0.47, 0.20, 0.01), 0.30, 0.25, QEasingCurve.OutCirc),
            Tween(Rect(0.65, 0.45, 0.10, 0.01), 0.55, 0.50, QEasingCurve.InOutCirc, slant=Slant(SlantCorner.TOP_LEFT)),
        ]),
        'loaded': Phase([
            Tween(Rect(0.75, 0.45, 0.00, 0.01), 0.30, 0.30, QEasingCurve.OutCirc),
        ]),
    }),
    RectDef(Rect(0.00, 1.00, 0.50), QColor(255, 255, 255), True, {
        'create': Phase([
            Tween(Rect(0.30, 0.53 - 0.01, 0.20, 0.01), 0.30, 0.25, QEasingCurve.OutCirc),
            Tween(Rect(0.25, 0.55 - 0.01, 0.10, 0.01), 0.55, 0.50, QEasingCurve.InOutCirc, slant=Slant(SlantCorner.BOTTOM_RIGHT)),
        ]),
        'loaded': Phase([
            Tween(Rect(0.25, 0.55 - 0.01, 0.00, 0.01), 0.30, 0.30, QEasingCurve.OutCirc),
        ]),
    }),
    RectDef(Rect(0.50, 1.00, 0.50), QColor(255, 255, 255), True, {
        'create': Phase([
            Tween(Rect(0.50, 0.53 - 0.01, 0.20, 0.01), 0.30, 0.25, QEasingCurve.OutCirc),
            Tween(Rect(0.65, 0.55 - 0.01, 0.10, 0.01), 0.55, 0.50, QEasingCurve.InOutCirc, slant=Slant(SlantCorner.BOTTOM_LEFT)),
        ]),
        'loaded': Phase([
            Tween(Rect(0.75, 0.55 - 0.01, 0.00, 0.01), 0.30, 0.30, QEasingCurve.OutCirc),
        ]),
    }),

    # Horizontal Thin Corner TL/TR/BL/BR
    RectDef(Rect(0.30, 0.47 + 0.005, 0.20), QColor(255, 255, 255), True, {
        'create': Phase([
            Tween(Rect(0.30,  0.47 + 0.005, 0.20, 0.005), 0.55, 0.00, QEasingCurve.InOutCirc),
            Tween(Rect(0.345, 0.45 + 0.005, 0.10, 0.005), 0.55, 0.50, QEasingCurve.InOutCirc, slant=Slant(SlantCorner.TOP_RIGHT)),
            Tween(Rect(0.345, 0.45 + 0.005, 0.05, 0.005), 1.05, 1.75, QEasingCurve.InCirc,    slant=Slant(SlantCorner.TOP_RIGHT)),
        ]),
        'loaded': Phase([
            Tween(Rect(0.345, 0.45 + 0.005, 0.00, 0.005), 0.00, 0.30, QEasingCurve.OutCirc),
        ]),
    }),
    RectDef(Rect(0.50, 0.47 + 0.005, 0.20), QColor(255, 255, 255), True, {
        'create': Phase([
            Tween(Rect(0.50,  0.47 + 0.005, 0.20, 0.005), 0.55, 0.00, QEasingCurve.InOutCirc),
            Tween(Rect(0.555, 0.45 + 0.005, 0.10, 0.005), 0.55, 0.50, QEasingCurve.InOutCirc, slant=Slant(SlantCorner.TOP_LEFT)),
            Tween(Rect(0.605, 0.45 + 0.005, 0.05, 0.005), 1.05, 1.75, QEasingCurve.InCirc,    slant=Slant(SlantCorner.TOP_LEFT)),
        ]),
        'loaded': Phase([
            Tween(Rect(0.655, 0.45 + 0.005, 0.00, 0.005), 0.00, 0.30, QEasingCurve.OutCirc),
        ]),
    }),
    RectDef(Rect(0.30, 0.53 - 0.01, 0.20), QColor(255, 255, 255), True, {
        'create': Phase([
            Tween(Rect(0.30,  0.53 - 0.01, 0.20, 0.005), 0.55, 0.00, QEasingCurve.InOutCirc),
            Tween(Rect(0.345, 0.55 - 0.01, 0.10, 0.005), 0.55, 0.50, QEasingCurve.InOutCirc, slant=Slant(SlantCorner.BOTTOM_RIGHT)),
            Tween(Rect(0.345, 0.55 - 0.01, 0.05, 0.005), 1.05, 1.75, QEasingCurve.InCirc,    slant=Slant(SlantCorner.BOTTOM_RIGHT)),
        ]),
        'loaded': Phase([
            Tween(Rect(0.345, 0.55 - 0.01, 0.00, 0.005), 0.00, 0.30, QEasingCurve.OutCirc),
        ]),
    }),
    RectDef(Rect(0.50, 0.53 - 0.01, 0.20), QColor(255, 255, 255), True, {
        'create': Phase([
            Tween(Rect(0.50,  0.53 - 0.01, 0.20, 0.005), 0.55, 0.00, QEasingCurve.InOutCirc),
            Tween(Rect(0.555, 0.55 - 0.01, 0.10, 0.005), 0.55, 0.50, QEasingCurve.InOutCirc, slant=Slant(SlantCorner.BOTTOM_LEFT)),
            Tween(Rect(0.605, 0.55 - 0.01, 0.05, 0.005), 1.05, 1.75, QEasingCurve.InCirc,    slant=Slant(SlantCorner.BOTTOM_LEFT)),
        ]),
        'loaded': Phase([
            Tween(Rect(0.655, 0.55 - 0.01, 0.00, 0.005), 0.00, 0.30, QEasingCurve.OutCirc),
        ]),
    }),

    # Vertical Corner TL/BL/TR/BR
    RectDef(Rect(0.00, 0.00, 0.00, 0.50), QColor(255, 255, 255), True, {
        'create': Phase([
            Tween(Rect(0.30, 0.47, 0.005625, 0.03), 0.30, 0.25, QEasingCurve.OutCirc),
            Tween(Rect(0.25, 0.45, 0.005625, 0.02), 0.55, 0.50, QEasingCurve.InOutCirc),
        ]),
        'loaded': Phase([
            Tween(Rect(0.25, 0.47, 0.005625, 0.00), 0.60, 0.30, QEasingCurve.OutCirc),
        ]),
    }),
    RectDef(Rect(0.00, 0.50, 0.00, 0.50), QColor(255, 255, 255), True, {
        'create': Phase([
            Tween(Rect(0.30, 0.50, 0.005625, 0.03), 0.30, 0.25, QEasingCurve.OutCirc),
            Tween(Rect(0.25, 0.53, 0.005625, 0.02), 0.55, 0.50, QEasingCurve.InOutCirc),
        ]),
        'loaded': Phase([
            Tween(Rect(0.25, 0.53, 0.005625, 0.00), 0.60, 0.30, QEasingCurve.OutCirc),
        ]),
    }),
    RectDef(Rect(1.00, 0.00, 0.00, 0.50), QColor(255, 255, 255), True, {
        'create': Phase([
            Tween(Rect(0.70 - 0.005625, 0.47, 0.005625, 0.03), 0.30, 0.25, QEasingCurve.OutCirc),
            Tween(Rect(0.75 - 0.005625, 0.45, 0.005625, 0.02), 0.55, 0.50, QEasingCurve.InOutCirc),
        ]),
        'loaded': Phase([
            Tween(Rect(0.75 - 0.005625, 0.47, 0.005625, 0.00), 0.60, 0.30, QEasingCurve.OutCirc),
        ]),
    }),
    RectDef(Rect(1.00, 0.00, 0.00, 0.50), QColor(255, 255, 255), True, {
        'create': Phase([
            Tween(Rect(0.70 - 0.005625, 0.50, 0.005625, 0.03), 0.30, 0.25, QEasingCurve.OutCirc),
            Tween(Rect(0.75 - 0.005625, 0.53, 0.005625, 0.02), 0.55, 0.50, QEasingCurve.InOutCirc),
        ]),
        'loaded': Phase([
            Tween(Rect(0.75 - 0.005625, 0.53, 0.005625, 0.00), 0.60, 0.30, QEasingCurve.OutCirc),
        ]),
    }),

    # Large Square L/R
    RectDef(Rect(0.50, 0.50), QColor(180, 180, 180), True, {
        'create': Phase([
            Tween(Rect(0.50 - 10/1920, 0.50 - 10/1080, 20/1920, 20/1080), 0.00, 0.30, QEasingCurve.OutCirc),
            Tween(Rect(0.23,           0.50 - 10/1080, 20/1920, 20/1080), 0.30, 1.00, QEasingCurve.OutBack),
        ]),
        'loaded': Phase([
            Tween(Rect(0.25,           0.50 - 10/1080, 0.005625, 20/1080), 0.30, 0.30, QEasingCurve.OutCirc, QColor(255, 255, 255)),
            Tween(Rect(0.25,           0.50,            0.005625, 0),       0.90, 0.30, QEasingCurve.OutCirc),
        ]),
    }),
    RectDef(Rect(0.50, 0.50), QColor(180, 180, 180), True, {
        'create': Phase([
            Tween(Rect(0.50 - 10/1920,      0.50 - 10/1080, 20/1920, 20/1080), 0.00, 0.30, QEasingCurve.OutCirc),
            Tween(Rect(0.77 - 20/1920,      0.50 - 10/1080, 20/1920, 20/1080), 0.30, 1.00, QEasingCurve.OutBack),
        ]),
        'loaded': Phase([
            Tween(Rect(0.75 - 0.005625,     0.50 - 10/1080, 0.005625, 20/1080), 0.30, 0.30, QEasingCurve.OutCirc, QColor(255, 255, 255)),
            Tween(Rect(0.75 - 0.005625,     0.50,            0.005625, 0),       0.90, 0.30, QEasingCurve.OutCirc),
        ]),
    }),

    # Small Square TL/TR/BL/BR
    RectDef(Rect(0.50, 0.50), QColor(180, 180, 180), True, {
        'create': Phase([
            Tween(Rect(0.50 - 5/1920,  0.50 - 5/1080,  10/1920, 10/1080), 0.00, 0.30, QEasingCurve.OutCirc),
            Tween(Rect(0.50 - 70/1920, 0.50 - 70/1080, 10/1920, 10/1080), 0.30, 1.00, QEasingCurve.OutBack),
        ]),
        'loaded': Phase([
            Tween(Rect(0.50 - 5/1920,  0.50 - 70/1080, 10/1920, 10/1080), 0.30, 0.30, QEasingCurve.OutCirc, QColor(255, 255, 255)),
            Tween(Rect(0.50,           0.50),                              0.60, 0.30, QEasingCurve.OutCirc),
        ]),
    }),
    RectDef(Rect(0.50, 0.50), QColor(180, 180, 180), True, {
        'create': Phase([
            Tween(Rect(0.50 - 5/1920,  0.50 - 5/1080,  10/1920, 10/1080), 0.00, 0.30, QEasingCurve.OutCirc),
            Tween(Rect(0.50 + 70/1920, 0.50 - 70/1080, 10/1920, 10/1080), 0.30, 1.00, QEasingCurve.OutBack),
        ]),
        'loaded': Phase([
            Tween(Rect(0.50 - 5/1920,  0.50 - 70/1080, 10/1920, 10/1080), 0.30, 0.30, QEasingCurve.OutCirc, QColor(255, 255, 255)),
            Tween(Rect(0.50,           0.50),                              0.60, 0.30, QEasingCurve.OutCirc),
        ]),
    }),
    RectDef(Rect(0.50, 0.50), QColor(180, 180, 180), True, {
        'create': Phase([
            Tween(Rect(0.50 - 5/1920,  0.50 - 5/1080,  10/1920, 10/1080), 0.00, 0.30, QEasingCurve.OutCirc),
            Tween(Rect(0.50 - 70/1920, 0.50 + 70/1080, 10/1920, 10/1080), 0.30, 1.00, QEasingCurve.OutBack),
        ]),
        'loaded': Phase([
            Tween(Rect(0.50 - 5/1920,  0.50 + 70/1080, 10/1920, 10/1080), 0.30, 0.30, QEasingCurve.OutCirc, QColor(255, 255, 255)),
            Tween(Rect(0.50,           0.50),                              0.60, 0.30, QEasingCurve.OutCirc),
        ]),
    }),
    RectDef(Rect(0.50, 0.50), QColor(180, 180, 180), True, {
        'create': Phase([
            Tween(Rect(0.50 - 5/1920,  0.50 - 5/1080,  10/1920, 10/1080), 0.00, 0.30, QEasingCurve.OutCirc),
            Tween(Rect(0.50 + 70/1920, 0.50 + 70/1080, 10/1920, 10/1080), 0.30, 1.00, QEasingCurve.OutBack),
        ]),
        'loaded': Phase([
            Tween(Rect(0.50 - 5/1920,  0.50 + 70/1080, 10/1920, 10/1080), 0.30, 0.30, QEasingCurve.OutCirc, QColor(255, 255, 255)),
            Tween(Rect(0.50,           0.50),                              0.60, 0.30, QEasingCurve.OutCirc),
        ]),
    }),

    # Progress Bar Outline T/B/L/R
    RectDef(Rect(0.50, 0.50), QColor(120, 120, 120), True, {
        'create': Phase([
            Tween(Rect(0.25 + 0.005625*2, 0.45 + 0.01*2, 0.05625 - 0.005625*2*2, 0.0025), 0.30, 0.70, QEasingCurve.InOutQuad),
            Tween(Rect(0.25 + 0.005625*2, 0.45 + 0.01*2, 0.50    - 0.005625*2*2, 0.0025), 1.00, 1.00, QEasingCurve.InOutQuad),
        ]),
        'loaded': Phase([
            Tween(Rect(0.25 + 0.005625*2, 0.45 + 0.01*2, 0.50 - 0.005625*2*2, 0.0025),          0.30, 0.30, QEasingCurve.InOutQuad, QColor(255, 255, 255)),
            Tween(Rect(-0.2 + 0.25 + 0.005625*2, 0.45 + 0.01*2, 0.00, 0.0025),                  0.60, 1.20, QEasingCurve.OutQuint),
        ]),
    }),
    RectDef(Rect(0.50, 0.50), QColor(120, 120, 120), True, {
        'create': Phase([
            Tween(Rect(0.25 + 0.005625*2, 0.55 - 0.01*2 - 0.0025, 0.05625 - 0.005625*2*2, 0.0025), 0.30, 0.70, QEasingCurve.InOutQuad),
            Tween(Rect(0.25 + 0.005625*2, 0.55 - 0.01*2 - 0.0025, 0.50    - 0.005625*2*2, 0.0025), 1.00, 1.00, QEasingCurve.InOutQuad),
        ]),
        'loaded': Phase([
            Tween(Rect(0.25 + 0.005625*2, 0.55 - 0.01*2 - 0.0025, 0.50 - 0.005625*2*2, 0.0025),                                0.30, 0.30, QEasingCurve.InOutQuad, QColor(255, 255, 255)),
            Tween(Rect(0.2 + 0.25 + 0.005625*2 + 0.50 - 0.005625*2*2, 0.55 - 0.01*2 - 0.0025, 0, 0.0025), 0.60, 1.20, QEasingCurve.OutQuint),
        ]),
    }),
    RectDef(Rect(0.50, 0.50), QColor(120, 120, 120), True, {
        'create': Phase([
            Tween(Rect(0.25 + 0.005625*2, 0.45 + 0.01*2, 0.00140625, 0.10 - 0.01*2*2), 0.30, 0.70, QEasingCurve.InOutQuad),
        ]),
        'loaded': Phase([
            Tween(Rect(0.25 + 0.005625*2, 0.45 + 0.01*2 + 0.10 - 0.01*2*2, 0.00140625, 0.00), 0.30, 0.30, QEasingCurve.OutCirc, QColor(255, 255, 255)),
        ]),
    }),
    RectDef(Rect(0.50, 0.50), QColor(120, 120, 120), True, {
        'create': Phase([
            Tween(Rect(0.25 + 0.005625*2 + 0.05625 - 0.005625*2*2, 0.45 + 0.01*2, 0.00140625, 0.10 - 0.01*2*2),           0.30, 0.70, QEasingCurve.InOutQuad),
            Tween(Rect(0.25 + 0.005625*2 + 0.50 - 0.005625*2*2 - 0.00140625, 0.45 + 0.01*2, 0.00140625, 0.10 - 0.01*2*2), 1.00, 1.00, QEasingCurve.InOutQuad),
        ]),
        'loaded': Phase([
            Tween(Rect(0.25 + 0.005625*2 + 0.50 - 0.005625*2*2 - 0.00140625, 0.45 + 0.01*2, 0.00140625, 0.00), 0.30, 0.30, QEasingCurve.OutCirc, QColor(255, 255, 255)),
        ]),
    }),

    # Progress Bar
    RectDef(Rect(0.50, 0.45 + 0.01*3, 0.00, 0.10 - 0.01*3*2), QColor(255, 255, 255), True, {
        'create': Phase([
            Tween(Rect(0.25 + 0.005625*3, 0.45 + 0.01*3, 0.05625 - 0.005625*3*2, 0.10 - 0.01*3*2), 0.30, 0.70, QEasingCurve.InOutQuad),
            Tween(Rect(0.25 + 0.005625*3, 0.45 + 0.01*3, 0.50    - 0.005625*3*2, 0.10 - 0.01*3*2), 1.00, 1.80, QEasingCurve.InOutCirc),
        ]),
        'loaded': Phase([
            Tween(Rect(0.25 + 0.005625*3, 0.45 + 0.01*3, 0.50 - 0.005625*3*2, 0.10 - 0.01*3*2), 0.00, 0.30, QEasingCurve.OutCirc),
            Tween(Rect(0.50,              0.45 + 0.01*3, 0.00,                 0.10 - 0.01*3*2), 0.30, 0.25, QEasingCurve.OutCirc),
        ]),
    }),
]

LOADING_TEXT_DEFS = []

SELECTION_RECT_DEFS = [
    # Outline T/B/L/R
    RectDef(Rect(), QColor(255, 255, 255), False, {
        'selected': Phase([
            Tween(Rect(0.00, 0.00, 1.00), 0.00, 1.00, QEasingCurve.OutQuint, QColor(255, 255, 255), Rect(0, 0, 0, 2)),
        ]),
        'unselected': Phase([
            Tween(Rect(0.00, 0.00, 1.00), 0.00, 1.00, QEasingCurve.OutQuint, QColor(127, 127, 127), Rect(0, 0, 0, 2)),
        ]),
        'unfocused': Phase([
            Tween(Rect(),                 0.00, 1.00, QEasingCurve.OutQuint, QColor(127, 127, 127), Rect(0, 0, 0, 2)),
        ]),
    }, px=Rect(0, 0, 0, 2)),
    RectDef(Rect(1.00, 1.00), QColor(255, 255, 255), False, {
        'selected': Phase([
            Tween(Rect(0.00, 1.00, 1.00), 0.00, 1.00, QEasingCurve.OutQuint, QColor(255, 255, 255), Rect(0, -2, 0, 2)),
        ]),
        'unselected': Phase([
            Tween(Rect(0.00, 1.00, 1.00), 0.00, 1.00, QEasingCurve.OutQuint, QColor(127, 127, 127), Rect(0, -2, 0, 2)),
        ]),
        'unfocused': Phase([
            Tween(Rect(0.00, 1.00),       0.00, 1.00, QEasingCurve.OutQuint, QColor(127, 127, 127), Rect(0, -2, 0, 2)),
        ]),
    }, px=Rect(0, -2, 0, 2)),
    RectDef(Rect(), QColor(255, 255, 255), False, {
        'selected': Phase([
            Tween(Rect(0.00, 0.00, 0.00, 1.00), 0.00, 1.00, QEasingCurve.OutQuint, QColor(255, 255, 255), Rect(0, 0, 2)),
        ]),
        'unselected': Phase([
            Tween(Rect(0.00, 0.00, 0.00, 1.00), 0.00, 1.00, QEasingCurve.OutQuint, QColor(127, 127, 127), Rect(0, 0, 2)),
        ]),
        'unfocused': Phase([
            Tween(Rect(),                        0.00, 1.00, QEasingCurve.OutQuint, QColor(127, 127, 127), Rect(0, 0, 2)),
        ]),
    }, px=Rect(0, 0, 2)),
    RectDef(Rect(1.00, 1.00), QColor(255, 255, 255), False, {
        'selected': Phase([
            Tween(Rect(1.00, 0.00, 0.00, 1.00), 0.00, 1.00, QEasingCurve.OutQuint, QColor(255, 255, 255), Rect(-2, 0, 2)),
        ]),
        'unselected': Phase([
            Tween(Rect(1.00, 0.00, 0.00, 1.00), 0.00, 1.00, QEasingCurve.OutQuint, QColor(127, 127, 127), Rect(-2, 0, 2)),
        ]),
        'unfocused': Phase([
            Tween(Rect(1.00, 1.00),              0.00, 1.00, QEasingCurve.OutQuint, QColor(127, 127, 127), Rect(-2, 0, 2)),
        ]),
    }, px=Rect(-2, 0, 2)),

    # Corner HTR/VTR/HBL/VBL
    RectDef(Rect(-0.75, 0.00, 0.75), QColor(255, 255, 255), False, {
        'selected': Phase([
            Reset(),
            Tween(Rect(0.50, 0.00, 0.50), 0.00, 0.50, QEasingCurve.InQuint,  px=Rect(-10, 10, 0, 5)),
            Tween(Rect(1.00, 0.00),       0.50, 1.00, QEasingCurve.OutQuint, px=Rect(-30, 10, 20, 5), slant=Slant(SlantCorner.BOTTOM_LEFT)),
        ]),
        'unselected': Phase([
            Tween(Rect(1.00, 0.00),       0.00, 0.50, QEasingCurve.InQuint,  px=Rect(-10, 10, 0, 5)),
        ]),
    }, px=Rect(0, 10, 0, 5)),
    RectDef(Rect(1.00, 0.00), QColor(255, 255, 255), False, {
        'selected': Phase([
            Reset(),
            Tween(Rect(1.00, 0.00), 0.50, 0.50, QEasingCurve.OutQuint, px=Rect(-15, 10, 5, 70), slant=Slant(SlantCorner.BOTTOM_LEFT)),
        ]),
        'unselected': Phase([
            Tween(Rect(1.00, 0.00, 0.00, 1.00), 0.00, 0.50, QEasingCurve.InQuint,  px=Rect(-15, 10, 5)),
            Tween(Rect(1.00, 1.00, 0.00, 1.00), 0.50, 0.50, QEasingCurve.OutQuint, px=Rect(-15, 0,  5)),
        ]),
    }, px=Rect(-15, 10, 5)),
    RectDef(Rect(1.00, 1.00, 0.75), QColor(255, 255, 255), False, {
        'selected': Phase([
            Reset(),
            Tween(Rect(0.00, 1.00, 0.50), 0.00, 0.50, QEasingCurve.InQuint,  px=Rect(10, -15, 0, 5)),
            Tween(Rect(0.00, 1.00),       0.50, 1.00, QEasingCurve.OutQuint, px=Rect(10, -15, 20, 5), slant=Slant(SlantCorner.TOP_RIGHT)),
        ]),
        'unselected': Phase([
            Tween(Rect(0.00, 1.00),       0.00, 0.50, QEasingCurve.InQuint,  px=Rect(10, -15, 0, 5)),
        ]),
    }, px=Rect(0, -15, 0, 5)),
    RectDef(Rect(0.00, 1.00), QColor(255, 255, 255), False, {
        'selected': Phase([
            Reset(),
            Tween(Rect(0.00, 1.00), 0.50, 0.50, QEasingCurve.OutQuint, px=Rect(10, -80, 5, 70), slant=Slant(SlantCorner.TOP_RIGHT)),
        ]),
        'unselected': Phase([
            Tween(Rect(0.00, 0.00, 0.00, 1.00), 0.00, 0.50, QEasingCurve.InQuint,  px=Rect(10, -15, 5)),
            Tween(Rect(0.00, 0.00),              0.50, 0.50, QEasingCurve.OutQuint, px=Rect(10, 0,   5)),
        ]),
    }, px=Rect(10, -15, 5)),
]

SELECTION_TEXT_DEFS = [
    # Camera Name
    TextDef(1.00, 0.00, '', 14.0, QColor(255, 255, 255, 0), {
        'selected': Phase([
            TextTween(1.00, 0.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255, 255, 255, 220), 1.00, 0.00, 14.0, -20, 15),
        ]),
        'unselected': Phase([
            TextTween(1.00, 0.00, 0.00, 0.30, QEasingCurve.OutQuint, QColor(255, 255, 255, 80),  1.00, 0.00, 14.0, -20, 15),
        ]),
        'unfocused': Phase([
            TextTween(1.00, 0.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255, 255, 255, 0),   1.00, 0.00, 14.0, -20, 15),
        ]),
    }, True, False, 'Oxanium SemiBold', 1.00, 0.00, False, 0, 15, lambda cam: cam.name, True),

    # Camera Serial
    TextDef(1.00, 0.00, '', 14.0, QColor(255, 255, 255, 0), {
        'selected': Phase([
            TextTween(1.00, 0.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255, 255, 255, 220), 1.00, 0.00, 14.0, -20, 35),
        ]),
        'unselected': Phase([
            TextTween(1.00, 0.00, 0.00, 0.30, QEasingCurve.OutQuint, QColor(255, 255, 255, 80),  1.00, 0.00, 14.0, -20, 35),
        ]),
        'unfocused': Phase([
            TextTween(1.00, 0.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255, 255, 255, 0),   1.00, 0.00, 14.0, -20, 35),
        ]),
    }, True, False, 'Oxanium SemiBold', 1.00, 0.00, False, 0, 15, lambda cam: cam.serial, True),

    # Camera Name
    TextDef(0.00, 0.00, 'CAMERA #<#>', 14.0, QColor(255, 255, 255, 0), {
        'selected': Phase([
            TextTween(0.00, 0.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255, 255, 255, 220), 0.00, 0.00, 14.0, 20, 15),
        ]),
        'unselected': Phase([
            TextTween(0.00, 0.00, 0.00, 0.30, QEasingCurve.OutQuint, QColor(255, 255, 255, 80),  0.00, 0.00, 14.0, 20, 15),
        ]),
        'unfocused': Phase([
            TextTween(0.00, 0.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255, 255, 255, 0),   0.00, 0.00, 14.0, 20, 15),
        ]),
    }, True, False, 'Oxanium SemiBold', 1.00, 0.00, False, 0, 15, lambda cam: cam.position, True),

    # Camera Exposure
    TextDef(0.00, 1.00, 'EXPOSURE: <#>', 9.0, QColor(255, 255, 255, 0), {
        'selected': Phase([
            TextTween(0.00, 1.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255, 255, 255, 220), 0.00, 1.00, 9.0, 20, -15),
        ]),
        'unselected': Phase([
            TextTween(0.00, 1.00, 0.00, 0.30, QEasingCurve.OutQuint, QColor(255, 255, 255, 80),  0.00, 1.00, 9.0, 20, -15),
        ]),
        'unfocused': Phase([
            TextTween(0.00, 1.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255, 255, 255, 0),   0.00, 1.00, 9.0, 20, -15),
        ]),
    }, False, False, 'Oxanium SemiBold', 1.00, 1.00, False, 0, -15, lambda cam: cam.exposure, True),

    # Camera Gain
    TextDef(0.00, 1.00, 'GAIN: <#>', 9.0, QColor(255, 255, 255, 0), {
        'selected': Phase([
            TextTween(0.00, 1.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255, 255, 255, 220), 0.00, 1.00, 9.0, 20, -30),
        ]),
        'unselected': Phase([
            TextTween(0.00, 1.00, 0.00, 0.30, QEasingCurve.OutQuint, QColor(255, 255, 255, 80),  0.00, 1.00, 9.0, 20, -30),
        ]),
        'unfocused': Phase([
            TextTween(0.00, 1.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255, 255, 255, 0),   0.00, 1.00, 9.0, 20, -30),
        ]),
    }, False, False, 'Oxanium SemiBold', 1.00, 1.00, False, 0, -15, lambda cam: cam.gain, True),

    # Camera Gamma
    TextDef(0.00, 1.00, 'GAMMA: <#>', 9.0, QColor(255, 255, 255, 0), {
        'selected': Phase([
            TextTween(0.00, 1.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255, 255, 255, 220), 0.00, 1.00, 9.0, 20, -45),
        ]),
        'unselected': Phase([
            TextTween(0.00, 1.00, 0.00, 0.30, QEasingCurve.OutQuint, QColor(255, 255, 255, 80),  0.00, 1.00, 9.0, 20, -45),
        ]),
        'unfocused': Phase([
            TextTween(0.00, 1.00, 0.00, 0.40, QEasingCurve.OutQuint, QColor(255, 255, 255, 0),   0.00, 1.00, 9.0, 20, -45),
        ]),
    }, False, False, 'Oxanium SemiBold', 1.00, 1.00, False, 0, -15, lambda cam: cam.gamma, True),
]