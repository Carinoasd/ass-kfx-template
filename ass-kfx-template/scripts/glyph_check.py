"""检查字幕里每个样式的字体缺哪些字。

Author: Carinoasd

用法：python glyph_check.py 字幕.ass [--fontsdir 字体目录]

只检查 Dialogue 行和特效栏为 karaoke 的注释行（模板行、code 行跳过），
去掉 {} 里的标签和 \\N \\n \\h 后逐字查字体的 cmap。缺字会列出来，
没有缺字时输出「全部字都有」。行内 \\fn 换字体的部分不在检查范围内。
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fontfind import open_font  # noqa: E402


def parse(ass):
    styles, text = {}, {}
    sfmt = efmt = None
    sec = None
    for raw in open(ass, encoding="utf-8-sig"):
        s = raw.strip()
        if s.startswith("["):
            sec = s
            continue
        if sec in ("[V4+ Styles]", "[V4 Styles]"):
            if s.startswith("Format:"):
                sfmt = [x.strip() for x in s[7:].split(",")]
            elif s.startswith("Style:"):
                d = dict(zip(sfmt, [x.strip() for x in s[6:].split(",", len(sfmt) - 1)]))
                styles[d["Name"]] = d["Fontname"]
        elif sec == "[Events]":
            if s.startswith("Format:"):
                efmt = [x.strip() for x in s[7:].split(",")]
            elif s.startswith(("Dialogue:", "Comment:")):
                kind, rest = s.split(":", 1)
                d = dict(zip(efmt, rest.lstrip().split(",", len(efmt) - 1)))
                eff = d.get("Effect", "").strip()
                if kind == "Comment" and eff != "karaoke":
                    continue
                if eff.startswith(("template", "code", "fx")):
                    continue
                t = re.sub(r"\{[^}]*\}", "", d["Text"])
                t = t.replace("\\N", "").replace("\\n", "").replace("\\h", "")
                text.setdefault(d["Style"], set()).update(t)
    return styles, text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ass")
    ap.add_argument("--fontsdir")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    styles, text = parse(a.ass)
    missing_any = False
    for st, chars in sorted(text.items()):
        fam = styles.get(st)
        if fam is None:
            print(f"[样式 {st}] 样式表里没有这个样式")
            continue
        cmap = open_font(fam, a.fontsdir).getBestCmap()
        miss = sorted(c for c in chars if not c.isspace() and ord(c) not in cmap)
        if miss:
            missing_any = True
            print(f"[样式 {st}] 字体「{fam}」缺字：{' '.join(miss)}")
        else:
            print(f"[样式 {st}] 字体「{fam}」全部字都有（{len(chars)} 个不同字符）")
    sys.exit(2 if missing_any else 0)


if __name__ == "__main__":
    main()
