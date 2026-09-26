"""逐句检查表：每句歌词在几个时间点各截一帧，排成一张总览图。

Author: Carinoasd

用法：
  python review.py 特效.ass 输出目录 [--video 视频.mp4] [--style 日文样式名]
                   [--offsets s+0.3 s+0.9 m e-0.4 e-0.15] [--crop 宽:高:x:y] [--per-page 7]

时间点写法：s+0.3 表示句首后 0.3 秒，e-0.2 表示句尾前 0.2 秒，m 表示句中。
按「特效栏为 karaoke 的注释行」取歌词时间；--style 只看某个样式（例如只看日文行），
不填时每个样式各出一套。
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import Renderer  # noqa: E402


def t2s(t):
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def lyric_lines(ass):
    out = []
    for line in open(ass, encoding="utf-8-sig"):
        if line.startswith("Comment:"):
            p = line.split(",", 9)
            if len(p) == 10 and p[8].strip() == "karaoke":
                out.append((p[3], t2s(p[1]), t2s(p[2])))
    return out


def at(off, s, e):
    if off == "m":
        return (s + e) / 2
    if off.startswith("s"):
        return s + float(off[1:])
    return e + float(off[1:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ass")
    ap.add_argument("out_dir")
    ap.add_argument("--video")
    ap.add_argument("--fontsdir")
    ap.add_argument("--style")
    ap.add_argument("--bg", default="0x8a8580", help="无视频时的背景色")
    ap.add_argument("--offsets", nargs="+", default=["s+0.3", "s+0.9", "m", "e-0.4", "e-0.15"])
    ap.add_argument("--crop")
    ap.add_argument("--per-page", type=int, default=7)
    ap.add_argument("--width", type=int, default=560, help="每格宽度（像素）")
    a = ap.parse_args()

    lines = lyric_lines(a.ass)
    if not lines:
        sys.exit("没有找到特效栏为 karaoke 的注释行。请传入已套用模板的文件（保留了原歌词注释行）。")
    styles = [a.style] if a.style else sorted({st for st, _, _ in lines})
    r = Renderer(a.ass, a.video, a.fontsdir, a.bg)
    os.makedirs(os.path.join(a.out_dir, "frames"), exist_ok=True)
    cache = {}
    for st in styles:
        rows = [(s, e) for sty, s, e in lines if sty == st]
        for page in range(0, len(rows), a.per_page):
            chunk = rows[page:page + a.per_page]
            tiles = []
            for n, (s, e) in enumerate(chunk):
                row = []
                for off in a.offsets:
                    t = round(at(off, s, e), 3)
                    if t not in cache:
                        cache[t] = r.frame(t, os.path.join(a.out_dir, "frames", f"r_{t:.3f}.png"), a.crop)
                    row.append((cache[t], f"L{page + n + 1} {off} {t:.2f}"))
                tiles.append(row)
            first = Image.open(tiles[0][0][0])
            tw = a.width
            th = int(first.height * tw / first.width)
            cols = len(a.offsets)
            sheet = Image.new("RGB", (cols * tw + (cols - 1) * 3, len(tiles) * (th + 3)), (0, 0, 0))
            d = ImageDraw.Draw(sheet)
            for ri, row in enumerate(tiles):
                for ci, (png, lab) in enumerate(row):
                    x, y = ci * (tw + 3), ri * (th + 3)
                    sheet.paste(Image.open(png).convert("RGB").resize((tw, th), Image.LANCZOS), (x, y))
                    d.rectangle([x, y + th - 15, x + 8 + 6 * len(lab), y + th], fill=(0, 0, 0))
                    d.text((x + 3, y + th - 14), lab, fill=(255, 255, 0))
            safe = "".join(c if c.isalnum() else "_" for c in st)
            out = os.path.join(a.out_dir, f"review_{safe}_{page // a.per_page + 1}.png")
            sheet.save(out)
            print(out)


if __name__ == "__main__":
    main()
