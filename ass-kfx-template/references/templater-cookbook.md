# Aegisub 卡拉OK模板器技术手册

写模板代码前读这一份。assets/starter_build.py 里每一条都有实际用法，可以对照着看。

## 目录
1. 一个 {\k1} 的整句写法
2. 模板行的种类和写法限制
3. 逐字序号 idx()
4. 装饰：maxloop、retime、relayer
5. 带加速的位移：绕远处 \org 旋转
6. 多层矢量图形对齐：包围盒锁定
7. 用 \clip 做液面、揭示、扫光
8. 读取整首歌时间的「全局行」
9. 随机数和可重复性
10. 模板文件里的说明注释
11. 常见错误
12. 用 Yutils：字转轮廓、描边、转像素

## 1. 一个 {\k1} 的整句写法

用户通常要求「只在开头放一个 k1，不要每个音节打 k」。这时整句就是一个音节：

```
Comment: 0,0:19:24.68,0:19:28.90,日,,0,0,0,karaoke,{\k1}赤い実をひとつずつ
```

- 特效栏必须是 karaoke，否则模板器不处理。
- 逐字效果用 `template char`，它把这个音节拆成单字，每个字给出 syl.center、syl.left 等位置。
- 节奏全靠时间计算（逐字间隔 = 句长 × 系数 / 字数，再夹在上下限之间），不靠 \k。
- 句子里多出别的 \k 会把一句拆成多个音节，逐字序号和位置修正全部错乱。starter_build.py 会先删掉原有 \k 再加 {\k1}。

## 2. 模板行的种类和写法限制

| 特效栏 | 作用 |
|---|---|
| `code once` | 整个文件只执行一次。放参数表、图形、函数定义 |
| `code line` | 每句执行一次，在该句的各模板之前。放 setupLine() |
| `template char notext` | 每个字生成一行；notext 表示不自动附加原字，文字由函数返回 |
| `template syl noblank notext` | 每个音节生成一行；整句只有一个音节时每句一次，适合放装饰 |

模板行的样式决定它作用于哪个样式的歌词。主副两个样式各写一套。

写法限制（出错最多的地方）：

- code 行必须是一行。starter_build.py 的 lua() 会把多行代码拼成一行，所以源码里**不能用 `--` 行注释**（拼接后会把后面全部注释掉），说明只能写成 `--[[ ... ]]`。
- 模板文本里 `!函数()!` 会执行并替换成返回值；`$变量` 会被替换，所以返回的标签字符串里避免出现 `$`。
- code 环境里能直接用 string、math、line、orgline、syl、j、maxj、retime、relayer、maxloop；其他全局要写 `_G.`，例如 `_G.tonumber`、`_G.table.concat`、`_G.ipairs`、`_G.unicode.chars`、`_G.aegisub.text_extents`。
- 逐字模板**不会跳过空格**：空格也会调用一次函数。starter 的 letter() 对空格返回空串并 `retime("preline",0,0)`，生成的是零时长空行，画面上不显示。
- orgline 是原歌词行（有 left、top、width、height、middle、styleref、duration、actor），line 是正在生成的新行。

## 3. 逐字序号 idx()

逐字模板里，同一模板行处理的所有字共用同一个 syl 表对象，换模板行才换对象。据此数序号：

```lua
function idx()
  if syl ~= _lastsyl then _lastsyl = syl; _k = 0 end
  if j == 1 then _k = _k + 1 end
  return _k
end
```

投影层和文字层是两个模板行，各自从 1 数起，两层的第 k 个字对应同一个字。

## 4. 装饰：maxloop、retime、relayer

装饰数量每句不同，在 setupLine() 里先算好一张事件表 L.ev，再在 syl 模板里展开：

```lua
function extras()
  if j == 1 then maxloop(#L.ev) end   -- 第一次进来决定循环次数
  local e = L.ev[j]
  retime("preline", e.t0, e.t1)        -- 相对句首的起止时间，可以为负（提前出现）
  relayer(30)                          -- 改图层
  return "{" .. e.tags .. "\\p1}" .. SHAPE
end
```

