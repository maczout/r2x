"""End-to-end: run Response-2000 under Wine and compare with the hand-captured references.

Runs only when $R2X_RESPONSE_DIR points at a Response-2000 program folder and Wine, Xvfb and
mingw-w64 are installed.
"""
import os
import shutil
from pathlib import Path

import pytest

from r2x import record
from r2x.settings import Settings
from r2x.stages import ALL, PEAK, parse_stages
from r2x.worker.runner import run_job
from r2x.worker.session import OutOfScope

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


def solve(tmp_path, stages, name="Newbeam"):
    out = tmp_path / f"{name}.r2x.txt"
    header = run_job(REF / "newbeam" / "input.r2t", out, Path(RESPONSE), PREFIX, stages=stages)
    rec = record.read(out)
    assert rec.header == header
    return rec


def test_newbeam_peak_matches_references(tmp_path):
    rec = solve(tmp_path, PEAK)
    assert rec.header["stage-count"] == "60" and rec.header["peak-stage"] == "56"
    assert rec.sections == reference_sections("newbeam")   # all 7, nothing else


def test_newbeam_all_and_a_selection(tmp_path):
    every = solve(tmp_path, ALL, "all")
    assert every.stages() == list(range(60)) and len(every.sections) == 2 + 60 * 5
    for name, body in reference_sections("newbeam").items():
        assert every.sections[name] == body, name
    some = solve(tmp_path, parse_stages("peak,0-2,59"), "some")
    assert some.header["detail-stages"] == "0-2,56,59"
    for name, body in some.sections.items():
        assert every.sections[name] == body, name


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
    assert record.read(out).sections == reference_sections(case)


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
    assert record.read(out).sections == reference_sections(case)


def same_points(a: bytes, b: bytes, tol: float = 0.0011) -> bool:
    """Two exports with the same title and the same points, in any order, within tol."""
    from r2x.worker.session import export_points, export_title
    pa, pb = sorted(export_points(a)), sorted(export_points(b))
    return (export_title(a) == export_title(b) and len(pa) == len(pb)
            and all(abs(x1 - x2) <= tol and abs(y1 - y2) <= tol
                    for (x1, y1), (x2, y2) in zip(pa, pb)))


@pytest.mark.parametrize("case, settings", [("newbeam", Settings()),
                                            ("newbeam-csa", Settings(factors="csa"))])
def test_new_section_matches_newbeam(tmp_path, case, settings):
    """No input: Quick Define's defaults give Newbeam. The control curves are byte-identical to
    the case opened from input.r2t. The detail views list the reinforcement layers in another
    order and differ in the last digit of some depths (a section defined in memory against one
    read back from a file), so they are compared as points."""
    out = tmp_path / "newbeam.r2x.txt"
    header = run_job(None, out, Path(RESPONSE), PREFIX, settings=settings)
    assert header["input-name"] == "File > New"
    assert "input-sha256" not in header and "template-sha256" not in header
    rec, ref = record.read(out), reference_sections(case)
    assert rec.sections.keys() == ref.keys()
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
