function Div(el)
  if el.classes:includes("plotly-iframe") then
    local src = el.attributes.src
    local width = el.attributes.width or "900"
    local height = el.attributes.height or "520"

    local html = string.format([[
<div style="display:flex; justify-content:center;">
<iframe src="%s" width="%s" height="%s" style="border:none;"></iframe>
</div>]], src, width, height)

    return pandoc.RawBlock("html", html)
  end
end
