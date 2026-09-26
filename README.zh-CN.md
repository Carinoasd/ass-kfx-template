# ass-kfx-template

[繁體中文](README.md) ｜ **简体中文** ｜ [English](README.en.md)

> 一个给 Claude 用的 skill：把一份普通的 ASS 歌词，变成动画插入曲／OP／ED 等级的**卡拉OK特效字幕**。
> Claude 会读歌词、看画面、设计特效、自己套用、自己截屏检查，最后交给你「模板＋成品＋预览视频」三件。

| 字落下回弹＋主题图形（草莓） | 描边预告（Yutils） | 碎成粒子（Yutils） |
|---|---|---|
| ![落下回弹](docs/images/berry.gif) | ![描边预告](docs/images/ghost.gif) | ![碎成粒子](docs/images/dust.gif) |

---

## 这是什么？

先打个比方：

- **ASS 字幕**像是一张「字要放在哪、什么颜色」的清单。
- **Aegisub 的卡拉OK模板**像是一套「动作剧本」：写一次「每个字从上面掉下来、落地压扁弹一下」，它就会帮整首歌每一句、每一个字生出对应的动画。
- **这个 skill** 则是教 Claude 当一个「会写动作剧本的特效师」：它知道怎么写剧本、怎么在 Aegisub 外面自己试演、怎么截屏挑毛病，也记得过去被用户指正过的地方。

所以你只要丢一份歌词 `.ass`（最好再给视频），说一句「帮这首歌做特效」，就能拿到可以直接压进视频的特效字幕。

## 可以做到什么？

### 1. 真正「设计」过的特效，不是套公式

Claude 会先理解歌曲再动手：

- 读完整首歌词，抓出情绪（例如「小事终究会被忘记」）。
- 在每句中间截一张原片，看画面里有什么对象、颜色（例如主角在做草莓果酱）。
- 找出切镜时间点，把特效的高潮卡在切镜那一格。
- 想一个把歌词和画面连起来的「内核点子」。

skill 里附了一个完整范例「果酱罐」：果酱就是把草莓存起来，歌词说小事会忘，那就让整首歌一句一句把草莓存进罐子里，罐子从空到满，最后在切到果酱罐的镜头时盖上红白格子布、绑蝴蝶结。

### 2. 起始模板一行指令就生成

```bash
python ass-kfx-template/assets/starter_build.py 歌词.ass 输出_template.ass --main 日文样式 --sub 中文样式 --theme berry --yutils
```

生成的模板已经能跑，内容包括：

| 部分 | 效果 |
|---|---|
| 主行（大字） | 字从上方依序快速落下，落地压扁再回弹，颜色从闪色褪回本色 |
| 副行（翻译） | 在主行第一个字落地的同一格，从下方依序弹出 |
| 主题图形 | 草莓 🍓／花／爱心／星星 四种，**只在进场和退场出现**，不会一直挂在旁边 |
| 进场动作 | 5 套（从两侧飞入、从下方弹起、从上方砸落、沿上下缘穿过、描边预告） |
| 退场动作 | 5 套（冒出上浮、中心炸开、沿字顶扫过、加速下坠、碎成粒子） |
| 防重复 | 相邻两句不会用同一套；数量、大小、角度再小幅随机 |
| 短句 | 装饰动画按比例压缩，但不低于一半 |
| 最后一句 | 单独的收尾：主题图形沿字顶慢慢滑过，留下一串闪光 |

所有参数（颜色、时间、高度……）都集中在模板第一行的 `C`、`P` 表里，想改在 Aegisub 里就能改。

### 3. 用 Yutils 做「照着字形」的特效

