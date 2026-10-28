"""One define step: open the section in Response, go through one of its dialogs question by
question, press OK, Save As, and take the pictures for the section's report.

    python -m r2x.worker define NOUN [ACTION [NAME]] (--input FILE | --new) --out FILE [options]

The questions go to the command line over stdout and the answers come back on stdin
(r2x.ask). Everything is done through Response's own controls, in the dialog's order (the
catalogue, r2x/dialogs.json), and Response writes the file with its own Save As: r2x never
reads or writes the section's XML. A value is set only when the answer differs from what the
dialog shows, so Enter leaves a field exactly as Response had it.

Response's own dialogs that come up along the way are passed on, in its words: a Yes/No
question is asked of the person; a message is shown; its Reinforcement Types list (for a bar
designation it does not know) becomes a question for a bar from that list; its View Data
window of definition errors is shown.
"""

from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, IO

from r2x import ask, report as html_report
from r2x.ask import NO, YES, Question
from r2x.catalogue import Dialog, Field, Page, Step
from r2x.progress import Event, note
from r2x.settings import Settings
from r2x.worker import dialogs as settings_dialogs
from r2x.worker.session import IDCANCEL, IDOK, R2xError, Session, Window, wait_until, wine_path

# Response's menu commands and controls outside the catalogue.
CMD_SAVE_AS = 24334            # File > Save As
SAVE_AS_TITLE = "Save As"
FILE_NAME_BOX = 1148           # the common file dialog's file name (a ComboBoxEx)
CMD_GENERAL = 103              # Define > Edit General, for the date
GENERAL_TITLE = "General  Definitions"
DATE_BOX = 5050
WIZARD_BACK, WIZARD_NEXT, WIZARD_FINISH = 0x3023, 0x3024, 0x3025
YES_BUTTON, NO_BUTTON = 6, 7   # IDYES, IDNO in a message box
BAR_CHOOSER = "Reinforcement Types"
BAR_LIST = 5072                # its list box: one row per line of rebar.dat
VIEW_DATA = "View Data"        # Response's window of definition errors
VIEW_DATA_TEXT = 4028
NEW_SECTION = "Do you wish to create a new section?"
SHAPE_SUFFIX = " Section"      # list view items are "Rectangle Section" ...


class Abort(R2xError):
    """The person stopped answering (end of input): nothing is saved."""


# -- questions to the command line ----------------------------------------------------------------
class Asker:
    """Questions over stdout, answers on stdin (r2x.ask)."""

    def __init__(self, out: IO[str] = sys.stdout, inp: IO[str] = sys.stdin):
        self.out, self.inp = out, inp

    def ask(self, q: Question) -> str | None:
        ask.write(self.out, **ask.question_message(q))
        line = self.inp.readline()
        if not line:
            raise Abort("stopped without an answer; nothing saved")
        data = ask.read_line(line)
        if "answer" not in data:
            raise R2xError(f"expected an answer, got {line[:80]!r}")
        return data["answer"]

    def say(self, text: str):
        ask.write(self.out, say=text)

    def set(self, pairs: list[tuple[str, str]]):
        ask.write(self.out, set=[list(p) for p in pairs])

    def show(self, pairs: list[tuple[str, str]]):
        ask.write(self.out, show=[list(p) for p in pairs])

    def done(self, **info):
        ask.write(self.out, done=info)


# -- rebar.dat ----------------------------------------------------------------------------------
def bar_names(rebar_dat: Path) -> list[str]:
    """The names in Response's bar list, in its order: one per line of rebar.dat that is not a
    comment, the name being everything before the line's last two numbers (diameter, area).
    Response's Reinforcement Types list has one row per such line, in this order."""
    names = []
    for line in rebar_dat.read_text(encoding="latin-1").splitlines():
        if line.lstrip().startswith("//") or not line.strip():
            continue
        names.append(" ".join(line.split()[:-2]))
    return names


def bar_index(names: list[str], text: str) -> int | None:
    t = " ".join(text.split()).lower()
    return next((i for i, n in enumerate(names) if n.lower() == t), None)


# -- reading and setting the dialog's controls ----------------------------------------------------
@dataclass
class Shown:
    """A field as the dialog shows it now."""
    field: Field
    value: str          # check: y or n; choice, shape, radio: the item's text
    label: str
    unit: str
    choices: list[str]
    enabled: bool


