# 范例文件，属于 build_jam_jar.py，整理：Carinoasd
"""Vector art for v2: jam jar, jam, label, gingham cloth, ribbon bow, strawberry.

All shapes are ASS drawing strings in jar-local pixel units.  Every jar part is
prefixed with the same two moves (BOX) so that all parts share one bounding box
and line up under any \\an / scale / rotation in libass.
"""
import math

BOX_X0, BOX_Y0, BOX_X1, BOX_Y1 = -8, -14, 80, 96
BOX = f"m {BOX_X0} {BOX_Y0} m {BOX_X1} {BOX_Y1} "


def f(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"


def path(cmds):
    out = []
    for c in cmds:
        op, *pts = c
        out.append(op + " " + " ".join(f"{f(x)} {f(y)}" for x, y in pts))
    return " ".join(out) + " "


def rrect(x0, y0, x1, y1, r):
    k = 0.5523 * r
    return path([
        ("m", (x0 + r, y0)), ("l", (x1 - r, y0)), ("b", (x1 - r + k, y0), (x1, y0 + r - k), (x1, y0 + r)),
        ("l", (x1, y1 - r)), ("b", (x1, y1 - r + k), (x1 - r + k, y1), (x1 - r, y1)),
        ("l", (x0 + r, y1)), ("b", (x0 + r - k, y1), (x0, y1 - r + k), (x0, y1 - r)),
        ("l", (x0, y0 + r)), ("b", (x0, y0 + r - k), (x0 + r - k, y0), (x0 + r, y0)),
    ])


def ellipse(cx, cy, rx, ry):
    kx, ky = 0.5523 * rx, 0.5523 * ry
    return path([
        ("m", (cx, cy - ry)), ("b", (cx + kx, cy - ry), (cx + rx, cy - ky), (cx + rx, cy)),
        ("b", (cx + rx, cy + ky), (cx + kx, cy + ry), (cx, cy + ry)),
        ("b", (cx - kx, cy + ry), (cx - rx, cy + ky), (cx - rx, cy)),
        ("b", (cx - rx, cy - ky), (cx - kx, cy - ry), (cx, cy - ry)),
    ])


def jar_body(inset=0.0):
    """Glass jar silhouette (neck + shoulders + body), optionally inset."""
    i = inset
    nx0, nx1 = 14 + i, 58 - i          # neck
    bx0, bx1 = 4 + i, 68 - i           # body
    top, sh, bot = 7 + i, 23, 92 - i
    r = 11 - i * 0.6
    return path([
        ("m", (nx0, top)), ("l", (nx1, top)), ("l", (nx1, 12)),
        ("b", (nx1 + 6 - i * 0.3, 12.5 + i * 0.4), (bx1, 16 + i * 0.3), (bx1, sh + i * 0.2)),
        ("l", (bx1, bot - r)), ("b", (bx1, bot - r * 0.45), (bx1 - r * 0.45, bot), (bx1 - r, bot)),
        ("l", (bx0 + r, bot)), ("b", (bx0 + r * 0.45, bot), (bx0, bot - r * 0.45), (bx0, bot - r)),
        ("l", (bx0, sh + i * 0.2)), ("b", (bx0, 16 + i * 0.3), (nx0 - 6 + i * 0.3, 12.5 + i * 0.4), (nx0, 12)),
    ])


RIM = rrect(10, 0, 62, 8, 3.2)
BODY = jar_body()
INNER = jar_body(3.2)
# glass highlights: a long streak on the left, a short one next to it, a glint on the right shoulder
HILITE = (path([("m", (9.5, 30)), ("b", (9.5, 27.5), (12.5, 27.5), (12.5, 30)), ("l", (12.5, 74)),
                ("b", (12.5, 76.5), (9.5, 76.5), (9.5, 74))])
          + path([("m", (15.5, 33)), ("b", (15.5, 31.5), (17.3, 31.5), (17.3, 33)), ("l", (17.3, 46)),
                  ("b", (17.3, 47.5), (15.5, 47.5), (15.5, 46))])
          + path([("m", (57, 17)), ("b", (61, 18), (63.5, 21), (64, 25)), ("b", (62.5, 23), (60.5, 20.5), (57, 17))]))
# strawberry chunks inside the jam (dark) and glossy flecks (light)
CHUNKS = (ellipse(20, 80, 7, 5) + ellipse(44, 83, 8, 4.5) + ellipse(56, 70, 5.5, 6) + ellipse(31, 64, 6, 5)
          + ellipse(15, 50, 5, 5.5) + ellipse(48, 52, 7, 5) + ellipse(28, 38, 5.5, 4.5) + ellipse(54, 33, 5, 4.2))
FLECKS = (ellipse(24, 78, 1.6, 1.1) + ellipse(47, 81.5, 1.8, 1) + ellipse(33, 62.5, 1.5, 1) + ellipse(50, 50.5, 1.7, 1)
          + ellipse(18, 48.5, 1.3, 1) + ellipse(30, 36.5, 1.3, 0.9) + ellipse(57, 68.5, 1.2, 1.2))
LABEL = rrect(17, 54, 55, 76, 5)
LABEL_IN = rrect(19, 56, 53, 74, 3.8)


def gingham_cloth():
    """Gingham cover draped over the lid: returns (white, light, dark) cell drawings."""
    cols, rows = 7, 3
    # trapezoid: top edge (curved up a little), bottom edge wider
    tl, tr = (4.0, -10.0), (68.0, -10.0)
    bl, br = (-5.0, 12.0), (77.0, 12.0)

    def P(u, v):
        top = (tl[0] + (tr[0] - tl[0]) * u, tl[1] + (tr[1] - tl[1]) * u - 3.5 * math.sin(math.pi * u))
        bot = (bl[0] + (br[0] - bl[0]) * u, bl[1] + (br[1] - bl[1]) * u + 1.5 * math.sin(math.pi * u))
        return (top[0] + (bot[0] - top[0]) * v, top[1] + (bot[1] - top[1]) * v)

    cells = {"white": [], "light": [], "dark": []}
    for r in range(rows):
        for c in range(cols):
            u0, u1, v0, v1 = c / cols, (c + 1) / cols, r / rows, (r + 1) / rows
            quad = [P(u0, v0), P(u1, v0), P(u1, v1), P(u0, v1)]
            kind = "dark" if (r % 2 == 0 and c % 2 == 0) else ("white" if (r % 2 == 1 and c % 2 == 1) else "light")
            cells[kind].append(quad)
    # pinked (zigzag) bottom edge: one triangle per column, coloured like the last row
    r = rows
    for c in range(cols):
        a, b = P(c / cols, 1), P((c + 1) / cols, 1)
        tip = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 5.5)
        kind = "light" if c % 2 == 0 else "white"
        cells[kind].append([a, b, tip])
    out = {}
    for k, polys in cells.items():
        s = ""
        for poly in polys:
            s += "m " + f"{f(poly[0][0])} {f(poly[0][1])} " + " ".join(f"l {f(x)} {f(y)}" for x, y in poly[1:]) + " "
        out[k] = s
    return out


