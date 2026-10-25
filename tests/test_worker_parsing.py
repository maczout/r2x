"""Parsing, stage checks and Copy Chart Data mechanics, against the Newbeam reference exports
and a stand-in for the helper (no Wine needed)."""
from pathlib import Path

import pytest

from r2x.worker.export import check_stage
from r2x.worker.session import (CONTROL_CHARTS, NO_SHEAR_CHARTS, OutOfScope, R2xError, Session,
                                export_points, export_title, identify_stage, strain_curvature)

REF = Path(__file__).parent / "reference" / "newbeam"


def read(rel):
    return (REF / rel).read_bytes()


def test_titles_match_chart_table():
    assert export_title(read("control/moment_ex.txt")) == CONTROL_CHARTS[0].title
    assert export_title(read("control/moment_phi.txt")) == CONTROL_CHARTS[1].title
    for chart in NO_SHEAR_CHARTS:
        assert export_title(read(f"stages/056/{chart.key}.txt")) == chart.title


def test_control_curves_have_60_points():
    assert len(export_points(read("control/moment_ex.txt"))) == 60
    assert len(export_points(read("control/moment_phi.txt"))) == 60


def test_peak_stage_is_56():
    curve = export_points(read("control/moment_phi.txt"))
    strain = read("stages/056/longitudinal_strain.txt")
    assert strain_curvature(strain) == pytest.approx(40.389, abs=0.001)
    check_stage(strain, curve, 56)
    with pytest.raises(R2xError):
        check_stage(strain, curve, 55)
    assert identify_stage(strain, curve) == 56


def test_identify_stage_refuses_to_guess():
    strain = read("stages/056/longitudinal_strain.txt")
    flat = [(40.389, m) for m in range(5)]           # e.g. axial load only: one curvature
    with pytest.raises(R2xError, match="stages 0 to 4 all have curvature"):
        identify_stage(strain, flat)
    with pytest.raises(R2xError, match="not on the Moment-phi curve"):
        identify_stage(strain, [(0.0, 0.0), (1.0, 5.0)])


# -- Copy Chart Data through a stand-in helper ---------------------------------------------------
class FakeHelper:
    """Answers the helper's clipboard and menu commands like Response under Wine does.

    `lose` lists copy attempts (1-based) whose Return key goes missing, as seen rarely in Wine.
    """

    def __init__(self, exports: dict[str, bytes], lose=()):
        self.exports, self.lose = exports, set(lose)
        self.seq, self.clip, self.popup, self.downs, self.target = 0, None, False, 0, None
        self.attempt = 0

    def ask(self, command):
        cmd, *args = command.split()
        if cmd == "clipclear":
            self.seq, self.clip = self.seq + 1, None
        elif cmd == "clipseq":
            return str(self.seq)
        elif cmd == "rclick":
            self.attempt += 1
            self.popup, self.downs, self.target = True, 0, args[0]
        elif cmd == "popup":
            return "1" if self.popup else "0"
        elif cmd == "menukey":
            vk = int(args[0], 16)
            if vk == 0x28:
                self.downs += 1
            elif vk == 0x1B:
                self.popup = False
            elif vk == 0x0D and self.attempt not in self.lose:
                self.popup = False
                if self.downs == 2:
                    self.seq, self.clip = self.seq + 1, self.exports[self.target]
        elif cmd == "clip":
            if self.clip is None:
                raise R2xError("helper: 'clip' -> 'err no text'")
            return self.clip.hex()
        return ""

    def try_ask(self, command):
        try:
            return self.ask(command)
        except R2xError:
            return None


def session_with(exports, lose=()):
    notes = []
    s = Session(FakeHelper(exports, lose), note=notes.append)
    s._charts = {key: key for key in exports}     # window handle = chart key
    return s, notes


def test_copy_chart():
    data = read("stages/056/longitudinal_strain.txt")
    s, notes = session_with({"longitudinal_strain": data})
    assert s.copy_chart(NO_SHEAR_CHARTS[0], timeout=0.2) == data
    assert notes == []


def test_copy_chart_retries_a_lost_key():
    data = read("stages/056/longitudinal_strain.txt")
    s, notes = session_with({"longitudinal_strain": data}, lose=[1])
    assert s.copy_chart(NO_SHEAR_CHARTS[0], timeout=0.2) == data
    assert len(notes) == 1 and "trying again" in notes[0]
    assert s.h.popup is False


def test_copy_chart_gives_up():
    s, notes = session_with({"longitudinal_strain": b"x"}, lose=[1, 2, 3])
    with pytest.raises(R2xError, match="failed 3 times"):
        s.copy_chart(NO_SHEAR_CHARTS[0], timeout=0.1)
    assert len(notes) == 2


def test_wrong_title_is_an_error_not_a_retry():
    s, notes = session_with({"longitudinal_strain": read("control/moment_ex.txt")})
    with pytest.raises(R2xError, match="export title 'Control : Moment - |e_x'") as e:
        s.copy_chart(NO_SHEAR_CHARTS[0], timeout=0.2)
    assert not isinstance(e.value, OutOfScope) and notes == []


def test_shear_control_chart_is_out_of_scope():
    shear = read("control/moment_ex.txt").replace(b"Control : Moment - |e_x",
                                                  b"Control : Shear - |g_x_y")
    s, _ = session_with({"moment_ex": shear, "longitudinal_strain": shear})
    with pytest.raises(OutOfScope, match="loading includes shear"):
        s.copy_chart(CONTROL_CHARTS[0], timeout=0.2)
    with pytest.raises(R2xError) as e:            # a detail view with that title is just wrong
        s.copy_chart(NO_SHEAR_CHARTS[0], timeout=0.2)
    assert not isinstance(e.value, OutOfScope)
