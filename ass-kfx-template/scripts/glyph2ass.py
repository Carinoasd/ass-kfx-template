"""把字体里的字转成 ASS 矢量绘图（\\p1），用来补缺字或把字当图形做动画。

Author: Carinoasd

命令行：
  列出轮廓：python glyph2ass.py 字体 字 --list [--preview 轮廓.png]
  输出像素绘图：python glyph2ass.py 字体 字 --size 58 [--scale-x 100] [--pick 0,2,3]
  输出字体单位（放进模板运行时缩放）：python glyph2ass.py 字体 字 --units
  存进补字表：python glyph2ass.py 字体 字 --json 补字.json [--as 缺的字] [--pick ...]
      （给 starter_build.py --glyph-json 用；--as 把这个字形存到另一个字名下）
  验证：python glyph2ass.py 字体 字 --size 58 --verify
      （同一个字分别用文字和绘图在 libass 下渲染，比较墨迹像素和包围盒）

「字体」可以是字体文件路径，也可以是族名（加 --fontsdir 指定目录）。

像素绘图开头带 "m 0 0 m 字宽 字高" 两个空 move：libass 按包围盒对齐绘图，
有了它，绘图用 \\an 定位时和同字号的文字落在同一个位置，多层绘图也能互相对齐。

作为模块使用（拼字时）：
  from glyph2ass import load, Glyph
  g = load(font, "别")          # Glyph 对象，g.contours 是轮廓列表
  part = g.pick([0, 1])         # 取部分轮廓
  part = part.fit((x0, y0, x1, y1))   # 缩放平移到目标框（字体单位，y 向上）
  part = part.embolden(8)       # 向外扩 8 个字体单位，补回缩小后变细的笔画
  new = g.pick([2, 3]) + part   # 组合
  print(new.to_ass_px(size=58)) # 或 new.to_units()
  save_json("补字.json", "気", new)  # 存进补字表
"""
import argparse
import math
import os
import subprocess
import sys
import tempfile

from fontTools.pens.basePen import BasePen

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fontfind import open_font, vmetrics  # noqa: E402


class _Collector(BasePen):
    """把轮廓统一收集成三次贝塞尔：[(op, [(x, y), ...]), ...]，每个轮廓一张表。"""

    def __init__(self, gs):
        super().__init__(gs)
        self.contours, self.cur = [], None

    def _moveTo(self, p):
        self.cur = [("m", [p])]
        self.contours.append(self.cur)

    def _lineTo(self, p):
        self.cur.append(("l", [p]))

    def _curveToOne(self, p1, p2, p3):
        self.cur.append(("b", [p1, p2, p3]))

    def _closePath(self):
        pass

    _endPath = _closePath


def _pts(c):
    return [p for _, ps in c for p in ps]