def ribbon():
    """Red ribbon around the neck with a bow at the front."""
    band = path([("m", (12.5, 11)), ("l", (59.5, 11)), ("l", (59.5, 15.5)), ("l", (12.5, 15.5))])
    cx, cy = 36, 13
    loop_l = path([("m", (cx - 2, cy)), ("b", (cx - 10, cy - 11), (cx - 20, cy - 8), (cx - 18, cy - 1)),
                   ("b", (cx - 17, cy + 5), (cx - 9, cy + 6), (cx - 2, cy + 1))])
    loop_r = path([("m", (cx + 2, cy)), ("b", (cx + 10, cy - 11), (cx + 20, cy - 8), (cx + 18, cy - 1)),
                   ("b", (cx + 17, cy + 5), (cx + 9, cy + 6), (cx + 2, cy + 1))])
    tail_l = path([("m", (cx - 2, cy + 2)), ("l", (cx - 9, cy + 16)), ("l", (cx - 6, cy + 14.5)), ("l", (cx - 4.5, cy + 17.5)),
                   ("l", (cx + 0.5, cy + 3))])
    tail_r = path([("m", (cx + 2, cy + 2)), ("l", (cx + 9, cy + 15)), ("l", (cx + 5.8, cy + 14)), ("l", (cx + 4, cy + 17)),
                   ("l", (cx - 0.5, cy + 3))])
    knot = ellipse(cx, cy + 0.5, 3.6, 3.4)
    shine = path([("m", (cx - 15, cy - 3)), ("b", (cx - 13, cy - 7), (cx - 8, cy - 7), (cx - 5, cy - 3)),
                  ("b", (cx - 9, cy - 5), (cx - 12, cy - 5), (cx - 15, cy - 3))]) + \
        path([("m", (cx + 15, cy - 3)), ("b", (cx + 13, cy - 7), (cx + 8, cy - 7), (cx + 5, cy - 3)),
              ("b", (cx + 9, cy - 5), (cx + 12, cy - 5), (cx + 15, cy - 3))])
    return {"band": band, "bow": loop_l + loop_r + tail_l + tail_r, "knot": knot, "shine": shine}


# strawberry (same as v1) in its own 52x60 box
def _seed(cx, cy):
    return f"m {cx} {cy-2} b {cx+2} {cy-1} {cx+2} {cy+2} {cx} {cy+2} b {cx-2} {cy+2} {cx-2} {cy-1} {cx} {cy-2} "


BERRY_BOX = "m 0 0 m 52 60 "
BERRY = {
    "body": "m 26 14 b 36 9 50 12 49 26 b 48 40 36 52 26 58 b 16 52 4 40 3 26 b 2 12 16 9 26 14 ",
    "seed": "".join(_seed(x, y) for x, y in [(13, 29), (26, 29), (39, 29), (19, 38), (33, 38), (9, 22), (43, 22),
                                              (20, 46), (32, 46), (26, 53)])
            + "m 11 24 b 14 23 15 27 13 33 b 12 36 9 35 9 31 b 9 28 9 25 11 24 ",
    "calyx": "m 26 8 l 34 9 l 47 12 l 35 15 l 39 22 l 30 17 l 26 24 l 22 17 l 13 22 l 17 15 l 5 12 l 18 9 "
             "m 24 11 b 24 7 25 4 27 1 l 30 2 b 28 4 28 7 28 11 ",
}

STAR = "m 10 0 b 11 7 13 9 20 10 b 13 11 11 13 10 20 b 9 13 7 11 0 10 b 7 9 9 7 10 0 "
DOT = "m 3 0 b 5 0 6 1 6 3 b 6 5 5 6 3 6 b 1 6 0 5 0 3 b 0 1 1 0 3 0 "
