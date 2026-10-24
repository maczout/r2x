"""Run one job: a fresh copy of Response-2000 under Wine on a virtual display, then export."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from contextlib import ExitStack
from pathlib import Path
from typing import Callable

from r2x import __version__
from r2x.worker.export import export_all
from r2x.worker.session import Helper, R2xError, Session

HELPER_SOURCE = Path(__file__).with_name("helper.c")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ensure_helper(cache: Path) -> Path:
    """Path to helper.exe: $R2X_HELPER if set, otherwise built from helper.c into cache."""
    if os.environ.get("R2X_HELPER"):
        return Path(os.environ["R2X_HELPER"])
    exe = cache / f"helper-{sha256(HELPER_SOURCE)[:12]}.exe"
    if not exe.exists():
        cache.mkdir(parents=True, exist_ok=True)
        tmp = exe.with_suffix(".tmp")
        subprocess.run(["i686-w64-mingw32-gcc", "-O2", "-o", str(tmp), str(HELPER_SOURCE),
                        "-luser32"], check=True)
        tmp.replace(exe)
    return exe


def start_xvfb(first: int = 99, tries: int = 20) -> tuple[subprocess.Popen, str]:
    """Start Xvfb on a free display number from :99 up; return the process and DISPLAY value.

    Numbers are chosen here rather than with Xvfb's own search, which starts at :0 and can trip
    over a display server it cannot use (WSLg holds :0 under WSL).
    """
    errors = []
    for n in range(first, first + tries):
        if os.path.exists(f"/tmp/.X{n}-lock") or os.path.exists(f"/tmp/.X11-unix/X{n}"):
            continue
        r, w = os.pipe()  # Xvfb writes the display number here once it accepts connections
        proc = subprocess.Popen(["Xvfb", f":{n}", "-displayfd", str(w), "-screen", "0",
                                 "1920x1080x24", "-nolisten", "tcp"], pass_fds=(w,),
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        os.close(w)
        with os.fdopen(r) as f:
            ready = f.readline().strip()
        if ready:
            proc.stderr.close()
            return proc, f":{n}"
        proc.wait(10)
        errors.append(f":{n}: " + proc.stderr.read().decode(errors="replace").strip()[-300:])
    raise R2xError("Xvfb did not start. " + " | ".join(errors[-2:]))


def wine_path(p: Path) -> str:
    return "Z:" + str(p.resolve()).replace("/", "\\")


def run_job(input_r2t: Path, out: Path, response_dir: Path, prefix: Path,
            display: str | None = None, cache: Path | None = None,
            progress: Callable[[str], None] = print,
            on_stage: Callable[[int, int], None] = lambda i, n: None) -> dict:
    """Solve input_r2t in Response-2000 and write the full export to out. Returns the manifest."""
    input_r2t, out = Path(input_r2t), Path(out)
    response_dir = Path(response_dir)
    exe = response_dir / "r2k.exe"
    if not exe.is_file():
        raise R2xError(f"no r2k.exe in {response_dir}")
    cache = cache or Path.home() / ".cache" / "r2x"
    helper_exe = ensure_helper(cache)

    with ExitStack() as stack:
        env = dict(os.environ, WINEPREFIX=str(prefix), WINEARCH="win32", WINEDEBUG="-all")
        if display:
            env["DISPLAY"] = display
        else:
            xvfb, env["DISPLAY"] = start_xvfb()
            stack.callback(lambda: (xvfb.terminate(), xvfb.wait(10)))
        if not (prefix / "system.reg").exists():
            progress("creating Wine prefix (first run only)")
            subprocess.run(["wineboot", "-i"], env=env, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        stack.callback(lambda: subprocess.run(["wineserver", "-k"], env=env,
                                              stderr=subprocess.DEVNULL))

        # Each job gets its own copy of the program folder (Response writes Response.ini there).
        job = Path(tempfile.mkdtemp(prefix="r2x-job-"))
        stack.callback(shutil.rmtree, job, ignore_errors=True)
        shutil.copytree(response_dir, job / "Response")
        job_input = job / input_r2t.name
        shutil.copyfile(input_r2t, job_input)

        r2k = subprocess.Popen(["wine", "r2k.exe", wine_path(job_input)], cwd=job / "Response",
                               env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        def stop_response():  # runs before the helper closes and the prefix is shut down
            subprocess.run(["wineserver", "-k"], env=env, stderr=subprocess.DEVNULL)
            r2k.wait(10)
        stack.callback(stop_response)
        helper = Helper(str(helper_exe), env)
        stack.callback(helper.close)
        session = Session(helper)
        session.wait_for_file(input_r2t.stem)
        time.sleep(0.2)
        session.check_no_dialog()

        out.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(input_r2t, out / "input.r2t")
        n = export_all(session, out, progress, on_stage)

    wine_version = subprocess.run(["wine", "--version"], capture_output=True, text=True).stdout.strip()
    files = sorted(str(p.relative_to(out)).replace(os.sep, "/") for p in out.rglob("*")
                   if p.is_file() and p.name != "manifest.json")
    manifest = {
        "r2x_version": __version__,
        "response_exe_sha256": sha256(exe),
        "wine_version": wine_version,
        "input_sha256": sha256(input_r2t),
        "stage_count": n,
        "files": files,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest
