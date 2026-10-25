"""r2x command line: runs the r2x container once per input file.

On Windows the container runs in Docker inside WSL (`wsl --exec docker ...`); elsewhere `docker` is
called directly. Standard library only.

Environment:
  R2X_IMAGE        image name (default r2x)
  R2X_DOCKER       command that runs docker, e.g. "sudo docker" (default: see above)
  R2X_WSL_DISTRO   WSL distribution with Docker (default: WSL's default distribution)
"""

from __future__ import annotations

import argparse
import glob
import os
import shlex
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PureWindowsPath

from r2x import __version__

DEFAULT_IMAGE = "r2x"
_print_lock = threading.Lock()


def say(line: str):
    with _print_lock:
        print(line, file=sys.stderr, flush=True)


# -- docker -------------------------------------------------------------------------------------
def wsl_prefix() -> list[str]:
    distro = os.environ.get("R2X_WSL_DISTRO")
    return ["wsl"] + (["-d", distro] if distro else []) + ["--exec"]


def docker_command() -> list[str]:
    if os.environ.get("R2X_DOCKER"):
        return shlex.split(os.environ["R2X_DOCKER"])
    return wsl_prefix() + ["docker"] if os.name == "nt" else ["docker"]


def windows_to_wsl(path: str, automount: str = "/mnt") -> str:
    """C:\\Users\\x\\a b.r2t -> /mnt/c/Users/x/a b.r2t (WSL's default drive mounts)."""
    p = PureWindowsPath(path)
    if not p.drive or not p.drive.endswith(":") or len(p.drive) != 2:
        raise SystemExit(f"r2x: cannot map {path} into WSL (only drive-letter paths are supported)")
    return f"{automount}/{p.drive[0].lower()}/" + "/".join(p.parts[1:])


def docker_path(p: Path) -> str:
    """Path as the Docker daemon sees it."""
    p = p.resolve()
    if os.name == "nt" and not os.environ.get("R2X_DOCKER"):
        return windows_to_wsl(str(p))
    return str(p)


# -- inputs -------------------------------------------------------------------------------------
def expand_inputs(patterns: list[str]) -> list[Path]:
    """Expand globs here: PowerShell and cmd pass *.r2t through unexpanded."""
    out: list[Path] = []
    for pat in patterns:
        matches = sorted(glob.glob(pat)) if glob.has_magic(pat) else [pat]
        if not matches:
            raise SystemExit(f"r2x: no files match {pat}")
        for m in matches:
            p = Path(m)
            if not p.is_file():
                raise SystemExit(f"r2x: not a file: {m}")
            if p.resolve() not in [q.resolve() for q in out]:
                out.append(p)
    return out


def output_dir(inp: Path, out: Path | None) -> Path:
    """The raw record's path (docs/raw-format.md)."""
    return (out if out else inp.parent) / f"{inp.stem}.r2x.txt"


# -- commands -----------------------------------------------------------------------------------
def solve_one(inp: Path, dest: Path, image: str) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = docker_command() + [
        "run", "--rm", "--pull", "never", "--network", "none",
        "-v", f"{docker_path(inp)}:/in/{inp.name}:ro",
        "-v", f"{docker_path(dest.parent)}:/out",
        image, "python", "-m", "r2x.worker", f"/in/{inp.name}", f"/out/{dest.name}",
    ]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
                                encoding="utf-8", errors="replace")
    except FileNotFoundError:
        say(f"[{inp.stem}] failed: cannot run {cmd[0]!r}"
            + (" (is WSL installed?)" if os.name == "nt" else " (is Docker installed?)"))
        return False
    for line in proc.stderr:
        line = line.rstrip()
        if line:
            line = line.removeprefix("r2x: ").replace(f"/out/{dest.name}", str(dest))
            say(f"[{inp.stem}] {line}")
    return proc.wait() == 0


def cmd_solve(a) -> int:
    inputs = expand_inputs(a.inputs)
    dests = [output_dir(i, a.out) for i in inputs]
    clash = {d for d in dests if dests.count(d) > 1}
    if clash:
        raise SystemExit(f"r2x: several inputs would write {sorted(map(str, clash))[0]}")
    for d in dests:
        if d.exists():
            if not a.force:
                raise SystemExit(f"r2x: {d} exists (use --force to replace it)")
            d.unlink()
    with ThreadPoolExecutor(max_workers=max(1, a.jobs)) as pool:
        ok = list(pool.map(lambda pair: solve_one(*pair, a.image), zip(inputs, dests)))
    failed = ok.count(False)
    if len(inputs) > 1:
        say(f"r2x: {len(inputs) - failed} of {len(inputs)} solved")
    return 1 if failed else 0


def cmd_health(a) -> int:
    cmd = docker_command() + ["run", "--rm", "--pull", "never", "--network", "none", a.image,
                              "python", "-m", "r2x.worker.info"]
    print(f"r2x client {__version__}; image {a.image}; docker: {' '.join(docker_command())}")
    try:
        return subprocess.run(cmd).returncode
    except FileNotFoundError:
        print(f"cannot run {cmd[0]!r}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="r2x", description="Run Response-2000 from the command line.")
    p.add_argument("--version", action="version", version=f"r2x {__version__}")
    p.add_argument("--image", default=os.environ.get("R2X_IMAGE", DEFAULT_IMAGE),
                   help="container image (default: $R2X_IMAGE or r2x)")
    sub = p.add_subparsers(dest="command", required=True)

    solve = sub.add_parser("solve", help="solve input files and export their data")
    solve.add_argument("inputs", nargs="+", help="one or more input files, or globs")
    solve.add_argument("--out", type=Path, help="folder for the results (default: next to each input)")
    solve.add_argument("-j", "--jobs", type=int, default=1, help="inputs to run at once (default 1)")
    solve.add_argument("--force", action="store_true", help="replace existing result folders")
    solve.set_defaults(func=cmd_solve)

    health = sub.add_parser("health", help="show the image's r2x, Wine and Response-2000 versions")
    health.set_defaults(func=cmd_health)
    return p


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
