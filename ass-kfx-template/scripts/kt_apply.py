"""在 Aegisub 外面运行 Aegisub 自带的 kara-templater.lua，把卡拉OK模板套用到 .ass 上。

Author: Carinoasd

用法：
  python kt_apply.py 模板.ass 输出.ass [--aegisub Aegisub目录] [--fontsdir 字体目录]

--aegisub 可以是 Aegisub 的安装目录或其中的 automation 目录；不填时依次读取环境变量
AEGISUB_DIR、常见安装位置。结果和在 Aegisub 里执行「自动化 > 应用卡拉OK模板」一致。

字宽测量：Windows 上用 GDI，和 Aegisub 完全相同；其他系统用 FreeType 按字体文件换算，
可能有零点几像素误差，只用于预览，最终成品建议在 Windows 上再跑一次。
依赖：pip install lupa fonttools pillow

模板里可以 _G.require("Yutils")：先找 Aegisub 的 include 目录，找不到就用 skill 自带的
scripts/Yutils.lua。非 Windows 时 Yutils 的 create_font 改由 Python 按字体文件转轮廓。
"""
import argparse
import os
import sys

try:
    from lupa.luajit21 import LuaRuntime
except ImportError:
    try:
        from lupa import LuaRuntime
    except ImportError:
        sys.exit("缺少 lupa：pip install lupa")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
IS_WIN = sys.platform == "win32"


def find_automation(given):
    cands = []
    if given:
        cands.append(given)
    if os.environ.get("AEGISUB_DIR"):
        cands.append(os.environ["AEGISUB_DIR"])
    cands += [r"C:\Program Files\Aegisub", r"C:\Program Files (x86)\Aegisub",
              "/mnt/c/Program Files/Aegisub", "/mnt/c/Program Files (x86)/Aegisub", "/usr/share/aegisub", "/usr/local/share/aegisub",
              "/Applications/Aegisub.app/Contents/SharedSupport"]
    for c in cands:
        for sub in ("", "automation"):
            d = os.path.join(c, sub) if sub else c
            if os.path.isfile(os.path.join(d, "autoload", "kara-templater.lua")):
                return d
    sys.exit("找不到 Aegisub 的 automation 目录（里面应有 autoload/kara-templater.lua）。"
             "用 --aegisub 指定 Aegisub 目录，或设置环境变量 AEGISUB_DIR。")


# ---------------------------------------------------------------- 字宽测量
_extent_cache = {}

