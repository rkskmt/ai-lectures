-- card-grid.lua — harden the lecture-index card grid against Pandoc's
-- section hoisting.
--
-- Pandoc's makeSections collapses a Div whose content is exactly one
-- header-led section into a single <section> that inherits the Div's
-- classes. For a `.lectures` div holding just ONE `### {.sec}` category
-- (e.g. one term tab of an index, or a short handouts page), that emits a
-- <section class="sec … lectures"> nested inside the slide — and reveal.js
-- treats every nested <section> as a vertical slide, breaking navigation
-- and pointer events on the whole deck.
--
-- Fix at the source: demote `.sec` headers inside `.lectures` to styled
-- Divs before the writer runs, so no Header remains to hoist. The CSS
-- (.reveal .lectures .sec) is element-agnostic, so rendering is unchanged.
local function has_class(el, class_name)
  for _, class in ipairs(el.classes) do
    if class == class_name then
      return true
    end
  end
  return false
end

-- The `.ruled` variant draws each category as one framed box (header band
-- + rows) and flows the boxes in two columns, so a header and its grid need
-- a common parent that the column layout can keep in one piece. Wrap each
-- `.sec` and the blocks after it, up to the next `.sec`, in `.lec-group`.
-- Only under `.ruled`: the card grid needs no wrapper, and leaving its
-- output untouched keeps every other index page byte-for-byte the same.
local function group_categories(blocks)
  local out = {}
  local current = nil
  local function flush()
    if current then
      table.insert(out, pandoc.Div(current, pandoc.Attr("", {"lec-group"})))
    end
  end
  for _, block in ipairs(blocks) do
    if block.t == "Div" and has_class(block, "sec") then
      flush()
      current = {block}
    elseif current then
      table.insert(current, block)
    else
      table.insert(out, block)
    end
  end
  flush()
  return out
end

-- `ruled-accent` (front matter, or a course's _metadata.yaml) sets the one
-- colour of the `.ruled` index: the search box and the hover fill. The text
-- drawn on it is black or white, whichever contrasts more (WCAG relative
-- luminance), so a dark accent stays readable. Unset, custom.css keeps its
-- yellow. A value that is not a hex colour stops the render: an invalid
-- colour would only make the box silently transparent.
local accent = nil
local accent_ink = nil

local function channel(hex2)
  local c = tonumber(hex2, 16) / 255
  if c <= 0.04045 then
    return c / 12.92
  end
  return ((c + 0.055) / 1.055) ^ 2.4
end

local function read_accent(meta)
  local value = meta["ruled-accent"]
  if value == nil then
    return nil
  end
  local s = pandoc.utils.stringify(value)
  local r, g, b = s:match("^#(%x)(%x)(%x)$")
  if r then
    s = "#" .. r .. r .. g .. g .. b .. b
  end
  r, g, b = s:match("^#(%x%x)(%x%x)(%x%x)$")
  if not r then
    error("[cleanslidekit] ruled-accent must be a hex colour such as \"#ffe14a\", got: " .. s)
  end
  local l = 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
  accent = s
  accent_ink = ((l + 0.05) / 0.05 >= 1.05 / (l + 0.05)) and "#000" or "#fff"
  return nil
end

function Div(el)
  if not has_class(el, "lectures") then
    return nil
  end
  local changed = false
  local out = {}
  for _, block in ipairs(el.content) do
    if block.t == "Header" and has_class(block, "sec") then
      table.insert(out, pandoc.Div(
        {pandoc.Plain(block.content)},
        pandoc.Attr(block.identifier, block.classes, block.attributes)
      ))
      changed = true
    else
      table.insert(out, block)
    end
  end
  if has_class(el, "ruled") then
    el.content = pandoc.Blocks(group_categories(out))
    if accent then
      return {
        pandoc.RawBlock("html", "<style>.reveal{--ruled-accent:" .. accent
          .. ";--ruled-accent-ink:" .. accent_ink .. "}</style>"),
        el,
      }
    end
    return el
  end
  if changed then
    el.content = pandoc.Blocks(out)
    return el
  end
  return nil
end

-- pdf-gate: the index badge linking to the handouts page. The pdf/
-- directory is produced by tools/qmd2pdf and gitignored, so on a fresh
-- clone — or a course that has no handouts yet — the badge would point
-- at nothing. Keep it only when pdf/ next to the input file actually
-- holds at least one PDF at render time.
local function has_handout_pdfs()
  local dir = pandoc.path.join({
    pandoc.path.directory(quarto.doc.input_file), "pdf",
  })
  local ok, entries = pcall(pandoc.system.list_directory, dir)
  if not ok then
    return false
  end
  for _, name in ipairs(entries) do
    if name:lower():match("%.pdf$") then
      return true
    end
  end
  return false
end

function Link(el)
  if not has_class(el, "pdf-gate") then
    return nil
  end
  if has_handout_pdfs() then
    return nil
  end
  io.stderr:write("[cleanslidekit] pdf-gate: no pdf/*.pdf next to "
    .. quarto.doc.input_file .. " — badge omitted\n")
  return {}
end

-- Read the metadata in a pass of its own: within one filter pandoc visits
-- Meta only after the blocks, and Div needs the accent.
return {
  {Meta = read_accent},
  {Div = Div, Link = Link},
}
