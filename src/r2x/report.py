"""The optional HTML report (--report): screenshots for checking by eye that Response was driven
as intended.

One self-contained file with a left-column index and two parts:

- **Inputs**: Response's window before solving (section, materials and loads as Response
  summarises them), and the two dialogs that hold what r2x sets and reads back, units and
  material factors, and loads, as r2x leaves them.
- **Outputs**: Response's window in each captured detail view at the peak stage. The control
  charts are in every window.

No data: the raw record (.r2x.txt) is the result. The screenshots are drawn under Wine and live
only here.

`r2x define` writes the same report, with the inputs only (build_define): Response's input
screen after the step, and the dialog just set. A define after a solve so takes the outputs out,
and the report never shows results for an input that has changed since.

The page reloads itself when the file changes, so one browser tab can follow a session. A page
opened from disk (file://) cannot read files, but it can frame one and be posted to by it: every
second and a half it loads itself, hidden, in a frame, and that copy posts its stamp (a hash of
the page) back and stops loading. A different stamp means the file has changed: reload, which
keeps the place on the page. No server, no files besides the page. Standard library only.
"""

from __future__ import annotations

import base64
import hashlib
import html

from r2x.record import Record
from r2x.views import parse_views

OLD_VIEWS = "no-shear"     # records from r2x 0.1.0 have no views key

# Input screenshots: pictures key, heading, caption. In page order.
INPUTS = (
    ("input/screen", "Input screen",
     "Response-2000's window before solving, with r2x's settings applied"),
    ("input/preferences", "Units and material factors",
     "Options > Preferences, as r2x leaves it before solving"),
    ("input/loading", "Loads",
     "Loads > Sectional Loads (Define Loading), as r2x leaves it before solving"),
)


def window_key(view) -> str:
    """The pictures key of Response's window in a view."""
    return f"window/{view.name}"


def build(rec: Record, pictures: dict[str, bytes]) -> str:
    """The report for a record. pictures holds PNG bytes under the keys of INPUTS and
    window_key(view) for each view in the record; any may be missing."""
    h = rec.header
    peak = int(h["peak-stage"])
    views = parse_views(h.get("views", OLD_VIEWS))
    name = h.get("input-name", "")
    stages = f"0–{int(h['stage-count']) - 1}"
    refined = int(h.get("more-detail", "0") or 0)
    times = {1: "once", 2: "twice"}.get(refined, f"{refined} times")
    detail = f" after More Detail {times}" if refined else ""

    inputs = [(f"in-{key.split('/')[1]}", title, caption, pictures.get(key))
              for key, title, caption in INPUTS]
    outputs = [(f"out-{v.name}", f"{v.response} view",
                f"Response-2000's window in the {v.response} view at stage {peak}",
                pictures.get(window_key(v))) for v in views]

    made = ", ".join(x for x in (f"r2x {h['r2x-version']}" if h.get("r2x-version") else "",
                                 h.get("wine-version", "")) if x)
    sub = (f"Peak stage {peak} of {stages}{detail}. Screenshots for checking by eye that r2x "
           f"drove Response as intended; the data is in the raw record (<code>.r2x.txt</code>).")
    return _page(name, sub, [("inputs", "Inputs", inputs),
                             ("outputs", f"Outputs at stage {peak}", outputs)], made)


def build_define(name: str, step: str, pictures: dict[str, bytes], saved: bytes = b"",
                 made: str = "") -> str:
    """The report after a define step: the inputs only. pictures: "input/screen" (Response's
    window after Save As) and "dialog/1", "dialog/2", ... (the dialog, or a wizard's pages, as
    the step left them)."""
    pages = sorted((k for k in pictures if k.startswith("dialog/")),
                   key=lambda k: int(k.split("/")[1]))
    inputs = [("in-screen", "Input screen", f"Response-2000's window after {step}, as saved",
               pictures.get("input/screen"))]
    for k in pages:
        n = k.split("/")[1]
        title = "Dialog" if len(pages) == 1 else f"Dialog, page {n}"
        inputs.append((f"in-dialog-{n}", title, f"{step}: the dialog as r2x left it before "
                       f"pressing {'OK' if len(pages) == 1 else 'Next or Finish'}",
                       pictures[k]))
    digest = hashlib.sha256(saved).hexdigest()[:12] if saved else ""
    sub = (f"After <code>{html.escape(step)}</code>. Not solved since: <code>solve</code> adds "
           f"the outputs." + (f" File SHA-256 {digest}…" if digest else ""))
    return _page(name, sub, [("inputs", "Inputs", inputs)], made)


