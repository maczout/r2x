"""r2x command line: solves each input in the r2x container and keeps its raw record.

The interface is specified in docs/cli.md. The container runs once per input: in Docker inside
WSL on Windows (`wsl --exec docker ...`), with `docker` directly elsewhere. Standard library only.

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
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PureWindowsPath

from r2x import __version__, progress
from r2x.display import Display, Job
from r2x.progress import FAILED, OUT_OF_SCOPE, SOLVED, USAGE
from r2x.settings import FACTORS, UNITS, Settings, parse_pair
from r2x.stages import StageError, StageSpec, parse_stages
from r2x.views import ViewError, format_views, parse_views

DEFAULT_IMAGE = "r2x"
RECORD_SUFFIX = ".r2x.txt"
REPORT_SUFFIX = ".r2x.html"
NEW_NAME = "newbeam"     # record name without an input: Response's name for a new section


class UsageError(Exception):
    """A problem with the command line, found before anything runs (exit status 2)."""


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
        raise UsageError(f"cannot map {path} into WSL (only drive-letter paths are supported)")
    return f"{automount}/{p.drive[0].lower()}/" + "/".join(p.parts[1:])


def docker_path(p: Path) -> str:
    """Path as the Docker daemon sees it."""
    p = p.resolve()
    if os.name == "nt" and not os.environ.get("R2X_DOCKER"):
        return windows_to_wsl(str(p))
    return str(p)


# -- inputs and outputs -------------------------------------------------------------------------
def expand_inputs(patterns: list[str]) -> list[Path]:
    """Expand globs here: PowerShell and cmd pass *.r2t through unexpanded."""
    out: list[Path] = []
    for pat in patterns:
        matches = sorted(glob.glob(pat)) if glob.has_magic(pat) else [pat]
        if not matches:
            raise UsageError(f"no files match {pat}")
        for m in matches:
            p = Path(m)
            if not p.is_file():
                raise UsageError(f"not a file: {m}")
            if p.resolve() not in [q.resolve() for q in out]:
                out.append(p)
    return out


def job_name(inp: Path | None) -> str:
    return inp.stem if inp is not None else NEW_NAME


def record_path(inp: Path | None, out: Path | None) -> Path:
    """Where the input's raw record goes (docs/raw-format.md); without an input, the current
    folder."""
    folder = out if out else (inp.parent if inp is not None else Path("."))
    return folder / f"{job_name(inp)}{RECORD_SUFFIX}"


def report_path(record: Path) -> Path:
    """The report goes next to the record: NAME.r2x.html."""
    return record.with_name(record.name.removesuffix(RECORD_SUFFIX) + REPORT_SUFFIX)


def overall_status(statuses: list[int]) -> int:
    """The most serious outcome: failed, then usage error, then out of scope, then solved."""
    for s in (FAILED, USAGE, OUT_OF_SCOPE):
        if s in statuses:
            return s
    return SOLVED


# -- one input ----------------------------------------------------------------------------------
def container_command(inp: Path | None, record: Path, stages: StageSpec, settings: Settings,
                      image: str, report: Path | None = None, views=None) -> list[str]:
    """docker run for one input; without an input the worker defines a new section (--new).
    The report, if any, goes in the record's folder."""
    mounts = ["-v", f"{docker_path(inp)}:/in/{inp.name}:ro"] if inp is not None else []
    worker_input = [f"/in/{inp.name}"] if inp is not None else ["--new"]
    return docker_command() + [
        "run", "--rm", "--pull", "never", "--network", "none", *mounts,
        "-v", f"{docker_path(record.parent)}:/out",
        image, "python", "-m", "r2x.worker", *worker_input, f"/out/{record.name}",
        "--stage", str(stages), *(["--views", format_views(views)] if views else []),
        *settings.args(),
        *(["--report", f"/out/{report.name}"] if report is not None else []),
    ]


def run_container(inp: Path | None, record: Path, stages: StageSpec, settings: Settings,
                  image: str, display: Display, job: Job,
                  report: Path | None = None, views=None) -> tuple[int, str]:
    """Solve one input in its own container; return its exit status and, if it failed, why."""
    cmd = container_command(inp, record, stages, settings, image, report, views)
    display.start(job)
    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE, text=True, encoding="utf-8",
                                errors="replace")
    except FileNotFoundError:
        hint = "is WSL installed?" if os.name == "nt" else "is Docker installed?"
        return FAILED, f"cannot run {cmd[0]!r} ({hint})"
    reason, other = "", []
    for line in proc.stderr:
        e = progress.parse(line)
        if e is None:
            if line.strip():
                other.append(line.rstrip())
        elif e.kind in ("failed", "usage", "out-of-scope"):
            reason = e.text
        elif e.kind != "wrote":
            display.event(job, e)
    code = proc.wait()
    if code == SOLVED:
        for path in (record, report):
            if path is not None and not path.is_file():
                return FAILED, f"the container finished but wrote no {path.name}"
        return SOLVED, ""
    if code in (FAILED, USAGE, OUT_OF_SCOPE) and reason:
        return code, reason
    detail = " / ".join(other[-3:]) if other else "no message"
    return FAILED, f"exit status {code}: {detail}"


