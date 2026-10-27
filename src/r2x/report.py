"""The optional HTML report (--report): screenshots for checking by eye that Response was driven
as intended.

One self-contained file with a left-column index and two parts:

- **Inputs**: Response's window before solving (section, materials and loads as Response
  summarises them), and the two dialogs that hold what r2x sets and reads back, units and
  material factors, and loads, as r2x leaves them.
- **Outputs**: Response's window in each captured detail view at the peak stage. The control
  charts are in every window.

No data: the raw record (.r2x.txt) is the result. The screenshots are drawn under Wine and live
only here. Standard library only.
"""

from __future__ import annotations

import base64
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

    index = ['<nav class="index" aria-label="Contents"><p class="brand">r2x report</p>',
             f'<p class="case">{html.escape(name)}</p>']
    for anchor, label, items in (("inputs", "Inputs", inputs),
                                 ("outputs", f"Outputs at stage {peak}", outputs)):
        index.append(f'<a class="group" href="#{anchor}">{html.escape(label)}</a><ol>')
        index += [f'<li><a href="#{a}">{html.escape(t)}</a></li>' for a, t, _, _ in items]
        index.append("</ol>")
    index.append("</nav>")

    parts = [_HEAD.format(title=html.escape(f"{name} · r2x report"), css=_CSS),
             '<div class="layout">', *index, "<main>"]
    parts.append(f'<header><p class="kicker">r2x report · Response-2000 under Wine</p>'
                 f"<h1>{html.escape(name)}</h1>"
                 f'<p class="sub">Peak stage {peak} of {stages}{detail}. Screenshots for '
                 f"checking by eye that r2x drove Response as intended; the data is in the "
                 f"raw record (<code>.r2x.txt</code>).</p></header>")
    for anchor, heading, items in (("inputs", "Inputs", inputs),
                                   ("outputs", f"Outputs at stage {peak}", outputs)):
        parts.append(f'<section id="{anchor}"><h2>{html.escape(heading)}</h2>')
        parts += [_shot(a, t, c, png) for a, t, c, png in items]
        parts.append("</section>")
    made = ", ".join(x for x in (f"r2x {h['r2x-version']}" if h.get("r2x-version") else "",
                                 h.get("wine-version", "")) if x)
    parts.append('<footer><p>Drawn under Wine; fonts and line weights can differ slightly from '
                 f"Windows.{' ' + html.escape(made) + '.' if made else ''}</p></footer>")
    parts.append("</main></div></body></html>\n")
    return "".join(parts)


def _png(data: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii")


def _shot(anchor: str, title: str, caption: str, png: bytes | None) -> str:
    body = (f'<img src="{_png(png)}" alt="{html.escape(caption)}">' if png
            else '<div class="missing">No picture</div>')
    return (f'<figure class="shot" id="{anchor}"><h3>{html.escape(title)}</h3>{body}'
            f"<figcaption>{html.escape(caption)}</figcaption></figure>")


_HEAD = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}</style>
</head><body>
"""

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
