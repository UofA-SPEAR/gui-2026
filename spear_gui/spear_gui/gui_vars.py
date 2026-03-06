class Tween:
    def __init__(self, x, y, w, h, s, d, p, e, c):
        self.tx, self.ty, self.tw, self.th = x, y, w, h
        self.tween_start = s
        self.tween_dur = d
        self.phase = p
        self.ease = e
        self.color = c

class RectDef:
    def __init__(self, x, y, w, h, initial_color, is_uniform_scale, tween):
        self.ix, self.iy, self.iw, self.ih = x, y, w, h
        self.color = initial_color
        self.uniform_scale = is_uniform_scale
        self.tweens = tween

RECT_DEFS = [
    # Background T/B/L/R
    RectDef(0.00, 0.00, 1.00, 0.50, QColor(10, 10, 14), False, [
        Tween(0.00, 0.00, 1.00, 0.00, 0.30, 1.00, 'loaded', QEasingCurve.OutQuint, None)]),
    RectDef(0.00, 0.50, 1.00, 0.50, QColor(10, 10, 14), False, [
        Tween(0.00, 1.00, 1.00, 0.00, 0.30, 1.00, 'loaded', QEasingCurve.OutQuint, None)]),
    RectDef(0.00, 0.00, 0.50, 1.00, QColor(10, 10, 14), False, [
        Tween(0.00, 0.00, 0.00, 1.00, 0.30, 1.00, 'loaded', QEasingCurve.OutQuint, None)]),
    RectDef(0.50, 0.00, 0.50, 1.00, QColor(10, 10, 14), False, [
        Tween(1.00, 0.00, 0.00, 1.00, 0.30, 1.00, 'loaded', QEasingCurve.OutQuint, None)]),

    # Horizontal Corner TL/TR/BL/BR
    RectDef(0.00, -0.01, 0.50, 0, QColor(255, 255, 255), True, [
        Tween(0.30, 0.47, 0.20, 0.01, 0.30, 0.25, 'create', QEasingCurve.OutCirc, None),
        Tween(0.25, 0.45, 0.10, 0.01, 0.55, 0.50, 'create', QEasingCurve.InOutCirc, None),
        Tween(0.25, 0.45, 0.00, 0.01, 0.30, 0.30, 'loaded', QEasingCurve.OutCirc, None),
    ]),
    RectDef(0.50, -0.01, 0.50, 0, QColor(255, 255, 255), True, [
        Tween(0.50, 0.47, 0.20, 0.01, 0.30, 0.25, 'create', QEasingCurve.OutCirc, None),
        Tween(0.65, 0.45, 0.10, 0.01, 0.55, 0.50, 'create', QEasingCurve.InOutCirc, None),
        Tween(0.75, 0.45, 0.00, 0.01, 0.30, 0.30, 'loaded', QEasingCurve.OutCirc, None),
    ]),
    RectDef(0.00, 1.00, 0.50, 0, QColor(255, 255, 255), True, [
        Tween(0.30, 0.53 - 0.01, 0.20, 0.01, 0.30, 0.25, 'create', QEasingCurve.OutCirc, None),
        Tween(0.25, 0.55 - 0.01, 0.10, 0.01, 0.55, 0.50, 'create', QEasingCurve.InOutCirc, None),
        Tween(0.25, 0.55 - 0.01, 0.00, 0.01, 0.30, 0.30, 'loaded', QEasingCurve.OutCirc, None),
    ]),
    RectDef(0.50, 1.00, 0.50, 0, QColor(255, 255, 255), True, [
        Tween(0.50, 0.53 - 0.01, 0.20, 0.01, 0.30, 0.25, 'create', QEasingCurve.OutCirc, None),
        Tween(0.65, 0.55 - 0.01, 0.10, 0.01, 0.55, 0.50, 'create', QEasingCurve.InOutCirc, None),
        Tween(0.75, 0.55 - 0.01, 0.00, 0.01, 0.30, 0.30, 'loaded', QEasingCurve.OutCirc, None),
    ]),

    # Horizontal Thin Corner TL/TR/BL/BR
    RectDef(0.30, 0.47 + 0.005, 0.20, 0.00, QColor(255, 255, 255), True, [
        Tween(0.30, 0.47 + 0.005, 0.20, 0.005, 0.55, 0.00, 'create', QEasingCurve.InOutCirc, None),
        Tween(0.345, 0.45 + 0.005, 0.10, 0.005, 0.55, 0.50, 'create', QEasingCurve.InOutCirc, None),
        Tween(0.345, 0.45 + 0.005, 0.05, 0.005, 1.05, 1.75, 'create', QEasingCurve.InCirc, None),
        Tween(0.345, 0.45 + 0.005, 0.00, 0.005, 0.00, 0.30, 'loaded', QEasingCurve.OutCirc, None),
    ]),
    RectDef(0.50, 0.47 + 0.005, 0.20, 0.00, QColor(255, 255, 255), True, [
        Tween(0.50, 0.47 + 0.005, 0.20, 0.005, 0.55, 0.00, 'create', QEasingCurve.InOutCirc, None),
        Tween(0.555, 0.45 + 0.005, 0.10, 0.005, 0.55, 0.50, 'create', QEasingCurve.InOutCirc, None),
        Tween(0.605, 0.45 + 0.005, 0.05, 0.005, 1.05, 1.75, 'create', QEasingCurve.InCirc, None),
        Tween(0.655, 0.45 + 0.005, 0.00, 0.005, 0.00, 0.30, 'loaded', QEasingCurve.OutCirc, None),
    ]),
    RectDef(0.30, 0.53 - 0.01, 0.20, 0.00, QColor(255, 255, 255), True, [
        Tween(0.30, 0.53 - 0.01, 0.20, 0.005, 0.55, 0.00, 'create', QEasingCurve.InOutCirc, None),
        Tween(0.345, 0.55 - 0.01, 0.10, 0.005, 0.55, 0.50, 'create', QEasingCurve.InOutCirc, None),
        Tween(0.345, 0.55 - 0.01, 0.05, 0.005, 1.05, 1.75, 'create', QEasingCurve.InCirc, None),
        Tween(0.345, 0.55 - 0.01, 0.00, 0.005, 0.00, 0.30, 'loaded', QEasingCurve.OutCirc, None),
    ]),
    RectDef(0.50, 0.53 - 0.01, 0.20, 0.00, QColor(255, 255, 255), True, [
        Tween(0.50, 0.53 - 0.01, 0.20, 0.005, 0.55, 0.00, 'create', QEasingCurve.InOutCirc, None),
        Tween(0.555, 0.55 - 0.01, 0.10, 0.005, 0.55, 0.50, 'create', QEasingCurve.InOutCirc, None),
        Tween(0.605, 0.55 - 0.01, 0.05, 0.005, 1.05, 1.75, 'create', QEasingCurve.InCirc, None),
        Tween(0.655, 0.55 - 0.01, 0.00, 0.005, 0.00, 0.30, 'loaded', QEasingCurve.OutCirc, None),
    ]),

    # Vertical Corner TL/BL/TR/BR
    RectDef(0.00, 0.00, 0.00, 0.50, QColor(255, 255, 255), True, [
        Tween(0.30, 0.47, 0.005625, 0.03, 0.30, 0.25, 'create', QEasingCurve.OutCirc, None),
        Tween(0.25, 0.45, 0.005625, 0.02, 0.55, 0.50, 'create', QEasingCurve.InOutCirc, None),
        Tween(0.25, 0.47, 0.005625, 0.00, 0.60, 0.30, 'loaded', QEasingCurve.OutCirc, None),
    ]),
    RectDef(0.00, 0.50, 0.00, 0.50, QColor(255, 255, 255), True, [
        Tween(0.30, 0.50, 0.005625, 0.03, 0.30, 0.25, 'create', QEasingCurve.OutCirc, None),
        Tween(0.25, 0.53, 0.005625, 0.02, 0.55, 0.50, 'create', QEasingCurve.InOutCirc, None),
        Tween(0.25, 0.53, 0.005625, 0.00, 0.60, 0.30, 'loaded', QEasingCurve.OutCirc, None),
    ]),
    RectDef(1.00, 0.00, 0.00, 0.50, QColor(255, 255, 255), True, [
        Tween(0.70 - 0.005625, 0.47, 0.005625, 0.03, 0.30, 0.25, 'create', QEasingCurve.OutCirc, None),
        Tween(0.75 - 0.005625, 0.45, 0.005625, 0.02, 0.55, 0.50, 'create', QEasingCurve.InOutCirc, None),
        Tween(0.75 - 0.005625, 0.47, 0.005625, 0.00, 0.60, 0.30, 'loaded', QEasingCurve.OutCirc, None),
    ]),
    RectDef(1.00, 0.00, 0.00, 0.50, QColor(255, 255, 255), True, [
        Tween(0.70 - 0.005625, 0.50, 0.005625, 0.03, 0.30, 0.25, 'create', QEasingCurve.OutCirc, None),
        Tween(0.75 - 0.005625, 0.53, 0.005625, 0.02, 0.55, 0.50, 'create', QEasingCurve.InOutCirc, None),
        Tween(0.75 - 0.005625, 0.53, 0.005625, 0.00, 0.60, 0.30, 'loaded', QEasingCurve.OutCirc, None),
    ]),

    # Large Squares L/R
    RectDef(0.50, 0.50, 0.00, 0.00, QColor(180, 180, 180), True, [
        Tween(0.50 - 10/1920, 0.50 - 10/1080, 20/1920, 20/1080, 0.00, 0.30, 'create', QEasingCurve.OutCirc, None),
        Tween(0.23, 0.50 - 10/1080, 20/1920, 20/1080, 0.30, 1.00, 'create', QEasingCurve.OutBack, None),
        Tween(0.25, 0.50 - 10/1080, 0.005625, 20/1080, 0.30, 0.30, 'loaded', QEasingCurve.OutCirc, QColor(255, 255, 255)),
        Tween(0.25, 0.50, 0.005625, 0, 0.90, 0.30, 'loaded', QEasingCurve.OutCirc, None),
    ]),
    RectDef(0.50, 0.50, 0.00, 0.00, QColor(180, 180, 180), True, [
        Tween(0.50 - 10/1920, 0.50 - 10/1080, 20/1920, 20/1080, 0.00, 0.30, 'create', QEasingCurve.OutCirc, None),
        Tween(0.77 - 20/1920, 0.50 - 10/1080, 20/1920, 20/1080, 0.30, 1.00, 'create', QEasingCurve.OutBack, None),
        Tween(0.75 - 0.005625, 0.50 - 10/1080, 0.005625, 20/1080, 0.30, 0.30, 'loaded', QEasingCurve.OutCirc, QColor(255, 255, 255)),
        Tween(0.75 - 0.005625, 0.50, 0.005625, 0, 0.90, 0.30, 'loaded', QEasingCurve.OutCirc, None),
    ]),

    # Small Squares TL/TR/BL/BR
    RectDef(0.50, 0.50, 0.00, 0.00, QColor(180, 180, 180), True, [
        Tween(0.50 - 5/1920, 0.50 - 5/1080, 10/1920, 10/1080, 0.00, 0.30, 'create', QEasingCurve.OutCirc, None),
        Tween(0.50 - 70/1920, 0.50 - 70/1080, 10/1920, 10/1080, 0.30, 1.00, 'create', QEasingCurve.OutBack, None),
        Tween(0.50 - 5/1920, 0.50 - 70/1080, 10/1920, 10/1080, 0.30, 0.30, 'loaded', QEasingCurve.OutCirc, QColor(255, 255, 255)),
        Tween(0.50, 0.50, 0.00, 0.00, 0.60, 0.30, 'loaded', QEasingCurve.OutCirc, None),
    ]),
    RectDef(0.50, 0.50, 0.00, 0.00, QColor(180, 180, 180), True, [
        Tween(0.50 - 5/1920, 0.50 - 5/1080, 10/1920, 10/1080, 0.00, 0.30, 'create', QEasingCurve.OutCirc, None),
        Tween(0.50 + 70/1920, 0.50 - 70/1080, 10/1920, 10/1080, 0.30, 1.00, 'create', QEasingCurve.OutBack, None),
        Tween(0.50 - 5/1920, 0.50 - 70/1080, 10/1920, 10/1080, 0.30, 0.30, 'loaded', QEasingCurve.OutCirc, QColor(255, 255, 255)),
        Tween(0.50, 0.50, 0.00, 0.00, 0.60, 0.30, 'loaded', QEasingCurve.OutCirc, None),
    ]),
    RectDef(0.50, 0.50, 0.00, 0.00, QColor(180, 180, 180), True, [
        Tween(0.50 - 5/1920, 0.50 - 5/1080, 10/1920, 10/1080, 0.00, 0.30, 'create', QEasingCurve.OutCirc, None),
        Tween(0.50 - 70/1920, 0.50 + 70/1080, 10/1920, 10/1080, 0.30, 1.00, 'create', QEasingCurve.OutBack, None),
        Tween(0.50 - 5/1920, 0.50 + 70/1080, 10/1920, 10/1080, 0.30, 0.30, 'loaded', QEasingCurve.OutCirc, QColor(255, 255, 255)),
        Tween(0.50, 0.50, 0.00, 0.00, 0.60, 0.30, 'loaded', QEasingCurve.OutCirc, None),
    ]),
    RectDef(0.50, 0.50, 0.00, 0.00, QColor(180, 180, 180), True, [
        Tween(0.50 - 5/1920, 0.50 - 5/1080, 10/1920, 10/1080, 0.00, 0.30, 'create', QEasingCurve.OutCirc, None),
        Tween(0.50 + 70/1920, 0.50 + 70/1080, 10/1920, 10/1080, 0.30, 1.00, 'create', QEasingCurve.OutBack, None),
        Tween(0.50 - 5/1920, 0.50 + 70/1080, 10/1920, 10/1080, 0.30, 0.30, 'loaded', QEasingCurve.OutCirc, QColor(255, 255, 255)),
        Tween(0.50, 0.50, 0.00, 0.00, 0.60, 0.30, 'loaded', QEasingCurve.OutCirc, None),
    ]),

    # Progress Bar Outline T/B/L/R
    RectDef(0.50, 0.50, 0.00, 0.00, QColor(120, 120, 120), True, [
        Tween(0.25 + 0.005625 * 2, 0.45 + 0.01 * 2, 0.05625 - 0.005625 * 2 * 2, 0.0025, 0.30, 0.70, 'create', QEasingCurve.InOutQuad, None),
        Tween(0.25 + 0.005625 * 2, 0.45 + 0.01 * 2, 0.50 - 0.005625 * 2 * 2, 0.0025, 1.00, 1.00, 'create', QEasingCurve.InOutQuad, None),
        Tween(0.25 + 0.005625 * 2, 0.45 + 0.01 * 2, 0.50 - 0.005625 * 2 * 2, 0.0025, 0.30, 0.30, 'loaded', QEasingCurve.InOutQuad, QColor(255, 255, 255)),
        Tween(-0.2 + 0.25 + 0.005625 * 2, 0.45 + 0.01 * 2, 0.00, 0.0025, 0.60, 1.20, 'loaded', QEasingCurve.OutQuint, None),
    ]),
    RectDef(0.50, 0.50, 0.00, 0.00, QColor(120, 120, 120), True, [
        Tween(0.25 + 0.005625 * 2, 0.55 - 0.01 * 2 - 0.0025, 0.05625 - 0.005625 * 2 * 2, 0.0025, 0.30, 0.70, 'create', QEasingCurve.InOutQuad, None),
        Tween(0.25 + 0.005625 * 2, 0.55 - 0.01 * 2 - 0.0025, 0.50 - 0.005625 * 2 * 2, 0.0025, 1.00, 1.00, 'create', QEasingCurve.InOutQuad, None),
        Tween(0.25 + 0.005625 * 2, 0.55 - 0.01 * 2 - 0.0025, 0.50 - 0.005625 * 2 * 2, 0.0025, 0.30, 0.30, 'loaded', QEasingCurve.InOutQuad, QColor(255, 255, 255)),
        Tween(0.2 + 0.25 + 0.005625 * 2 + 0.50 - 0.005625 * 2 * 2, 0.55 - 0.01 * 2 - 0.0025, 0, 0.0025, 0.60, 1.20, 'loaded', QEasingCurve.OutQuint, None),
    ]),
    RectDef(0.50, 0.50, 0.00, 0.00, QColor(120, 120, 120), True, [
        Tween(0.25 + 0.005625 * 2, 0.45 + 0.01 * 2, 0.00140625, 0.10 - 0.01 * 2 * 2, 0.30, 0.70, 'create', QEasingCurve.InOutQuad, None),
        Tween(0.25 + 0.005625 * 2, 0.45 + 0.01 * 2 + 0.10 - 0.01 * 2 * 2, 0.00140625, 0.00, 0.30, 0.30, 'loaded', QEasingCurve.OutCirc, QColor(255, 255, 255)),
    ]),
    RectDef(0.50, 0.50, 0.00, 0.00, QColor(120, 120, 120), True, [
        Tween(0.25 + 0.005625 * 2 + 0.05625 - 0.005625 * 2 * 2, 0.45 + 0.01 * 2, 0.00140625, 0.10 - 0.01 * 2 * 2, 0.30, 0.70, 'create', QEasingCurve.InOutQuad, None),
        Tween(0.25 + 0.005625 * 2 + 0.50 - 0.005625 * 2 * 2 - 0.00140625, 0.45 + 0.01 * 2, 0.00140625, 0.10 - 0.01 * 2 * 2, 1.00, 1.00, 'create', QEasingCurve.InOutQuad, None),
        Tween(0.25 + 0.005625 * 2 + 0.50 - 0.005625 * 2 * 2 - 0.00140625, 0.45 + 0.01 * 2, 0.00140625, 0.00, 0.30, 0.30, 'loaded', QEasingCurve.OutCirc, QColor(255, 255, 255)),
    ]),
    
    # Progress Bar
    RectDef(0.50, 0.45 + 0.01 * 3, 0.00, 0.10 - 0.01 * 3 * 2, QColor(255, 255, 255), True, [
        Tween(0.25 + 0.005625 * 3, 0.45 + 0.01 * 3, 0.05625 - 0.005625 * 3 * 2, 0.10 - 0.01 * 3 * 2, 0.30, 0.70, 'create', QEasingCurve.InOutQuad, None),
        Tween(0.25 + 0.005625 * 3, 0.45 + 0.01 * 3, 0.50 - 0.005625 * 3 * 2, 0.10 - 0.01 * 3 * 2, 1.00, 1.80, 'create', QEasingCurve.InOutCirc, None),
        Tween(0.25 + 0.005625 * 3, 0.45 + 0.01 * 3, 0.50 - 0.005625 * 3 * 2, 0.10 - 0.01 * 3 * 2, 0.00, 0.30, 'loaded', QEasingCurve.OutCirc, None),
        Tween(0.50, 0.50, 0.00, 0.00, 0.30, 0.25, 'loaded', QEasingCurve.OutCirc, None),
    ]),
]

