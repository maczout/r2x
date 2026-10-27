"""Parsing, stage identification and Copy Chart Data mechanics, against the reference exports
and a stand-in for the helper (no Wine needed)."""
from pathlib import Path

import pytest

from r2x.worker.export import control_exports
from r2x.worker.identify import StageKeys, axis_unit, strain_at_axis, strain_curvature
from r2x.views import BY_NAME
from r2x.worker.session import (CONTROL_CHARTS, CONTROL_KEYS, STRAIN, OutOfScope, R2xError,
                                Session, export_points, export_title, view_charts)

NO_SHEAR_CHARTS = view_charts(BY_NAME["no-shear"])

REFS = Path(__file__).parent / "reference"
REF = REFS / "newbeam"


def read(rel):
    return (REF / rel).read_bytes()


def stage_folders(name):
    """A case's captured stages, ascending: [(stage number, folder)]."""
    return sorted((int(d.name), d) for d in (REFS / name / "stages").iterdir())


def case(name):
    """(control exports by record key, peak stage number, Longitudinal Strain export at it). The
    peak is the highest stage captured in every case."""
    d = REFS / name
    controls = control_exports(*[f.read_bytes() for f in sorted((d / "control").glob("*.txt"))])
    stage, folder = stage_folders(name)[-1]
    return controls, stage, (folder / "longitudinal_strain.txt").read_bytes()


def test_titles_match_chart_table():
    assert CONTROL_KEYS[export_title(read("control/moment_ex.txt"))] == "moment_ex"
    assert CONTROL_KEYS[export_title(read("control/moment_phi.txt"))] == "moment_phi"
    axial = (REFS / "newbeam-axial-only/control/axial_ex.txt").read_bytes()
    assert CONTROL_KEYS[export_title(axial)] == "axial_ex"
    for chart in NO_SHEAR_CHARTS:
        assert export_title(read(f"stages/056/{chart.key}.txt")) == chart.title


def test_control_curves_have_60_points():
    assert len(export_points(read("control/moment_ex.txt"))) == 60
    assert len(export_points(read("control/moment_phi.txt"))) == 60


@pytest.mark.parametrize("name", ["newbeam", "newbeam-axial", "newbeam-axial-only", "newbeam-csa",
                                  "newbeam-us", "newbeam-filenew"])
def test_every_reference_stage_is_identified(name):
    controls, _, _ = case(name)
    keys = StageKeys(controls)
    for stage, folder in stage_folders(name):
        strain = (folder / "longitudinal_strain.txt").read_bytes()
        assert keys.identify(strain) == stage
        keys.check(strain, stage)
        for other in (stage - 1, stage + 1):
            if 0 <= other < keys.count:
                with pytest.raises(R2xError):
                    keys.check(strain, other)


def test_newbeam_has_every_view_at_two_stages():
    """Hand captures of every view's charts at the peak and 20 stages below it (2026-10-26)."""
    from r2x.views import ALL, record_order
    keys = sorted(c.key for c in record_order(ALL))
    assert [s for s, _ in stage_folders("newbeam")] == [36, 56]
    for _, folder in stage_folders("newbeam"):
        assert sorted(p.stem for p in folder.glob("*.txt")) == keys
        for chart in record_order(ALL):
            assert export_title((folder / f"{chart.key}.txt").read_bytes()) == chart.title


def test_strain_features():
    strain = read("stages/056/longitudinal_strain.txt")
    assert axis_unit(strain, "X") == "mm/m" and axis_unit(strain, "Y") == "mm"
    assert strain_at_axis(strain) == pytest.approx(7.7869, abs=1e-6)
    assert strain_curvature(strain, "mrad/m") == pytest.approx(40.389, abs=0.001)
    assert strain_curvature(strain, "rad/furlong") is None          # unknown unit: no check
    us = (REFS / "newbeam-us/stages/056/longitudinal_strain.txt").read_bytes()
    assert axis_unit(us, "X") == "ms" and axis_unit(us, "Y") == "in"
    assert strain_at_axis(us) == pytest.approx(7.7869, abs=1e-6)  # strain has no units to change
    assert strain_curvature(us, "rad/10^3inch") == pytest.approx(1.026, abs=0.001)


