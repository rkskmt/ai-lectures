local COLON = "："

local function fw_colon(el)
  local text = el.text
  local s, e = text:find(COLON, 1, true)
  if not s then return end

  local out = {}
  local last = 1
  while s do
    if s > last then
      table.insert(out, pandoc.Str(text:sub(last, s - 1)))
    end
    table.insert(out, pandoc.Span(
      {pandoc.Str(COLON)},
      pandoc.Attr("", {"fw-colon"})
    ))
    last = e + 1
    s, e = text:find(COLON, last, true)
  end
  if last <= #text then
    table.insert(out, pandoc.Str(text:sub(last)))
  end
  return out
end

function Pandoc(doc)
  doc.blocks = doc.blocks:walk({Str = fw_colon})
  return doc
end
