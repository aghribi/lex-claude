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

-- the template mark (backgrounds/mark.*), nil when the charter has none
local function charter_mark()
  for _, f in ipairs(pandoc.system.list_directory(bg)) do
    if f:match("^mark%.") then return bg_rel .. "/" .. f end
  end
end
local sync_steps = 0  -- clicks used by the last `.sync`, for the `.takeaway` after it
local last_step = 0   -- last beamer overlay used on the slide, for a `.spotlight` after it
local legend_id = 0   -- beamer: unique tikz names for `.sync` legends

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

-- `## Title {.lead}`: the first slide of a project or part, on a tinted content background until its first click
-- (backgrounds/lead.png, or lead2.png right after another lead: attribute `lead`, set by lead_variants)
function Header(h)
  sync_steps = 0
  last_step = 0
  if h.attributes.lead and quarto.doc.is_format("beamer") then
    h.content:insert(1, pandoc.RawInline("latex", "\\only<1>{\\brandlead{" .. h.attributes.lead .. ".png}\\color{white}}"))
    return h
  end
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
    local out, steps = {}, tonumber(read_all(deck_file("_diagrams/" .. stem .. ".steps")))
    -- with a link strip (links.lua) the picture stops above it
    local size = div.attributes.links and "width=\\linewidth,height=0.66\\paperheight,keepaspectratio" or "width=\\linewidth"
    for n = 0, steps - 1 do  -- the last step stays, under a `.spotlight` that may follow
      out[#out + 1] = string.format("\\includegraphics<%d%s>[%s]{%s}", n + 1, n == steps - 1 and "-" or "", size,
                                    deck_file("_diagrams/" .. stem .. "-" .. n .. ".pdf"))
    end
    last_step = steps
    return pandoc.RawBlock("latex", table.concat(out, "\n"))
  end
  return pandoc.BulletList({ { pandoc.Plain({ pandoc.Str("diagram") }) } })  -- removed by pptx_components.py
end

