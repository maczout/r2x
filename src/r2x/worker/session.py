"""Drive one running Response-2000 instance through the in-Wine helper.

Everything here is mechanics: which window to right-click, when the clipboard has changed, which
load stage is on screen. Exported text is passed through as the exact CF_TEXT bytes Response put
on the clipboard.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import Callable

# Response-2000 main-menu command IDs (RT_MENU resource of r2k.exe 1.9.7).
CMD_SECTIONAL_RESPONSE = 5092
VK_PRIOR, VK_NEXT, VK_DOWN, VK_RETURN, VK_ESCAPE = 0x21, 0x22, 0x28, 0x0D, 0x1B
IDOK, IDCANCEL = 1, 2

# Position of "Copy Chart Data" in every chart's context menu (after "Copy Chart Picture").
COPY_CHART_DATA_DOWNS = 2


@dataclass(frozen=True)
class Chart:
    """A chart with a data export: where it sits in Response and the title its export carries."""
    key: str            # record section name (detail views) or position (control charts)
    title: str | None   # "Title :" line of the export; None: any title in CONTROL_KEYS
    grid: tuple | None  # (row, col) in the nine-graph view, or None for a control chart
    control: int | None = None  # 0 = top control chart, 1 = bottom


# Which control charts Response shows depends on the loading, so the two positions are copied
# and their titles say what they are.
CONTROL_CHARTS = (
    Chart("control_top", None, None, 0),
    Chart("control_bottom", None, None, 1),
)
# Control-chart titles r2x knows, and the record section each becomes.
CONTROL_KEYS = {
    "Control : Moment - |e_x": "moment_ex",      # moment increment, top
    "Control : Moment - |f": "moment_phi",       # moment increment, bottom
    "Control : Axial Load - |e_x": "axial_ex",   # axial-only increment, top and bottom
}
NO_SHEAR_CHARTS = (
    Chart("longitudinal_strain", "Longitudinal Strain", (1, 2)),
    Chart("shrinkage_thermal_strain", "Shrinkage & Thermal Strain", (1, 3)),
    Chart("long_reinforcement_stress", "Long. Reinforcement Stress", (2, 2)),
    Chart("long_reinf_stress_at_crack", "Long. Reinf Stress at Crack", (2, 3)),
    Chart("longitudinal_concrete_stress", "Longitudinal Concrete Stress", (3, 1)),
)


class R2xError(RuntimeError):
    """The job failed (exit status 1)."""


class WaitTimeout(R2xError):
    """Response did not react in time: an input to it may have been lost, so retrying can help."""


class OutOfScope(R2xError):
    """The input asks for an analysis r2x does not cover, such as shear (exit status 3)."""


# Control-chart titles of analyses outside r2x's scope, and why.
OUT_OF_SCOPE_TITLES = {"Control : Shear": "the loading includes shear"}


@dataclass
class Window:
    hwnd: str
    parent: str
    visible: bool
    rect: tuple[int, int, int, int]
    cls: str
    text: str


class Helper:
    """The helper process inside Wine: one command per line, one reply line (tree: more)."""

    def __init__(self, exe: str, env: dict):
        self.proc = subprocess.Popen(["wine", exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, env=env, bufsize=0)

    def _send(self, command: str) -> str:
        self.proc.stdin.write(command.encode("ascii") + b"\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise R2xError(f"helper exited during {command!r}")
        return line.decode("ascii").rstrip("\r\n")

    def ask(self, command: str) -> str:
        """Send a command; return the text after 'ok', or raise on 'err'."""
        reply = self._send(command)
        if reply == "ok" or reply.startswith("ok "):
            return reply[3:]
        raise R2xError(f"helper: {command!r} -> {reply!r}")

    def try_ask(self, command: str) -> str | None:
        try:
            return self.ask(command)
        except R2xError:
            return None

    def windows(self, which: str = "tree") -> list[Window]:
        n = int(self.ask(which))
        out = []
        for _ in range(n):
            f = self.proc.stdout.readline().decode("latin-1").rstrip("\r\n").split("\t")
            out.append(Window(f[0], f[1], f[2] == "1", tuple(int(x) for x in f[3:7]), f[7],
                              "\t".join(f[8:])))
        return out

    def close(self):
        try:
            self._send("quit")
        except Exception:
            pass
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def wait_until(predicate, timeout: float, what: str, interval: float = 0.01):
    t0 = time.monotonic()
    while True:
        result = predicate()
        if result:
            return result
        if time.monotonic() - t0 > timeout:
            raise WaitTimeout(f"timed out after {timeout:.0f} s waiting for {what}")
        time.sleep(interval)


def export_title(data: bytes) -> str | None:
    for line in data.decode("latin-1").splitlines():
        head, sep, rest = line.partition(":")
        if sep and head.strip() == "Title":
            return rest.strip()
    return None


def export_points(data: bytes) -> list[tuple[float, float]]:
    """Numeric (x, y) rows of an export, in order."""
    pts = []
    for line in data.decode("latin-1").splitlines():
        p = line.split()
        if len(p) == 2:
            try:
                pts.append((float(p[0]), float(p[1])))
            except ValueError:
                pass
    return pts


class Session:
    """A solved or solvable Response-2000 window, reached through a Helper."""

    def __init__(self, helper: Helper, note: Callable[[str], None] = lambda s: None):
        self.h = helper
        self.note = note
        self._charts: dict[str, str] | None = None

    # -- windows ------------------------------------------------------------------------------
    def main_window(self) -> tuple[str, str]:
        hwnd, _, title = self.h.ask("main").partition("\t")
        return hwnd, title

    def wait_for_file(self, stem: str, timeout: float = 60) -> str:
        """Wait until Response's main window shows the input file; return the window title."""
        def loaded():
            self.check_no_dialog()
            reply = self.h.try_ask("main")
            title = reply.partition("\t")[2] if reply else ""
            return title if stem.lower() in title.lower() else None
        return wait_until(loaded, timeout, f"Response to open {stem}", 0.1)

    def check_no_dialog(self):
        """Raise if Response is showing a message box or other dialog."""
        boxes = self.h.windows("dialogs")
        if boxes:
            raise R2xError(self.describe_dialog(boxes[0].hwnd, boxes[0].text))

    def find_charts(self) -> dict[str, str]:
        """Map chart key -> window handle for the solved No Shear view."""
        ws = [w for w in self.h.windows() if w.visible]
        grid = [w for w in ws if w.cls == "OWL_Window" and w.text == ""
                and w.rect[2] - w.rect[0] > 200 and w.rect[3] - w.rect[1] > 150]
        rows = sorted({w.rect[1] for w in grid})
        cols = sorted({w.rect[0] for w in grid})
        if len(grid) != 9 or len(rows) != 3 or len(cols) != 3:
            raise R2xError(f"expected a 3 x 3 chart grid, found {len(grid)} charts")
        at = {(rows.index(w.rect[1]) + 1, cols.index(w.rect[0]) + 1): w.hwnd for w in grid}
        ctrl = sorted((w for w in ws if w.cls == "OWL_Window:F" and w.text.startswith("Control")),
                      key=lambda w: w.rect[1])
        if len(ctrl) != 2:
            raise R2xError(f"expected 2 control charts, found {len(ctrl)}")
        charts = {c.key: ctrl[c.control].hwnd for c in CONTROL_CHARTS}
        charts.update({c.key: at[c.grid] for c in NO_SHEAR_CHARTS})
        self._charts = charts
        return charts

    # -- clipboard ----------------------------------------------------------------------------
    def copy_chart(self, chart: Chart, timeout: float = 5, attempts: int = 3) -> bytes:
        """Right-click the chart, choose Copy Chart Data, return the clipboard's CF_TEXT bytes.

        About one copy in several thousand gets no reply (seen once in about 6,500 under
        Wine 9.0; the menu keys seem to be lost). Such a copy is dismissed and tried again. A
        retry cannot pass off the wrong data: every export's title is checked, and the stage
        checks in export.py compare its contents with the control curve.
        """
        for attempt in range(1, attempts + 1):
            try:
                data = self._copy_once(chart, timeout)
                break
            except WaitTimeout as e:
                self._dismiss_popup()
                if attempt == attempts:
                    raise R2xError(f"Copy Chart Data of {chart.key} failed {attempts} times: {e}")
                self.note(f"Copy Chart Data of {chart.key} got no reply ({e}); trying again")
        title = export_title(data)
        if chart.control is not None:
            if title in CONTROL_KEYS:
                return data
            for start, why in OUT_OF_SCOPE_TITLES.items():
                if title and title.startswith(start):
                    raise OutOfScope(f"{why} (Response's control chart is {title!r})")
            raise R2xError(f"{chart.key}: unknown control chart {title!r}")
        if title != chart.title:
            raise R2xError(f"{chart.key}: export title {title!r}, expected {chart.title!r}")
        return data

    def _copy_once(self, chart: Chart, timeout: float) -> bytes:
        hwnd = (self._charts or self.find_charts())[chart.key]
        self.h.ask("clipclear")
        seq = self.h.ask("clipseq")
        self.h.ask(f"rclick {hwnd}")
        wait_until(lambda: self.h.ask("popup") == "1", timeout, f"context menu of {chart.key}", 0.005)
        for _ in range(COPY_CHART_DATA_DOWNS):
            self.h.ask(f"menukey {VK_DOWN:#x}")
        self.h.ask(f"menukey {VK_RETURN:#x}")
        wait_until(lambda: self.h.ask("clipseq") != seq, timeout, f"chart data of {chart.key}", 0.005)
        reply = wait_until(lambda: self.h.try_ask("clip"), timeout, f"clipboard text of {chart.key}",
                           0.01)
        return bytes.fromhex(reply)

    def _dismiss_popup(self, timeout: float = 2):
        """Close a context menu left open by a copy that got no reply."""
        t0 = time.monotonic()
        while self.h.ask("popup") == "1":
            if time.monotonic() - t0 > timeout:
                raise R2xError("a chart's context menu does not close")
            self.h.try_ask(f"menukey {VK_ESCAPE:#x}")
            time.sleep(0.1)

    # -- solving ------------------------------------------------------------------------------
    def solve(self, quiet: float = 1.0, timeout: float = 300) -> tuple[bytes, bytes]:
        """Solve -> Sectional Response; return the final exports of the top and bottom control
        charts.

        Under Wine there is no readable "finished" flag (the menu state lives in Response's
        process), so the solve counts as finished when the bottom control curve has not changed
        for `quiet` seconds. Response adds points about every 0.2 s while solving.
        """
        self.h.ask(f"cmd {CMD_SECTIONAL_RESPONSE}")
        t0 = time.monotonic()
        def charts_ready():
            try:
                return self.find_charts()
            except R2xError:
                self.check_no_dialog()
                return None
        wait_until(charts_ready, 60, "the solution view's charts", 0.05)
        # The top control chart's title tells an analysis with shear from one without; check it
        # now rather than after the solve.
        self.copy_chart(CONTROL_CHARTS[0])
        last, since = None, time.monotonic()
        while True:
            self.check_no_dialog()
            data = self.copy_chart(CONTROL_CHARTS[1])
            now = time.monotonic()
            if data != last:
                last, since = data, now
            elif now - since >= quiet and len(export_points(data)) >= 2:
                break
            if now - t0 > timeout:
                raise R2xError(f"solve did not settle within {timeout:.0f} s")
            time.sleep(0.05)
        top = self.copy_chart(CONTROL_CHARTS[0])
        return top, last

    # -- dialogs ------------------------------------------------------------------------------
    def describe_dialog(self, hwnd: str, title: str) -> str:
        texts = [w.text for w in self.h.windows(f"kids {hwnd}")
                 if w.cls == "Static" and w.text.strip()]
        return f"Response shows a dialog {title!r}: {' / '.join(texts)}"

    def open_dialog(self, command: int, title: str, timeout: float = 10) -> str:
        """Run a main-menu command that opens a dialog; return the dialog's window handle."""
        self.check_no_dialog()
        self.h.ask(f"cmd {command}")
        def opened():
            for w in self.h.windows("dialogs"):
                if w.text == title:
                    return w.hwnd
            return None
        return wait_until(opened, timeout, f"the {title!r} dialog", 0.02)

    def wait_for_dialog_title(self, dialog: str, title: str, timeout: float = 10):
        """Wait until an open dialog's title changes to title (a wizard's next page, say)."""
        def shown():
            others = [w for w in self.h.windows("dialogs") if w.hwnd != dialog]
            if others:
                raise R2xError(self.describe_dialog(others[0].hwnd, others[0].text))
            return any(w.hwnd == dialog and w.text == title for w in self.h.windows("dialogs"))
        wait_until(shown, timeout, f"the {title!r} dialog", 0.02)

    def control(self, dialog: str, control_id: int) -> str:
        return self.h.ask(f"find {dialog} {control_id}")

    def get_text(self, dialog: str, control_id: int) -> str:
        """A control's text, without the padding Response puts around numbers."""
        reply = self.h.ask(f"gettext {self.control(dialog, control_id)}")
        return bytes.fromhex(reply).decode("latin-1").strip()

    def set_text(self, dialog: str, control_id: int, text: str):
        encoded = text.encode("latin-1").hex() or "-"
        self.h.ask(f"settext {self.control(dialog, control_id)} {encoded}")

    def is_checked(self, dialog: str, control_id: int) -> bool:
        return self.h.ask(f"getcheck {self.control(dialog, control_id)}") == "1"

    def click(self, dialog: str, control_id: int):
        """Post a click; it takes effect after messages already posted, so wait for its result."""
        self.h.ask(f"click {self.control(dialog, control_id)}")

    def close_dialog(self, dialog: str, ok: bool, timeout: float = 10):
        """Press OK (or Cancel) and wait for the dialog to close. A message box that Response opens
        instead (rejecting a value, say) is an error that quotes it."""
        self.h.ask(f"cmd {IDOK if ok else IDCANCEL} {dialog}")
        def closed():
            others = [w for w in self.h.windows("dialogs") if w.hwnd != dialog]
            if others:
                raise R2xError(self.describe_dialog(others[0].hwnd, others[0].text))
            return self.h.ask(f"alive {dialog}") == "0"
        wait_until(closed, timeout, "the dialog to close", 0.02)
        self.check_no_dialog()

    # -- load stages --------------------------------------------------------------------------
    def press(self, vk: int, times: int = 1):
        hwnd = self.main_window()[0]
        for _ in range(times):
            self.h.ask(f"key {hwnd} {vk:#x}")
