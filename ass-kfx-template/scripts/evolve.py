"""自我进化的最后一步：跑冒烟测试 → 升版本号 → 写更新记录 → 打包成新的 .skill。

Author: Carinoasd

用法（在改好的 skill 副本上跑，不要直接改已安装的那份）：
  python evolve.py --note "改了什么" [--note "又改了什么"] [--out 输出目录] [--zip]
                   [--aegisub Aegisub目录] [--font 字体] [--dry-run]

- 冒烟测试（selftest.py）没全部通过就停下，不升版、不打包。
- 版本号在 SKILL.md 的「Version: N」一行，每次 +1。
- 更新记录写在 CHANGELOG.md 最上面（日期 + 每条 --note）。
- 打包成 输出目录/ass-kfx-template-vN.skill（--zip 时再多一份 .zip，内容相同）。
- --dry-run：只跑测试、显示会升到几版，不改任何文件。
"""
import argparse
import datetime
import os
import re
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NAME = os.path.basename(ROOT)
SKIP_DIRS = {"__pycache__", ".git", "dist"}


def pack(out_path):
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for base, dirs, files in os.walk(ROOT):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for f in sorted(files):
                if f.endswith((".pyc", ".skill")):
                    continue
                full = os.path.join(base, f)
                z.write(full, os.path.join(NAME, os.path.relpath(full, ROOT)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--note", action="append", required=True, help="这次改了什么（可写多条）")
    ap.add_argument("--out", default=os.getcwd(), help="新 .skill 放哪里（默认当前目录）")
    ap.add_argument("--zip", action="store_true", help="另存一份 .zip（方便上传云端）")
    ap.add_argument("--aegisub")
    ap.add_argument("--font")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("== 冒烟测试 ==")
    cmd = [sys.executable, os.path.join(HERE, "selftest.py")]
    if a.aegisub:
        cmd += ["--aegisub", a.aegisub]
    if a.font:
        cmd += ["--font", a.font]
    if subprocess.run(cmd).returncode != 0:
        sys.exit("冒烟测试没通过：先修好再进化。原来的版本没有被改动。")

    skill_md = os.path.join(ROOT, "SKILL.md")
    text = open(skill_md, encoding="utf-8").read()
    m = re.search(r"^Version: (\d+)$", text, flags=re.M)
    if not m:
        sys.exit("SKILL.md 里找不到「Version: N」这一行。")
    new = int(m.group(1)) + 1
    print(f"== 版本 {m.group(1)} → {new} ==")
    if a.dry_run:
        print("dry-run：不改文件、不打包。")
        return

    open(skill_md, "w", encoding="utf-8").write(text[:m.start()] + f"Version: {new}" + text[m.end():])
    log = os.path.join(ROOT, "CHANGELOG.md")
    old = open(log, encoding="utf-8").read() if os.path.exists(log) else "# 更新记录\n"
    head, _, rest = old.partition("\n")
    entry = f"\n## v{new}（{datetime.date.today().isoformat()}）\n" + "".join(f"- {n}\n" for n in a.note)
    open(log, "w", encoding="utf-8").write(head + "\n" + entry + rest)

    os.makedirs(a.out, exist_ok=True)
    out = os.path.join(a.out, f"{NAME}-v{new}.skill")
    pack(out)
    print(f"已打包：{out}")
    if a.zip:
        z = out[:-6] + ".zip"
        pack(z)
        print(f"已打包：{z}")


if __name__ == "__main__":
    main()