# -- commands -----------------------------------------------------------------------------------
def settings_from(a) -> Settings:
    return Settings(a.units, a.factors, a.initial, a.increment)


def check_solve_args(a) -> None:
    for flag in ("out", "report"):
        if a.stdout and getattr(a, flag):
            raise UsageError(f"--stdout writes no files, so --{flag} does not apply")


def cmd_solve(a) -> int:
    check_solve_args(a)
    inputs: list[Path | None] = expand_inputs(a.inputs) if a.inputs else [None]
    live = sys.stderr.isatty()
    if a.stdout:
        if len(inputs) != 1:
            raise UsageError(f"--stdout takes one input; {len(inputs)} given")
        return solve_to_stdout(inputs[0], a, live)

    records = [record_path(i, a.out) for i in inputs]
    reports = [report_path(r) if a.report else None for r in records]
    clash = sorted({str(r) for r in records if records.count(r) > 1})
    if clash:
        raise UsageError(f"several inputs would write {clash[0]}")
    existing = [p for p in records + reports if p is not None and p.exists()]
    if existing and not a.overwrite:
        more = f" (and {len(existing) - 1} more)" if len(existing) > 1 else ""
        raise UsageError(f"{existing[0]} exists{more}; use --overwrite to replace")
    if a.out:
        a.out.mkdir(parents=True, exist_ok=True)
    for p in existing:
        p.unlink()

    with Display(sys.stderr, live, a.quiet) as display:
        jobs = [display.add(job_name(i)) for i in inputs]

        def solve(k: int) -> int:
            status, reason = run_container(inputs[k], records[k], a.stage, settings_from(a),
                                           a.image, display, jobs[k], reports[k], a.views)
            where = str(records[k]) + (f", {reports[k].name}" if reports[k] else "")
            display.finish(jobs[k], status, reason, where)
            return status

        with ThreadPoolExecutor(max_workers=a.parallel) as pool:
            statuses = list(pool.map(solve, range(len(inputs))))
        display.summary()
    return overall_status(statuses)


def solve_to_stdout(inp: Path | None, a, live: bool) -> int:
    """Solve into a temporary folder, then copy the record's bytes to stdout unchanged."""
    with tempfile.TemporaryDirectory(prefix="r2x-") as tmp:
        record = Path(tmp) / f"{job_name(inp)}{RECORD_SUFFIX}"
        with Display(sys.stderr, live, a.quiet) as display:
            job = display.add(job_name(inp))
            status, reason = run_container(inp, record, a.stage, settings_from(a), a.image,
                                           display, job, views=a.views)
            display.finish(job, status, reason, "stdout")
        if status == SOLVED:
            # The binary buffer, so that Windows cannot rewrite the record's line endings.
            try:
                with open(record, "rb") as f:
                    shutil.copyfileobj(f, sys.stdout.buffer)
                sys.stdout.buffer.flush()
            except BrokenPipeError:
                os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
                return FAILED
    return status


def cmd_health(a) -> int:
    cmd = docker_command() + ["run", "--rm", "--pull", "never", "--network", "none", a.image,
                              "python", "-m", "r2x.worker.info"]
    print(f"r2x client {__version__}; image {a.image}; docker: {' '.join(docker_command())}")
    try:
        return subprocess.run(cmd).returncode
    except FileNotFoundError:
        print(f"cannot run {cmd[0]!r}", file=sys.stderr)
        return FAILED


# -- arguments ----------------------------------------------------------------------------------
SOLVE_DESCRIPTION = """\
Run a full sectional response in Response-2000 1.9.7 and capture the data
from its control charts and detail views.

Scope: axial load and moment. Not M-N interaction or full-member analysis.
r2x never edits the input file. Options override the input. Options you
leave out keep the input's value, or Response's start-up default if the
input has none."""

SOLVE_EPILOG = """\
Results (NAME is the input file name, or newbeam without one):
  NAME.r2x.txt          Raw record: exported chart data, byte for byte, with
                        versions, input SHA-256 and the settings in effect.
  NAME.r2x.html         Report (--report only).

Exit status: 0 solved · 1 failed · 2 usage error · 3 out of scope
With several inputs, the most serious: 1, then 2, then 3.

Examples:
  r2x solve
  r2x solve beam.r2t --report
  r2x solve beam.r2t --stage all
  r2x solve beam.r2t --views cracking,no-shear
  r2x solve col.rsp --units si --initial -2000,0 --increment 0,1
  r2x solve cases\\*.r2t --out results --parallel 4
  r2x solve beam.r2t --stdout | py parse.py"""


class HelpFormatter(argparse.RawTextHelpFormatter):
    """Help laid out as in docs/cli.md: `-p, --parallel N`, `INPUT ...`, on any Python 3.10+."""

    def __init__(self, prog):
        super().__init__(prog, max_help_position=24, width=80)

    def _format_action_invocation(self, action):
        if not action.option_strings:
            return f"{action.metavar} ..." if action.nargs in ("*", "+") else action.metavar
        names = ", ".join(action.option_strings)
        if action.nargs == 0:
            return names
        return f"{names} {self._format_args(action, action.dest.upper())}"


