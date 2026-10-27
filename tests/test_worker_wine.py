"""End-to-end: run Response-2000 under Wine and compare with the hand-captured references.

Runs only when $R2X_RESPONSE_DIR points at a Response-2000 program folder and Wine, Xvfb and
mingw-w64 are installed.
"""
import base64
import os
import re
import shutil
import struct
from pathlib import Path

import pytest

from r2x import record
from r2x.settings import Settings
from r2x.stages import ALL, PEAK, parse_stages
from r2x.views import ALL as ALL_VIEWS, BY_NAME, parse_views, record_order
from r2x.worker.runner import run_job
from r2x.worker.session import OutOfScope

NO_SHEAR = parse_views("no-shear")
CHARTS = len(record_order(ALL_VIEWS))       # detail-view sections per stage with every view

REF = Path(__file__).parent / "reference"
RESPONSE = os.environ.get("R2X_RESPONSE_DIR")
PREFIX = Path(os.environ.get("R2X_WINEPREFIX", Path.home() / ".cache/r2x/prefix"))

pytestmark = pytest.mark.skipif(
    not (RESPONSE and all(shutil.which(t) for t in ("wine", "Xvfb", "i686-w64-mingw32-gcc"))),
    reason="needs $R2X_RESPONSE_DIR, wine, Xvfb and mingw-w64")


def reference_sections(case):
    """Reference files as record sections: stages/056/x.txt -> stage/56/x, and so on."""
    root = REF / case
    out = {}
    for p in sorted(root.rglob("*.txt")):
        parts = p.relative_to(root).parts
        name = (f"control/{p.stem}" if parts[0] == "control"
                else f"stage/{int(parts[1])}/{p.stem}")
        out[name] = p.read_bytes()
    return out


def solve(tmp_path, stages, name="Newbeam", report=None, views=ALL_VIEWS):
    out = tmp_path / f"{name}.r2x.txt"
    header = run_job(REF / "newbeam" / "input.r2t", out, Path(RESPONSE), PREFIX, stages=stages,
                     report=report, views=views)
    rec = record.read(out)
    assert rec.header == header
    return rec


def assert_matches(rec, case):
    """Every hand-captured export of the case is in the record, byte for byte, and each detail
    stage has the charts of the record's views."""
    ref = reference_sections(case)
    for name, body in ref.items():
        assert rec.sections.get(name) == body, name
    keys = [c.key for c in record_order(parse_views(rec.header["views"]))]
    controls = [n for n in ref if n.startswith("control/")]
    assert list(rec.sections) == controls + [f"stage/{i}/{k}" for i in rec.stages() for k in keys]


PNG = re.compile(r'<img src="data:image/png;base64,([A-Za-z0-9+/=]+)"')


def report_pictures(path: Path) -> list[tuple[int, int]]:
    """Width and height of every picture in a report, in page order."""
    sizes = []
    for b64 in PNG.findall(path.read_text(encoding="utf-8")):
        png = base64.b64decode(b64)
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        sizes.append(struct.unpack(">II", png[16:24]))
    return sizes


def test_newbeam_peak_matches_references(tmp_path):
    rec = solve(tmp_path, PEAK)
    assert rec.header["stage-count"] == "60" and rec.header["peak-stage"] == "56"
    assert rec.header["views"] == "general,cracking,reinforcement,no-shear"
    assert_matches(rec, "newbeam")
    assert len(rec.sections) == 2 + CHARTS


def test_no_shear_alone_is_what_r2x_0_1_0_wrote(tmp_path):
    rec = solve(tmp_path, PEAK, views=NO_SHEAR)
    assert rec.header["views"] == "no-shear"
    assert rec.sections == reference_sections("newbeam")   # all 7, nothing else
    assert list(rec.sections) == ["control/moment_ex", "control/moment_phi", *(
        f"stage/56/{c.key}" for c in BY_NAME["no-shear"].charts)]


def test_newbeam_all_and_a_selection(tmp_path):
    every = solve(tmp_path, ALL, "all")
    assert every.stages() == list(range(60)) and len(every.sections) == 2 + 60 * CHARTS
    assert_matches(every, "newbeam")
    # with a report: pictures are taken at the peak, before paging to the other stages; and
    # views in another order, or fewer, give the same exports
    some = solve(tmp_path, parse_stages("peak,0-2,59"), "some", report=tmp_path / "some.html",
                 views=parse_views("no-shear,cracking"))
    assert some.header["detail-stages"] == "0-2,56,59"
    assert some.header["views"] == "cracking,no-shear"
    for name, body in some.sections.items():
        assert every.sections[name] == body, name
    # the control charts, then each view's window and the charts not already shown
    assert len(report_pictures(tmp_path / "some.html")) == 2 + 2 + 7 + 4


def test_report_leaves_the_record_unchanged(tmp_path):
    html = tmp_path / "Newbeam.r2x.html"
    rec = solve(tmp_path, PEAK, report=html)
    plain = solve(tmp_path / "..", PEAK, name=f"{tmp_path.name}-plain")
    assert rec.sections == plain.sections
    assert_matches(rec, "newbeam")
    sizes = report_pictures(html)
    # two control charts, then each view: its window and its charts not shown already
    windows = [s for s in sizes if s[0] > 1000]
    assert len(sizes) == 2 + 4 + CHARTS and len(windows) == 4
    assert all(w == 900 and 500 < h < 800 for w, h in sizes if (w, h) not in windows)
    page = html.read_text(encoding="utf-8")
    assert "No Shear view at stage 56" in page and "No picture" not in page
    assert sorted(p.name for p in tmp_path.iterdir()) == ["Newbeam.r2x.html", "Newbeam.r2x.txt"]


