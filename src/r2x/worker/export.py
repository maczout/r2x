"""Export a solved session: both control charts, and the detail views of the selected stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from r2x.progress import Event, note
from r2x.record import control_section, stage_section
from r2x.settings import MORE_DETAIL_MAX
from r2x.stages import StageSpec, format_ranges
from r2x.views import ALL, BY_NAME, View, record_order
from r2x.worker.identify import StageKeys
from r2x.worker.session import (CONTROL_KEYS, STRAIN, VK_NEXT, VK_PRIOR, R2xError,
                                Session, export_title, view_charts, wait_until)

GENERAL = BY_NAME["general"]
SHEAR_STRAIN = next(c for c in view_charts(GENERAL) if c.key == "shear_strain")


@dataclass
class Export:
    stage_count: int
    peak: int                     # the stage Response showed when the solve finished
    stages: list[int]             # stages whose detail views were exported, ascending
    sections: list[tuple[str, bytes]] = field(default_factory=list)  # in record order
    # PNG pictures of the peak stage when asked for: "window/NAME", Response's window in each
    # view, taken before any paging.
    pictures: dict[str, bytes] = field(default_factory=dict)
    more_detail: int = 0          # More Detail presses that refined the solve


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


def visit_order(session: Session, views) -> list[View]:
    """The views to go through: the one on screen first (no switch), then the others in
    catalogue order. With all four views that is three switches per stage."""
    current = session.view()
    return sorted(views, key=lambda v: v != current)


# -- telling load stages apart --------------------------------------------------------------------
@dataclass(frozen=True)
class Look:
    """What r2x reads to tell the stage on screen: its Longitudinal Strain export and, in a
    thorough look, the General view's Shear Strain export too."""
    strain: bytes
    shear: bytes | None = None


class Pager:
    """Moves through the load stages one page at a time, checking each against the control
    curves.

    A plain look is the Longitudinal Strain export alone, as without shear it changes from every
    stage to the next. A thorough look adds Shear Strain, from the General view: with shear in
    the increment the strain profile can stay the same for several stages (V alone: εx is 0
    until the section cracks), and so can a solve's two stages with an increment of 0,0,0.
    """

    def __init__(self, session: Session, keys: StageKeys, thorough: bool):
        self.s = session
        self.keys = keys
        self.thorough = thorough

    def look(self) -> Look:
        if not self.thorough:
            return Look(self.s.copy_chart(STRAIN))
        self.s.select_view(GENERAL)
        return Look(self.s.copy_chart(STRAIN), self.s.copy_chart(SHEAR_STRAIN))

    def to_zero(self) -> Look:
        """Page down until Response stops, at stage 0."""
        self.s.press(VK_NEXT, times=self.keys.count)
        return wait_until(lambda: self._if_stage(0), 30, "load stage 0", 0.05)

    def up(self, here: Look, i: int) -> Look:
        """Page up from the stage seen as `here` to stage i, and check it is stage i."""
        self.s.press(VK_PRIOR)
        there = wait_until(lambda: self._changed(here), 10, f"load stage {i}", 0.005)
        self.keys.check(there.strain, i)
        return there

    def at_last(self, here: Look):
        """One more page up from the last stage must not move."""
        self.s.press(VK_PRIOR)
        if self.look() != here:
            raise R2xError(f"Response has more than the {self.keys.count} stages on its control "
                           "curves")

    def find(self, opened: Look, candidates: list[int]) -> tuple[int, Look]:
        """The stage seen as `opened`, among candidates that its strain profile alone cannot
        tell apart: page from stage 0 to the last candidate and compare each candidate's look
        with it. Returns the stage and the look at the last candidate, where it stops."""
        here = self.to_zero()
        same = [0] if 0 in candidates and here == opened else []
        for i in range(1, max(candidates) + 1):
            here = self.up(here, i)
            if i in candidates and here == opened:
                same.append(i)
        if len(same) != 1:
            raise R2xError(f"cannot tell which stage Response showed: its exports match stages "
                           f"{format_ranges(same or candidates)}")
        return same[0], here

    def _if_stage(self, i: int) -> Look | None:
        here = self.look()
        return here if self.keys.matches(here.strain, i) else None

    def _changed(self, previous: Look) -> Look | None:
        here = self.look()
        return here if here != previous else None


def thorough_look(controls: dict[str, bytes], keys: StageKeys) -> bool:
    """Whether the strain profile alone may not change from one stage to the next."""
    return "shear_gxy" in controls or bool(keys.repeats)