def stage_spec(text: str) -> StageSpec:
    try:
        return parse_stages(text)
    except StageError as e:
        raise argparse.ArgumentTypeError(str(e))


def views_spec(text: str):
    try:
        return parse_views(text)
    except ViewError as e:
        raise argparse.ArgumentTypeError(str(e))


def load_pair(text: str) -> tuple[float, float]:
    try:
        return parse_pair(text)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e))


def increment_pair(text: str) -> tuple[float, float]:
    n, m = load_pair(text)
    if n == 0 and m == 0:
        raise argparse.ArgumentTypeError("the increment cannot be 0,0")
    return n, m


def positive_int(text: str) -> int:
    try:
        n = int(text)
    except ValueError:
        n = 0
    if n < 1:
        raise argparse.ArgumentTypeError(f"{text!r}: expected a whole number, 1 or more")
    return n


def join_pair_values(argv: list[str]) -> list[str]:
    """--initial -2000,0 -> --initial=-2000,0, so argparse does not take -2000,0 for an option."""
    out, it = [], iter(argv)
    for arg in it:
        if arg in ("--initial", "--increment"):
            value = next(it, None)
            out.append(arg if value is None else f"{arg}={value}")
        else:
            out.append(arg)
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="r2x", description="Run Response-2000 from the command line.")
    p.add_argument("--version", action="version", version=f"r2x {__version__}")
    p.add_argument("--image", default=os.environ.get("R2X_IMAGE", DEFAULT_IMAGE),
                   help="container image (default: $R2X_IMAGE or r2x)")
    sub = p.add_subparsers(dest="command", required=True, metavar="{solve,health}")

    s = sub.add_parser("solve", help="solve inputs and capture their exported data",
                       usage="r2x solve [INPUT ...] [options]", description=SOLVE_DESCRIPTION,
                       epilog=SOLVE_EPILOG, formatter_class=HelpFormatter, add_help=False,
                       allow_abbrev=False)
    s.add_argument("-h", "--help", action="help", help=argparse.SUPPRESS)

    g = s.add_argument_group("Input")
    g.add_argument("inputs", nargs="*", metavar="INPUT",
                   help=".rsp or .r2t files; globs allowed (cases\\*.r2t).\n"
                        "Default: a new Quick Define section (Newbeam).")

    g = s.add_argument_group("Analysis")
    g.add_argument("--units", choices=UNITS, type=str.lower,
                   help="Units for loads and results.\n"
                        "Default: input's, else si.\n"
                        "  si     kN    kN·m    mm   MPa\n"
                        "  us     kip   kip·ft  in   psi, ksi\n"
                        "  kgcm   ton   ton·m   cm   kg/cm2, t/cm2")
    g.add_argument("--factors", choices=FACTORS, type=str.lower,
                   help="Material reduction factors.\n"
                        "Default: input's, else none.")
    g.add_argument("--initial", type=load_pair, metavar="N,M",
                   help="Initial load, in the units in effect.\n"
                        "Default: input's, else 0,0.")
    g.add_argument("--increment", type=increment_pair, metavar="N,M",
                   help="Load increment; only signs and ratio matter.\n"
                        "Default: input's, else 0,1.\n"
                        "N: tension positive. M: compression on top positive.")

    g = s.add_argument_group("Output")
    g.add_argument("--stage", type=stage_spec, default=stage_spec("peak"), metavar="STAGES",
                   help="Stages for the detail views: peak, all, or numbers\n"
                        "and ranges (0,10,20-30 or peak,0-5). 0 is the\n"
                        "initial load. Control charts always cover every\n"
                        "stage. Default: peak.")
    g.add_argument("--views", type=views_spec, default=views_spec("all"), metavar="VIEWS",
                   help="Detail views: all, or any of general, cracking,\n"
                        "reinforcement, no-shear. Default: all.")
    g.add_argument("--report", action="store_true",
                   help="Also write an HTML report of the peak stage.\n"
                        "Default: off.")
    g.add_argument("--out", type=Path, metavar="DIR",
                   help="Folder for results. Default: next to each input.")
    g.add_argument("--stdout", action="store_true",
                   help="Write the raw record to stdout and no files. One\n"
                        "input only; not with --report.")
    g.add_argument("--overwrite", action="store_true",
                   help="Replace existing results. Default: stop.")

    g = s.add_argument_group("Running")
    g.add_argument("-p", "--parallel", type=positive_int, default=1, metavar="N",
                   help="Solve up to N inputs at once. Default: 1.")
    g.add_argument("-q", "--quiet", action="store_true", help="Errors only. Default: off.")
    s.set_defaults(func=cmd_solve)

    health = sub.add_parser("health", help="show the image's r2x, Wine and Response-2000 versions")
    health.set_defaults(func=cmd_health)
    return p


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    a = build_parser().parse_args(join_pair_values(argv))
    try:
        return a.func(a)
    except UsageError as e:
        print(f"r2x: {e}", file=sys.stderr)
        return USAGE


if __name__ == "__main__":
    raise SystemExit(main())
