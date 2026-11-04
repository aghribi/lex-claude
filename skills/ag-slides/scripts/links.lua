-- Link strip per slide, from the deck's links.yml (title -> [kind, label, url], kinds git, data, info, ref).
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

local function strip_html(items)
  local out = {}
  for _, it in ipairs(items) do
    local k, label, url = fields(it)
    local ico = k == "ref" and "" or assert(read(quarto.utils.resolve_path("icons/" .. k .. ".svg")), "links.yml: unknown kind " .. k)
    out[#out + 1] = '<a class="lk ' .. k .. '" href="' .. url .. '" target="_blank">' .. ico .. "<span>" .. label .. "</span></a>"
  end
  return pandoc.RawBlock("html", '<div class="links">' .. table.concat(out) .. "</div>")
end

local function strip_tex(items)
  local out = {}
  for _, it in ipairs(items) do
    local k, label, url = fields(it)
    local ico = k == "ref" and "" or "\\includegraphics[height=1.6ex]{" .. quarto.utils.resolve_path("icons/" .. k .. ".png") .. "}\\,"
    out[#out + 1] = ico .. "\\href{" .. esc_tex(url) .. "}{" .. esc_tex(label) .. "}"
  end
  return pandoc.RawBlock("latex", "\\brandlinks{" .. table.concat(out, "\\quad ") .. "}")
end

local function key(s)
  return (s:gsub("\u{2019}", "'"))
end

function Pandoc(doc)
  local make = quarto.doc.is_format("revealjs") and strip_html or (quarto.doc.is_format("beamer") and strip_tex)
  local yml = make and read("links.yml")
  if not yml then return nil end
  local links = {}
  for k, v in pairs(pandoc.read("---\n" .. yml .. "\n---\n", "markdown").meta) do links[key(k)] = v end
  local blocks, pending = pandoc.List(), nil
  for _, b in ipairs(doc.blocks) do
    if b.t == "Header" and b.level <= 2 then
      if pending then blocks:insert(make(pending)) end
      pending = b.level == 2 and links[key(pandoc.utils.stringify(b.content))] or nil
    end
    blocks:insert(b)
  end
  if pending then blocks:insert(make(pending)) end
  doc.blocks = blocks
  return doc
end
