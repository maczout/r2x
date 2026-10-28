"""r2x define under Wine: each of Response's dialogs driven question by question, and the file
Response saves. Runs where test_worker_wine.py runs.

Files are compared byte for byte where a reference exists (Newbeam), and otherwise by the
attributes the step should change: the tests read the saved XML; r2x itself never does.
"""
import re
import shutil
from pathlib import Path

import pytest

from define_driver import define
from test_worker_wine import REF, pytestmark  # noqa: F401

NEWBEAM = REF / "newbeam" / "input.r2t"
NEWBEAM_DATE = "2026/10/24"


def attrs(xml: str, element: str) -> list[dict]:
    """Every <element ...> in a saved file as {attribute: value} (attributes span lines)."""
    out = []
    for m in re.finditer(rf"<{element}\b([^>]*?)/?>", xml, re.S):
        out.append(dict(re.findall(r'(\w+)\s*="([^"]*)"', m.group(1))))
    return out


@pytest.fixture(scope="module")
def resaved(tmp_path_factory) -> Path:
    """Newbeam as r2x's file chain holds it after one step: opened and saved again by Response
    (its longitudinal layers sorted by depth), here by an Edit General that changes nothing
    but is pressed through. A second open and save leaves it alone."""
    folder = tmp_path_factory.mktemp("resaved")
    f = folder / "newbeam.r2t"
    shutil.copyfile(NEWBEAM, f)
    r = define([], input_file=f, out=f, extra=["--screen", "resave"])
    assert r.status == 0, r.stderr
    again = folder / "again.r2t"
    shutil.copyfile(f, again)
    r = define([], input_file=again, out=again, extra=["--screen", "resave"])
    assert r.status == 0 and again.read_bytes() == f.read_bytes(), r.stderr
    return f


def copy(src: Path, tmp_path: Path, name="section.r2t") -> Path:
    f = tmp_path / name
    shutil.copyfile(src, f)
    return f


# -- D1: Quick Define ---------------------------------------------------------------------------
def test_quick_every_default_is_newbeam(tmp_path):
    out, report = tmp_path / "new.r2t", tmp_path / "new.r2x.html"
    r = define(["quick"], out=out, report=report, date=NEWBEAM_DATE)
    assert r.status == 0, r.stderr
    assert out.read_bytes() == NEWBEAM.read_bytes()     # File > New's Newbeam, date and all
    keys = [q["key"] for q in r.questions]
    assert keys == ["title", "analysis-by", "fc", "fy", "fyt", "prestress", "shape", "dim1",
                    "dim2", "top-number", "top-by-area", "top-bar", "bottom-number",
                    "bottom-by-area", "bottom-bar", "stirrup-type", "stirrup-by-area",
                    "stirrup-bar", "spacing", "cover", "strands", "prestrain"]
    q = {q["key"]: q for q in r.questions}
    assert (q["fc"]["value"], q["fc"]["unit"]) == ("35.0", "MPa")
    assert (q["dim1"]["text"], q["dim1"]["value"], q["dim1"]["unit"]) == ("b", "250", "mm")
    assert q["shape"]["choices"] == ["Rectangle", "Circular", "T-Beam", "I-Beam"]
    assert r.set == [] and r.done["saved"] and r.done["title"] == "New Cross Section"
    page = report.read_text(encoding="utf-8")
    assert page.count("data:image/png;base64,") == 1 + 4        # input screen, four pages
    assert "Outputs" not in page and "R2X_STAMP" in page


