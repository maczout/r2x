"""Response-2000's Preferences and Define Loading dialogs: apply r2x's settings and read back the
settings in effect, with a picture of each dialog for the report when asked.

Control IDs are from r2k.exe's RT_DIALOG resources (`python tools/dialogs.py r2k.exe`): dialog
320 is the Preferences page, dialog 5 is Define Loading. Units are set before loads, because
switching units converts the loads already entered (docs/cli.md).
"""

from __future__ import annotations

from pathlib import Path

from r2x.settings import Settings, format_number
from r2x.worker.session import R2xError, Session, wait_until

# Main-menu commands (RT_MENU resource).
CMD_PREFERENCES = 321          # Options > Preferences
CMD_SECTIONAL_LOADS = 152      # Loads > Sectional Loads

PREFERENCES = "Response-2000 Preferences"
UNIT_RADIOS = {"si": 5028, "us": 5029, "kgcm": 5030}
FACTOR_FIELDS = (5041, 5044, 5045)                       # concrete, steel, prestress
FACTOR_BUTTONS = {"csa": 5046, "none": 5023}
FACTOR_VALUES = {"csa": ("0.65", "0.85", "0.90"), "none": ("1.00", "1.00", "1.00")}

LOADING = "Define Loading"
CONSTANT = (101, 5052, 5053)                             # axial load, moment, shear
INCREMENT = (5054, 5055, 5056)


def apply(session: Session, settings: Settings):
    """Set the requested settings through the dialogs. Settings left as None are not touched."""
    if settings.units or settings.factors:
        dlg = session.open_dialog(CMD_PREFERENCES, PREFERENCES)
        if settings.units:
            session.click(dlg, UNIT_RADIOS[settings.units])
            wait_until(lambda: session.is_checked(dlg, UNIT_RADIOS[settings.units]), 5,
                       f"the {settings.units} units button", 0.02)
        if settings.factors:
            session.click(dlg, FACTOR_BUTTONS[settings.factors])
            want = FACTOR_VALUES[settings.factors]
            wait_until(lambda: tuple(session.get_text(dlg, c) for c in FACTOR_FIELDS) == want, 5,
                       f"the {settings.factors} material factors", 0.02)
        session.close_dialog(dlg, ok=True)

    if settings.initial is not None or settings.increment is not None:
        dlg = session.open_dialog(CMD_SECTIONAL_LOADS, LOADING)
        for fields, loads in ((CONSTANT, settings.initial), (INCREMENT, settings.increment)):
            if loads is not None:
                for cid, value in zip(fields, loads):
                    session.set_text(dlg, cid, format_number(value))
        session.close_dialog(dlg, ok=True)


def read(session: Session, pictures: Path | None = None) -> tuple[dict[str, str], dict[str, bytes]]:
    """The settings in effect, as Response's dialogs show them, for the record header.

    With a pictures folder (scratch space for the helper), also each dialog as it is on screen,
    for the report: "input/preferences" and "input/loading".
    """
    shots: dict[str, bytes] = {}
    dlg = session.open_dialog(CMD_PREFERENCES, PREFERENCES)
    units = [name for name, cid in UNIT_RADIOS.items() if session.is_checked(dlg, cid)]
    factors = [session.get_text(dlg, c) for c in FACTOR_FIELDS]
    if pictures is not None:
        shots["input/preferences"] = session.snapshot(pictures, settled=True, window=dlg)
    session.close_dialog(dlg, ok=False)
    if len(units) != 1:
        raise R2xError(f"Preferences shows {len(units)} unit systems selected")

    dlg = session.open_dialog(CMD_SECTIONAL_LOADS, LOADING)
    constant = [session.get_text(dlg, c) for c in CONSTANT]
    increment = [session.get_text(dlg, c) for c in INCREMENT]
    if pictures is not None:
        shots["input/loading"] = session.snapshot(pictures, settled=True, window=dlg)
    session.close_dialog(dlg, ok=False)
    return ({"units": units[0], "factors": ",".join(factors),
             "initial": ",".join(constant), "increment": ",".join(increment)}, shots)


# -- File > New ---------------------------------------------------------------------------------
CMD_QUICK_DEFINE = 150         # Define > Quick Define
QUICK_DEFINE = "Quick Define - Step {} of 4"
WIZARD_NEXT, WIZARD_FINISH = 0x3024, 0x3025     # property-sheet wizard buttons


def quick_define(session: Session, timeout: float = 10):
    """Define a new section by accepting every default of the four Quick Define pages.

    On a fresh start this is what File > New shows. File > New's own command (24331) does not
    respond to a posted message under Wine, so r2x opens the wizard with Define > Quick Define.
    """
    start_title = session.main_window()[1]
    wizard = session.open_dialog(CMD_QUICK_DEFINE, QUICK_DEFINE.format(1))
    for step in range(1, 5):
        session.click(wizard, WIZARD_FINISH if step == 4 else WIZARD_NEXT)
        if step < 4:
            session.wait_for_dialog_title(wizard, QUICK_DEFINE.format(step + 1), timeout)
    wait_until(lambda: session.h.ask(f"alive {wizard}") == "0", timeout,
               "the Quick Define wizard to finish", 0.02)
    session.check_no_dialog()
    wait_until(lambda: session.main_window()[1] != start_title, timeout,
               "Response to show the new section", 0.02)