if IS_WIN:
    import ctypes
    from ctypes import wintypes
    gdi32 = ctypes.WinDLL("gdi32")

    class LOGFONTW(ctypes.Structure):
        _fields_ = [
            ("lfHeight", wintypes.LONG), ("lfWidth", wintypes.LONG),
            ("lfEscapement", wintypes.LONG), ("lfOrientation", wintypes.LONG),
            ("lfWeight", wintypes.LONG), ("lfItalic", wintypes.BYTE),
            ("lfUnderline", wintypes.BYTE), ("lfStrikeOut", wintypes.BYTE),
            ("lfCharSet", wintypes.BYTE), ("lfOutPrecision", wintypes.BYTE),
            ("lfClipPrecision", wintypes.BYTE), ("lfQuality", wintypes.BYTE),
            ("lfPitchAndFamily", wintypes.BYTE), ("lfFaceName", ctypes.c_wchar * 32),
        ]

    class TEXTMETRICW(ctypes.Structure):
        _fields_ = [
            ("tmHeight", wintypes.LONG), ("tmAscent", wintypes.LONG),
            ("tmDescent", wintypes.LONG), ("tmInternalLeading", wintypes.LONG),
            ("tmExternalLeading", wintypes.LONG), ("tmAveCharWidth", wintypes.LONG),
            ("tmMaxCharWidth", wintypes.LONG), ("tmWeight", wintypes.LONG),
            ("tmOverhang", wintypes.LONG), ("tmDigitizedAspectX", wintypes.LONG),
            ("tmDigitizedAspectY", wintypes.LONG), ("tmFirstChar", ctypes.c_wchar),
            ("tmLastChar", ctypes.c_wchar), ("tmDefaultChar", ctypes.c_wchar),
            ("tmBreakChar", ctypes.c_wchar), ("tmItalic", wintypes.BYTE),
            ("tmUnderlined", wintypes.BYTE), ("tmStruckOut", wintypes.BYTE),
            ("tmPitchAndFamily", wintypes.BYTE), ("tmCharSet", wintypes.BYTE),
        ]

    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateFontIndirectW.restype = wintypes.HFONT
    gdi32.CreateFontIndirectW.argtypes = [ctypes.POINTER(LOGFONTW)]
    gdi32.SelectObject.restype = wintypes.HGDIOBJ
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi32.GetTextExtentPoint32W.argtypes = [wintypes.HDC, wintypes.LPCWSTR, ctypes.c_int, ctypes.POINTER(wintypes.SIZE)]
    gdi32.GetTextMetricsW.argtypes = [wintypes.HDC, ctypes.POINTER(TEXTMETRICW)]
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    gdi32.SetMapMode.argtypes = [wintypes.HDC, ctypes.c_int]

    def _measure(fontname, fontsize, bold, italic, underline, strikeout, spacing, encoding, text):
        """和 Aegisub 在 Windows 上的 text_extents 相同：按 64 倍字号测量再缩回。"""
        fs, sp = fontsize * 64, spacing * 64
        dc = gdi32.CreateCompatibleDC(None)
        gdi32.SetMapMode(dc, 1)
        lf = LOGFONTW()
        lf.lfHeight = int(fs)
        lf.lfWeight = 700 if bold else 400
        lf.lfItalic, lf.lfUnderline, lf.lfStrikeOut = int(bool(italic)), int(bool(underline)), int(bool(strikeout))
        lf.lfCharSet = int(encoding)
        lf.lfOutPrecision, lf.lfClipPrecision, lf.lfQuality = 4, 0, 4
        lf.lfFaceName = fontname[:31]
        font = gdi32.CreateFontIndirectW(ctypes.byref(lf))
        old = gdi32.SelectObject(dc, font)
        sz = wintypes.SIZE()
        width = height = 0.0
        if sp != 0:
            for ch in text:
                gdi32.GetTextExtentPoint32W(dc, ch, 1, ctypes.byref(sz))
                width += sz.cx + sp
                height = sz.cy
        else:
            buf = ctypes.create_unicode_buffer(text)
            n = len(text.encode("utf-16-le")) // 2
            gdi32.GetTextExtentPoint32W(dc, buf, n, ctypes.byref(sz))
            width, height = sz.cx, sz.cy
        tm = TEXTMETRICW()
        gdi32.GetTextMetricsW(dc, ctypes.byref(tm))
        gdi32.SelectObject(dc, old)
        gdi32.DeleteObject(font)
        gdi32.DeleteDC(dc)
        return width / 64, height / 64, tm.tmDescent / 64, tm.tmExternalLeading / 64
else:
    from fontfind import find_font, vmetrics
    from fontTools.ttLib import TTFont
    _fonts = {}
    _warned = set()
    FONTSDIR = None

    def _measure(fontname, fontsize, bold, italic, underline, strikeout, spacing, encoding, text):
        """用字体文件的 advance 宽度换算。字号按 libass/GDI 的方式对应到 win 上伸加下伸。"""
        fk = (fontname, bool(bold))
        if fk not in _fonts:
            hit = find_font(fontname, FONTSDIR, bool(bold))
            if not hit:
                sys.exit(f"找不到样式字体「{fontname}」，用 --fontsdir 指定字体目录。")
            f = TTFont(hit[0], fontNumber=hit[1])
            asc, h = vmetrics(f)
            desc = h - asc
            _fonts[fk] = (f.getBestCmap(), f["hmtx"].metrics, h, desc, f["head"].unitsPerEm)
        cmap, hmtx, h, desc, upem = _fonts[fk]
        s = fontsize / h
        width = 0.0
        for ch in text:
            g = cmap.get(ord(ch))
            if g is None:
                if (fontname, ch) not in _warned:
                    _warned.add((fontname, ch))
                    sys.stderr.write(f"[提示] 「{fontname}」缺字 {ch}，按一个全角宽度估算\n")
                width += upem * s
            else:
                width += hmtx[g][0] * s
            width += spacing
        if "measure" not in _warned:
            _warned.add("measure")
            sys.stderr.write("[提示] 非 Windows 环境按字体文件测量字宽，和 Aegisub 可能差零点几像素，最终成品建议在 Windows 上重跑\n")
        return width, fontsize, desc * s, 0.0