def test_report_axial_only(tmp_path):
    """Both control charts are the same chart: the report shows it once, as the record does."""
    html = tmp_path / "axial.html"
    out = tmp_path / "axial.r2x.txt"
    run_job(REF / "newbeam-axial-only" / "saved.r2t", out, Path(RESPONSE), PREFIX, report=html,
            views=NO_SHEAR)
    assert record.read(out).sections == reference_sections("newbeam-axial-only")
    assert len(report_pictures(html)) == 7


def test_shear_input_is_out_of_scope(tmp_path):
    shear = Path(RESPONSE) / "dm-n1n.rsp"
    if not shear.is_file():
        pytest.skip("no dm-n1n.rsp in the Response folder")
    with pytest.raises(OutOfScope, match="shear"):
        run_job(shear, tmp_path / "dm.r2x.txt", Path(RESPONSE), PREFIX)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("case", ["newbeam-axial", "newbeam-axial-only", "newbeam-csa"])
def test_saved_settings_match_references(tmp_path, case):
    """Response's own Save As stores the case's settings (loads, factors) in saved.r2t, and
    solving that file gives the hand-captured exports. See tests/reference/<case>/README.md."""
    out = tmp_path / f"{case}.r2x.txt"
    run_job(REF / case / "saved.r2t", out, Path(RESPONSE), PREFIX, stages=PEAK)
    assert_matches(record.read(out), case)


FLAGS = [
    ("newbeam-us", Settings(units="us"),
     {"units": "us", "factors": "1.00,1.00,1.00", "initial": "0.00,0.00,0.00",
      "increment": "0.00,0.74,0.00"}),
    ("newbeam-csa", Settings(factors="csa"),
     {"units": "si", "factors": "0.65,0.85,0.90", "initial": "0.00,0.00,0.00",
      "increment": "0.00,1.00,0.00"}),
    ("newbeam-axial", Settings(initial=(-2000, 0)),
     {"units": "si", "factors": "1.00,1.00,1.00", "initial": "-2000.00,0.00,0.00",
      "increment": "0.00,1.00,0.00"}),
    ("newbeam-axial-only", Settings(increment=(-1, 0)),
     {"units": "si", "factors": "1.00,1.00,1.00", "initial": "0.00,0.00,0.00",
      "increment": "-1.00,0.00,0.00"}),
]


@pytest.mark.parametrize("case, settings, effective", FLAGS, ids=[f[0] for f in FLAGS])
def test_settings_match_references(tmp_path, case, settings, effective):
    """Each option, applied to Newbeam through Response's dialogs, gives the case captured by
    hand with the same setting (tests/reference/<case>/README.md)."""
    out = tmp_path / f"{case}.r2x.txt"
    header = run_job(REF / "newbeam" / "input.r2t", out, Path(RESPONSE), PREFIX,
                     settings=settings)
    assert {k: header[k] for k in effective} == effective
    assert_matches(record.read(out), case)


def same_points(a: bytes, b: bytes, tol: float = 0.0011) -> bool:
    """Two exports with the same title and the same points, in any order, within tol."""
    from r2x.worker.session import export_points, export_title
    pa, pb = sorted(export_points(a)), sorted(export_points(b))
    return (export_title(a) == export_title(b) and len(pa) == len(pb)
            and all(abs(x1 - x2) <= tol and abs(y1 - y2) <= tol
                    for (x1, y1), (x2, y2) in zip(pa, pb)))


def test_new_section_matches_file_new(tmp_path):
    """No input: r2x's Quick Define with every default gives exactly what File > New gives on
    Windows (tests/reference/newbeam-filenew)."""
    out = tmp_path / "newbeam.r2x.txt"
    header = run_job(None, out, Path(RESPONSE), PREFIX)
    assert header["input-name"] == "File > New"
    assert "input-sha256" not in header and "template-sha256" not in header
    assert_matches(record.read(out), "newbeam-filenew")


def test_new_section_with_factors(tmp_path):
    """Settings apply to a new section too. There is no hand capture of File > New with CSA
    factors, so this compares with newbeam-csa (opened from a file): the control curves are
    byte-identical; the detail views differ as newbeam-filenew does from newbeam (layer order,
    last digit of some depths), so they are compared as points."""
    out = tmp_path / "newbeam.r2x.txt"
    run_job(None, out, Path(RESPONSE), PREFIX, settings=Settings(factors="csa"))
    rec, ref = record.read(out), reference_sections("newbeam-csa")
    assert set(ref) <= set(rec.sections)
    for name, body in ref.items():
        if name.startswith("control/"):
            assert rec.sections[name] == body, name
        else:
            assert same_points(rec.sections[name], body), name


def test_new_section_records_the_template(tmp_path):
    response = tmp_path / "Response"
    shutil.copytree(RESPONSE, response)
    shutil.copyfile(REF / "newbeam-csa" / "saved.r2t", response / "r2k.r2k")
    header = run_job(None, tmp_path / "new.r2x.txt", response, PREFIX)
    assert header["template-sha256"] == __import__("hashlib").sha256(
        (response / "r2k.r2k").read_bytes()).hexdigest()
    assert header["factors"] == "0.65,0.85,0.90"      # Response loads the template at start
