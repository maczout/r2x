"""python tools/tier_c.py RECORD SECTION [RECORD SECTION ...] — checks on records alone.

Tier C of the first verification pass (docs/risk-register.md): checks that need no oracle, only
the record and the section's file. They catch a wrong stage or garbage, not a subtle difference
from Response on Windows. A prototype: plain reinforced sections (no tendons), SI units.

- **Stage order** (S7): up to the peak, the bottom control chart's deformation (curvature for
  a moment, εx for an axial load alone, γxy or εx for shear alone) moves one way from stage to
  stage. Response steps the deformation and finds the load, so a stage out of order shows as a
  reversal. (εx at the centroid can reverse as a section cracks, and a shear failure can
  unload after its peak: neither is checked.)
- **Equilibrium** (S11): at each exported stage, the concrete stress (Longitudinal Concrete
  Stress, integrated over the section's width, less the bars' area: Response's concrete is
  net of the bars) and the bars' average stress (Long. Reinforcement Stress, times each
  layer's area) add up to the stage's N, and their moment about the export's depth origin
  (the gross section's centroid) to its M. N and M at a stage
  come from the control chart and the header's loads.
- **Squash load** (S11): with an axial increment alone, the largest compression against
  f'c (Ag − As) + fy As, as a ratio for judging, not a pass or fail.
- **Repeat** (S4): `--same A B` says whether two records of one solve have the same sections.

The section's file is read for the widths (sectionSOLID: height and width, from the bottom) and
the layers (longreinfx: height z and area A). r2x itself never reads it; this tool belongs to
verification, and later to the clone. Standard library only, and r2x.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from r2x import record                                      # noqa: E402
from r2x.worker.session import export_points                # noqa: E402

# Tolerances, as a share of the internal forces (the sum of |force| over the concrete and the
# bars, and of |force × lever arm| for the moment): the exports print stresses at layer points
# to three decimals, and integrating between the points loses a little. Checked on 2026-11-07:
# Newbeam at every stage, under N, V and N with V, and Marshall.rsp, all within 0.5 %.
TOL = 0.01


@dataclass
class Layer:
    z: float          # height from the bottom, mm
    area: float       # mm², the layer's total


@dataclass
class Section:
    widths: list[tuple[float, float]]     # (height from the bottom, width), mm, bottom first
    layers: list[Layer]
    fc: float
    fy: float
    prestressed: bool

    def width(self, z: float) -> float:
        pts = self.widths
        for (z0, b0), (z1, b1) in zip(pts, pts[1:]):
            if z0 <= z <= z1:
                return b0 if z1 == z0 else b0 + (b1 - b0) * (z - z0) / (z1 - z0)
        return 0.0

    def gross(self) -> tuple[float, float]:
        """Area and centroid height of the concrete outline, mm² and mm."""
        a = m = 0.0
        for (z0, b0), (z1, b1) in zip(self.widths, self.widths[1:]):
            dz = z1 - z0
            a += (b0 + b1) / 2 * dz
            m += dz * (b0 * (2 * z0 + z1) + b1 * (z0 + 2 * z1)) / 6
        return a, m / a


def attrs(xml: str, element: str) -> list[dict[str, str]]:
    return [dict(re.findall(r'(\w+)\s*="([^"]*)"', m.group(1)))
            for m in re.finditer(rf"<{element}\b([^>]*?)/?>", xml, re.S)]


def read_section(path: Path) -> Section:
    """The first cross-section in the file, the one Response opens (an .rsp can hold several)."""
    xml = path.read_text(encoding="utf-8", errors="replace")
    xml = re.search(r"<r3g_beam\b.*?</r3g_beam>", xml, re.S).group(0)
    body = re.search(r"<sectionSOLID\s*>(.*?)</sectionSOLID>", xml, re.S).group(1)
    widths = []
    for line in body.strip().splitlines():
        p = line.split()
        widths.append((float(p[0]), float(p[1])))
    widths.sort()
    layers, prestressed = [], False
    for a in attrs(xml, "longreinfx"):
        if "dep" in a:
            prestressed = True
        layers.append(Layer(float(a["z"]), float(a["A"])))
    fc = float(attrs(xml, "concrete")[0]["fcp"])
    fy = float(attrs(xml, "rebar")[0]["fy"])
    return Section(widths, layers, fc, fy, prestressed)


# -- loads at a stage ---------------------------------------------------------------------------
def three(text: str) -> tuple[float, float, float]:
    n, m, v = (float(x) for x in text.split(","))
    return n, m, v


def stage_loads(rec: record.Record) -> list[tuple[float, float]]:
    """(N, M) at every stage, from the bottom control chart's load and the header's loads."""
    n0, m0, v0 = three(rec.header.get("initial", "0,0,0"))
    dn, dm, dv = three(rec.header.get("increment", "0,1,0"))
    controls = [k.split("/", 1)[1] for k in rec.sections if k.startswith("control/")]
    bottom = controls[-1]
    loads = [y for _, y in export_points(rec.control(bottom))]
    if bottom.startswith("moment"):
        lam = [(m - m0) / dm for m in loads] if dm else None
    elif bottom.startswith("shear"):
        lam = [(v - v0) / dv for v in loads] if dv else None
    else:
        lam = [(n - n0) / dn for n in loads] if dn else None
    if lam is None:
        return [(n0, m0)] * len(loads)
    out = []
    for i, l in enumerate(lam):
        n, m = n0 + l * dn, m0 + l * dm
        if bottom.startswith("moment"):
            m = loads[i]
        elif bottom.startswith("axial"):
            n = loads[i]
        out.append((n, m))
    return out


# -- checks -------------------------------------------------------------------------------------
def stage_order(rec: record.Record) -> list[str]:
    key = [k for k in rec.sections if k.startswith("control/")][-1]       # the bottom chart
    peak = int(rec.header["peak-stage"])
    xs = [x for x, _ in export_points(rec.sections[key])][1:peak + 1]     # from stage 1
    steps = [b - a for a, b in zip(xs, xs[1:]) if b != a]
    if not steps:
        return []
    sign = 1 if sum(1 for d in steps if d > 0) >= len(steps) / 2 else -1
    back = [i + 2 for i, (a, b) in enumerate(zip(xs, xs[1:])) if (b - a) * sign < 0]
    return [f"{key}: deformation reverses before the peak at stage(s) {back[:8]}"] if back \
        else []


def concrete_at(conc: list[tuple[float, float]], y: float) -> float:
    """The concrete stress at depth y, between the export's points (bottom up)."""
    for (s0, y0), (s1, y1) in zip(conc, conc[1:]):
        if y0 <= y <= y1 and y1 > y0:
            return s0 + (s1 - s0) * (y - y0) / (y1 - y0)
    return 0.0


