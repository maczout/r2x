"""python tools/define_cases.py  — write the define reference cases' session.txt and README.md.

From tests/reference/define/cases.json: each case is run once under Wine, answering by field
key, to learn the questions in their order; then

- session.txt is the r2x session that makes the case (one answer per line, Enter for the
  questions left as Response shows them), which tests/test_define_cases_wine.py and
  tests/reference/define/check.ps1 run;
- README.md says how to make the same file by hand in Response-2000 on Windows (hand.r2t).

Needs what the Wine tests need ($R2X_RESPONSE_DIR, wine, Xvfb, mingw-w64).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from r2x.catalogue import BY_NOUN, parse_step
from r2x.worker.define import Asker, run_define

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "tests" / "reference" / "define"
NEWBEAM = ROOT / "tests" / "reference" / "newbeam" / "input.r2t"
FILE = "r2x.r2t"
DATE = "2026/10/24"


class KeyAsker(Asker):
    def __init__(self, answers: dict):
        self.answers = dict(answers)
        self.asked: list[tuple[dict, str | None]] = []      # (question, answer given)

    def ask(self, q):
        a = self.answers.pop(q.key, None)
        if a is None and not q.keep:
            raise SystemExit(f"no answer for {q.key}: {q.text}")
        self.asked.append((q, a))
        return a

    def say(self, text):
        print(f"    Response: {text}")

    def set(self, pairs):
        pass

    def done(self, **info):
        pass


def gui_lines(step_words: list[str], asked) -> list[str]:
    """How to give the same answers in Response's dialog, for the case's README: numbered
    steps, with the values to set as indented items under them."""
    step = parse_step(step_words)
    d = step.dialog
    menu = d.summary.split(":")[0]
    value = lambda q, a: f"{q.text}: {a}" + (f" {q.unit}" if q.unit else "")
    if d.kind == "wizard":
        out = [f"{menu}. Set only these, pressing Next after each page and Finish after the "
               f"last:"]
        for i, page in enumerate(d.pages, 1):
            keys = {f.key for f in page.fields}
            here = [value(q, a) for q, a in asked if q.key in keys and a is not None]
            out.append(f"   - Step {i} of 4: " + ("; ".join(here) if here else "nothing"))
        return out
    page = d.pages[0].title
    where = menu + (f", {page}" if d.kind in ("sheet", "list") and page else "")
    if d.kind == "list" and step.action == "delete":
        return [f"{where}: select {step.name} in the list, press Delete, then OK."]
    head = {"modify": f"{where}: select {step.name} in the list, then set:",
            "add": f"{where}: type {step.name} in Name, then set:"}.get(step.action,
                                                                         f"{where}: set:")
    out = [head] + [f"   - {value(q, a)}" for q, a in asked if a is not None]
    if d.kind == "list":
        out.append(f"   - then press {'Add' if step.action == 'add' else 'Modify'}, and OK")
    else:
        out.append("   - then OK")
    return out


def numbered(lines: list[str]) -> str:
    out, n = [], 0
    for line in lines:
        if line.startswith(" "):
            out.append(line)
        else:
            n += 1
            out.append(f"{n}. {line}")
    return "\n".join(out)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--response-dir", type=Path, default=os.environ.get("R2X_RESPONSE_DIR"))
    p.add_argument("--prefix", type=Path,
                   default=os.environ.get("R2X_WINEPREFIX", Path.home() / ".cache/r2x/prefix"))
    p.add_argument("names", nargs="*", help="only these cases")
    a = p.parse_args()
    cases = json.loads((CASES / "cases.json").read_text(encoding="utf-8"))["cases"]
    for case in cases:
        if a.names and case["name"] not in a.names:
            continue
        print(case["name"])
        folder = CASES / case["name"]
        folder.mkdir(exist_ok=True)
        session, gui = [], []
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / FILE
            if case["from"] == "newbeam":
                shutil.copyfile(NEWBEAM, f)
                session.append(f"open {FILE}")
                gui.append(f"File > Open `..\\..\\newbeam\\input.r2t` (Newbeam).")
            else:
                gui.append("Start Response-2000 with no file.")
            for step in case["steps"]:
                words = step["define"].split()
                asker = KeyAsker(step["answers"])
                run_define(parse_step(words), f if f.exists() else None, f, a.response_dir,
                           a.prefix, date=DATE, asker=asker)
                if asker.answers:
                    raise SystemExit(f"{case['name']}: never asked {sorted(asker.answers)}")
                session.append(f"define {step['define']}")
                if words[0] == "quick":
                    session.append(FILE)                      # File name
                session += [ans or "" for _, ans in asker.asked]
                gui += gui_lines(words, asker.asked)
        session.append("quit")
        (folder / "session.txt").write_text("\n".join(session) + "\n", encoding="utf-8",
                                            newline="\r\n")
        steps = numbered(gui + ["File > Save As `hand.r2t` in this folder."])
        readme = f"""# define case: {case['name']}

{case['about']}.

**By hand**, in Response-2000 on Windows (anything not listed stays as Response shows it):

{steps}

**By r2x:** `..\\check.ps1` runs `session.txt` in an r2x session in this folder (it makes
`{FILE}`{' from a copy of Newbeam' if case['from'] == 'newbeam' else ''}) and compares it with
`hand.r2t`, byte for byte{', but for the date' if case['from'] is None else ''}.
`tests/test_define_cases_wine.py` does the same under Wine.

Written by `tools/define_cases.py` from `cases.json`.
"""
        (folder / "README.md").write_text(readme, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
