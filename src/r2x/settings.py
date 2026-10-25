"""Analysis settings that r2x applies through Response's dialogs.

Shared by the command line, which checks them before anything runs, and the worker, which applies
them. A setting left as None keeps the input's value. Standard library only.
"""

from __future__ import annotations

from dataclasses import dataclass

UNITS = ("si", "us", "kgcm")
FACTORS = ("none", "csa")


@dataclass(frozen=True)
class Settings:
    units: str | None = None                       # one of UNITS
    factors: str | None = None                     # one of FACTORS
    initial: tuple[float, float] | None = None     # N, M in the units in effect
    increment: tuple[float, float] | None = None   # N, M; only signs and ratio matter

    def __post_init__(self):
        if self.units is not None and self.units not in UNITS:
            raise ValueError(f"units must be one of {', '.join(UNITS)}")
        if self.factors is not None and self.factors not in FACTORS:
            raise ValueError(f"factors must be one of {', '.join(FACTORS)}")
        if self.increment is not None and self.increment == (0, 0):
            raise ValueError("the increment cannot be 0,0")

    def args(self) -> list[str]:
        """The worker's command-line options for these settings."""
        out: list[str] = []
        if self.units:
            out += ["--units", self.units]
        if self.factors:
            out += ["--factors", self.factors]
        if self.initial is not None:
            out += [f"--initial={format_pair(self.initial)}"]
        if self.increment is not None:
            out += [f"--increment={format_pair(self.increment)}"]
        return out


def parse_pair(text: str) -> tuple[float, float]:
    """'N,M' -> (N, M). Raises ValueError."""
    parts = str(text).split(",")
    try:
        if len(parts) != 2:
            raise ValueError
        n, m = float(parts[0]), float(parts[1])
    except ValueError:
        raise ValueError(f"{text!r}: expected N,M, e.g. -2000,0") from None
    if n != n or m != m or abs(n) == float("inf") or abs(m) == float("inf"):
        raise ValueError(f"{text!r}: expected finite numbers")
    return n, m


def format_number(x: float) -> str:
    """A number as typed into a Response field: plain decimal, no exponent, no trailing zeros."""
    if x == 0:
        return "0"
    return f"{x:.10f}".rstrip("0").rstrip(".")


def format_pair(pair: tuple[float, float]) -> str:
    return f"{format_number(pair[0])},{format_number(pair[1])}"