# ---------------------------------------------------------------- Yutils 支援
_shape_fonts = {}

def yutils_dirs(aeg):
    """require("Yutils") 的查找顺序：Aegisub 的 include（含用户目录，DependencyControl 装在这里），
    最后才用 skill 自带的 scripts/Yutils.lua。和 Aegisub 里实际能 require 到的尽量一致。"""
    dirs = [os.path.join(aeg, "include")]
    if os.environ.get("APPDATA"):
        dirs.append(os.path.join(os.environ["APPDATA"], "Aegisub", "automation", "include"))
    dirs.append(HERE)
    return [d.replace("\\", "/") for d in dirs]


def py_text_to_shape(fontname, bold, italic, size, xscale, yscale, hspace, text):
    """非 Windows 时代替 Yutils 的 create_font().text_to_shape()（Yutils 在 Linux 要 pangocairo，
    WSL 常常没有）。换算方式和 Yutils 在 Windows 上一致：字号 = win 上伸 + 下伸，
    y 从字格顶端算起，x 逐字累加 advance + 字间距。只用于预览。"""
    from glyph2ass import load
    fk = (fontname, bool(bold))
    if fk not in _shape_fonts:
        hit = find_font(fontname, FONTSDIR, bool(bold))
        if not hit:
            sys.exit(f"找不到样式字体「{fontname}」，用 --fontsdir 指定字体目录。")
        _shape_fonts[fk] = TTFont(hit[0], fontNumber=hit[1])
    font = _shape_fonts[fk]
    asc, h = vmetrics(font)
    s = size / h
    sx, sy = s * xscale, s * yscale
    x, parts = 0.0, []
    for ch in text:
        try:
            g = load(font, ch)
        except KeyError:
            x += size * xscale + hspace
            continue
        if g.contours:
            parts.append(g._cmds(lambda u, v, ox=x: (ox + u * sx, (asc - v) * sy)))
        x += g.adv * sx + hspace
    return " ".join(parts), x, size * yscale, asc * sy, (h - asc) * sy


def text_extents(fontname, fontsize, bold, italic, underline, strikeout,
                 scale_x, scale_y, spacing, encoding, text):
    key = (fontname, fontsize, bool(bold), bool(italic), scale_x, scale_y, spacing, encoding, text)
    if key not in _extent_cache:
        w, h, d, e = _measure(fontname, fontsize, bold, italic, underline, strikeout, spacing, encoding, text)
        _extent_cache[key] = (scale_x / 100 * w, scale_y / 100 * h, scale_y / 100 * d, scale_y / 100 * e)
    return _extent_cache[key]


# ---------------------------------------------------------------- ASS i/o
def ass_time_to_ms(t):
    h, m, s = t.split(":")
    s, cs = s.split(".")
    return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(cs) * 10


def ms_to_ass_time(ms):
    ms = max(0, int(ms))
    cs = ms // 10
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def parse_color(c):
    # style colour &HAABBGGRR -> Aegisub hands scripts "&HAABBGGRR&"
    return c.strip() + "&"


