"""起始模板生成器：把一份双语歌词 .ass 变成可在 Aegisub 里套用的卡拉OK特效模板。

Author: Carinoasd

用法：
  python starter_build.py 歌词.ass 模板.ass --main 主行样式 [--sub 副行样式]
         [--theme berry|flower|heart|star] [--glyph-json 补字.json] [--seed 数字] [--no-finale]
         [--yutils]

生成的模板：
  - 每句歌词改成注释行，特效栏填 karaoke，开头只有一个 {\\k1}（整句当一个音节）。
  - 主行：字从上方依次快速落下，落地压扁回弹，颜色从闪色褪成本色。
  - 副行：在主行第一个字落地的同一刻，从下方依次弹出。
  - 主题元素只在进场、退场出现；进场 4 套、退场 4 套动作，相邻两句不重复同一套。
  - 短句按时长压缩装饰动画；每个样式最后一句标成 finale，有单独的收尾。
  - 参数都在第一行 code once 的 C（颜色）和 P（时间、位置）里。
  - 加 --yutils：模板在运行时 require Yutils（https://github.com/Youka/Yutils），把字转成轮廓，
    多出第 5 套进场「描边预告」和第 5 套退场「碎成粒子」；参数在 YP 表里。
    在 Aegisub 里用时，Aegisub 的 automation/include 要有 Yutils.lua（见 SKILL.md）。

这是起点，不是成品：拿到歌曲后按歌词和画面改主题图形、颜色、节奏（见 SKILL.md）。
然后用 scripts/kt_apply.py 套用、scripts/review.py 检查。
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import shapes  # noqa: E402


def lua(code):
    """模板的 code 行只能写在一行里：去掉空行和整行注释，其余按空格拼起来。
    行内说明只能用 --[[ ]] 块注释，写 -- 会把后面整行都注释掉。"""
    out = []
    for ln in code.strip().splitlines():
        s = ln.strip()
        if s and not s.startswith("--"):
            out.append(s)
    return " ".join(out)


def lua_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


THEMES = {
    # 每层：绘图（已带 BOX）+ 这一层的标签。多层共用同一个 BOX，叠起来对齐。
    "berry": {"size": 0.9, "layers": [
        (shapes.BERRY_BOX + shapes.BERRY["body"], "\\bord1.2\\3c&H3D20B3&\\1c&H553BEE&"),
        (shapes.BERRY_BOX + shapes.BERRY["seed"], "\\bord0\\1c&HC2F2FF&"),
        (shapes.BERRY_BOX + shapes.BERRY["calyx"], "\\bord1\\3c&H3A7D2E&\\1c&H5FB858&")],
        "flash": "&HC7B8FF&", "spark": "&HF2FCFF&", "glow": "&HA8EBFF&"},
    "flower": {"size": 1.6, "layers": [
        (shapes.FLOWER_BOX + shapes.FLOWER, "\\bord0.8\\3c&HE0D9FF&\\1c&HFFFFFF&"),
        (shapes.FLOWER_BOX + shapes.FLOWER_CORE, "\\bord0\\1c&H4AD8FF&")],
        "flash": "&HE6DCFF&", "spark": "&HFFFFFF&", "glow": "&HD8E8FF&"},
    "heart": {"size": 1.4, "layers": [
        (shapes.HEART_BOX + shapes.HEART, "\\bord1\\3c&H5A3ACF&\\1c&H7A5BFF&")],
        "flash": "&HB9A8FF&", "spark": "&HF2F0FF&", "glow": "&HC8C0FF&"},
    "star": {"size": 1.6, "layers": [
        (shapes.STAR_BOX + shapes.STAR, "\\bord0.8\\3c&H3AB0E8&\\1c&H9CE4FF&")],
        "flash": "&H9CE4FF&", "spark": "&HF2FCFF&", "glow": "&H9CE4FF&"},
}

CODE_PARAMS = r"""
MAIN, SUB = %(main)s, %(sub)s
math.randomseed(%(seed)d)
NV = 4 --[[进场、退场各有几套动作可选；--yutils 时是 5]]
C = {
  flash = "%(flash)s", --[[字刚出现时的闪色，之后褪成样式本色]]
  mainShadow = "&H44288E&", subShadow = "&H44288E&", --[[投影颜色（&HBBGGRR&）]]
  spark = "%(spark)s", glow = "%(glow)s", --[[闪光星和 finale 暖光]]
}
P = {
  R = 4000, --[[位移用绕远处 \org 的小角度旋转来做，这是旋转半径，一般不用改]]
  inStag = {18, 32}, inDur = 240, dropH = 16, --[[主行：逐字间隔上下限 ms、单字下落时长、下落高度 px]]
  subRise = 14, subPop = 260, --[[副行：从下方弹起的高度、时长；在主行第一个字落地时开始]]
  outDur = 380, outRise = 18, outStag = {12, 26}, --[[退场：时长、上浮高度、逐字间隔]]
  shadowX = 3, shadowY = 4, solidShadow = true, --[[主行实心投影偏移；false 时用柔和阴影]]
  fxIn = 1100, fxOut = 1000, fxCount = {2, 4}, fxSize = %(size)s, --[[装饰进退场时长上限、每次数量、图形缩放]]
  minLine = 2400, --[[短于这个时长的句子，装饰时长按比例压缩，最少压到 55%%]]
  fxLayer = 30, --[[装饰从这个图层开始往上叠]]
}
"""

CODE_ASSETS = r"""
TH = { %(layers)s }
SPARK = %(star)s DOT = %(dot)s
GS = %(gs)s --[[补字表：字 -> {asc, h, adv, d}，d 是字体单位的轮廓，由 glyph2ass.py --json 生成]]
"""

CODE_HELPERS = r"""
function clamp(x, a, b) if x < a then return a elseif x > b then return b end return x end
function rnd(a, b) return a + (b - a) * math.random() end
function ri(x) return math.floor(x + 0.5) end
function fn(x) return string.format("%.1f", x) end
function f2(x) return string.format("%.2f", x) end
function idx()
  --[[逐字模板里同一模板行的所有字共用一个 syl 对象，换模板行才换对象：据此数出这是第几个字]]
  if syl ~= _lastsyl then _lastsyl = syl; _k = 0 end
  if j == 1 then _k = _k + 1 end
  return _k
