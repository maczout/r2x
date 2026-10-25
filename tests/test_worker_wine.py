"""End-to-end: run Response-2000 under Wine and compare with the hand-captured references.

Runs only when $R2X_RESPONSE_DIR points at a Response-2000 program folder and Wine, Xvfb and
mingw-w64 are installed.
"""
import os
import shutil
from pathlib import Path

import pytest

from r2x import record
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


@pytest.mark.parametrize("case", ["newbeam-axial", "newbeam-csa"])
def test_saved_settings_match_references(tmp_path, case):
    """Response's own Save As stores the case's settings (loads, factors) in saved.r2t, and
    solving that file gives the hand-captured exports. See tests/reference/<case>/README.md."""
    out = tmp_path / f"{case}.r2x.txt"
    run_job(REF / case / "saved.r2t", out, Path(RESPONSE), PREFIX, stages=PEAK)
    assert record.read(out).sections == reference_sections(case)
