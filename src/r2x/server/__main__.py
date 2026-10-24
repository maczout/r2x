"""python -m r2x.server — run the HTTP API and its workers.

Settings (environment):
  R2X_TOKEN            required; clients send it as a bearer token
  R2X_WORKERS          number of Response instances run side by side (default 1)
  R2X_DATA             working storage for jobs and per-worker Wine prefixes (default ~/data)
  R2X_RESPONSE_DIR     Response-2000 program folder
  R2X_WINEPREFIX       prepared Wine prefix that each worker copies
  R2X_RETENTION_HOURS  how long finished jobs are kept (default 24)
  R2X_MAX_UPLOAD_MB    largest accepted input (default 5)
  R2X_PORT             listening port (default 8000)
"""

from __future__ import annotations

import hashlib
import logging
import os
import subprocess
import sys
from pathlib import Path

import uvicorn

from r2x import __version__
from r2x.server.app import create_app
from r2x.server.jobs import JobManager


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    env = os.environ
    token = env.get("R2X_TOKEN", "")
    if not token:
        print("R2X_TOKEN must be set", file=sys.stderr)
        return 2
    response_dir = Path(env.get("R2X_RESPONSE_DIR", "/opt/response"))
    exe = response_dir / "r2k.exe"
    info = {
        "r2x_version": __version__,
        "wine_version": subprocess.run(["wine", "--version"], capture_output=True,
                                       text=True).stdout.strip(),
        "response_exe_sha256": hashlib.sha256(exe.read_bytes()).hexdigest(),
    }
    manager = JobManager(
        data=Path(env.get("R2X_DATA", Path.home() / "data")),
        workers=int(env.get("R2X_WORKERS", "1")),
        response_dir=response_dir,
        template_prefix=Path(env.get("R2X_WINEPREFIX", Path.home() / "prefix")),
        retention_hours=float(env.get("R2X_RETENTION_HOURS", "24")),
    )
    manager.start()
    app = create_app(manager, token, info, int(float(env.get("R2X_MAX_UPLOAD_MB", "5")) * 2**20))
    uvicorn.run(app, host="0.0.0.0", port=int(env.get("R2X_PORT", "8000")), log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