def test_quick_t_beam_with_a_bar_response_does_not_know(tmp_path):
    out = tmp_path / "pier-cap.r2t"
    r = define(["quick"], {
        "title": "Pier cap", "analysis-by": "JM", "fc": "40", "fy": "450", "fyt": "420",
        "prestress": "None", "shape": "T-Beam", "dim1": "900", "dim2": "1200", "dim3": "300",
        "dim4": "200", "top-number": "4", "top-bar": "99M", "bar": "20M",
        "bottom-number": "6", "bottom-bar": "30M", "stirrup-type": "Closed Stirrup",
        "stirrup-bar": "15M", "spacing": "300", "cover": "50"}, out=out, date="2026/10/27")
    assert r.status == 0, r.stderr
    # Response offered its Reinforcement Types list for 99M; r2x asked for a bar from it
    (chooser,) = r.asked("bar")
    assert "99M" in chooser["text"] and not chooser["keep"]
    xml = out.read_text()
    beam = attrs(xml, "r3g_beam")[0]
    assert (beam["name"], beam["doneby"], beam["date"]) == ("Pier cap", "JM", "2026/10/27")
    assert attrs(xml, "concrete")[0]["fcp"] == "40.0"
    assert attrs(xml, "shapesection")[0] == {"name": "TBEAM", "par1": "900.0",
                                              "par2": "1200.0", "par3": "300.0",
                                              "par4": "200.0"}
    layers = {l.get("name", "bot"): l for l in attrs(xml, "longreinfx")}
    assert (layers["top"]["num"], layers["top"]["bartitle"]) == ("4", "20M")
    assert {l["bartitle"] for n, l in layers.items() if n != "top"} == {"30M"}
    stirrup = attrs(xml, "transreinfz")[0]
    assert (stirrup["bartitle"], stirrup["pattern"], stirrup["space"]) == ("15M", "3", "300.0")
    assert dict(r.set)["Top, Bar Designation"] == "20M"           # the bar picked, read back
    assert r.done["title"] == "Pier cap"


def test_quick_passes_on_responses_own_corrections(tmp_path):
    """Response takes a negative width and makes it positive, saying so in its View Data
    window after Finish: r2x shows that, and the section is as Response made it."""
    out = tmp_path / "neg.r2t"
    r = define(["quick"], {"dim1": "-100"}, out=out, date=NEWBEAM_DATE)
    assert r.status == 0, r.stderr
    (said,) = r.said
    assert said.startswith("Response reports: Errors in defining Section")
    assert "Negative width found" in said and "Made positive" in said
    assert attrs(out.read_text(), "shapesection")[0]["par1"] == "100.0"


def test_quick_in_us_units_before_it(tmp_path):
    """A session's units come first: Quick Define's defaults are then US ones."""
    out = tmp_path / "us.r2t"
    r = define(["quick"], out=out, date=NEWBEAM_DATE, extra=["--units", "us"])
    assert r.status == 0, r.stderr
    q = {q["key"]: q for q in r.questions}
    assert (q["fc"]["value"], q["fc"]["unit"], q["dim1"]["unit"]) == ("5000", "psi", "in")
    assert attrs(out.read_text(), "r3g_beam")[0]["units"] == "US"


def test_quick_on_an_existing_file_starts_a_new_section(tmp_path):
    f = copy(NEWBEAM, tmp_path)
    r = define(["quick"], {"title": "Second"}, input_file=f, out=f, date=NEWBEAM_DATE)
    assert r.status == 0, r.stderr
    assert not r.asked("response")               # "create a new section?" is answered by r2x
    assert attrs(f.read_text(), "r3g_beam")[0]["name"] == "Second"


def test_giving_up_saves_nothing(tmp_path):
    f = copy(NEWBEAM, tmp_path)
    before = f.read_bytes()
    # Response's question about the duplicate name needs an answer; the input ends instead
    r = define(["long", "add", "top"], {"number": "2"}, input_file=f, out=f)
    assert r.status == 1 and "nothing saved" in r.stderr
    assert f.read_bytes() == before


# -- D1: loads, units, factors -------------------------------------------------------------------
def test_loads_land_where_response_saves_them(tmp_path):
    f = copy(NEWBEAM, tmp_path)
    r = define(["loads"], {"axial": "-2000", "moment-increment": "0", "shear-increment": "1"},
               input_file=f, out=f)
    assert r.status == 0, r.stderr
    assert attrs(f.read_text(), "sectloading")[0] == {"BN": "-2000.0", "MM": "0.000",
                                                      "MV": "1.000"}
    assert dict(r.set) == {"Axial Load, Constant": "-2000.00 kN",
                           "Moment, Increment": "0.00 kNm", "Shear, Increment": "1.00 kN"}


