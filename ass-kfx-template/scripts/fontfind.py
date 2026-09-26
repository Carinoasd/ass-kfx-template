"""按字体族名找到字体文件，供 kt_apply / glyph_check / glyph2ass 共用。

Author: Carinoasd

查找顺序：--fontsdir 指定的目录 > 系统字体目录（Windows、macOS、Linux）。
按 name 表里的族名（ID 1、4、16）匹配，TTC 也会逐个子字体查。
"""
import os
import sys

from fontTools.ttLib import TTCollection, TTFont

_SYS_DIRS = [
    r"C:\Windows\Fonts",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts"),
    "/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts"),
    os.path.expanduser("~/.local/share/fonts"), "/Library/Fonts", "/System/Library/Fonts",
    os.path.expanduser("~/Library/Fonts"),
    # WSL 下可以直接读 Windows 字体
    "/mnt/c/Windows/Fonts",
]
_EXT = (".ttf", ".otf", ".ttc", ".otc")
_index = None


def _info(font):
    """取出匹配要用的名字：全名(4)、族名(1)、子族名(2)、印刷族名(16)，以及字重和是否斜体。"""
    n = {1: set(), 2: set(), 4: set(), 16: set()}
    for rec in font["name"].names:
        if rec.nameID in n:
            try:
                n[rec.nameID].add(rec.toUnicode().strip().lower())
            except Exception:
                pass
    os2 = font["OS/2"] if "OS/2" in font else None
    weight = os2.usWeightClass if os2 is not None else 400
    italic = bool(os2.fsSelection & 1) if os2 is not None else False
    return n, weight, italic


_REGULAR = {"regular", "normal", "book", "roman", "standard"}


def _scan(dirs):
    """返回 {名字: [(优先级, 字重, 斜体, 路径, 子字体序号), ...]}"""
    idx = {}
    for d in dirs:
        if not d or not os.path.isdir(d):
            continue
        for root, _, files in os.walk(d):
            for fn in files:
                if not fn.lower().endswith(_EXT):
                    continue
                p = os.path.join(root, fn)
                try:
                    if fn.lower().endswith((".ttc", ".otc")):
                        fonts = TTCollection(p, lazy=True).fonts
                    else:
                        fonts = [TTFont(p, lazy=True)]
                    for i, f in enumerate(fonts):
                        n, w, it = _info(f)
                        regular = bool(n[2] & _REGULAR)
                        for name in n[4]:
                            idx.setdefault(name, []).append((0, w, it, p, i))
                        for name in n[1]:
                            idx.setdefault(name, []).append((1 if regular else 2, w, it, p, i))
                        for name in n[16]:
                            idx.setdefault(name, []).append((3, w, it, p, i))
                except Exception:
                    continue
    return idx


def _best(cands, bold):
    target = 700 if bold else 400
    # 粗体样式：同名的各字重一视同仁，按字重挑，和 GDI 请求 700 时的行为一致
    c = min(cands, key=lambda t: ((t[0] if not bold else (1 if t[0] < 3 else 3)), t[2], abs(t[1] - target)))
    return c[3], c[4]


def find_font(family, fontsdir=None, bold=False):
    """返回 (路径, TTC 子字体序号)，找不到返回 None。

    和 libass/GDI 的选择接近：优先全名或族名完全相同的常规体；
    同一族有多个字重时选最接近 400（bold=True 时 700）的非斜体。
    """
    global _index
    key = family.strip().lstrip("@").lower()
    if fontsdir:
        local = _scan([fontsdir])
        if key in local:
            return _best(local[key], bold)
    if _index is None:
        _index = _scan(_SYS_DIRS)
    if key in _index:
        return _best(_index[key], bold)
    return None


def open_font(family_or_path, fontsdir=None):
    """接受字体文件路径或族名，返回 TTFont。"""
    if os.path.isfile(family_or_path):
        if family_or_path.lower().endswith((".ttc", ".otc")):
            return TTFont(family_or_path, fontNumber=0)
        return TTFont(family_or_path)
    hit = find_font(family_or_path, fontsdir)
    if not hit:
        sys.exit(f"找不到字体：{family_or_path}。用 --fontsdir 指定字体所在目录，或直接传字体文件路径。")
    path, num = hit
    return TTFont(path, fontNumber=num)


def vmetrics(font):
    """libass 换算字号用的上伸和总高（字体单位）：优先 OS/2 的 win 值。"""
    os2 = font["OS/2"] if "OS/2" in font else None
    if os2 is not None and (os2.usWinAscent + os2.usWinDescent) > 0:
        return os2.usWinAscent, os2.usWinAscent + os2.usWinDescent
    hh = font["hhea"]
    return hh.ascent, hh.ascent - hh.descent
