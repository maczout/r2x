"""The optional HTML report (--report): the peak stage as Response shows it, next to its data.

One self-contained file: the control charts, then each detail view captured: Response's window
in that view, and each of its charts as Copy Chart Picture draws it, beside a table of its Copy
Chart Data export. A chart that recurs in several views is shown under the first. The pictures
are rendered under Wine and live only here; the raw record stays text-only.
Standard library only.
"""

from __future__ import annotations

import base64
import html
import re
from dataclasses import dataclass, field

from r2x.record import Record
from r2x.views import parse_views

OLD_VIEWS = "no-shear"     # records from r2x 0.1.0 have no views key


def window_key(view) -> str:
    """The pictures key of Response's window in a view."""
    return f"window/{view.name}"

LOAD_UNITS = {"si": ("kN", "kN·m"), "us": ("kip", "kip·ft"), "kgcm": ("ton", "ton·m")}
UNIT_NAMES = {"si": "SI", "us": "US customary", "kgcm": "kg/cm metric"}

# Response writes Greek letters as |letter, drawn in the Symbol font; _c and ^c are a subscript
# and a superscript character.
SYMBOL = dict(zip("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
                  "αβχδεφγηιϕκλμνοπθρστυϖωξψζΑΒΧΔΕΦΓΗΙϑΚΛΜΝΟΠΘΡΣΤΥςΩΞΨΖ"))


def markup(text: str) -> str:
    """Response's chart-title markup as HTML: |e_x -> ε<sub>x</sub>, 10^3 -> 10<sup>3</sup>."""
    out, i = [], 0
    while i < len(text):
        c = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if c == "|" and nxt in SYMBOL:
            out.append(SYMBOL[nxt])
            i += 2
        elif c in "_^" and nxt:
            tag = "sub" if c == "_" else "sup"
            out.append(f"<{tag}>{html.escape(nxt)}</{tag}>")
            i += 2
        else:
            out.append(html.escape(c))
            i += 1
    joined = "".join(out)
    return joined.replace("</sub><sub>", "").replace("</sup><sup>", "")


@dataclass
class Chart:
    """A Copy Chart Data export, read for display."""
    title: str = ""
    x_title: str = ""
    y_title: str = ""
    # (line type, points); a point is the two numbers as exported, or None where Response
    # starts a new line within the series ("New Line").
    series: list[tuple[str, list[tuple[str, str] | None]]] = field(default_factory=list)


def parse_export(data: bytes) -> Chart:
    chart = Chart()
    for line in data.decode("latin-1").splitlines():
        head, sep, rest = line.partition(":")
        name = head.strip()
        if sep and name in ("Title", "X Axis Title", "Y Axis Title") and not chart.series:
            setattr(chart, {"Title": "title", "X Axis Title": "x_title",
                            "Y Axis Title": "y_title"}[name], rest.strip())
        elif sep and name == "Line type":
            chart.series.append((rest.strip(), []))
        elif chart.series and line.strip() == "New Line":
            chart.series[-1][1].append(None)
        elif chart.series and _numbers(line):
            chart.series[-1][1].append(tuple(line.split()))
    return chart


def _numbers(line: str) -> bool:
    fields = line.split()
    if len(fields) != 2:
        return False
    try:
        float(fields[0]), float(fields[1])
    except ValueError:
        return False
    return True


def build(rec: Record, pictures: dict[str, bytes]) -> str:
    """The report for a record whose peak stage has detail views. pictures holds PNG bytes:
    control-chart section keys, window_key(view) for each view, and chart keys; any may be
    missing."""
    h = rec.header
    peak = int(h["peak-stage"])
    views = parse_views(h.get("views", OLD_VIEWS))
    controls = [name.split("/", 1)[1] for name in rec.sections if name.startswith("control/")]
    name = h.get("input-name", "")
    parts = [_HEAD.format(title=html.escape(f"{name} · r2x report"), css=_CSS)]
    parts.append(f'<header><p class="kicker">r2x report · Response-2000 under Wine</p>'
                 f"<h1>{html.escape(name)}</h1>"
                 f'<p class="sub">Peak stage {peak} of {_stage_range(h)}. '
                 f"Pictures as Response draws them; data as it exports it.</p></header><main>")
    parts.append(_settings(h))
    links = [("control", "Control charts")] + [(_anchor(v), f"{v.response} view") for v in views]
    parts.append('<nav class="toc">' + " · ".join(
        f'<a href="#{a}">{html.escape(t)}</a>' for a, t in links) + "</nav>")

    parts.append('<section id="control"><h2>Control charts</h2><p class="note">Every stage, 0 '
                 f'to {int(h["stage-count"]) - 1}.</p>')
    for key in controls:
        parts.append(_panel(rec.control(key), pictures.get(key)))
    parts.append("</section>")

    shown: dict[str, str] = {}      # chart key -> the view it is shown under
    for view in views:
        parts.append(f'<section id="{_anchor(view)}"><h2>{html.escape(view.response)} view at '
                     f"stage {peak}</h2>")
        parts.append(_figure(pictures.get(window_key(view)),
                             f"Response-2000's window in the {view.response} view at stage "
                             f"{peak}", wide=True))
        again = [f'<a href="#{_anchor(c)}">{html.escape(c.title)}</a> '
                 f"(under {html.escape(shown[c.key])})" for c in view.charts if c.key in shown]
        if again:
            parts.append(f'<p class="note">Also in this view: {"; ".join(again)}.</p>')
        for chart in view.charts:
            if chart.key not in shown:
                shown[chart.key] = view.response
                parts.append(_panel(rec.stage(peak, chart.key), pictures.get(chart.key),
                                    _anchor(chart)))
        parts.append("</section>")

    parts.append(_provenance(h))
    parts.append("</main></body></html>\n")
    return "".join(parts)


