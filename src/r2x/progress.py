"""Progress lines: how the worker reports on stderr, and how the command line reads it back.

Every line the worker writes for the command line starts with "r2x: " and has a fixed form:

    r2x: note: creating Wine prefix (first run only)
    r2x: solving
    r2x: solved: 60 stages, peak 56
    r2x: stage 56 (1/1)                  stage 56 exported, the first of one
    r2x: wrote /out/Newbeam.r2x.txt in 9.1 s
    r2x: failed: <reason>                exit status 1
    r2x: usage error: <reason>           exit status 2 (e.g. a stage past the last stage)
    r2x: out of scope: <reason>          exit status 3

Anything else on stderr (a Python traceback, say) is not part of the protocol. Standard library
only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

PREFIX = "r2x: "

# Exit statuses, shared by the worker and the command line.
SOLVED, FAILED, USAGE, OUT_OF_SCOPE = 0, 1, 2, 3


@dataclass(frozen=True)
class Event:
    kind: str                  # note solving solved stage wrote failed usage out-of-scope
    text: str = ""             # note, wrote (path), failed, usage, out-of-scope
    count: int | None = None   # solved: number of stages
    stage: int | None = None   # solved: peak stage; stage: the stage exported
    done: int | None = None    # stage: how many exported so far
    total: int | None = None   # stage: how many to export
    seconds: float | None = None  # wrote

    def line(self) -> str:
        k = self.kind
        if k == "solving":
            body = "solving"
        elif k == "solved":
            body = f"solved: {self.count} stages, peak {self.stage}"
        elif k == "stage":
            body = f"stage {self.stage} ({self.done}/{self.total})"
        elif k == "wrote":
            body = f"wrote {self.text} in {self.seconds:.1f} s"
        elif k in _TEXT_KINDS:
            body = f"{_TEXT_KINDS[k]}: {_one_line(self.text)}"
        else:
            raise ValueError(f"unknown event kind {k!r}")
        return PREFIX + body


_TEXT_KINDS = {"note": "note", "failed": "failed", "usage": "usage error",
               "out-of-scope": "out of scope"}
_TEXT_LABELS = {label: kind for kind, label in _TEXT_KINDS.items()}

_SOLVED = re.compile(r"solved: (\d+) stages, peak (\d+)")
_STAGE = re.compile(r"stage (\d+) \((\d+)/(\d+)\)")
_WROTE = re.compile(r"wrote (.+) in (\d+(?:\.\d+)?) s")


def _one_line(text: str) -> str:
    return " ".join(str(text).split())


def note(text: str) -> Event:
    return Event("note", text)


def parse(line: str) -> Event | None:
    """The event on a worker stderr line, or None if the line is not part of the protocol."""
    line = line.rstrip("\r\n")
    if not line.startswith(PREFIX):
        return None
    body = line[len(PREFIX):]
    if body == "solving":
        return Event("solving")
    if m := _SOLVED.fullmatch(body):
        return Event("solved", count=int(m.group(1)), stage=int(m.group(2)))
    if m := _STAGE.fullmatch(body):
        return Event("stage", stage=int(m.group(1)), done=int(m.group(2)), total=int(m.group(3)))
    if m := _WROTE.fullmatch(body):
        return Event("wrote", text=m.group(1), seconds=float(m.group(2)))
    label, sep, text = body.partition(": ")
    if sep and label in _TEXT_LABELS:
        return Event(_TEXT_LABELS[label], text)
    return None
