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
from r2x.worker.session import export_points

NO_SHEAR = parse_views("no-shear")
NO_SHEAR_KEYS = [c.key for c in BY_NAME["no-shear"].charts]
CHARTS = len(record_order(ALL_VIEWS))       # detail-view sections per stage with every view

REF = Path(__file__).parent / "reference"
RESPONSE = os.environ.get("R2X_RESPONSE_DIR")
PREFIX = Path(os.environ.get("R2X_WINEPREFIX", Path.home() / ".cache/r2x/prefix"))

pytestmark = pytest.mark.skipif(
    not (RESPONSE and all(shutil.which(t) for t in ("wine", "Xvfb", "i686-w64-mingw32-gcc"))),
    reason="needs $R2X_RESPONSE_DIR, wine, Xvfb and mingw-w64")


def reference_sections(case, stages=None, keys=None):
    """Reference files as record sections: stages/056/x.txt -> stage/56/x, and so on; with
    stages or keys, only the detail charts of those stages or record keys."""
    root = REF / case
    out = {}
    for p in sorted(root.rglob("*.txt")):
        parts = p.relative_to(root).parts
        if parts[0] == "control":
            out[f"control/{p.stem}"] = p.read_bytes()
        elif (stages is None or int(parts[1]) in stages) and (keys is None or p.stem in keys):
            out[f"stage/{int(parts[1])}/{p.stem}"] = p.read_bytes()
    return out


def solve(tmp_path, stages, name="Newbeam", report=None, views=ALL_VIEWS, settings=Settings(),
          more_detail=0, source=None, events=None):
    out = tmp_path / f"{name}.r2x.txt"
    header = run_job(source or REF / "newbeam" / "input.r2t", out, Path(RESPONSE), PREFIX,
                     stages=stages, report=report, views=views, settings=settings,
                     more_detail=more_detail, on_event=(events.append if events is not None
                                                        else lambda e: None))
    rec = record.read(out)
    assert rec.header == header
    return rec


def assert_matches(rec, case):
    """Every hand-captured export of the case at the record's stages and in its views is in the
    record, byte for byte, and each detail stage has the charts of the record's views."""
    keys = [c.key for c in record_order(parse_views(rec.header["views"]))]
    ref = reference_sections(case, rec.stages(), keys)
    for name, body in ref.items():
        assert rec.sections.get(name) == body, name
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
    assert rec.sections == reference_sections("newbeam", [56], NO_SHEAR_KEYS)  # 7, no more
    assert list(rec.sections) == ["control/moment_ex", "control/moment_phi", *(
        f"stage/56/{c.key}" for c in BY_NAME["no-shear"].charts)]


def test_newbeam_all_and_a_selection(tmp_path):
    every = solve(tmp_path, ALL, "all")
    assert every.stages() == list(range(60)) and len(every.sections) == 2 + 60 * CHARTS
    assert_matches(every, "newbeam")      # every view at stages 56 and 36, paged to
    assert len(reference_sections("newbeam")) == 2 + 2 * CHARTS
    # with a report: pictures are taken at the peak, before paging to the other stages; and
    # views in another order, or fewer, give the same exports
    some = solve(tmp_path, parse_stages("peak,0-2,59"), "some", report=tmp_path / "some.html",
                 views=parse_views("no-shear,cracking"))
    assert some.header["detail-stages"] == "0-2,56,59"
    assert some.header["views"] == "cracking,no-shear"
    for name, body in some.sections.items():
        assert every.sections[name] == body, name
    # the three inputs, then each view's window
    assert len(report_pictures(tmp_path / "some.html")) == 3 + 2


def test_report_leaves_the_record_unchanged(tmp_path):
    html = tmp_path / "Newbeam.r2x.html"
    rec = solve(tmp_path, PEAK, report=html)
    plain = solve(tmp_path / "..", PEAK, name=f"{tmp_path.name}-plain")
    assert rec.sections == plain.sections
    assert_matches(rec, "newbeam")
    sizes = report_pictures(html)
    # the input screen and two dialogs, then Response's window in each view
    assert len(sizes) == 3 + 4
    assert sizes[0][0] > 1000 and all(w < 600 and h < 500 for w, h in sizes[1:3])
    assert all(s == sizes[0] for s in sizes[3:])             # every window the same size
    page = html.read_text(encoding="utf-8")
    assert "<h2>Outputs at stage 56</h2>" in page and "No picture" not in page
    assert sorted(p.name for p in tmp_path.iterdir()) == ["Newbeam.r2x.html", "Newbeam.r2x.txt"]


def test_report_axial_only(tmp_path):
    """One view asked for: the inputs and one window."""
    html = tmp_path / "axial.html"
    out = tmp_path / "axial.r2x.txt"
    run_job(REF / "newbeam-axial-only" / "saved.r2t", out, Path(RESPONSE), PREFIX, report=html,
            views=NO_SHEAR)
    assert record.read(out).sections == reference_sections("newbeam-axial-only")
    assert len(report_pictures(html)) == 3 + 1


