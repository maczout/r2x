"""r2x command line: solves each input in the r2x container and keeps its raw record.

The interface is specified in docs/cli.md. The container runs once per input: in Docker inside
WSL on Windows (`wsl --exec docker ...`), with `docker` directly elsewhere. Standard library only.

Response-2000 is the user's own: `r2x setup --response FOLDER` links its program folder once
(r2x/config.py), and every run mounts it read-only at /opt/response.

Environment:
  R2X_IMAGE            image name (default ghcr.io/maczout/r2x:VERSION, this client's version)
  R2X_DOCKER           command that runs docker, e.g. "sudo docker" (default: see above)
  R2X_WSL_DISTRO       WSL distribution with Docker (default: WSL's default distribution)
  R2X_RESPONSE         Response-2000's program folder, instead of the one setup linked
  R2X_ALLOW_UNVERIFIED 1: run a build of r2k.exe that r2x has not been checked against
  R2X_CONFIG           the settings file, instead of the usual place (r2x/config.py)
"""

from __future__ import annotations

import argparse
import functools
import glob
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import textwrap
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PureWindowsPath

from r2x import __version__, config, progress
from r2x.ask import Question
from r2x.catalogue import CatalogueError, parse_step
from r2x.define import (SECTION_SUFFIXES, Prompter, record_for, report_for, run_step, set_line,
                        today, worker_command)
from r2x.display import Display, Job
from r2x.notice import DISCLAIMER
from r2x.progress import FAILED, OUT_OF_SCOPE, SOLVED, USAGE
from r2x.response import (ALLOW_ENV, Program, ResponseError, read_program,
                          unverified_message)
from r2x.settings import FACTORS, UNITS, Settings, parse_loads, parse_more_detail
from r2x.stages import StageError, StageSpec, parse_stages
from r2x.views import ViewError, format_views, parse_views

DEFAULT_IMAGE = f"ghcr.io/maczout/r2x:{__version__}"   # the published image, this version
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


# -- Response-2000, linked ------------------------------------------------------------------------
NOT_LINKED = ("Response-2000 is not linked: r2x setup --response FOLDER, where FOLDER is its "
              "program folder (the one with r2k.exe)")


def linked_program() -> tuple[Program, bool]:
    """The linked program folder, checked, and whether an unverified r2k.exe is allowed."""
    try:
        link = config.link()
    except ValueError as e:
        raise UsageError(str(e))
    if link.folder is None:
        raise UsageError(NOT_LINKED)
    try:
        program = read_program(link.folder)
    except (ResponseError, OSError) as e:
        raise UsageError(f"{e} (linked in {link.source}; r2x setup --response FOLDER links "
                         f"another)")
    if not program.verified and not link.allow_unverified:
        raise UsageError(unverified_message(program))
    return program, link.allow_unverified


def response_mounts(program: Program, allow_unverified: bool) -> list[str]:
    """docker run options that give the container the program folder, read-only."""
    allow = ["-e", f"{ALLOW_ENV}=1"] if allow_unverified and not program.verified else []
    return ["-v", f"{docker_path(program.folder)}:/opt/response:ro", *allow]


def linked_mounts() -> list[str]:
    return response_mounts(*linked_program())


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
                      image: str, report: Path | None = None, views=None,
                      more_detail: int | str = 0, link: list[str] = ()) -> list[str]:
    """docker run for one input; without an input the worker defines a new section (--new).
    The report, if any, goes in the record's folder; link mounts Response (linked_mounts)."""
    mounts = ["-v", f"{docker_path(inp)}:/in/{inp.name}:ro"] if inp is not None else []
    worker_input = [f"/in/{inp.name}"] if inp is not None else ["--new"]
    return docker_command() + [
        "run", "--rm", "--pull", "never", "--network", "none", *link, *mounts,
        "-v", f"{docker_path(record.parent)}:/out",
        image, "python", "-m", "r2x.worker", *worker_input, f"/out/{record.name}",
        "--stage", str(stages), *(["--views", format_views(views)] if views else []),
        *settings.args(),
        *(["--more-detail", str(more_detail)] if more_detail else []),
        *(["--report", f"/out/{report.name}"] if report is not None else []),
    ]