def _page(name: str, sub: str, groups, made: str = "") -> str:
    """The page: an index down the left, then each group of screenshots."""
    index = ['<nav class="index" aria-label="Contents"><p class="brand">r2x report</p>',
             f'<p class="case">{html.escape(name)}</p>']
    for anchor, label, items in groups:
        index.append(f'<a class="group" href="#{anchor}">{html.escape(label)}</a><ol>')
        index += [f'<li><a href="#{a}">{html.escape(t)}</a></li>' for a, t, _, _ in items]
        index.append("</ol>")
    index.append("</nav>")

    body = ['<div class="layout">', *index, "<main>"]
    body.append(f'<header><p class="kicker">r2x report · Response-2000 under Wine</p>'
                f"<h1>{html.escape(name)}</h1>"
                f'<p class="sub">{sub}</p></header>')
    for anchor, heading, items in groups:
        body.append(f'<section id="{anchor}"><h2>{html.escape(heading)}</h2>')
        body += [_shot(a, t, c, png) for a, t, c, png in items]
        body.append("</section>")
    body.append('<footer><p>Drawn under Wine; fonts and line weights can differ slightly from '
                f"Windows.{' ' + html.escape(made) + '.' if made else ''} This page reloads "
                "itself when r2x rewrites it.</p></footer>")
    body.append("</main></div>" + _RELOAD + "</body></html>\n")
    text = "".join(body)
    stamp = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return _HEAD.format(title=html.escape(f"{name} · r2x report"), css=_CSS, stamp=stamp) + text


def _png(data: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii")


def _shot(anchor: str, title: str, caption: str, png: bytes | None) -> str:
    body = (f'<img src="{_png(png)}" alt="{html.escape(caption)}">' if png
            else '<div class="missing">No picture</div>')
    return (f'<figure class="shot" id="{anchor}"><h3>{html.escape(title)}</h3>{body}'
            f"<figcaption>{html.escape(caption)}</figcaption></figure>")


# The stamp comes first, and a copy loaded in a frame posts it and stops right there.
_HEAD = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<script>var R2X_STAMP = "{stamp}";
if (window.parent !== window) {{ window.parent.postMessage({{r2xStamp: R2X_STAMP}}, "*");
  window.stop(); }}</script>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}</style>
</head><body>
"""

# Load the page again every 1.5 s in a hidden frame; reload when its stamp differs.
_RELOAD = """<script>(function () {
  if (window.parent !== window) return;
  var frame = null;
  window.addEventListener("message", function (e) {
    if (!e.data || typeof e.data.r2xStamp !== "string") return;
    if (frame) { frame.remove(); frame = null; }
    if (e.data.r2xStamp !== R2X_STAMP) location.reload();
  });
  setInterval(function () {
    if (frame) frame.remove();
    frame = document.createElement("iframe");
    frame.style.display = "none";
    frame.src = location.href.split("#")[0].split("?")[0] + "?r2x=" + Date.now();
    document.body.appendChild(frame);
  }, 1500);
})();</script>"""

_CSS = """
:root {
  --ink: #1c1d1f; --muted: #61656b; --rule: #e2e2de; --panel: #f7f7f4; --accent: #1f4e8c;
  --mono: ui-monospace, "Cascadia Mono", Consolas, "Liberation Mono", monospace;
  color-scheme: light;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { margin: 0; background: #fff; color: var(--ink);
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, "Liberation Sans", sans-serif; }
.layout { display: grid; grid-template-columns: 230px minmax(0, 1fr); max-width: 1500px;
  margin: 0 auto; }
.index { position: sticky; top: 0; align-self: start; height: 100vh; overflow-y: auto;
  padding: 28px 18px 28px 24px; border-right: 1px solid var(--rule); background: var(--panel);
  font-size: 14px; }
.index .brand { margin: 0; color: var(--muted); font-size: 12px; letter-spacing: .04em;
  text-transform: uppercase; }
.index .case { margin: 2px 0 18px; font-weight: 600; overflow-wrap: anywhere; }
.index a { color: var(--ink); text-decoration: none; }
.index a:hover { color: var(--accent); text-decoration: underline; }
.index .group { display: block; margin-top: 14px; font-weight: 600; color: var(--accent); }
.index ol { list-style: none; margin: 4px 0 0; padding: 0 0 0 10px;
  border-left: 2px solid var(--rule); }
.index li { margin: 3px 0; }
main { padding: 0 32px 48px; min-width: 0; }
header { padding-top: 28px; }
.kicker { margin: 0; color: var(--muted); font-size: 13px; letter-spacing: .04em;
  text-transform: uppercase; }
h1 { margin: 4px 0 4px; font-size: 28px; line-height: 1.2; overflow-wrap: anywhere; }
.sub { margin: 0; color: var(--muted); max-width: 70ch; }
h2 { font-size: 21px; margin: 40px 0 8px; padding-bottom: 6px; border-bottom: 2px solid var(--ink); }
h3 { font-size: 16px; margin: 0 0 8px; }
section { scroll-margin-top: 12px; }
figure { margin: 28px 0 0; scroll-margin-top: 12px; }
.shot img { display: block; max-width: 100%; height: auto; border: 1px solid var(--rule); }
figcaption { color: var(--muted); font-size: 13px; margin-top: 6px; }
.missing { display: grid; place-items: center; min-height: 160px; max-width: 900px;
  background: var(--panel); color: var(--muted); border-radius: 6px; }
footer { margin-top: 48px; color: var(--muted); font-size: 13px; border-top: 1px solid var(--rule); }
code { font-family: var(--mono); font-size: .92em; }
@media (max-width: 760px) {
  .layout { display: block; }
  .index { position: static; height: auto; border-right: 0; border-bottom: 1px solid var(--rule);
    padding: 16px; }
  main { padding: 0 16px 32px; }
}
@media print {
  .layout { display: block; }
  .index { display: none; }
  figure { break-inside: avoid; }
}
"""