def test_units_and_factors(tmp_path):
    f = copy(NEWBEAM, tmp_path)
    assert define(["units"], {"units": "US Customary"}, input_file=f, out=f).status == 0
    assert define(["factors"], {"concrete": "0.65", "steel": "0.85", "prestress": "0.90"},
                  input_file=f, out=f).status == 0
    xml = f.read_text()
    assert attrs(xml, "r3g_beam")[0]["units"] == "US"
    opts = attrs(xml, "analysisoptions")[0]
    assert (opts["phic"], opts["phis"], opts["phip"]) == ("0.65", "0.85", "0.90")


def test_nothing_changed_saves_nothing(tmp_path):
    f = copy(NEWBEAM, tmp_path)
    before = f.read_bytes()
    r = define(["general"], input_file=f, out=f)
    assert r.status == 0 and r.done == {"saved": False, "seconds": r.done["seconds"]}
    assert f.read_bytes() == before and "nothing changed" in " ".join(r.said)


# -- D2: the editing dialogs ---------------------------------------------------------------------
def test_general(tmp_path, resaved):
    f = copy(resaved, tmp_path)
    r = define(["general"], {"title": "Pier cap", "comments": "North pier",
                             "analysis-by": "JM", "auto-long-spacing": "n",
                             "long-spacing": "300", "centroidal-axis": "n",
                             "moment-axis": "250"}, input_file=f, out=f)
    assert r.status == 0, r.stderr
    beam = attrs(f.read_text(), "r3g_beam")[0]
    assert beam == {"name": "Pier cap\nNorth pier", "doneby": "JM", "date": NEWBEAM_DATE,
                    "smx": "300.0", "axialloc": "250.0"}
    # only the fields answered differently come back
    assert [k for k, _ in r.set] == ["Title", "Comments", "Analysis By",
                                    "Automatic Longitudinal Spacing", "Longitudinal Spacing",
                                    "Centroidal Moment axis", "Moment axis"]


def test_materials_passes_on_responses_question(tmp_path, resaved):
    f = copy(resaved, tmp_path)
    r = define(["materials"], {"fc": "45", "fy": "500", "response": "n"}, input_file=f, out=f)
    assert r.status == 0, r.stderr
    (q,) = r.asked("response")
    assert "overwrite the detailed parameters" in q["text"]
    xml = f.read_text()
    assert attrs(xml, "concrete")[0]["fcp"] == "45.0"
    assert [b["fy"] for b in attrs(xml, "rebar")] == ["400.0", "400.0"]   # No: fy kept
    r = define(["materials"], {"fy": "500", "response": "y"}, input_file=f, out=f)
    assert r.status == 0, r.stderr
    assert [b["fy"] for b in attrs(f.read_text(), "rebar")] == ["500.0"]  # Yes: one type


def test_section(tmp_path, resaved):
    f = copy(resaved, tmp_path)
    r = define(["section"], {"shape": "I-Beam", "dim3": "100", "dim4": "120", "dim5": "150",
                             "dim6": "250"}, input_file=f, out=f)
    assert r.status == 0, r.stderr
    assert [q["text"] for q in r.questions] == ["Shape", "btop", "h", "bweb", "ttop", "tbot",
                                                "bbot"]
    assert attrs(f.read_text(), "shapesection")[0] == {
        "name": "IBEAM", "par1": "250.0", "par2": "600.0", "par3": "100.0", "par4": "120.0",
        "par5": "150.0", "par6": "250.0"}


