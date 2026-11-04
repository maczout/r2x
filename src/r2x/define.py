"""The command-line side of r2x define: run one step in the container and put its questions to
the person.

A step is one container run (docs/define.md, How a define step works): Response opens the
section's file, one of its dialogs is gone through question by question, and Response saves the
file back with its own Save As; the section's report beside it is rewritten with Response's
input screen. The questions come from the worker over stdout and the answers go back on its
stdin (r2x.ask). Standard library only.
"""

from __future__ import annotations

import datetime as _dt
import json
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Callable

from r2x import ask, progress
from r2x.ask import AnswerError, Question
from r2x.catalogue import Step
from r2x.progress import FAILED, SOLVED, USAGE
from r2x.settings import Settings

SECTION_SUFFIXES = (".r2t", ".rsp")
REPORT_SUFFIX = ".r2x.html"
RECORD_SUFFIX = ".r2x.txt"


def report_for(section: Path) -> Path:
    """A section's report: NAME.r2x.html beside NAME.r2t, as solve --report writes it."""
    return section.with_name(section.stem + REPORT_SUFFIX)


def record_for(section: Path) -> Path:
    return section.with_name(section.stem + RECORD_SUFFIX)


def today() -> str:
    """The date as Response writes it, on the computer r2x runs on (Windows)."""
    return _dt.date.today().strftime("%Y/%m/%d")


def file_name_from(title: str) -> str:
    """A file name from a section title: 'Pier cap' -> pier-cap.r2t."""
    stem = "-".join("".join(c if c.isalnum() else " " for c in title.lower()).split())
    return (stem or "section") + ".r2t"


# -- asking -------------------------------------------------------------------------------------
class Prompter:
    """Asks the questions: at a terminal, or from lines piped in (one answer per line; at the
    end of the input, Enter for every question that has a value to keep).

    A field inside one of the dialog's frames is asked under the frame's text, printed once as a
    heading over the frame's questions. A question with choices prints them under itself,
    numbered (but for Response's bar list, whose names can be numbers), and its answer is typed
    on the line after them."""

    def __init__(self, inp: IO[str] = sys.stdin, out: IO[str] = sys.stdout):
        self.inp, self.out = inp, out
        self.interactive = inp.isatty() if hasattr(inp, "isatty") else False
        self.ended = False
        self.frame = ""            # the frame whose heading was printed last

    def print(self, text: str = ""):
        self.out.write(text + "\n")
        self.out.flush()

    def line(self, prompt: str) -> str | None:
        """One line typed after the prompt; None at the end of the input."""
        if self.ended:
            return None
        self.out.write(prompt)
        self.out.flush()
        text = self.inp.readline()
        if not text:
            self.ended = True
            self.out.write("\n")
            return None
        text = text.rstrip("\r\n")
        if not self.interactive:
            self.out.write(text + "\n")    # piped: show the answer as if typed
        return text

    def answer(self, q: Question) -> tuple[bool, str | None]:
        """(answered, the answer to send); not answered: the input ended or no answer came."""
        indent = "  "
        if q.frame:
            if q.frame != self.frame:
                self.print(f"  {q.frame}")
            indent = "    "
        self.frame = q.frame
        if q.is_menu() or q.is_list():
            self.print(indent + q.heading())
            lines = (ask.format_choices if q.is_menu() else ask.format_names)(
                q.choices, 76 - len(indent))
            for line in lines:
                self.print(f"{indent}  {line}")
            prompt = f"{indent}> "
        else:
            prompt = indent + q.prompt()
        while True:
            text = self.line(prompt)
            if text is None:
                return (True, None) if q.keep else (False, None)
            try:
                return True, ask.check_answer(q, text)
            except AnswerError as e:
                self.print(f"{indent}  {e}")


# -- one step in the container -------------------------------------------------------------------
@dataclass
class StepResult:
    status: int
    reason: str = ""
    saved: bool = False
    readback: list[list[str]] = field(default_factory=list)
    title: str = ""
    seconds: float = 0.0


