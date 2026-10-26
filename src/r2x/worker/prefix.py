"""The Wine prefix Response runs in: created once, then checked before every job.

    python -m r2x.worker.prefix      creates or updates $R2X_WINEPREFIX (the image does this once)

Two things are set up beyond Wine's defaults:

- Windows are unmanaged. Xvfb has no window manager, and Wine would otherwise wait 2 s for one
  each time a dialog closes. The exports are unchanged.
- A copy of Wine's Symbol font that Response can use. Response writes the Greek letters in its
  chart titles (εx, φ) as Latin letters in the Symbol font, which Windows maps to U+F020-U+F0FF.
  Wine's own symbol.ttf has the right glyphs ('e' is epsilon) but maps them only at
  U+0020-U+00FF, so Wine draws boxes. The copy, r2x-symbol.ttf, adds the symbol-encoded map and
  a higher font revision, so Wine prefers it. Only the pictures change, not the data. Making it
  needs fontTools; without it, or without Wine's fonts, the Greek letters stay boxes.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

from r2x.progress import Event, note

X11_DRIVER_KEY = r"HKCU\Software\Wine\X11 Driver"
_UNMANAGED = re.compile(r'\[Software\\\\Wine\\\\X11 Driver\][^\[]*"Managed"="N"')

SYMBOL_FONT = "r2x-symbol.ttf"
WINE_FONT_DIRS = ("/usr/share/wine/fonts", "/usr/lib/wine/fonts", "/opt/wine-stable/share/wine/fonts")


def default_prefix() -> Path:
    return Path(os.environ.get("R2X_WINEPREFIX", Path.home() / ".cache/r2x/prefix"))


def prepare_prefix(prefix: Path, env: dict, on_event: Callable[[Event], None]):
    """Create the Wine prefix if needed; make windows unmanaged; install the Symbol font."""
    if not (prefix / "system.reg").exists():
        on_event(note("creating Wine prefix (first run only)"))
        subprocess.run(["wineboot", "-i"], env=env, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    user_reg = prefix / "user.reg"
    if not (user_reg.exists() and _UNMANAGED.search(user_reg.read_text(errors="replace"))):
        subprocess.run(["wine", "reg", "add", X11_DRIVER_KEY, "/v", "Managed", "/d", "N", "/f"],
                       env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    fonts = prefix / "drive_c" / "windows" / "Fonts"
    if not (fonts / SYMBOL_FONT).exists():
        problem = install_symbol_font(fonts)
        if problem:
            on_event(note(f"Greek letters in chart pictures will show as boxes: {problem}"))


def install_symbol_font(fonts: Path, sources=WINE_FONT_DIRS) -> str | None:
    """Write r2x-symbol.ttf into the prefix's Fonts folder; return why not, if it cannot."""
    source = next((Path(d) / "symbol.ttf" for d in sources if (Path(d) / "symbol.ttf").is_file()),
                  None)
    if source is None:
        return "Wine's symbol.ttf was not found (is fonts-wine installed?)"
    try:
        data = symbol_encoded(source.read_bytes())
    except ImportError:
        return "fontTools is not installed"
    fonts.mkdir(parents=True, exist_ok=True)
    tmp = fonts / f".{SYMBOL_FONT}.{os.getpid()}.tmp"
    tmp.write_bytes(data)
    os.replace(tmp, fonts / SYMBOL_FONT)
    return None


def symbol_encoded(ttf: bytes) -> bytes:
    """The font with a Windows symbol cmap (platform 3, encoding 0) at U+F020-U+F0FF, mapping
    each code to the glyph the font has at code - 0xF000, and its revision raised by one."""
    import io

    from fontTools.ttLib import TTFont
    from fontTools.ttLib.tables._c_m_a_p import CmapSubtable

    font = TTFont(io.BytesIO(ttf))
    latin = font.getBestCmap()
    symbol = CmapSubtable.newSubtable(4)
    symbol.platformID, symbol.platEncID, symbol.language = 3, 0, 0
    symbol.cmap = {0xF000 + code: glyph for code, glyph in latin.items() if 0x20 <= code <= 0xFF}
    tables = font["cmap"].tables
    tables[:] = [t for t in tables if (t.platformID, t.platEncID) != (3, 0)] + [symbol]
    font["head"].fontRevision = font["head"].fontRevision + 1.0
    out = io.BytesIO()
    font.save(out)
    return out.getvalue()


def main() -> int:
    prefix = default_prefix()
    env = dict(os.environ, WINEPREFIX=str(prefix), WINEARCH="win32", WINEDEBUG="-all")
    prepare_prefix(prefix, env, lambda e: print(e.line(), file=sys.stderr, flush=True))
    subprocess.run(["wineserver", "-w"], env=env, check=True)
    print(f"Wine prefix ready: {prefix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