def clean_label(text: str) -> str:
    t = " ".join(text.replace("&", "").split())
    t = re.sub(r"\s*(or)?:$", "", t)
    return t


class Driver:
    """Drives one of Response's dialogs for a define step, passing Response's own questions and
    messages on to the person."""

    def __init__(self, session: Session, asker: Asker, rebar_dat: Path | None,
                 pictures: Path | None):
        self.s, self.h, self.asker = session, session.h, asker
        self.bars = bar_names(rebar_dat) if rebar_dat and rebar_dat.is_file() else []
        self.pictures = pictures
        self.changed: list[tuple[Field, str, str]] = []   # field, label, answer
        self.pending_bars: list[tuple[str, str, str]] = []   # (key, label, answer) set on a page
        self.picked: dict[str, str] = {}                  # key: the bar picked from Response's list
        self.shots: dict[str, bytes] = {}
        self._own: set[str] = set()                       # the dialogs being driven

    # controls -----------------------------------------------------------------------------
    def ctl(self, container: str, cid: int) -> str:
        return self.h.ask(f"find {container} {cid}")

    def text(self, hwnd: str) -> str:
        return bytes.fromhex(self.h.ask(f"gettext {hwnd}")).decode("latin-1")

    def items(self, cmd: str, hwnd: str) -> list[str]:
        return [bytes.fromhex(x).decode("latin-1") for x in self.h.lines(f"{cmd} {hwnd}")]

    def read(self, container: str, f: Field) -> Shown:
        label = f.question
        if f.label is not None:
            shown = clean_label(self.text(self.ctl(container, f.label)))
            label = f.prefix + shown if shown else f.question
        unit = clean_label(self.text(self.ctl(container, f.unit))) if f.unit else ""
        if f.kind == "radio":
            checked = [o.text for o in f.options
                       if self.h.ask(f"getcheck {self.ctl(container, o.id)}") == "1"]
            return Shown(f, checked[0] if checked else "", label, unit,
                         [o.text for o in f.options], True)
        hwnd = self.ctl(container, f.id)
        enabled = self.h.ask(f"enabled {hwnd}") == "1" and self.h.ask(f"alive {hwnd}") == "1"
        choices: list[str] = []
        if f.kind == "check":
            value = YES if self.h.ask(f"getcheck {hwnd}") == "1" else NO
        elif f.kind == "choice":
            choices = self.items("cbitems", hwnd)
            i = int(self.h.ask(f"cbget {hwnd}"))
            value = choices[i] if 0 <= i < len(choices) else ""
        elif f.kind == "shape":
            choices = [c.removesuffix(SHAPE_SUFFIX) for c in self.items("lvitems", hwnd)]
            i = int(self.h.ask(f"lvget {hwnd}"))
            value = choices[i] if 0 <= i < len(choices) else ""
        else:
            raw = self.text(hwnd)
            lines = raw.split("\r\n")
            if f.kind == "first-line":
                value = lines[0]
            elif f.kind == "other-lines":
                value = " / ".join(lines[1:])
            else:
                value = raw.strip()
        return Shown(f, value, label, unit, choices, enabled)

    def question(self, sh: Shown) -> Question:
        f = sh.field
        kind = {"first-line": "text", "other-lines": "text"}.get(f.kind, f.kind)
        hint = ""
        if f.kind == "bar":
            hint = "a name from Response's bar list (rebar.dat), e.g. 25M or #8"
        elif f.kind == "other-lines":
            hint = "one line; it replaces every line after the title"
        return Question(f.key, sh.label, kind, sh.value, sh.unit, sh.choices, True, hint)

    def put(self, container: str, sh: Shown, answer: str):
        """Put an answer into the dialog's control as a person would."""
        f = sh.field
        if f.kind == "radio":
            opt = next(o for o in f.options if o.text == answer)
            self.act(f"sclick {self.ctl(container, opt.id)}")
            return
        hwnd = self.ctl(container, f.id)
        if f.kind == "check":
            self.act(f"sclick {hwnd}")
            wait_until(lambda: (self.h.ask(f"getcheck {hwnd}") == "1") == (answer == YES), 5,
                       f"the {sh.label} check box", 0.02)
        elif f.kind == "choice":
            self.act(f"cbselect {hwnd} {sh.choices.index(answer)}")
        elif f.kind == "shape":
            self.act(f"lvselect {hwnd} {sh.choices.index(answer)}")
        elif f.kind in ("first-line", "other-lines"):
            lines = self.text(hwnd).split("\r\n")
            if f.kind == "first-line":
                lines[0] = answer
            else:
                lines = lines[:1] + ([answer] if answer else [])
            joined = "\r\n".join(lines)
            self.act(f"settext {hwnd} {joined.encode('latin-1').hex() or '-'}")
        else:
            self.act(f"settext {hwnd} {answer.encode('latin-1').hex() or '-'}")

    def act(self, command: str):
        """A command that Response may answer with a dialog of its own: pass that on."""
        reply = self.h.ask(command)
        if reply == "busy":
            self.interruptions(wait=2.0)

    # fields -------------------------------------------------------------------------------
    def ask_fields(self, container: str, fields: tuple[Field, ...]) -> int:
        """Ask each field in order and set the answers; return how many changed."""
        n = 0
        for f in fields:
            if f.unless is not None and self.h.ask(
                    f"getcheck {self.ctl(container, f.unless)}") == "1":
                continue
            sh = self.read(container, f)
            if not sh.enabled:
                continue
            answer = self.asker.ask(self.question(sh))
            if answer is None or self.same(sh, answer):
                continue
            self.put(container, sh, answer)
            self.changed.append((f, sh.label, answer))
            if f.kind == "bar":
                self.pending_bars.append((f.key, sh.label, answer))
            n += 1
        return n

    @staticmethod
    def same(sh: Shown, answer: str) -> bool:
        if sh.field.kind in ("number", "integer"):
            try:
                return float(sh.value) == float(answer)
            except ValueError:
                return False
        if sh.field.kind == "bar":
            return sh.value.lower() == answer.strip().lower()
        return sh.value == answer

    # Response's own dialogs -----------------------------------------------------------------
    def others(self, own: set[str]) -> list[Window]:
        return [w for w in self.h.windows("dialogs") if w.hwnd not in own]

    def interruptions(self, wait: float = 0.0, own: set[str] | None = None) -> int:
        """Pass on any dialog Response has opened besides the ones being driven (own); with
        wait, look for one that far ahead. Return how many were handled."""
        own = own if own is not None else self._own
        handled, t0 = 0, time.monotonic()
        while True:
            boxes = self.others(own)
            if not boxes:
                if time.monotonic() - t0 >= wait:
                    return handled
                time.sleep(0.05)
                continue
            self.handle(boxes[0])
            handled += 1
            t0 = time.monotonic()
            wait = min(wait, 0.3)

    def handle(self, box: Window, settle: float = 1.5):
        """Pass on one of Response's dialogs. A dialog is read again for a moment until it is
        recognised, since Response may still be building it (its title, its buttons)."""
        t0 = time.monotonic()
        while True:
            if self.h.ask(f"alive {box.hwnd}") == "0":
                return
            title = next((w.text for w in self.h.windows("dialogs") if w.hwnd == box.hwnd),
                         box.text)
            kids = self.h.windows(f"kids {box.hwnd}")
            texts = [w.text for w in kids if w.cls == "Static" and w.text.strip()]
            buttons = {w.text.replace("&", ""): w for w in kids if w.cls == "Button"}
            if title == BAR_CHOOSER:
                return self.choose_bar(box)
            if title == VIEW_DATA:
                body = self.text(self.ctl(box.hwnd, VIEW_DATA_TEXT)).replace("\r\n", "\n")
                self.asker.say("Response reports: "
                               + " / ".join(l.strip() for l in body.splitlines() if l.strip()))
                self.h.ask(f"cmd {IDOK} {box.hwnd}")
                return self.gone(box.hwnd)
            if "Yes" in buttons and "No" in buttons and texts:
                message = " ".join(texts)
                if message == NEW_SECTION:   # define quick on an existing file: a new section
                    self.h.ask(f"cmd {YES_BUTTON} {box.hwnd}")
                else:
                    a = self.asker.ask(Question("response", f"Response asks: {message}", "yesno",
                                                keep=False))
                    self.h.ask(f"cmd {YES_BUTTON if a == YES else NO_BUTTON} {box.hwnd}")
                return self.gone(box.hwnd)
            if buttons and set(buttons) <= {"OK", "Cancel", "Help"} and texts:
                self.asker.say(f"Response says: {' '.join(texts)}")
                self.h.ask(f"cmd {IDOK} {box.hwnd}")
                return self.gone(box.hwnd)
            if time.monotonic() - t0 > settle:
                raise R2xError(self.s.describe_dialog(box.hwnd, title))
            time.sleep(0.1)

    def gone(self, hwnd: str, timeout: float = 10):
        wait_until(lambda: self.h.ask(f"alive {hwnd}") == "0", timeout, "Response's dialog to close",
                   0.02)

    def choose_bar(self, box: Window):
        """Response does not know a bar designation and offers its list (one row per line of
        rebar.dat). Ask for one from that list; Response's own Cancel would take the first."""
        unknown = [b for b in self.pending_bars if bar_index(self.bars, b[2]) is None]
        key, label, given = unknown[0] if unknown else ("bar", "Bar", "")
        if unknown:
            self.pending_bars.remove(unknown[0])
        while True:
            a = self.asker.ask(Question(
                "bar", f"Response has no bar {given!r}; {label} from its list", "bar", keep=False,
                hint="a name in rebar.dat: " + ", ".join(self.bars[:16]) + ", ..."))
            i = bar_index(self.bars, a or "")
            if i is not None:
                break
            self.asker.say(f"{a!r} is not in Response's bar list (rebar.dat)")
            given = a or ""
        lb = self.ctl(box.hwnd, BAR_LIST)
        self.h.ask(f"lbselect {lb} {i}")
        self.h.ask(f"cmd {IDOK} {box.hwnd}")
        self.gone(box.hwnd)
        self.picked[key] = self.bars[i]
        if key == "bar" and not unknown:
            self.changed.append((Field("bar", "bar", label), label, self.bars[i]))

    # buttons --------------------------------------------------------------------------------
    def press(self, container: str, button: int, done: Callable[[], bool], what: str,
              own: set[str], timeout: float = 20):
        """Press a button and wait until done(), passing on Response's dialogs meanwhile."""
        self._own = own
        self.act(f"sclick {self.ctl(container, button)}")
        t0 = time.monotonic()
        while not done():
            if self.interruptions(0.0, own):
                t0 = time.monotonic()
            elif time.monotonic() - t0 > timeout:
                raise R2xError(f"Response did not {what} within {timeout:.0f} s")
            time.sleep(0.03)
        self.interruptions(0.3, own)

    def open(self, menu: int, title: str, timeout: float = 10) -> str:
        """Run a menu command and wait for its dialog, passing on Response's questions first
        (Quick Define on an existing section asks whether to start a new one)."""
        self.s.check_no_dialog()
        self.h.ask(f"cmd {menu}")
        t0 = time.monotonic()
        while True:
            boxes = self.h.windows("dialogs")
            for w in boxes:
                if w.text == title:
                    self._own = {w.hwnd}
                    return w.hwnd
            if boxes and time.monotonic() - t0 > 0.5:
                # Not the dialog asked for (a box of Response's, or the dialog still untitled).
                self._own = set()
                try:
                    self.handle(boxes[0], settle=0.5)
                except R2xError:
                    if time.monotonic() - t0 > timeout:
                        raise
                t0 = time.monotonic() if self.h.ask(f"alive {boxes[0].hwnd}") == "0" else t0
            elif time.monotonic() - t0 > timeout:
                raise R2xError(f"Response did not open {title!r} within {timeout:.0f} s")
            time.sleep(0.03)

    def page(self, sheet: str, title: str) -> str:
        """The page of a property sheet with this title, shown."""
        index, hwnd = self.h.ask(f"psget {sheet}").split()
        if self.text(hwnd) == title:
            return hwnd
        for i in range(8):
            if self.h.try_ask(f"psselect {sheet} {i}") is None:
                break
            index, hwnd = self.h.ask(f"psget {sheet}").split()
            if self.text(hwnd) == title:
                return hwnd
        raise R2xError(f"the {title!r} page is not in the dialog")

    def snap(self, key: str, hwnd: str | None = None):
        if self.pictures is not None:
            self.shots[key] = self.s.snapshot(self.pictures, settled=True, window=hwnd)

    def readback(self, container: str, fields: tuple[Field, ...]) -> list[tuple[str, str, str]]:
        """(key, label, value with its unit) of each field the dialog shows."""
        out = []
        for f in fields:
            if f.unless is not None and self.h.ask(
                    f"getcheck {self.ctl(container, f.unless)}") == "1":
                continue
            sh = self.read(container, f)
            if not sh.enabled:
                continue
            value = f"{sh.value} {sh.unit}".strip() if sh.value != "" else "(blank)"
            out.append((f.key, sh.label, value))
        return out

    def changes(self, read: list[tuple[str, str, str]]) -> list[tuple[str, str]]:
        """What the step changed, as read back: the fields answered differently from what the
        dialog showed, with a bar picked from Response's list in place of the one given."""
        keys = {f.key for f, _, _ in self.changed}
        return [(label, self.picked.get(key, value)) for key, label, value in read
                if key in keys]


