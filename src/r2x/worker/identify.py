"""Which load stage a detail-view export belongs to.

Response shows no stage number. r2x matches the stage on screen to the control curves through
its Longitudinal Strain export, which is a straight strain profile over the section depth:

- εx, its strain at y = 0 (the reference axis), against the εx of the Moment–εx, Axial Load–εx
  or Shear–εx curve, when there is one. Strain is dimensionless (mm/m or ms), so no units are
  involved.
- its curvature against the Moment–φ curve, when there is one. The units (mrad/m and mm in SI,
  rad/10³ in and in in US units) are read from the axis titles; with units r2x does not know,
  the curvature check is left out.

Without shear in the increment there are both curves, or the εx curve alone (axial-only
increment); with shear, one of them, beside Shear–γxy. Shear–γxy is no key: its γxy is the
average shear strain weighted by shear force (∫ τ γxy b dy / V), which needs the section's width
at each depth, and no export has that (docs/cli.md, Shear and More Detail).

A stage matches when every available check agrees. Several stages can match (a shear solve's
curvature hardly changes near its peak); export.py then tells them apart by their exports.
"""

from __future__ import annotations

import re

from r2x.worker.session import R2xError, export_points

# Units in axis titles, as factors to SI (strain to 1, lengths to m, curvature to 1/m).
STRAIN_UNITS = {"mm/m": 1e-3, "ms": 1e-3}
LENGTH_UNITS = {"mm": 1e-3, "cm": 1e-2, "m": 1.0, "in": 0.0254}
CURVATURE_UNITS = {"mrad/m": 1e-3, "rad/10^3inch": 1.0 / (1000 * 0.0254)}

# Tolerances: the control curves print 3 decimals and the strain export 4, so a correct match is
# within about 0.0006 of εx and 0.001 of curvature; the relative terms cover large values.
EX_TOL = 0.0006
CURVATURE_TOL = 0.002


def axis_unit(data: bytes, axis: str) -> str | None:
    """'X Axis Title : Curvature (mrad/m)' -> 'mrad/m' (axis 'X' or 'Y')."""
    for line in data.decode("latin-1").splitlines():
        head, sep, rest = line.partition(":")
        if sep and head.strip() == f"{axis} Axis Title":
            m = re.search(r"\(([^()]*)\)\s*$", rest.strip())
            return m.group(1).strip() if m else None
    return None


def strain_profile(strain: bytes) -> tuple[float, float, float, float]:
    """(e_top, y_top, e_bot, y_bot) of a Longitudinal Strain export.

    The export is a closed outline: (0, y_top), (e_top, y_top), ..., (e_bot, y_bot), (0, y_bot).
    """
    pts = export_points(strain)
    if len(pts) < 4:
        raise R2xError("Longitudinal Strain export has too few points")
    (e_top, y_top), (e_bot, y_bot) = pts[1], pts[-2]
    if y_top == y_bot:
        raise R2xError("Longitudinal Strain export has no depth")
    return e_top, y_top, e_bot, y_bot


def strain_at_axis(strain: bytes) -> float:
    """εx: the profile's strain at y = 0, in the export's strain units."""
    e_top, y_top, e_bot, y_bot = strain_profile(strain)
    return e_top + (e_bot - e_top) * y_top / (y_top - y_bot)


def strain_curvature(strain: bytes, curvature_unit: str) -> float | None:
    """The profile's curvature in curvature_unit, or None if the units are not known."""
    s = STRAIN_UNITS.get(axis_unit(strain, "X") or "")
    length = LENGTH_UNITS.get(axis_unit(strain, "Y") or "")
    c = CURVATURE_UNITS.get(curvature_unit)
    if s is None or length is None or c is None:
        return None
    e_top, y_top, e_bot, y_bot = strain_profile(strain)
    return (e_bot - e_top) * s / ((y_top - y_bot) * length) / c


EX_KEYS = ("moment_ex", "axial_ex", "shear_ex")     # control charts that plot εx


class StageKeys:
    """Per-stage εx and curvature from the control charts, keyed as in the record
    (moment_ex, moment_phi, axial_ex, shear_gxy, shear_ex)."""

    def __init__(self, controls: dict[str, bytes]):
        points = {k: export_points(v) for k, v in controls.items()}
        counts = {len(p) for p in points.values()}
        if len(counts) > 1:
            raise R2xError("control curves disagree: " + " vs ".join(
                f"{len(p)} points ({k})" for k, p in points.items()))
        ex_key = next((k for k in EX_KEYS if k in controls), None)
        self.ex: list[float] | None = ([x for x, _ in points[ex_key]] if ex_key is not None
                                       else None)
        self.phi: list[float] | None = None
        self.phi_unit = ""
        if "moment_phi" in controls:
            self.phi = [x for x, _ in points["moment_phi"]]
            self.phi_unit = axis_unit(controls["moment_phi"], "X") or ""
        if self.ex is None and self.phi is None:
            raise R2xError(f"no control chart with εx or curvature among {sorted(controls)}")
        if not self.count:
            raise R2xError("the control curves are empty")
        # Stages whose control points are the same, in every chart, as the stage before: an
        # increment of 0,0,0 gives two such stages. Their strain profiles can be the same too.
        rows = list(zip(*points.values()))
        self.repeats = [i for i in range(1, len(rows)) if rows[i] == rows[i - 1]]

    @property
    def count(self) -> int:
        return len(self.ex if self.ex is not None else self.phi)

    def describe(self, strain: bytes) -> tuple[float, float | None]:
        """(εx, curvature or None) of the stage in a Longitudinal Strain export."""
        phi = strain_curvature(strain, self.phi_unit) if self.phi is not None else None
        return strain_at_axis(strain), phi

    def matches(self, strain: bytes, i: int) -> bool:
        ex, phi = self.describe(strain)
        if self.ex is not None and abs(ex - self.ex[i]) > EX_TOL + 1e-4 * abs(self.ex[i]):
            return False
        if phi is not None and abs(phi - self.phi[i]) > CURVATURE_TOL + 1e-4 * abs(self.phi[i]):
            return False
        return True

    def candidates(self, strain: bytes) -> list[int]:
        """Every stage the Longitudinal Strain export could belong to."""
        return [i for i in range(self.count) if self.matches(strain, i)]

    def check(self, strain: bytes, i: int):
        """Raise unless the Longitudinal Strain export belongs to stage i."""
        if not self.matches(strain, i):
            raise R2xError(f"stage {i}: the strain profile gives {self._said(strain)}; the control "
                           f"curves have {self._at(i)}")

    def identify(self, strain: bytes) -> int:
        """The one stage the Longitudinal Strain export belongs to."""
        found = self.candidates(strain)
        if len(found) == 1:
            return found[0]
        if not found:
            raise R2xError(f"the stage on screen ({self._said(strain)}) is not on the control "
                           "curves")
        raise R2xError(f"cannot tell which stage is on screen ({self._said(strain)}): stages "
                       f"{', '.join(map(str, found))} all match")

    def _said(self, strain: bytes) -> str:
        ex, phi = self.describe(strain)
        curvature = f"curvature {phi:.4f} {self.phi_unit}" if phi is not None else ""
        return ", ".join(t for t in (f"εx {ex:.4f}" if self.ex is not None else "", curvature)
                         if t) or "no εx or curvature curve to compare"

    def _at(self, i: int) -> str:
        parts = []
        if self.ex is not None:
            parts.append(f"εx {self.ex[i]:.3f}")
        if self.phi is not None:
            parts.append(f"curvature {self.phi[i]:.3f} {self.phi_unit}")
        return ", ".join(parts)