def equilibrium(rec: record.Record, sec: Section, stage: int) -> tuple[float, float, float,
                                                                     float]:
    """(N, M) from the stresses at a stage, kN and kNm: the concrete's integrated over the
    width, plus each layer's area times its bars' average stress; M about the export's depth
    origin (the gross section's centroid), compression on top positive. Then the scales:
    the sums of |force| and of |force × lever arm|."""
    _, zbar = sec.gross()
    conc = export_points(rec.stage(stage, "longitudinal_concrete_stress"))
    if conc[0][1] > conc[-1][1]:
        conc = conc[::-1]                             # bottom up
    force = moment = 0.0                              # N, and N·mm about y = 0
    abs_force = abs_moment = 0.0
    for (s0, y0), (s1, y1) in zip(conc, conc[1:]):
        dy = y1 - y0
        if dy <= 0:
            continue
        f0, f1 = s0 * sec.width(y0 + zbar), s1 * sec.width(y1 + zbar)     # N/mm
        df = (f0 + f1) / 2 * dy
        dm = dy * (f0 * (2 * y0 + y1) + f1 * (y0 + 2 * y1)) / 6
        force, moment = force + df, moment + dm
        abs_force, abs_moment = abs_force + abs(df), abs_moment + abs(dm)
    bars = export_points(rec.stage(stage, "long_reinforcement_stress"))
    bands = [(min(y0, y1), max(y0, y1), s0) for (s0, y0), (s1, y1) in zip(bars, bars[1:])
             if s0 == s1 and s0 != 0 and y0 != y1]
    for layer in sec.layers:
        y = layer.z - zbar
        s = next((st for lo, hi, st in bands if lo - 0.5 <= y <= hi + 0.5), 0.0)
        sc = concrete_at(conc, y)                     # the concrete the bars displace
        force += (s - sc) * layer.area
        moment += (s - sc) * layer.area * y
        abs_force += abs(s * layer.area)
        abs_moment += abs(s * layer.area * y)
    return force / 1000, -moment / 1e6, abs_force / 1000, abs_moment / 1e6


