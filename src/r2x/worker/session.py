"""Drive one running Response-2000 instance through the in-Wine helper.

Everything here is mechanics: which window to right-click, when the clipboard has changed, which
load stage is on screen. Exported text is passed through as the exact CF_TEXT bytes Response put
on the clipboard.
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from r2x.views import CONTROLS, STRAIN_KEY, VIEWS, View
from r2x.worker.images import bmp_to_png

# Response-2000 main-menu command IDs (RT_MENU resource of r2k.exe 1.9.7).
CMD_SECTIONAL_RESPONSE = 5092
CMD_MORE_DETAIL = 11845      # Solve > More Detail
VK_PRIOR, VK_NEXT, VK_DOWN, VK_RETURN, VK_ESCAPE = 0x21, 0x22, 0x28, 0x0D, 0x1B
IDOK, IDCANCEL = 1, 2

# Copy Chart Data's position in every data chart's context menu, after Copy Chart Picture.
COPY_CHART_DATA_DOWNS = 2


@dataclass(frozen=True)
class Chart:
    """A chart with a data export: where it sits in Response and the title its export carries."""
    key: str            # record section name (detail views) or position (control charts)
    title: str | None   # "Title :" line of the export; None: any title in CONTROL_KEYS
    grid: tuple | None  # (row, col) in the nine-chart grid, or None for a control chart
    control: int | None = None  # 0 = top control chart, 1 = bottom


def view_charts(view: View) -> tuple[Chart, ...]:
    """A detail view's charts with a data export (views.json), in grid order."""
    return tuple(Chart(c.key, c.title, c.grid) for c in view.charts)


# Longitudinal Strain is at the same place in every view r2x captures (tests/test_views.py); its
# export identifies the load stage on screen.
STRAIN = next(c for c in view_charts(VIEWS[0]) if c.key == STRAIN_KEY)


# Which control charts Response shows depends on the loading, so the two positions are copied
# and their titles say what they are.
CONTROL_CHARTS = (
    Chart("control_top", None, None, 0),
    Chart("control_bottom", None, None, 1),
)
# Control-chart titles r2x knows, and the record section each becomes (views.json). Which two
# Response shows depends on the increment (docs/cli.md): with shear in it, Shear-γxy on top and
# below it Moment-φ (with a moment), Axial Load-εx (with an axial load) or Shear-εx (shear
# alone); without, Moment-εx and Moment-φ, or Axial Load-εx in both places (axial alone).
CONTROL_KEYS = {c.title: c.key for c in CONTROLS}


class R2xError(RuntimeError):
    """The job failed (exit status 1)."""


class WaitTimeout(R2xError):
    """Response did not react in time: an input to it may have been lost, so retrying can help."""


class OutOfScope(R2xError):
    """The input asks for an analysis r2x does not cover (exit status 3). Reserved: since r2x
    0.3.0 nothing raises it."""


class Cpu:
    """Response's processor time, read from /proc on the Linux side of Wine.

    Under Wine there is no readable "solving" flag, but a solving Response keeps its process
    busy, and an idle one uses next to nothing.
    """

    def __init__(self, pid: int):
        self.stat = Path(f"/proc/{pid}/stat")

    def seconds(self) -> float | None:
        try:
            fields = self.stat.read_text().rsplit(")", 1)[1].split()
        except (OSError, IndexError):
            return None
        return (int(fields[11]) + int(fields[12])) / os.sysconf("SC_CLK_TCK")

    def share(self, window: float = 0.2) -> float | None:
        """The share of one processor Response used over the next `window` seconds, or None if
        its process cannot be read."""
        t0, s0 = time.monotonic(), self.seconds()
        time.sleep(window)
        t1, s1 = time.monotonic(), self.seconds()
        if s0 is None or s1 is None:
            return None
        return (s1 - s0) / (t1 - t0)


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

    def lines(self, command: str) -> list[str]:
        """A command that replies "ok N" and then N lines; the lines."""
        n = int(self.ask(command))
        return [self.proc.stdout.readline().decode("latin-1").rstrip("\r\n") for _ in range(n)]

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


