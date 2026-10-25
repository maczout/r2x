"""Export a solved session: both control charts, and the detail views of the selected stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from r2x.progress import Event
from r2x.record import control_section, stage_section
from r2x.stages import StageSpec
from r2x.worker.session import (CONTROL_CHARTS, NO_SHEAR_CHARTS, VK_NEXT, VK_PRIOR, R2xError,
                                Session, curvature_matches, export_points, identify_stage,
                                strain_curvature, wait_until)

STRAIN = NO_SHEAR_CHARTS[0]
assert STRAIN.key == "longitudinal_strain"


@dataclass
class Export:
    stage_count: int
    peak: int                     # the stage Response showed when the solve finished
    stages: list[int]             # stages whose detail views were exported, ascending
    sections: list[tuple[str, bytes]] = field(default_factory=list)  # in record order


def check_stage(strain: bytes, curve: list[tuple[float, float]], i: int):
    """Raise unless the Longitudinal Strain export belongs to stage i of the Moment-phi curve."""
    phi, expected = strain_curvature(strain), curve[i][0]
    if not curvature_matches(phi, expected):
        raise R2xError(f"stage {i}: strain profile gives curvature {phi:.4f} mrad/m, "
                       f"Moment-phi curve has {expected:.3f}")


def export(session: Session, spec: StageSpec,
           on_event: Callable[[Event], None] = lambda e: None) -> Export:
    """Solve, then copy the control charts and the detail views of the stages in spec.

    Raises StageError (from spec.resolve) if spec names a stage past the last one.
    """
    on_event(Event("solving"))
    moment_ex, moment_phi = session.solve()
    curve = export_points(moment_phi)
    n = len(curve)
    if len(export_points(moment_ex)) != n:
        raise R2xError(f"control curves disagree: {len(export_points(moment_ex))} vs {n} points")
    strain = session.copy_chart(STRAIN)
    peak = identify_stage(strain, curve)
    on_event(Event("solved", count=n, stage=peak))
    targets = spec.resolve(n, peak)

    result = Export(n, peak, targets)
    result.sections += [(control_section(c.key), data)
                        for c, data in zip(CONTROL_CHARTS, (moment_ex, moment_phi))]

    def export_stage(i: int, strain: bytes):
        result.sections.append((stage_section(i, STRAIN.key), strain))
        for chart in NO_SHEAR_CHARTS[1:]:
            result.sections.append((stage_section(i, chart.key), session.copy_chart(chart)))
        on_event(Event("stage", stage=i, done=targets.index(i) + 1, total=len(targets)))

    # Response opens on the peak stage and shows no stage number. Stages at or above the peak are
    # reached by paging up from it. For any stage below, page down until Response stops at
    # stage 0, then up. Every step is checked against the Moment-phi curve.
    if targets[0] >= peak:
        at = peak
    else:
        session.press(VK_NEXT, times=n)
        strain = wait_until(lambda: _strain_if_stage(session, curve, 0), 30, "load stage 0", 0.05)
        at = 0
    if at in targets:
        export_stage(at, strain)
    for i in range(at + 1, targets[-1] + 1):
        previous = strain
        session.press(VK_PRIOR)
        strain = wait_until(lambda: _changed(session, previous), 10, f"load stage {i}", 0.005)
        check_stage(strain, curve, i)
        if i in targets:
            export_stage(i, strain)

    if targets[-1] == n - 1:
        # One more page up must not move past the last stage.
        session.press(VK_PRIOR)
        if session.copy_chart(STRAIN) != strain:
            raise R2xError(f"Response has more than the {n} stages on its Moment-phi curve")
    return result


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
