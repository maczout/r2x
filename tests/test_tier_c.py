"""tools/tier_c.py, the first verification pass's checks on records alone, on exports captured
by hand on Windows (tests/reference): equilibrium closes, and stages are in order."""
import sys
from pathlib import Path

import pytest

from r2x.record import Record

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "tools"))
import tier_c  # noqa: E402

REF = HERE / "reference"


def reference_record(case: str, header: dict) -> Record:
    root = REF / case
    sections = {f"control/{p.stem}": p.read_bytes() for p in sorted((root / "control").iterdir())}
    for stage in sorted((root / "stages").iterdir()):
        for p in sorted(stage.iterdir()):
            sections[f"stage/{int(stage.name)}/{p.stem}"] = p.read_bytes()
    return Record(1, header, sections)


@pytest.mark.parametrize("case, header", [
    ("newbeam", {"initial": "0,0,0", "increment": "0,1,0", "peak-stage": "56"}),
    ("newbeam-axial", {"initial": "-2000,0,0", "increment": "0,1,0", "peak-stage": "37"}),
    ("newbeam-shear", {"initial": "0,0,0", "increment": "0,1,1", "peak-stage": "30"}),
])
def test_equilibrium_closes_on_windows_exports(case, header):
    rec = reference_record(case, header)
    sec = tier_c.read_section(REF / "newbeam" / "input.r2t")
    loads = tier_c.stage_loads(rec)
    assert not tier_c.stage_order(rec)
    for stage in rec.stages():
        n, m = loads[stage]
        sn, sm, fscale, mscale = tier_c.equilibrium(rec, sec, stage)
        assert abs(sn - n) <= tier_c.TOL * fscale, (stage, n, sn)
        assert abs(sm - m) <= tier_c.TOL * mscale, (stage, m, sm)


def test_section_reads_the_first_cross_section_only():
    sec = tier_c.read_section(REF / "newbeam" / "input.r2t")
    assert sec.widths == [(0.0, 250.0), (600.0, 250.0)] and sec.gross() == (150000.0, 300.0)
    assert [(l.z, l.area) for l in sec.layers] == [(538.95, 300.0), (63.9, 1500.0)]
    assert not sec.prestressed
