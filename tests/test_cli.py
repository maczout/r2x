"""The command line, with tests/fake_docker.py standing in for Docker (no Wine needed)."""
import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

from r2x import __version__, record
from r2x.cli import (build_parser, expand_inputs, join_pair_values, main, overall_status,
                     record_path, UsageError, windows_to_wsl)
from r2x.display import Display
from r2x.progress import Event
from r2x.stages import PEAK, parse_stages

HERE = Path(__file__).parent
FAKE_DOCKER = f'"{sys.executable}" "{HERE / "fake_docker.py"}"'


def parse(*argv):
    return build_parser().parse_args(join_pair_values(["solve", *argv]))


# -- arguments ----------------------------------------------------------------------------------
def test_version(capsys):
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--version"])
    assert __version__ in capsys.readouterr().out


def test_defaults():
    a = parse("a.r2t", "b.rsp")
    assert a.inputs == ["a.r2t", "b.rsp"] and a.stage == PEAK and a.parallel == 1
    assert a.out is None and not (a.stdout or a.overwrite or a.quiet or a.report)
    assert a.units is None and a.initial is None and a.image == "r2x"


def test_options():
    a = parse("a.r2t", "--stage", "peak,0-5", "--out", "res", "-p", "4", "-q", "--overwrite",
              "--units", "US", "--factors", "csa", "--initial", "-2000,0", "--increment",
              "0,-1.5")
    assert a.stage == parse_stages("peak,0-5") and a.out == Path("res") and a.parallel == 4
    assert a.quiet and a.overwrite and a.units == "us" and a.factors == "csa"
    assert a.initial == (-2000.0, 0.0) and a.increment == (0.0, -1.5)
    assert parse("--initial=-5,1", "x.r2t").initial == (-5.0, 1.0)


@pytest.mark.parametrize("argv, message", [
    (["--stage", "30-20"], "runs backwards"),
    (["--stage", "x"], "'x'"),
    (["--stage", "1,,2"], "empty item"),
    (["-p", "0"], "1 or more"),
    (["--parallel", "two"], "1 or more"),
    (["--initial", "5"], "expected N,M"),
    (["--increment", "0,0"], "cannot be 0,0"),
    (["--units", "imperial"], "invalid choice"),
    (["--stag", "all"], "unrecognized arguments"),       # no abbreviations
])
def test_usage_errors_exit_2(argv, message, capsys):
    with pytest.raises(SystemExit) as e:
        parse("a.r2t", *argv)
    assert e.value.code == 2 and message in capsys.readouterr().err


def test_help_matches_spec(capsys):
    """`r2x solve --help` is the text agreed in docs/cli.md, plus two notes of its own."""
    spec = (HERE.parent / "docs" / "cli.md").read_text(encoding="utf-8")
    spec = spec[spec.index("```\nusage: r2x solve") + 4:]
    spec = spec[:spec.index("```")]
    with pytest.raises(SystemExit):
        build_parser().parse_args(["solve", "--help"])
    text = capsys.readouterr().out
    for note in ("\nNot available yet: --units, --factors, --initial, --increment, --report,\n"
                 "and solving without an input.\n",
                 "With several inputs, the most serious: 1, then 2, then 3.\n"):
        assert note in text
        text = text.replace(note, "")
    assert text == spec


def test_windows_to_wsl():
    assert windows_to_wsl(r"C:\Users\maczo\cases\Liping LB1.rsp") == \
        "/mnt/c/Users/maczo/cases/Liping LB1.rsp"
    assert windows_to_wsl(r"D:\x") == "/mnt/d/x"
    with pytest.raises(UsageError):
        windows_to_wsl(r"\\wsl$\Ubuntu\home\x.r2t")


def test_expand_inputs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for n in ("b.r2t", "a.r2t", "c.rsp"):
        Path(n).write_text("x")
    assert [p.name for p in expand_inputs(["*.r2t"])] == ["a.r2t", "b.r2t"]
    assert [p.name for p in expand_inputs(["c.rsp", "*.rsp"])] == ["c.rsp"]   # no duplicates
    with pytest.raises(UsageError):
        expand_inputs(["*.xyz"])
    with pytest.raises(UsageError):
        expand_inputs(["missing.r2t"])


def test_record_path():
    assert record_path(Path("cases/Newbeam.r2t"), None) == Path("cases/Newbeam.r2x.txt")
    assert record_path(Path("cases/Newbeam.r2t"), Path("res")) == Path("res/Newbeam.r2x.txt")