- 没有装饰的句子也要放一个零时长占位事件，否则 maxloop(0) 行为不确定。
- 多层图形（例如草莓三层）：每个事件的每一层各占一行。starter 在 setupLine() 末尾把事件展开成工作表 L.jobs（主题图形 × 层数、闪光和自带绘图 e.d 各一行），extras() 里 `maxloop(#L.jobs)`，第 j 行取 `L.jobs[j]`。这样不会生成一堆零时长的空行。
- retime 之后，\t、\move 的时间都相对新的起点计算。

## 5. 带加速的位移：绕远处 \org 旋转

\move 是匀速的，没有缓动参数。要做重力下落、弹起减速，把 \org 放在字左边很远处（R = 4000px），用 \frz 小角度旋转来近似上下平移，这样 \t 的加速参数就作用在位移上：

```lua
function vt(v)  -- 竖直位移 v 像素（负数向上）对应的角度
  return string.format("%.4f", math.deg(math.asin(-v / P.R)))
end
-- 从上方 16px 加速落下：
"\\an2\\pos(x,y)\\org(x-4000,y)\\frz" .. vt(-16) .. "\\t(a,a+240,2,\\frz0)"
-- 退场再上浮 18px：
"\\t(o,o+380,0.7,\\frz" .. vt(-18) .. ")"
```

- 加速参数大于 1 是先慢后快（下落），小于 1 是先快后慢（弹起、上浮）。
- 旋转角度极小（16px 约 0.23°），字本身看不出倾斜。
- 这一招占用了 \frz，同一行不能再用 \frz 做自转。需要自转的装饰改用 \move 加 \t(\frz)。
- 横向位移同理：\org 放在正上方或正下方远处。

## 6. 多层矢量图形对齐：包围盒锁定

libass 按绘图的包围盒对齐 \an。草莓的果身、籽、叶子三层形状不同，包围盒不同，直接叠会错位。每层开头加同样的两个空 move：

```
m 0 0 m 52 60 m 26 14 b 36 9 ...     果身
m 0 0 m 52 60 m 13 29 b ...          籽
```

这样三层包围盒都是 52×60，同样的 \an \pos \fscx \frz 下严丝合缝。补字的字形也用同样方法（`m 0 0 m 字宽 字高`）和文字对齐。

VSFilter 不认这种写法，会画碎。用户确认只要 libass 时才用；这一点要写进交付说明。

## 7. 用 \clip 做液面、揭示、扫光

矩形 \clip 可以放进 \t 里动画：

```
\clip(0,300,1920,1080)\t(1000,1550,0.6,\clip(0,280,1920,1080))   液面上涨 20px
\clip(x0,top,x0,bottom)\t(a,a+400,\clip(x0,top,x1,bottom))        从左到右写出
```

矢量 \clip(绘图) 不能动画，但可以用来把装饰限制在某个形状里（例如气泡只在罐子内部出现）。

## 8. 读取整首歌时间的「全局行」

需要跨句的效果（罐子随每句歌词装满、最后一句封口）时：

1. 每句的 setupLine() 把关键时刻存进全局表，例如 `SONG[#SONG+1] = {s=..., e=..., land=...}`。
2. 另建一个样式和一句放在**所有歌词之后**的注释行，它的模板一次读完 SONG，生成整首歌的全局装饰（用 `retime("set", 绝对开始, 绝对结束)`）。
3. 这一行的开始时间设成最后一句的结束时间，按时间排序后仍在最后。交付说明里写明「这一行必须放最后」。

## 9. 随机数和可重复性

code once 第一行 `math.randomseed(固定数字)`。同一个模板重复套用结果完全一样，用户说「再套一次新歌词」时不会莫名其妙变样。想要另一种随机排布就换种子。

避免重复感：进场、退场各准备 3 到 4 套动作，记住上一句用的哪套（按样式分别记），新句随机选一套不同的。数量、大小、角度、间隔也在小范围内随机。

## 10. 模板文件里的说明注释

模板文件开头放几行无特效的注释行，写：怎么用（{\k1}、karaoke、应用模板）、哪些行必须放在哪、参数在哪、图层用途、只保证哪个渲染器、补了哪些字。用户会在 Aegisub 里直接看到。

## 11. 常见错误