# -- the steps ----------------------------------------------------------------------------------
@dataclass
class Outcome:
    changed: bool                       # whether the section changed (else nothing is saved)
    readback: list[tuple[str, str]] = field(default_factory=list)


def quick(d: Driver, dialog: Dialog, date: str | None) -> Outcome:
    """Define > Quick Define, page by page: a new section."""
    first = dialog.pages[0].title
    wizard = d.open(dialog.menu, first)
    own = {wizard}
    read = []
    for k, page in enumerate(dialog.pages):
        container = d.h.ask(f"psget {wizard}").split()[1]
        d.pending_bars = []
        d.ask_fields(container, page.fields)
        read += d.readback(container, page.fields)
        d.snap(f"dialog/{k + 1}", wizard)
        last = k == len(dialog.pages) - 1
        if last:
            d.press(wizard, WIZARD_FINISH, lambda: d.h.ask(f"alive {wizard}") == "0",
                    "finish Quick Define", own)
        else:
            nxt = dialog.pages[k + 1].title
            d.press(wizard, WIZARD_NEXT,
                    lambda: any(w.hwnd == wizard and w.text == nxt
                                for w in d.h.windows("dialogs")), f"show {nxt!r}", own)
    d.interruptions(0.5, set())       # View Data, if Response found errors in the section
    if date:
        set_date(d, date)
    return Outcome(True, d.changes(read))


