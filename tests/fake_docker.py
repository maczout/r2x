"""A stand-in for `docker`, for testing the command line without Docker:

    R2X_DOCKER="python tests/fake_docker.py" r2x solve ...

It reads the `docker run` command the command line builds and maps the container's /in and /out
paths back to the host folders mounted there.

FAKE_DOCKER_MODE=fake (default) imitates the worker without Wine. The input's text decides:
    fail   -> "failed", exit 1          shear  -> "out of scope", exit 3
    crash  -> a traceback, exit 1       noout  -> exit 0 without writing a record
    slow   -> takes about a second      noreport -> exit 0 without writing a report
    otherwise: 10 stages, peak 7, and a stub report if one is asked for
FAKE_DOCKER_MODE=wine runs the real worker on this machine instead, with its own copy of the Wine
prefix as each container has, so that inputs can run in parallel (needs $R2X_RESPONSE_DIR).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def parse_run(args: list[str]) -> tuple[dict[str, str], list[str]]:
    """docker run options -> ({container path: host path}, command run in the container)."""
    mounts, i = {}, 0
    while i < len(args):
        a = args[i]
        if a in ("--pull", "--network"):
            i += 2
        elif a == "-v":
            spec = args[i + 1].removesuffix(":ro")
            host, container = spec.rsplit(":", 1)
            mounts[container] = host
            i += 2
        elif a.startswith("-"):
            i += 1
        else:
            return mounts, args[i + 1:]       # args[i] is the image
    raise SystemExit("fake docker: no image in the command")


def host_path(mounts: dict[str, str], p: str) -> Path:
    if p in mounts:
        return Path(mounts[p])
    folder, _, name = p.rpartition("/")
    return Path(mounts[folder]) / name


def fake_worker(inp: Path | None, out: Path, stage: str, settings: dict[str, str],
                report: Path | None, views: str = "all") -> int:
    from r2x import record
    from r2x.progress import Event
    from r2x.stages import StageError, parse_stages
    from r2x.views import format_views, parse_views

    def say(e):
        print(e.line(), file=sys.stderr, flush=True)

    text = inp.read_text(errors="replace") if inp else ""
    name = inp.name if inp else "File > New"
    say(Event("solving"))
    if "slow" in text:
        time.sleep(1)
    if "crash" in text:
        print("Traceback (most recent call last):\nRuntimeError: boom", file=sys.stderr)
        return 1
    if "fail" in text:
        say(Event("failed", "Response shows a dialog 'Invalid File': Not a valid file format"))
        return 1
    if "shear" in text:
        say(Event("out-of-scope", "the loading includes shear"))
        return 3
    say(Event("solved", count=10, stage=7))
    try:
        targets = parse_stages(stage).resolve(10, 7)
    except StageError as e:
        say(Event("usage", str(e)))
        return 2
    sections = [("control/moment_phi", b"curve\r\n")]
    for k, i in enumerate(targets):
        sections.append((f"stage/{i}/longitudinal_strain", b"stage %d\r\n" % i))
        say(Event("stage", stage=i, done=k + 1, total=len(targets)))
    if report is not None and "noreport" not in text:
        report.write_text("<!doctype html>\n<title>fake report</title>\n", encoding="utf-8")
    if "noout" not in text:
        out.write_bytes(record.encode({"input-name": name, **settings,
                                       "views": format_views(parse_views(views)),
                                       "stage-count": "10", "peak-stage": "7"}, sections))
        say(Event("wrote", str(out), seconds=0.1))
    return 0


def wine_worker(inp: Path | None, out: Path, stage: str, settings: dict[str, str],
                report: Path | None, views: str = "all") -> int:
    template = Path(os.environ.get("R2X_WINEPREFIX", Path.home() / ".cache/r2x/prefix"))
    with tempfile.TemporaryDirectory(prefix="fake-docker-") as tmp:
        prefix = Path(tmp) / "prefix"
        if (template / "system.reg").exists():
            shutil.copytree(template, prefix, symlinks=True)
        env = dict(os.environ, R2X_WINEPREFIX=str(prefix))
        options = [f"--{k}={v}" for k, v in settings.items()]
        options += ["--report", str(report)] if report is not None else []
        source = [str(inp)] if inp else ["--new"]
        return subprocess.run([sys.executable, "-m", "r2x.worker", *source, str(out),
                               "--stage", stage, "--views", views, *options],
                              env=env).returncode


def main(argv: list[str]) -> int:
    if not argv or argv[0] != "run":
        raise SystemExit(f"fake docker: only 'run' is supported, not {argv[:1]}")
    mounts, command = parse_run(argv[1:])
    if command[:3] == ["python", "-m", "r2x.worker.info"]:
        print(json.dumps({"r2x_version": "fake", "wine_version": None}))
        return 0
    if command[:3] != ["python", "-m", "r2x.worker"]:
        raise SystemExit(f"fake docker: unexpected command {command}")
    inp = None if command[3] == "--new" else host_path(mounts, command[3])
    out = host_path(mounts, command[4])
    stage = command[command.index("--stage") + 1] if "--stage" in command else "peak"
    views = command[command.index("--views") + 1] if "--views" in command else "all"
    settings = {}                       # --units us, --initial=-2000,0 ... as the worker gets them
    rest = command[5:]
    for i, arg in enumerate(rest):
        for key in ("units", "factors", "initial", "increment"):
            if arg == f"--{key}":
                settings[key] = rest[i + 1]
            elif arg.startswith(f"--{key}="):
                settings[key] = arg.split("=", 1)[1]
    report = host_path(mounts, rest[rest.index("--report") + 1]) if "--report" in rest else None
    worker = wine_worker if os.environ.get("FAKE_DOCKER_MODE") == "wine" else fake_worker
    return worker(inp, out, stage, settings, report, views)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
