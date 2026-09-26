-- Author: Carinoasd
-- Minimal Aegisub automation environment for running the real kara-templater.lua
-- outside Aegisub. Python fills in: INCLUDE_DIR, PY_TEXT_EXTENTS, PY_READ_FILE, PY_LOG,
-- PY_FILE_EXISTS, YUTILS_DIRS, PY_TEXT_TO_SHAPE (nil on Windows).

aegisub = aegisub or {}
aegisub.debug = {
  out = function(level, fmt, ...)
    if type(level) ~= "number" then
      PY_LOG(0, string.format(level, fmt, ...))
      return
    end
    if level <= 3 then
      local ok, s = pcall(string.format, fmt, ...)
      PY_LOG(level, ok and s or tostring(fmt))
    end
  end
}
aegisub.progress = {
  set = function() end,
  task = function() end,
  title = function() end,
  is_cancelled = function() return false end,
}
aegisub.cancel = function() error("aegisub.cancel() called", 2) end
aegisub.gettext = function(s) return s end
aegisub.video_size = function() return 1920, 1080 end
aegisub.set_undo_point = function() end
aegisub.macros = {}
aegisub.filters = {}
aegisub.register_macro = function(name, desc, fn, validate)
  aegisub.macros[name] = fn
end
aegisub.register_filter = function(name, desc, prio, fn)
  aegisub.filters[name] = fn
end
aegisub.text_extents = function(style, text)
  return PY_TEXT_EXTENTS(style.fontname, style.fontsize, style.bold, style.italic,
    style.underline, style.strikeout, style.scale_x, style.scale_y, style.spacing,
    style.encoding, text)
end

-- port of aegisub/util.moon (only the parts the templater and templates can reach)
local util = {}
function util.copy(tbl)
  local r = {}
  for k, v in pairs(tbl) do r[k] = v end
  return r
end
function util.deep_copy(tbl)
  local seen = {}
  local function copy(val)
    if type(val) ~= "table" then return val end
    if seen[val] then return seen[val] end
    local result = {}
    seen[val] = result
    for k, v in pairs(val) do result[k] = copy(v) end
    return result
  end
  return copy(tbl)
end
function util.ass_color(r, g, b) return string.format("&H%02X%02X%02X&", b, g, r) end
function util.ass_alpha(a) return string.format("&H%02X&", a) end
function util.ass_style_color(r, g, b, a) return string.format("&H%02X%02X%02X%02X", a, b, g, r) end
function util.extract_color(s)
  local a, b, g, r = s:match('&H(%x%x)(%x%x)(%x%x)(%x%x)')
  if a then return tonumber(r, 16), tonumber(g, 16), tonumber(b, 16), tonumber(a, 16) end
  b, g, r = s:match('&H(%x%x)(%x%x)(%x%x)&')
  if b then return tonumber(r, 16), tonumber(g, 16), tonumber(b, 16), 0 end
  a = s:match('&H(%x%x)&')
  if a then return 0, 0, 0, tonumber(a, 16) end
  r, g, b, a = s:match('#(%x%x)(%x?%x?)(%x?%x?)(%x?%x?)')
  if r then return tonumber(r, 16), tonumber(g, 16) or 0, tonumber(b, 16) or 0, tonumber(a, 16) or 0 end
end
function util.alpha_from_style(scolor) return util.ass_alpha(select(4, util.extract_color(scolor))) end
function util.color_from_style(scolor)
  local r, g, b = util.extract_color(scolor)
  return util.ass_color(r or 0, g or 0, b or 0)
end
function util.clamp(val, min, max)
  if val < min then return min elseif val > max then return max else return val end
end
function util.interpolate(pct, min, max)
  if pct <= 0 then return min elseif pct >= 1 then return max else return pct * (max - min) + min end
end
function util.interpolate_color(pct, first, last)
  local r1, g1, b1 = util.extract_color(first)
  local r2, g2, b2 = util.extract_color(last)
  return util.ass_color(util.interpolate(pct, r1, r2), util.interpolate(pct, g1, g2), util.interpolate(pct, b1, b2))
end
function util.interpolate_alpha(pct, first, last)
  return util.ass_alpha(util.interpolate(pct, select(4, util.extract_color(first)), select(4, util.extract_color(last))))
