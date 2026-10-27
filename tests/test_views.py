"""The detail-view catalogue (src/r2x/views.json): its own rules, and docs/raw-format.md's table."""
import re
from pathlib import Path

import pytest

from r2x.views import (ALL, BY_NAME, STRAIN_KEY, VIEWS, ViewError, format_views, key_for,
                       parse_views, record_order, views_of)

DOCS = Path(__file__).parent.parent / "docs"


def test_four_views_as_response_names_them():
    assert [(v.name, v.response) for v in VIEWS] == [
        ("general", "General"), ("cracking", "Cracking"), ("reinforcement", "Reinforcement"),
        ("no-shear", "No Shear")]


def test_keys_follow_the_titles():
    for view in VIEWS:
        for chart in view.charts:
            assert chart.key == key_for(chart.title), chart


def test_each_view_lists_cells_once_in_grid_order():
    for view in VIEWS:
        cells = [c.grid for c in view.charts]
        assert cells == sorted(set(cells)), view.name
        assert all(1 <= r <= 3 and 1 <= c <= 3 for r, c in cells)
        assert len({c.key for c in view.charts}) == len(view.charts)


def test_a_key_is_one_chart_everywhere():
    titles = {}
    for view in VIEWS:
        for chart in view.charts:
            assert titles.setdefault(chart.key, chart.title) == chart.title


def test_longitudinal_strain_is_in_every_view_at_the_same_place():
    """The stage checks copy it in whatever view is on screen (worker/export.py)."""
    for view in VIEWS:
        assert [c.grid for c in view.charts if c.key == STRAIN_KEY] == [(1, 2)], view.name


def test_no_shear_is_what_r2x_0_1_0_captured():
    assert [c.key for c in BY_NAME["no-shear"].charts] == [
        "longitudinal_strain", "shrinkage_thermal_strain", "long_reinforcement_stress",
        "long_reinf_stress_at_crack", "longitudinal_concrete_stress"]
    assert [c.key for c in record_order([BY_NAME["no-shear"]])] == \
        [c.key for c in BY_NAME["no-shear"].charts]


def test_record_order():
    keys = [c.key for c in record_order(ALL)]
    assert len(keys) == len(set(keys)) == 21
    assert keys[:2] == ["longitudinal_strain", "transverse_strain"]
    assert keys[-2:] == ["shrinkage_thermal_strain", "longitudinal_concrete_stress"]
    # the order asked for makes no difference
    both = parse_views("no-shear,reinforcement")
    assert record_order(both) == record_order(parse_views("reinforcement,no-shear"))
    assert [c.key for c in record_order(both)][:5] == [
        "longitudinal_strain", "transverse_strain", "long_reinforcement_stress",
        "long_reinf_stress_at_crack", "long_average_bond"]


@pytest.mark.parametrize("text, names", [
    ("all", "general,cracking,reinforcement,no-shear"),
    ("ALL", "general,cracking,reinforcement,no-shear"),
    ("no-shear", "no-shear"),
    ("No-Shear, cracking", "cracking,no-shear"),
    ("cracking,cracking", "cracking"),
])
def test_parse_views(text, names):
    views = parse_views(text)
    assert format_views(views) == names
    assert parse_views(format_views(views)) == views


@pytest.mark.parametrize("text, message", [
    ("mohr", "'mohr' in 'mohr': use all, or any of general, cracking, reinforcement, no-shear"),
    ("no shear", "'no shear'"),
    ("general,", "an empty item"),
    ("all,general", "'all'"),
])
def test_parse_views_errors(text, message):
    with pytest.raises(ViewError, match=re.escape(message)):
        parse_views(text)


def test_raw_format_table_is_the_catalogue():
    """docs/raw-format.md's detail-view table: every chart once, in record order, with its title
    and the views that show it."""
    text = (DOCS / "raw-format.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| `stage/N/([a-z0-9_]+)` \| `([^`]+)` \| ([^|]+) \|$", text, re.M)
    assert rows == [(c.key, c.title, ", ".join(v.response for v in views_of(c.key)))
                    for c in record_order(ALL)]


def test_raw_format_control_table_is_the_catalogue():
    """docs/raw-format.md's control-chart table: every control chart the catalogue knows."""
    from r2x.views import CONTROLS
    text = (DOCS / "raw-format.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| `control/([a-z0-9_]+)` \| `([^`]+)` \|$", text, re.M)
    assert rows == [(c.key, c.title.replace("|", "\\|")) for c in CONTROLS]
    assert len({c.key for c in CONTROLS}) == len({c.title for c in CONTROLS}) == len(CONTROLS)
