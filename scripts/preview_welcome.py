# One-off: render the welcome email from apps-script/Code.gs to preview-welcome.html
# so it can be eyeballed in a browser without sending anything.
import re
from pathlib import Path

root = Path(__file__).resolve().parent.parent
gs = (root / "apps-script" / "Code.gs").read_text(encoding="utf-8")

# isolate the function body
m = re.search(r"function welcomeHtml_\(\) \{(.*?)\n\}", gs, re.S)
body = m.group(1)

# drop JS comment lines
lines = [l for l in body.splitlines() if not l.strip().startswith("//")]
body = "\n".join(lines)

# turn the JS expression into a Python expression
start = body.index("return")
expr = body[start + len("return"):].strip()
if expr.endswith(";"):
    expr = expr[:-1]

ns = {
    "SITE_URL": "https://videoedits4clients-crypto.github.io/ai-news-hub/",
    "SKILLATLAS_URL": "https://videoedits4clients-crypto.github.io/skillatlas/",
    "CHANNEL_URL": "https://whatsapp.com/channel/0029Vb8mlry8F2pN2kfEZT0L",
}
exec("ICON = SITE_URL + \"icon.png\"", ns)
html = eval("(" + expr + ")", ns)

out = root / "preview-welcome.html"
out.write_text(html, encoding="utf-8")
print("wrote", out, len(html), "chars")
