"""python tools/define_survey.py [--response-dir DIR]  — survey the define dialogs under Wine.

For every field in r2x's catalogue (src/r2x/dialogs.json): its control ID, the value Response
shows for Newbeam (Quick Define's defaults for quick; tests/reference/newbeam/input.r2t for the
others), the precision the dialog shows it with, and where Response saves it. Prints a Markdown
table (docs/define.md has its output) and the time each step took. Needs what the Wine tests
need ($R2X_RESPONSE_DIR, wine, Xvfb, mingw-w64).
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
from r2x.worker.define import Asker, run_define, run_show

ROOT = Path(__file__).resolve().parent.parent
NEWBEAM = ROOT / "tests" / "reference" / "newbeam" / "input.r2t"


class Recorder(Asker):
    """Answers Enter to everything and keeps the questions."""

    def __init__(self):
        self.questions, self.shown, self.said = [], [], []

    def ask(self, q):
        self.questions.append(q)
        return None

    def say(self, text):
        self.said.append(text)

    def set(self, pairs):
        pass

    def show(self, pairs):
        self.shown = pairs

    def done(self, **info):
        pass


def match(d, shown: list) -> dict:
    """show's (label, value) pairs -> {field key: (label, value, "")}, or for a list dialog
    {field key: [(item, value), ...]}. The pairs come in the fields' order, skipping fields the
    dialog does not show; a field whose label comes from the dialog matches any label."""
    out: dict = {}
    if d.kind == "list":
        prefix = d.item.capitalize() + " "
        item, k = None, 0
        for label, value in shown:
            if label == prefix.strip() + "s":    # "Tendon layers: none"
                continue
            if label.startswith(prefix):
                item, k = label[len(prefix):], 0
                continue
            while k < len(d.fields):
                f = d.fields[k]
                k += 1
                if f.question == label.strip() or f.label is not None:
                    out.setdefault(f.key, []).append((item, value))
                    break
        return out
    k = 0
    for label, value in shown:
        while k < len(d.fields):
            f = d.fields[k]
            k += 1
            if f.question == label or f.label is not None:
                out[f.key] = (label, value, "")
                break
    return out


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
        for d in catalogue.DIALOGS:
            rec = Recorder()
            t0 = time.monotonic()
            if d.kind == "wizard":
                run_define(Step(d), None, Path(tmp) / "quick.r2t", a.response_dir, a.prefix,
                           asker=rec)
                values = {q.key: (q.text, q.value, q.unit) for q in rec.questions}
            else:
                shutil.copyfile(NEWBEAM, work)
                run_show(Step(d), work, a.response_dir, a.prefix, asker=rec)
                values = match(d, rec.shown)
            times.append((d.noun, time.monotonic() - t0))
            for f in d.fields:
                v = values.get(f.key)
                if isinstance(v, list):
                    shown = "; ".join(f"{i}: {x}" for i, x in v)
                    prec = precision(v[0][1].split()[0], f.kind) if v else ""
                elif v:
                    shown = f"{v[1]} {v[2]}".strip() if v[1] != "" else "(blank)"
                    prec = precision(v[1].split()[0], f.kind) if v[1] else "text"
                elif d.kind == "list":
                    shown, prec = f"no {d.item}s", ""
                else:
                    shown, prec = "(not shown)", ""
                cid = f.id if f.id is not None else "/".join(str(o.id) for o in f.options)
                rows.append(f"| {d.noun} | {f.key} | {f.question} | {cid} | {f.kind} | "
                            f"{shown} | {prec} | {f.xml or '-'} |")
    print("| Noun | Field | Question | Control | Kind | Newbeam shows | Precision | Saved as |")
    print("|---|---|---|---|---|---|---|---|")
    print("\n".join(rows))
    print()
    print("| Noun | Seconds (show, or Quick Define with Enter throughout) |")
    print("|---|---|")
    for noun, s in times:
        print(f"| {noun} | {s:.1f} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