def run_container(inp: Path | None, record: Path, stages: StageSpec, settings: Settings,
                  image: str, display: Display, job: Job,
                  report: Path | None = None, views=None,
                  more_detail: int | str = 0, link: list[str] = ()) -> tuple[int, str]:
    """Solve one input in its own container; return its exit status and, if it failed, why."""
    cmd = container_command(inp, record, stages, settings, image, report, views, more_detail,
                            link)
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
    if "Unable to find image" in detail or "No such image" in detail:
        return FAILED, f"no image {image} here: r2x setup pulls it"
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
    link = linked_mounts()
    if a.stdout:
        if len(inputs) != 1:
            raise UsageError(f"--stdout takes one input; {len(inputs)} given")
        return solve_to_stdout(inputs[0], a, live, link)

    records = [record_path(i, a.out) for i in inputs]
    reports = [report_path(r) if a.report else None for r in records]
    clash = sorted({str(r) for r in records if records.count(r) > 1})
    if clash:
        raise UsageError(f"several inputs would write {clash[0]}")
    existing = [p for p in records + reports if p is not None and p.exists()]
    if existing and not a.overwrite and not replace_ok(existing):
        print("r2x: nothing solved", file=sys.stderr)
        return SOLVED
    if a.out:
        a.out.mkdir(parents=True, exist_ok=True)
    for p in existing:
        p.unlink()

    with Display(sys.stderr, live, a.quiet) as display:
        jobs = [display.add(job_name(i)) for i in inputs]

        def solve(k: int) -> int:
            status, reason = run_container(inputs[k], records[k], a.stage, settings_from(a),
                                           a.image, display, jobs[k], reports[k], a.views,
                                           a.more_detail, link)
            where = str(records[k]) + (f", {reports[k].name}" if reports[k] else "")
            display.finish(jobs[k], status, reason, where)
            return status

        with ThreadPoolExecutor(max_workers=a.parallel) as pool:
            statuses = list(pool.map(solve, range(len(inputs))))
        display.summary()
    return overall_status(statuses)


def replace_ok(existing: list[Path]) -> bool:
    """Whether to replace results that exist: asked at a terminal, as Windows asks before Save
    As replaces a file. With no one to ask (piped, a script), r2x stops: --overwrite says yes."""
    if len(existing) == 1:
        what = f"{existing[0]} exists: replace it"
    else:
        what = f"{existing[0]} and {len(existing) - 1} more exist: replace them"
    if not (sys.stdin.isatty() and sys.stderr.isatty()):
        raise UsageError(f"{what.split(':')[0]}; use --overwrite to replace")
    ok, answer = Prompter(sys.stdin, sys.stderr).answer(Question("replace", what, "yesno", "n"))
    return ok and answer == "y"


def solve_to_stdout(inp: Path | None, a, live: bool, link: list[str]) -> int:
    """Solve into a temporary folder, then copy the record's bytes to stdout unchanged."""
    with tempfile.TemporaryDirectory(prefix="r2x-") as tmp:
        record = Path(tmp) / f"{job_name(inp)}{RECORD_SUFFIX}"
        with Display(sys.stderr, live, a.quiet) as display:
            job = display.add(job_name(inp))
            status, reason = run_container(inp, record, a.stage, settings_from(a), a.image,
                                           display, job, views=a.views,
                                           more_detail=a.more_detail, link=link)
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


def describe_link() -> list[str]:
    """r2x health's and setup's line on the linked Response, and its mounts if usable."""
    try:
        link = config.link()
    except ValueError as e:
        print(f"Response-2000: {e}")
        return []
    if link.folder is None:
        print(f"Response-2000: not linked (r2x setup --response FOLDER)")
        return []
    try:
        program = read_program(link.folder)
    except (ResponseError, OSError) as e:
        print(f"Response-2000: {e} (linked in {link.source})")
        return []
    allowed = "; allowed (--allow-unverified)" if link.allow_unverified and not \
        program.verified else ""
    print(f"Response-2000: {program.folder} (linked in {link.source})")
    print(f"  {program.describe()}{allowed}")
    return response_mounts(program, link.allow_unverified)


