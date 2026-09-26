"""【范例，不是通用工具】《与你相恋到生命尽头》第 12 集插入曲「果酱罐」版特效模板生成器。

整理：Carinoasd。原始代码由 Claude 在一次真实制作中写成，经用户多轮修改后定稿。
设计解说见 references/showcase-jam-jar.md。

依赖这首歌的样式名（12IN日 / 12IN中）、字体（方正达利体简繁 Heavy）和补字轮廓编号，
换一首歌不能直接运行。读它是为了看「华丽」的效果在代码里怎么组织：
全局罐子行、跨句状态 SONG、液面裁切（clip）动画、多层图形包围盒锁定、落地同步、封口卡切镜。

用法（仅限原歌曲）：python build_jam_jar.py 原歌词.ass 输出_template.ass
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import art  # noqa: E402
from glyph_build import build_glyphs  # noqa: E402
from label_text import text_shape  # noqa: E402

JP, CN, JAR = "12IN日v2", "12IN中v2", "12IN罐v2"
FONT = "方正达利体简繁 Heavy"
V2_STYLES = [
    f"Style: {JP},{FONT},40,&H00F0F8FF,&H000000FF,&H006A4ED2,&H0044288E,-1,0,0,0,100,100,0,0,1,2.5,0,7,108,10,16,1",
    f"Style: {CN},{FONT},58,&H00F0F8FF,&H000000FF,&H00A38CFF,&H0044288E,-1,0,0,0,100,100,0,0,1,3.5,0,7,106,10,62,1",
    f"Style: {JAR},{FONT},20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,10,10,10,1",
]


def lua(code):
    out = []
    for ln in code.strip().splitlines():
        s = ln.strip()
        if not s or s.startswith("--"):
            continue
        out.append(s)
    return " ".join(out)


def shift(shape, dx, dy):
    """Translate every coordinate pair of a drawing string."""
    toks, out, i = shape.split(), [], 0
    for t in toks:
        try:
            v = float(t)
        except ValueError:
            out.append(t)
            continue
        out.append(art.f(v + (dx if i % 2 == 0 else dy)))
        i += 1
    return " ".join(out) + " "


cloth = art.gingham_cloth()
rb = art.ribbon()
SHAPES = {
    "box": art.BOX, "body": art.BODY, "inner": art.INNER, "hilite": art.HILITE,
    "chunks": art.CHUNKS, "flecks": art.FLECKS, "label": art.LABEL, "labelIn": art.LABEL_IN,
    "labelText": text_shape("いちご", 36 + art.OX, 65.5 + art.OY, 11.5),
    "rim": art.RIM,
    "sbox": "m 0 0 m 88 46 ", "clothW": cloth["white"], "clothL": cloth["light"], "clothD": cloth["dark"],
    "band": rb["band"], "bow": rb["bow"], "knot": rb["knot"], "shineR": rb["shine"],
    "bbox": art.BERRY_BOX, "bbody": art.BERRY["body"], "bseed": art.BERRY["seed"], "bcalyx": art.BERRY["calyx"],
    "star": art.STAR, "dot": art.DOT,
    "fbox": "m 0 0 m 18 18 ",
    "shine": "m 0 0 l 9 0 l 9 150 l 0 150 ",
}
_petal = "m -1.9 -2.6 b -6.9 -10.3 6.9 -10.3 1.9 -2.6 b 7.6 -9.8 11.9 3.4 3.0 1.0 b 11.6 4.2 0.4 12.4 0.0 3.2 b -0.4 12.4 -11.6 4.2 -3.0 1.0 b -11.9 3.4 -7.6 -9.8 -1.9 -2.6 "
_pistil = "m 0 -2.6 b 1.4 -2.6 2.6 -1.4 2.6 0 b 2.6 1.4 1.4 2.6 0 2.6 b -1.4 2.6 -2.6 1.4 -2.6 0 b -2.6 -1.4 -1.4 -2.6 0 -2.6 "
SHAPES["petal"] = shift(_petal, 9, 9)
SHAPES["pistil"] = shift(_pistil, 9, 9)

CODE_PARAMS = r"""
JP, CN, JAR = "12IN日v2", "12IN中v2", "12IN罐v2"
math.randomseed(20250923)
SONG = {}
C = {
  cnFill = "&HF3F8FF&", cnBord = "&HA38CFF&", cnShadow = "&H44288E&", cnFlash = "&HC7B8FF&", --[[中文大字：奶油色字、粉色描边、深莓色实心投影、弹出时的草莓粉]]
  jpFill = "&HF0F8FF&", jpBord = "&H6A4ED2&", jpShadow = "&H44288E&", jpFlash = "&HC7B8FF&", --[[日文小字：奶油色字、树莓色描边、柔和投影、落地时的草莓粉]]
  berry = "&H553BEE&", berryD = "&H3D20B3&", seed = "&HC2F2FF&", leaf = "&H5FB858&", leafD = "&H3A7D2E&", --[[草莓]]
  glass = "&HFFFBF6&", jam = "&H3F1FD3&", chunk = "&H3015A3&", fleck = "&HB4A0FF&", surf = "&H6A50F0&", --[[玻璃和果酱]]
  label = "&HE6F4FF&", labelLine = "&H6E55E0&", labelIn = "&HB5A5F6&", labelText = "&H4F32D8&", rim = "&HFFFFFF&", rimLine = "&HFFFFFF&",
  gWhite = "&HFFFFFF&", gWhiteLine = "&HE0D0F4&", gLight = "&HB6A2F8&", gDark = "&H5F43E0&", ribbon = "&H482BD6&", ribbonD = "&H331CA8&", knot = "&H3A1FB8&", --[[格子布和蝴蝶结]]
  sugar = "&HF2FCFF&", sun = "&HA8EBFF&", petal = "&HFFFFFF&", petalBord = "&HE0D9FF&", pistil = "&H4AD8FF&",
  warm = "&HF0FAFF&", sunFill = "&H9CE4FF&", glow = "&H8FD8FF&" --[[阳光句]]
}
P = {
  jarX = 8, jarY = 2, jarScale = 1.1, jarLead = 700, jarOut = 600, --[[罐子位置、缩放、在第一句前多少ms出现、最后一句后多少ms开始淡出]]
  fall = 200, fallH = 14, --[[日文字下落时长和高度。第一个日文字在句首开始下落，句首后 fall 毫秒落地，草莓在同一时刻落进果酱]]
  riseH = 14, cnPop = 260, --[[中文字在草莓落地时从下方弹出：弹起高度、时长]]
  jpStag = {20, 34}, cnStag = {16, 26}, --[[逐字间隔上下限，ms]]
  shadowX = 3, shadowY = 4, --[[中文实心投影的偏移]]
  outDur = 360, outRise = 16, outStag = {14, 28}, --[[退场]]
  dropFall = 320, rise = 550, --[[草莓下落时长、果酱上涨时长]]
  sealDelay = 3200, --[[最后一句开始后多少ms封口]]
  sunStart = 1300, sunGap = 2600, sunStag = 55, sunDur = 760
}
"""

CODE_SHAPES = "OX, OY = %d, %d S = {" % (art.OX, art.OY) + ", ".join(f'{k} = "{v}"' for k, v in SHAPES.items()) + "}"

_G = build_glyphs()
CODE_GLYPHS = ('GM = {asc = 942, h = 1171, adv = 1000} --[[本字体的上伸高度、上伸加下伸、字宽，单位为字体单位]] '
               'GS = {' + ", ".join(f'["{ch}"] = "{_G[ch]}"' for ch in ("気", "別")) + '}')

CODE_HELPERS = r"""
function clamp(x, a, b) if x < a then return a elseif x > b then return b end return x end
function rnd(a, b) return a + (b - a) * math.random() end
function ri(x) return math.floor(x + 0.5) end
function fn(x) return string.format("%.1f", x) end
function f2(x) return string.format("%.2f", x) end
function idx()
  if syl ~= _lastsyl then _lastsyl = syl; _k = 0 end
  if j == 1 then _k = _k + 1 end
  return _k