def _anchor(item) -> str:
    """An id for a view or a chart in the page."""
    return f"view-{item.name}" if hasattr(item, "response") else f"chart-{item.key}"


# -- pieces -------------------------------------------------------------------------------------
def _stage_range(h: dict[str, str]) -> str:
    return f"0–{int(h['stage-count']) - 1}"


def _loads(value: str, units: str) -> str:
    force, moment = LOAD_UNITS.get(units, ("", ""))
    labels = (("N", force), ("M", moment), ("V", force))
    vals = value.split(",")
    if len(vals) != 3:
        return html.escape(value)
    return " · ".join(f"{k} {html.escape(v)} {u}".rstrip() for (k, u), v in zip(labels, vals))


def _settings(h: dict[str, str]) -> str:
    units = h.get("units", "")
    factors = h.get("factors", "").split(",")
    factor_text = (" · ".join(f"{k} {v}" for k, v in zip(("concrete", "steel", "prestress"),
                                                         factors))
                   if len(factors) == 3 else html.escape(h.get("factors", "")))
    items = [
        ("Units", html.escape(UNIT_NAMES.get(units, units))),
        ("Material factors", factor_text),
        ("Initial load", _loads(h.get("initial", ""), units)),
        ("Increment", _loads(h.get("increment", ""), units)),
        ("Load stages", f"{html.escape(h['stage-count'])} ({_stage_range(h)}), peak "
                        f"{html.escape(h['peak-stage'])}"),
    ]
    cells = "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in items)
    return f'<dl class="settings">{cells}</dl>'


