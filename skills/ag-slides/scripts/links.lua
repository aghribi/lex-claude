-- Link strip per slide, from the deck's links.yml (title -> [kind, label, url], kinds git, github, gitlab, data, paper, web, info, ref).
-- A talk at the same event is [talk, <Indico contribution URL>]: talks.py (pre-render) resolves its label into _talks.json.
-- A fourth field n ties a link to the n-th `.point` of the slide's `.sync`: it shows while that point is the current one.
-- revealjs and beamer are written here; pptx_links.py draws it in pptx.
local function read(path)
  local f = io.open(path, "rb")
  if not f then return nil end
  local s = f:read("a")
  f:close()
  return s
end

local function esc_tex(s)
  return (s:gsub("[%%#&_]", "\\%0"))
end

local function fields(it)
  return pandoc.utils.stringify(it[1]), pandoc.utils.stringify(it[2]), pandoc.utils.stringify(it[3])
end

local function anchor(it)
  local k, label, url = fields(it)
  local ico = k == "ref" and "" or assert(read(quarto.utils.resolve_path("icons/" .. k .. ".svg")), "links.yml: unknown kind " .. k)
  local title = it.title and (' title="' .. it.title:gsub('"', "&quot;") .. '"') or ""
  return '<a class="lk ' .. k .. '" href="' .. url .. '" target="_blank"' .. title .. ">" .. ico .. "<span>" .. label .. "</span></a>"
end

-- [talk, url, n] -> [talk, label, url, n] from _talks.json, with the talk title for the hover
local function expand(items, talks)
  local out = {}
  for _, it in ipairs(items) do
    if pandoc.utils.stringify(it[1]) == "talk" then
      local url = pandoc.utils.stringify(it[2])
      local t = assert(talks and talks[url], "links.yml: talk " .. url .. " missing from _talks.json; is talks.py in the pre-render hook?")
      out[#out + 1] = { "talk", t.label, url, it[3], title = t.title .. ", " .. t.room }
    else
      out[#out + 1] = it
    end
  end
  return out
end

-- links tied to point s show from the fragment of point s (at[s]) to that of point s + 1: a point takes one
-- fragment plus one per frame of its `steps`, a `.spotlight` after it one more (charter.lua `sync_clicks`)
local function sync_clicks(pts)
  local at, c = {}, 0
  for _, p in ipairs(pts) do
    if p.classes:includes("spotlight") then
      c = c + 1
    else
      at[#at + 1] = c
      c = c + 1
      for _ in (p.attributes.steps or ""):gmatch("%S+") do c = c + 1 end
    end
  end
  return at
end

local function by_step(items)
  local always, steps = {}, {}
  for _, it in ipairs(items) do
    local s = it[4] and tonumber(pandoc.utils.stringify(it[4]))
    if s then
      steps[s] = steps[s] or {}
      table.insert(steps[s], it)
    else
      always[#always + 1] = it
    end
  end
  return always, steps
end

local function strip_html(items, n, at)
  local always, steps = by_step(items)
  local out = {}
  for _, it in ipairs(always) do out[#out + 1] = anchor(it) end
  local cells = {}
  for s, its in pairs(steps) do
    local inner = {}
    for _, it in ipairs(its) do inner[#inner + 1] = anchor(it) end
    local cell = '<span class="lk-step">' .. table.concat(inner) .. "</span>"
    if s < n then cell = '<span class="lk-step fragment fade-out" data-fragment-index="' .. at[s + 1] .. '">' .. cell .. "</span>" end
    if s > 1 then cell = '<span class="lk-step fragment fade-in" data-fragment-index="' .. at[s] .. '">' .. cell .. "</span>" end
    cells[#cells + 1] = cell
  end
  if #cells > 0 then out[#out + 1] = '<span class="lk-steps">' .. table.concat(cells) .. "</span>" end
  return pandoc.RawBlock("html", '<div class="links">' .. table.concat(out) .. "</div>")
end

local function tex_link(it)
  local k, label, url = fields(it)
  local ico = k == "ref" and "" or "\\includegraphics[height=1.6ex]{" .. quarto.utils.resolve_path("icons/" .. k .. ".png") .. "}\\,"
  return ico .. "\\href{" .. esc_tex(url) .. "}{" .. esc_tex(label) .. "}"
end

local function strip_tex(items, n, at)
  local always, steps = by_step(items)
  local out = {}
  for _, it in ipairs(always) do out[#out + 1] = tex_link(it) end
  local only = {}
  for s, its in pairs(steps) do
    local inner = {}
    for _, it in ipairs(its) do inner[#inner + 1] = tex_link(it) end
    only[#only + 1] = string.format("\\only<%d-%s>{%s}", at[s] + 1, s == n and "" or at[s + 1], table.concat(inner, "\\quad "))
  end
  if #only > 0 then out[#out + 1] = table.concat(only) end
  -- the strip is pinned above the footer: a line of space at the end of the frame lifts a bottom takeaway clear of it;
  -- the strip itself opens the frame, so a `.spotlight` veil drawn later covers it
  return pandoc.RawBlock("latex", "\\brandlinks{" .. table.concat(out, "\\quad ") .. "}"), pandoc.RawBlock("latex", "\\vspace{1.1em}")
end

local function key(s)
  return (s:gsub("\u{2019}", "'"))
end

function Pandoc(doc)
  local make = quarto.doc.is_format("revealjs") and strip_html or (quarto.doc.is_format("beamer") and strip_tex)
  local yml = make and read("links.yml")
  if not yml then return nil end
  local cache = read("_talks.json")
  local talks = cache and pandoc.json.decode(cache, false)
  local links = {}
  for k, v in pairs(pandoc.read("---\n" .. yml .. "\n---\n", "markdown").meta) do links[key(k)] = expand(v, talks) end
  local blocks, pending, pts, start = pandoc.List(), nil, {}, 0
  local function flush()
    if not pending then return end
    local at = sync_clicks(pts)
    local strip, tail = make(pending, #at, at)
    if tail then
      blocks:insert(start + 1, strip)
      blocks:insert(tail)
    else
      blocks:insert(strip)
    end
  end
  for _, b in ipairs(doc.blocks) do
    if b.t == "Header" and b.level <= 2 then
      flush()
      pending = b.level == 2 and links[key(pandoc.utils.stringify(b.content))] or nil
      pts, start = {}, #blocks + 1
    elseif b.t == "Div" and b.classes:includes("diagram") and pending then
      b.attributes["links"] = "1"  -- charter.lua leaves room for the strip under it in beamer
    elseif b.t == "Div" and b.classes:includes("sync") then
      for _, c in ipairs(b.content) do
        if c.t == "Div" then pts[#pts + 1] = c end
      end
    end
    blocks:insert(b)
  end
  flush()
  doc.blocks = blocks
  return doc
end
