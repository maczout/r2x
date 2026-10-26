"""Export a solved session: both control charts, and the detail views of the selected stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from r2x.progress import Event
from r2x.record import control_section, stage_section
from r2x.stages import StageSpec
from r2x.worker.identify import StageKeys
from r2x.worker.session import (CONTROL_CHARTS, CONTROL_KEYS, NO_SHEAR_CHARTS, VK_NEXT, VK_PRIOR,
                                R2xError, Session, export_title, wait_until)

STRAIN = NO_SHEAR_CHARTS[0]
assert STRAIN.key == "longitudinal_strain"


@dataclass
class Export:
    stage_count: int
    peak: int                     # the stage Response showed when the solve finished
    stages: list[int]             # stages whose detail views were exported, ascending
    sections: list[tuple[str, bytes]] = field(default_factory=list)  # in record order
    # PNG pictures of the peak stage when asked for: "main-window", then each control chart by
    # its section key and each detail view by its chart key, in screen order.
    pictures: dict[str, bytes] = field(default_factory=dict)


def control_exports(*exports: bytes) -> dict[str, bytes]:
    """Control-chart exports by record section name, in screen order (top first).

    With an axial-only increment both control charts are the same chart; it is kept once.
    """
    out: dict[str, bytes] = {}
    for data in exports:
        key = CONTROL_KEYS[export_title(data)]
        if key in out:
            if out[key] != data:
                raise R2xError(f"both control charts are {key}, with different data")
            continue
        out[key] = data
    return out


def export(session: Session, spec: StageSpec,
           on_event: Callable[[Event], None] = lambda e: None,
           pictures: Path | None = None) -> Export:
    """Solve, then copy the control charts and the detail views of the stages in spec.

    With a pictures folder (scratch space for the helper), also capture the main window and
    every chart as pictures, at the peak, before any paging.
    Raises StageError (from spec.resolve) if spec names a stage past the last one.
    """
    on_event(Event("solving"))
    top, bottom = session.solve()
    controls = control_exports(top, bottom)
    keys = StageKeys(controls)
    n = keys.count
    strain = session.copy_chart(STRAIN)
    peak = keys.identify(strain)
    on_event(Event("solved", count=n, stage=peak))
    targets = spec.resolve(n, peak)

    result = Export(n, peak, targets)
    result.sections += [(control_section(key), data) for key, data in controls.items()]
    if pictures is not None:
        result.pictures = capture_pictures(session, (top, bottom), pictures)

    def export_stage(i: int, strain: bytes):
        result.sections.append((stage_section(i, STRAIN.key), strain))
        for chart in NO_SHEAR_CHARTS[1:]:
            result.sections.append((stage_section(i, chart.key), session.copy_chart(chart)))
        on_event(Event("stage", stage=i, done=targets.index(i) + 1, total=len(targets)))

    # Response opens on the peak stage and shows no stage number. Stages at or above the peak are
    # reached by paging up from it. For any stage below, page down until Response stops at
    # stage 0, then up. Every step is checked against the control curves.
    if targets[0] >= peak:
        at = peak
    else:
        session.press(VK_NEXT, times=n)
        strain = wait_until(lambda: _strain_if_stage(session, keys, 0), 30, "load stage 0", 0.05)
        at = 0
    if at in targets:
        export_stage(at, strain)
    for i in range(at + 1, targets[-1] + 1):
        previous = strain
        session.press(VK_PRIOR)
        strain = wait_until(lambda: _changed(session, previous), 10, f"load stage {i}", 0.005)
        keys.check(strain, i)
        if i in targets:
            export_stage(i, strain)

    if targets[-1] == n - 1:
        # One more page up must not move past the last stage.
        session.press(VK_PRIOR)
        if session.copy_chart(STRAIN) != strain:
            raise R2xError(f"Response has more than the {n} stages on its control curves")
    return result


def capture_pictures(session: Session, control_data: tuple[bytes, bytes],
                     scratch: Path) -> dict[str, bytes]:
    """The main window as it is now, then Copy Chart Picture of each chart. A control chart that
    repeats the other (axial-only increment) is taken once, as in the record."""
    out = {"main-window": session.snapshot(scratch)}
    for chart, data in zip(CONTROL_CHARTS, control_data):
        key = CONTROL_KEYS[export_title(data)]
        if key not in out:
            out[key] = session.copy_picture(chart, scratch)
    for chart in NO_SHEAR_CHARTS:
        out[chart.key] = session.copy_picture(chart, scratch)
    return out


def _strain_if_stage(session: Session, keys: StageKeys, i: int) -> bytes | None:
    data = session.copy_chart(STRAIN)
    return data if keys.matches(data, i) else None


def _changed(session: Session, previous: bytes) -> bytes | None:
    data = session.copy_chart(STRAIN)
    return data if data != previous else None