end
function util.HSV_to_RGB(H, S, V)
  local r, g, b = 0, 0, 0
  if S == 0 then
    r = util.clamp(V*255, 0, 255); g = r; b = r
  else
    H = math.abs(H) % 360
    local Hi = math.floor(H/60)
    local f = H/60.0 - Hi
    local p = V*(1-S)
    local q = V*(1-f*S)
    local t = V*(1-(1-f)*S)
    if Hi == 0 then r, g, b = V*255, t*255, p*255
    elseif Hi == 1 then r, g, b = q*255, V*255, p*255
    elseif Hi == 2 then r, g, b = p*255, V*255, t*255
    elseif Hi == 3 then r, g, b = p*255, q*255, V*255
    elseif Hi == 4 then r, g, b = t*255, p*255, V*255
    else r, g, b = V*255, p*255, q*255 end
  end
  return r, g, b
end
function util.trim(s) return (s:gsub('^%s*(.-)%s*$', '%1')) end
function util.headtail(s)
  local a, b, head, tail = s:find('(.-)%s+(.*)')
  if a then return head, tail else return s, '' end
end
function util.words(s)
  return function()
    if s == '' then return end
    local head, tail = util.headtail(s)
    s = tail
    return head
  end
end
package.preload['aegisub.util'] = function() return util end

-- port of aegisub/unicode.moon
local unicode = {}
function unicode.charwidth(s, i)
  local b = s:byte(i or 1)
  if not b then return 1
  elseif b < 128 then return 1
  elseif b < 224 then return 2
  elseif b < 240 then return 3
  else return 4 end
end
function unicode.chars(s)
  local curchar, i = 0, 1
  return function()
    if i > s:len() then return end
    local j = i
    curchar = curchar + 1
    i = i + unicode.charwidth(s, i)
    return s:sub(j, i - 1), curchar
  end
end
function unicode.len(s)
  local n = 0
  for c in unicode.chars(s) do n = n + 1 end
  return n
end
function unicode.codepoint(s)
  local b = s:byte(1)
  if b < 128 then return b end
  local res, w
  if b < 224 then res = b - 192; w = 2
  elseif b < 240 then res = b - 224; w = 3
  else res = b - 240; w = 4 end
  for i = 2, w do res = res*64 + s:byte(i) - 128 end
  return res
end
package.preload['aegisub.unicode'] = function() return unicode end

-- port of AssKaraoke + LuaParseKaraokeData (auto4_lua.cpp)
aegisub.parse_karaoke_data = function(line)
  local text = line.text
  local syls = {}
  local syl = { start_time = line.start_time, duration = 0, tag = "\\k", text = "", stripped = "" }
  local pos = 1
  while pos <= #text do
    local s, e = text:find("%b{}", pos)
    local plain = s and text:sub(pos, s - 1) or text:sub(pos)
    if plain ~= "" then
      syl.text = syl.text .. plain
      syl.stripped = syl.stripped .. plain
    end
    if not s then break end
    local block = text:sub(s + 1, e - 1)
    if not block:find("\\") then
      syl.text = syl.text .. "{" .. block .. "}"
    else
      local in_tag = false
      for tag in block:gmatch("\\[^\\]*") do
        local kname, kval = tag:match("^\\(k[fo]?)(%d+%.?%d*)")
        if not kname then
          kval = tag:match("^\\K(%d+%.?%d*)")
          if kval then kname = "kf" end
        end
        if kname then
          if in_tag then syl.text = syl.text .. "}"; in_tag = false end
          if syl.duration > 0 or syl.stripped ~= "" then
            table.insert(syls, syl)
            syl = { start_time = syl.start_time, duration = syl.duration, tag = syl.tag, text = "", stripped = "" }
          end
          syl.tag = "\\" .. kname
          syl.start_time = syl.start_time + syl.duration
          syl.duration = math.floor(tonumber(kval) or 0) * 10
        else
          if not in_tag then syl.text = syl.text .. "{"; in_tag = true end
          syl.text = syl.text .. tag
        end
      end
      if in_tag then syl.text = syl.text .. "}" end
    end
    pos = e + 1
  end
  table.insert(syls, syl)

  local res = {}
  res[0] = { duration = 0, start_time = 0, end_time = 0, tag = "", text = "", text_stripped = "" }
  for i, sy in ipairs(syls) do
    res[i] = {
      duration = sy.duration,
      start_time = sy.start_time - line.start_time,
      end_time = sy.start_time + sy.duration - line.start_time,
      tag = sy.tag,
      text = sy.text,
      text_stripped = sy.stripped,
    }
  end
  return res