def set_date(d: Driver, date: str):
    """Edit General's date: Response stamps a new section with its own clock's date, which is
    the container's (UTC); r2x sets the date of the computer r2x was run from."""
    dlg = d.open(CMD_GENERAL, GENERAL_TITLE)
    box = d.ctl(dlg, DATE_BOX)
    if d.text(box).strip() != date:
        d.act(f"settext {box} {date.encode('latin-1').hex()}")
        d.press(dlg, IDOK, lambda: d.h.ask(f"alive {dlg}") == "0", "close Edit General", {dlg})
    else:
        d.h.ask(f"cmd {IDCANCEL} {dlg}")
        d.gone(dlg)


def form(d: Driver, dialog: Dialog) -> Outcome:
    """A dialog or one page of a property sheet: its fields, then OK."""
    page = dialog.pages[0]
    dlg = d.open(dialog.menu, dialog.title)
    container = d.page(dlg, page.title) if dialog.kind == "sheet" else dlg
    n = d.ask_fields(container, page.fields)
    d.snap("dialog/1", dlg)
    if not n:
        d.h.ask(f"cmd {IDCANCEL} {dlg}")
        d.gone(dlg)
        return Outcome(False)
    d.press(dlg, IDOK, lambda: d.h.ask(f"alive {dlg}") == "0", f"close {dialog.title!r}", {dlg})
    d.interruptions(0.5, set())
    # Read back what Response kept.
    dlg = d.open(dialog.menu, dialog.title)
    container = d.page(dlg, page.title) if dialog.kind == "sheet" else dlg
    read = d.changes(d.readback(container, page.fields))
    d.h.ask(f"cmd {IDCANCEL} {dlg}")
    d.gone(dlg)
    return Outcome(True, read)


