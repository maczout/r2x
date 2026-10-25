"""python -m r2x.worker INPUT RECORD [--stage STAGES]  — solve one input and write its raw record.

Needs Wine, Xvfb and mingw-w64 (see docs/development.md). Progress goes to stderr in the fixed
form of r2x.progress. Exit status: 0 solved, 1 failed, 2 usage error, 3 out of scope.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from r2x.progress import FAILED, OUT_OF_SCOPE, SOLVED, USAGE, Event
from r2x.stages import StageError, parse_stages
from r2x.worker.runner import run_job
from r2x.worker.session import OutOfScope, R2xError


def report(event: Event):
    print(event.line(), file=sys.stderr, flush=True)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m r2x.worker", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", type=Path)
    p.add_argument("record", type=Path, help="raw record file to write (e.g. Newbeam.r2x.txt)")
    p.add_argument("--stage", default="peak", metavar="STAGES",
                   help="stages for the detail views: peak, all, or numbers and ranges "
                        "(default: peak)")
    p.add_argument("--response-dir", type=Path, default=os.environ.get("R2X_RESPONSE_DIR"),
                   help="Response-2000 program folder (default: $R2X_RESPONSE_DIR)")
    p.add_argument("--prefix", type=Path,
                   default=os.environ.get("R2X_WINEPREFIX", Path.home() / ".cache/r2x/prefix"),
                   help="Wine prefix (default: $R2X_WINEPREFIX or ~/.cache/r2x/prefix)")
    p.add_argument("--display", help="use this X display instead of starting Xvfb")
    a = p.parse_args(argv)
    if not a.response_dir:
        p.error("--response-dir or $R2X_RESPONSE_DIR is required")
    try:
        stages = parse_stages(a.stage)
    except StageError as e:
        p.error(f"--stage: {e}")

    t0 = time.monotonic()
    try:
        run_job(a.input, a.record, a.response_dir, Path(a.prefix), a.display, stages=stages,
                on_event=report)
    except OutOfScope as e:
        report(Event("out-of-scope", str(e)))
        return OUT_OF_SCOPE
    except StageError as e:
        report(Event("usage", str(e)))
        return USAGE
    except R2xError as e:
        report(Event("failed", str(e)))
        return FAILED
    report(Event("wrote", str(a.record), seconds=time.monotonic() - t0))
    return SOLVED


if __name__ == "__main__":
    raise SystemExit(main())