def _png(data: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii")


def _figure(png: bytes | None, caption: str, wide: bool = False) -> str:
    cls = "shot wide" if wide else "shot"
    body = (f'<img src="{_png(png)}" alt="{html.escape(caption)}">' if png
            else '<div class="missing">No picture</div>')
    return f'<figure class="{cls}">{body}<figcaption>{html.escape(caption)}</figcaption></figure>'


def _panel(data: bytes, png: bytes | None, anchor: str | None = None) -> str:
    chart = parse_export(data)
    title = markup(chart.title)
    rows = []
    many = len(chart.series) > 1
    for line_type, points in chart.series:
        if many:
            rows.append(f'<tr class="series"><th colspan="2">Line type {html.escape(line_type)}'
                        f"</th></tr>")
        rows += [f"<tr><td>{html.escape(pt[0])}</td><td>{html.escape(pt[1])}</td></tr>" if pt
                 else '<tr class="break"><td colspan="2">new line</td></tr>' for pt in points]
    count = sum(pt is not None for _, points in chart.series for pt in points)
    table = (f'<div class="data"><table><thead><tr><th>{markup(chart.x_title)}</th>'
             f"<th>{markup(chart.y_title)}</th></tr></thead><tbody>{''.join(rows)}</tbody>"
             f"</table></div>")
    raw = (f"<details><summary>Copy Chart Data text ({count} points)</summary>"
           f"<pre>{html.escape(data.decode('latin-1'))}</pre></details>")
    picture = (f'<img src="{_png(png)}" alt="{html.escape(_plain(chart.title))}, as Response '
               f'draws it">' if png else '<div class="missing">No picture</div>')
    ident = f' id="{anchor}"' if anchor else ""
    return (f'<article class="panel"{ident}><h3>{title}</h3><div class="pair">'
            f'<div class="pic">{picture}</div><div class="numbers">{table}{raw}</div>'
            f"</div></article>")


def _plain(text: str) -> str:
    """Response's markup as plain text: |e_x -> εx."""
    text = re.sub(r"\|(.)", lambda m: SYMBOL.get(m.group(1), m.group(1)), text)
    return re.sub(r"[_^](.)", r"\1", text)


def _provenance(h: dict[str, str]) -> str:
    rows = "".join(f"<tr><th>{html.escape(k)}</th><td>{html.escape(v)}</td></tr>"
                   for k, v in h.items())
    return ('<section class="provenance"><h2>Record header</h2>'
            '<p class="note">The data is Response\'s Copy Chart Data, as in the raw record '
            "(<code>.r2x.txt</code>), which is the result; this report is for reading. The "
            "pictures are drawn under Wine and checked by eye against Windows; fonts and line "
            "weights can differ slightly.</p>"
            f'<table class="header">{rows}</table></section>')


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
body { margin: 0; background: #fff; color: var(--ink);
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, "Liberation Sans", sans-serif; }
header, main { max-width: 1180px; margin: 0 auto; padding: 0 24px; }
header { padding-top: 32px; padding-bottom: 8px; }
.kicker { margin: 0; color: var(--muted); font-size: 13px; letter-spacing: .04em;
  text-transform: uppercase; }
h1 { margin: 4px 0 4px; font-size: 30px; line-height: 1.2; overflow-wrap: anywhere; }
.sub { margin: 0; color: var(--muted); }
h2 { font-size: 20px; margin: 40px 0 12px; padding-bottom: 6px; border-bottom: 1px solid var(--rule); }
h3 { font-size: 16px; margin: 0 0 10px; }
.note { color: var(--muted); margin: -4px 0 14px; }
.toc { margin: 18px 0 0; color: var(--muted); }
a { color: var(--accent); }
section > .shot { margin-bottom: 16px; }
.settings { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;
  margin: 20px 0 0; }
.settings div { background: var(--panel); border-radius: 8px; padding: 10px 14px; }
.settings dt { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
.settings dd { margin: 2px 0 0; font-variant-numeric: tabular-nums; }
figure { margin: 0; }
.shot img { display: block; width: 100%; height: auto; border: 1px solid var(--rule); }
figcaption { color: var(--muted); font-size: 13px; margin-top: 6px; }
.panel { border: 1px solid var(--rule); border-radius: 10px; padding: 16px; margin: 0 0 16px;
  break-inside: avoid; }
.pair { display: grid; grid-template-columns: minmax(0, 11fr) minmax(0, 9fr); gap: 16px;
  align-items: start; }
.pic img { display: block; width: 100%; height: auto; border: 1px solid var(--rule); }
.data { max-height: 440px; overflow: auto; border: 1px solid var(--rule); border-radius: 6px; }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }
.data th, .data td { padding: 3px 10px; text-align: right; white-space: nowrap; }
.data thead th { position: sticky; top: 0; background: var(--panel); font-weight: 600;
  border-bottom: 1px solid var(--rule); }
.data td { font-family: var(--mono); font-size: 13px; }
.data tbody tr:nth-child(even) td { background: #fbfbf9; }
.data tr.break td { font-family: inherit; font-size: 12px; color: var(--muted); text-align: left;
  background: #fff; border-top: 1px dashed var(--rule); }
.data tr.series th { text-align: left; color: var(--accent); background: #fff; font-weight: 600;
  padding-top: 8px; }
details { margin-top: 8px; color: var(--muted); font-size: 13px; }
summary { cursor: pointer; }
pre { font-family: var(--mono); font-size: 12px; background: var(--panel); padding: 10px;
  border-radius: 6px; max-height: 320px; overflow: auto; color: var(--ink); }
.missing { display: grid; place-items: center; min-height: 160px; background: var(--panel);
  color: var(--muted); border-radius: 6px; }
.provenance { padding-bottom: 48px; }
.header { font-size: 13px; width: auto; }
.header th { text-align: left; color: var(--muted); font-weight: 500; padding: 4px 16px 4px 0;
  white-space: nowrap; vertical-align: top; }
.header td { font-family: var(--mono); overflow-wrap: anywhere; padding: 4px 0; }
code { font-family: var(--mono); font-size: .92em; }
@media (max-width: 760px) {
  header, main { padding: 0 16px; }
  header { padding-top: 24px; }
  .pair { grid-template-columns: 1fr; }
}
@media print {
  .data, pre { max-height: none; overflow: visible; }
  details { display: none; }
  h2 { break-after: avoid; }
}
"""