def names_in(d: Driver, page: str, dialog: Dialog) -> list[str]:
    return d.items("lbitems", d.ctl(page, dialog.list.box))


def listed(d: Driver, dialog: Dialog, action: str | None, name: str | None) -> Outcome:
    """A list of named items (layers, stirrup types, tendons): add, modify or delete one."""
    page, lc = dialog.pages[0], dialog.list
    dlg = d.open(dialog.menu, dialog.title)
    container = d.page(dlg, page.title)
    names = names_in(d, container, dialog)
    if action is None:
        a = d.asker.ask(Question("action", f"Add, modify or delete a {dialog.item}", "choice",
                                 "Modify" if names else "Add", "",
                                 ["Add", "Modify", "Delete"] if names else ["Add"]))
        action = (a or ("Modify" if names else "Add")).lower()
    if action in ("modify", "delete"):
        if not names:
            raise R2xError(f"Response lists no {dialog.item} to {action}")
        if name is None:
            name = d.asker.ask(Question("name", f"{dialog.item.capitalize()}", "choice",
                                        names[0], "", names, len(names) == 1)) or names[0]
        match = [n for n in names if n == name] or [n for n in names if n.lower() == name.lower()]
        if not match:
            raise R2xError(f"Response lists no {dialog.item} {name!r} (it has "
                           f"{', '.join(names)})")
        name = match[0]
        box = d.ctl(container, lc.box)
        d.act(f"lbselect {box} {names.index(name)}")
    name_box = d.ctl(container, lc.name)
    if action == "delete":
        d.snap("dialog/1", dlg)
        d.press(container, lc.delete, lambda: name not in names_in(d, container, dialog),
                f"delete {name!r}", {dlg})
        read = [(dialog.item.capitalize(), f"{name} deleted")]
    else:
        if action == "add":
            if name is None:
                current = d.text(name_box).strip()
                name = d.asker.ask(Question("name", "Name", "text",
                                            current if current not in names else "", "", [],
                                            bool(current) and current not in names))
                name = name if name is not None else current
            if d.text(name_box).strip() != name:
                d.act(f"settext {name_box} {name.encode('latin-1').hex()}")
        else:
            new = d.asker.ask(Question("name", "Name", "text", name))
            if new is not None and new != name:
                d.act(f"settext {name_box} {new.encode('latin-1').hex()}")
                d.changed.append((Field("name", "text", "Name"), "Name", new))
        d.pending_bars = []
        n = d.ask_fields(container, page.fields)
        d.snap("dialog/1", dlg)
        if action == "modify" and not n and not d.changed:
            d.h.ask(f"cmd {IDCANCEL} {dlg}")
            d.gone(dlg)
            return Outcome(False)
        renamed = next((answer for f, _, answer in d.changed if f.key == "name"), None)
        before = names_in(d, container, dialog)
        d.press(container, lc.add if action == "add" else lc.modify,
                lambda: True, f"{action} {name!r}", {dlg})
        after = names_in(d, container, dialog)
        new = [n for n in after if n not in before]
        if action == "add" and new:      # Response may give it a name of its own (top1)
            if new[0] != name:
                d.asker.say(f"Response named the new {dialog.item} {new[0]!r}")
            name = new[0]
        if renamed and renamed in after:
            name = renamed
    d.press(dlg, IDOK, lambda: d.h.ask(f"alive {dlg}") == "0", f"close {dialog.title!r}", {dlg})
    d.interruptions(0.5, set())
    if action != "delete":
        dlg = d.open(dialog.menu, dialog.title)
        container = d.page(dlg, page.title)
        names = names_in(d, container, dialog)
        if name not in names:
            raise R2xError(f"after {action}, Response lists no {dialog.item} {name!r}")
        d.act(f"lbselect {d.ctl(container, lc.box)} {names.index(name)}")
        read = [(dialog.item.capitalize(), name)] + [(label, value) for _, label, value
                                                     in d.readback(container, page.fields)]
        d.h.ask(f"cmd {IDCANCEL} {dlg}")
        d.gone(dlg)
    return Outcome(True, read)