def _fmt(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


class Glyph:
    def __init__(self, contours, asc, height, adv):
        self.contours, self.asc, self.height, self.adv = contours, asc, height, adv

    def _new(self, contours):
        return Glyph(contours, self.asc, self.height, self.adv)

    def __add__(self, other):
        return self._new(self.contours + other.contours)

    def pick(self, idx):
        return self._new([self.contours[i] for i in idx])

    def bbox(self):
        ps = [p for c in self.contours for p in _pts(c)]
        xs, ys = [p[0] for p in ps], [p[1] for p in ps]
        return min(xs), min(ys), max(xs), max(ys)

    def transform(self, fx):
        return self._new([[(op, [fx(x, y) for x, y in ps]) for op, ps in c] for c in self.contours])

    def fit(self, box):
        x0, y0, x1, y1 = self.bbox()
        tx0, ty0, tx1, ty1 = box
        sx, sy = (tx1 - tx0) / (x1 - x0), (ty1 - ty0) / (y1 - y0)
        return self.transform(lambda x, y: (tx0 + (x - x0) * sx, ty0 + (y - y0) * sy))

    def embolden(self, d):
        """每个轮廓沿角平分线向外偏移 d 个字体单位（FreeType 的做法），不改变位置。"""
        out = []
        for c in self.contours:
            ps = _pts(c)
            n = len(ps)
            area = sum(ps[i][0] * ps[(i + 1) % n][1] - ps[(i + 1) % n][0] * ps[i][1] for i in range(n)) / 2
            sign = 1.0 if area < 0 else -1.0
            moved = []
            for i in range(n):
                px, py = ps[i]
                ax, ay = ps[i - 1]
                bx, by = ps[(i + 1) % n]
                ix, iy, ox, oy = px - ax, py - ay, bx - px, by - py
                li, lo = math.hypot(ix, iy), math.hypot(ox, oy)
                if li == 0 or lo == 0:
                    moved.append((px, py))
                    continue
                ix, iy, ox, oy = ix / li, iy / li, ox / lo, oy / lo
                dot = ix * ox + iy * oy
                if dot <= -0.9375:
                    moved.append((px, py))
                    continue
                k = 1 + dot
                moved.append((px + sign * -(iy + oy) * d / k, py + sign * (ix + ox) * d / k))
            it = iter(moved)
            out.append([(op, [next(it) for _ in ps_]) for op, ps_ in c])
        return self._new(out)

    def _cmds(self, fx):
        parts = []
        for c in self.contours:
            for op, ps in c:
                parts.append(op + " " + " ".join(f"{_fmt(a)} {_fmt(b)}" for a, b in (fx(*p) for p in ps)))
        return " ".join(parts)

    def to_units(self):
        """字体单位（x 向右，y 向上，基线为 0）。模板里按 GM 的 asc/h/adv 运行时换算。"""
        return self._cmds(lambda x, y: (x, y))

    def to_ass_px(self, size, scale_x=100, scale_y=100):
        """像素绘图，和同字号文字的位置、大小一致，开头带包围盒锁定。"""
        s = size / self.height
        sx, sy = s * scale_x / 100, s * scale_y / 100
        body = self._cmds(lambda x, y: (x * sx, (self.asc - y) * sy))
        return f"m 0 0 m {_fmt(self.adv * sx)} {_fmt(self.height * sy)} " + body


def save_json(path, ch, g):
    """把字形（字体单位）合并进补字表 JSON：{字: {asc, h, adv, d}}。"""
    import json
    data = {}
    if os.path.exists(path):
        data = json.load(open(path, encoding="utf-8"))
    data[ch] = {"asc": g.asc, "h": g.height, "adv": g.adv, "d": g.to_units()}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return path


def load(font, ch):
    cmap = font.getBestCmap()
    if ord(ch) not in cmap:
        raise KeyError(f"字体里没有「{ch}」")
    name = cmap[ord(ch)]
    gs = font.getGlyphSet()
    pen = _Collector(gs)
    gs[name].draw(pen)
    asc, h = vmetrics(font)
    return Glyph(pen.contours, asc, h, font["hmtx"].metrics[name][0])


def preview(g, out_png, scale=0.5):
    from PIL import Image, ImageDraw
    x0, y0, x1, y1 = g.bbox()
    pad = 40
    W, H = int((x1 - x0) * scale) + 2 * pad, int((y1 - y0) * scale) + 2 * pad
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    colors = [(220, 40, 60), (30, 120, 220), (20, 150, 60), (200, 120, 0), (140, 50, 180), (0, 150, 150)]
    tr = lambda x, y: (pad + (x - x0) * scale, pad + (y1 - y) * scale)
    for i, c in enumerate(g.contours):
        col = colors[i % len(colors)]
        pts, last = [], None
        for op, ps in c:
            if op == "m":
                last = ps[0]
                pts.append(tr(*last))
            elif op == "l":
                last = ps[0]
                pts.append(tr(*last))
            else:
                p0 = last
                for k in range(1, 9):
                    t = k / 8
                    mt = 1 - t
                    x = mt ** 3 * p0[0] + 3 * mt * mt * t * ps[0][0] + 3 * mt * t * t * ps[1][0] + t ** 3 * ps[2][0]
                    y = mt ** 3 * p0[1] + 3 * mt * mt * t * ps[0][1] + 3 * mt * t * t * ps[1][1] + t ** 3 * ps[2][1]
                    pts.append(tr(x, y))
                last = ps[2]
        if len(pts) > 1:
            d.line(pts + [pts[0]], fill=col, width=2)
            d.text(pts[0], str(i), fill=col)
    im.save(out_png)
    return out_png


def verify(font_arg, fontsdir, family, ch, drawing, size):
    """文字和绘图各渲染一次，报告墨迹像素数和包围盒。两者应基本一致。"""
    import numpy as np
    from PIL import Image
    tmp = tempfile.mkdtemp(prefix="kfxg_")
    head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 600\nPlayResY: 300\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
            "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
            "MarginR, MarginV, Encoding\n"
            f"Style: V,{family},{size},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    res = []
    for name, text in (("text", ch), ("draw", "{\\p1}" + drawing)):
        p = os.path.join(tmp, name + ".ass")
        open(p, "w", encoding="utf-8").write(head + f"Dialogue: 0,0:00:00.00,0:00:01.00,V,,0,0,0,,{{\\an5\\pos(300.5,150.5)}}{text}\n")
        vf = f"subtitles={name}.ass"
        if fontsdir:
            vf += ":fontsdir='" + os.path.abspath(fontsdir).replace("\\", "/").replace(":", "\\:") + "'"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                        "color=c=black:s=600x300:d=1", "-vf", vf, "-frames:v", "1", name + ".png"], cwd=tmp, check=True)
        a = np.asarray(Image.open(os.path.join(tmp, name + ".png")).convert("L"))
        ys, xs = np.nonzero(a > 20)
        res.append((int((a > 128).sum()), (xs.min(), ys.min(), xs.max(), ys.max()) if len(xs) else None))
    (ti, tb), (di, db) = res
    tb = tuple(int(v) for v in tb) if tb else None
    db = tuple(int(v) for v in db) if db else None
    pct = (di - ti) / ti * 100 if ti else 100
    print(f"文字：墨迹 {ti} 像素，包围盒 {tb}")
    print(f"绘图：墨迹 {di} 像素（{pct:+.1f}%），包围盒 {db}")
    # 包围盒是主要依据；墨迹因抗锯齿差几个百分点属正常，且会随字号正负变化
    ok = bool(tb and db) and max(abs(a - b) for a, b in zip(tb, db)) <= 1 and abs(pct) <= 6
    print("结果：一致" if ok else "结果：有偏差。包围盒不同说明位置或字号换算错；墨迹差很多说明字重或轮廓不对")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("font", help="字体文件路径或族名")
    ap.add_argument("char")
    ap.add_argument("--fontsdir")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--preview")
    ap.add_argument("--pick", help="只取这些轮廓，例如 0,2,3")
    ap.add_argument("--size", type=float)
    ap.add_argument("--scale-x", type=float, default=100)
    ap.add_argument("--scale-y", type=float, default=100)
    ap.add_argument("--units", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--json", help="合并进这个补字表文件")
    ap.add_argument("--as", dest="as_char", help="在补字表里用这个字名存（默认就是 char）")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    font = open_font(a.font, a.fontsdir)
    g = load(font, a.char)
    if a.pick:
        g = g.pick([int(i) for i in a.pick.split(",")])
    if a.list:
        print(f"asc={g.asc} h={g.height} adv={g.adv}")
        for i, c in enumerate(g.contours):
            ps = _pts(c)
            xs, ys = [p[0] for p in ps], [p[1] for p in ps]
            print(f"轮廓 {i}: {len(c)} 段, x {min(xs):.0f}~{max(xs):.0f}, y {min(ys):.0f}~{max(ys):.0f}")
    if a.preview:
        print(preview(g, a.preview))
    if a.units:
        print(f"GM = {{asc = {g.asc}, h = {g.height}, adv = {g.adv}}}")
        print(g.to_units())
    if a.json:
        print("已写入", save_json(a.json, a.as_char or a.char, g))
    if a.size:
        d = g.to_ass_px(a.size, a.scale_x, a.scale_y)
        if a.verify:
            family = a.font if not os.path.isfile(a.font) else font["name"].getBestFamilyName()
            verify(a.font, a.fontsdir, family, a.char, d, a.size)
        else:
            print(d)


if __name__ == "__main__":
    main()