def test_overall_status():
    assert overall_status([]) == 0 and overall_status([0, 0]) == 0
    assert overall_status([0, 3]) == 3 and overall_status([3, 2, 0]) == 2
    assert overall_status([3, 2, 1, 0]) == 1


# -- running, through the fake docker -----------------------------------------------------------
@pytest.fixture
def cases(tmp_path, monkeypatch):
    monkeypatch.setenv("R2X_DOCKER", FAKE_DOCKER)
    monkeypatch.delenv("FAKE_DOCKER_MODE", raising=False)
    d = tmp_path / "cases"
    d.mkdir()
    for name, text in [("beam", "ok"), ("bad", "fail"), ("shear", "shear"), ("crash", "crash"),
                       ("noout", "noout"), ("slow1", "slow"), ("slow2", "slow")]:
        (d / f"{name}.r2t").write_text(text)
    return d


def r2x(*argv):
    """Run r2x in a subprocess: returns (exit status, stdout bytes, stderr text)."""
    env = dict(os.environ, PYTHONPATH=str(HERE.parent / "src"))
    p = subprocess.run([sys.executable, "-m", "r2x.cli", *argv], capture_output=True, env=env)
    return p.returncode, p.stdout, p.stderr.decode()


def test_solve_writes_record_next_to_input(cases):
    status, out, err = r2x("solve", str(cases / "beam.r2t"))
    rec = record.read(cases / "beam.r2x.txt")
    assert status == 0 and out == b""
    assert rec.stages() == [7] and rec.header["input-name"] == "beam.r2t"
    assert f"[beam] solved: 10 stages, peak 7 -> {cases / 'beam.r2x.txt'}" in err
    assert "\r" not in err                     # no spinner when stderr is not a terminal


def test_stage_and_out(cases, tmp_path):
    status, _, _ = r2x("solve", str(cases / "beam.r2t"), "--stage", "all",
                       "--out", str(tmp_path / "res" / "deep"))
    assert status == 0
    assert record.read(tmp_path / "res" / "deep" / "beam.r2x.txt").stages() == list(range(10))


def test_existing_record_needs_overwrite(cases):
    (cases / "beam.r2x.txt").write_text("old")
    status, _, err = r2x("solve", str(cases / "beam.r2t"))
    assert status == 2 and "use --overwrite" in err
    assert (cases / "beam.r2x.txt").read_text() == "old"
    status, _, _ = r2x("solve", str(cases / "beam.r2t"), "--overwrite")
    assert status == 0 and record.read(cases / "beam.r2x.txt").stages() == [7]


@pytest.mark.parametrize("name, status, message", [
    ("bad", 1, "[bad] failed: Response shows a dialog 'Invalid File'"),
    ("shear", 3, "[shear] out of scope: the loading includes shear"),
    ("crash", 1, "[crash] failed: exit status 1: Traceback (most recent call last): / "
                 "RuntimeError: boom"),
    ("noout", 1, "[noout] failed: the container finished but wrote no noout.r2x.txt"),
])
def test_failures(cases, name, status, message):
    code, _, err = r2x("solve", str(cases / f"{name}.r2t"))
    assert code == status and message in err
    assert not (cases / f"{name}.r2x.txt").exists()


def test_stage_past_last_is_a_usage_error(cases):
    code, _, err = r2x("solve", str(cases / "beam.r2t"), "--stage", "12")
    assert code == 2 and "[beam] usage error: stage 12 is past the last stage, 9" in err


def test_several_inputs_and_summary(cases):
    code, _, err = r2x("solve", str(cases / "beam.r2t"), str(cases / "shear.r2t"),
                       str(cases / "bad.r2t"), "-p", "3")
    assert code == 1
    assert "r2x: 1 of 3 solved, 1 failed, 1 out of scope" in err
    code, _, err = r2x("solve", str(cases / "beam.r2t"), str(cases / "shear.r2t"), "--overwrite")
    assert code == 3


def test_glob_and_parallel(cases):
    code, _, err = r2x("solve", str(cases / "slow*.r2t"), "--parallel", "2")
    assert code == 0 and "r2x: 2 of 2 solved" in err
    assert (cases / "slow1.r2x.txt").exists() and (cases / "slow2.r2x.txt").exists()


def test_quiet_shows_errors_only(cases):
    code, _, err = r2x("solve", str(cases / "beam.r2t"), str(cases / "shear.r2t"), "-q")
    assert code == 3 and err.strip().splitlines() == [
        "[shear] out of scope: the loading includes shear"]


