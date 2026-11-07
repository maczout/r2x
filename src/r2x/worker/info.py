"""python -m r2x.worker.info — print the versions this image runs with, as JSON.

Response-2000 is the user's own, mounted at $R2X_RESPONSE_DIR (r2x health mounts the linked
folder); without it, the Response keys are null.
"""

import json
import os
import subprocess
from pathlib import Path

from r2x import __version__
from r2x.response import ResponseError, read_program


def main() -> int:
    try:
        program = read_program(Path(os.environ.get("R2X_RESPONSE_DIR", "/opt/response")))
    except (ResponseError, OSError):
        program = None
    print(json.dumps({
        "r2x_version": __version__,
        "wine_version": subprocess.run(["wine", "--version"], capture_output=True,
                                       text=True).stdout.strip(),
        "response_exe_sha256": program.exe_sha256 if program else None,
        "response_verified": program.verified if program else None,
        "response_files_sha256": program.files_sha256 if program else None,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