def load_ass(path):
    with open(path, encoding="utf-8-sig") as f:
        lines = f.read().splitlines()
    sections = []  # (name, [raw lines]) kept for non-event/style sections
    info, styles, events = [], [], []
    style_fmt = event_fmt = None
    cur = None
    for raw in lines:
        s = raw.strip()
        if s.startswith("[") and s.endswith("]"):
            cur = s
            sections.append((cur, []))
            continue
        if cur is None:
            continue
        if cur == "[Script Info]":
            sections[-1][1].append(raw)
            if s and not s.startswith(";") and ":" in s:
                k, v = s.split(":", 1)
                info.append({"class": "info", "section": cur, "key": k.strip(), "value": v.strip(), "raw": raw})
        elif cur == "[V4+ Styles]":
            if s.startswith("Format:"):
                style_fmt = [x.strip() for x in s[7:].split(",")]
            elif s.startswith("Style:"):
                vals = [x.strip() for x in s[6:].split(",", len(style_fmt) - 1)]
                d = dict(zip(style_fmt, vals))
                styles.append({
                    "class": "style", "section": cur, "raw": raw,
                    "name": d["Name"], "fontname": d["Fontname"], "fontsize": float(d["Fontsize"]),
                    "color1": parse_color(d["PrimaryColour"]), "color2": parse_color(d["SecondaryColour"]),
                    "color3": parse_color(d["OutlineColour"]), "color4": parse_color(d["BackColour"]),
                    "bold": d["Bold"] != "0", "italic": d["Italic"] != "0",
                    "underline": d["Underline"] != "0", "strikeout": d["StrikeOut"] != "0",
                    "scale_x": float(d["ScaleX"]), "scale_y": float(d["ScaleY"]),
                    "spacing": float(d["Spacing"]), "angle": float(d["Angle"]),
                    "borderstyle": int(d["BorderStyle"]), "outline": float(d["Outline"]),
                    "shadow": float(d["Shadow"]), "align": int(d["Alignment"]),
                    "margin_l": int(d["MarginL"]), "margin_r": int(d["MarginR"]),
                    "margin_t": int(d["MarginV"]), "margin_b": int(d["MarginV"]),
                    "encoding": int(d["Encoding"]), "relative_to": 2,
                })
        elif cur == "[Events]":
            if s.startswith("Format:"):
                event_fmt = [x.strip() for x in s[7:].split(",")]
            elif s.startswith("Dialogue:") or s.startswith("Comment:"):
                kind, rest = s.split(":", 1)
                vals = [x for x in rest.lstrip().split(",", len(event_fmt) - 1)]
                d = dict(zip(event_fmt, vals))
                events.append({
                    "class": "dialogue", "section": cur, "raw": raw,
                    "comment": kind == "Comment", "layer": int(d["Layer"]),
                    "start_time": ass_time_to_ms(d["Start"]), "end_time": ass_time_to_ms(d["End"]),
                    "style": d["Style"], "actor": d["Name"],
                    "margin_l": int(d["MarginL"]), "margin_r": int(d["MarginR"]),
                    "margin_t": int(d["MarginV"]), "margin_b": int(d["MarginV"]),
                    "effect": d["Effect"], "text": d["Text"], "extra": {},
                })
        else:
            sections[-1][1].append(raw)
    return sections, info, styles, events, style_fmt, event_fmt


def fmt_num(v):
    v = float(v)
    return str(int(v)) if v == int(v) else f"{v:g}"


def style_line(st):
    col = lambda c: c.rstrip("&")
    b = lambda v: "-1" if v else "0"
    return ("Style: " + ",".join([
        st["name"], st["fontname"], fmt_num(st["fontsize"]), col(st["color1"]), col(st["color2"]),
        col(st["color3"]), col(st["color4"]), b(st["bold"]), b(st["italic"]), b(st["underline"]),
        b(st["strikeout"]), fmt_num(st["scale_x"]), fmt_num(st["scale_y"]), fmt_num(st["spacing"]),
        fmt_num(st["angle"]), str(int(st["borderstyle"])), fmt_num(st["outline"]), fmt_num(st["shadow"]),
        str(int(st["align"])), str(int(st["margin_l"])), str(int(st["margin_r"])),
        str(int(st["margin_t"])), str(int(st["encoding"]))]))


