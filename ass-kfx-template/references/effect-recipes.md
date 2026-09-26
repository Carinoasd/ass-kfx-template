# 特效配方库

每个配方给出：适合什么歌、效果长什么样、放进 letter() 的标签写法（入场 / 退场），以及需要的装饰。
变量沿用 starter_build.py：`a` 是这个字的入场时刻（ms，相对句首），`o` 是退场时刻，`x, y` 是字的定位点（\an2，字底中点），
`L.yt L.yb` 是行的上下沿，`L.x0 L.x1` 是行的左右端，`L.out` 是退场时长，`k` 是第几个字，`L.n` 是字数。

配方可以组合：入场用一个、退场用另一个、装饰再选一个。选之前先按 design-lessons.md 理解歌词和画面。
每换一个配方都要用 render.py 截图确认，这里的数值是起点。

## 目录
| 配方 | 气氛 |
|---|---|
| A 落下回弹（starter 默认） | 轻松、可爱、日常 |
| B 打字机 | 独白、回忆、信件 |
| C 失焦对焦 | 梦境、朦胧、抒情 |
| D 手写揭示 | 日记、书信、温柔 |
| E 光带扫过 | 温暖、希望、副歌高潮 |
| F 卡片翻转 | 明快、节奏感强 |
| G 渐变色字 | 青春、彩色、多样 |
| H 水墨晕开 | 古风、和风、安静 |
| I 震动故障 | 激烈、紧张、电子、摇滚 |
| J 碎裂退场 | 离别、崩溃、高潮后的收尾 |
| K 飘落消散 | 感伤、结束、季节感 |
| L 描边预告（Yutils） | 期待、预感、副歌前的铺垫 |
| M 碎成粒子（Yutils） | 消逝、回忆散去、星空、魔法 |
| N 沿轮廓走光（Yutils） | 华丽、闪耀、高潮 |

L、M、N 要在模板里 require Yutils，写法和坐标约定见 templater-cookbook.md 第 12 节。starter_build.py 加 `--yutils` 就带 L（进场第 5 套）和 M（退场第 5 套）。

---

## A 落下回弹
starter_build.py 已实现。字从上方加速落下（\org 旋转位移），落地压扁回弹，颜色从闪色褪成本色。副行在主行第一个字落地时从下方弹出。

## B 打字机
字一个个硬切出现（没有淡入），后面跟一个闪烁的光标。逐字间隔放慢到 50 到 90ms，让人感觉在打字。

入场：
```lua
s = s .. string.format("\\alpha&HFF&\\t(%d,%d,\\alpha&H00&)", a, a + 1)
```
光标（用 syl 模板的装饰事件，每句一个）：一个细长矩形 `m 0 0 l 4 0 l 4 44 l 0 44`，
在每个字出现时跳到这个字的右边（每个字一个事件，时长到下一个字出现），最后一个字后闪烁 3 次再消失：
```lua
-- 第 k 个字的光标事件
spec(tin(k), tin(k + 1), string.format("\\an7\\pos(%s,%s)\\1c&HFFFFFF&\\bord0", fn(L.cx[k] + w/2 + 2), fn(L.yt + 4)))
-- 结尾闪烁
"\\t(0,1,\\alpha&HFF&)\\t(300,301,\\alpha&H00&)\\t(600,601,\\alpha&HFF&)\\t(900,901,\\alpha&H00&)"
```
退场：整行同时淡出 300ms，或倒序逐字删除（o 改成 `L.dur - L.out - (k-1)*L.ostag`）。

## C 失焦对焦
字从大而模糊、透明，缩小聚焦成清晰。适合慢歌，入场时长放到 500 到 700ms，逐字间隔 40 到 60ms。

入场：
```lua
s = s .. string.format("\\alpha&HFF&\\blur12\\fscx135\\fscy135\\t(%d,%d,0.6,\\alpha&H00&\\blur0.6\\fscx100\\fscy100)", a, a + 600)
```
退场（反向散焦上浮）：
```lua
s = s .. string.format("\\t(%d,%d,1.5,\\alpha&HFF&\\blur10\\fscx120\\fscy120)", o, o + L.out)
```
装饰：几颗大而虚的光斑（DOT 放大到 800% 以上、\blur15、\alpha&HC0&）缓慢漂移，表现景深。

## D 手写揭示
每个字用矩形 \clip 从左到右揭开，像被笔写出来；一个小光点跟着揭开的边缘走。

入场（w 是这个字的宽度，t 是字的上沿，b 是下沿，时长 250 到 400ms）：
```lua
local l = x - w / 2
s = s .. string.format("\\clip(%s,%s,%s,%s)\\t(%d,%d,\\clip(%s,%s,%s,%s))", fn(l), fn(t), fn(l), fn(b), a, a + 320, fn(l), fn(t), fn(l + w + 2), fn(b))
```
逐字间隔 = 上一个字写完的时间，让「笔」连续移动。
光点装饰：`\move(l, 字中线, l + w, 字中线, 0, 320)` 的小 DOT，\blur2，主题色。
注意：\clip 会同时裁掉描边和投影，投影层要用同一个 clip，否则投影先出现。

