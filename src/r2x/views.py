"""The detail views r2x captures, and their charts: the catalogue in views.json.

Response-2000 shows a solved section as a grid of nine charts, in one of several views chosen
from a list beside the control charts. views.json records, for each view r2x captures, which
grid cells hold a chart with a data export, its title and its record key. The same file tells
tests/reference/capture.ps1 what to ask for. Standard library only.

The --views option:

    all                               every view below (the default)
    general,cracking,reinforcement,no-shear   any of them, in any order, separated by commas

Records list the views in the catalogue's order whatever order they were asked for in, and a
chart that recurs in several views (Longitudinal Strain is in all of them) is one section.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

STRAIN_KEY = "longitudinal_strain"   # in every view; it identifies the stage on screen


class ViewError(ValueError):
    """A --views value that names no view r2x knows."""


@dataclass(frozen=True)
class ViewChart:
    key: str               # record section name: stage/N/KEY
    title: str             # the export's "Title :" line
    grid: tuple[int, int]  # (row, column) in the nine-chart grid


@dataclass(frozen=True)
class ControlChart:
    key: str               # record section name: control/KEY
    title: str             # the export's "Title :" line


@dataclass(frozen=True)
class View:
    name: str                       # r2x's name, as --views takes it
    response: str                   # its name in Response's view list
    charts: tuple[ViewChart, ...]   # grid order: row by row


def key_for(title: str) -> str:
    """The record key a chart title gives: 'Long. Reinf Stress at Crack' -> 'long_reinf_stress_
    at_crack'. The catalogue stores the keys; tests check they follow this rule."""
    return re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")


def _load() -> tuple[tuple[View, ...], tuple[ControlChart, ...]]:
    data = json.loads(Path(__file__).with_name("views.json").read_text(encoding="utf-8"))
    views = tuple(View(v["name"], v["response"],
                       tuple(ViewChart(c["key"], c["title"], tuple(c["grid"]))
                             for c in v["charts"]))
                  for v in data["views"])
    return views, tuple(ControlChart(c["key"], c["title"]) for c in data["controls"])


VIEWS, CONTROLS = _load()   # the detail views; the control charts Response can show
BY_NAME = {v.name: v for v in VIEWS}
ALL = VIEWS


def parse_views(text: str) -> tuple[View, ...]:
    """'all' or a comma-separated list of view names -> the views, in catalogue order."""
    names = [t.strip().lower() for t in str(text).split(",")]
    if names == ["all"]:
        return ALL
    unknown = [n for n in names if n not in BY_NAME]
    if unknown:
        what = "an empty item" if unknown[0] == "" else repr(unknown[0])
        raise ViewError(f"{what} in {text!r}: use all, or any of "
                        f"{', '.join(v.name for v in VIEWS)}")
    return tuple(v for v in VIEWS if v.name in names)


def format_views(views) -> str:
    """Canonical form, as the record header's views key holds it; parse_views reads it back."""
    names = {v.name for v in views}
    return ",".join(v.name for v in VIEWS if v.name in names)


def record_order(views) -> list[ViewChart]:
    """Each chart of these views once, in record order: the views in catalogue order, each
    view's charts row by row, a chart taking its place from the first view that has it."""
    names = {v.name for v in views}
    out: dict[str, ViewChart] = {}
    for view in VIEWS:
        if view.name in names:
            for chart in view.charts:
                out.setdefault(chart.key, chart)
    return list(out.values())


def views_of(key: str) -> list[View]:
    """The views that show the chart with this record key."""
    return [v for v in VIEWS if any(c.key == key for c in v.charts)]