def check_record(path: Path, section: Path) -> bool:
    rec = record.read(path)
    sec = read_section(section)
    ok = True
    print(f"{path.name} ({section.name}): {rec.header.get('stage-count')} stages, "
          f"peak {rec.header.get('peak-stage')}, increment {rec.header.get('increment')}")
    for p in stage_order(rec):
        print(f"  CHECK stage order: {p}")
        ok = False
    if rec.header.get("units", "si") != "si":
        print("  skipped: equilibrium in SI units only (prototype)")
        return ok
    if sec.prestressed:
        print("  skipped: equilibrium for sections without tendons only (prototype)")
        return ok
    loads = stage_loads(rec)
    for stage in rec.stages():
        n, m = loads[stage]
        try:
            sn, sm, fscale, mscale = equilibrium(rec, sec, stage)
        except KeyError:
            continue                                  # the view with the stresses not captured
        n_ok = abs(sn - n) <= TOL * max(fscale, 1.0)
        m_ok = abs(sm - m) <= TOL * max(mscale, 1.0)
        flag = "ok   " if n_ok and m_ok else "CHECK"
        ok &= n_ok and m_ok
        print(f"  {flag} stage {stage:3d}: N {n:9.1f} kN, stresses {sn:9.1f} "
              f"({100 * abs(sn - n) / max(fscale, 1):.2f} %); M {m:8.1f} kNm, stresses "
              f"{sm:8.1f} ({100 * abs(sm - m) / max(mscale, 1):.2f} %)")
    increment = three(rec.header.get("increment", "0,1,0"))
    if increment[0] and not increment[1] and not increment[2]:
        ag, _ = sec.gross()
        as_ = sum(l.area for l in sec.layers)
        p0 = (sec.fc * (ag - as_) + sec.fy * as_) / 1000
        peak = int(rec.header["peak-stage"])
        npeak = loads[peak][0]
        fc_eff = (abs(npeak) - sec.fy * as_ / 1000) * 1000 / (ag - as_)
        print(f"  squash load: {npeak:.1f} kN at the peak against f'c (Ag - As) + fy As = "
              f"{-p0:.1f} kN: ratio {abs(npeak) / p0:.3f}; with the bars at fy, the "
              f"concrete carries {fc_eff:.1f} MPa = {fc_eff / sec.fc:.3f} f'c")
    return ok


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--same", nargs=2, type=Path, metavar=("A", "B"),
                   help="two records of the same solve: are their sections the same?")
    p.add_argument("pairs", nargs="*", type=Path, metavar="RECORD SECTION")
    a = p.parse_args(argv)
    ok = True
    if a.same:
        ra, rb = record.read(a.same[0]), record.read(a.same[1])
        diff = [k for k in set(ra.sections) | set(rb.sections)
                if ra.sections.get(k) != rb.sections.get(k)]
        print(f"repeat: {'same sections' if not diff else f'{len(diff)} sections differ'}")
        ok = not diff
    if len(a.pairs) % 2:
        p.error("give each record with its section's file")
    for rec, sec in zip(a.pairs[::2], a.pairs[1::2]):
        ok &= check_record(rec, sec)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
