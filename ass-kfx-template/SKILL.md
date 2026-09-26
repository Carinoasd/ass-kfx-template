---
name: ass-kfx-template
description: 为动画插入曲、OP、ED 制作 ASS 卡拉OK特效字幕（Aegisub kara-templater 模板），包括只用开头一个 {\k1} 的整句特效、主题装饰、双语歌词、补缺字、libass 截图验证。用户提到特效字幕、卡拉OK模板、k1、Aegisub 模板、歌词特效、karaoke template、.ass 歌词做效果、kfx、插入曲字幕，或上传 .ass 歌词要求「做漂亮一点」「做个模板」时都要用这个 skill，即使没有明确说「模板」。
---

# ASS 卡拉OK特效模板

Author: Carinoasd
Version: 3

这个 skill 让你为一首歌做出可在 Aegisub 里套用的特效模板，并在 Aegisub 外自己套用、截图检查，交付模板、成品和预览。

目录：
- `scripts/`：selftest.py（冒烟测试）、evolve.py（测试＋升版＋打包，见「自我进化」）、kt_apply.py（套用模板）、render.py（libass 截图）、review.py（逐句检查表）、glyph_check.py（查缺字）、glyph2ass.py（字转绘图、补字）、Yutils.lua（模板里用的特效工具库，MIT，来自 github.com/Youka/Yutils）
- `assets/starter_build.py`：起始模板生成器，能直接跑；`assets/shapes.py`：图形素材；`assets/examples/jam_jar/`：华丽范例的完整代码（只供阅读）
- `tests/smoke_song.ass`：冒烟测试用的歌词；`CHANGELOG.md`：每一版改了什么、还没做的想法
- `references/`：design-lessons.md（用户真实修改意见，**开工前必读**）、showcase-jam-jar.md（目标水准的完整范例，**设计前必读**）、templater-cookbook.md（写模板代码前读）、effect-recipes.md（选风格时读）、missing-glyphs.md（有缺字时读）

## 环境

