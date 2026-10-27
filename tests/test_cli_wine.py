"""End-to-end through the command line, with the real worker under Wine in place of Docker
(tests/fake_docker.py in wine mode). Runs where test_worker_wine.py runs."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from r2x import record

from test_worker_wine import (CHARTS, NO_SHEAR_KEYS, REF, assert_matches,  # noqa: F401
                              pytestmark, reference_sections)

HERE = Path(__file__).parent


def r2x(*argv, cwd=None):
    env = dict(os.environ, PYTHONPATH=str(HERE.parent / "src"), FAKE_DOCKER_MODE="wine",
               R2X_DOCKER=f'"{sys.executable}" "{HERE / "fake_docker.py"}"')
    p = subprocess.run([sys.executable, "-m", "r2x.cli", *argv], capture_output=True, env=env,
                       cwd=cwd)
    return p.returncode, p.stdout, p.stderr.decode()


def test_stdout_matches_references():
    """--views reaches the worker: No Shear alone is exactly the hand-captured case."""
    code, out, err = r2x("solve", str(REF / "newbeam" / "input.r2t"), "--stdout", "--views",
                         "no-shear")
    assert code == 0, err
    assert record.decode(out).sections == reference_sections("newbeam", [56], NO_SHEAR_KEYS)


def test_report_through_the_command_line(tmp_path):
    code, _, err = r2x("solve", str(REF / "newbeam" / "input.r2t"), "--report", "--out",
                       str(tmp_path))
    assert code == 0, err
    assert_matches(record.read(tmp_path / "input.r2x.txt"), "newbeam")
    page = (tmp_path / "input.r2x.html").read_text(encoding="utf-8")
    assert page.count("data:image/png;base64,") == 2 + 4 + CHARTS


def test_parallel_with_an_out_of_scope_input(tmp_path):
    shear = Path(os.environ["R2X_RESPONSE_DIR"]) / "dm-n1n.rsp"
    if not shear.is_file():
        pytest.skip("no dm-n1n.rsp in the Response folder")
    code, _, err = r2x("solve", str(REF / "newbeam" / "input.r2t"), str(shear), "-p", "2",
                       "--out", str(tmp_path))
    assert code == 3, err
    assert "[dm-n1n] out of scope: the loading includes shear" in err
    assert_matches(record.read(tmp_path / "input.r2x.txt"), "newbeam")
    assert not (tmp_path / "dm-n1n.r2x.txt").exists()


def test_no_input(tmp_path):
    code, out, err = r2x("solve", "--stdout", cwd=tmp_path)
    assert code == 0, err
    rec = record.decode(out)
    assert rec.header["input-name"] == "File > New" and rec.header["peak-stage"] == "56"
    assert rec.control("moment_phi") == (REF / "newbeam/control/moment_phi.txt").read_bytes()
