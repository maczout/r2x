"""Parsing and stage-check logic, against the Newbeam reference exports (no Wine needed)."""
from pathlib import Path

import pytest

from r2x.worker.export import check_stage, stage_dir_name
from r2x.worker.session import (CONTROL_CHARTS, NO_SHEAR_CHARTS, R2xError, export_points,
                                export_title, strain_curvature)

REF = Path(__file__).parent / "reference" / "newbeam"


def read(rel):
    return (REF / rel).read_bytes()


def test_titles_match_chart_table():
    assert export_title(read("control/moment_ex.txt")) == CONTROL_CHARTS[0].title
    assert export_title(read("control/moment_phi.txt")) == CONTROL_CHARTS[1].title
    for chart in NO_SHEAR_CHARTS:
        assert export_title(read(f"stages/056/{chart.key}.txt")) == chart.title


def test_control_curves_have_60_points():
    assert len(export_points(read("control/moment_ex.txt"))) == 60
    assert len(export_points(read("control/moment_phi.txt"))) == 60


def test_peak_stage_is_56():
    curve = export_points(read("control/moment_phi.txt"))
    strain = read("stages/056/longitudinal_strain.txt")
    assert strain_curvature(strain) == pytest.approx(40.389, abs=0.001)
    check_stage(strain, curve, 56)
    with pytest.raises(R2xError):
        check_stage(strain, curve, 55)


def test_stage_dir_name():
    assert stage_dir_name(0, 60) == "000"
    assert stage_dir_name(1234, 2000) == "1234"