def event_line(ev):
    kind = "Comment" if ev["comment"] else "Dialogue"
    return f"{kind}: " + ",".join([
        str(int(ev["layer"])), ms_to_ass_time(ev["start_time"]), ms_to_ass_time(ev["end_time"]),
        ev["style"], ev["actor"] or "", str(int(ev["margin_l"])), str(int(ev["margin_r"])),
        str(int(ev["margin_t"])), ev["effect"] or "", ev["text"]])


# ---------------------------------------------------------------- run
def main(src, dst, aeg):
    sections, info, styles, events, style_fmt, event_fmt = load_ass(src)
    res_x = res_y = None
    for i in info:
        if i["key"] == "PlayResX":
            res_x = int(i["value"])
        if i["key"] == "PlayResY":
            res_y = int(i["value"])

    lua = LuaRuntime(unpack_returned_tuples=True)
    g = lua.globals()
    g.INCLUDE_DIR = os.path.join(aeg, "include").replace("\\", "/")
    g.PY_TEXT_EXTENTS = text_extents
    g.PY_READ_FILE = lambda p: open(p, encoding="utf-8-sig").read()
    g.PY_FILE_EXISTS = os.path.isfile
    ydirs = lua.table()
    for i, d in enumerate(yutils_dirs(aeg), 1):
        ydirs[i] = d
    g.YUTILS_DIRS = ydirs
    g.PY_TEXT_TO_SHAPE = None if IS_WIN else py_text_to_shape
    errors = []

    def log(level, msg):
        errors.append((level, msg))
        sys.stderr.write(f"[aegisub.debug {level}] {msg}\n")

    g.PY_LOG = log
    lua.execute(open(os.path.join(HERE, "mock.lua"), encoding="utf-8").read())

    def to_lua(d):
        t = lua.table()
        for k, v in d.items():
            if k == "extra":
                t[k] = lua.table()
            else:
                t[k] = v
        return t

    entries = lua.table()
    n = 0
    for e in info + styles + events:
        n += 1
        entries[n] = to_lua(e)
    subs, store = g.make_subs(entries, res_x, res_y)

    kt = open(os.path.join(aeg, "autoload", "kara-templater.lua"), encoding="utf-8-sig").read()
    lua.execute(kt)
    g.macro_apply_templates(subs, lua.table())

    # collect results
    out_styles, out_events = [], []
    for i in range(1, len(store) + 1):
        e = store[i]
        cls = e["class"]
        if cls == "style":
            d = {k: e[k] for k in ["name", "fontname", "fontsize", "color1", "color2", "color3", "color4",
                                   "bold", "italic", "underline", "strikeout", "scale_x", "scale_y",
                                   "spacing", "angle", "borderstyle", "outline", "shadow", "align",
                                   "margin_l", "margin_r", "margin_t", "encoding"]}
            out_styles.append(style_line(d))
        elif cls == "dialogue":
            d = {k: e[k] for k in ["comment", "layer", "start_time", "end_time", "style", "actor",
                                   "margin_l", "margin_r", "margin_t", "effect", "text"]}
            out_events.append(event_line(d))

    out = []
    for name, raws in sections:
        out.append(name)
        if name == "[V4+ Styles]":
            out.append("Format: " + ", ".join(style_fmt))
            out.extend(out_styles)
            out.append("")
        elif name == "[Events]":
            out.append("Format: " + ", ".join(event_fmt))
            out.extend(out_events)
        else:
            out.extend(raws)
    with open(dst, "w", encoding="utf-8-sig", newline="\r\n") as f:
        f.write("\n".join(out) + "\n")
    fx = sum(1 for l in out_events if ",fx," in l)
    bad = [e for e in errors if e[0] <= 2]
    print(f"已写出 {dst}：共 {len(out_events)} 行事件，其中特效行 {fx} 行；模板器报错 {len(bad)} 条")
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="在 Aegisub 外套用卡拉OK模板")
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--aegisub", help="Aegisub 目录或其 automation 目录")
    ap.add_argument("--fontsdir", help="非 Windows 时查找样式字体的目录")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if not IS_WIN:
        FONTSDIR = a.fontsdir
    main(a.src, a.dst, find_automation(a.aegisub))
