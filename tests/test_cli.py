import pytest

from r2x import __version__
from r2x.cli import build_parser


def test_version(capsys):
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--version"])
    assert __version__ in capsys.readouterr().out


def test_solve_args():
    args = build_parser().parse_args(["solve", "a.r2t", "b.r2t", "--out", "results"])
    assert args.inputs == ["a.r2t", "b.r2t"]
    assert args.out == "results"