def cmd_health(a) -> int:
    print(f"r2x client {__version__}; image {a.image}; docker: {' '.join(docker_command())}")
    print(textwrap.fill(DISCLAIMER, 78))
    mounts = describe_link()
    cmd = docker_command() + ["run", "--rm", "--pull", "never", "--network", "none", *mounts,
                              a.image, "python", "-m", "r2x.worker.info"]
    try:
        code = subprocess.run(cmd).returncode
    except FileNotFoundError:
        print(f"cannot run {cmd[0]!r}", file=sys.stderr)
        return FAILED
    if code != 0:
        print(f"r2x: the image did not run: is it here? (r2x setup pulls {a.image})",
              file=sys.stderr)
        return FAILED
    return SOLVED


def image_present(image: str) -> bool:
    cmd = docker_command() + ["image", "inspect", "--format", "{{.Id}}", image]
    try:
        return subprocess.run(cmd, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL).returncode == 0
    except FileNotFoundError:
        hint = "is WSL installed?" if os.name == "nt" else "is Docker installed?"
        raise UsageError(f"cannot run {docker_command()[0]!r} ({hint})")


def cmd_setup(a) -> int:
    """Link Response-2000's program folder (once), then make sure the image is here."""
    if a.response is not None:
        try:
            program = read_program(a.response)
        except (ResponseError, OSError) as e:
            raise UsageError(str(e))
        if not program.verified and not a.allow_unverified:
            raise UsageError(unverified_message(program))
        try:
            settings = config.load()
        except ValueError:
            settings = {}            # a damaged settings file is replaced
        settings["response"] = str(program.folder.resolve())
        settings["allow_unverified"] = bool(a.allow_unverified)
        path = config.save(settings)
        print(f"r2x: linked Response-2000 in {path}")
    elif a.allow_unverified:
        raise UsageError("--allow-unverified goes with --response FOLDER")
    if not describe_link():
        return USAGE
    if image_present(a.image):
        print(f"image {a.image}: here")
        return SOLVED
    print(f"image {a.image}: pulling it (about 1.3 GB, once)")
    if subprocess.run(docker_command() + ["pull", a.image]).returncode != 0:
        print(f"r2x: could not pull {a.image}", file=sys.stderr)
        return FAILED
    return SOLVED


# -- define and the session ---------------------------------------------------------------------
def step_command(image: str):
    """The docker command for one define step (r2x.define.worker_command)."""
    return functools.partial(worker_command, docker_command(), image, docker_path,
                             link=linked_mounts())


def section_args(words: list[str], what: str):
    """[NOUN ...] FILE -> (step words, the section's file)."""
    if not words:
        raise UsageError(f"r2x {what} needs the section's file, last")
    file = Path(words[-1])
    if file.suffix.lower() not in SECTION_SUFFIXES:
        raise UsageError(f"{words[-1]}: the section's file comes last (.r2t or .rsp)")
    return words[:-1], file


def cmd_define(a) -> int:
    words, file = section_args(a.words, "define NOUN [ACTION [NAME]]")
    try:
        step = parse_step(words)
    except CatalogueError as e:
        raise UsageError(str(e))
    if not file.parent.is_dir():
        raise UsageError(f"no folder {file.parent} for {file.name}")
    prompter = Prompter()
    command = step_command(a.image)
    report = report_for(file)
    if step.noun == "quick":
        if file.exists():
            ok, answer = prompter.answer(Question("replace", f"{file.name} exists: replace its "
                                                  "section", "yesno", "n"))
            if not ok or answer != "y":
                print("r2x: nothing done", file=sys.stderr)
                return SOLVED
        cmd = command(["quick"], input_file=file if file.exists() else None, out=file,
                      report=report, date=today())
    else:
        if not file.is_file():
            raise UsageError(f"no file {file} (define quick makes one)")
        cmd = command(step.words(), input_file=file, out=file, report=report)
    result = run_step(cmd, prompter)
    if result.status != SOLVED:
        print(f"r2x: define {' '.join(step.words())} failed: {result.reason}", file=sys.stderr)
        return result.status
    if result.saved:
        prompter.print(set_line(result.readback))
        prompter.print(f"r2x: saved {file}, report {report.name} ({result.seconds:.1f} s)")
    else:
        prompter.print(f"r2x: nothing changed; {file} is as it was")
    return SOLVED


