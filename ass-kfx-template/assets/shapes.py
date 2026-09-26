"""ASS 矢量图形素材和画图函数。

Author: Carinoasd

所有图形都是 ASS 绘图字符串（配合 {\\p1} 使用），单位是像素，y 轴向下。
每个图形都有自己的「盒子」BOX：两个空 move 固定包围盒，多层图形叠在一起
（例如草莓的果身、籽、叶子分三层上不同颜色）时，只要每层都以同一个 BOX 开头，
在 libass 下用同一个 \\an \\pos \\fscx \\frz 就能严丝合缝地对齐。
VSFilter 不认这种写法，只保证 libass。

看全部图形：python shapes.py 图鉴.ass  然后用 scripts/render.py 渲染
"""
import math


def f(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"


def path(cmds):
    """[("m", (x, y)), ("l", (x, y)), ("b", c1, c2, p), ...] -> 绘图字符串"""
    out = []
    for c in cmds:
        op, *pts = c
        out.append(op + " " + " ".join(f"{f(x)} {f(y)}" for x, y in pts))
    return " ".join(out) + " "


def box(w, h, x0=0, y0=0):
    return f"m {f(x0)} {f(y0)} m {f(w)} {f(h)} "


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


def xform(shape, dx=0.0, dy=0.0, sx=1.0, sy=1.0):
    """平移缩放一个绘图字符串的所有坐标。"""
    out, i = [], 0
    for tok in shape.split():
        try:
            v = float(tok)
        except ValueError:
            out.append(tok)
            continue
        out.append(f(v * sx + dx) if i % 2 == 0 else f(v * sy + dy))
        i += 1
    return " ".join(out) + " "


def star4(cx, cy, r):
    """四角闪光星，内收的曲线让它看起来像一闪。"""
    k = r * 0.1
    return path([("m", (cx, cy - r)), ("b", (cx + k, cy - k * 3), (cx + k * 3, cy - k), (cx + r, cy)),
                 ("b", (cx + k * 3, cy + k), (cx + k, cy + k * 3), (cx, cy + r)),
                 ("b", (cx - k, cy + k * 3), (cx - k * 3, cy + k), (cx - r, cy)),
                 ("b", (cx - k * 3, cy - k), (cx - k, cy - k * 3), (cx, cy - r))])


def heart(cx, cy, w):
    s = w / 2
    return path([("m", (cx, cy - s * 0.35)),
                 ("b", (cx + s * 0.25, cy - s * 1.0), (cx + s * 1.1, cy - s * 0.85), (cx + s * 0.95, cy - s * 0.1)),
                 ("b", (cx + s * 0.85, cy + s * 0.35), (cx + s * 0.3, cy + s * 0.7), (cx, cy + s * 0.95)),
                 ("b", (cx - s * 0.3, cy + s * 0.7), (cx - s * 0.85, cy + s * 0.35), (cx - s * 0.95, cy - s * 0.1)),
                 ("b", (cx - s * 1.1, cy - s * 0.85), (cx - s * 0.25, cy - s * 1.0), (cx, cy - s * 0.35))])


def five_petal(cx, cy, r, inner=0.28):
    """五瓣花（樱花、草莓花都能用），r 为花瓣外沿半径。"""
    cmds = []
    for i in range(5):
        a0 = math.radians(-90 + i * 72)
        a1, a2 = a0 - math.radians(34), a0 + math.radians(34)
        p0 = (cx + r * inner * math.cos(a1), cy + r * inner * math.sin(a1))
        tip_l = (cx + r * 1.15 * math.cos(a1 + 0.12), cy + r * 1.15 * math.sin(a1 + 0.12))
        tip_r = (cx + r * 1.15 * math.cos(a2 - 0.12), cy + r * 1.15 * math.sin(a2 - 0.12))
        p1 = (cx + r * inner * math.cos(a2), cy + r * inner * math.sin(a2))
        if i == 0:
            cmds.append(("m", p0))
        cmds.append(("b", tip_l, tip_r, p1))
    return path(cmds)


# ---------------------------------------------------------------- 现成图形
STAR_BOX = box(20, 20)
STAR = star4(10, 10, 10)                 # 闪光
DOT_BOX = box(6, 6)
DOT = ellipse(3, 3, 3, 3)                # 糖粒、光点、溅起的液滴
HEART_BOX = box(24, 24)
HEART = heart(12, 12, 22)
FLOWER_BOX = box(24, 24)
FLOWER = five_petal(12, 12, 10)          # 花瓣层
FLOWER_CORE = ellipse(12, 12, 2.8, 2.8)  # 花心层，同一个 BOX


def _seed(cx, cy):
    return f"m {cx} {cy-2} b {cx+2} {cy-1} {cx+2} {cy+2} {cx} {cy+2} b {cx-2} {cy+2} {cx-2} {cy-1} {cx} {cy-2} "


# 草莓：三层（果身 / 籽和高光 / 萼片与果柄），共用 52x60 的盒子
BERRY_BOX = box(52, 60)
BERRY = {
    "body": "m 26 14 b 36 9 50 12 49 26 b 48 40 36 52 26 58 b 16 52 4 40 3 26 b 2 12 16 9 26 14 ",
    "seed": "".join(_seed(x, y) for x, y in [(13, 29), (26, 29), (39, 29), (19, 38), (33, 38), (9, 22), (43, 22),
                                          (20, 46), (32, 46), (26, 53)])
            + "m 11 24 b 14 23 15 27 13 33 b 12 36 9 35 9 31 b 9 28 9 25 11 24 ",
    "calyx": "m 26 8 l 34 9 l 47 12 l 35 15 l 39 22 l 30 17 l 26 24 l 22 17 l 13 22 l 17 15 l 5 12 l 18 9 "
             "m 24 11 b 24 7 25 4 27 1 l 30 2 b 28 4 28 7 28 11 ",
}
# 草莓配色（ASS 颜色是 &HBBGGRR&）：果身、果身描边、籽、叶、叶描边
BERRY_COLORS = {"body": "&H553BEE&", "bodyLine": "&H3D20B3&", "seed": "&HC2F2FF&",
                "calyx": "&H5FB858&", "calyxLine": "&H3A7D2E&"}


def gallery(out_ass):
    """把所有图形排成一张图鉴，方便用 render.py 看样子。"""
    items = [("STAR", STAR_BOX + STAR, "&H9CE4FF&", 4), ("DOT", DOT_BOX + DOT, "&HFFFFFF&", 8),
             ("HEART", HEART_BOX + HEART, "&H7A5BFF&", 4), ("FLOWER", FLOWER_BOX + FLOWER, "&HFFFFFF&", 4)]
    ev = []
    for i, (name, shp, col, sc) in enumerate(items):
        x = 200 + i * 300
        ev.append(f"Dialogue: 1,0:00:00.00,0:00:05.00,G,,0,0,0,,{{\\an5\\pos({x},400)\\fscx{sc*100}\\fscy{sc*100}"
                  f"\\bord1\\3c&H505050&\\1c{col}\\p1}}{shp}")
        ev.append(f"Dialogue: 1,0:00:00.00,0:00:05.00,G,,0,0,0,,{{\\an8\\pos({x},560)\\fs40}}{name}")
    ev.append(f"Dialogue: 2,0:00:00.00,0:00:05.00,G,,0,0,0,,{{\\an5\\pos(1100,400)\\fscx400\\fscy400\\bord0"
              f"\\1c&H4AD8FF&\\p1}}{FLOWER_BOX}{FLOWER_CORE}")
    c = BERRY_COLORS
    for layer, part, tags in ((3, "body", f"\\bord1.2\\3c{c['bodyLine']}\\1c{c['body']}"),
                              (4, "seed", f"\\bord0\\1c{c['seed']}"),
                              (5, "calyx", f"\\bord1\\3c{c['calyxLine']}\\1c{c['calyx']}")):
        ev.append(f"Dialogue: {layer},0:00:00.00,0:00:05.00,G,,0,0,0,,{{\\an5\\pos(1600,400)\\fscx400\\fscy400"
                  f"\\frz15{tags}\\p1}}{BERRY_BOX}{BERRY[part]}")
    ev.append("Dialogue: 1,0:00:00.00,0:00:05.00,G,,0,0,0,,{\\an8\\pos(1600,560)\\fs40}BERRY (3 layers)")
    head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 800\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
            "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
            "MarginL, MarginR, MarginV, Encoding\n"
            "Style: G,Arial,40,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    open(out_ass, "w", encoding="utf-8-sig").write(head + "\n".join(ev) + "\n")
    print(out_ass)


if __name__ == "__main__":
    import sys
    gallery(sys.argv[1] if len(sys.argv) > 1 else "shapes_gallery.ass")
