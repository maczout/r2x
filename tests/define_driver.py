"""Run one define step in the worker and answer its questions from a script (Wine tests).

answers: {key: answer} for the questions to answer, by the field's key in dialogs.json (or
"name", "action", "response" for Response's own Yes/No questions, "bar" for its bar list); a
list of answers for a key asked more than once. Every other question is answered with Enter.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

def response_dir() -> str:
    return os.environ.get("R2X_RESPONSE_DIR", "Response")


def prefix() -> Path:
    return Path(os.environ.get("R2X_WINEPREFIX", Path.home() / ".cache/r2x/prefix"))


@dataclass
class Result:
    status: int
    questions: list[dict] = field(default_factory=list)
    said: list[str] = field(default_factory=list)
    set: list[list[str]] = field(default_factory=list)
    shown: list[list[str]] = field(default_factory=list)
    done: dict = field(default_factory=dict)
    stderr: str = ""

    def asked(self, key: str) -> list[dict]:
        return [q for q in self.questions if q["key"] == key]


def define(words: list[str], answers: dict | None = None, input_file: Path | None = None,
           out: Path | None = None, report: Path | None = None, date: str | None = None,
           extra: list[str] = (), show: bool = False) -> Result:
    answers = {k: (list(v) if isinstance(v, list) else [v]) for k, v in (answers or {}).items()}
    cmd = [sys.executable, "-m", "r2x.worker", "define", *words,
           "--response-dir", response_dir(), "--prefix", str(prefix()), *extra]
    if input_file is not None:
        cmd += ["--input", str(input_file)]
    if out is not None:
        cmd += ["--out", str(out)]
    if report is not None:
        cmd += ["--report", str(report)]
    if date is not None:
        cmd += ["--date", date]
    if show:
        cmd.append("--show")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, encoding="utf-8")
    result = Result(0)
    for line in proc.stdout:
        msg = json.loads(line)
        if "ask" in msg:
            q = msg["ask"]
            result.questions.append(q)
            queue = answers.get(q["key"])
            a = queue.pop(0) if queue else None
            if a is None and not q["keep"]:
                proc.stdin.close()     # no answer for a question that needs one: give up
                continue
            proc.stdin.write(json.dumps({"answer": a}) + "\n")
            proc.stdin.flush()
        elif "say" in msg:
            result.said.append(msg["say"])
        elif "set" in msg:
            result.set = msg["set"]
        elif "show" in msg:
            result.shown = msg["show"]
        elif "done" in msg:
            result.done = msg["done"]
    result.stderr = proc.stderr.read()
    result.status = proc.wait()
    return result


if __name__ == "__main__":   # python tests/define_driver.py WORDS... -- key=value ...
    args = sys.argv[1:]
    words, pairs = (args[:args.index("--")], args[args.index("--") + 1:]) if "--" in args \
        else (args, [])
    opts = dict(p.split("=", 1) for p in pairs)
    r = define(words, {k: v for k, v in opts.items() if not k.startswith("@")},
               Path(opts["@in"]) if "@in" in opts else None,
               Path(opts["@out"]) if "@out" in opts else None,
               Path(opts["@report"]) if "@report" in opts else None, opts.get("@date"),
               show="@show" in opts)
    for q in r.questions:
        print("Q", q["key"], repr(q["text"]), q["unit"], repr(q["value"]), q["choices"][:6])
    for s in r.said:
        print("SAY", s)
    print("SET", r.set)
    print("SHOW", r.shown)
    print("DONE", r.done, "status", r.status)
    print(r.stderr)