CAMERA_LAYOUT = [
        [[[0,1,1,1],[0,0,1,1],[1/6,0,5/6,1],[1/6,0,5/6,1],[1/6,0,5/6,1],[1/6,0,5/6,1],[1/6,0,4/6,1]],
        [[0,1,1,1],[0,0,1,1],[0,0,1,1/2],[0,0,1,1/2],[0,0,1/2,1/2],[0,0,1/2,1/2],[0,0,1/3,1/2],[0,0,1/3,1/2],[0,0,1/4,1/2]],
        [[0,1,1,1],[0,0,1,1],[0,0,1,1/2]]],
        [[[-1/6,0,1/6,1],[0,0,1/6,1],[0,0,1/6,1/2],[0,0,1/6,1/3],[0,0,1/6,1/4]],
        [[0,1,1,1/2],[0,1/2,1,1/2],[0,1/2,1/2,1/2],[1/2,0,1/2,1/2],[1/2,0,1/2,1/2],[1/3,0,1/3,1/2],[1/3,0,1/3,1/2],[1/4,0,1/4,1/2]],
        [[0,1,1,1/2],[0,1/2,1,1/2],[0,1/2,1/2,1/2]]],
        [[[0,1,1/6,1/2],[0,1/2,1/6,1/2],[0,1/3,1/6,1/3],[0,1/4,1/6,1/4]],
        [[1,1/2,1/2,1/2],[1/2,1/2,1/2,1/2],[0,1/2,1/2,1/2],[0,1/2,1/3,1/2],[2/3,0,1/3,1/2],[2/3,0,1/3,1/2],[2/4,0,1/4,1/2]],
        [[1,1/2,1/2,1/2],[1/2,1/2,1/2,1/2],[1/2,1/2,1/2,1/4],[1/2,1/2,1/2,1/4],[1/2,1/2,1/4,1/4],[1/2,1/2,1/4,1/4],[1/2,1/2,1/6,1/4]]],
        [[[0,1,1/6,1/3],[0,2/3,1/6,1/3],[0,2/4,1/6,1/4]],
        [[1,1/2,1/2,1/2],[1/2,1/2,1/2,1/2],[1/3,1/2,1/3,1/2],[0,1/2,1/3,1/2],[0,1/2,1/4,1/2],[3/4,0,1/4,1/2]],
        [[1/2,1,1/2,1/4],[1/2,3/4,1/2,1/4],[1/2,3/4,1/4,1/4],[3/4,1/2,1/4,1/4],[3/4,1/2,1/4,1/4],[4/6,1/2,1/6,1/4]]],
        [[[0,1,1/6,1/4],[0,3/4,1/6,1/4]],
        [[1,1/2,1/3,1/2],[2/3,1/2,1/3,1/2],[1/3,1/2,1/3,1/2],[1/4,1/2,1/4,1/2],[0,1/2,1/4,1/2]],
        [[1,3/4,1/4,1/4],[3/4,3/4,1/4,1/4],[1/2,3/4,1/4,1/4],[1/2,3/4,1/6,1/4],[5/6,1/2,1/6,1/4]]],
        [[[1,0,1/6,1],[5/6,0,1/6,1],[5/6,0,1/6,1/2],[5/6,0,1/6,1/3]],
        [[1,1/2,1/3,1/2],[2/3,1/2,1/3,1/2],[2/4,1/2,1/4,1/2],[1/4,1/2,1/4,1/2]],
        [[1,3/4,1/4,1/4],[3/4,3/4,1/4,1/4],[4/6,3/4,1/6,1/4],[1/2,3/4,1/6,1/4]]],
        [[[5/6,1,1/6,1/2],[5/6,1/2,1/6,1/2],[5/6,1/3,1/6,1/3]],
        [[1,1/2,1/4,1/2],[3/4,1/2,1/4,1/2],[2/4,1/2,1/4,1/2]],
        [[1,3/4,1/6,1/4],[5/6,3/4,1/6,1/4],[4/6,3/4,1/6,1/4]]],
        [[[5/6,1,1/6,1/3],[5/6,2/3,1/6,1/3]],
        [[1,1/2,1/4,1/2],[3/4,1/2,1/4,1/2]],
        [[1,3/4,1/6,1/4],[5/6,3/4,1/6,1/4]]],
    ]