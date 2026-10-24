"""python -m r2x.worker.info — print the versions this image runs with, as JSON."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

from r2x import __version__


def main() -> int:
    response = Path(os.environ.get("R2X_RESPONSE_DIR", "/opt/response"))
    exe = response / "r2k.exe"
    print(json.dumps({
        "r2x_version": __version__,
        "wine_version": subprocess.run(["wine", "--version"], capture_output=True,
                                       text=True).stdout.strip(),
        "response_exe_sha256": hashlib.sha256(exe.read_bytes()).hexdigest() if exe.is_file()
                               else None,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