加上 `--yutils` 后，模板会在运行时加载 [Yutils](https://github.com/Youka/Yutils)，把字转成真正的轮廓：

- **描边预告**：字掉下来之前，落点先亮起一个空心的字形轮廓，字落进去时轮廓淡掉。像在说「这里马上会出现一个字」。
- **碎成粒子**：退场时，字照原本的笔画碎成几十颗小方块，从左到右依序起飞、上飘、缩小消失。远看还是那个字，接着慢慢散掉。很适合讲「消逝」「回忆」「星空」的歌。

参考文档里还写了「沿轮廓走光」等更多照字形做的配方。

### 4. 不用开 Aegisub 也能套用、截屏

| 工具 | 做什么 |
|---|---|
| `kt_apply.py` | 直接运行 Aegisub 内置的 `kara-templater.lua`，结果和在 Aegisub 里按「套用卡拉OK模板」一样 |
| `render.py` | 用 libass（ffmpeg）把指定时间点截成图，也能连续截屏、放大局部 |
| `review.py` | 每句在进场、句中、退场各截一张，排成一张总览图，一眼看完整首 |

Claude 每做一版都会自己截屏逐张看，确认同步、对齐、在亮暗背景上都看得清楚，发现问题先修再给你看。

### 5. 自动处理缺字

`glyph_check.py` 开工第一步就检查字体缺哪些字。遇到缺字时，`glyph2ass.py` 可以用本字体的笔画**拼出**缺的字（例如用「别」「気」的部件拼），或从另一个字体借字，尽量不换字。

### 6. 会自我进化

这个 skill 会随着每次做歌变强：

1. **记笔记**：每次交付后，用户的意见会分类写回 skill 里。例如用户说「太素了」，就记进设计经验；说「这个效果好看」，就存进特效配方库。
2. **防呆测试**：`selftest.py` 会跑 31 项冒烟测试，每个主题、每一套进退场都实际套用一次，模板器报错必须是 0，最后再用 libass 截屏。
3. **升版打包**：`evolve.py` 先跑测试，**没过就拒绝升版、拒绝打包**；过了才会把版本号 +1、写进 `CHANGELOG.md`，并打包成新的 `.skill`。

## 安装

### 当作 Claude skill 使用（推荐）

1. 把 `ass-kfx-template/` 这个文件夹压成 zip，扩展名改成 `.skill`（或直接用 `.zip`）。
2. 在 Claude 的设置里找到 Skills，上传这个文件。
3. 之后对 Claude 说「帮这首插入曲做特效字幕」「做个卡拉OK模板」，它就会自动使用这个 skill。

### 自己在电脑上跑脚本

需要：

- Python 3，加上 `pip install lupa fonttools pillow numpy`
- 带 libass 的 ffmpeg
- Aegisub（`kt_apply.py` 要用到它的 `automation/autoload/kara-templater.lua`）

> 💡 在 Windows 上请用 **Windows 的 Python** 跑 `kt_apply.py`，字宽测量才会和 Aegisub 完全一致。WSL／Linux 也能跑，但可能差零点几像素，只适合预览。

### 用到 Yutils 时

如果要在 Aegisub 里重新套用有 `--yutils` 的模板，请把 `ass-kfx-template/scripts/Yutils.lua` 拷贝到下面任一个文件夹（装过 DependencyControl 的通常已经有，不用再放）：

- `Aegisub 安装目录\automation\include\`
- `%APPDATA%\Aegisub\automation\include\`

## 快速上手（手动流程）

```bash
cd ass-kfx-template

# 1. 查缺字
python scripts/glyph_check.py 歌词.ass

# 2. 生成起始模板
python assets/starter_build.py 歌词.ass song_template.ass --main 日 --sub 中 --theme berry --yutils

# 3. 套用（模板器报错必须是 0）
python scripts/kt_apply.py song_template.ass song_fx.ass --aegisub "C:\Program Files\Aegisub"

# 4. 截屏检查（每句进场／句中／退场）
python scripts/review.py song_fx.ass check --video 原片.mp4 --style 日

# 5. 压预览视频
ffmpeg -ss 起 -to 止 -copyts -i 原片.mp4 -vf "subtitles=song_fx.ass" -c:a aac -ss 起 preview.mp4
```

歌词的写法有一个规定：**每句开头只放一个 `{\k1}`，特效栏填 `karaoke`**。`starter_build.py` 会自动帮你改好。

## 文件结构

```
ass-kfx-template/
├── SKILL.md                  给 Claude 看的操作说明（工作流程、交付规范、自我进化）
├── CHANGELOG.md              每一版改了什么、还没做的想法
├── requirements.txt
├── assets/
│   ├── starter_build.py      起始模板生成器（主题、5 套进场、5 套退场）
│   ├── shapes.py             主题图形素材（草莓、花、爱心、星星……）
│   └── examples/jam_jar/     「果酱罐」完整范例的代码（只供阅读）
├── scripts/
│   ├── kt_apply.py / mock.lua  在 Aegisub 外运行 kara-templater
│   ├── render.py / review.py   libass 截屏、逐句总览
│   ├── glyph_check.py / glyph2ass.py / fontfind.py   查缺字、字转绘图、拼字
│   ├── Yutils.lua            Yutils 函数库（MIT）
│   ├── selftest.py           冒烟测试
│   └── evolve.py             测试 → 升版 → 打包
├── references/
│   ├── design-lessons.md     用户真实的修改意见（开工前必读）
│   ├── showcase-jam-jar.md   目标水准的完整范例解说
│   ├── effect-recipes.md     特效配方库 A～N（落下回弹、打字机、水墨晕开、碎成粒子……）
│   ├── templater-cookbook.md 模板器技术手册（含 Yutils 用法）
│   └── missing-glyphs.md     补缺字方法
└── tests/smoke_song.ass      冒烟测试用的歌词
```

## 限制

- 只保证 **libass**（mpv、ffmpeg 压制、MPC-HC 的 libass 模式）。VSFilter 不支持包围盒锁定的写法，多层图形会错位。
- 「碎成粒子」一句 10 个字大约会多 600 行事件。压制没有问题；播放器即时播放吃力时，可以调大 `YP.step` 或调小 `YP.max`。
- Windows 上直接通过 Yutils 用 GDI 取字形的路径，还没在真正的 Windows 上跑过 `selftest.py`（见 `CHANGELOG.md`「还没做的想法」）。

## 授权

MIT © Carinoasd。`scripts/Yutils.lua` 来自 [Youka/Yutils](https://github.com/Youka/Yutils)，同为 MIT 授权，原始版权声明保留在文件开头。