## E 光带扫过
整行出现后，一道斜的亮光从左扫到右，字被照亮。用于副歌、结尾，或卡在画面变亮的切镜点。

做法：文字层之上再加一层「高光文字」（同样的字，亮色、加 \blur），只在一条移动的竖带里可见：
```lua
-- 高光层（额外的 template char 行，图层高于文字层）
local band = 90
s = string.format("\\an2\\pos(%s,%s)\\1c&HD8F4FF&\\3c&HD8F4FF&\\blur3", fn(x), fn(y))
s = s .. string.format("\\clip(%s,%s,%s,%s)\\t(%d,%d,\\clip(%s,%s,%s,%s))",
  fn(L.x0 - band), fn(L.yt - 10), fn(L.x0), fn(L.yb + 10), ts, ts + 700,
  fn(L.x1), fn(L.yt - 10), fn(L.x1 + band), fn(L.yb + 10))
```
ts 是扫光开始时刻（全行都在的时候）。想要多次扫光就在 setupLine 里算好 L.sw 列表，每次一行（参考 starter 的 finale）。
配一颗星沿行上沿同速移动，效果更明显。

## F 卡片翻转
字绕竖轴翻过来。节奏感强的歌逐字间隔 20ms，整句很快翻完。

入场（\an5 以字中心为轴；用 \an2 时轴在字底）：
```lua
s = string.format("\\an5\\pos(%s,%s)", fn(x), fn(L.ym)) .. string.format("\\fry90\\alpha&HFF&\\t(%d,%d,0.5,\\fry0)\\t(%d,%d,\\alpha&H00&)", a, a + 280, a, a + 60)
```
退场：`\t(o,o+250,\fry-90\alpha&HFF&)`。想要上下翻就用 \frx。
注意 \fry 和 \org 位移法冲突（都依赖 \org），这个配方不和 A 的下落混用。

## G 渐变色字
整句从第一个字到最后一个字颜色渐变（例如粉到橙）。颜色在 Lua 里按 k / L.n 插值：
```lua
function lerpc(c1, c2, t)  -- c 是 {r, g, b}，返回 &HBBGGRR&
  local r = ri(c1[1] + (c2[1] - c1[1]) * t)
  local g = ri(c1[2] + (c2[2] - c1[2]) * t)
  local b = ri(c1[3] + (c2[3] - c1[3]) * t)
  return string.format("&H%02X%02X%02X&", b, g, r)
end
local col = lerpc({255, 140, 170}, {255, 190, 110}, (k - 1) / math.max(1, L.n - 1))
s = s .. "\\1c" .. col
```
描边保持统一的深色，渐变只在填充色上，避免难读。

## H 水墨晕开
字像墨滴在纸上化开：先出现一团虚的墨色，再收拢成清楚的字。

入场（两层：晕染层在下、文字层在上）：
```lua
-- 晕染层：大模糊、半透明，扩大后淡去
"\\1c&H303030&\\3c&H303030&\\bord6\\blur14\\alpha&HFF&\\fscx60\\fscy60"
.. string.format("\\t(%d,%d,\\alpha&H70&\\fscx130\\fscy130)\\t(%d,%d,\\alpha&HFF&)", a, a + 300, a + 300, a + 900)
-- 文字层：稍晚出现
string.format("\\alpha&HFF&\\blur4\\t(%d,%d,\\alpha&H00&\\blur0.6)", a + 150, a + 500)
```
配色用墨黑、朱红、米白。装饰：退场时几点墨滴（DOT，\blur3）向下渗开。

## I 震动故障
字出现时剧烈抖动几下，或者出现红青分离的故障感。只用于激烈的段落，不要整首都用。

抖动（在入场后 200ms 内，用 \t 的瞬时切换改位置；配合 \org 法的话改 \frz，否则改 \fscx 和 \frz 的小角度）：
```lua
local jit = ""
for m = 0, 5 do
  local t = a + m * 35
  jit = jit .. string.format("\\t(%d,%d,\\frz%d)", t, t + 1, (m % 2 == 0) and 3 or -3)
end
s = s .. jit .. string.format("\\t(%d,%d,\\frz0)", a + 210, a + 211)
```
红青分离：额外两行 template char，分别 `\1c&H0000FF&` 和 `\1c&HFFFF00&`，\alpha&H60&，x 偏移 ±3px，只在入场 200ms 内可见（`\t(a+200,a+201,\alpha&HFF&)`）。
更强的故障：加几行 \clip 横条，把一条字横向错开 10 到 20px，持续 1 到 2 帧。

## J 碎裂退场
退场时每个字被切成几条竖条，各自朝不同方向飞散旋转。

