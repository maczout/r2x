"""Applying settings through Response's dialogs and reading them back, against a stand-in for
Response's Preferences and Define Loading dialogs (no Wine needed)."""
import pytest

from r2x.settings import Settings
from r2x.worker import dialogs
from r2x.worker.dialogs import CONSTANT, FACTOR_FIELDS, INCREMENT, UNIT_RADIOS
from r2x.worker.session import R2xError, Session, Window

# kN and kNm per kip and kip-ft (US) or ton and ton-m (kg/cm), as Response converts.
PER_UNIT = {"si": (1.0, 1.0), "us": (4.448222, 1.355818), "kgcm": (9.80665, 9.80665)}
CSA, NONE = ("0.65", "0.85", "0.90"), ("1.00", "1.00", "1.00")


class FakeResponse:
    """Answers the helper's dialog commands the way Response does: loads are kept in SI and shown
    with two decimals in the units in effect; OK commits a dialog, Cancel discards it."""

    def __init__(self, units="si", factors=NONE, constant=(0, 0, 0), increment=(0, 1, 0),
                 reject=False):
        self.units, self.factors = units, factors
        self.loads = {"c": list(constant), "i": list(increment)}   # SI: kN, kNm, kN
        self.reject = reject          # answer OK with a message box instead of closing
        self.open = None              # (hwnd, title, {control id: value})
        self.box = None
        self.commands = []

    # -- what Response shows ------------------------------------------------------------------
    def _shown(self, kind, k):
        per = PER_UNIT[self.units][1 if k == 1 else 0]
        return f"{self.loads[kind][k] / per:.2f}"

    def windows(self, which="tree"):
        if which == "dialogs":
            out = [Window(self.open[0], "0", True, (0, 0, 9, 9), "#32770", self.open[1])] \
                if self.open else []
            return out + ([Window("bx", "0", True, (0, 0, 9, 9), "#32770", "Error")]
                          if self.box else [])
        if which == "kids bx":
            return [Window("st", "bx", True, (0, 0, 9, 9), "Static", "Not a number")]
        return []

    def ask(self, command):
        self.commands.append(command)
        cmd, *a = command.split()
        if cmd == "cmd" and len(a) == 1:
            if a[0] == "321":
                c = {cid: str(int(u == self.units)) for u, cid in UNIT_RADIOS.items()}
                c.update(zip(FACTOR_FIELDS, self.factors))
                self.open = ("p1", dialogs.PREFERENCES, c)
            elif a[0] == "152":
                c = {cid: self._shown("c", k) for k, cid in enumerate(CONSTANT)}
                c.update({cid: self._shown("i", k) for k, cid in enumerate(INCREMENT)})
                self.open = ("l1", dialogs.LOADING, c)
            return ""
        if cmd == "cmd":                               # OK or Cancel to the open dialog
            if a[0] == "1":
                if self.reject:
                    self.box = True
                    return ""
                self._commit()
            self.open = None
            return ""
        if cmd == "find":
            return f"{a[0]}:{a[1]}"
        if cmd == "alive":
            return "1" if self.open and self.open[0] == a[0] else "0"
        controls, cid = self.open[2], int(a[0].split(":")[1])
        if cmd == "gettext":
            return f"  {controls[cid]}".encode().hex()       # padded, as Response does
        if cmd == "settext":
            controls[cid] = "" if a[1] == "-" else bytes.fromhex(a[1]).decode()
            return ""
        if cmd == "getcheck":
            return controls[cid]
        if cmd == "click":
            if cid in UNIT_RADIOS.values():
                for r in UNIT_RADIOS.values():
                    controls[r] = str(int(r == cid))
            else:
                controls.update(zip(FACTOR_FIELDS, CSA if cid == dialogs.FACTOR_BUTTONS["csa"]
                                    else NONE))
            return ""
        raise AssertionError(f"unexpected command {command!r}")

    def try_ask(self, command):
        return self.ask(command)

    def _commit(self):
        hwnd, _, c = self.open
        if hwnd == "p1":
            self.units = next(u for u, cid in UNIT_RADIOS.items() if c[cid] == "1")
            self.factors = tuple(c[f] for f in FACTOR_FIELDS)
        else:
            for kind, fields in (("c", CONSTANT), ("i", INCREMENT)):
                for k, cid in enumerate(fields):
                    self.loads[kind][k] = float(c[cid]) * PER_UNIT[self.units][1 if k == 1 else 0]