end
function xform(shape, ox, oy, sx, sy)
  local out, i = {}, 0
  for tok in shape:gmatch("%S+") do
    local v = _G.tonumber(tok)
    if v then
      i = i + 1
      if i % 2 == 1 then out[#out + 1] = f2(ox + v * sx) else out[#out + 1] = f2(oy + v * sy) end
    else
      out[#out + 1] = tok
    end
  end
  return _G.table.concat(out, " ")
end
function glyph(ch)
  local st = orgline.styleref
  local s = st.fontsize / GM.h
  local sx, sy = s * st.scale_x / 100, s * st.scale_y / 100
  local out, i = {}, 0
  for tok in GS[ch]:gmatch("%S+") do
    local v = _G.tonumber(tok)
    if v then
      i = i + 1
      if i % 2 == 1 then out[#out + 1] = f2(v * sx) else out[#out + 1] = f2((GM.asc - v) * sy) end
    else
      out[#out + 1] = tok
    end
  end
  return string.format("m 0 0 m %s %s ", f2(GM.adv * sx), f2(GM.h * sy)) .. _G.table.concat(out, " ")
end
function charX(k) return line.left + syl.center + L.dx[k] end
function tin(k) if L.jp then return ri((k - 1) * L.stag) else return ri(P.fall + (k - 1) * L.stag) end end
function tout(k) return ri(L.dur - P.outDur - (L.n - k) * L.ostag) end
function tilt(px) return string.format("%.4f", math.deg(math.asin(px / 4000))) end
function setupLine()
  L = { n = 0, dur = orgline.duration, jp = (orgline.style == JP), sun = (orgline.actor == "sun"), cx = {}, cy = {}, dx = {}, ev = {}, sw = {} }
  L.fs = orgline.styleref.fontsize / 58
  local st, acc = orgline.styleref, 0
  for c in _G.unicode.chars(orgline.text_stripped) do
    if c ~= " " and c ~= "　" then
      L.n = L.n + 1
      local d = 0
      if GS[c] then d = GM.adv * st.fontsize / GM.h * st.scale_x / 100 - _G.aegisub.text_extents(st, c) end
      L.dx[L.n] = acc + d / 2
      acc = acc + d
    end
  end
  if L.n == 0 then L.n = 1; L.dx[1] = 0 end
  local sg = L.jp and P.jpStag or P.cnStag
  L.stag = clamp(L.dur * (L.jp and 0.12 or 0.08) / L.n, sg[1], sg[2])
  L.ostag = clamp(L.dur * 0.06 / L.n, P.outStag[1], P.outStag[2])
  L.x0, L.x1 = orgline.left, orgline.left + orgline.width + acc
  L.yb, L.ym = orgline.top + orgline.height, orgline.middle
  if L.jp then SONG[#SONG + 1] = { s = orgline.start_time, e = orgline.end_time, plop = orgline.start_time + P.fall, sun = L.sun } end
  local g0, g1 = tin(L.n) + P.fall + 500, tout(1) - 700
  if g1 > g0 then
    for m = 1, math.max(1, math.floor(L.n / (L.jp and 8 or 5))) do
      L.ev[#L.ev + 1] = { kind = "glint", k = math.random(1, L.n), t = ri(rnd(g0, g1)), dx = rnd(8, 16) * L.fs, dy = rnd(-26, -16) * L.fs, sc = ri(math.random(100, 140) * L.fs) }
    end
  end
  for k = 1, L.n do
    if math.random() < (L.jp and 0.2 or 0.35) then
      local b = { k = k, t = tout(k) - 40 + math.random(0, 80), dx = rnd(-14, 14) * L.fs, drift = rnd(-16, 16), rise = rnd(34, 52) * L.fs, sc = ri(math.random(80, 120) * L.fs), r0 = math.random(0, 72), r1 = math.random(90, 200) * (math.random() < 0.5 and -1 or 1) }
      L.ev[#L.ev + 1] = { kind = "flower", part = 1, b = b }
      L.ev[#L.ev + 1] = { kind = "flower", part = 2, b = b }
    end
  end
  if L.sun then
    local ts = math.max(P.sunStart, tin(L.n) + 500)
    while ts + (L.n - 1) * P.sunStag + P.sunDur < tout(L.n) - 150 do
      L.sw[#L.sw + 1] = ts
      if not L.jp then L.ev[#L.ev + 1] = { kind = "travel", t = ts } end
      ts = ts + P.sunGap
    end
  end
  if #L.ev == 0 then L.ev[1] = { kind = "none" } end
end
"""

CODE_LETTERS = r"""
function letter(kind)
  local k = idx()
  local sh = (kind == "shadow")
  local x, y = charX(k), L.yb
  if not sh then L.cx[k] = x; L.cy[k] = L.ym end
  if sh then
    if L.jp then x, y = x + 2, y + 2 else x, y = x + P.shadowX, y + P.shadowY end
  end
  local a, o = tin(k), tout(k)
  --[[位移都用绕远处 \org 的微小旋转来做：\t 的加速参数因此能作用在位移上]]
  local s = string.format("\\an2\\pos(%s,%s)\\org(%s,%s)", fn(x), fn(y), fn(x - 4000), fn(y))
  local al, bl
  if L.jp then
    if sh then
      s = s .. "\\bord4.3\\1c" .. C.jpShadow .. "\\3c" .. C.jpShadow
      al, bl = "&H80&", 3
    else
      s = s .. "\\bord2.5\\1c" .. C.jpFlash .. "\\3c" .. C.jpBord .. string.format("\\t(%d,%d,\\1c%s)", a + P.fall, a + P.fall + 420, C.jpFill)
      al, bl = "&H00&", 0.5
    end
    s = s .. string.format("\\frz%s\\t(%d,%d,2,\\frz0)", tilt(P.fallH), a, a + P.fall)
    s = s .. string.format("\\alpha&HFF&\\blur3\\t(%d,%d,\\alpha%s\\blur%s)", a, a + 90, al, bl)
    local F = a + P.fall
    s = s .. string.format("\\t(%d,%d,\\fscx114\\fscy84)\\t(%d,%d,\\fscx95\\fscy107)\\t(%d,%d,\\fscx100\\fscy100)", F - 10, F + 60, F + 60, F + 160, F + 160, F + 260)
  else
    if sh then
      s = s .. "\\bord4\\1c" .. C.cnShadow .. "\\3c" .. C.cnShadow
      al, bl = "&H00&", 0.8
    else
      s = s .. "\\bord3.5\\1c" .. C.cnFlash .. "\\3c" .. C.cnBord .. string.format("\\t(%d,%d,\\1c%s)", a + 80, a + 520, C.cnFill)
      al, bl = "&H00&", 0.6
    end
    s = s .. string.format("\\frz%s\\t(%d,%d,0.5,\\frz0)", tilt(-P.riseH), a, a + P.cnPop)
    s = s .. string.format("\\alpha&HFF&\\blur5\\fscx70\\fscy70\\t(%d,%d,\\alpha%s\\blur%s)\\t(%d,%d,\\fscx106\\fscy106)\\t(%d,%d,\\fscx100\\fscy100)", a, a + 150, al, bl, a, a + 170, a + 170, a + 300)
  end
  for _, ts in _G.ipairs(L.sw) do
    local t1 = ts + (k - 1) * P.sunStag
    local t2, t3 = t1 + ri(P.sunDur * 0.35), t1 + P.sunDur
    if sh then
      s = s .. string.format("\\t(%d,%d,\\fscx106\\fscy106)\\t(%d,%d,\\fscx100\\fscy100)", t1, t2, t2, t3)
    else
      s = s .. string.format("\\t(%d,%d,\\1c%s\\fscx106\\fscy106)\\t(%d,%d,\\1c%s\\fscx100\\fscy100)", t1, t2, C.sunFill, t2, t3, C.warm)
    end
  end
  s = s .. string.format("\\t(%d,%d,0.7,\\frz%s)\\t(%d,%d,\\alpha&HFF&\\blur%s)", o, o + P.outDur, tilt(P.outRise * L.fs), o, o + P.outDur, sh and 6 or 4)
  local ch = syl.text_stripped
  if GS[ch] then return "{" .. s .. "\\p1}" .. glyph(ch) end
  return "{" .. s .. "}" .. ch
end
function extras()
  if j == 1 then maxloop(#L.ev) end
  local e = L.ev[j]
  if e.kind == "none" then retime("preline", 0, 0) return "" end
  if e.kind == "travel" then
    local ta = ri(P.sunDur * 0.35)
    local tb = (L.n - 1) * P.sunStag + ta
    retime("preline", e.t, e.t + tb + 260)
    local ya = L.ym - 26
    return string.format("{\\an5\\move(%s,%s,%s,%s,%d,%d)\\fscx0\\fscy0\\t(%d,%d,\\fscx150\\fscy150)\\t(%d,%d,\\fscx0\\fscy0)\\t(0,%d,\\frz240)\\bord2\\3c%s\\3a&H90&\\blur1.5\\1c%s\\p1}%s", fn(L.cx[1] + 12), fn(ya), fn(L.cx[L.n] + 12), fn(ya), ta, tb, ta - 200, ta, tb, tb + 260, tb + 260, C.sun, C.sugar, S.star)
  end
  if e.kind == "flower" then
    local b = e.b
    local x, y = L.cx[b.k], L.cy[b.k]
    local life = 900
    retime("preline", b.t, b.t + life)
    local s = string.format("{\\an5\\move(%s,%s,%s,%s,0,%d)\\frz%d\\t(0,%d,\\frz%d)\\fscx%d\\fscy%d\\t(0,120,\\fscx%d\\fscy%d)\\t(%d,%d,\\fscx0\\fscy0\\alpha&HFF&)\\blur0.6", fn(x + b.dx), fn(y - 8), fn(x + b.dx + b.drift), fn(y - 8 - b.rise), life, b.r0, life, b.r0 + b.r1, ri(b.sc * 0.4), ri(b.sc * 0.4), b.sc, b.sc, ri(life * 0.45), life)
    if e.part == 1 then return s .. "\\bord0.8\\3c" .. C.petalBord .. "\\1c" .. C.petal .. "\\p1}" .. S.fbox .. S.petal end
    relayer(28)
    return s .. "\\bord0\\1c" .. C.pistil .. "\\p1}" .. S.fbox .. S.pistil
  end
  local x, y = L.cx[e.k], L.cy[e.k]
  retime("preline", e.t, e.t + 600)
  return string.format("{\\an5\\pos(%s,%s)\\fscx0\\fscy0\\t(0,220,\\fscx%d\\fscy%d)\\t(220,600,1.4,\\fscx0\\fscy0)\\t(0,600,\\frz90)\\bord1.5\\3c%s\\3a&HB0&\\blur1.2\\1c%s\\p1}%s", fn(x + e.dx), fn(y + e.dy), e.sc, e.sc, C.sun, C.sugar, S.star)
end
"""

CODE_JAR = r"""
function buildJar()
  J = { ev = {} }
  local ev = J.ev
  local N = #SONG
  if N == 0 then ev[1] = { layer = 0, t0 = 0, t1 = 0, text = "" } return end
  local sc = P.jarScale
  local S100 = sc * 100
  local jx, jy = P.jarX, P.jarY
  local ax, ay = jx + 44 * sc, jy + 110 * sc
  local T0 = SONG[1].s - P.jarLead
  local T1 = SONG[N].e + P.jarOut
  local T2 = T1 + 500
  local function sy(l) return jy + (l + OY) * sc end
  local function sx(l) return jx + (l + OX) * sc end
  local EMPTY, FULL = 88.8, 18.5
  local lv = {}
  for i = 0, N do lv[i] = EMPTY - (EMPTY - FULL) * i / N end
  local function add(layer, t0, t1, text) ev[#ev + 1] = { layer = layer, t0 = ri(t0), t1 = ri(t1), text = text } end
  local pop = string.format("\\fscx0\\fscy0\\t(0,220,0.6,\\fscx%s\\fscy%s)\\t(220,340,\\fscx%s\\fscy%s)\\t(340,440,\\fscx%s\\fscy%s)", f2(S100 * 1.08), f2(S100 * 1.08), f2(S100 * 0.97), f2(S100 * 1.03), f2(S100), f2(S100))
  local fade = string.format("\\t(%d,%d,\\alpha&HFF&)", T1 - T0, T2 - T0)
  local plop = {}
  for i = 1, N do plop[i] = SONG[i].plop end
  for i = 1, N do
    local p = plop[i] - T0
    pop = pop .. string.format("\\t(%d,%d,\\fscx%s\\fscy%s)\\t(%d,%d,\\fscx%s\\fscy%s)\\t(%d,%d,\\fscx%s\\fscy%s)", p, p + 90, f2(S100 * 1.035), f2(S100 * 0.965), p + 90, p + 220, f2(S100 * 0.99), f2(S100 * 1.012), p + 220, p + 330, f2(S100), f2(S100))
  end
  local base = string.format("\\an2\\pos(%s,%s)", f2(ax), f2(ay)) .. pop
  local function part(layer, tags, shape, clip)
    add(layer, T0, T2, "{" .. base .. tags .. (clip or "") .. fade .. "\\p1}" .. S.box .. shape)
  end
  local function levelClip(band)
    local top = sy(lv[0])
    local c = string.format("\\clip(0,%s,1920,%s)", f2(top), f2(band and top + band * sc or 1080))
    for i = 1, N do
      local p = plop[i] - T0
      local t = sy(lv[i])
      c = c .. string.format("\\t(%d,%d,0.6,\\clip(0,%s,1920,%s))", p, p + P.rise, f2(t), f2(band and t + band * sc or 1080))
    end
    return c
  end
  add(1, T0, T2, "{" .. string.format("\\an2\\pos(%s,%s)", f2(ax + 2 * sc), f2(ay + 3 * sc)) .. pop .. "\\bord0\\blur4\\1c&H3A2270&\\alpha&H88&" .. fade .. "\\p1}" .. S.box .. S.body)
  part(2, "\\bord0\\blur0.6\\1c" .. C.glass .. "\\alpha&HB0&", S.body)
  part(6, "\\bord0\\blur0.5\\1c" .. C.jam, S.inner, levelClip())
  part(7, "\\bord0\\blur0.8\\1c" .. C.chunk, S.chunks, levelClip())
  part(8, "\\bord0\\blur0.5\\1c" .. C.fleck .. "\\alpha&H40&", S.flecks, levelClip())
  part(9, "\\bord0\\blur0.6\\1c" .. C.surf, S.inner, levelClip(2.4))
  part(10, "\\bord1.6\\blur0.6\\1a&HFF&\\3c&HFFFFFF&\\3a&H50&", S.body)
  part(11, "\\bord0\\blur0.8\\1c&HFFFFFF&\\alpha&H70&", S.hilite)
  part(13, "\\bord1\\blur0.5\\1c" .. C.label .. "\\3c" .. C.labelLine, S.label)
  part(14, "\\bord0.8\\blur0.4\\1a&HFF&\\3c" .. C.labelIn, S.labelIn)
  part(15, "\\bord0\\blur0.4\\1c" .. C.labelText, S.labelText)
  part(16, "\\bord1.2\\blur0.5\\1c" .. C.rim .. "\\1a&HA8&\\3c" .. C.rimLine .. "\\3a&H38&", S.rim)
  local bottom = sy(EMPTY)
  for i = 1, N do
    local p = plop[i]
    local F = P.dropFall
    local d0 = p - F
    local surfY = sy(lv[i - 1])
    --[[草莓锚点在 p 时刻到达 yI（底部刚碰到液面），之后减速沉到 yS 并淡出]]
    local yI = math.min(surfY - 13, bottom - 16)
    local yS = math.min(surfY + 4, bottom - 16)
    local x = ax + rnd(-3, 3)
    local side = (i % 2 == 1) and 1 or -1
    local R = 700
    local th0 = side * math.deg(math.asin((yS + 34) / R))
    local thI = side * math.deg(math.asin((yS - yI) / R))
    local bs = 50 * sc
    local life = F + 170
    local tags = string.format("\\an5\\pos(%s,%s)\\org(%s,%s)\\frz%s\\t(0,%d,2,\\frz%s)\\t(%d,%d,0.5,\\frz0)", f2(x), f2(yS), f2(x - side * R), f2(yS), f2(th0), F, f2(thI), F, F + 160)
    tags = tags .. string.format("\\fscx%s\\fscy%s\\t(0,%d,2,\\fscx%s\\fscy%s)\\t(%d,%d,\\fscx%s\\fscy%s)\\t(%d,%d,\\fscx%s\\fscy%s)\\t(%d,%d,\\alpha&HFF&)\\blur0.5", f2(bs), f2(bs), F, f2(bs * 0.88), f2(bs * 1.14), F, F + 70, f2(bs * 1.12), f2(bs * 0.9), F + 70, F + 160, f2(bs), f2(bs), F + 40, life)
    add(3, d0, d0 + life, "{" .. tags .. "\\bord1.2\\3c" .. C.berryD .. "\\1c" .. C.berry .. "\\p1}" .. S.bbox .. S.bbody)
    add(4, d0, d0 + life, "{" .. tags .. "\\bord0\\1c" .. C.seed .. "\\p1}" .. S.bbox .. S.bseed)
    add(5, d0, d0 + life, "{" .. tags .. "\\bord1\\3c" .. C.leafD .. "\\1c" .. C.leaf .. "\\p1}" .. S.bbox .. S.bcalyx)
    for m = 1, 4 do
      local dx = rnd(-18, 18)
      local up = rnd(10, 22) * sc
      local dsc = math.random(70, 100)
      add(9, p, p + 380, string.format("{\\an5\\move(%s,%s,%s,%s,0,380)\\fscx%d\\fscy%d\\t(0,380,1.3,\\fscx0\\fscy0)\\bord0\\blur0.4\\1c%s\\p1}%s", f2(x + dx * 0.25), f2(surfY), f2(x + dx), f2(surfY - up), dsc, dsc, C.surf, S.dot))
    end
    add(24, p + 420, p + 880, string.format("{\\an5\\pos(%s,%s)\\fscx0\\fscy0\\t(0,160,\\fscx90\\fscy90)\\t(160,460,1.4,\\fscx0\\fscy0)\\t(0,460,\\frz90)\\bord1\\3c%s\\3a&HB0&\\blur0.8\\1c%s\\p1}%s", f2(sx(62)), f2(sy(22)), C.sun, C.sugar, S.star))
  end
  local innerClip = xform(S.inner, jx, jy, sc, sc)
  local bt = plop[1] + 1500
  while bt < T1 - 800 do
    local cur = lv[0]
    for i = 1, N do if plop[i] + P.rise <= bt then cur = lv[i] end end
    if cur < 72 then
      local bx = sx(rnd(14, 58))
      local y0, y1 = sy(86), sy(cur + 3)
      local life = ri((y0 - y1) * 24)
      local bsz = math.random(45, 70)
      add(8, bt, bt + life, string.format("{\\an5\\move(%s,%s,%s,%s)\\fscx%d\\fscy%d\\bord0\\blur0.5\\1c%s\\alpha&H50&\\t(%d,%d,\\alpha&HFF&)\\clip(%s)\\p1}%s", f2(bx), f2(y0), f2(bx + rnd(-3, 3)), f2(y1), bsz, bsz, C.fleck, life - 150, life, innerClip, S.dot))
    end
    bt = bt + math.random(900, 2200)
  end
  local bodyClip = xform(S.body, jx, jy, sc, sc)
  local st = T0 + 1800
  while st < T1 - 1200 do
    add(12, st, st + 900, string.format("{\\an5\\move(%s,%s,%s,%s)\\bord0\\blur2\\1c&HFFFFFF&\\alpha&H78&\\frz-20\\clip(%s)\\p1}%s", f2(sx(-6)), f2(sy(50)), f2(sx(80)), f2(sy(50)), bodyClip, S.shine))
    st = st + math.random(5500, 7500)
  end
  local Ts = SONG[N].s + P.sealDelay
  if Ts > SONG[N].e - 400 then Ts = math.max(SONG[N].s + 600, SONG[N].e - 1500) end
  local sx2, sy2 = jx + 44 * sc, jy + 46 * sc
  local drop = string.format("\\an2\\move(%s,%s,%s,%s,0,260)\\fscx%s\\fscy%s\\t(240,320,\\fscx%s\\fscy%s)\\t(320,440,\\fscx%s\\fscy%s)\\t(440,560,\\fscx%s\\fscy%s)", f2(sx2), f2(sy2 - 70), f2(sx2), f2(sy2), f2(S100), f2(S100), f2(S100 * 1.12), f2(S100 * 0.86), f2(S100 * 0.96), f2(S100 * 1.05), f2(S100), f2(S100))
  local sfade = string.format("\\t(%d,%d,\\alpha&HFF&)", T1 - Ts, T2 - Ts)
  local function spart(layer, tags, shape) add(layer, Ts, T2, "{" .. drop .. tags .. sfade .. "\\p1}" .. S.sbox .. shape) end
  spart(17, "\\bord0.8\\blur0.5\\1c" .. C.gWhite .. "\\3c" .. C.gWhiteLine, S.clothW)
  spart(18, "\\bord0\\blur0.5\\1c" .. C.gLight, S.clothL)
  spart(19, "\\bord0\\blur0.5\\1c" .. C.gDark, S.clothD)
  spart(20, "\\bord0\\blur0.5\\1c" .. C.ribbon, S.band)
  spart(21, "\\bord0.8\\blur0.5\\1c" .. C.ribbon .. "\\3c" .. C.ribbonD, S.bow)
  spart(22, "\\bord0\\blur0.5\\1c" .. C.knot, S.knot)
  spart(23, "\\bord0\\blur0.6\\1c&HFFFFFF&\\alpha&H80&", S.shineR)
  local cxj, cyj = sx(36), sy(40)
  for m = 1, 9 do
    local ang = math.rad(m * 40 + rnd(-12, 12))
    local r0, r1 = 20 * sc, rnd(48, 72) * sc
    local ss = math.random(70, 120)
    add(24, Ts + 240, Ts + 900, string.format("{\\an5\\move(%s,%s,%s,%s,0,660)\\fscx%d\\fscy%d\\t(0,660,0.7,\\fscx0\\fscy0\\frz180)\\bord1\\3c%s\\3a&HA0&\\blur0.8\\1c%s\\p1}%s", f2(cxj + r0 * math.cos(ang)), f2(cyj + r0 * math.sin(ang)), f2(cxj + r1 * math.cos(ang)), f2(cyj + r1 * math.sin(ang)), ss, ss, C.sun, C.sugar, S.star))
  end
  add(0, Ts + 200, T2, string.format("{\\an5\\pos(%s,%s)\\fscx1500\\fscy1500\\bord0\\blur14\\1c%s\\alpha&HFF&\\t(0,500,\\alpha&H70&)\\t(500,1600,\\alpha&HA8&)\\t(%d,%d,\\alpha&HFF&)\\p1}%s", f2(cxj), f2(cyj), C.glow, T1 - Ts - 200, T2 - Ts - 200, S.dot))
end
function jarAll()
  if j == 1 then buildJar(); maxloop(#J.ev) end
  local e = J.ev[j]
  relayer(e.layer)
  retime("set", e.t0, e.t1)
  return e.text
end
"""

NOTES = [
    "草莓果酱卡拉OK模板 v2。每句歌词开头只放一个 {\\k1}，特效栏填 karaoke，然后执行 自动化 > 应用卡拉OK模板。",
    "每句只能有开头这一个 \\k。模板把整句当作一个音节来算逐字序号，多加 \\k 会打乱序号。",
    "最后一行是罐子行（样式 12IN罐v2），必须放在所有歌词之后。罐子读取前面每句日文的时间：每句的草莓和第一个日文字在句首后 P.fall 毫秒同时落地，"
    "中文在同一时刻弹出，果酱随之涨高；最后一句开始后 P.sealDelay 毫秒盖上格子布。罐子行自己的时间不影响效果。",
    "说话人栏填 sun 的句子会加金色光波，目前用在最后一句。P.sealDelay 设为 3200，对应最后一句开始后切到果酱罐镜头的时刻。",
    "参数在下面第一行 code once，C 是颜色（格式 &HBBGGRR&），P 是时间和位置（单位 ms 和 px）。",
    "图层 0 是封口时的暖光，1 到 24 是罐子（2 玻璃，3 到 5 落下的草莓，6 到 9 果酱，16 罐口，17 到 23 格子布和蝴蝶结），25 是文字投影，26 是文字，27 和 28 是闪光与草莓花。",
    "字体缺 気 和 別。补字那一行 code once 存了用本字体轮廓拼成的字形，模板会自动替换，并修正其后文字的位置。",
]


def build(src_path, dst):
    src = open(src_path, encoding="utf-8-sig").read()
    head, ev = src.split("[Events]")
    head = head.rstrip("\r\n")
    # append the v2 styles right after the existing ones
    lines = head.splitlines()
    last_style = max(i for i, l in enumerate(lines) if l.startswith("Style:"))
    lines[last_style + 1:last_style + 1] = V2_STYLES
    head = "\n".join(lines)
    ev_lines = ev.strip().splitlines()
    fmt = ev_lines[0]

    def c(layer, style, effect, text):
        return f"Comment: {layer},0:00:00.00,0:00:00.00,{style},,0,0,0,{effect},{text}"

    out = [head + "\n", "[Events]", fmt]
    for n in NOTES:
        out.append(c(0, JP, "", n))
    out.append(c(0, JP, "code once", lua(CODE_PARAMS)))
    out.append(c(0, JP, "code once", CODE_SHAPES))
    out.append(c(0, JP, "code once", CODE_GLYPHS))
    out.append(c(0, JP, "code once", lua(CODE_HELPERS)))
    out.append(c(0, JP, "code once", lua(CODE_LETTERS)))
    out.append(c(0, JP, "code once", lua(CODE_JAR)))
    for st in (JP, CN):
        out.append(c(0, st, "code line", "setupLine()"))
        out.append(c(25, st, "template char noblank notext", '!letter("shadow")!'))
        out.append(c(26, st, "template char noblank notext", '!letter("main")!'))
        out.append(c(27, st, "template syl noblank notext", "!extras()!"))
    out.append(c(0, JAR, "template syl noblank notext", "!jarAll()!"))
    lyric = [l for l in ev_lines[1:] if l.startswith("Dialogue:")]
    last_end = None
    for n, l in enumerate(lyric):
        parts = l.split(",", 9)
        text = parts[9]
        if parts[3] == "12IN日":
            parts[3] = JP
            text = text.replace("特别", "特別")
        elif parts[3] == "12IN中":
            parts[3] = CN
        parts[0] = "Comment: " + parts[0].split(":", 1)[1].strip()
        if n >= len(lyric) - 2:
            parts[4] = "sun"
        parts[8] = "karaoke"
        parts[9] = "{\\k1}" + text
        last_end = parts[2]
        out.append(",".join(parts))
    # the jar line: after every lyric line (also after sorting by start time)
    h, m, s = last_end.split(":")
    t = int(h) * 3600 + int(m) * 60 + float(s) + 1.0
    jar_end = f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"
    out.append(f"Comment: 0,{last_end},{jar_end},{JAR},,0,0,0,karaoke,{{\\k1}}罐")
    with open(dst, "w", encoding="utf-8-sig", newline="\r\n") as f:
        f.write("\n".join(out) + "\n")
    print("wrote", dst)


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
