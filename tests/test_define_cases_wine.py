"""r2x define's reference cases (tests/reference/define) under Wine: each case's session.txt,
run in an r2x session through the command line (tests/fake_docker.py in wine mode), against
the file made by hand in Response on Windows (hand.r2t), where there is one.

As check.ps1 does on Windows: the same bytes (a Quick Define case but for the date); or else
the same section with its longitudinal layers in another order, which Response, opening
either, saves the same, and which solves to the same record.
"""
import importlib.util
import json
import re
import shutil
from pathlib import Path

import pytest

from r2x import record
from r2x.worker.runner import run_job

from define_driver import define
from test_session_wine import session
from test_worker_wine import PREFIX, REF, RESPONSE, pytestmark  # noqa: F401

CASES = REF / "define"
DATE = re.compile(rb'date(\s*)="\d{4}/\d{2}/\d{2}"')
ALL = json.loads((CASES / "cases.json").read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", ALL, ids=[c["name"] for c in ALL])
def test_case(case, tmp_path):
    folder = CASES / case["name"]
    if case["from"] == "newbeam":
        shutil.copyfile(REF / "newbeam" / "input.r2t", tmp_path / "r2x.r2t")
    script = (folder / "session.txt").read_text(encoding="utf-8").splitlines()
    code, out, err = session(script, tmp_path)
    assert code == 0, err + out
    assert "failed" not in out, out
    made = (tmp_path / "r2x.r2t").read_bytes()
    hand = folder / "hand.r2t"
    if not hand.exists():
        pytest.skip(f"no hand.r2t yet: made {len(made)} bytes (see {case['name']}/README.md)")
    expected = hand.read_bytes()
    if case["from"] is None:          # a new section: Response dates it with the day
        made, expected = DATE.sub(rb'date\1="-"', made), DATE.sub(rb'date\1="-"', expected)
    if made == expected:
        return
    # Not the same bytes: the same section, its layers in another order?
    spec = importlib.util.spec_from_file_location("compare", CASES / "compare.py")
    compare = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(compare)
    shutil.copyfile(hand, tmp_path / "hand.r2t")
    assert compare.same_sections(tmp_path / "hand.r2t", tmp_path / "r2x.r2t"), \
        "not the same section (date and layer order aside)"
    resaved = {}
    for name in ("hand", "r2x"):     # opened and saved again by Response
        out = tmp_path / f"{name}-resaved.r2t"
        r = define([], input_file=tmp_path / f"{name}.r2t", out=out, extra=["--screen", "resave"])
        assert r.status == 0, r.stderr
        resaved[name] = DATE.sub(rb'date\1="-"', out.read_bytes())
    assert resaved["hand"] == resaved["r2x"], "Response saves the two files differently"
    records = {}
    for name in ("hand", "r2x"):
        out = tmp_path / f"{name}.r2x.txt"
        run_job(tmp_path / f"{name}.r2t", out, Path(RESPONSE), PREFIX)
        records[name] = record.read(out).sections
    assert records["hand"] == records["r2x"], "the two files solve to different records"
