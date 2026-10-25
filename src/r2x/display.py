"""What the command line shows on stderr while it solves.

On a terminal: one status line with a spinner, redrawn in place, and a permanent line per input
as it finishes. Otherwise (a log file, a pipe): the permanent lines only. With --quiet: errors
only. stdout is never touched, so --stdout can carry the record. Standard library only.
"""

from __future__ import annotations

import shutil
import threading
import time
from dataclasses import dataclass, field
from typing import TextIO

from r2x.progress import FAILED, OUT_OF_SCOPE, SOLVED, USAGE, Event

SPINNER = "|/-\\"
TICK = 0.1


@dataclass
class Job:
    name: str                      # input file stem, as shown in brackets
    state: str = "waiting"
    started: float | None = None
    status: int | None = None      # exit status once finished
    reason: str = ""               # why it did not solve
    solved: Event | None = None    # the worker's "solved" event
    notes: list[str] = field(default_factory=list)


class Display:
    def __init__(self, stream: TextIO, live: bool, quiet: bool = False):
        self.stream = stream
        self.quiet = quiet
        self.live = live and not quiet
        self.lock = threading.Lock()
        self.jobs: list[Job] = []
        self._drawn = 0          # width of the status line on screen
        self._frame = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # -- lifecycle ----------------------------------------------------------------------------
    def __enter__(self):
        if self.live:
            self._thread = threading.Thread(target=self._spin, daemon=True, name="spinner")
            self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        if self._thread:
            self._thread.join()
        with self.lock:
            self._clear()
            self.stream.flush()

    def _spin(self):
        while not self._stop.wait(TICK):
            self.tick()

    # -- events from the jobs -----------------------------------------------------------------
    def add(self, name: str) -> Job:
        job = Job(name)
        with self.lock:
            self.jobs.append(job)
        return job

    def start(self, job: Job):
        with self.lock:
            job.started, job.state = time.monotonic(), "starting"
            self._draw()

    def event(self, job: Job, e: Event):
        with self.lock:
            if e.kind == "solving":
                job.state = "solving"
            elif e.kind == "solved":
                job.solved = e
                job.state = f"solved: {e.count} stages, peak {e.stage}"
            elif e.kind == "stage":
                job.state = f"stage {e.stage} ({e.done}/{e.total})"
            elif e.kind == "note":
                job.notes.append(e.text)
                if not self.quiet:
                    self._print(f"[{job.name}] note: {e.text}")
            self._draw()

    def finish(self, job: Job, status: int, reason: str = "", where: str = ""):
        """Report the input's outcome: where its record went, or why there is none."""
        seconds = time.monotonic() - job.started if job.started else 0.0
        with self.lock:
            job.status, job.reason, job.state = status, reason, "done"
            if status == SOLVED:
                if not self.quiet:
                    what = (f"solved: {job.solved.count} stages, peak {job.solved.stage}"
                            if job.solved else "solved")
                    self._print(f"[{job.name}] {what} -> {where} ({seconds:.1f} s)")
            else:
                label = {USAGE: "usage error", OUT_OF_SCOPE: "out of scope"}.get(status, "failed")
                self._print(f"[{job.name}] {label}: {reason}")
            self._draw()

    def summary(self):
        """One closing line when there were several inputs."""
        if self.quiet or len(self.jobs) < 2:
            return
        counts = {s: sum(j.status == s for j in self.jobs)
                  for s in (SOLVED, FAILED, USAGE, OUT_OF_SCOPE)}
        parts = [f"{counts[SOLVED]} of {len(self.jobs)} solved"]
        parts += [f"{counts[s]} {label}" for s, label in
                  ((FAILED, "failed"), (USAGE, "usage error"), (OUT_OF_SCOPE, "out of scope"))
                  if counts[s]]
        with self.lock:
            self._print("r2x: " + ", ".join(parts))

    # -- drawing ------------------------------------------------------------------------------
    def tick(self):
        with self.lock:
            self._frame += 1
            self._draw()

    def status_line(self) -> str:
        running = [j for j in self.jobs if j.started is not None and j.status is None]
        done = sum(j.status is not None for j in self.jobs)
        if not running:
            return ""
        now = time.monotonic()
        parts = [f"[{j.name}] {j.state}, {now - j.started:.0f} s" for j in running]
        head = f"{SPINNER[self._frame % len(SPINNER)]} "
        if len(self.jobs) > 1:
            head += f"{done}/{len(self.jobs)} done  "
        return head + "  ".join(parts)

    def _draw(self):
        if not self.live:
            return
        width = max(10, shutil.get_terminal_size((80, 24)).columns - 1)
        line = self.status_line()[:width]
        # Overwrite in place with spaces, not escape codes, so any Windows console copes.
        self.stream.write("\r" + line.ljust(self._drawn) + "\r" + line)
        self.stream.flush()
        self._drawn = len(line)

    def _clear(self):
        if self.live and self._drawn:
            self.stream.write("\r" + " " * self._drawn + "\r")
            self._drawn = 0

    def _print(self, text: str):
        self._clear()
        self.stream.write(text + "\n")
        self.stream.flush()