- Python 依赖：`pip install lupa fonttools pillow numpy`；ffmpeg 要带 libass。
- Aegisub：kt_apply.py 需要 Aegisub 的 automation 目录（里面有 autoload/kara-templater.lua）。默认查 `C:\Program Files\Aegisub`，其他位置用 `--aegisub` 或环境变量 AEGISUB_DIR 指定。开始菜单里的是快捷方式，不是安装目录。
- **在 Windows 上用 Windows 的 Python 运行 kt_apply.py**，字宽测量和 Aegisub 完全一致。在 WSL、Linux 下也能跑，但字宽是按字体文件换算的，可能差零点几像素，只能用于预览；交付前在 Windows 侧重跑一次。
- 字体：样式用到的字体要装在系统里，或者用 `--fontsdir` 指定目录。
- Yutils（用了 `--yutils` 或模板里 require Yutils 时）：kt_apply.py 自己找得到，不用装；但用户要在 Aegisub 里重新套用，就得把 scripts/Yutils.lua 放进 Aegisub 的 `automation\include\`（或 `%APPDATA%\Aegisub\automation\include\`，装过 DependencyControl 的通常已经有）。

## 工作流程

### 1. 理解歌曲和画面
读 references/design-lessons.md。然后：
- 读 .ass：样式（字体、字号、位置、颜色）、每句时间和歌词，哪行是主语言、哪行是翻译。
- 看画面：视频不在手边就问路径。每句中间截一帧原片（`render.py 原歌词.ass 输出 --video 视频 时间...`），找切镜点。
- 读 references/showcase-jam-jar.md，看用户满意时的效果是什么水准。想一个同时回应歌词主题和画面内容的核心点子（例如「果酱把草莓存起来」对应「小事会被忘记」），再决定具体效果。starter 加几个飘动图形只是下限。
- 用几句话告诉用户你的理解和设计方向：歌词情绪、画面里的物件和颜色、打算用什么主题元素和配方（effect-recipes.md）、高潮卡在哪里。用户只给了简单要求时，说完直接做，不用等确认。

### 2. 查缺字
`python scripts/glyph_check.py 歌词.ass`。有缺字就按 missing-glyphs.md 给用户方案（拼字、借字体、换字），用户倾向不换字。

### 3. 生成模板
```
python assets/starter_build.py 歌词.ass 输出_template.ass --main 主行样式 --sub 副行样式 --theme berry [--glyph-json 补字.json] [--yutils]
```
- `--yutils`：多一套进场「描边预告」和一套退场「碎成粒子」，按字的真实形状做效果（effect-recipes.md 的 L、M）。歌词讲消逝、回忆、星空，或用户要「更华丽」时优先考虑。要自己写按字形的效果，读 templater-cookbook.md 第 12 节。
- 主行：视觉上的主角（字大的那行），挂装饰。副行：另一种语言。
- 起始模板是能跑的起点。按第 1 步的设计改：主题图形（shapes.py 或自己画，多层要包围盒锁定）、颜色、入场退场配方、节奏参数。改代码前读 templater-cookbook.md。
- 改的时候直接改 starter_build.py 的副本（放在工作目录），保留生成脚本，之后用户要改参数或换歌词都能重新生成。

### 4. 套用
```
python scripts/kt_apply.py 输出_template.ass 输出_fx.ass [--aegisub Aegisub目录]
```
模板器报错数必须是 0。报错时看 templater-cookbook.md 第 11 节。

### 5. 检查
除非用户说「不用检查」，否则每版都做：
- `python scripts/review.py 输出_fx.ass 检查 --video 视频 --style 主行样式`：每句入场、中间、退场各一帧。逐张看完。
- 同步：关键时刻（落地、切镜）前后逐帧截（间隔 0.042 秒）。
- 多层图形和补字：`render.py --crop 宽:高:x:y --zoom 4` 放大看对齐。
- 亮暗不同的镜头上都看一下文字是否清楚。
- 对照 design-lessons.md 自查：有没有逐字变色、装饰是否只在进退场、够不够丰富、相邻句是否重复、够不够长。

发现问题先改再给用户看。

### 6. 交付
- 原始文件不动；新版本另存（v2、v3），用户要求才覆盖。
- 三件：`_template.ass`（可在 Aegisub 里用「自动化 > 应用卡拉OK模板」重新套用）、`_fx.ass`（成品）、预览视频：
  ```
  ffmpeg -ss 起 -to 止 -copyts -i 视频 -vf "subtitles=输出_fx.ass" -c:a aac -ss 起 预览.mp4
  ```
  （在 .ass 所在目录运行，文件名避免逗号和方括号）
- 说明写清：每句只能开头一个 {\k1}、特效栏 karaoke；参数在第一行 code once 的哪里；哪些行必须放最后；只保证 libass；补了哪些字；用了 Yutils 的话，要把 Yutils.lua 一起交给用户并说明放哪个目录。
- 解释你做了什么、为什么这样设计、怎么验证的。

## 改版时

- 用户的意见往往指向 design-lessons.md 里的某一条，按那一条的做法改。
- 用户说「好看优先、不拘泥原样式」时，可以换颜色、描边、投影、字号，保留用户明说不换的（通常是字体）。
- 用户换了新歌词要求重新套用：用同一个生成脚本和随机种子，只换输入。
- 用户说「直接给 ass」：生成、套用、交付，跳过第 5 步。

## 自我进化

这个 skill 靠每次实际做歌时用户的意见长大。**每次交付后、用户给了意见或说满意时都做一次**，不用等用户提。
（Claude 不能直接改已安装的 skill，所以做法是改一份副本、测试、打包成新版 .skill 交给用户安装。）

### 1. 判断这次学到了什么

只记用户真的说过或明确认可的东西，不记自己的猜测。按种类放：

| 这次发生了什么 | 写到哪里 | 怎么写 |
|---|---|---|
| 用户指出第一版哪里不对（太素、不同步、逐字变色……） | references/design-lessons.md 对应小节 | 用户原话（引号）+ 以后第一版就该怎么做 + 这首歌的例子 |
| 做了一个新效果，用户说好看 | references/effect-recipes.md 新配方 | 适合什么歌、长什么样、letter()/装饰的写法、参数起点 |
| 新效果够通用、每首歌都可能用 | assets/starter_build.py 加成新的一套进场或退场（NV +1） | 同时改 selftest.py 让它被测到 |
| 踩到技术坑（模板器报错、位置偏移、渲染器差异） | templater-cookbook.md 第 11 节表格；能修的直接修脚本 | 现象 → 原因 → 做法 |
| 整首歌做到用户很满意 | references/ 加一份 showcase-歌名.md，代码放 assets/examples/歌名/ | 仿照 showcase-jam-jar.md：核心点子、时间线、为什么华丽 |

规则：
- 只对这首歌成立的偏好（「这首用蓝色」）不写成通则；写成通则前想想换一首歌还对不对。
- 新经验和旧经验冲突时，改旧条目并注明「（vN 起改为……）」，不要留两条互相矛盾的。
- 文件保持精简：同类条目合并，不要一直往后追加。

### 2. 改副本

把整个 skill 目录复制到工作目录（例如 `./ass-kfx-template/`），在副本上改。原本安装的那份不动。

### 3. 测试、升版、打包

```
python ass-kfx-template/scripts/evolve.py --note "一句话说明改了什么" [--note ...] --out 输出目录 --zip [--aegisub Aegisub目录]
```
它会先跑 selftest.py（每个主题、每套进退场都套用一遍，模板器报错必须为 0，再用 libass 截图）。
没通过就不会升版、不会打包：先修好。通过后 SKILL.md 的 Version +1、CHANGELOG.md 加一条、产出 `ass-kfx-template-vN.skill`（和 .zip）。
只想确认有没有改坏：`python scripts/selftest.py`。

### 4. 告诉用户

用一两句话说这次学到了什么、改了哪些文件、新版叫什么；提醒用户到设置的 Skills 区上传新 .skill 替换旧版（用户要的话也可以帮忙传到云端）。
CHANGELOG.md 底部的「还没做的想法」是下次进化的候选，做完一项就移到对应版本下面。