def apply_and_read(fake, settings):
    session = Session(fake)
    dialogs.apply(session, settings)
    effective, pictures = dialogs.read(session)
    assert pictures == {}                       # pictures only with a folder for them
    return effective


def test_defaults_are_read_back_and_nothing_is_changed():
    fake = FakeResponse()
    assert apply_and_read(fake, Settings()) == {
        "units": "si", "factors": "1.00,1.00,1.00", "initial": "0.00,0.00,0.00",
        "increment": "0.00,1.00,0.00"}
    assert not [c for c in fake.commands if c.startswith(("click", "settext", "cmd 1 "))]


def test_input_settings_are_kept():
    fake = FakeResponse(units="us", factors=CSA, constant=(-2000, 0, 0))
    eff = apply_and_read(fake, Settings())
    assert eff["units"] == "us" and eff["factors"] == "0.65,0.85,0.90"
    assert eff["initial"] == "-449.62,0.00,0.00" and eff["increment"] == "0.00,0.74,0.00"


def test_units_are_set_before_loads():
    """--initial is in the units in effect: set after --units, it is not converted again."""
    fake = FakeResponse()
    eff = apply_and_read(fake, Settings(units="us", initial=(-449.62, 0, 0),
                                        increment=(-1, 0, 0)))
    assert eff["units"] == "us"
    assert eff["initial"] == "-449.62,0.00,0.00" and eff["increment"] == "-1.00,0.00,0.00"
    assert fake.loads["c"][0] == pytest.approx(-2000, abs=0.1)        # kN inside Response


def test_factors_and_overrides():
    eff = apply_and_read(FakeResponse(factors=CSA), Settings(factors="none"))
    assert eff["factors"] == "1.00,1.00,1.00"
    eff = apply_and_read(FakeResponse(), Settings(factors="csa", units="kgcm"))
    assert eff["factors"] == "0.65,0.85,0.90" and eff["units"] == "kgcm"
    eff = apply_and_read(FakeResponse(constant=(-100, 5, 7)), Settings(initial=(0, 20, 0)))
    assert eff["initial"] == "0.00,20.00,0.00"      # all three loads are set


def test_shear_is_set_like_the_other_loads():
    """Since r2x 0.3.0 shear is in scope: V goes into Define Loading with N and M."""
    fake = FakeResponse(constant=(-100, 5, 7))
    eff = apply_and_read(fake, Settings(increment=(0, 1, 1)))
    assert eff["initial"] == "-100.00,5.00,7.00" and eff["increment"] == "0.00,1.00,1.00"
    eff = apply_and_read(fake, Settings(units="us", initial=(0, 0, 50), increment=(0, 0, 0)))
    assert eff["initial"] == "0.00,0.00,50.00" and eff["increment"] == "0.00,0.00,0.00"
    assert fake.loads["c"][2] == pytest.approx(50 * 4.448222)       # kips, kept in kN


def test_a_message_box_instead_of_closing_is_an_error():
    with pytest.raises(R2xError, match="Response shows a dialog 'Error': Not a number"):
        apply_and_read(FakeResponse(reject=True), Settings(initial=(1, 1, 0)))


def test_settings_args_round_trip():
    s = Settings(units="us", factors="csa", initial=(-2000.0, 0.0, 0.0),
                 increment=(0.0, -1.5, 2.0))
    assert s.args() == ["--units", "us", "--factors", "csa", "--initial=-2000,0,0",
                        "--increment=0,-1.5,2"]
    assert Settings().args() == []