def test_axial_only_has_one_control_chart_and_no_curvature():
    controls, _, strain = case("newbeam-axial-only")
    assert list(controls) == ["axial_ex"]
    keys = StageKeys(controls)
    assert keys.phi is None and keys.count == 35 and keys.describe(strain)[1] is None


def test_identify_refuses_to_guess():
    controls, _, strain = case("newbeam")
    keys = StageKeys(controls)
    keys.ex = [keys.ex[56]] * 3                     # three stages that look alike
    keys.phi = [keys.phi[56]] * 3
    with pytest.raises(R2xError, match="stages 0, 1, 2 all match"):
        keys.identify(strain)
    keys.ex = [0.0, 1.0]
    keys.phi = [0.0, 1.0]
    with pytest.raises(R2xError, match="not on the control curves"):
        keys.identify(strain)


def test_control_exports():
    ex, phi = read("control/moment_ex.txt"), read("control/moment_phi.txt")
    assert list(control_exports(ex, phi)) == ["moment_ex", "moment_phi"]
    axial = (REFS / "newbeam-axial-only/control/axial_ex.txt").read_bytes()
    assert control_exports(axial, axial) == {"axial_ex": axial}
    with pytest.raises(R2xError, match="different data"):
        control_exports(axial, axial.replace(b"0.000", b"0.001", 1))


# -- Copy Chart Data through a stand-in helper ---------------------------------------------------
class FakeHelper:
    """Answers the helper's clipboard and menu commands like Response under Wine does.

    `lose` lists copy attempts (1-based) whose Return key goes missing, as seen rarely in Wine.
    `widths` gives a chart's context-menu width (default 134, a data chart's under Wine).
    """

    def __init__(self, exports: dict[str, bytes], lose=(), widths=None):
        self.exports, self.lose, self.widths = exports, set(lose), widths or {}
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
        elif cmd == "popuprect":
            if not self.popup:
                raise R2xError("helper: 'popuprect' -> 'err no popup'")
            return f"100 100 {100 + self.widths.get(self.target, 134)} 226"
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


def session_with(exports, lose=(), widths=None):
    notes = []
    s = Session(FakeHelper(exports, lose, widths), note=notes.append)
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


def retitled(data: bytes, title: str) -> bytes:
    return data.replace(export_title(data).encode("latin-1"), title.encode("latin-1"), 1)


def test_shear_control_charts_are_known():
    """Since r2x 0.3.0 shear is in scope: Shear-γxy and Shear-εx are control charts like the
    others."""
    gxy = retitled(read("control/moment_ex.txt"), "Control : Shear - |g_x_y")
    ex = retitled(read("control/moment_ex.txt"), "Control : Shear - |e_x")
    s, _ = session_with({"control_top": gxy, "control_bottom": ex, "longitudinal_strain": gxy})
    assert s.copy_chart(CONTROL_CHARTS[0], timeout=0.2) == gxy
    assert s.copy_chart(CONTROL_CHARTS[1], timeout=0.2) == ex
    assert list(control_exports(gxy, ex)) == ["shear_gxy", "shear_ex"]
    with pytest.raises(R2xError) as e:            # a detail view with that title is just wrong
        s.copy_chart(NO_SHEAR_CHARTS[0], timeout=0.2)
    assert not isinstance(e.value, OutOfScope)


def test_control_positions_take_any_known_control_chart():
    axial = (REFS / "newbeam-axial-only/control/axial_ex.txt").read_bytes()
    odd = axial.replace(b"Control : Axial Load - |e_x", b"Control : Torsion - |q")
    s, _ = session_with({"control_top": read("control/moment_phi.txt"), "control_bottom": axial,
                         "longitudinal_strain": odd})
    assert s.copy_chart(CONTROL_CHARTS[0], timeout=0.2) == read("control/moment_phi.txt")
    assert s.copy_chart(CONTROL_CHARTS[1], timeout=0.2) == axial
    s, _ = session_with({"control_top": odd})
    with pytest.raises(R2xError, match="unknown control chart 'Control : Torsion - |q'") as e:
        s.copy_chart(CONTROL_CHARTS[0], timeout=0.2)
    assert not isinstance(e.value, OutOfScope)