end
function vt(v)
  --[[竖直位移 v 像素（负数向上）对应的 \frz 角度。\org 固定在字左侧 R 远处，转一个小角度约等于上下平移，\t 的加速参数就能作用在位移上]]
  return string.format("%.4f", math.deg(math.asin(clamp(-v / P.R, -1, 1))))
end
function pick(n, last)
  --[[从 1..n 里随机选一个，不和上一次相同]]
  if last < 1 then return math.random(1, n) end
  local v = math.random(1, n - 1)
  if v >= last then v = v + 1 end
  return v
end
function glyph(ch)
  local st, g = orgline.styleref, GS[ch]
  local s = st.fontsize / g.h
  local sx, sy = s * st.scale_x / 100, s * st.scale_y / 100
  local out, i = {}, 0
  for tok in g.d:gmatch("%S+") do
    local v = _G.tonumber(tok)
    if v then
      i = i + 1
      if i % 2 == 1 then out[#out + 1] = f2(v * sx) else out[#out + 1] = f2((g.asc - v) * sy) end
    else
      out[#out + 1] = tok
    end
  end
  return string.format("m 0 0 m %s %s ", f2(g.adv * sx), f2(g.h * sy)) .. _G.table.concat(out, " ")
end
"""

CODE_SETUP = r"""
function tin(k)
  if L.main then return ri((k - 1) * L.stag) end
  return ri(P.inDur + (k - 1) * L.stag)
end
function tout(k) return ri(L.dur - L.out - (L.n - k) * L.ostag) end
function spec(t0, t1, tags, sc) L.ev[#L.ev + 1] = { t0 = ri(t0), t1 = ri(t1), tags = tags, sc = sc } end
function setupLine()
  local st = orgline.styleref
  L = { n = 0, dur = orgline.duration, main = (orgline.style == MAIN), finale = (orgline.actor == "finale"),
        dx = {}, cx = {}, cl = {}, ch = {}, cw = {}, blank = {}, ev = {}, dust = {} }
  local acc, pos = 0, 0
  for c in _G.unicode.chars(orgline.text_stripped) do
    L.n = L.n + 1
    L.blank[L.n] = (c == " " or c == "　")
    local w = _G.aegisub.text_extents(st, c)
    local d = 0
    --[[补字的绘图宽度和缺字时量到的宽度不同，记下差值，修正后面每个字的位置]]
    if GS[c] then d = GS[c].adv * st.fontsize / GS[c].h * st.scale_x / 100 - w end
    L.dx[L.n] = acc + d / 2
    L.cl[L.n], L.ch[L.n], L.cw[L.n] = orgline.left + pos, c, w
    L.cx[L.n] = orgline.left + pos + (w + d) / 2
    acc, pos = acc + d, pos + w + d
  end
  if L.n == 0 then L.n = 1; L.dx[1] = 0; L.cx[1] = orgline.left; L.blank[1] = true end
  L.stag = clamp(L.dur * 0.1 / L.n, P.inStag[1], P.inStag[2])
  L.ostag = clamp(L.dur * 0.06 / L.n, P.outStag[1], P.outStag[2])
  L.out = L.finale and P.outDur * 2 or P.outDur
  L.q = clamp(L.dur / P.minLine, 0.55, 1)
  L.x0, L.x1 = orgline.left, orgline.left + orgline.width + acc
  L.yt, L.yb, L.ym = orgline.top, orgline.top + orgline.height, orgline.middle
  L.fs = st.fontsize / 58
  VAR = VAR or {}
  local last = VAR[orgline.style] or { vin = 0, vout = 0 }
  L.vin, L.vout = pick(NV, last.vin), pick(NV, last.vout)
  VAR[orgline.style] = { vin = L.vin, vout = L.vout }
  if L.main then fxIn() end
  if L.finale then fxFinale() else fxOut() end
  if #L.ev == 0 then spec(0, 0, "", 0) end
  --[[展开成「一个装饰的一层 = 一行」的工作表：主题图形每层一行；闪光和自带绘图（e.d）只占一行]]
  L.jobs = {}
  for _, e in _G.ipairs(L.ev) do
    if e.sc == 0 or e.d then L.jobs[#L.jobs + 1] = { e = e, li = 0 }
    else for li = 1, #TH do L.jobs[#L.jobs + 1] = { e = e, li = li } end end
  end
end
"""

CODE_LETTER = r"""
function letter(kind)
  local k = idx()
  if L.blank[k] then retime("preline", 0, 0) return "" end
  local sh = (kind == "shadow")
  local x, y = line.left + syl.center + L.dx[k], L.yb
  if sh then
    if L.main and P.solidShadow then x, y = x + P.shadowX, y + P.shadowY else x, y = x + 2, y + 2 end
  end
  local a, o = tin(k), tout(k)
  local s = string.format("\\an2\\pos(%s,%s)\\org(%s,%s)", fn(x), fn(y), fn(x - P.R), fn(y))
  local sc = L.main and C.mainShadow or C.subShadow
  if sh then
    local soft = not (L.main and P.solidShadow)
    s = s .. "\\1c" .. sc .. "\\3c" .. sc .. (soft and "\\bord4\\blur3" or "\\blur0.8")
  else
    s = s .. "\\1c" .. C.flash .. string.format("\\t(%d,%d,\\1c%s)", a + P.inDur, a + P.inDur + 420, "&H" .. orgline.styleref.color1:sub(5, 10) .. "&")
  end
  local al = (sh and not (L.main and P.solidShadow)) and "&H80&" or "&H00&"
  if L.main then
    local F = a + P.inDur
    s = s .. string.format("\\frz%s\\t(%d,%d,2,\\frz0)", vt(-P.dropH * L.fs), a, F)
    s = s .. string.format("\\alpha&HFF&\\t(%d,%d,\\alpha%s)", a, a + 90, al)
    s = s .. string.format("\\t(%d,%d,\\fscx114\\fscy84)\\t(%d,%d,\\fscx95\\fscy107)\\t(%d,%d,\\fscx100\\fscy100)", F - 10, F + 60, F + 60, F + 160, F + 160, F + 260)
  else
    s = s .. string.format("\\frz%s\\t(%d,%d,0.5,\\frz0)", vt(P.subRise * L.fs), a, a + P.subPop)
    s = s .. string.format("\\alpha&HFF&\\fscx70\\fscy70\\t(%d,%d,\\alpha%s)\\t(%d,%d,\\fscx106\\fscy106)\\t(%d,%d,\\fscx100\\fscy100)", a, a + 150, al, a, a + 170, a + 170, a + 300)
  end
  if L.finale and not sh then
    local t1 = ri(L.dur * 0.55) + (k - 1) * 45
    s = s .. string.format("\\t(%d,%d,\\1c%s\\fscx106\\fscy106)\\t(%d,%d,\\fscx100\\fscy100)", t1, t1 + 260, C.glow, t1 + 260, t1 + 700)
  end
  if L.dust[k] then
    --[[这个字要碎成粒子：本体在粒子出现的同一刻很快消失]]
    s = s .. string.format("\\t(%d,%d,\\alpha&HFF&)", o, o + YP.vanish)
  else
    s = s .. string.format("\\t(%d,%d,0.7,\\frz%s)\\t(%d,%d,\\alpha&HFF&\\blur4)", o, o + L.out, vt(-P.outRise * L.fs), o, o + L.out)
  end
  local ch = syl.text_stripped
  if GS[ch] then return "{" .. s .. "\\p1}" .. glyph(ch) end
  return "{" .. s .. "}" .. ch
end
function extras()
  --[[每个装饰的每一层 = 一行（见 setupLine 的 L.jobs）。第一次进来时决定循环次数]]
  if j == 1 then maxloop(#L.jobs) end
  local jb = L.jobs[j]
  local e, li = jb.e, jb.li
  retime("preline", e.t0, e.t1)
  if e.t1 <= e.t0 then return "" end
  if e.d then
    relayer(P.fxLayer + #TH + 2)
    return "{" .. e.tags .. "\\p1}" .. e.d
  end
  if li == 0 then
    relayer(P.fxLayer + #TH + 1)
    return "{" .. e.tags .. "\\p1}" .. (e.dot and DOT or SPARK)
  end
  relayer(P.fxLayer + li)
  local sc = ri(e.sc * P.fxSize * L.fs)
  return "{" .. string.format("\\fscx%d\\fscy%d", sc, sc) .. e.tags .. TH[li].tags .. "\\p1}" .. TH[li].d
end
"""

CODE_FX = r"""
function sparkAt(t, x, y, n, r)
  --[[小闪光：n 颗向外散开的星点]]
  for m = 1, n do
    local ang = math.rad(m * 360 / n + rnd(-20, 20))
    local r1 = rnd(r * 0.7, r * 1.2) * L.fs
    local ss = math.random(45, 80)
    local e = { t0 = ri(t), t1 = ri(t + 420), sc = 0, dot = (m % 2 == 0) }
    e.tags = string.format("\\an5\\move(%s,%s,%s,%s,0,420)\\fscx%d\\fscy%d\\t(0,420,0.7,\\fscx0\\fscy0\\frz160)\\bord0\\blur0.6\\1c%s", fn(x), fn(y), fn(x + r1 * math.cos(ang)), fn(y + r1 * math.sin(ang)), ss, ss, C.spark)
    L.ev[#L.ev + 1] = e
  end
end
function fxIn()
  local D = ri(P.fxIn * L.q)
  local cnt = math.random(P.fxCount[1], P.fxCount[2])
  local land = P.inDur
  if L.vin == 1 then
    --[[从行两端外侧飞向两端，落定时弹一下后消失]]
    for m = 1, cnt do
      local side = (m % 2 == 1) and -1 or 1
      local ex = side < 0 and L.x0 - 18 * L.fs or L.x1 + 18 * L.fs
      local ey = L.ym + rnd(-10, 10) * L.fs
      local sx = ex + side * rnd(140, 220) * L.fs
      local t0 = -ri(D * 0.35) + (m - 1) * 70
      local t1 = land + (m - 1) * 70
      spec(t0, t1 + 380, string.format("\\an5\\move(%s,%s,%s,%s,0,%d)\\frz%d\\t(0,%d,0.6,\\frz0)\\t(%d,%d,\\fscx0\\fscy0\\alpha&HFF&)", fn(sx), fn(ey - 30), fn(ex), fn(ey), t1 - t0, side * 200, t1 - t0, t1 - t0 + 60, t1 - t0 + 380), math.random(85, 110))
      if m <= 2 then sparkAt(t1, ex, ey, 5, 34) end
    end
  elseif L.vin == 2 then
    --[[从行下方弹起，冲过字顶再回落消失]]
    for m = 1, cnt do
      local k = math.random(1, L.n)
      local x = L.x0 + (L.x1 - L.x0) * (m - 0.5) / cnt + rnd(-20, 20)
      local t0 = tin(k) - 120
      spec(t0, t0 + ri(D * 0.8), string.format("\\an5\\move(%s,%s,%s,%s,0,%d)\\frz%d\\t(0,%d,\\frz%d)\\t(%d,%d,\\fscx0\\fscy0\\alpha&HFF&)", fn(x), fn(L.yb + 50 * L.fs), fn(x + rnd(-24, 24)), fn(L.yt - 26 * L.fs), ri(D * 0.45), math.random(-30, 30), ri(D * 0.8), math.random(-120, 120), ri(D * 0.45), ri(D * 0.8)), math.random(70, 100))
    end
  elseif L.vin == 3 then
    --[[从上方加速落到字上，和主行第一个字同一刻落地，压扁后消失]]
    for m = 1, cnt do
      local k = (m == 1) and 1 or math.random(2, math.max(2, L.n))
      if k > L.n then k = L.n end
      local x = L.cx[k]
      local yl = L.yt - 6 * L.fs
      local h = rnd(90, 150) * L.fs
      local F = tin(k) + land
      local t0 = F - 300
      local fall = string.format("\\an2\\pos(%s,%s)\\org(%s,%s)\\frz%s\\t(0,300,2,\\frz0)", fn(x), fn(yl), fn(x - P.R), fn(yl), vt(-h))
      spec(t0, F + 360, fall .. "\\t(290,360,\\fscx125\\fscy75)\\t(360,660,\\fscx0\\fscy0\\alpha&HFF&)", math.random(80, 105))
      sparkAt(F, x, yl - 6, 4, 26)
    end
  elseif L.vin == 5 then
    yGhost()
  else
    --[[一大一小沿行上沿、下沿交错穿过]]
    local w = L.x1 - L.x0
    spec(-ri(D * 0.2), ri(D * 0.8), string.format("\\an5\\move(%s,%s,%s,%s)\\t(\\frz-240)\\fad(120,200)", fn(L.x0 - 60), fn(L.yt - 8), fn(L.x0 + w + 60), fn(L.yt - 8)), 120)
    spec(-ri(D * 0.1), ri(D * 0.9), string.format("\\an5\\move(%s,%s,%s,%s)\\t(\\frz300)\\fad(120,200)", fn(L.x1 + 60), fn(L.yb + 4), fn(L.x1 - w - 60), fn(L.yb + 4)), 70)
  end
end
function fxOut()
  if not L.main then return end
  local D = ri(P.fxOut * L.q)
  local cnt = math.random(P.fxCount[1], P.fxCount[2])
  local o = tout(1)
  if L.vout == 1 then
    --[[从字上冒出，边转边上浮缩小]]
    for m = 1, cnt do
      local k = math.random(1, L.n)
      local x = L.cx[k]
      local t0 = tout(k) - 40
      spec(t0, t0 + D, string.format("\\an5\\move(%s,%s,%s,%s)\\fscx0\\fscy0\\frz%d\\t(0,160,\\fscx100\\fscy100)\\t(0,%d,\\frz%d)\\t(%d,%d,\\fscx0\\fscy0\\alpha&HFF&)", fn(x), fn(L.ym), fn(x + rnd(-30, 30)), fn(L.yt - rnd(50, 80) * L.fs), math.random(0, 60), D, math.random(-200, 200), ri(D * 0.5), D), math.random(70, 100))
    end
  elseif L.vout == 2 then
    --[[从行中心向外炸开]]
    local cx = (L.x0 + L.x1) / 2
    for m = 1, cnt + 2 do
      local ang = math.rad(m * 360 / (cnt + 2) + rnd(-15, 15))
      local r = rnd(90, 150) * L.fs
      spec(o, o + D, string.format("\\an5\\move(%s,%s,%s,%s,0,%d)\\t(0,%d,0.6,\\fscx0\\fscy0\\frz%d)\\t(%d,%d,\\alpha&HFF&)", fn(cx), fn(L.ym), fn(cx + r * math.cos(ang)), fn(L.ym + r * 0.5 * math.sin(ang)), D, D, math.random(-180, 180), ri(D * 0.6), D), math.random(55, 80))
    end
  elseif L.vout == 3 then
    --[[沿字顶从左扫到右，和逐字退场同步]]
    local dd = (L.n - 1) * L.ostag + L.out
    spec(o - 60, o + dd, string.format("\\an5\\move(%s,%s,%s,%s,0,%d)\\t(0,%d,\\frz360)\\fad(100,160)", fn(L.x0 - 10), fn(L.yt - 4), fn(L.x1 + 10), fn(L.yt - 4), dd, dd), 90)
    for m = 1, 4 do
      local t = o + ri(dd * m / 5)
      sparkAt(t, L.x0 + (L.x1 - L.x0) * m / 5, L.yt - 4, 3, 20)
    end
  elseif L.vout == 5 then
    yDust()
  else
    --[[从字上加速下坠并淡出]]
    for m = 1, cnt do
      local k = math.random(1, L.n)
      local x = L.cx[k]
      local t0 = tout(k)
      spec(t0, t0 + D, string.format("\\an5\\pos(%s,%s)\\org(%s,%s)\\t(0,%d,1.8,\\frz%s)\\t(0,%d,\\alpha&HFF&)", fn(x), fn(L.ym), fn(x - P.R), fn(L.ym), D, vt(rnd(60, 100) * L.fs), D), math.random(70, 95))
    end
  end
end
function fxFinale()
  --[[最后一句：一颗主题图形沿字顶慢慢滑过并留下闪光，退场更慢]]
  if not L.main then return end
  local t0 = ri(L.dur * 0.5)
  local t1 = tout(L.n) + L.out
  spec(t0, t1, string.format("\\an5\\move(%s,%s,%s,%s,0,%d)\\t(0,%d,\\frz-360)\\fad(200,400)", fn(L.x0 - 20), fn(L.yt - 10), fn(L.x1 + 20), fn(L.yt - 10), t1 - t0, t1 - t0), 110)
  for m = 1, 6 do
    local t = t0 + ri((t1 - t0) * m / 7)
    sparkAt(t, L.x0 + (L.x1 - L.x0) * m / 7, L.yt - 10, 4, 24)
  end
end
"""

CODE_YUTILS = r"""
NV = 5
YP = {
  ghostLead = 260, ghostBord = 1.3, ghostAlpha = "&H60&", --[[进场 5「描边预告」：字落下前多少 ms 先出现空心轮廓（不早于句首，免得和上一句重叠）、轮廓线宽 px、轮廓透明度]]
  step = 3, max = 60, minAlpha = 150, --[[退场 5「碎成粒子」：每隔几个像素取一粒、每个字最多几粒、像素覆盖率门槛（0-255）]]
  size = 2.2, life = {420, 820}, rise = {18, 60}, drift = {-20, 46}, --[[粒子边长 px、存活 ms、上飘距离 px、横向漂移 px]]
  sweep = 160, vanish = 70, --[[粒子从字左到字右的起飞时差 ms、字本体消失时长 ms]]
}
YU, YS = nil, {}
function yu()
  --[[载入 Yutils：Aegisub 从 automation/include 找 Yutils.lua]]
  if YU == nil then
    local ok, m = _G.pcall(_G.require, "Yutils")
    if not ok then _G.error("找不到 Yutils：把 Yutils.lua 放进 Aegisub 的 automation/include 目录。" .. _G.tostring(m)) end
    YU = m
  end
  return YU
end
function ychar(c)
  --[[字 c 在本行样式下的轮廓（像素，原点是字格左上角）、空心描边和采样后的粒子点，按样式缓存]]
  local st = orgline.styleref
  local key = st.name .. "|" .. c
  if YS[key] == nil then
    local r = { pts = {} }
    if not GS[c] and c ~= " " and c ~= "　" then
      local Y = yu()
      local function b(v) return v == true or v == 1 or v == -1 end
      local f = Y.decode.create_font(st.fontname, b(st.bold), b(st.italic), false, false, st.fontsize, st.scale_x / 100, st.scale_y / 100, st.spacing)
      local d = f.text_to_shape(c)
      if d and d:find("%d") then
        r.d = d
        --[[开头两个空 move 是包围盒锁定：libass 按包围盒对齐绘图，锁定后 \\an7\\pos 放在字格左上角就和文字重合]]
        local lock = string.format("m 0 0 m %s %s ", f2(_G.aegisub.text_extents(st, c)), f2(st.fontsize * st.scale_y / 100))
        r.outline = lock .. Y.shape.to_outline(Y.shape.flatten(d), YP.ghostBord)
        for _, p in _G.ipairs(Y.shape.to_pixels(d)) do
          if p.alpha >= YP.minAlpha and p.x % YP.step == 0 and p.y % YP.step == 0 then r.pts[#r.pts + 1] = p end
        end
      end
    end
    YS[key] = r
  end
  return YS[key]
end
function yGhost()
  --[[进场 5：每个字落下前，落点先亮起一个空心轮廓，字落地时轮廓淡掉]]
  for k = 1, L.n do
    local g = (not L.blank[k]) and ychar(L.ch[k]) or {}
    if g.outline then
      local a = tin(k)
      local t0, t1 = math.max(0, a - YP.ghostLead), a + P.inDur + 120
      local land = t1 - t0 - 120
      local tags = string.format("\\an7\\pos(%s,%s)\\bord0\\shad1\\4c%s\\blur0.6\\1c%s\\alpha&HFF&\\t(0,140,\\alpha%s)\\t(%d,%d,\\alpha&HFF&)", fn(L.cl[k]), fn(L.yt), C.mainShadow, C.glow, YP.ghostAlpha, land - 40, land + 120)
      L.ev[#L.ev + 1] = { t0 = ri(t0), t1 = ri(t1), tags = tags, sc = 1, d = g.outline }
    end
  end
end
function yDust()
  --[[退场 5：每个字按真实字形碎成小方块，从左到右依次起飞、上飘、缩小消失]]
  if L.finale then return end
  local col = "&H" .. orgline.styleref.color1:sub(5, 10) .. "&"
  local sq = string.format("m 0 0 l %s 0 %s %s 0 %s", f2(YP.size), f2(YP.size), f2(YP.size), f2(YP.size))
  for k = 1, L.n do
    local g = (not L.blank[k]) and ychar(L.ch[k]) or { pts = {} }
    local n = #g.pts
    if n > 0 then
      L.dust[k] = true
      local keep = math.min(1, YP.max / n)
      local o = tout(k)
      for _, p in _G.ipairs(g.pts) do
        if math.random() <= keep then
          local life = ri(math.random(YP.life[1], YP.life[2]) * L.q) --[[短句按比例缩短，少和下一句重叠]]
          local t0 = o + ri(YP.sweep * p.x / math.max(1, L.cw[k]))
          local x0, y0 = L.cl[k] + p.x, L.yt + p.y
          local x1, y1 = x0 + rnd(YP.drift[1], YP.drift[2]) * L.fs, y0 - rnd(YP.rise[1], YP.rise[2]) * L.fs
          local c = (math.random() < 0.3) and C.glow or col
          local tags = string.format("\\an7\\move(%s,%s,%s,%s,0,%d)\\bord0\\shad0.8\\4c%s\\blur0.5\\1c%s\\t(0,%d,1.4,\\fscx0\\fscy0\\frz%d\\alpha&HFF&)", fn(x0), fn(y0), fn(x1), fn(y1), life, C.mainShadow, c, life, math.random(-180, 180))
          L.ev[#L.ev + 1] = { t0 = t0, t1 = t0 + life, tags = tags, sc = 1, d = sq }
        end
      end
    end
  end
end
"""

NOTES = [
    "卡拉OK特效模板（由 starter_build.py 生成）。每句歌词只在开头放一个 {\\k1}，特效栏填 karaoke，然后执行 自动化 > 应用卡拉OK模板。",
    "只能有开头这一个 \\k：模板把整句当作一个音节，再逐字计数；多加 \\k 会打乱逐字序号。没有 \\k 的句子不会生成特效。",
    "参数在第一行 code once：C 是颜色（&HBBGGRR&），P 是时间（ms）和位置（px）。说话人栏填 finale 的句子用单独的收尾动画。",
    "图层：0 投影，1 文字，P.fxLayer 以上是装饰。主题图形在第二行 code once 的 TH 表里，每层一个 {d = 绘图, tags = 标签}。",
    "只保证 libass（mpv、MPC-HC 的 libass 模式、压制用的 ffmpeg）。VSFilter 不认绘图的包围盒锁定写法，多层图形会错位。",
]
NOTE_YUTILS = "本模板用到 Yutils（字转轮廓、描边、转像素）：Aegisub 的 automation/include 目录里要有 Yutils.lua，否则套用时会报「找不到 Yutils」。参数在 YP 表。"



def build(src, dst, main, sub, theme, glyphs, seed, finale, yutils=False):
    th = THEMES[theme]
    raw = open(src, encoding="utf-8-sig").read()
    if "[Events]" not in raw:
        sys.exit("输入文件没有 [Events] 段。")
    head, ev = raw.split("[Events]", 1)
    ev_lines = [l for l in ev.strip().splitlines() if l.strip()]
    fmt = ev_lines[0]
    styles_in_head = set(re.findall(r"^Style:\s*([^,]+),", head, flags=re.M))
    for st in (main, sub):
        if st and st not in styles_in_head:
            sys.exit(f"样式表里没有样式「{st}」。现有样式：{', '.join(sorted(styles_in_head))}")

    layers = ", ".join("{d = %s, tags = %s}" % (lua_str(d), lua_str(t)) for d, t in th["layers"])
    gs = "{" + ", ".join('[%s] = {asc = %s, h = %s, adv = %s, d = %s}' % (
        lua_str(ch), g["asc"], g["h"], g["adv"], lua_str(g["d"])) for ch, g in glyphs.items()) + "}"
    params = CODE_PARAMS % {"main": lua_str(main), "sub": lua_str(sub or ""), "seed": seed,
                            "flash": th["flash"], "spark": th["spark"], "glow": th["glow"], "size": th["size"]}
    assets = CODE_ASSETS % {"layers": layers, "star": lua_str(shapes.STAR_BOX + shapes.STAR),
                            "dot": lua_str(shapes.DOT_BOX + shapes.DOT), "gs": gs}

    def c(layer, style, effect, text):
        return f"Comment: {layer},0:00:00.00,0:00:00.00,{style},,0,0,0,{effect},{text}"

    out = [head.rstrip("\r\n") + "\n", "[Events]", fmt]
    out += [c(0, main, "", n) for n in NOTES + ([NOTE_YUTILS] if yutils else [])]
    out.append(c(0, main, "code once", lua(params)))
    out.append(c(0, main, "code once", lua(assets)))
    out.append(c(0, main, "code once", lua(CODE_HELPERS)))
    out.append(c(0, main, "code once", lua(CODE_SETUP)))
    out.append(c(0, main, "code once", lua(CODE_LETTER)))
    out.append(c(0, main, "code once", lua(CODE_FX)))
    if yutils:
        out.append(c(0, main, "code once", lua(CODE_YUTILS)))
    for st in [s for s in (main, sub) if s]:
        out.append(c(0, st, "code line", "setupLine()"))
        out.append(c(0, st, "template char notext", '!letter("shadow")!'))
        out.append(c(1, st, "template char notext", '!letter("main")!'))
        out.append(c(0, st, "template syl noblank notext", "!extras()!"))

    lyric_idx = {main: [], sub: []}
    rows = []
    for l in ev_lines[1:]:
        m = re.match(r"^(Dialogue|Comment):\s*(.*)$", l)
        if not m:
            rows.append(l)
            continue
        parts = m.group(2).split(",", 9)
        if len(parts) < 10:
            rows.append(l)
            continue
        eff = parts[8].strip()
        if eff.startswith(("template", "code")) or eff == "fx":
            continue  # 旧模板行和旧特效行不带过来
        is_lyric = parts[3] in (main, sub) and (m.group(1) == "Dialogue" or eff == "karaoke")
        if not is_lyric:
            rows.append(l)
            continue
        text = re.sub(r"\\[kK][fo]?\d+(\.\d+)?", "", parts[9])
        text = re.sub(r"\{\}", "", text)
        parts[8] = "karaoke"
        parts[9] = "{\\k1}" + text
        lyric_idx[parts[3]].append(len(rows))
        rows.append(parts)
    if finale:
        for st, ids in lyric_idx.items():
            if ids:
                rows[ids[-1]][4] = "finale"
    for r in rows:
        out.append(r if isinstance(r, str) else "Comment: " + ",".join(r))
    with open(dst, "w", encoding="utf-8-sig", newline="\r\n") as f:
        f.write("\n".join(out) + "\n")
    n = sum(len(v) for v in lyric_idx.values())
    print(f"已写出 {dst}：{n} 句歌词，主题 {theme}，补字 {len(glyphs)} 个" + ("，已启用 Yutils 特效" if yutils else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--main", required=True, help="主行样式名（大字、主角）")
    ap.add_argument("--sub", help="副行样式名（小字、配角），可不填")
    ap.add_argument("--theme", choices=sorted(THEMES), default="flower")
    ap.add_argument("--glyph-json", help="glyph2ass.py --json 生成的补字表")
    ap.add_argument("--seed", type=int, default=20260926)
    ap.add_argument("--no-finale", action="store_true")
    ap.add_argument("--yutils", action="store_true", help="启用 Yutils 特效（描边预告、碎成粒子）")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    glyphs = json.load(open(a.glyph_json, encoding="utf-8")) if a.glyph_json else {}
    build(a.src, a.dst, a.main, a.sub, a.theme, glyphs, a.seed, not a.no_finale, a.yutils)


if __name__ == "__main__":
    main()
