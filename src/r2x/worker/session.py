"""Drive one running Response-2000 instance through the in-Wine helper.

Everything here is mechanics: which window to right-click, when the clipboard has changed, which
load stage is on screen. Exported text is passed through as the exact CF_TEXT bytes Response put
on the clipboard.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass

# Response-2000 main-menu command IDs (RT_MENU resource of r2k.exe 1.9.7).
CMD_SECTIONAL_RESPONSE = 5092
VK_PRIOR, VK_NEXT, VK_DOWN, VK_RETURN = 0x21, 0x22, 0x28, 0x0D

# Position of "Copy Chart Data" in every chart's context menu (after "Copy Chart Picture").
COPY_CHART_DATA_DOWNS = 2


@dataclass(frozen=True)
class Chart:
    """A chart with a data export: where it sits in Response and the title its export carries."""
    key: str            # output file stem
    title: str          # "Title :" line of the export
    grid: tuple | None  # (row, col) in the nine-graph view, or None for a control chart
    control: int | None = None  # 0 = top control chart, 1 = bottom


CONTROL_CHARTS = (
    Chart("moment_ex", "Control : Moment - |e_x", None, 0),
    Chart("moment_phi", "Control : Moment - |f", None, 1),
)
NO_SHEAR_CHARTS = (
    Chart("longitudinal_strain", "Longitudinal Strain", (1, 2)),
    Chart("shrinkage_thermal_strain", "Shrinkage & Thermal Strain", (1, 3)),
    Chart("long_reinforcement_stress", "Long. Reinforcement Stress", (2, 2)),
    Chart("long_reinf_stress_at_crack", "Long. Reinf Stress at Crack", (2, 3)),
    Chart("longitudinal_concrete_stress", "Longitudinal Concrete Stress", (3, 1)),
)


class R2xError(RuntimeError):
    pass


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
            raise R2xError(f"timed out after {timeout:.0f} s waiting for {what}")
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


def strain_curvature(data: bytes) -> float:
    """Curvature (mrad/m) of the displayed stage, from the Longitudinal Strain export.

    The export is a closed outline: (0, y_top), (e_top, y_top), ..., (e_bot, y_bot), (0, y_bot),
    strains in mm/m and depths in mm.
    """
    pts = export_points(data)
    if len(pts) < 4:
        raise R2xError("Longitudinal Strain export has too few points")
    (e_top, y_top), (e_bot, y_bot) = pts[1], pts[-2]
    return (e_bot - e_top) / (y_top - y_bot) * 1000.0


class Session:
    """A solved or solvable Response-2000 window, reached through a Helper."""

    def __init__(self, helper: Helper):
        self.h = helper
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
            box = boxes[0]
            texts = [w.text for w in self.h.windows(f"kids {box.hwnd}")
                     if w.cls == "Static" and w.text.strip()]
            raise R2xError(f"Response shows a dialog {box.text!r}: {' / '.join(texts)}")

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
    def copy_chart(self, chart: Chart, timeout: float = 5) -> bytes:
        """Right-click the chart, choose Copy Chart Data, return the clipboard's CF_TEXT bytes."""
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
        data = bytes.fromhex(reply)
        title = export_title(data)
        if title != chart.title:
            raise R2xError(f"{chart.key}: export title {title!r}, expected {chart.title!r}")
        return data

    # -- solving ------------------------------------------------------------------------------
    def solve(self, quiet: float = 1.0, timeout: float = 300) -> tuple[bytes, bytes]:
        """Solve -> Sectional Response; return the final control curve exports.

        Under Wine there is no readable "finished" flag (the menu state lives in Response's
        process), so the solve counts as finished when the Moment-phi curve has not changed for
        `quiet` seconds. Response adds points about every 0.2 s while solving.
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
        moment_ex = self.copy_chart(CONTROL_CHARTS[0])
        return moment_ex, last

    # -- load stages --------------------------------------------------------------------------
    def press(self, vk: int, times: int = 1):
        hwnd = self.main_window()[0]
        for _ in range(times):
            self.h.ask(f"key {hwnd} {vk:#x}")