def show(d: Driver, dialog: Dialog) -> list[tuple[str, str]]:
    """A dialog's values, as Response shows them; nothing is pressed but Cancel."""
    if dialog.kind == "wizard":
        raise R2xError("Quick Define always starts a new section: show general, section, ... "
                       "instead")
    dlg = d.open(dialog.menu, dialog.title)
    page = dialog.pages[0]
    container = d.page(dlg, page.title) if dialog.kind in ("sheet", "list") else dlg
    out = []
    if dialog.kind == "list":
        box = d.ctl(container, dialog.list.box)
        names = names_in(d, container, dialog)
        if not names:
            out.append((dialog.item.capitalize() + "s", "none"))
        for i, n in enumerate(names):
            d.act(f"lbselect {box} {i}")
            out.append((f"{dialog.item.capitalize()} {n}", ""))
            out += [("  " + label, value) for _, label, value
                    in d.readback(container, page.fields)]
    else:
        out = [(label, value) for _, label, value in d.readback(container, page.fields)]
    d.snap("dialog/1", dlg)
    d.h.ask(f"cmd {IDCANCEL} {dlg}")
    d.gone(dlg)
    return out


def save_as(session: Session, folder: Path, name: str) -> bytes:
    """File > Save As into folder/name; return the bytes Response wrote."""
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / name
    target.unlink(missing_ok=True)
    dlg = session.open_dialog(CMD_SAVE_AS, SAVE_AS_TITLE)
    session.set_text(dlg, FILE_NAME_BOX, wine_path(target))
    session.h.ask(f"cmd {IDOK} {dlg}")
    wait_until(lambda: target.exists() and session.h.ask(f"alive {dlg}") == "0", 20,
               "Response to save the file", 0.05)
    session.check_no_dialog()
    size = -1
    def steady():   # Response may still be writing when the file appears
        nonlocal size
        now = target.stat().st_size
        ok = now == size and now > 0
        size = now
        return ok
    wait_until(steady, 10, "the saved file", 0.05)
    return target.read_bytes()


