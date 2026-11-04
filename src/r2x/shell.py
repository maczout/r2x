"""The r2x session: `r2x` with no command. A prompt at which a section is defined step by step,
then solved.

    r2x> define quick                 a new section, question by question
    r2x> define long add web          add a longitudinal reinforcement layer
    r2x> solve --increment 0,1,1      solve the session's file (any r2x solve options)

The session works on one file. Each step is one container run: Response opens the file, one of
its dialogs is set, Response saves the file back (Save As), and the section's report beside it
is rewritten; the report reloads itself, so one browser tab follows the session. Repeated steps
and solves overwrite the file, its report and its record. The file from before the last step is
kept in the session for undo; nothing else is written. Standard library only.
"""

from __future__ import annotations

import os
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from r2x import catalogue
from r2x.ask import Question
from r2x.catalogue import CatalogueError, parse_step
from r2x.define import (SECTION_SUFFIXES, Prompter, StepResult, file_name_from, report_for,
                        run_step, set_line, today)
from r2x.progress import SOLVED
from r2x.settings import Settings

NEW_TITLE = "New Cross Section"   # Response's title for a new section
UNITS = {"SI Metric": "si", "US Customary": "us", "kg/cm Metric": "kgcm"}

HELP = """\
Commands:
  define NOUN ...      set part of the section, question by question; Enter keeps the value
                       shown (help define lists the nouns)
  open FILE            work on this file (.r2t or .rsp)
  solve [OPTIONS]      solve the file and update its report (r2x solve --help for OPTIONS)
  undo                 put the file back as it was before the last step
  report               open the section's report in the browser
  help [define [NOUN]] this, or what a define asks
  quit                 end the session (every step is already saved)"""


def split_words(line: str) -> list[str]:
    """Words of a command line; "double quotes" group words. Backslashes are kept (Windows
    paths)."""
    words, cur, quoted, any_ = [], [], False, False
    for ch in line:
        if ch == '"':
            quoted, any_ = not quoted, True
        elif ch.isspace() and not quoted:
            if cur or any_:
                words.append("".join(cur))
            cur, any_ = [], False
        else:
            cur.append(ch)
    if quoted:
        raise ValueError("a quote is not closed")
    if cur or any_:
        words.append("".join(cur))
    return words


@dataclass
class Undo:
    file: Path                 # the file the step wrote
    before: bytes | None       # its bytes before the step (None: the step made it)
    current: Path | None       # the session's file before the step
    what: str                  # the step, for messages


