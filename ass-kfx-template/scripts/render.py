"""用 libass（ffmpeg 的 subtitles 滤镜）把 .ass 渲染到视频帧上，截图检查效果。

Author: Carinoasd

用法：
  单帧：python render.py 字幕.ass 输出目录 --video 视频.mp4 1164.5 1170.2 ...
  连续：python render.py 字幕.ass 输出目录 --video 视频.mp4 --seq 起 止 间隔 [--cols 4]
  放大某区域：加 --crop 宽:高:x:y（ffmpeg crop 格式）和 --zoom 2
  没有视频时省略 --video，用纯色背景（--bg 颜色，默认灰色），尺寸取 PlayResX/Y。

时间一律用秒（小数），和 ass 里的时间轴相同，例如 19:24.68 写成 1164.68。
--fontsdir 指定样式字体所在目录；字体已装在系统里可以不填。
依赖：ffmpeg（需带 libass）、pillow
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw


def esc(p):
    """ffmpeg 滤镜参数里的路径：斜杠统一，冒号和引号转义。"""
    return p.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def play_res(ass):
    w, h = 1920, 1080
    for line in open(ass, encoding="utf-8-sig"):
        m = re.match(r"\s*PlayRes([XY])\s*:\s*(\d+)", line)
        if m:
            if m.group(1) == "X":
                w = int(m.group(2))
            else:
                h = int(m.group(2))
        if line.strip() == "[Events]":
            break
    return w, h


class Renderer:
    def __init__(self, ass, video=None, fontsdir=None, bg="0x8a8580"):
        if not shutil.which("ffmpeg"):
            sys.exit("找不到 ffmpeg，请先安装并加入 PATH。")
        self.tmp = tempfile.mkdtemp(prefix="kfx_")
        # 复制到临时目录，避开文件名里的逗号、方括号等滤镜特殊字符
        shutil.copy(ass, os.path.join(self.tmp, "sub.ass"))
        self.video = os.path.abspath(video) if video else None
        self.fontsdir = os.path.abspath(fontsdir) if fontsdir else None
        self.bg = bg
        self.size = play_res(ass)

    def _vf(self, extra=""):
        vf = "subtitles=sub.ass"
        if self.fontsdir:
            vf += f":fontsdir='{esc(self.fontsdir)}'"
        return vf + extra

    def _src(self, t, dur):
        if self.video:
            # 输入端跳转 + copyts：帧的时间戳保持原片时间，字幕才能对上
            return ["-ss", f"{t:.3f}", "-copyts", "-t", f"{dur:.3f}", "-i", self.video]
        w, h = self.size
        return ["-f", "lavfi", "-i", f"color=c={self.bg}:s={w}x{h}:r=30:d={t + dur + 1:.3f}"]

    def _run(self, args):
        r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"] + args,
                           cwd=self.tmp, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            sys.exit(r.stderr[-2000:])

    def frame(self, t, out_png, crop=None, zoom=1.0):
        extra = f",crop={crop}" if crop else ""
        if zoom != 1.0:
            extra += f",scale=iw*{zoom}:ih*{zoom}:flags=lanczos"
        if self.video:
            self._run(self._src(t, 0.5) + ["-vf", self._vf(extra), "-frames:v", "1", os.path.abspath(out_png)])
        else:
            self._run(self._src(t, 0.1) + ["-ss", f"{t:.3f}", "-vf", self._vf(extra), "-frames:v", "1",
                                           os.path.abspath(out_png)])
        return out_png

    def frames(self, times, out_dir, crop=None, zoom=1.0):
        os.makedirs(out_dir, exist_ok=True)
        return [self.frame(t, os.path.join(out_dir, f"f_{t:.3f}.png"), crop, zoom) for t in times]


def contact_sheet(pngs, labels, out_png, cols=4, width=640):
    ims = [Image.open(p).convert("RGB") for p in pngs]
    tw = width
    th = int(ims[0].height * tw / ims[0].width)
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols - 1) * 3, rows * th + (rows - 1) * 3), (0, 0, 0))
    d = ImageDraw.Draw(sheet)
    for i, (im, lab) in enumerate(zip(ims, labels)):
        x, y = (i % cols) * (tw + 3), (i // cols) * (th + 3)
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (x, y))
        d.rectangle([x, y, x + 8 + 7 * len(lab), y + 16], fill=(0, 0, 0))
        d.text((x + 4, y + 2), lab, fill=(255, 255, 0))
    sheet.save(out_png)
    return out_png


def main():
    ap = argparse.ArgumentParser(description="用 libass 渲染字幕截图")
    ap.add_argument("ass")
    ap.add_argument("out_dir")
    ap.add_argument("times", nargs="*", type=float, help="要截的时间点（秒）")
    ap.add_argument("--video")
    ap.add_argument("--fontsdir")
    ap.add_argument("--bg", default="0x8a8580", help="无视频时的背景色")
    ap.add_argument("--seq", nargs=3, type=float, metavar=("起", "止", "间隔"))
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--crop", help="宽:高:x:y")
    ap.add_argument("--zoom", type=float, default=1.0)
    a = ap.parse_args()
    r = Renderer(a.ass, a.video, a.fontsdir, a.bg)
    os.makedirs(a.out_dir, exist_ok=True)
    if a.seq:
        t0, t1, step = a.seq
        times = [round(t0 + i * step, 3) for i in range(int(round((t1 - t0) / step)) + 1)]
        pngs = r.frames(times, os.path.join(a.out_dir, "seq_frames"), a.crop, a.zoom)
        out = contact_sheet(pngs, [f"{t:.2f}s" for t in times],
                            os.path.join(a.out_dir, f"seq_{t0:.2f}-{t1:.2f}.png"), a.cols)
        print(out)
    for p in r.frames(a.times, a.out_dir, a.crop, a.zoom):
        print(p)


if __name__ == "__main__":
    main()
