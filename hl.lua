local function hl_str(el)
  local text = el.text
  local out = {}
  local last = 1
  local any = false
  local pos = 1

  while pos <= #text do
    local s, e, cap = text:find("==([^=%s]+)==", pos)
    if not s then break end
    any = true
    if s > last then
      table.insert(out, pandoc.Str(text:sub(last, s - 1)))
    end
    table.insert(out, pandoc.Span(
      {pandoc.Str(cap)},
      pandoc.Attr("", {"hl"})
    ))
    last = e + 1
    pos = e + 1
  end

  if not any then return end
  if last <= #text then
    table.insert(out, pandoc.Str(text:sub(last)))
  end
  return out
end

function Pandoc(doc)
  doc.blocks = doc.blocks:walk({Str = hl_str})
  return doc
end