class Shell:
    def __init__(self, command: Callable[..., list[str]], solve: Callable[[list[str], Path], int],
                 prompter: Prompter | None = None, cwd: Path | None = None,
                 browser: bool | None = None):
        """command(words, **worker_command options) -> docker command for a define step;
        solve(options, file) -> exit status of solving file with r2x solve's options."""
        self.command, self.solve_file = command, solve
        self.p = prompter or Prompter()
        self.cwd = Path(cwd or Path.cwd())
        self.file: Path | None = None
        self.undo: Undo | None = None
        self.units: str | None = None          # units asked for before there is a section
        self.browser = self.p.interactive if browser is None else browser
        self.opened: set[Path] = set()

    # -- the loop -------------------------------------------------------------------------------
    def run(self) -> int:
        self.p.print("r2x session: define a section, then solve it. help lists the commands.")
        while True:
            line = self.p.line("r2x> ")
            if line is None:
                return SOLVED
            try:
                if not self.do(line):
                    return SOLVED
            except KeyboardInterrupt:
                self.p.print("  stopped")

    def do(self, line: str) -> bool:
        try:
            words = split_words(line)
        except ValueError as e:
            self.p.print(f"  {e}")
            return True
        if not words:
            return True
        cmd, rest = words[0].lower(), words[1:]
        if cmd in ("quit", "exit", "q"):
            return False
        handler = {"define": self.define, "open": self.open, "solve": self.solve,
                   "undo": self.do_undo, "help": self.help, "report": self.report}.get(cmd)
        if handler is None:
            self.p.print(f"  no command {words[0]!r}; help lists them")
        else:
            handler(rest)
        return True

    def path(self, name: str) -> Path:
        p = Path(name)
        return p if p.is_absolute() else self.cwd / p

    # -- commands -------------------------------------------------------------------------------
    def define(self, words: list[str]):
        try:
            step = parse_step(words)
        except CatalogueError as e:
            self.p.print(f"  {e}")
            return
        if step.noun == "quick":
            return self.quick()
        if self.file is None:
            if step.noun == "units":
                return self.units_first()
            self.p.print("  no section yet: define quick, or open FILE")
            return
        self.step(step.words(), f"define {' '.join(step.words())}", self.file, self.file)

    def quick(self):
        default = self.file.name if self.file else file_name_from(NEW_TITLE)
        name = self.p.line(f"  File name [{default}]: ")
        name = (name or "").strip() or default
        target = self.path(name if Path(name).suffix.lower() in SECTION_SUFFIXES
                           else name + ".r2t")
        if not target.parent.is_dir():
            self.p.print(f"  no folder {target.parent}")
            return
        if target.exists() and target != self.file:
            ok, a = self.p.answer(Question("replace", f"{target.name} exists: replace its "
                                           "section", "yesno", "n"))
            if not ok or a != "y":
                self.p.print("  nothing done")
                return
        # Response opens the file being replaced (or the session's file), so the new section
        # is in its units, as in the GUI; with neither, the units asked for come first.
        source = target if target.exists() else self.file
        settings = Settings(units=self.units) if source is None and self.units else Settings()
        self.step(["quick"], "define quick", source, target, date=today(), settings=settings)

    def units_first(self):
        ok, a = self.p.answer(Question("units", "Units", "radio", "SI Metric", "",
                                       list(UNITS)))
        if ok and a:
            self.units = UNITS[a]
            self.p.print(f"  {a}: for the section define quick makes")

    def step(self, words: list[str], what: str, source: Path | None, target: Path, **options):
        before = target.read_bytes() if target.exists() else None
        report = report_for(target)
        cmd = self.command(words, input_file=source, out=target, report=report, **options)
        result = run_step(cmd, self.p)
        if not self.outcome(result, what):
            return
        if result.saved:
            self.p.print(set_line(result.readback))
            self.undo = Undo(target, before, self.file, what)
            self.file = target
            self.saved(result, report)
        else:
            self.p.print("  nothing changed")

    def outcome(self, result: StepResult, what: str) -> bool:
        if result.status != SOLVED:
            stopped = result.reason.startswith("stopped")
            self.p.print(f"  {result.reason}" if stopped else f"  {what} failed: {result.reason}")
            return False
        return True

    def saved(self, result: StepResult, report: Path):
        self.p.print(f"  saved {self.file.name}, report {report.name} updated "
                     f"({result.seconds:.1f} s)")
        if self.browser and report not in self.opened and report.exists():
            self.opened.add(report)
            webbrowser.open(report.resolve().as_uri())

    def open(self, words: list[str]):
        if len(words) != 1:
            self.p.print("  open FILE")
            return
        p = self.path(words[0])
        if not p.is_file():
            self.p.print(f"  no file {p}")
            return
        self.file, self.undo = p, None
        report = report_for(p)
        self.p.print(f"  working on {p.name}")
        if not report.exists():   # give the section its report: its input screen
            result = run_step(self.command([], input_file=p, report=report,
                                           screen=f"open {p.name}"), self.p)
            if self.outcome(result, "the report"):
                self.p.print(f"  report {report.name} written")

    def solve(self, words: list[str]):
        if self.file is None:
            self.p.print("  no section yet: define quick, or open FILE")
            return
        self.solve_file(words, self.file)

    def do_undo(self, words: list[str]):
        u = self.undo
        if u is None:
            self.p.print("  nothing to undo")
            return
        if u.before is None:
            self.undo, self.file = None, u.current
            back = f"; back to {u.current.name}" if u.current else ""
            self.p.print(f"  {u.what} made {u.file.name}, which stays as it is{back}")
            return
        tmp = u.file.with_name(f".{u.file.name}.undo.tmp")
        tmp.write_bytes(u.before)
        os.replace(tmp, u.file)
        self.undo, self.file = None, u.current or u.file
        report = report_for(u.file)
        result = run_step(self.command([], input_file=u.file, report=report,
                                       screen=f"undo of {u.what}"), self.p)
        self.p.print(f"  undone: {u.file.name} is as it was before {u.what}")
        if self.outcome(result, "the report after undo"):
            self.p.print(f"  report {report.name} updated")

    def report(self, words: list[str]):
        if self.file is None or not report_for(self.file).exists():
            self.p.print("  no report yet")
            return
        webbrowser.open(report_for(self.file).resolve().as_uri())

    def help(self, words: list[str]):
        if not words:
            self.p.print(HELP)
        elif words[0].lower() == "define" and len(words) == 1:
            self.p.print(define_help())
        elif words[0].lower() == "define":
            d = catalogue.BY_NOUN.get(words[1].lower())
            self.p.print(catalogue.help_text(d) if d else f"  no dialog {words[1]!r}")
        else:
            self.p.print(HELP)


def define_help() -> str:
    lines = ["define NOUN: set part of the section, question by question. Enter keeps the",
             "value shown."]
    for d in catalogue.DIALOGS:
        lines.append(f"  {d.noun + (' add|modify|delete [NAME]' if d.kind == 'list' else ''):<34}"
                     f"{d.summary}")
    lines.append("At the session's prompt, help define NOUN lists a dialog's questions.")
    return "\n".join(lines)