@pytest.mark.parametrize("argv", [["--new"], ["--new", "a", "b"], ["only-one"], ["a", "b", "c"]])
def test_worker_wants_input_and_record_or_new_and_record(argv, capsys):
    from r2x.worker.__main__ import main
    with pytest.raises(SystemExit) as e:
        main(argv + ["--response-dir", "."])
    err = capsys.readouterr().err
    assert e.value.code == 2 and ("give RECORD with --new" in err or "required: PATH" in err)


def test_a_picture_only_chart_is_refused_before_any_menu_item_is_chosen():
    """In a picture-only chart's menu the second item toggles a drawing mode; r2x must not press
    it. The menu width of a data chart is learnt from the first control chart copied."""
    ex = read("control/moment_ex.txt")
    s, _ = session_with({"control_top": ex, "longitudinal_strain": b"x"},
                        widths={"longitudinal_strain": 110})
    assert s.copy_chart(CONTROL_CHARTS[0], timeout=0.2) == ex
    with pytest.raises(R2xError, match=r"row 1, column 2 .* has no Copy Chart Data .* 110 "
                                       r"pixels wide, a data chart's 134"):
        s.copy_chart(STRAIN, timeout=0.2)
    assert s.h.popup is False and s.h.downs == 0          # closed with Escape, nothing chosen


def test_a_chart_not_in_the_view_on_screen_is_an_error():
    s, _ = session_with({"control_top": read("control/moment_ex.txt")})
    with pytest.raises(R2xError, match="transverse_strain is not in the view on screen"):
        s.copy_chart(view_charts(BY_NAME["general"])[1], timeout=0.2)


# -- stage keys with shear --------------------------------------------------------------------------
def test_shear_with_moment_identifies_by_curvature_alone():
    """With V and M in the increment the control charts are Shear-γxy and Moment-φ: curvature
    is the only key (γxy needs the section's widths, docs/cli.md)."""
    controls, _, _ = case("newbeam")
    gxy = retitled(controls["moment_ex"], "Control : Shear - |g_x_y")
    keys = StageKeys(control_exports(gxy, controls["moment_phi"]))
    assert keys.ex is None and keys.phi is not None and keys.count == 60
    for stage, folder in stage_folders("newbeam"):
        strain = (folder / "longitudinal_strain.txt").read_bytes()
        assert keys.candidates(strain) == [stage]
        assert keys.describe(strain)[1] == pytest.approx(keys.phi[stage], abs=0.002)


def test_shear_alone_identifies_by_ex():
    """With V alone in the increment the bottom control chart is Shear-εx."""
    controls, peak, strain = case("newbeam-axial-only")
    ex = retitled(controls["axial_ex"], "Control : Shear - |e_x")
    gxy = retitled(controls["axial_ex"], "Control : Shear - |g_x_y")
    keys = StageKeys(control_exports(gxy, ex))
    assert keys.phi is None and keys.ex is not None
    assert keys.identify(strain) == peak


def test_repeated_control_points_and_several_candidates():
    """An increment of 0,0,0: two stages, both the initial load."""
    controls, _, strain = case("newbeam")
    def first_two(data):
        lines = data.split(b"\r\n")
        start = next(i for i, l in enumerate(lines) if l.startswith(b"Line type")) + 1
        return b"\r\n".join(lines[:start] + [lines[start], lines[start]] + [b""])
    keys = StageKeys({k: first_two(v) for k, v in controls.items()})
    assert keys.count == 2 and keys.repeats == [1]
    zero = (REF / "stages/036/longitudinal_strain.txt").read_bytes()
    keys.ex, keys.phi = [strain_at_axis(zero)] * 2, [strain_curvature(zero, "mrad/m")] * 2
    assert keys.candidates(zero) == [0, 1]
    assert StageKeys(controls).repeats == []


def test_control_curves_must_have_the_same_stages():
    controls, _, _ = case("newbeam")
    short = controls["moment_phi"].rsplit(b"\r\n", 2)[0] + b"\r\n"
    with pytest.raises(R2xError, match="control curves disagree"):
        StageKeys({"moment_ex": controls["moment_ex"], "moment_phi": short})
    gxy = retitled(controls["moment_ex"], "Control : Shear - |g_x_y")
    with pytest.raises(R2xError, match="no control chart with εx or curvature"):
        StageKeys({"shear_gxy": gxy})
