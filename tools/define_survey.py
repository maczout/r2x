"""python tools/define_survey.py [--response-dir DIR]  — survey the define dialogs under Wine.

For every field in r2x's catalogue (src/r2x/dialogs.json): its control ID, the frame it sits in
and the label the dialog shows, the value Response shows for Newbeam (Quick Define's defaults
for quick; tests/reference/newbeam/input.r2t for the others, each item of a list dialog in
turn), the precision the dialog shows it with, and where Response saves it. Every question is
answered with Enter, so nothing is saved. Prints a Markdown table (docs/define.md has its
output) and the time each step took. Needs what the Wine tests need ($R2X_RESPONSE_DIR, wine,
Xvfb, mingw-w64).
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

from r2x import catalogue
from r2x.catalogue import Step
from r2x.worker.define import Abort, Asker, run_define
from r2x.worker.session import R2xError

ROOT = Path(__file__).resolve().parent.parent
NEWBEAM = ROOT / "tests" / "reference" / "newbeam" / "input.r2t"


class Recorder(Asker):
    """Answers Enter to everything and keeps the questions; a question that needs an answer
    ends the step, as the end of the input does at the command line."""

    def __init__(self):
        self.questions, self.said = [], []

    def ask(self, q):
        self.questions.append(q)
        if not q.keep:
            raise Abort("stopped without an answer; nothing saved")
        return None

    def say(self, text):
        self.said.append(text)

    def set(self, items):
        pass

    def done(self, **info):
        pass


def survey(step: Step, inp: Path | None, out: Path, a) -> dict:
    """{field key: question} for one step answered with Enter throughout."""
    rec = Recorder()
    try:
        run_define(step, inp, out, a.response_dir, a.prefix, asker=rec)
    except R2xError as e:            # a list with nothing to modify; an Add answered with Enter
        rec.said.append(str(e))
    asked: dict = {}
    for q in rec.questions:          # the first of each (modify asks for "name" twice)
        asked.setdefault(q.key, q)
    return asked


def precision(value: str, kind: str = "number") -> str:
    if kind not in ("number", "integer"):
        return "text"
    try:
        float(value)
    except ValueError:
        return "text"
    return f"{len(value.split('.')[1])} dp" if "." in value else "0 dp"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--response-dir", type=Path, default=os.environ.get("R2X_RESPONSE_DIR"))
    p.add_argument("--prefix", type=Path,
                   default=os.environ.get("R2X_WINEPREFIX", Path.home() / ".cache/r2x/prefix"))
    a = p.parse_args()
    if not a.response_dir:
        p.error("--response-dir or $R2X_RESPONSE_DIR is required")
    rows, times = [], []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "newbeam.r2t"
        shutil.copyfile(NEWBEAM, work)
        for d in catalogue.DIALOGS:
            t0 = time.monotonic()
            if d.kind == "wizard":
                runs = [("", survey(Step(d), None, Path(tmp) / "quick.r2t", a))]
            elif d.kind == "list":
                first = survey(Step(d, "modify"), work, work, a)
                names = first["name"].choices if "name" in first else []
                runs = [(n, survey(Step(d, "modify", n), work, work, a)) for n in names]
                if not runs:                 # none to modify: the fields an Add asks
                    spare = Path(tmp) / "spare.r2t"
                    shutil.copyfile(NEWBEAM, spare)
                    runs = [("(add)", survey(Step(d, "add", "survey"), spare, spare, a))]
            else:
                runs = [("", survey(Step(d), work, work, a))]
            times.append((d.noun, (time.monotonic() - t0) / max(1, len(runs))))
            for f in d.fields:
                asked = [(item, qs[f.key]) for item, qs in runs if f.key in qs]
                if not asked:
                    shown, prec, frame, label = (f"no {d.item}s" if d.kind == "list" and not runs
                                                 else "(not shown)"), "", "", ""
                else:
                    q = asked[0][1]
                    frame, label = q.frame, q.text
                    values = [(item, f"{q.value} {q.unit}".strip() if q.value != "" else "(blank)")
                              for item, q in asked]
                    shown = "; ".join(f"{i}: {v}" if i else v for i, v in values)
                    prec = precision(q.value.split()[0] if q.value else "", f.kind)
                cid = f.id if f.id is not None else "/".join(str(o.id) for o in f.options)
                rows.append(f"| {d.noun} | {f.key} | {frame or '-'} | {label or f.question} | "
                            f"{cid} | {f.kind} | {shown} | {prec} | {f.xml or '-'} |")
    print("| Noun | Field | Frame | Question | Control | Kind | Newbeam shows | Precision | "
          "Saved as |")
    print("|---|---|---|---|---|---|---|---|---|")
    print("\n".join(rows))
    print()
    print("| Noun | Seconds (Enter throughout, per item for a list) |")
    print("|---|---|")
    for noun, s in times:
        print(f"| {noun} | {s:.1f} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
