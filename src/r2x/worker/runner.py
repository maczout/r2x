"""Run one job: a fresh copy of Response-2000 under Wine on a virtual display, then export."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import time
from contextlib import ExitStack
from pathlib import Path
from typing import Callable

from r2x import __version__, record
from r2x.progress import Event, note
from r2x.settings import Settings
from r2x.stages import PEAK, StageSpec, format_ranges
from r2x.worker import dialogs
from r2x.worker.export import export
from r2x.worker.session import Helper, R2xError, Session, wait_until

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


# Without a window manager (Xvfb has none), Wine waits 2 s for one each time a managed window
# such as a dialog closes. Unmanaged windows skip the wait; the exports are unchanged.
X11_DRIVER_KEY = r"HKCU\Software\Wine\X11 Driver"
_UNMANAGED = re.compile(r'\[Software\\\\Wine\\\\X11 Driver\][^\[]*"Managed"="N"')


def prepare_prefix(prefix: Path, env: dict, on_event: Callable[[Event], None]):
    """Create the Wine prefix if needed, and make sure it does not use window management."""
    if not (prefix / "system.reg").exists():
        on_event(note("creating Wine prefix (first run only)"))
        subprocess.run(["wineboot", "-i"], env=env, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    user_reg = prefix / "user.reg"
    if not (user_reg.exists() and _UNMANAGED.search(user_reg.read_text(errors="replace"))):
        subprocess.run(["wine", "reg", "add", X11_DRIVER_KEY, "/v", "Managed", "/d", "N", "/f"],
                       env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wine_path(p: Path) -> str:
    return "Z:" + str(p.resolve()).replace("/", "\\")


# A Response document with this name in the program folder is its template for new sections.
TEMPLATE = "r2k.r2k"
NEW_INPUT = "File > New"      # input-name in the record header when there is no input file


def run_job(input_file: Path | None, out: Path, response_dir: Path, prefix: Path,
            display: str | None = None, stages: StageSpec = PEAK,
            settings: Settings = Settings(), cache: Path | None = None,
            on_event: Callable[[Event], None] = lambda e: None) -> dict[str, str]:
    """Solve input_file in Response-2000 and write its raw record to the file out.

    With no input file, Response starts empty and the section is defined by accepting every
    default of Quick Define, as File > New does (docs/cli.md). Settings are applied through
    Response's dialogs before solving, and the settings in effect are read back into the header.
    An input whose loading includes shear stops here (OutOfScope). The record is written only
    once the export is complete, under a temporary name first, so a failed job leaves no file
    behind. Returns the record header.
    """
    input_file = Path(input_file) if input_file is not None else None
    out = Path(out)
    response_dir = Path(response_dir)
    exe = response_dir / "r2k.exe"
    if not exe.is_file():
        raise R2xError(f"no r2k.exe in {response_dir}")
    if not out.parent.is_dir():
        raise R2xError(f"no folder {out.parent} to write the record in")
    cache = cache or Path.home() / ".cache" / "r2x"
    helper_exe = ensure_helper(cache)

    with ExitStack() as stack:
        env = dict(os.environ, WINEPREFIX=str(prefix), WINEARCH="win32", WINEDEBUG="-all")
        if display:
            env["DISPLAY"] = display
        else:
            xvfb, env["DISPLAY"] = start_xvfb()
            stack.callback(lambda: (xvfb.terminate(), xvfb.wait(10)))
        prepare_prefix(prefix, env, on_event)
        stack.callback(lambda: subprocess.run(["wineserver", "-k"], env=env,
                                              stderr=subprocess.DEVNULL))

        # Each job gets its own copy of the program folder (Response writes Response.ini there).
        job = Path(tempfile.mkdtemp(prefix="r2x-job-"))
        stack.callback(shutil.rmtree, job, ignore_errors=True)
        shutil.copytree(response_dir, job / "Response")
        args = []
        if input_file is not None:
            job_input = job / input_file.name
            shutil.copyfile(input_file, job_input)
            args = [wine_path(job_input)]

        r2k = subprocess.Popen(["wine", "r2k.exe", *args], cwd=job / "Response",
                               env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        def stop_response():  # runs before the helper closes and the prefix is shut down
            subprocess.run(["wineserver", "-k"], env=env, stderr=subprocess.DEVNULL)
            r2k.wait(10)
        stack.callback(stop_response)
        helper = Helper(str(helper_exe), env)
        stack.callback(helper.close)
        session = Session(helper, note=lambda text: on_event(note(text)))
        if input_file is not None:
            session.wait_for_file(input_file.stem)
            time.sleep(0.2)
            session.check_no_dialog()
        else:
            wait_until(lambda: helper.try_ask("main"), 60, "Response to start", 0.1)
            time.sleep(0.2)
            session.check_no_dialog()
            dialogs.quick_define(session)
        dialogs.apply(session, settings)
        effective = dialogs.read(session)
        dialogs.check_scope(effective)
        result = export(session, stages, on_event)

    wine_version = subprocess.run(["wine", "--version"], capture_output=True, text=True).stdout.strip()
    header = {
        "r2x-version": __version__,
        "response-exe-sha256": sha256(exe),
        "wine-version": wine_version,
        **({"input-name": input_file.name, "input-sha256": sha256(input_file)} if input_file
           else {"input-name": NEW_INPUT}),
        **({"template-sha256": sha256(response_dir / TEMPLATE)}
           if input_file is None and (response_dir / TEMPLATE).is_file() else {}),
        **effective,
        "stage-count": str(result.stage_count),
        "peak-stage": str(result.peak),
        "detail-stages": format_ranges(result.stages),
    }
    data = record.encode(header, result.sections)
    tmp = out.with_name(f".{out.name}.{os.getpid()}.tmp")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, out)
    except PermissionError:
        tmp.unlink(missing_ok=True)
        raise R2xError(f"cannot write to {out.parent} (uid {os.getuid()} needs write access)")
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return header
