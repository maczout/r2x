"""The --stage option: which load stages get their detail views exported.

    peak        the stage Response shows when the solve finishes
    all         every stage
    N, N-M      stage numbers and inclusive ranges; 0 is the initial load
    peak,0-5    any mix, separated by commas

Shared by the command line, which checks the syntax before anything runs, and the worker, which
resolves it once the solve has given the number of stages and the peak. Standard library only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_NUMBER_OR_RANGE = re.compile(r"(\d+)(?:-(\d+))?")
MAX_STAGE = 99999   # far beyond any solve; keeps a mistyped range from filling memory


class StageError(ValueError):
    """A stage selection that is malformed, or names a stage the solve does not have."""


@dataclass(frozen=True)
class StageSpec:
    peak: bool = False
    all: bool = False
    numbers: frozenset[int] = frozenset()

    def __str__(self) -> str:
        """Canonical form, which parse_stages() reads back to the same spec."""
        if self.all:
            return "all"
        parts = (["peak"] if self.peak else []) + ([format_ranges(self.numbers)]
                                                   if self.numbers else [])
        return ",".join(parts)

    def resolve(self, count: int, peak: int) -> list[int]:
        """Sorted stage numbers for a solve with `count` stages (0 to count-1) and this peak."""
        if self.all:
            return list(range(count))
        past = sorted(i for i in self.numbers if i >= count)
        if past:
            raise StageError(f"stage {format_ranges(past)} is past the last stage, {count - 1}"
                             if len(past) == 1 else
                             f"stages {format_ranges(past)} are past the last stage, {count - 1}")
        return sorted(self.numbers | ({peak} if self.peak else set()))


PEAK = StageSpec(peak=True)
ALL = StageSpec(all=True)


def parse_stages(text: str) -> StageSpec:
    peak = every = False
    numbers: set[int] = set()
    tokens = [t.strip().lower() for t in str(text).split(",")]
    for token in tokens:
        if token == "peak":
            peak = True
        elif token == "all":
            every = True
        else:
            m = _NUMBER_OR_RANGE.fullmatch(token)
            if not m:
                what = "an empty item" if not token else f"{token!r}"
                raise StageError(f"{what} in {text!r}: use peak, all, a stage number or a range "
                                 "like 20-30")
            first = int(m.group(1))
            last = int(m.group(2)) if m.group(2) is not None else first
            if max(first, last) > MAX_STAGE:
                raise StageError(f"{token} is out of range: stage numbers go up to {MAX_STAGE}")
            if last < first:
                raise StageError(f"range {token} runs backwards; write {last}-{first}")
            numbers.update(range(first, last + 1))
    if every:
        return ALL
    return StageSpec(peak=peak, numbers=frozenset(numbers))


def format_ranges(numbers) -> str:
    """[0, 1, 2, 5, 7, 8] -> '0-2,5,7-8'."""
    out: list[str] = []
    run: list[int] = []
    for n in sorted(set(numbers)):
        if run and n == run[-1] + 1:
            run.append(n)
            continue
        if run:
            out.append(f"{run[0]}-{run[-1]}" if len(run) > 1 else str(run[0]))
        run = [n]
    if run:
        out.append(f"{run[0]}-{run[-1]}" if len(run) > 1 else str(run[0]))
    return ",".join(out)
