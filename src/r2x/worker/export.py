"""Export every chart at every load stage of a solved session, in the README's output layout."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from r2x.worker.session import (CONTROL_CHARTS, NO_SHEAR_CHARTS, VK_NEXT, VK_PRIOR, R2xError,
                                Session, export_points, strain_curvature, wait_until)

STRAIN = NO_SHEAR_CHARTS[0]
assert STRAIN.key == "longitudinal_strain"

# Curvature check tolerance (mrad/m): the control curve prints 3 decimals and the strain export
# 4 decimals over the section depth, so a correct match is within about 0.001.
CURVATURE_TOL = 0.002


def stage_dir_name(i: int, n: int) -> str:
    return f"{i:0{max(3, len(str(n - 1)))}d}"


def check_stage(strain: bytes, curve: list[tuple[float, float]], i: int):
    """Raise unless the Longitudinal Strain export belongs to stage i of the Moment-phi curve."""
    phi, expected = strain_curvature(strain), curve[i][0]
    if abs(phi - expected) > CURVATURE_TOL + 1e-4 * abs(expected):
        raise R2xError(f"stage {i}: strain profile gives curvature {phi:.4f} mrad/m, "
                       f"Moment-phi curve has {expected:.3f}")


def export_all(session: Session, out: Path, progress: Callable[[str], None] = lambda s: None,
               on_stage: Callable[[int, int], None] = lambda i, n: None) -> int:
    """Solve, then write control/ and stages/NNN/ under out. Returns the number of stages."""
    moment_ex, moment_phi = session.solve()
    curve = export_points(moment_phi)
    n = len(curve)
    if len(export_points(moment_ex)) != n:
        raise R2xError(f"control curves disagree: {len(export_points(moment_ex))} vs {n} points")
    progress(f"solved: {n} load stages")

    (out / "control").mkdir(parents=True, exist_ok=True)
    for chart, data in zip(CONTROL_CHARTS, (moment_ex, moment_phi)):
        (out / "control" / f"{chart.key}.txt").write_bytes(data)

    # Response opens on the maximum-moment stage. Page down until stage 0 (it stops there), then
    # page up through every stage, checking each one against the Moment-phi curve.
    session.press(VK_NEXT, times=n)
    strain = wait_until(lambda: _strain_if_stage(session, curve, 0), 30, "load stage 0", 0.05)
    for i in range(n):
        if i:
            previous = strain
            session.press(VK_PRIOR)
            strain = wait_until(lambda: _changed(session, previous), 10, f"load stage {i}", 0.005)
            check_stage(strain, curve, i)
        d = out / "stages" / stage_dir_name(i, n)
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{STRAIN.key}.txt").write_bytes(strain)
        for chart in NO_SHEAR_CHARTS[1:]:
            (d / f"{chart.key}.txt").write_bytes(session.copy_chart(chart))
        on_stage(i + 1, n)

    # One more page up must not move past the last stage.
    session.press(VK_PRIOR)
    if session.copy_chart(STRAIN) != strain:
        raise R2xError(f"Response has more than the {n} stages on its Moment-phi curve")
    return n


def _strain_if_stage(session: Session, curve, i: int) -> bytes | None:
    data = session.copy_chart(STRAIN)
    try:
        check_stage(data, curve, i)
    except R2xError:
        return None
    return data


def _changed(session: Session, previous: bytes) -> bytes | None:
    data = session.copy_chart(STRAIN)
    return data if data != previous else None