# -- the job ------------------------------------------------------------------------------------
def run_define(step: Step, input_file: Path | None, out: Path, response_dir: Path, prefix: Path,
               report: Path | None = None, date: str | None = None,
               settings: Settings = Settings(), display: str | None = None,
               asker: Asker | None = None,
               on_event: Callable[[Event], None] = lambda e: None) -> dict:
    """One define step on input_file (or a new section), saved by Response to out, with the
    section's report rewritten beside it when report is given. Returns what was done."""
    from r2x.worker.runner import start_response, write_files

    asker = asker or Asker()
    t0 = time.monotonic()
    dialog = step.dialog
    if input_file is None and dialog.noun != "quick":
        raise R2xError(f"define {dialog.noun} needs a section: define quick first, or open a "
                       "file")
    with start_response(input_file, response_dir, prefix, display, on_event=on_event) as running:
        session, job = running.session, running.job
        pictures = job / "pictures" if report is not None else None
        if pictures:
            pictures.mkdir()
        if settings.units or settings.factors:
            settings_dialogs.apply(session, settings)   # a session's units, before Quick Define
        d = Driver(session, asker, job / "Response" / "rebar.dat", pictures)
        if dialog.kind == "wizard":
            outcome = quick(d, dialog, date)
        elif dialog.kind == "list":
            outcome = listed(d, dialog, step.action, step.name)
        else:
            outcome = form(d, dialog)
        if not outcome.changed:
            asker.say("nothing changed; the file is as it was")
            asker.done(saved=False, seconds=round(time.monotonic() - t0, 1))
            return {"saved": False}
        data = save_as(session, job / "saved", out.name)
        title = session.main_window()[1].split("  -  ")[-1].strip()
        if pictures is not None:
            d.snap("input/screen")
    asker.set(outcome.readback)
    files = []
    if report is not None:
        page = html_report.build_define(out.name, step_title(step), d.shots, data)
        files.append((report, page.encode("utf-8")))
    files.append((out, data))
    write_files(files)
    asker.done(saved=True, file=out.name, title=title, seconds=round(time.monotonic() - t0, 1))
    return {"saved": True}


def run_show(step: Step, input_file: Path, response_dir: Path, prefix: Path,
             display: str | None = None, asker: Asker | None = None,
             on_event: Callable[[Event], None] = lambda e: None):
    """A dialog's values for show: Response opens the file, the dialog is read and cancelled."""
    from r2x.worker.runner import start_response

    asker = asker or Asker()
    with start_response(input_file, response_dir, prefix, display, on_event=on_event) as running:
        d = Driver(running.session, asker, None, None)
        asker.show(show(d, step.dialog))
    asker.done(saved=False)


