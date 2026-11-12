-- ag-slides charter filter, shipped inside each charter's Quarto extension.
-- revealjs: template backgrounds on the title slide, section slides (#), content slides (##) and {.plain} slides,
--           and the template footer inside every slide.
-- beamer: loads the charter theme from the extension and passes it the deck footer.

local bg = quarto.utils.resolve_path("backgrounds")
-- revealjs: path relative to the project, mirrored into build/ by the deck's `resources:`
local bg_rel = bg:match("(_extensions/.*)$") or bg
-- "contain", not "cover": reveal letterboxes the 16:9 slide in the window, and the background must sit in the same box
-- (with "cover" a 16:10 screen crops the template's sides, logo included)

local footer = ""

local function role_of(h)
  if h.classes:includes("plain") then return "plain" end
  if h.level == 1 then return "section" end
  if h.level == 2 then return "content" end
end

local function html_esc(s)
  return (s:gsub("&", "&amp;"):gsub("<", "&lt;"):gsub(">", "&gt;"))
end

local TEX = { ["\\"] = "\\textbackslash{}", ["~"] = "\\textasciitilde{}", ["^"] = "\\textasciicircum{}" }

local function tex_esc(s)
  return (s:gsub("[\\{}$&#^_%%~]", function(c) return TEX[c] or ("\\" .. c) end))
end

-- `eyebrow:` in the front matter: a short label above the title on the title slide
function Meta(meta)
  footer = meta.footer and pandoc.utils.stringify(meta.footer) or ""
  local eyebrow = meta.eyebrow and pandoc.utils.stringify(meta.eyebrow)
  if quarto.doc.is_format("revealjs") then
    if eyebrow and meta.title then
      meta.pagetitle = meta.pagetitle or pandoc.utils.stringify(meta.title)
      local t = pandoc.Inlines({ pandoc.RawInline("html", '<span class="eyebrow">' .. html_esc(eyebrow) .. "</span>") })
      t:extend(meta.title)
      meta.title = t
    end
    local attrs = meta["title-slide-attributes"] or {}
    attrs["data-background-image"] = attrs["data-background-image"] or (bg_rel .. "/title.png")
    attrs["data-background-size"] = attrs["data-background-size"] or "contain"
    meta["title-slide-attributes"] = attrs
  elseif quarto.doc.is_format("beamer") then
    -- the deck's own title cover, as in revealjs and pptx
    local tsa = meta["title-slide-attributes"]
    local title_bg = tsa and tsa["data-background-image"] and pandoc.utils.stringify(tsa["data-background-image"])
    quarto.doc.include_text("in-header", table.concat({
      "\\def\\brandbgdir{" .. bg .. "}",
      "\\usepackage{" .. quarto.utils.resolve_path("beamerthemecharter") .. "}",
      "\\renewcommand\\brandfooter{" .. footer .. "}",
      eyebrow and ("\\def\\brandeyebrow{" .. tex_esc(eyebrow) .. "}") or "",
      title_bg and ("\\def\\brandtitlebg{" .. title_bg .. "}") or "",
    }, "\n"))
  end
  return meta
end

function Header(h)
  if not quarto.doc.is_format("revealjs") or h.attributes["background-image"] then return nil end
  local role = role_of(h)
  if role then
    h.attributes["background-image"] = bg_rel .. "/" .. role .. ".png"
    h.attributes["background-size"] = "contain"
  end
  return h
end

-- components (components.scss): .tiles > .tile, .cards > .card, .steps > .step, .timeline over a list.
-- revealjs: entrance animation index per child; `.build` turns the children into fragments.
-- pptx and beamer have no grid: tiles, cards and steps become a list, the timeline two tables in columns.
local GRIDS = { tiles = true, cards = true, steps = true }
local GRID_MAX = 4

local function grid_kind(div)
  for _, c in ipairs(div.classes) do
    if GRIDS[c] then return c end
  end
end

-- `- M8 D2.1 Accelerator measurement procedures (CERN)`: month, id, title; ids starting with MS are milestones
local function timeline_events(div)
  local evs = {}
  for _, b in ipairs(div.content) do
    if b.t == "BulletList" then
      for _, item in ipairs(b.content) do
        local txt = pandoc.utils.stringify(item)
        local m, id, title = txt:match("^M(%d+)%s+(%S+)%s+(.*)$")
        if not m then error("timeline item must read `M<month> <id> <title>`: " .. txt) end
        evs[#evs + 1] = { m = tonumber(m), id = id, title = title, ms = id:match("^MS") ~= nil }
      end
    end
  end
  table.sort(evs, function(a, b) return a.m < b.m end)
  return evs
end

local function timeline_html(div, evs)
  local months = tonumber(div.attributes.months) or evs[#evs].m
  -- label width in months: deliverables above the axis, milestones below
  local spans = { up = tonumber(div.attributes["label-up"]) or months / 4, down = tonumber(div.attributes["label-down"]) or months / 6 }
  local out = { '<div class="timeline"><div class="axis"></div>' }
  for t = 0, months, 12 do
    out[#out + 1] = string.format('<span class="tick" style="left:%.2f%%">M%d</span>', 100 * t / months, t)
  end
  if div.attributes.now then
    local n = tonumber(div.attributes.now)
    out[#out + 1] = string.format('<div class="now" style="left:%.2f%%"><span>M%d, today</span></div>', 100 * n / months, n)
  end
  -- each label runs right or left of its event, whichever sits closer to the axis without overlapping
  -- a label already placed on the same side; levels stack away from the axis
  local ends, stems = { up = {}, down = {} }, {}
  local function level_for(side, a)
    local l = 0
    while ends[side][l] and a < ends[side][l] do l = l + 1 end
    return l
  end
  for i, e in ipairs(evs) do
    local side = e.ms and "down" or "up"
    local span = spans[side]
    local best
    for _, late in ipairs({ false, true }) do
      local a, b = late and e.m - span or e.m, late and e.m or e.m + span
      if a >= 0 and b <= months then
        local l = level_for(side, a)
        if not best or l < best.l then best = { l = l, b = b, late = late } end
      end
    end
    ends[side][best.l] = best.b
    local pos = string.format('left:%.2f%%;height:%dpx;--i:%d', 100 * e.m / months, 40 + 95 * best.l, i)
    stems[#stems + 1] = string.format('<div class="stem %s" style="%s"></div>', side, pos)
    out[#out + 1] = string.format('<div class="ev %s%s" style="%s;--w:%.2f"><div class="lbl"><b>%s</b><i>M%d</i><br>%s</div></div>',
      side, best.late and " late" or "", pos, 100 * span / months, html_esc(e.id), e.m, html_esc(e.title))
  end
  -- stems first: every label paints over every stem
  table.insert(out, 2, table.concat(stems))
  out[#out + 1] = "</div>"
  return pandoc.RawBlock("html", table.concat(out))
end

-- one list item per child: first paragraph in bold, then the rest of the text
local function grid_list(div, kind)
  local items = {}
  for _, child in ipairs(div.content) do
    if child.t == "Div" then
      local inl = pandoc.Inlines({})
      for j, b in ipairs(child.content) do
        if b.content then
          local part = pandoc.Inlines(b.content)
          if j == 1 then
            part = pandoc.Inlines({ pandoc.Strong(part) })
          else
            if j == 2 and kind ~= "tiles" then inl:insert(pandoc.Str(":")) end
            inl:insert(pandoc.Space())
          end
          inl:extend(part)
        end
      end
      items[#items + 1] = { pandoc.Plain(inl) }
    end
  end
  return pandoc.BulletList(items)
end

-- pptx and beamer: two tables side by side, deliverables and milestones; pandoc sets tables in small type
local function timeline_columns(evs)
  local cols = {}
  for _, ms in ipairs({ false, true }) do
    local rows = {}
    for _, e in ipairs(evs) do
      if e.ms == ms then
        rows[#rows + 1] = { { pandoc.Plain({ pandoc.Strong(e.id), pandoc.Space(), pandoc.Str(e.title) }) }, { pandoc.Plain({ pandoc.Str("M" .. e.m) }) } }
      end
    end
    local head = { { pandoc.Plain({ pandoc.Str(ms and "Milestone" or "Deliverable") }) }, { pandoc.Plain({ pandoc.Str("Month") }) } }
    local tbl = pandoc.utils.from_simple_table(pandoc.SimpleTable({}, { pandoc.AlignLeft, pandoc.AlignRight }, { 0, 0 }, head, rows))
    cols[#cols + 1] = pandoc.Div({ tbl }, pandoc.Attr("", { "column" }, { width = "50%" }))
  end
  return pandoc.Div(cols, pandoc.Attr("", { "columns" }))
end

-- `.diagram src=figures/x.yml`: diagram.py (pre-render) drew it into _diagrams/.
-- revealjs: inline svg with fragments. beamer: one overlay per step. pptx: pptx_components.py draws it.
local function deck_file(rel)
  return pandoc.path.join({ pandoc.path.directory(quarto.doc.input_file), rel })
end

local function read_all(path)
  local f = assert(io.open(path, "r"), "missing " .. path .. ": is diagram.py in the pre-render hook?")
  local s = f:read("a")
  f:close()
  return s
end

local function diagram(div)
  local stem = pandoc.path.split_extension(pandoc.path.filename(div.attributes.src))
  if quarto.doc.is_format("revealjs") then
    return pandoc.RawBlock("html", '<div class="diagram">' .. read_all(deck_file("_diagrams/" .. stem .. ".svg")) .. "</div>")
  elseif quarto.doc.is_format("beamer") then
    local out = {}
    for n = 0, tonumber(read_all(deck_file("_diagrams/" .. stem .. ".steps"))) - 1 do
      out[#out + 1] = string.format("\\includegraphics<%d>[width=\\linewidth]{%s}", n + 1, deck_file("_diagrams/" .. stem .. "-" .. n .. ".pdf"))
    end
    return pandoc.RawBlock("latex", table.concat(out, "\n"))
  end
  return pandoc.BulletList({ { pandoc.Plain({ pandoc.Str("diagram") }) } })  -- removed by pptx_components.py
end

function Div(div)
  local reveal = quarto.doc.is_format("revealjs")
  if div.classes:includes("diagram") then return diagram(div) end
  if div.classes:includes("timeline") then
    local evs = timeline_events(div)
    return reveal and timeline_html(div, evs) or timeline_columns(evs)
  end
  local kind = grid_kind(div)
  if not kind then return nil end
  if not reveal then return grid_list(div, kind) end
  local build = div.classes:includes("build")
  if not build then div.classes:insert("comp-anim") end
  local i = 0
  for _, child in ipairs(div.content) do
    if child.t == "Div" then
      child.attributes.style = "--i:" .. i
      if child.attributes.icon then
        child.content:insert(1, pandoc.RawBlock("html", '<span class="ico">' .. read_all(deck_file("_icons/" .. child.attributes.icon .. ".svg")) .. "</span>"))
      end
      if build then child.classes:insert("fragment") end
      i = i + 1
    end
  end
  return div
end

-- pptx: pandoc cannot draw tiles, cards or steps, so their content goes to _components.json beside the deck,
-- keyed by slide title; pptx_components.py (post-render) replaces the fallback list with shapes
local function child_parts(child)
  local head, tag, body = "", nil, {}
  for j, b in ipairs(child.content) do
    if b.content then
      if j == 1 then
        head = pandoc.utils.stringify(b)
      else
        local rest = pandoc.Inlines({})
        for _, il in ipairs(b.content) do
          if il.t == "Span" and il.classes:includes("tag") then tag = pandoc.utils.stringify(il) else rest:insert(il) end
        end
        body[#body + 1] = pandoc.utils.stringify(rest)
      end
    end
  end
  return { head = head, tag = tag, body = (table.concat(body, " "):gsub("^%s+", "")), accent = child.classes:includes("accent"), icon = child.attributes.icon }
end

-- every deck gets a contents slide after the title: up to 4 sections as steps listing their slides
-- (or the section's `subtitle` attribute), otherwise a numbered list of the sections, or of the slides
-- when the deck has no sections; `.nocontents` keeps a slide off the list
local function contents(doc)
  local sections, slides, first = {}, {}, nil
  for i, b in ipairs(doc.blocks) do
    if b.t == "Header" and b.level <= 2 then
      first = first or i
      local name = pandoc.utils.stringify(b.content)
      if b.level == 1 then
        sections[#sections + 1] = { head = name, slides = {}, subtitle = b.attributes.subtitle }
      elseif not b.classes:includes("plain") and not b.classes:includes("nocontents") then
        slides[#slides + 1] = name
        if #sections > 0 then table.insert(sections[#sections].slides, name) end
      end
    end
  end
  if not first then return nil end
  local body
  if #sections > 0 and #sections <= GRID_MAX then
    local steps = {}
    for _, sec in ipairs(sections) do
      steps[#steps + 1] = pandoc.Div({ pandoc.Para(pandoc.Str(sec.head)), pandoc.Para(pandoc.Str(sec.subtitle or table.concat(sec.slides, " · "))) }, pandoc.Attr("", { "step" }))
    end
    body = pandoc.Div(steps, pandoc.Attr("", { "steps" }))
  else
    local items = {}
    for _, sec in ipairs(#sections > 0 and sections or slides) do
      items[#items + 1] = { pandoc.Plain(pandoc.Str(sec.head or sec)) }
    end
    body = pandoc.OrderedList(items)
  end
  doc.blocks:insert(first, body)
  doc.blocks:insert(first, pandoc.Header(2, pandoc.Str("Contents")))
  return doc
end

local function record(doc)
  if not quarto.doc.is_format("pptx") then return nil end
  local slides, title = {}, nil
  for _, b in ipairs(doc.blocks) do
    if b.t == "Header" and b.level <= 2 then
      title = pandoc.utils.stringify(b.content)
      if b.attributes.logo then slides[#slides + 1] = { title = title, kind = "logo", src = b.attributes.logo } end
    elseif b.t == "Div" and title and b.classes:includes("diagram") then
      slides[#slides + 1] = { title = title, kind = "diagram", src = b.attributes.src }
    elseif b.t == "Div" and title and grid_kind(b) then
      local items = {}
      for _, c in ipairs(b.content) do
        if c.t == "Div" then items[#items + 1] = child_parts(c) end
      end
      slides[#slides + 1] = { title = title, kind = grid_kind(b), items = items, build = b.classes:includes("build") }
    end
  end
  local m = doc.meta
  local out = { slides = slides, eyebrow = m.eyebrow and pandoc.utils.stringify(m.eyebrow) or nil,
                institute = m.institute and pandoc.utils.stringify(m.institute) or nil }
  local dir = pandoc.path.directory(quarto.doc.input_file)
  local f = assert(io.open(pandoc.path.join({ dir, "_components.json" }), "w"))
  f:write(pandoc.json.encode(out))
  f:close()
end

-- `logo="file"` on a slide heading: the image right of the title (box from the template geometry), swapped
-- with the template mark when the charter has one (backgrounds/mark.*); pptx_components.py places it in pptx
local function logo(doc)
  local reveal, tex = quarto.doc.is_format("revealjs"), quarto.doc.is_format("beamer")
  if not (reveal or tex) then return nil end
  local mark
  for _, f in ipairs(pandoc.system.list_directory(bg)) do
    if f:match("^mark%.") then mark = bg_rel .. "/" .. f end
  end
  local out = {}
  for _, b in ipairs(doc.blocks) do
    out[#out + 1] = b
    local src = b.t == "Header" and b.level == 2 and b.attributes.logo
    if src and reveal then
      if mark then
        out[#out + 1] = pandoc.Div({}, pandoc.Attr("", { "brand-cover" }))
        out[#out + 1] = pandoc.Div(pandoc.Plain({ pandoc.Image({}, mark) }), pandoc.Attr("", { "brand-mark" }))
      end
      out[#out + 1] = pandoc.Div(pandoc.Plain({ pandoc.Image({}, src) }), pandoc.Attr("", { "brand-logo" }))
    elseif src then
      -- in the frame title: an overlay there takes no space, a block in the frame body pushes the content down
      b.content:insert(pandoc.RawInline("latex", "\\brandlogo{" .. src .. "}"))
    end
  end
  doc.blocks = out
  return doc
end

-- revealjs: close every slide with the footer; a block before a slide heading ends the previous slide
-- numbers are written at build time: reveal hides far slides (display: none) and CSS counters skip them
local function foot(n)
  local esc = footer:gsub("&", "&amp;"):gsub("<", "&lt;")
  return pandoc.RawBlock("html", '<div class="brand-foot"><span class="brand-url"></span><span class="brand-text">' .. esc .. '</span><span class="brand-num">' .. n .. '</span></div>')
end

function Pandoc(doc)
  if not quarto.doc.is_format("revealjs") then return nil end
  local out, n = {}, 1  -- the title slide is number 1, as in the pptx
  for _, b in ipairs(doc.blocks) do
    if b.t == "Header" and b.level <= 2 then
      if n > 1 then out[#out + 1] = foot(n) end
      n = n + 1
    end
    out[#out + 1] = b
  end
  if n > 1 then out[#out + 1] = foot(n) end
  doc.blocks = out
  return doc
end

return { { Meta = Meta }, { Pandoc = contents }, { Pandoc = record }, { Header = Header, Div = Div }, { Pandoc = logo }, { Pandoc = Pandoc } }