-- `.sync`: points on the left (`::: {.point fig="..." credit="..."}`), each with its figure on the right
-- (a point without `fig` keeps the previous one; `icon=` replaces the bullet; `legend=` puts the figure's legend,
-- cropped out of it, in the left column under the points). Each click shows the next point and swaps the figure;
-- earlier points half-fade. A `.takeaway` after it
-- comes on the next click, at the bottom of the slide (on its own, it comes on the first click).
-- A `.spotlight` inside it, after point k, takes the click between point k and point k + 1.
local function sync_points(div)
  local pts, spot, k = {}, nil, nil
  for _, c in ipairs(div.content) do
    if c.t == "Div" and c.classes:includes("spotlight") then
      spot, k = c, #pts
    elseif c.t == "Div" then
      pts[#pts + 1] = c
    end
  end
  return pts, spot, k
end

-- click that shows point i of a `.sync` whose spotlight follows point k (revealjs fragment index; beamer overlay - 1)
local function sync_click(i, k)
  return i - 1 + ((k and i > k) and 1 or 0)
end

local function frag(div, cls, idx)
  div.classes:extend({ "fragment", cls })
  div.attributes["data-fragment-index"] = tostring(idx)
  return div
end

-- figures of a `.sync`: each runs from its point to the next point that has one; `live="url"` shows the page
-- itself in revealjs, `fig` stays the picture elsewhere; `poster` stands in for an animated `fig` in beamer and pptx
local framed  -- figures whose border differs from the slide: diagram.py lists them in _diagrams/frames.json

local function sync_figs(pts)
  if not framed then
    framed = {}
    local f = io.open(deck_file("_diagrams/frames.json"), "r")
    if f then
      for _, path in ipairs(pandoc.json.decode(f:read("a"))) do framed[path] = true end
      f:close()
    end
  end
  local out = {}
  for i, p in ipairs(pts) do
    if p.attributes.fig then
      if #out > 0 then out[#out].last = i - 1 end
      out[#out + 1] = { first = i, last = #pts, fig = p.attributes.fig, live = p.attributes.live, credit = p.attributes.credit,
                        poster = p.attributes.poster,
                        frame = framed[p.attributes.fig], legend = p.attributes.legend }
    end
  end
  return out
end

local spotlight_html, spotlight_tex

local function sync(div)
  local pts, spot, k = sync_points(div)
  local n = #pts
  local function click(i) return sync_click(i, k) end
  sync_steps = n + (spot and 1 or 0)
  last_step = sync_steps
  if quarto.doc.is_format("revealjs") then
    local text, figs = {}, {}
    for i, p in ipairs(pts) do
      local point = pandoc.Div(p.content, pandoc.Attr("", { "sync-point" }))
      if p.attributes.icon then
        point.classes:insert("has-icon")
        point.content:insert(1, pandoc.RawBlock("html", '<span class="ico">' .. read_all(deck_file("_icons/" .. p.attributes.icon .. ".svg")) .. "</span>"))
      end
      if n > 1 then
        if i == 1 then frag(point, "semi-fade-out", click(2)) else frag(point, "fade-in-then-semi-out", click(i)) end
      end
      text[#text + 1] = point
    end
    -- point i shows on fragment i - 1; a figure fades in with its first point and out with the next figure
    local live = false
    for _, f in ipairs(sync_figs(pts)) do
      live = live or f.live ~= nil
      local media = f.live
        and pandoc.RawBlock("html", '<div class="sync-live"><iframe src="' .. f.live .. '" loading="lazy"></iframe></div>')
        or pandoc.Plain({ pandoc.Image({}, f.fig) })
      local fig = pandoc.Div({ media }, pandoc.Attr("", { "sync-fig" }))
      if f.frame then fig.classes:insert("framed") end
      if f.credit and not f.live then fig.content:insert(pandoc.Div(pandoc.Plain(pandoc.Str(f.credit)), pandoc.Attr("", { "sync-credit" }))) end
      local function shown(d)
        if f.last < n then d = frag(pandoc.Div({ d }), "fade-out", click(f.last + 1)) end
        if f.first > 1 then d = frag(pandoc.Div({ d }), "fade-in", click(f.first)) end
        d.classes:insert("sync-cell")
        return d
      end
      figs[#figs + 1] = shown(fig)
      if f.legend then  -- under its own point, over the room of the points still to come
        local leg = pandoc.Div({ pandoc.Plain({ pandoc.Image({}, f.legend) }) }, pandoc.Attr("", { "sync-legend", framed[f.legend] and "framed" or nil }))
        if f.last < n then leg = frag(pandoc.Div({ leg }), "fade-out", click(f.last + 1)) end
        leg.classes:insert("sync-legend-box")
        text[f.first].content:insert(leg)
      end
    end
    local out = { pandoc.Div(text, pandoc.Attr("", { "sync-points" })), pandoc.Div(figs, pandoc.Attr("", { "sync-figs" })) }
    -- a live page takes the right half of the slide and covers the template mark: draw the mark in the left half
    local mark = live and charter_mark()
    if mark then out[#out + 1] = pandoc.Div(pandoc.Plain({ pandoc.Image({}, mark) }), pandoc.Attr("", { "sync-live-mark" })) end
    if spot then out[#out + 1] = frag(spotlight_html(spot), "fade-in-then-out", k) end
    return pandoc.Div(out, pandoc.Attr("", { "sync" }))
  elseif quarto.doc.is_format("beamer") then
    local items, figs, legends = {}, {}, {}
    for _, f in ipairs(sync_figs(pts)) do
      local credit = f.credit and ("\\\\[2pt]{\\tiny\\itshape\\color{.!60}" .. tex_esc(f.credit) .. "}") or ""
      local img = string.format("\\includegraphics[width=\\dimexpr\\linewidth-2pt,height=0.5\\textheight,keepaspectratio]{%s}", deck_file(f.poster or f.fig))
      if f.frame then img = "{\\setlength\\fboxsep{0pt}\\fcolorbox{brandForeground!25}{white}{" .. img .. "}}" end
      local span = string.format("%d-%s", click(f.first) + 1, f.last == n and "" or tostring(click(f.last + 1)))
      figs[#figs + 1] = string.format("\\only<%s>{%s%s}", span, img, credit)
      if f.legend then legends[f.first] = { span = span, file = deck_file(f.legend) } end
    end
    -- a legend hangs under its own point, over the room of the points still to come, so the layout never moves
    for i, p in ipairs(pts) do
      local tex = pandoc.write(pandoc.Pandoc(p.content), "latex"):gsub("%s+$", "")
      local leg = legends[i]
      if leg then
        legend_id = legend_id + 1
        local id = "synclegend" .. legend_id
        tex = string.format("\\tikz[remember picture,overlay]\\coordinate (%s);%s\\tikz[remember picture,overlay]{\\coordinate (%s-end);"
          .. "\\node[anchor=north,inner sep=0pt,xshift=0.5\\linewidth,yshift=-1ex] at (%s |- %s-end) {\\only<%s>{\\includegraphics[width=0.85\\linewidth,height=0.25\\textheight,keepaspectratio]{%s}}};}",
          id, tex, id, id, id, leg.span, leg.file)
      end
      items[#items + 1] = string.format("\\item<%d-> {\\color<%d->{brandForeground!40}%s\\par}", click(i) + 1, click(i) + 2, tex)
    end
    return pandoc.RawBlock("latex", table.concat({
      "\\begin{columns}[c]", "\\begin{column}{0.42\\textwidth}", "\\setbeamerfont{itemize/enumerate body}{size=\\footnotesize}", "\\begin{itemize}\\setlength{\\itemsep}{3pt}", table.concat(items, "\n"), "\\end{itemize}",
      "\\end{column}", "\\begin{column}{0.56\\textwidth}", "\\centering", table.concat(figs, "\n"), "\\end{column}", "\\end{columns}",
      spot and spotlight_tex(spot, k + 1) or "" }, "\n"))
  end
  return pandoc.BulletList({ { pandoc.Plain({ pandoc.Str("sync") }) } })  -- removed by pptx_components.py
end

-- `.spotlight`: one message on its own, on the click after everything else on the slide. The slide fades under a
-- white veil and a card grows from the link strip (bottom left) to the centre, changing colour on the way.
-- `label="..."` heads the card, the div's content fills it; `talk="<Indico contribution URL>"` fills it from
-- _talks.json (talks.py) instead: speaker, title, day, time, room, link.
local function spotlight_parts(div)
  local url = div.attributes.talk
  if not url then return div.attributes.label or "", div.content end
  local f = assert(io.open("_talks.json", "r"), ".spotlight talk=: no _talks.json; is talks.py in the pre-render hook?")
  local talks = pandoc.json.decode(f:read("a"), false)
  f:close()
  local t = assert(talks[url], ".spotlight talk=: " .. url .. " is not a talk link in links.yml")
  local y, mo, d, hh, mi = t.start:match("(%d+)-(%d+)-(%d+)T(%d+):(%d+)")
  local when = os.date("%a %d %b, %H:%M", os.time({ year = y, month = mo, day = d, hour = hh, min = mi }))
  return div.attributes.label or "In this workshop", {
    pandoc.Para({ pandoc.Strong(pandoc.Str(t.speakers)) }),
    pandoc.Para(pandoc.Str(t.title)),
    pandoc.Para({ pandoc.Str(when .. (t.room ~= "" and (" · " .. t.room) or "")), pandoc.Space(),
                  pandoc.Link("Indico", url, "", pandoc.Attr("", {}, { target = "_blank" })) }),
  }
end

function spotlight_html(div)
  local label, blocks = spotlight_parts(div)
  return pandoc.Div({ pandoc.Div({ pandoc.Div(pandoc.Plain(pandoc.Str(label)), pandoc.Attr("", { "spotlight-label" })),
                                   pandoc.Div(blocks, pandoc.Attr("", { "spotlight-body" })) }, pandoc.Attr("", { "spotlight-card" })) },
                    pandoc.Attr("", { "spotlight" }))
end

-- the beamer card on overlay `step` only
function spotlight_tex(div, step)
  local label, blocks = spotlight_parts(div)
  local tex = pandoc.write(pandoc.Pandoc(blocks), "latex"):gsub("%s+$", "")
  return string.format(
    "\\only<%d>{\\begin{tikzpicture}[remember picture,overlay]\\fill[white,opacity=0.85] (current page.south west) rectangle (current page.north east);"
    .. "\\node[draw=brandPrimary,line width=1.5pt,rounded corners=6pt,fill=white,text width=0.58\\paperwidth,inner sep=10pt] at (current page.center)"
    .. " {{\\scriptsize\\bfseries\\color{brandSecondary}%s}\\par\\smallskip\\small %s};\\end{tikzpicture}}",
    step, tex_esc(label:upper()), tex)
end

local function spotlight(div)
  if quarto.doc.is_format("revealjs") then
    local d = spotlight_html(div)
    d.classes:insert("fragment")
    return d
  elseif quarto.doc.is_format("beamer") then
    return pandoc.RawBlock("latex", spotlight_tex(div, math.max(last_step, 1) + 1))
  end
  return pandoc.BulletList({ { pandoc.Plain({ pandoc.Str("spotlight") }) } })  -- removed by pptx_components.py
end

-- `.live`: web pages over the whole slide, one tab each: `::: {.tab label="..." src="<url>" poster="<png>"}`.
-- revealjs: a tab bar on top (a click on it also gives the keyboard back to the slides), the pages load with the slide;
-- beamer and pptx: the first tab's poster, a screenshot of the page.
local function live(div)
  local tabs = {}
  for _, c in ipairs(div.content) do
    if c.t == "Div" and c.classes:includes("tab") then tabs[#tabs + 1] = c.attributes end
  end
  if quarto.doc.is_format("revealjs") then
    local bar, frames = {}, {}
    for i, t in ipairs(tabs) do
      bar[#bar + 1] = string.format('<button class="live-tab%s" onclick="liveTab(this, %d)">%s</button>',
                                    i == 1 and " on" or "", i - 1, html_esc(t.label))
      frames[#frames + 1] = string.format('<iframe data-src="%s"%s></iframe>', html_esc(t.src), i == 1 and "" or " hidden")
    end
    return pandoc.RawBlock("html", '<div class="live-tabs"><div class="live-bar">' .. table.concat(bar) .. "</div>"
      .. table.concat(frames) .. "</div><script>function liveTab(b, i) { const r = b.closest('.live-tabs');"
      .. " r.querySelectorAll('.live-tab').forEach((x, k) => x.classList.toggle('on', k === i));"
      .. " r.querySelectorAll('iframe').forEach((f, k) => { f.hidden = k !== i; }); }</script>")
  end
  if quarto.doc.is_format("beamer") then
    return pandoc.RawBlock("latex", string.format(
      "\\begin{center}\\includegraphics[width=\\linewidth,height=0.62\\textheight,keepaspectratio]{%s}\\end{center}", deck_file(tabs[1].poster)))
  end
  return pandoc.Para({ pandoc.Image({}, tabs[1].poster) })
end

local function takeaway(div)
  local step = sync_steps + 1
  sync_steps = 0
  last_step = step
  if quarto.doc.is_format("revealjs") then
    div.classes:insert("fragment")
    div.attributes["data-fragment-index"] = tostring(math.max(step - 1, 0))
    return div
  elseif quarto.doc.is_format("beamer") then
    local tex = pandoc.write(pandoc.Pandoc(div.content), "latex"):gsub("%s+$", "")
    return pandoc.RawBlock("latex", string.format(
      "\\vfill\\uncover<%d->{\\colorbox{brandSecondary!14}{\\parbox{\\dimexpr\\linewidth-2\\fboxsep}{\\footnotesize\\color{brandPrimary}\\bfseries %s}}}", step, tex))
  end
  return pandoc.BulletList({ { pandoc.Plain({ pandoc.Str("takeaway") }) } })  -- removed by pptx_components.py
end

function Div(div)
  local reveal = quarto.doc.is_format("revealjs")
  if div.classes:includes("diagram") then return diagram(div) end
  if div.classes:includes("sync") then return sync(div) end
  if div.classes:includes("takeaway") then return takeaway(div) end
  if div.classes:includes("live") then return live(div) end
  if div.classes:includes("spotlight") and not div.classes:includes("in-sync") then return spotlight(div) end
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

-- text of a `.sync` point or a `.takeaway` as runs, bold where the source is **strong**
local function runs(blocks)
  local out = {}
  for _, b in ipairs(blocks) do
    if b.content then
      if #out > 0 then out[#out + 1] = { t = " " } end
      for _, il in ipairs(b.content) do
        if il.t == "Space" or il.t == "SoftBreak" then
          out[#out + 1] = { t = " " }
        else
          out[#out + 1] = { t = pandoc.utils.stringify(il), b = il.t == "Strong" or nil }
        end
      end
    end
  end
  return out
end

local function record(doc)
  if not quarto.doc.is_format("pptx") then return nil end
  local slides, title = {}, nil
  for _, b in ipairs(doc.blocks) do
    if b.t == "Header" and b.level <= 2 then
      title = pandoc.utils.stringify(b.content)
      if b.attributes.logo then slides[#slides + 1] = { title = title, kind = "logo", src = b.attributes.logo } end
      if b.attributes.lead then slides[#slides + 1] = { title = title, kind = "lead", src = b.attributes.lead .. ".png" } end
    elseif b.t == "Div" and title and b.classes:includes("diagram") then
      slides[#slides + 1] = { title = title, kind = "diagram", src = b.attributes.src }
    elseif b.t == "Div" and title and b.classes:includes("sync") then
      local items, pts, spot, k = {}, sync_points(b)
      for _, c in ipairs(pts) do
        items[#items + 1] = { runs = runs(c.content), fig = c.attributes.poster or c.attributes.fig, credit = c.attributes.credit, icon = c.attributes.icon,
                              legend = c.attributes.legend }
      end
      slides[#slides + 1] = { title = title, kind = "sync", items = items, spot = k }
      if spot then
        local label, blocks = spotlight_parts(spot)
        local paras = {}
        for _, bl in ipairs(blocks) do paras[#paras + 1] = runs({ bl }) end
        slides[#slides + 1] = { title = title, kind = "spotlight", label = label, paras = paras, after = k }
      end
    elseif b.t == "Div" and title and b.classes:includes("takeaway") then
      slides[#slides + 1] = { title = title, kind = "takeaway", runs = runs(b.content) }
    elseif b.t == "Div" and title and b.classes:includes("spotlight") then
      local label, blocks = spotlight_parts(b)
      local paras = {}
      for _, bl in ipairs(blocks) do paras[#paras + 1] = runs({ bl }) end
      slides[#slides + 1] = { title = title, kind = "spotlight", label = label, paras = paras }
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

-- `logo="file"` on a slide heading: the project logo left in the title box, the title moved right (box from the
-- template geometry, `logo_box` in charter.py); the template mark stays; pptx_components.py places it in pptx
local function logo(doc)
  local reveal, tex = quarto.doc.is_format("revealjs"), quarto.doc.is_format("beamer")
  if not (reveal or tex) then return nil end
  local out = {}
  for _, b in ipairs(doc.blocks) do
    out[#out + 1] = b
    local src = b.t == "Header" and b.level == 2 and b.attributes.logo
    if src and reveal then
      out[#out + 1] = pandoc.Div(pandoc.Plain({ pandoc.Image({}, src) }), pandoc.Attr("", { "brand-logo" }))
    elseif src then
      -- first in the frame title: an overlay there takes no space, and its \hspace moves the title text right
      -- on a `.lead` frame a white chip keeps a dark logo readable on the dark ground
      local chip = b.attributes.lead and "[fill=white,rounded corners=2pt,inner sep=1.5pt]" or ""
      b.content:insert(1, pandoc.RawInline("latex", "\\brandlogo" .. chip .. "{" .. src .. "}"))
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

-- `.lead` headings get `lead` = "lead", or "lead2" when the slide before was a lead with "lead": two in a row differ
local function lead_variants(doc)
  local prev
  for _, b in ipairs(doc.blocks) do
    if b.t == "Header" and b.level <= 2 then
      local cur
      if b.level == 2 and b.classes:includes("lead") then cur = prev == "lead" and "lead2" or "lead" end
      if cur then b.attributes.lead = cur end
      prev = cur
    end
  end
  return doc
end

-- revealjs: the tint is a layer over the slide background, faded out once a fragment of the slide shows
local LEAD_JS = "<script>window.addEventListener('load', function () { function f() {"
  .. " document.querySelectorAll('.reveal .slides section.lead').forEach(function (s) {"
  .. " s.classList.toggle('lead-off', !!s.querySelector('.fragment.visible')); }); }"
  .. " ['ready', 'slidechanged', 'fragmentshown', 'fragmenthidden'].forEach(function (e) { Reveal.on(e, f); }); f(); });</script>"

-- list items take their colour from the beamer theme, not the current colour: set it too
local LEAD_TEX = "\\only<1>{\\color{white}\\setbeamercolor{itemize/enumerate body}{fg=white}"
  .. "\\setbeamercolor{itemize item}{fg=white}}"

-- revealjs loads images a few slides ahead, so a GIF that plays once would end before it is seen: restart the
-- GIFs of a slide when it is shown, and of a fragment when it appears (a new query string restarts the animation)
local GIF_JS = "<script>window.addEventListener('load', function () { function go(root) {"
  .. " if (!root) return; root.querySelectorAll('img').forEach(function (i) {"
  .. " var s = i.getAttribute('src') || i.getAttribute('data-src') || '';"
  .. " if (!/\\.gif(\\?|$)/i.test(s)) return; i.src = s.split('?')[0] + '?t=' + Date.now(); }); }"
  .. " Reveal.on('slidechanged', function (e) { go(e.currentSlide); });"
  .. " Reveal.on('fragmentshown', function (e) { go(e.fragment); }); go(Reveal.getCurrentSlide()); });</script>"

local function lead_tints(doc)
  if quarto.doc.is_format("beamer") then  -- reverse contrast: light body text on the first overlay
    local out = {}
    for _, b in ipairs(doc.blocks) do
      out[#out + 1] = b
      if b.t == "Header" and b.attributes.lead then out[#out + 1] = pandoc.RawBlock("latex", LEAD_TEX) end
    end
    doc.blocks = out
    return doc
  end
  if not quarto.doc.is_format("revealjs") then return nil end
  local out, any = {}, false
  for _, b in ipairs(doc.blocks) do
    out[#out + 1] = b
    if b.t == "Header" and b.attributes.lead then
      any = true
      out[#out + 1] = pandoc.RawBlock("html", '<div class="lead-tint" style="background-image: url(\'' .. bg_rel .. "/" .. b.attributes.lead .. '.png\')"></div>')
    end
  end
  if any then out[#out + 1] = pandoc.RawBlock("html", LEAD_JS) end
  out[#out + 1] = pandoc.RawBlock("html", GIF_JS)
  doc.blocks = out
  return doc
end

-- a `.spotlight` inside a `.sync` is drawn by the `.sync`; the Div pass runs bottom-up, so mark it first
local function in_sync(div)
  if not div.classes:includes("sync") then return nil end
  for _, c in ipairs(div.content) do
    if c.t == "Div" and c.classes:includes("spotlight") then c.classes:insert("in-sync") end
  end
  return div
end

return { { Meta = Meta }, { Pandoc = lead_variants }, { Pandoc = contents }, { Pandoc = record }, { Div = in_sync }, { Header = Header, Div = Div },
         { Pandoc = logo }, { Pandoc = lead_tints }, { Pandoc = Pandoc } }