def wine_path(p: Path) -> str:
    """A Linux path as programs in the Wine prefix see it (drive Z:)."""
    return "Z:" + str(Path(p).resolve()).replace("/", "\\")


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

    def __init__(self, helper: Helper, note: Callable[[str], None] = lambda s: None,
                 cpu: Cpu | None = None):
        self.h = helper
        self.note = note
        self.cpu = cpu
        self._charts: dict[str, str] | None = None   # chart key -> window, in the view on screen
        self._charts_view: View | None = None         # the view _charts was found in
        self._view_list: tuple[str, list[str]] | None = None  # drop-down window, its items
        self._data_menu_width: int | None = None

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
        """Map chart key -> window handle: the control charts, and the charts of the detail view
        on screen that have a data export (none if r2x does not capture that view)."""
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
        view = self.view()
        if view is not None:
            charts.update({c.key: at[c.grid] for c in view_charts(view)})
        self._charts, self._charts_view = charts, view
        return charts

    # -- detail views -------------------------------------------------------------------------
    def _views(self) -> tuple[str, list[str]]:
        """Response's view list (the drop-down above the control charts) and its items."""
        if self._view_list is None:
            boxes = [w for w in self.h.windows() if w.visible and w.cls == "ComboBox"]
            if len(boxes) != 1:
                raise R2xError(f"expected Response's view list, found {len(boxes)} drop-downs")
            items = [bytes.fromhex(x).decode("latin-1")
                     for x in self.h.lines(f"cbitems {boxes[0].hwnd}")]
            self._view_list = boxes[0].hwnd, items
        return self._view_list

    def view(self) -> View | None:
        """The detail view on screen, or None if it is not one r2x captures."""
        hwnd, items = self._views()
        i = int(self.h.ask(f"cbget {hwnd}"))
        label = items[i] if 0 <= i < len(items) else None
        return next((v for v in VIEWS if v.response == label), None)

    def select_view(self, view: View):
        """Show this detail view. The stage on screen stays as it is (export.py checks that)."""
        hwnd, items = self._views()
        if view.response not in items:
            raise R2xError(f"Response's view list has no {view.response!r} "
                           f"(it has {', '.join(items)})")
        i = items.index(view.response)
        if int(self.h.ask(f"cbget {hwnd}")) == i:
            return
        # The helper sends the change notification as the drop-down would, and the reply comes
        # once Response has put the view's charts in place.
        self.h.ask(f"cbselect {hwnd} {i}")
        if int(self.h.ask(f"cbget {hwnd}")) != i:
            raise R2xError(f"Response did not switch to the {view.response} view")
        self._charts = None

    # -- clipboard ----------------------------------------------------------------------------
    def copy_chart(self, chart: Chart, timeout: float = 5, attempts: int = 3) -> bytes:
        """Right-click the chart, choose Copy Chart Data, return the clipboard's CF_TEXT bytes.

        About one copy in several thousand gets no reply (seen once in about 6,500 under
        Wine 9.0; the menu keys seem to be lost). Such a copy is dismissed and tried again. A
        retry cannot pass off the wrong data: every export's title is checked, and the stage
        checks in export.py compare its contents with the control curve.
        """
        def copy():
            self._choose(chart, COPY_CHART_DATA_DOWNS, "chart data", timeout)
            reply = wait_until(lambda: self.h.try_ask("clip"), timeout,
                               f"clipboard text of {chart.key}", 0.01)
            return bytes.fromhex(reply)
        data = self._retrying(chart, "Copy Chart Data", copy, attempts)
        title = export_title(data)
        if chart.control is not None:
            if title in CONTROL_KEYS:
                return data
            raise R2xError(f"{chart.key}: unknown control chart {title!r}")
        if title != chart.title:
            raise R2xError(f"{chart.key}: export title {title!r}, expected {chart.title!r}")
        return data

    def snapshot(self, scratch: Path, settled: bool = False, interval: float = 0.15,
                 timeout: float = 5, window: str | None = None) -> bytes:
        """Response's main window, or another of its windows (a dialog), as it is on screen, as
        a PNG.

        settled: take it until two in a row are the same, so that a view Response is still
        drawing is not caught half-drawn.
        """
        bmp = Path(scratch) / "window.bmp"
        def snap() -> bytes:
            hwnd = window or self.main_window()[0]
            self.h.ask(f"snap {hwnd} {wine_path(bmp).encode().hex()}")
            try:
                return bmp.read_bytes()
            finally:
                bmp.unlink(missing_ok=True)
        shot = snap()
        t0 = time.monotonic()
        while settled:
            time.sleep(interval)
            again = snap()
            if again == shot:
                break
            if time.monotonic() - t0 > timeout:
                raise R2xError(f"Response's window did not settle within {timeout:.0f} s")
            shot = again
        return bmp_to_png(shot)

    def _retrying(self, chart: Chart, what: str, copy: Callable, attempts: int):
        for attempt in range(1, attempts + 1):
            try:
                return copy()
            except WaitTimeout as e:
                self._dismiss_popup()
                if attempt == attempts:
                    raise R2xError(f"{what} of {chart.key} failed {attempts} times: {e}")
                self.note(f"{what} of {chart.key} got no reply ({e}); trying again")

    def _choose(self, chart: Chart, downs: int, what: str, timeout: float):
        """Choose an item of the chart's context menu and wait until the clipboard changes."""
        charts = self._charts or self.find_charts()
        if chart.key not in charts:
            raise R2xError(f"{chart.key} is not in the {self._view_name()}")
        hwnd = charts[chart.key]
        self.h.ask("clipclear")
        seq = self.h.ask("clipseq")
        self.h.ask(f"rclick {hwnd}")
        wait_until(lambda: self.h.ask("popup") == "1", timeout, f"context menu of {chart.key}", 0.005)
        if downs == COPY_CHART_DATA_DOWNS:
            self._check_data_menu(chart)
        for _ in range(downs):
            self.h.ask(f"menukey {VK_DOWN:#x}")
        self.h.ask(f"menukey {VK_RETURN:#x}")
        wait_until(lambda: self.h.ask("clipseq") != seq, timeout, f"{what} of {chart.key}", 0.005)

    def _check_data_menu(self, chart: Chart):
        """Refuse to go on unless the open context menu is a data chart's.

        A chart that is only a picture (cross section, crack diagram, ...) has another menu, in
        which the second item toggles a drawing mode instead of copying data. Every data chart's
        menu is as wide as its Copy Chart Picture item makes it, whatever its length (the top
        control chart's has three items, the others six); picture menus are narrower. The width
        is taken from the first control chart copied (solve() copies them first): control
        charts are found by their window class and title, so they always have data.
        """
        left, _, right, _ = map(int, self.h.ask("popuprect").split())
        width = right - left
        if chart.control is not None:
            if self._data_menu_width is None:
                self._data_menu_width = width
            return
        if self._data_menu_width is not None and width != self._data_menu_width:
            self._dismiss_popup()
            where = f"row {chart.grid[0]}, column {chart.grid[1]}" if chart.grid else "its place"
            raise R2xError(f"{chart.key}: the chart at {where} of the {self._view_name()} has no "
                           f"Copy Chart Data (its menu is {width} pixels wide, a data chart's "
                           f"{self._data_menu_width})")

    def _view_name(self) -> str:
        view = self._charts_view
        return f"{view.response} view" if view else "view on screen"

    def _dismiss_popup(self, timeout: float = 2):
        """Close a context menu left open by a copy that got no reply."""
        t0 = time.monotonic()
        while self.h.ask("popup") == "1":
            if time.monotonic() - t0 > timeout:
                raise R2xError("a chart's context menu does not close")
            self.h.try_ask(f"menukey {VK_ESCAPE:#x}")
            time.sleep(0.1)

    # -- solving ------------------------------------------------------------------------------
    def solve(self, quiet: float = 1.0, timeout: float = 300,
              on_count: Callable[[int], None] = lambda n: None) -> tuple[bytes, bytes]:
        """Solve -> Sectional Response; return the final exports of the top and bottom control
        charts. on_count gets the number of stages solved so far, each time it grows.

        Under Wine there is no readable "finished" flag (the menu state lives in Response's
        process), so the solve counts as finished once the bottom control curve has not changed
        for `quiet` seconds and Response's process is idle (Cpu). Response adds points every
        0.05 to 0.5 s while solving.
        """
        self.h.ask(f"cmd {CMD_SECTIONAL_RESPONSE}")
        def charts_ready():
            try:
                return self.find_charts()
            except R2xError:
                self.check_no_dialog()
                return None
        wait_until(charts_ready, 60, "the solution view's charts", 0.05)
        # The top chart first: the first control chart copied sets the width a data chart's
        # context menu has (_check_data_menu).
        self.copy_chart(CONTROL_CHARTS[0])
        bottom = self._settle(None, quiet, timeout, on_count)
        return self.copy_chart(CONTROL_CHARTS[0]), bottom

    def more_detail(self, bottom: bytes, quiet: float = 1.0, timeout: float = 300,
                    on_count: Callable[[int], None] = lambda n: None) -> tuple[bytes, bytes] | None:
        """Solve -> More Detail once, after a solve whose bottom control chart exported
        `bottom`. Return the control charts' exports after it, or None if Response refined
        nothing (it stops adding stages at 327, and then the command does nothing visible).
        """
        self.check_no_dialog()
        self.h.ask(f"cmd {CMD_MORE_DETAIL}")
        after = self._settle(bottom, quiet, timeout, on_count)
        if after == bottom:
            return None
        return self.copy_chart(CONTROL_CHARTS[0]), after

    def _settle(self, last: bytes | None, quiet: float, timeout: float,
                on_count: Callable[[int], None]) -> bytes:
        """Copy the bottom control chart until it has not changed for `quiet` seconds, has a
        point, and Response is idle; return its export. Fails if Response adds no stage for
        `timeout` seconds without finishing."""
        since = time.monotonic()
        while True:
            self.check_no_dialog()
            data = self.copy_chart(CONTROL_CHARTS[1])
            now = time.monotonic()
            if data != last:
                last, since = data, now
                on_count(len(export_points(data)))
            elif now - since >= quiet and export_points(data) and self._idle():
                return data
            if time.monotonic() - since > timeout:
                raise R2xError(f"Response added no load stage for {timeout:.0f} s and did not "
                               "finish")
            time.sleep(0.05)

    def _idle(self, below: float = 0.1) -> bool:
        """Response's process used less than `below` of a processor over a short wait (True if
        its process cannot be read: the unchanged curve decides alone)."""
        if self.cpu is None:
            return True
        share = self.cpu.share()
        return share is None or share < below

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