def run_file(input_file: Path, out: Path | None, response_dir: Path, prefix: Path,
             report: Path | None, caption: str, display: str | None = None,
             asker: Asker | None = None, on_event: Callable[[Event], None] = lambda e: None):
    """No dialog: Response opens the file; with out, saves it there (File > Save As); and the
    report is rewritten with its input screen. For open, save and undo in a session."""
    from r2x.worker.runner import start_response, write_files

    asker = asker or Asker()
    t0 = time.monotonic()
    with start_response(input_file, response_dir, prefix, display, on_event=on_event) as running:
        session, job = running.session, running.job
        data = save_as(session, job / "saved", out.name) if out is not None else None
        title = session.main_window()[1].split("  -  ")[-1].strip()
        shots = {}
        if report is not None:
            pictures = job / "pictures"
            pictures.mkdir()
            shots["input/screen"] = session.snapshot(pictures, settled=True)
    files = []
    name = (out or input_file).name
    if report is not None:
        page = html_report.build_define(name, caption, shots,
                                        data if data is not None else input_file.read_bytes())
        files.append((report, page.encode("utf-8")))
    if out is not None:
        files.append((out, data))
    write_files(files)
    asker.done(saved=out is not None, file=name, title=title,
               seconds=round(time.monotonic() - t0, 1))


def step_title(step: Step) -> str:
    return "define " + " ".join(step.words())


# -- command line -------------------------------------------------------------------------------
def main(argv: list[str]) -> int:
    import argparse
    import os

    from r2x.catalogue import CatalogueError, parse_step
    from r2x.progress import FAILED, SOLVED, USAGE
    from r2x.settings import FACTORS, UNITS

    p = argparse.ArgumentParser(prog="python -m r2x.worker define",
                                description="One define step through Response's own dialog.")
    p.add_argument("words", nargs="*", metavar="WORD", help="NOUN [ACTION [NAME]]")
    p.add_argument("--input", type=Path, help="the section's file (left out: a new section)")
    p.add_argument("--out", type=Path, help="where Response saves the section")
    p.add_argument("--report", type=Path, help="the section's report, rewritten")
    p.add_argument("--date", help="Edit General's date for a new section (YYYY/MM/DD)")
    p.add_argument("--units", choices=UNITS, help="set before Quick Define")
    p.add_argument("--factors", choices=FACTORS, help="set before Quick Define")
    p.add_argument("--show", action="store_true", help="only read the dialog's values")
    p.add_argument("--screen", metavar="CAPTION",
                   help="no dialog: rewrite the report with the input screen (and with --out, "
                        "Save As there first); CAPTION says what was done")
    p.add_argument("--response-dir", type=Path, default=os.environ.get("R2X_RESPONSE_DIR"))
    p.add_argument("--prefix", type=Path,
                   default=os.environ.get("R2X_WINEPREFIX", Path.home() / ".cache/r2x/prefix"))
    p.add_argument("--display")
    a = p.parse_args(argv)
    report = lambda e: print(e.line(), file=sys.stderr, flush=True)
    if not a.response_dir:
        p.error("--response-dir or $R2X_RESPONSE_DIR is required")
    if a.screen is not None:
        if a.input is None:
            p.error("--screen needs --input")
        try:
            run_file(a.input, a.out, a.response_dir, a.prefix, a.report, a.screen, a.display,
                     on_event=report)
        except R2xError as e:
            report(Event("failed", str(e)))
            return FAILED
        return SOLVED
    try:
        step = parse_step(a.words)
    except CatalogueError as e:
        report(Event("usage", str(e)))
        return USAGE
    try:
        if a.show:
            if a.input is None:
                raise R2xError("show needs --input")
            run_show(step, a.input, a.response_dir, a.prefix, a.display, on_event=report)
        else:
            if a.out is None:
                p.error("--out is required")
            run_define(step, a.input, a.out, a.response_dir, a.prefix, a.report, a.date,
                       Settings(a.units, a.factors), a.display, on_event=report)
    except R2xError as e:
        report(Event("failed", str(e)))
        return FAILED
    return SOLVED
