"""Analysis settings that r2x applies through Response's dialogs.

Shared by the command line, which checks them before anything runs, and the worker, which applies
them. A setting left as None keeps the input's value. Standard library only.
"""

from __future__ import annotations

from dataclasses import dataclass

UNITS = ("si", "us", "kgcm")
FACTORS = ("none", "csa")
MORE_DETAIL_MAX = "max"   # --more-detail max: press More Detail until Response stops refining

Loads = tuple[float, float, float]   # N, M, V, as the Define Loading dialog has them


@dataclass(frozen=True)
class Settings:
    units: str | None = None             # one of UNITS
    factors: str | None = None           # one of FACTORS
    initial: Loads | None = None         # N, M, V in the units in effect
    increment: Loads | None = None       # N, M, V; only signs and ratio matter; 0,0,0 allowed

    def __post_init__(self):
        if self.units is not None and self.units not in UNITS:
            raise ValueError(f"units must be one of {', '.join(UNITS)}")
        if self.factors is not None and self.factors not in FACTORS:
            raise ValueError(f"factors must be one of {', '.join(FACTORS)}")
        for name in ("initial", "increment"):
            value = getattr(self, name)
            if value is not None and len(value) != 3:
                raise ValueError(f"{name} must be N,M,V")

    def args(self) -> list[str]:
        """The worker's command-line options for these settings."""
        out: list[str] = []
        if self.units:
            out += ["--units", self.units]
        if self.factors:
            out += ["--factors", self.factors]
        if self.initial is not None:
            out += [f"--initial={format_loads(self.initial)}"]
        if self.increment is not None:
            out += [f"--increment={format_loads(self.increment)}"]
        return out


def parse_loads(text: str) -> Loads:
    """'N,M,V' -> (N, M, V). Raises ValueError; two values ask for V to be added."""
    parts = str(text).split(",")
    if len(parts) == 2:
        raise ValueError(f"{text!r}: loads are N,M,V since r2x 0.3.0; add V, e.g. "
                         f"{text},0")
    try:
        if len(parts) != 3:
            raise ValueError
        loads = tuple(float(p) for p in parts)
    except ValueError:
        raise ValueError(f"{text!r}: expected N,M,V, e.g. -2000,0,0") from None
    if any(x != x or abs(x) == float("inf") for x in loads):
        raise ValueError(f"{text!r}: expected finite numbers")
    return loads


def parse_more_detail(text: str) -> int | str:
    """--more-detail: a number of presses (0 or more), or 'max'. Raises ValueError."""
    text = str(text).strip().lower()
    if text == MORE_DETAIL_MAX:
        return MORE_DETAIL_MAX
    try:
        n = int(text)
    except ValueError:
        n = -1
    if n < 0:
        raise ValueError(f"{text!r}: expected a whole number of presses (0 or more), or max")
    return n


def format_number(x: float) -> str:
    """A number as typed into a Response field: plain decimal, no exponent, no trailing zeros."""
    if x == 0:
        return "0"
    return f"{x:.10f}".rstrip("0").rstrip(".")


def format_loads(loads: Loads) -> str:
    return ",".join(format_number(x) for x in loads)
