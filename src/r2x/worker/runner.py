"""Run one job: a fresh copy of Response-2000 under Wine on a virtual display, then export."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
import time
from contextlib import ExitStack
from pathlib import Path
from typing import Callable

from r2x import __version__, record, report as html_report
from r2x.progress import Event, note
from r2x.settings import Settings
from r2x.stages import PEAK, StageSpec, format_ranges
from r2x.views import ALL, format_views
from r2x.worker import dialogs
from r2x.worker.export import export
from r2x.worker.prefix import prepare_prefix
from r2x.worker.session import Cpu, Helper, R2xError, Session, wait_until, wine_path

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
                        "-luser32", "-lgdi32"], check=True)
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


# A Response document with this name in the program folder is its template for new sections.
TEMPLATE = "r2k.r2k"
NEW_INPUT = "File > New"      # input-name in the record header when there is no input file


def run_job(input_file: Path | None, out: Path, response_dir: Path, prefix: Path,
            display: str | None = None, stages: StageSpec = PEAK,
            settings: Settings = Settings(), cache: Path | None = None,
            on_event: Callable[[Event], None] = lambda e: None,
            report: Path | None = None, views=ALL, more_detail: int | str = 0) -> dict[str, str]:
    """Solve input_file in Response-2000 and write its raw record to the file out.

    views: the detail views to capture (r2x.views), each at every stage in stages.
    more_detail: Solve > More Detail presses after the solve, or "max" (r2x.settings).

    With no input file, Response starts empty and the section is defined by accepting every
    default of Quick Define, as File > New does (docs/cli.md). Settings are applied through
    Response's dialogs before solving, and the settings in effect are read back into the header.
    The record is written only once the export is complete, under a temporary name first, so a
    failed job leaves no file behind. With report, an HTML report (r2x/report.py) of the inputs
    and the peak stage is written there too, before the record. Returns the record header.
    """
    input_file = Path(input_file) if input_file is not None else None
    out = Path(out)
    response_dir = Path(response_dir)
    exe = response_dir / "r2k.exe"
    if not exe.is_file():
        raise R2xError(f"no r2k.exe in {response_dir}")
    report = Path(report) if report is not None else None
    for path, what in ((out, "the record"), (report, "the report")):
        if path is not None and not path.parent.is_dir():
            raise R2xError(f"no folder {path.parent} to write {what} in")
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
        session = Session(helper, note=lambda text: on_event(note(text)), cpu=Cpu(r2k.pid))
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
        pictures, inputs = None, {}
        if report is not None:
            pictures = job / "pictures"
            pictures.mkdir()
            inputs["input/screen"] = session.snapshot(pictures, settled=True)
        effective, shots = dialogs.read(session, pictures)
        inputs.update(shots)
        result = export(session, stages, views, on_event, pictures, more_detail)

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
        "more-detail": str(result.more_detail),
        "views": format_views(views),
        "stage-count": str(result.stage_count),
        "peak-stage": str(result.peak),
        "detail-stages": format_ranges(result.stages),
    }
    data = record.encode(header, result.sections)
    files = [(out, data)]
    if report is not None:
        page = html_report.build(record.decode(data), {**inputs, **result.pictures})
        files.insert(0, (report, page.encode("utf-8")))
    write_files(files)
    return header


def write_files(files: list[tuple[Path, bytes]]):
    """Write each file under a temporary name, then rename them in order, so a reader never sees
    a partial file and the last file (the record) appears only once the others are in place."""
    tmps = [path.with_name(f".{path.name}.{os.getpid()}.tmp") for path, _ in files]
    try:
        for tmp, (_, data) in zip(tmps, files):
            tmp.write_bytes(data)
        for tmp, (path, _) in zip(tmps, files):
            os.replace(tmp, path)
    except PermissionError:
        folder = next(path.parent for path, _ in files)
        raise R2xError(f"cannot write to {folder} (uid {os.getuid()} needs write access)")
    finally:
        for tmp in tmps:
            tmp.unlink(missing_ok=True)