def test_a_shear_example_solves(tmp_path):
    """Since r2x 0.3.0 shear is in scope: one of Response's own shear examples."""
    shear = Path(RESPONSE) / "dm-n1n.rsp"
    if not shear.is_file():
        pytest.skip("no dm-n1n.rsp in the Response folder")
    rec = solve(tmp_path, PEAK, "dm", source=shear)
    assert rec.header["increment"] == "0.00,1.50,1.00"
    assert (rec.header["stage-count"], rec.header["peak-stage"]) == ("30", "25")
    assert [n for n in rec.sections if n.startswith("control/")] == [
        "control/shear_gxy", "control/moment_phi"]
    assert len(rec.sections) == 2 + CHARTS


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
    ("newbeam-axial", Settings(initial=(-2000, 0, 0)),
     {"units": "si", "factors": "1.00,1.00,1.00", "initial": "-2000.00,0.00,0.00",
      "increment": "0.00,1.00,0.00"}),
    ("newbeam-axial-only", Settings(increment=(-1, 0, 0)),
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


# -- shear and More Detail (r2x 0.3.0) -----------------------------------------------------------
# No hand captures yet (tests/reference gains them in Step 3 of the 0.3.0 plan); these rely on
# r2x's own checks: every stage identified from its strain profile, recurring charts the same
# bytes in every view, and each solve's numbers as found under Wine on 2026-10-27.
SHEAR = Settings(increment=(0, 1, 1))


def test_shear_with_moment(tmp_path):
    """Newbeam with M/V = 1 m: Shear-γxy above Moment-φ, opening on its peak shear."""
    events = []
    peak = solve(tmp_path, PEAK, "peak", settings=SHEAR, events=events)
    h = peak.header
    assert (h["increment"], h["stage-count"], h["peak-stage"]) == ("0.00,1.00,1.00", "43", "30")
    assert list(peak.sections)[:2] == ["control/shear_gxy", "control/moment_phi"]
    assert len(peak.sections) == 2 + CHARTS and not [e for e in events if e.kind == "note"]
    every = solve(tmp_path, ALL, "all", settings=SHEAR)
    assert every.stages() == list(range(43)) and len(every.sections) == 2 + 43 * CHARTS
    for name, body in peak.sections.items():
        assert every.sections[name] == body, name
    gxy = export_points(every.control("shear_gxy"))
    assert max(range(43), key=lambda i: gxy[i][1]) == 30          # the peak shear


def test_shear_alone(tmp_path):
    """V alone: Shear-εx below Shear-γxy, and the strain profile stays the same for the first
    stages, so r2x pages by the General view's Shear Strain too (not recorded here)."""
    rec = solve(tmp_path, parse_stages("0-12,peak"), settings=Settings(increment=(0, 0, 1)),
                views=NO_SHEAR)
    h = rec.header
    assert (h["stage-count"], h["peak-stage"], h["detail-stages"]) == ("52", "16", "0-12,16")
    assert list(rec.sections)[:2] == ["control/shear_gxy", "control/shear_ex"]
    assert not [n for n in rec.sections if n.endswith("/shear_strain")]
    assert rec.stage(1, "longitudinal_strain") == rec.stage(9, "longitudinal_strain")


def test_a_peak_its_strain_profile_cannot_tell(tmp_path):
    """Marshall.rsp's curvature at its peak matches four other stages; r2x pages from stage 0
    to tell which it is."""
    source = Path(RESPONSE) / "Marshall.rsp"
    if not source.is_file():
        pytest.skip("no Marshall.rsp in the Response folder")
    events = []
    rec = solve(tmp_path, PEAK, "marshall", source=source, views=NO_SHEAR, events=events)
    assert (rec.header["stage-count"], rec.header["peak-stage"]) == ("40", "34")
    assert [e.text for e in events if e.kind == "note"] == [
        "the stage on screen could be any of stages 34-35,37-39; paging from stage 0 to tell "
        "which"]


def test_an_increment_of_zero(tmp_path):
    """0,0,0 solves the initial load alone: two control points, both that load."""
    rec = solve(tmp_path, ALL, settings=Settings(initial=(0, 100, 0), increment=(0, 0, 0)))
    h = rec.header
    assert (h["increment"], h["stage-count"], h["peak-stage"]) == ("0.00,0.00,0.00", "2", "1")
    phi = export_points(rec.control("moment_phi"))
    assert phi[0] == phi[1] and phi[0][1] == 100.0
    assert rec.stages() == [0, 1]


def test_more_detail(tmp_path):
    """Each press puts a stage between every two up to the peak, keeping the others byte for
    byte; Response stops at 327 stages."""
    plain = solve(tmp_path, PEAK, "plain", views=NO_SHEAR)
    twice = solve(tmp_path, PEAK, "twice", views=NO_SHEAR, more_detail=2)
    h = twice.header
    assert (h["more-detail"], h["stage-count"], h["peak-stage"]) == ("2", "228", "224")
    old = plain.control("moment_phi").split(b"\r\n")
    new = iter(twice.control("moment_phi").split(b"\r\n"))
    assert all(any(line == other for other in new) for line in old)    # in order, unchanged
    assert twice.stage(224, "longitudinal_strain") == plain.stage(56, "longitudinal_strain")
    events = []
    most = solve(tmp_path, PEAK, "most", views=NO_SHEAR, more_detail=5, events=events)
    assert (most.header["more-detail"], most.header["stage-count"]) == ("3", "327")
    assert [e.text for e in events if e.kind == "note"] == [
        "More Detail refined the solve 3 of the 5 times asked: Response refines it no further "
        "than 327 stages"]
    assert solve(tmp_path, PEAK, "max", views=NO_SHEAR, more_detail="max").sections == \
        most.sections