SESSION_SOLVE_ONLY = ("stdout", "out", "overwrite", "report")


def session_solve(options: list[str], file: Path, image: str) -> int:
    """solve at a session's prompt: r2x solve's options for the session's file. The record and
    the report go beside it and are replaced."""
    p = argparse.ArgumentParser(prog="solve", usage="solve [options]", add_help=False,
                                formatter_class=HelpFormatter, allow_abbrev=False,
                                description="Solve the session's file; the record and the "
                                            "report go beside it.")
    p.add_argument("-h", "--help", action="help", help=argparse.SUPPRESS)
    add_solve_options(p)
    try:
        o = p.parse_args(join_pair_values(options))
    except SystemExit as e:        # argparse has said why (or printed the help)
        return USAGE if e.code else SOLVED
    given = [f"--{k}" for k in SESSION_SOLVE_ONLY if getattr(o, k)]
    if given or o.parallel != 1:
        print(f"  {', '.join(given or ['--parallel'])}: not in a session (the record and the "
              f"report always go beside the file)")
        return USAGE
    record, report = record_for(file), report_for(file)
    try:
        link = linked_mounts()
    except UsageError as e:
        print(f"  {e}")
        return USAGE
    with Display(sys.stderr, sys.stderr.isatty(), o.quiet) as display:
        job = display.add(file.stem)
        status, reason = run_container(file, record, o.stage, settings_from(o), image, display,
                                       job, report, o.views, o.more_detail, link)
        display.finish(job, status, reason, f"{record.name}, {report.name}")
    return status


def cmd_session(a) -> int:
    from r2x.shell import Shell
    shell = Shell(step_command(a.image), lambda options, file: session_solve(options, file,
                                                                            a.image))
    return shell.run()


# -- arguments ----------------------------------------------------------------------------------
SOLVE_DESCRIPTION = """\
Run a full sectional response in Response-2000 1.9.7 and capture the data
from its control charts and detail views.

Scope: axial load, moment and shear. Not interaction diagrams or member
response.
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
  r2x solve beam.r2t --increment 0,1,1 --more-detail 2
  r2x solve col.rsp --units si --initial -2000,0,0 --increment 0,1,0
  r2x solve cases\\*.r2t --out results --parallel 4
  r2x solve beam.r2t --stdout | py parse.py

""" + textwrap.fill(DISCLAIMER, 78)


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


def loads(text: str) -> tuple[float, float, float]:
    try:
        return parse_loads(text)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e))


def more_detail_spec(text: str) -> int | str:
    try:
        return parse_more_detail(text)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e))


def positive_int(text: str) -> int:
    try:
        n = int(text)
    except ValueError:
        n = 0
    if n < 1:
        raise argparse.ArgumentTypeError(f"{text!r}: expected a whole number, 1 or more")
    return n


def join_pair_values(argv: list[str]) -> list[str]:
    """--initial -2000,0,0 -> --initial=-2000,0,0, so argparse does not take -2000,0,0 for an
    option."""
    out, it = [], iter(argv)
    for arg in it:
        if arg in ("--initial", "--increment"):
            value = next(it, None)
            out.append(arg if value is None else f"{arg}={value}")
        else:
            out.append(arg)
    return out