def test_stdout(cases):
    code, out, err = r2x("solve", str(cases / "beam.r2t"), "--stdout", "--stage", "0,9")
    assert code == 0 and record.decode(out).stages() == [0, 9]
    assert b"\r\n" in out and "-> stdout" in err
    assert sorted(p.name for p in cases.iterdir()) == sorted(
        p.name for p in cases.iterdir() if not p.name.endswith(".r2x.txt"))   # no files
    code, out, err = r2x("solve", str(cases / "bad.r2t"), "--stdout")
    assert code == 1 and out == b""


@pytest.mark.parametrize("argv, message", [
    (["slow*.r2t", "--stdout"], "--stdout takes one input; 2 given"),
    (["beam.r2t", "--stdout", "--out", "x"], "--out does not apply"),
    (["beam.r2t", "--units", "si"], "--units: not available yet"),
    (["beam.r2t", "--report", "--initial", "1,0"], "--initial, --report: not available yet"),
    ([], "without an input (File > New) is not available yet"),
    (["nothing*.r2t"], "no files match"),
    (["beam.r2t", str(Path(".") / "beam.r2t"), "be*.r2t"], ""),  # same file thrice: once
])
def test_command_line_problems(cases, monkeypatch, argv, message):
    monkeypatch.chdir(cases)
    code, out, err = r2x("solve", *argv)
    if message:
        assert code == 2 and message in err and out == b""
    else:
        assert code == 0


def test_main_in_process(cases, capsys):
    assert main(["solve", str(cases / "beam.r2t"), "-q"]) == 0
    assert main(["solve", str(cases / "beam.r2t")]) == 2
    assert "exists" in capsys.readouterr().err


def test_health(cases):
    code, out, _ = r2x("health")
    assert code == 0 and b"r2x client" in out and b'"r2x_version": "fake"' in out


# -- the status line ----------------------------------------------------------------------------
def test_display_live():
    s = io.StringIO()
    d = Display(s, live=True)
    a, b = d.add("Newbeam"), d.add("Cm4")
    d.start(a)
    d.event(a, Event("solving"))
    d.start(b)
    d.event(a, Event("solved", count=60, stage=56))
    d.event(a, Event("stage", stage=56, done=1, total=1))
    d.tick()
    assert d.status_line() == "/ 0/2 done  [Newbeam] stage 56 (1/1), 0 s  [Cm4] starting, 0 s"
    d.finish(a, 0, where="Newbeam.r2x.txt")
    d.finish(b, 3, "the loading includes shear")
    d.summary()
    d._clear()
    text = s.getvalue()
    lines = [seg.rsplit("\r", 1)[-1] for seg in text.split("\n")]
    assert lines[0].startswith("[Newbeam] solved: 60 stages, peak 56 -> Newbeam.r2x.txt (")
    assert lines[1] == "[Cm4] out of scope: the loading includes shear"
    assert lines[2] == "r2x: 1 of 2 solved, 1 out of scope"
    assert text.endswith("\n") or text.rstrip(" \r").endswith("\n")
    assert "\x1b" not in text                   # no escape codes


def test_display_not_live_has_no_carriage_returns():
    s = io.StringIO()
    d = Display(s, live=False)
    j = d.add("x")
    d.start(j)
    d.event(j, Event("stage", stage=1, done=1, total=2))
    d.event(j, Event("note", "trying again"))
    d.tick()
    d.finish(j, 1, "boom")
    assert s.getvalue() == "[x] note: trying again\n[x] failed: boom\n"


@pytest.mark.skipif(os.name == "nt", reason="uses a pseudo-terminal")
def test_spinner_on_a_terminal(cases):
    """With stderr on a terminal, a status line is drawn and cleared."""
    import pty
    import select
    master, slave = pty.openpty()
    env = dict(os.environ, PYTHONPATH=str(HERE.parent / "src"), COLUMNS="100")
    p = subprocess.Popen([sys.executable, "-m", "r2x.cli", "solve", str(cases / "slow1.r2t")],
                         stdout=subprocess.DEVNULL, stderr=slave, env=env)
    os.close(slave)
    chunks = []
    while True:
        r, _, _ = select.select([master], [], [], 10)
        if not r:
            break
        try:
            data = os.read(master, 4096)
        except OSError:
            break
        if not data:
            break
        chunks.append(data)
    assert p.wait() == 0
    os.close(master)
    text = b"".join(chunks).decode()
    assert "[slow1] solving" in text and "\r" in text
    assert "[slow1] solved: 10 stages, peak 7 ->" in text