end

-- include(): run a file from the automation include dir in the global env
function include(name)
  local src = PY_READ_FILE(INCLUDE_DIR .. "/" .. name)
  local f, err = loadstring(src, "@" .. name)
  if not f then error(err) end
  return f()
end

-- require("Yutils"): search Aegisub's include dirs, then the copy bundled with the skill.
-- Off Windows, Yutils needs pangocairo for fonts; replace create_font with a Python
-- version (same coordinates as Yutils on Windows) so text_to_shape works in WSL too.
package.preload["Yutils"] = function()
  local path
  for _, d in ipairs(YUTILS_DIRS or {}) do
    if PY_FILE_EXISTS(d .. "/Yutils.lua") then path = d .. "/Yutils.lua" break end
  end
  if not path then error("Yutils.lua not found in Aegisub include dirs or the skill's scripts/") end
  local f, err = loadstring(PY_READ_FILE(path), "@Yutils.lua")
  if not f then error(err) end
  local Y = f()
  if Yutils == nil then Yutils = Y end
  if PY_TEXT_TO_SHAPE then
    Y.decode.create_font = function(family, bold, italic, underline, strikeout, size, xscale, yscale, hspace)
      xscale, yscale, hspace = xscale or 1, yscale or 1, hspace or 0
      local function run(text)
        return PY_TEXT_TO_SHAPE(family, bold, italic, size, xscale, yscale, hspace, text)
      end
      return {
        metrics = function()
          local _, _, h, asc, desc = run("")
          return { height = h, ascent = asc, descent = desc, internal_leading = 0, external_leading = 0 }
        end,
        text_extents = function(text)
          local _, w, h = run(text)
          return { width = w, height = h }
        end,
        text_to_shape = function(text)
          return (run(text))
        end,
      }
    end
  end
  return Y
end

-- Aegisub's LuaJIT is built with 5.2 compat, so ipairs honours __ipairs
do
  local raw_ipairs = ipairs
  function ipairs(t)
    if type(t) == "userdata" then
      local mt = getmetatable(t)
      if mt and mt.__ipairs then return mt.__ipairs(t) end
    end
    return raw_ipairs(t)
  end
end

-- Subtitle file object (userdata so that # works like in Aegisub)
function make_subs(entries, res_x, res_y)
  local store = entries
  local u = newproxy(true)
  local mt = getmetatable(u)
  local methods = {}
  methods.append = function(...)
    for _, l in ipairs({...}) do table.insert(store, util.copy(l)) end
  end
  methods.insert = function(i, ...)
    for k, l in ipairs({...}) do table.insert(store, i + k - 1, util.copy(l)) end
  end
  methods.delete = function(...)
    local idx = {...}
    if type(idx[1]) == "table" then idx = idx[1] end
    table.sort(idx, function(a, b) return a > b end)
    for _, i in ipairs(idx) do table.remove(store, i) end
  end
  methods.deleterange = function(a, b)
    for i = b, a, -1 do table.remove(store, i) end
  end
  methods.script_resolution = function() return res_x, res_y end
  mt.__len = function() return #store end
  mt.__ipairs = function()
    return function(_, i)
      i = i + 1
      if store[i] then return i, util.copy(store[i]) end
    end, u, 0
  end
  mt.__index = function(_, k)
    if type(k) == "number" then
      local l = store[k]
      if not l then error("Requested out-of-range line from subtitle file: " .. tostring(k), 2) end
      return util.copy(l)
    end
    return methods[k]
  end
  mt.__newindex = function(_, k, v)
    if type(k) ~= "number" then error("bad subs index") end
    if k > 0 then
      if v == nil then table.remove(store, k) else store[k] = util.copy(v) end
    elseif k < 0 then
      table.insert(store, -k, util.copy(v))
    else
      table.insert(store, util.copy(v))
    end
  end
  return u, store
end
