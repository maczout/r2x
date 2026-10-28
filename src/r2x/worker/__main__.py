"""python -m r2x.worker (INPUT | --new) RECORD [options]  — solve one input and write its record.
python -m r2x.worker define NOUN [ACTION [NAME]] [options]  — one define step (r2x.worker.define).

With --new instead of an input, the section is a new one with Quick Define's defaults, as
File > New gives.

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
from r2x.settings import FACTORS, UNITS, Settings, parse_loads, parse_more_detail
from r2x.stages import StageError, parse_stages
from r2x.views import ViewError, parse_views
from r2x.worker.runner import run_job
from r2x.worker.session import OutOfScope, R2xError


def report(event: Event):
    print(event.line(), file=sys.stderr, flush=True)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["define"]:
        from r2x.worker.define import main as define_main
        return define_main(argv[1:])
    p = argparse.ArgumentParser(prog="python -m r2x.worker", description=__doc__,
                                usage="%(prog)s (INPUT | --new) RECORD [options]",
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("paths", nargs="+", type=Path, metavar="PATH",
                   help="input file (left out with --new) and the raw record file to write")
    p.add_argument("--new", action="store_true",
                   help="no input: a new section with Quick Define's defaults (File > New)")
    p.add_argument("--stage", default="peak", metavar="STAGES",
                   help="stages for the detail views: peak, all, or numbers and ranges "
                        "(default: peak)")
    p.add_argument("--views", default="all", metavar="VIEWS",
                   help="detail views: all, or any of general, cracking, reinforcement, "
                        "no-shear (default: all)")
    p.add_argument("--units", choices=UNITS, help="override the input's units")
    p.add_argument("--factors", choices=FACTORS, help="override the input's material factors")
    p.add_argument("--initial", metavar="N,M,V",
                   help="override the initial load (units in effect)")
    p.add_argument("--increment", metavar="N,M,V", help="override the load increment")
    p.add_argument("--more-detail", default="0", metavar="N",
                   help="Solve > More Detail presses after the solve, or max (default: 0)")
    p.add_argument("--report", type=Path, metavar="HTML",
                   help="also write an HTML report of the peak stage to this file")
    p.add_argument("--response-dir", type=Path, default=os.environ.get("R2X_RESPONSE_DIR"),
                   help="Response-2000 program folder (default: $R2X_RESPONSE_DIR)")
    p.add_argument("--prefix", type=Path,
                   default=os.environ.get("R2X_WINEPREFIX", Path.home() / ".cache/r2x/prefix"),
                   help="Wine prefix (default: $R2X_WINEPREFIX or ~/.cache/r2x/prefix)")
    p.add_argument("--display", help="use this X display instead of starting Xvfb")
    a = p.parse_args(argv)
    if len(a.paths) != (1 if a.new else 2):
        p.error("give RECORD with --new, otherwise INPUT and RECORD")
    a.input, a.record = (None, a.paths[0]) if a.new else a.paths
    if not a.response_dir:
        p.error("--response-dir or $R2X_RESPONSE_DIR is required")
    try:
        stages = parse_stages(a.stage)
    except StageError as e:
        p.error(f"--stage: {e}")
    try:
        views = parse_views(a.views)
    except ViewError as e:
        p.error(f"--views: {e}")
    try:
        settings = Settings(a.units, a.factors,
                            parse_loads(a.initial) if a.initial is not None else None,
                            parse_loads(a.increment) if a.increment is not None else None)
        more_detail = parse_more_detail(a.more_detail)
    except ValueError as e:
        p.error(str(e))

    t0 = time.monotonic()
    try:
        run_job(a.input, a.record, a.response_dir, Path(a.prefix), a.display, stages=stages,
                settings=settings, on_event=report, report=a.report, views=views,
                more_detail=more_detail)
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
