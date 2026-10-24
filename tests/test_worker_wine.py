"""End-to-end: run Response-2000 under Wine and compare with the hand-captured references.

Runs only when $R2X_RESPONSE_DIR points at a Response-2000 program folder and Wine, Xvfb and
mingw-w64 are installed.
"""
import os
import shutil
from pathlib import Path

import pytest

from r2x.worker.runner import run_job

REF = Path(__file__).parent / "reference"
RESPONSE = os.environ.get("R2X_RESPONSE_DIR")

pytestmark = pytest.mark.skipif(
    not (RESPONSE and all(shutil.which(t) for t in ("wine", "Xvfb", "i686-w64-mingw32-gcc"))),
    reason="needs $R2X_RESPONSE_DIR, wine, Xvfb and mingw-w64")


def reference_files(case):
    root = REF / case
    return sorted(p.relative_to(root) for p in root.rglob("*.txt"))


def test_newbeam(tmp_path):
    out = tmp_path / "Newbeam_r2x"
    prefix = Path(os.environ.get("R2X_WINEPREFIX", Path.home() / ".cache/r2x/prefix"))
    manifest = run_job(REF / "newbeam" / "input.r2t", out, Path(RESPONSE), prefix,
                       progress=lambda s: None)
    assert manifest["stage_count"] == 60
    assert len(list((out / "stages").iterdir())) == 60
    for rel in reference_files("newbeam"):
        assert (out / rel).read_bytes() == (REF / "newbeam" / rel).read_bytes(), rel