def export_views(session: Session, views, stage: int, look: Look) -> dict[str, bytes]:
    """Every chart of these views at the stage on screen, by record key.

    look holds the exports that identified the stage. Every view shows Longitudinal Strain, and
    its export must be the same bytes in each, which also shows the stage did not move when the
    view changed. Any other chart that recurs in several views must be the same bytes in each
    too; it becomes one section. A Shear Strain export taken only to tell stages apart is not
    recorded unless the General view is among the views.
    """
    got = {STRAIN.key: look.strain}
    where = {STRAIN.key: "the stage check"}
    if look.shear is not None:
        got[SHEAR_STRAIN.key], where[SHEAR_STRAIN.key] = look.shear, "the stage check"
    for view in visit_order(session, views):
        session.select_view(view)
        for chart in view_charts(view):
            data = session.copy_chart(chart)
            if chart.key not in got:
                got[chart.key], where[chart.key] = data, f"the {view.response} view"
            elif got[chart.key] != data:
                raise R2xError(f"stage {stage}: {chart.title} in the {view.response} view differs "
                               f"from {where[chart.key]}")
    return got


def refine(session: Session, top: bytes, bottom: bytes, presses: int | str,
           on_event: Callable[[Event], None]) -> tuple[bytes, bytes, int]:
    """Solve > More Detail, `presses` times or (MORE_DETAIL_MAX) until Response refines no
    further. Returns the control charts' exports after it and the presses that took effect."""
    want = None if presses == MORE_DETAIL_MAX else int(presses)
    done = 0
    while want is None or done < want:
        press = done + 1
        after = session.more_detail(
            bottom, on_count=lambda n: on_event(Event("refining", count=n, done=press)))
        if after is None:
            break
        top, bottom = after
        done = press
    if want is not None and done < want:
        n = StageKeys(control_exports(top, bottom)).count
        on_event(note(f"More Detail refined the solve {done} of the {want} times asked: "
                      f"Response refines it no further than {n} stages"))
    return top, bottom, done


def export(session: Session, spec: StageSpec, views=ALL,
           on_event: Callable[[Event], None] = lambda e: None,
           pictures: Path | None = None, more_detail: int | str = 0) -> Export:
    """Solve (and refine with More Detail), then copy the control charts and the detail views
    of the stages in spec.

    With a pictures folder (scratch space for the helper), also capture Response's window in
    each view, at the peak, before any paging.
    Raises StageError (from spec.resolve) if spec names a stage past the last one.
    """
    if not views:
        raise R2xError("no detail views to capture")
    on_event(Event("solving"))
    top, bottom = session.solve(on_count=lambda n: on_event(Event("solving", count=n)))
    applied = 0
    if more_detail:
        top, bottom, applied = refine(session, top, bottom, more_detail, on_event)
    controls = control_exports(top, bottom)
    keys = StageKeys(controls)
    n = keys.count
    pager = Pager(session, keys, thorough_look(controls, keys))

    result = Export(n, -1, [], more_detail=applied)
    result.sections += [(control_section(key), data) for key, data in controls.items()]
    if pictures is not None:
        result.pictures = capture_windows(session, views, pictures)

    # Response opens on the peak stage and shows no stage number. If its strain profile matches
    # several stages, page from stage 0 and compare (Pager.find).
    opened = pager.look()
    candidates = keys.candidates(opened.strain)
    if len(candidates) > 1 and not pager.thorough:
        pager.thorough = True
        opened = pager.look()
    if not candidates:
        keys.identify(opened.strain)          # raises, saying what the profile gives
    if len(candidates) == 1:
        peak = at = candidates[0]
        here = opened
    else:
        on_event(note(f"the stage on screen could be any of stages {format_ranges(candidates)}; "
                      "paging from stage 0 to tell which"))
        peak, here = pager.find(opened, candidates)
        at = max(candidates)
    on_event(Event("solved", count=n, stage=peak))
    targets = spec.resolve(n, peak)
    result.peak, result.stages = peak, targets
    order = [c.key for c in record_order(views)]

    def export_stage(i: int, look: Look):
        got = export_views(session, views, i, look)
        result.sections.extend((stage_section(i, key), got[key]) for key in order)
        on_event(Event("stage", stage=i, done=targets.index(i) + 1, total=len(targets)))

    # Stages at or above the stage on screen are reached by paging up from it. For any stage
    # below, page down until Response stops at stage 0, then up. Every step is checked against
    # the control curves. Paging works in any view, and changing the view keeps the stage, so
    # one pass covers every view.
    if targets[0] < at:
        here, at = pager.to_zero(), 0
    if at in targets:
        export_stage(at, here)
    for i in range(at + 1, targets[-1] + 1):
        here = pager.up(here, i)
        if i in targets:
            export_stage(i, here)
    if targets[-1] == n - 1:
        pager.at_last(here)
    return result


def capture_windows(session: Session, views, scratch: Path) -> dict[str, bytes]:
    """Response's window in each view, as it is on screen, the view on screen first."""
    out: dict[str, bytes] = {}
    for view in visit_order(session, views):
        session.select_view(view)
        out[f"window/{view.name}"] = session.snapshot(scratch, settled=True)
    return out
