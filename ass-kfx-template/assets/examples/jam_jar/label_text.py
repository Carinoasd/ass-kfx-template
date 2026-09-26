# 范例文件，属于 build_jam_jar.py，整理：Carinoasd
"""Outline of a short text in 方正达利体, as an ASS drawing centred on (cx, cy), em size in px."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fontTools.ttLib import TTFont  # noqa: E402
from glyph_build import CubicCollector, FONT, contours_of  # noqa: E402
from fontTools.pens.pointPen import PointToSegmentPen  # noqa: E402


def text_shape(text, cx, cy, em, tracking=0.0):
    font = TTFont(FONT)
    cmap = font.getBestCmap()
    s = em / 1000.0
    adv = [font["hmtx"][cmap[ord(c)]][0] * s + tracking for c in text]
    total = sum(adv) - tracking
    x = cx - total / 2
    parts = []
    for c, a in zip(text, adv):
        pen = CubicCollector()
        pp = PointToSegmentPen(pen)
        for cont in contours_of(font, cmap[ord(c)]):
            pp.beginPath()
            for i, (px, py, on) in enumerate(cont):
                seg = ("qcurve" if not cont[i - 1][2] else "line") if on else None
                pp.addPoint((px, py), segmentType=seg)
            pp.endPath()
        for cmd, pts in pen.cmds:
            parts.append(cmd + " " + " ".join(f"{x + px * s:.2f} {cy - (py - 355) * s:.2f}" for px, py in pts))
        x += a
    return " ".join(parts) + " "


if __name__ == "__main__":
    print(text_shape("いちご", 44, 79.5, 11.5)[:200])