| 现象 | 原因 |
|---|---|
| 模板器报 attempt to perform arithmetic on nil | 序号越界：字数统计和 idx() 计数口径不同（例如一个跳过空格一个没跳） |
| 某句完全没有特效 | 这句没有 {\k1}，或特效栏不是 karaoke，或样式和模板行样式不同 |
| 字的位置整体偏 1 到 2 像素 | 补字的绘图宽度和原字宽不同，没做位置修正；或者在非 Windows 上测量字宽 |
| 多层图形错位 | 某层漏了包围盒锁定，或各层 \fscx、\pos 不一致 |
| 装饰动画不同步 | \t 时间是相对该行开始的，retime 改了开始时间后要重新算 |
| 重新套用后旧特效还在 | 旧的 fx 行没删；kara-templater 会自动删 effect 为 fx 的行，手动改过 effect 的不会删 |
| 报「找不到 Yutils」 | Aegisub 的 automation/include 里没有 Yutils.lua，见第 12 节 |

## 12. 用 Yutils：字转轮廓、描边、转像素

[Yutils](https://github.com/Youka/Yutils)（MIT 授权）是 ASS 特效常用的 Lua 工具库。模板器只给得出字的位置和宽度，Yutils 能给出**字的形状**，所以能做出「按字形碎成粒子」「空心描边」「沿笔画走光」这类效果。skill 自带一份在 scripts/Yutils.lua。

**安装（在 Aegisub 里用必做）**：把 scripts/Yutils.lua 复制到 `Aegisub安装目录\automation\include\` 或 `%APPDATA%\Aegisub\automation\include\`。装过 DependencyControl 的，那里多半已经有 Yutils.lua，不用再放。kt_apply.py 找的顺序一样：先找这两个目录，都没有才用 skill 自带的。

**载入**：code once 里
```lua
function yu()
  if YU == nil then
    local ok, m = _G.pcall(_G.require, "Yutils")
    if not ok then _G.error("找不到 Yutils：把 Yutils.lua 放进 Aegisub 的 automation/include 目录。" .. _G.tostring(m)) end
    YU = m
  end
  return YU
end
```
用 pcall 包起来，没装时给用户看得懂的错误，而不是一长串堆栈。

**常用函数**（完整清单在 Yutils.lua 开头的注释里）：

| 函数 | 做什么 | 用在哪 |
|---|---|---|
| `Y.decode.create_font(字体, 粗, 斜, 下划线, 删除线, 字号, x缩放, y缩放, 字距).text_to_shape(字)` | 字 → 绘图轮廓（像素，原点在字格左上角） | 一切按字形做的效果 |
| `Y.shape.to_outline(Y.shape.flatten(形状), 线宽)` | 实心形状 → 空心描边 | 配方 L |
| `Y.shape.to_pixels(形状)` | 形状 → 像素点表 `{x, y, alpha}` | 配方 M |
| `Y.shape.split(形状, 最大段长)` | 把长线段切短，点变密 | 配方 N、变形前细分 |
| `Y.shape.filter(形状, function(x, y) return 新x, 新y end)` | 逐点变换（波浪、扭曲、放射） | 字形变形 |
| `Y.shape.bounding(形状)` | 包围盒 x0, y0, x1, y1 | 定位、居中 |
| `Y.math.bezier(比例, 控制点)` | 贝塞尔曲线上的点 | 装饰沿曲线飞 |

**坐标约定（最容易出错）**：
- create_font 的 x缩放、y缩放是**比例**（1 = 100%），传 `st.scale_x / 100`；粗体、斜体要传 true/false。
- text_to_shape 的原点是字格左上角：放到画面上用 `\an7\pos(字格左, 行顶)`，字格左 = `orgline.left + 前面字宽之和`（starter 存在 L.cl[k]），行顶 = `orgline.top`。
- 绘图前面加包围盒锁定 `m 0 0 m 字宽 字高`（第 6 节），不然 libass 按轮廓的包围盒对齐，会整体偏移。
- to_pixels 返回的 x、y 和原形状同一套坐标，直接加到字格左上角就是屏幕位置。

**缓存**：text_to_shape 和 to_pixels 都慢，同一个字在同一个样式下只算一次（starter 的 ychar() 用 `样式名|字` 当键存进 YS）。

**在 Aegisub 外预览**：Windows 上 kt_apply.py 直接用 Yutils 自己的 GDI 取轮廓，和 Aegisub 一致。WSL、Linux 上 Yutils 要 pangocairo，常常没有，kt_apply.py 会改用 Python 按字体文件取轮廓，位置可能差零点几像素，只用于预览。

