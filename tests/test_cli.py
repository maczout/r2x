from pathlib import Path

import pytest

from r2x import __version__
from r2x.cli import build_parser, expand_inputs, output_dir, windows_to_wsl


def test_version(capsys):
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--version"])
    assert __version__ in capsys.readouterr().out


def test_solve_args():
    a = build_parser().parse_args(["solve", "a.r2t", "b.rsp", "--out", "results", "-j", "2"])
    assert a.inputs == ["a.r2t", "b.rsp"] and a.out == Path("results") and a.jobs == 2
    assert a.image == "r2x"


def test_windows_to_wsl():
    assert windows_to_wsl(r"C:\Users\maczo\cases\Liping LB1.rsp") == \
        "/mnt/c/Users/maczo/cases/Liping LB1.rsp"
    assert windows_to_wsl(r"D:\x") == "/mnt/d/x"
    with pytest.raises(SystemExit):
        windows_to_wsl(r"\\wsl$\Ubuntu\home\x.r2t")


def test_expand_inputs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for n in ("b.r2t", "a.r2t", "c.rsp"):
        Path(n).write_text("x")
    assert [p.name for p in expand_inputs(["*.r2t"])] == ["a.r2t", "b.r2t"]
    assert [p.name for p in expand_inputs(["c.rsp", "*.rsp"])] == ["c.rsp"]   # no duplicates
    with pytest.raises(SystemExit):
        expand_inputs(["*.xyz"])
    with pytest.raises(SystemExit):
        expand_inputs(["missing.r2t"])


def test_output_dir():
    assert output_dir(Path("cases/Newbeam.r2t"), None) == Path("cases/Newbeam_r2x")
    assert output_dir(Path("cases/Newbeam.r2t"), Path("res")) == Path("res/Newbeam_r2x")
