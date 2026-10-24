"""python -m r2x.worker INPUT.r2t OUTDIR  — run one job locally (needs Wine, Xvfb, mingw-w64)."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from r2x.worker.runner import run_job
from r2x.worker.session import R2xError


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m r2x.worker", description=__doc__)
    p.add_argument("input", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--response-dir", type=Path, default=os.environ.get("R2X_RESPONSE_DIR"),
                   help="Response-2000 program folder (default: $R2X_RESPONSE_DIR)")
    p.add_argument("--prefix", type=Path,
                   default=os.environ.get("R2X_WINEPREFIX", Path.home() / ".cache/r2x/prefix"),
                   help="Wine prefix (default: $R2X_WINEPREFIX or ~/.cache/r2x/prefix)")
    p.add_argument("--display", help="use this X display instead of starting Xvfb")
    a = p.parse_args(argv)
    if not a.response_dir:
        p.error("--response-dir or $R2X_RESPONSE_DIR is required")

    name = a.input.stem
    t0 = time.monotonic()

    def progress(msg):
        print(f"[{name}] {msg}", file=sys.stderr, flush=True)

    def on_stage(i, n):
        if i == n or i % 10 == 0:
            progress(f"exported stage {i}/{n}")

    try:
        run_job(a.input, a.out, a.response_dir, Path(a.prefix), a.display,
                progress=progress, on_stage=on_stage)
    except R2xError as e:
        progress(f"failed: {e}")
        return 1
    progress(f"done in {time.monotonic() - t0:.1f} s -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