在 syl 模板或专门的 template char 行里，用 maxloop(片数) 生成碎片，每片用矩形 \clip 取字的一条：
```lua
-- 第 j 片（共 P.shards 片），字宽 w，字左沿 l
if j == 1 then maxloop(P.shards) end
local sw = w / P.shards
local cl = string.format("\\clip(%s,%s,%s,%s)", fn(l + (j - 1) * sw), fn(L.yt - 20), fn(l + j * sw), fn(L.yb + 20))
retime("preline", o, o + 600)
return "{" .. string.format("\\an2\\move(%s,%s,%s,%s)\\t(0,600,\\frz%d\\alpha&HFF&)", fn(x), fn(y), fn(x + rnd(-40, 40)), fn(y + rnd(20, 70)), math.random(-60, 60)) .. cl .. "}" .. syl.text_stripped
```
注意 \clip 是屏幕坐标，不跟着 \move 走：碎片移出 clip 范围就被裁掉了。所以碎片移动距离要小（40 到 70px），或者改用绘图（glyph2ass 把字转成绘图后按轮廓分片）。
主文字层在 o 时刻瞬间隐藏：`\t(o,o+1,\alpha&HFF&)`。

用 Yutils 可以不受 \clip 限制：`ychar(c).d` 是字的真实轮廓，用 `Y.shape.split` 细分后按区域分组成几块绘图，每块单独 \move 飞走，飞多远都不会被裁。

## K 飘落消散
退场时字像花瓣一样边转边往下飘，左右摆动。

退场（\move 下落 + \fry 翻转 + \frz 摆动）：
```lua
s = s .. string.format("\\t(%d,%d,\\fry%d\\frz%d\\alpha&HFF&)", o, o + 900, math.random(120, 240), math.random(-30, 30))
```
位移用 \move 需要改成独立的退场行；和 A 的 \org 位移共存时，退场改用 \org 竖直位移下落（vt 正数）加 \fry。
装饰：同时飘下几片主题元素（花瓣、雪花、叶子），数量随句长变化。

## L 描边预告（Yutils）
字落下之前，落点先亮起一个空心的字形轮廓，字落进轮廓里时轮廓淡掉，像「这里即将出现一个字」。

starter 的 yGhost()。轮廓来自 `Y.shape.to_outline(Y.shape.flatten(字的轮廓), 线宽)`，前面加包围盒锁定，用 `\an7\pos(字格左, 行顶)` 放：
```lua
local g = ychar(L.ch[k])        -- g.outline 已带包围盒锁定
spec(a - 260, a + P.inDur + 120, "\\an7\\pos(" .. fn(L.cl[k]) .. "," .. fn(L.yt) .. ")\\bord0\\1c" .. C.glow .. "\\alpha&HFF&\\t(0,140,\\alpha&H50&)...")
```
参数：YP.ghostLead（提前量）、YP.ghostBord（线宽，1 到 2 像素最好看，太粗会糊成一块）、YP.ghostAlpha。
变化：轮廓用 \clip 从左到右扫出来；或者轮廓颜色从 C.glow 渐变到字色。

## M 碎成粒子（Yutils）
退场时每个字按真实字形碎成许多小方块，从左到右依次起飞，上飘、旋转、缩小消失。和 J 的差别：J 是几条竖条，M 是几十颗粒子，远看还是那个字的形状。

starter 的 yDust()。粒子位置来自 `Y.shape.to_pixels(字的轮廓)`，按 YP.step 隔点取样，每字最多 YP.max 颗：
- 字本体在 o 时刻 YP.vanish ms 内隐藏（letter() 里看 L.dust[k]）。
- 每颗一行，`\an7\move(字格左+p.x, 行顶+p.y, 终点)`，绘图是边长 YP.size 的小方块。
- 起飞时差 `YP.sweep * p.x / 字宽`，所以是从左往右散开。

**行数会很多**：一句 10 个字 × 60 颗 = 600 行。压制没问题；播放器实时渲染吃力时调大 YP.step 或调小 YP.max。只给主行用，副行保留普通退场。
变化：粒子往下落（rise 取负数）配合 K 的季节感；粒子换成主题小图形（花瓣、星星）；粒子颜色取画面主色。

## N 沿轮廓走光（Yutils）
高潮句，一颗小光点沿着每个字的笔画轮廓跑一圈。

轮廓点取法：`Y.shape.split(Y.shape.flatten(d), 4)` 把轮廓切成每段不超过 4px，再用 `Y.shape.filter(形状, function(x, y) ... end)` 把所有点收集成表，按顺序每隔几个点生成一个短时长的光点行（\an5\pos(点) + \blur2），时间依次后移。
点太多时每隔 N 个取一个。光点配 \1c 暖白、\3c 字色，\bord2\blur3 做辉光。

---

## 组合建议

| 歌曲类型 | 入场 | 退场 | 装饰 |
|---|---|---|---|
| 日常、轻松 | A 或 F | 上浮淡出 | 主题物件弹跳、闪光 |
| 抒情慢歌 | C 或 D | C 反向 | 光斑、飘浮粒子 |
| 回忆、独白 | B | 整行淡出 | 光标、纸张纹理色 |
| 副歌高潮 | A 或 F + E 扫光 | J 或上浮 | 更多、更大的主题物件 |
| 激烈、战斗 | I | J | 火花、碎片 |
| 和风、古风 | H | K | 花瓣、墨点 |
| 离别、结尾 | C | K | 缓慢飘落的主题物件 |

同一首歌里主歌和副歌可以用不同强度：主歌用简单的入场、少量装饰，副歌加扫光、增加装饰数量。