def worker_command(docker: list[str], image: str, docker_path: Callable[[Path], str],
                   words: list[str], *, input_file: Path | None = None, out: Path | None = None,
                   report: Path | None = None, date: str | None = None,
                   settings: Settings = Settings(), screen: str | None = None) -> list[str]:
    """docker run for one define step (with screen, no dialog: the report's input screen, and
    Save As to out if given). The section's file is mounted read-only at /in, the folder
    Response saves into and the report goes to at /out."""
    mounts, args = [], []
    if input_file is not None:
        mounts += ["-v", f"{docker_path(input_file)}:/in/{input_file.name}:ro"]
        args += ["--input", f"/in/{input_file.name}"]
    folder = (out or report).parent if (out or report) is not None else None
    if folder is not None:
        mounts += ["-v", f"{docker_path(folder)}:/out"]
    if out is not None:
        args += ["--out", f"/out/{out.name}"]
    if report is not None:
        if report.parent != folder:
            raise ValueError("the report goes beside the section")
        args += ["--report", f"/out/{report.name}"]
    if date:
        args += ["--date", date]
    if settings.units:
        args += ["--units", settings.units]
    if settings.factors:
        args += ["--factors", settings.factors]
    if screen is not None:
        args += ["--screen", screen]
    return docker + ["run", "--rm", "-i", "--pull", "never", "--network", "none", *mounts,
                     image, "python", "-m", "r2x.worker", "define", *words, *args]


def run_step(cmd: list[str], prompter: Prompter,
             on_note: Callable[[str], None] | None = None) -> StepResult:
    """Run a define step's container, answering its questions; return its outcome."""
    note = on_note or (lambda text: prompter.print(f"  note: {text}"))
    prompter.frame = ""
    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, encoding="utf-8",
                                errors="replace", bufsize=1)
    except FileNotFoundError:
        return StepResult(FAILED, f"cannot run {cmd[0]!r} (is Docker installed?)")
    result = StepResult(SOLVED)
    failure, other = [""], []

    def read_stderr():
        for line in proc.stderr:
            e = progress.parse(line)
            if e is None:
                if line.strip():
                    other.append(line.rstrip())
            elif e.kind in ("failed", "usage", "out-of-scope"):
                failure[0] = e.text
            elif e.kind == "note":
                note(e.text)
    errors = threading.Thread(target=read_stderr, daemon=True)
    errors.start()
    try:
        for line in proc.stdout:
            try:
                msg = ask.read_line(line)
            except ValueError:
                other.append(line.rstrip())
                continue
            if "ask" in msg:
                ok, answer = prompter.answer(ask.read_question(msg["ask"]))
                if not ok:
                    proc.stdin.close()      # the worker stops without saving
                    continue
                proc.stdin.write(f'{{"answer": {json.dumps(answer)}}}\n')
                proc.stdin.flush()
            elif "say" in msg:
                prompter.print(f"  {msg['say']}")
            elif "set" in msg:
                result.readback = msg["set"]
            elif "done" in msg:
                d = msg["done"]
                result.saved, result.title = d.get("saved", False), d.get("title", "")
                result.seconds = d.get("seconds", 0.0)
    except KeyboardInterrupt:
        proc.stdin.close()
        prompter.print("")
        proc.wait()
        errors.join(5)
        return StepResult(FAILED, "stopped; nothing saved")
    except BrokenPipeError:
        pass
    code = proc.wait()
    errors.join(5)
    if code == SOLVED:
        return result
    reason = failure[0] or (" / ".join(other[-3:]) if other else f"exit status {code}")
    return StepResult(code if code in (FAILED, USAGE) else FAILED, reason)


def set_line(readback: list[list[str]], width: int = 78) -> str:
    """What a step set, read back from the dialog, wrapped. Fields of one frame go together
    under the frame's text, as they were asked: [label, value] or [label, value, frame]."""
    import textwrap
    if not readback:
        return "  set: nothing, every answer as Response had it"
    groups: list[tuple[str, list[str]]] = []
    for item in readback:
        label, value = item[0], item[1]
        frame = item[2] if len(item) > 2 else ""
        if not groups or groups[-1][0] != frame:
            groups.append((frame, []))
        groups[-1][1].append(f"{label} {value}")
    lines = []
    for frame, items in groups:
        text = (f"{frame}: " if frame else "") + "; ".join(items)
        first = "  set: " if not lines else "       "
        lines += textwrap.wrap(text, width, initial_indent=first,
                               subsequent_indent="       " + ("  " if frame else ""),
                               break_on_hyphens=False)
    return "\n".join(lines)
