"""冒烟测试：改过 skill 之后跑一遍，确认没有把原本能用的东西弄坏。

Author: Carinoasd

用法：
  python selftest.py [--aegisub Aegisub目录] [--font 字体族名] [--keep 输出目录] [--no-render]

做的事（用 tests/smoke_song.ass：有 1.2 秒的短句、带多个 \\k 的句子、英文和全角空格）：
  1. glyph_check.py 能跑
  2. 每个主题 × 有无 --yutils，各生成模板、套用：模板器报错必须是 0，特效行数必须 > 0
  3. 把进场、退场强制成第 1 到 NV 套，逐套套用：每一套都不能报错；
     --yutils 的第 5 套要真的生成描边（\\alpha&H60&）和粒子（m 0 0 l）
  4. 用 libass 渲染几帧，确认成品能被渲染（--no-render 跳过）
全部通过时退出码 0；evolve.py 打包前会先跑这个。
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from fontfind import find_font  # noqa: E402

SONG = os.path.join(ROOT, "tests", "smoke_song.ass")
PICK = "L.vin, L.vout = pick(NV, last.vin), pick(NV, last.vout)"
FONT_CANDIDATES = ["Microsoft JhengHei", "Microsoft YaHei", "Yu Gothic", "MS Gothic", "Meiryo",
                   "Noto Sans CJK TC", "Noto Sans CJK JP", "Noto Sans CJK SC", "Source Han Sans TC",
                   "WenQuanYi Zen Hei", "Droid Sans Fallback"]

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("  [通过] " if ok else "  [失败] ") + name + (f"：{detail}" if detail else ""))
    return ok


def run(args):
    r = subprocess.run([sys.executable] + args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout + r.stderr


def apply(tpl, fx, aeg, fontsdir):
    args = [os.path.join(HERE, "kt_apply.py"), tpl, fx]
    if aeg:
        args += ["--aegisub", aeg]
    if fontsdir:
        args += ["--fontsdir", fontsdir]
    code, out = run(args)
    m = re.search(r"其中特效行 (\d+) 行；模板器报错 (\d+) 条", out)
    if code != 0 or not m:
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        first = [l for l in lines if l.startswith("[aegisub.debug") or "Error" in l or "error:" in l]
        return False, (first[:2] or lines[-3:] or ["无输出"]), ""
    fx_n, err_n = int(m.group(1)), int(m.group(2))
    body = open(fx, encoding="utf-8-sig").read()
    return err_n == 0 and fx_n > 0, f"特效行 {fx_n}，报错 {err_n}", body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aegisub", help="Aegisub 目录（同 kt_apply.py）")
    ap.add_argument("--font", help="测试用的 CJK 字体族名；不填时自动找一个装着的")
    ap.add_argument("--keep", help="把测试产物留在这个目录（默认用完就删）")
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    font, hit = a.font, None
    for cand in ([font] if font else FONT_CANDIDATES):
        hit = find_font(cand)
        if hit:
            font = cand
            break
    if not hit:
        sys.exit("找不到可用的 CJK 字体，用 --font 指定一个装着的字体族名。")
    fontsdir = os.path.dirname(hit[0])
    print(f"测试字体：{font}（{hit[0]}）")

    work = a.keep or tempfile.mkdtemp(prefix="kfx_selftest_")
    os.makedirs(work, exist_ok=True)
    song = os.path.join(work, "smoke_song.ass")
    open(song, "w", encoding="utf-8-sig").write(open(SONG, encoding="utf-8-sig").read().replace("SMOKE_FONT", font))
    build = os.path.join(ROOT, "assets", "starter_build.py")

    print("1. 查缺字")
    code, out = run([os.path.join(HERE, "glyph_check.py"), song, "--fontsdir", fontsdir])
    check("glyph_check.py", code == 0, "" if code == 0 else out[-300:])

    print("2. 各主题 × 有无 Yutils")
    import importlib.util
    spec = importlib.util.spec_from_file_location("sb", build)
    sb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sb)
    last_fx = None
    for theme in sorted(sb.THEMES):
        for yu in (False, True):
            tag = f"{theme}{'+yutils' if yu else ''}"
            tpl, fx = os.path.join(work, f"{tag}_t.ass"), os.path.join(work, f"{tag}_fx.ass")
            code, out = run([build, song, tpl, "--main", "JP", "--sub", "CN", "--theme", theme] + (["--yutils"] if yu else []))
            if not check(f"生成模板 {tag}", code == 0, "" if code == 0 else out[-300:]):
                continue
            ok, detail, _ = apply(tpl, fx, a.aegisub, fontsdir)
            check(f"套用 {tag}", ok, detail if isinstance(detail, str) else " / ".join(detail))
            if ok:
                last_fx = fx

    print("3. 逐套强制进场、退场")
    for yu in (False, True):
        nv = 5 if yu else 4
        base = os.path.join(work, f"force{'_yu' if yu else ''}_t.ass")
        run([build, song, base, "--main", "JP", "--sub", "CN", "--theme", "berry"] + (["--yutils"] if yu else []))
        src = open(base, encoding="utf-8-sig").read()
        if not check(f"模板里找得到选套代码（{'yutils' if yu else '基本'}）", PICK in src, "" if PICK in src else "starter_build.py 改过 setupLine 的话，同步改 selftest.py 的 PICK"):
            continue
        for v in range(1, nv + 1):
            tpl = os.path.join(work, f"force{'_yu' if yu else ''}_{v}_t.ass")
            fx = tpl.replace("_t.ass", "_fx.ass")
            open(tpl, "w", encoding="utf-8-sig").write(src.replace(PICK, f"L.vin, L.vout = {v}, {v}"))
            ok, detail, body = apply(tpl, fx, a.aegisub, fontsdir)
            check(f"第 {v} 套{'（yutils）' if yu else ''}", ok, detail if isinstance(detail, str) else " / ".join(detail))
            if ok and yu and v == 5:
                check("描边预告有生成", "\\alpha&H60&" in body)
                check("碎成粒子有生成", "\\p1}m 0 0 l " in body)

    if not a.no_render and last_fx:
        print("4. libass 渲染")
        if not shutil.which("ffmpeg"):
            check("ffmpeg", False, "找不到 ffmpeg，跳过渲染可加 --no-render")
        else:
            out_dir = os.path.join(work, "render")
            code, out = run([os.path.join(HERE, "render.py"), last_fx, out_dir, "1.4", "4.0", "8.8", "--fontsdir", fontsdir])
            check("render.py 截图", code == 0 and os.path.isdir(out_dir) and len(os.listdir(out_dir)) > 0, "" if code == 0 else out[-300:])

    bad = [r for r in results if not r[1]]
    print(f"\n结果：{len(results) - len(bad)} 项通过，{len(bad)} 项失败" + (f"；产物在 {work}" if a.keep else ""))
    if not a.keep:
        shutil.rmtree(work, ignore_errors=True)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
