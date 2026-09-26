# 范例文件，属于 build_jam_jar.py，整理：Carinoasd
"""Synthesize the two glyphs missing from 方正达利体简繁 Heavy (気, 別) out of its own outlines.

Output: ASS drawing command strings in font units (x right, y up, baseline 0),
converted to cubic beziers.  Import build_glyphs() or run to print them.
"""
import math
import os

from fontTools.pens.basePen import BasePen
from fontTools.pens.pointPen import PointToSegmentPen
from fontTools.ttLib import TTFont

FONT = os.environ.get("JAM_FONT", r"C:\Windows\Fonts\方正达利体简繁 Heavy.TTF")


def contours_of(font, gname):
    """[(x, y, on)] per contour, straight from glyf."""
    g = font["glyf"]
    coords, ends, flags = g[gname].getCoordinates(g)
    out, s = [], 0
    for e in ends:
        out.append([(float(coords[i][0]), float(coords[i][1]), bool(flags[i] & 1)) for i in range(s, e + 1)])
        s = e + 1
    return out


def bbox(contours):
    xs = [p[0] for c in contours for p in c]
    ys = [p[1] for c in contours for p in c]
    return min(xs), min(ys), max(xs), max(ys)


def transform(contours, fx):
    return [[(*fx(x, y), on) for x, y, on in c] for c in contours]


def signed_area(c):
    a = 0.0
    for i in range(len(c)):
        x0, y0 = c[i][0], c[i][1]
        x1, y1 = c[(i + 1) % len(c)][0], c[(i + 1) % len(c)][1]
        a += x0 * y1 - x1 * y0
    return a / 2


def embolden(contours, d):
    """Offset every contour outward by d font units (FreeType's bisector method, no translation)."""
    res = []
    for c in contours:
        n = len(c)
        # TrueType outer contours are clockwise (negative area in y-up coords); outward normal = (-dy, dx)
        sign = 1.0 if signed_area(c) < 0 else -1.0
        out = []
        for i in range(n):
            px, py, on = c[i]
            ax, ay = c[i - 1][0], c[i - 1][1]
            bx, by = c[(i + 1) % n][0], c[(i + 1) % n][1]
            ix, iy = px - ax, py - ay
            ox, oy = bx - px, by - py
            li, lo = math.hypot(ix, iy), math.hypot(ox, oy)
            if li == 0 or lo == 0:
                out.append((px, py, on))
                continue
            ix, iy, ox, oy = ix / li, iy / li, ox / lo, oy / lo
            dot = ix * ox + iy * oy
            if dot <= -0.9375:
                out.append((px, py, on))
                continue
            k = 1 + dot
            sx = sign * -(iy + oy) * d / k
            sy = sign * (ix + ox) * d / k
            out.append((px + sx, py + sy, on))
        res.append(out)
    return res


class CubicCollector(BasePen):
    def __init__(self):
        super().__init__(None)
        self.cmds = []

    def _moveTo(self, p):
        self.cmds.append(("m", [p]))

    def _lineTo(self, p):
        self.cmds.append(("l", [p]))

    def _curveToOne(self, p1, p2, p3):
        self.cmds.append(("b", [p1, p2, p3]))

    def _closePath(self):
        pass

    _endPath = _closePath


def to_commands(contours):
    pen = CubicCollector()
    pp = PointToSegmentPen(pen)
    for c in contours:
        pp.beginPath()
        n = len(c)
        for i, (x, y, on) in enumerate(c):
            if on:
                seg = "qcurve" if not c[i - 1][2] else "line"
            else:
                seg = None
            pp.addPoint((x, y), segmentType=seg)
        pp.endPath()
    parts = []
    for cmd, pts in pen.cmds:
        parts.append(cmd + " " + " ".join(f"{x:.1f} {y:.1f}".replace(".0 ", " ") for x, y in pts))
    s = " ".join(parts)
    # tidy "12.0" -> "12"
    return " ".join(t[:-2] if t.endswith(".0") else t for t in s.split())


def build_glyphs(x_target=(55, -72, 665, 368), x_embolden=8.0):
    font = TTFont(FONT)
    # 別: 别 with the stroke joining 口 to 力 removed
    b = contours_of(font, "uni522B")
    c3 = b[3]  # points 44..108 of the glyph -> local indices 0..64
    local = lambda i: i - 44
    kou = c3[local(83):local(103) + 1]
    lower = c3[local(44):local(82) + 1] + c3[local(104):local(108) + 1]
    betsu = [b[0], b[1], b[2], kou, lower]
    # 気: frame of 氣 (contours 4, 5, 7) + the X of 区 (contour 0) fitted where 米 was
    k = contours_of(font, "uni6C23")
    frame = [k[4], k[5], k[7]]
    x_shape = [contours_of(font, "uni533A")[0]]
    x0, y0, x1, y1 = bbox(x_shape)
    tx0, ty0, tx1, ty1 = x_target
    sx, sy = (tx1 - tx0) / (x1 - x0), (ty1 - ty0) / (y1 - y0)
    x_fit = transform(x_shape, lambda x, y: (tx0 + (x - x0) * sx, ty0 + (y - y0) * sy))
    x_fit = embolden(x_fit, x_embolden)
    ki = frame + x_fit
    plain = contours_of(font, "uni522B")  # unmodified 别, used to validate the pipeline
    return {"別": to_commands(betsu), "気": to_commands(ki), "别": to_commands(plain)}


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    for ch, cmd in build_glyphs().items():
        print(ch, len(cmd), cmd[:160], "...")
