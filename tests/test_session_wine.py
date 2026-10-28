"""A whole r2x session through the command line, with the real worker under Wine in place of
Docker (tests/fake_docker.py in wine mode): define a section by questions, solve it, undo."""
import os
import re
import subprocess
import sys
from pathlib import Path

from r2x import record
from r2x.define import today

from test_worker_wine import REF, pytestmark  # noqa: F401

HERE = Path(__file__).parent


def session(script: list[str], cwd: Path):
    env = dict(os.environ, PYTHONPATH=str(HERE.parent / "src"), FAKE_DOCKER_MODE="wine",
               R2X_DOCKER=f'"{sys.executable}" "{HERE / "fake_docker.py"}"')
    p = subprocess.run([sys.executable, "-m", "r2x.cli"], input="\n".join(script) + "\n",
                       text=True, capture_output=True, env=env, cwd=cwd)
    return p.returncode, p.stdout, p.stderr


def test_define_solve_undo(tmp_path):
    enter = [""] * 22                       # every question of Quick Define: Response's value
    code, out, err = session([
        "define quick", "newbeam.r2t", *enter,
        "solve --views no-shear",
        "define long add web", "2", "", "15M", "300", "",
        "show",
        "undo",
        "show",
    ], tmp_path)
    assert code == 0, err + out
    f = tmp_path / "newbeam.r2t"
    # Enter through Quick Define gives Newbeam, dated today on this computer
    newbeam = (REF / "newbeam" / "input.r2t").read_bytes()
    assert f.read_bytes() == newbeam.replace(b'"2026/10/24"', f'"{today()}"'.encode())
    assert "set: nothing, every answer as Response had it" in out
    # the solve: Newbeam's record, the record beside the file, the report with the outputs
    rec = record.read(tmp_path / "newbeam.r2x.txt")
    assert (rec.header["stage-count"], rec.header["peak-stage"]) == ("60", "56")
    assert "[newbeam] solved: 60 stages, peak 56 -> newbeam.r2x.txt, newbeam.r2x.html" in err
    # the layer added, then taken away again by undo; the record is a solve of the file again
    assert "set: Layer web; Number of Bars 2" in out
    shows = re.findall(r"record: (.*)", out)
    assert "stale" in shows[0] and "a solve of this file" in shows[1]
    assert "undone: newbeam.r2t is as it was before define long add web" in out
    page = (tmp_path / "newbeam.r2x.html").read_text(encoding="utf-8")
    assert "undo of define long add web" in page and "Outputs" not in page
