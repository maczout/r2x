"""r2x define's reference cases (tests/reference/define) under Wine: each case's session.txt,
run in an r2x session through the command line (tests/fake_docker.py in wine mode), against
the file made by hand in Response on Windows (hand.r2t), where there is one.

As check.ps1 does on Windows; a Quick Define case is compared but for the date.
"""
import json
import re
import shutil
from pathlib import Path

import pytest

from test_session_wine import session
from test_worker_wine import REF, pytestmark  # noqa: F401

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
    assert made == expected