def add_solve_options(s: argparse.ArgumentParser):
    """r2x solve's options, for the solve command and for solve in a session."""
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
    g.add_argument("--initial", type=loads, metavar="N,M,V",
                   help="Initial load, in the units in effect.\n"
                        "Default: input's, else 0,0,0.")
    g.add_argument("--increment", type=loads, metavar="N,M,V",
                   help="Load increment; only signs and ratio matter.\n"
                        "0,0,0 solves the initial load alone.\n"
                        "Default: input's, else 0,1,0.\n"
                        "N: tension positive. M: compression on top positive.")
    g.add_argument("--more-detail", type=more_detail_spec, default=0, metavar="N",
                   help="Refine the solve N times (more load stages), or\n"
                        "max: until Response refines no further.\n"
                        "Default: 0.")

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
                   help="Also write an HTML report: screenshots of the\n"
                        "inputs and of the peak stage. Default: off.")
    g.add_argument("--out", type=Path, metavar="DIR",
                   help="Folder for results. Default: next to each input.")
    g.add_argument("--stdout", action="store_true",
                   help="Write the raw record to stdout and no files. One\n"
                        "input only; not with --report.")
    g.add_argument("--overwrite", action="store_true",
                   help="Replace existing results without asking. Default:\n"
                        "ask at a terminal, else stop.")

    g = s.add_argument_group("Running")
    g.add_argument("-p", "--parallel", type=positive_int, default=1, metavar="N",
                   help="Solve up to N inputs at once. Default: 1.")
    g.add_argument("-q", "--quiet", action="store_true", help="Errors only. Default: off.")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="r2x", description="Run Response-2000 from the command line.",
                                epilog=DISCLAIMER)
    p.add_argument("--version", action="version", version=f"r2x {__version__}")
    p.add_argument("--image", default=os.environ.get("R2X_IMAGE", DEFAULT_IMAGE),
                   help=f"container image (default: $R2X_IMAGE or {DEFAULT_IMAGE})")
    sub = p.add_subparsers(dest="command", metavar="{solve,define,setup,health}",
                           description="With no command: a session at the r2x> prompt "
                                       "(define, solve, ...; help there).")

    s = sub.add_parser("solve", help="solve inputs and capture their exported data",
                       usage="r2x solve [INPUT ...] [options]", description=SOLVE_DESCRIPTION,
                       epilog=SOLVE_EPILOG, formatter_class=HelpFormatter, add_help=False,
                       allow_abbrev=False)
    s.add_argument("-h", "--help", action="help", help=argparse.SUPPRESS)

    g = s.add_argument_group("Input")
    g.add_argument("inputs", nargs="*", metavar="INPUT",
                   help=".rsp or .r2t files; globs allowed (cases\\*.r2t).\n"
                        "Default: a new section, Response's default (Newbeam).")

    add_solve_options(s)
    s.set_defaults(func=cmd_solve)

    d = sub.add_parser("define", help="set part of a section, question by question",
                       usage="r2x define NOUN [ACTION [NAME]] FILE",
                       description=define_description(), formatter_class=HelpFormatter,
                       epilog="r2x with no command starts a session, where the file is kept "
                              "between steps and undo goes back one step.")
    d.add_argument("words", nargs="+", metavar="WORD", help=argparse.SUPPRESS)
    d.set_defaults(func=cmd_define)

    setup = sub.add_parser("setup", help="link your Response-2000 and get the image (once)",
                           usage="r2x setup [--response FOLDER] [--allow-unverified]",
                           description="Link your own copy of Response-2000 (its program "
                                       "folder, the one with r2k.exe) and pull the image if it "
                                       "is not here. With no options: check both.")
    setup.add_argument("--response", type=Path, metavar="FOLDER",
                       help="Response-2000's program folder")
    setup.add_argument("--allow-unverified", action="store_true",
                       help="link it even if r2k.exe is not a build r2x has been checked "
                            "against; every record says so")
    setup.set_defaults(func=cmd_setup)

    health = sub.add_parser("health", help="show the linked Response-2000 and the image's "
                                           "r2x and Wine versions")
    health.set_defaults(func=cmd_health)
    return p


def define_description() -> str:
    from r2x.shell import define_help
    return ("Set part of the section in FILE, question by question. The file is saved, and\n"
            "its report beside it (NAME.r2x.html) is rewritten and reloads itself in the\n"
            "browser.\n\n"
            + define_help())


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    a = build_parser().parse_args(join_pair_values(argv))
    if a.command is None:
        a.func = cmd_session
    try:
        return a.func(a)
    except UsageError as e:
        print(f"r2x: {e}", file=sys.stderr)
        return USAGE


if __name__ == "__main__":
    raise SystemExit(main())