def test_long_add_then_delete_leaves_the_file_as_it_was(tmp_path, resaved):
    f = copy(resaved, tmp_path)
    r = define(["long", "add", "web"], {"number": "2", "bar": "15M", "depth": "300"},
               input_file=f, out=f)
    assert r.status == 0, r.stderr
    web = [l for l in attrs(f.read_text(), "longreinfx") if l.get("name") == "web"]
    assert web == [{"z": "300.00", "type": "Steel 1", "num": "2", "A": "400.0",
                    "bartitle": "15M", "name": "web"}]
    assert define(["long", "delete", "web"], input_file=f, out=f).status == 0
    assert f.read_bytes() == resaved.read_bytes()


def test_long_modify_reads_every_field_at_the_dialogs_precision(tmp_path, resaved):
    """Modify takes every field as the dialog shows it, as in the GUI: Newbeam's bottom layer
    at 63.90 shows as 64, so changing only its bar count stores 64.00."""
    f = copy(resaved, tmp_path)
    r = define(["long", "modify", "bot"], {"number": "4"}, input_file=f, out=f)
    assert r.status == 0, r.stderr
    bot = [l for l in attrs(f.read_text(), "longreinfx") if "name" not in l][0]
    assert (bot["num"], bot["z"], bot["bartitle"]) == ("4", "64.00", "25M")


def test_long_add_with_a_duplicate_name_asks_as_response_does(tmp_path, resaved):
    """Response asks whether to modify the existing layer, then (the layer selected being
    another) whether to overwrite it; or, with No, adds the layer under a name of its own."""
    f = copy(resaved, tmp_path)
    r = define(["long", "add", "top"], {"number": "2", "response": ["y", "y"]}, input_file=f,
               out=f)
    assert r.status == 0, r.stderr
    first, second = (q["text"] for q in r.asked("response"))
    assert "duplicate name" in first and "overwrite the existing type" in second
    top = [l for l in attrs(f.read_text(), "longreinfx") if l.get("name") == "top"]
    assert len(top) == 1 and top[0]["num"] == "2"
    f = copy(resaved, tmp_path, "no.r2t")
    r = define(["long", "add", "top"], {"number": "2", "response": "n"}, input_file=f, out=f)
    assert r.status == 0, r.stderr
    assert r.said == ["Response named the new layer 'top1'"] and r.set[0] == ["Layer", "top1"]
    names = [l.get("name", "bot") for l in attrs(f.read_text(), "longreinfx")]
    assert sorted(names) == ["bot", "top", "top1"]


def test_trans_modify_with_a_new_name(tmp_path, resaved):
    f = copy(resaved, tmp_path)
    r = define(["trans", "modify", "stirrup"], {"name": "hoops", "spacing": "200",
                                                "bar-type": "Hoop", "response": "y"},
               input_file=f, out=f)
    assert r.status == 0, r.stderr
    (t,) = attrs(f.read_text(), "transreinfz")
    assert (t["name"], t["space"], t["pattern"]) == ("hoops", "200.0", "4")


def test_tendons_add(tmp_path, resaved):
    f = copy(resaved, tmp_path)
    r = define(["tendons", "add", "t1"], {"number": "4", "strand": "S13", "prestrain": "6.5",
                                          "depth": "100", "slope": "0", "type": "Low Relax"},
               input_file=f, out=f)
    assert r.status == 0, r.stderr
    t = [l for l in attrs(f.read_text(), "longreinfx") if l.get("name") == "t1"]
    assert t == [{"z": "100.00", "type": "Low Relax", "num": "4", "A": "396.0",
                  "bartitle": "S13", "dep": "6.50", "name": "t1"}]


def test_show_reads_a_dialog_and_changes_nothing(tmp_path, resaved):
    f = copy(resaved, tmp_path)
    r = define(["long"], input_file=f, show=True)
    assert r.status == 0, r.stderr
    shown = dict(r.shown)
    assert "Layer bot" in shown and "Layer top" in shown
    assert ["  Dist. from Bottom", "64 mm"] in r.shown
    assert f.read_bytes() == resaved.read_bytes()
