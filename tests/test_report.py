"""The HTML report, the BMP-to-PNG conversion and the Symbol font fix (no Wine needed)."""
import io
import struct
import zlib
from pathlib import Path

import pytest

from r2x import record, report
from r2x.views import ALL, BY_NAME
from r2x.worker.images import bmp_to_png
from r2x.worker.prefix import install_symbol_font, symbol_encoded

REFS = Path(__file__).parent / "reference"
HEADER = {"r2x-version": "0.1.0", "input-name": "Newbeam <1>.r2t", "units": "si",
          "factors": "0.65,0.85,0.90", "initial": "-2000.00,0.00,0.00",
          "increment": "0.00,1.00,0.00", "stage-count": "60", "peak-stage": "56",
          "detail-stages": "56"}


def reference_record(case, **header):
    """A record as r2x 0.1.0 wrote it (no views key: the No Shear charts) from a case's
    captures at its peak, the highest stage captured."""
    root = REFS / case
    stage = max(int(d.name) for d in (root / "stages").iterdir())
    sections = [(f"control/{p.stem}", p.read_bytes())
                for p in sorted((root / "control").glob("*.txt"))]
    sections += [(f"stage/{stage}/{c.key}",
                  (root / f"stages/{stage:03d}/{c.key}.txt").read_bytes())
                 for c in BY_NAME["no-shear"].charts]
    h = dict(HEADER, **{"peak-stage": str(stage), "detail-stages": str(stage)}, **header)
    return record.decode(record.encode(h, sections))


def bmp(width, height, pixels):
    """A bottom-up 24-bit BMP; pixels[row][col] = (r, g, b), row 0 at the top."""
    stride = (width * 3 + 3) & ~3
    body = b""
    for row in reversed(pixels):
        line = b"".join(bytes((b, g, r)) for r, g, b in row)
        body += line + b"\0" * (stride - len(line))
    info = struct.pack("<IiiHHIIiiII", 40, width, height, 1, 24, 0, len(body), 0, 0, 0, 0)
    return b"BM" + struct.pack("<IHHI", 14 + 40 + len(body), 0, 0, 54) + info + body


def png_pixels(png):
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    pos, chunks = 8, {}
    while pos < len(png):
        n, kind = struct.unpack_from(">I4s", png, pos)
        data = png[pos + 8:pos + 8 + n]
        assert zlib.crc32(kind + data) & 0xFFFFFFFF == struct.unpack_from(">I", png, pos + 8 + n)[0]
        chunks[kind] = chunks.get(kind, b"") + data
        pos += 12 + n
    w, h = struct.unpack_from(">II", chunks[b"IHDR"])
    raw = zlib.decompress(chunks[b"IDAT"])
    rows = []
    for r in range(h):
        line = raw[r * (1 + 3 * w):(r + 1) * (1 + 3 * w)]
        assert line[0] == 0
        rows.append([tuple(line[1 + 3 * c:4 + 3 * c]) for c in range(w)])
    return rows


def test_bmp_to_png():
    pixels = [[(255, 0, 0), (0, 255, 0), (0, 0, 255)], [(1, 2, 3), (250, 251, 252), (0, 0, 0)]]
    assert png_pixels(bmp_to_png(bmp(3, 2, pixels))) == pixels
    with pytest.raises(ValueError):
        bmp_to_png(b"PK not a bitmap")


PNG = bmp_to_png(bmp(1, 1, [[(255, 255, 255)]]))


def build(header=None, pictures=None, views=None):
    """A report for Newbeam's reference record: its control charts, with views as given."""
    rec = reference_record("newbeam", **({"views": views} if views else {}), **(header or {}))
    return report.build(rec, PICTURES if pictures is None else pictures)


INPUTS = ["input/screen", "input/preferences", "input/loading"]
PICTURES = {k: PNG for k in INPUTS + [f"window/{v.name}" for v in ALL]}


def test_report_is_screenshots_under_inputs_and_outputs():
    page = build(views="general,cracking,reinforcement,no-shear")
    assert page.startswith("<!doctype html>") and page.endswith("</html>\n")
    assert page.count('<img src="data:image/png;base64,') == 3 + 4 and "No picture" not in page
    assert "<h1>Newbeam &lt;1&gt;.r2t</h1>" in page and "Peak stage 56 of 0–59." in page
    heads = [page.index(h) for h in ("<h2>Inputs</h2>", "<h3>Input screen</h3>",
                                     "<h3>Units and material factors</h3>", "<h3>Loads</h3>",
                                     "<h2>Outputs at stage 56</h2>", "<h3>General view</h3>",
                                     "<h3>Cracking view</h3>", "<h3>Reinforcement view</h3>",
                                     "<h3>No Shear view</h3>")]
    assert heads == sorted(heads)
    # no data: no tables, no export text, no record header, no chart pictures
    assert "<table" not in page and "Data from Graph" not in page and "<pre" not in page
    assert "input-sha256" not in page
    assert "<script" not in page and "http" not in page.replace("http-equiv", "")  # self-contained


def test_report_has_a_left_column_index():
    page = build(views="general,no-shear")
    nav = page[page.index('<nav class="index"'):page.index("</nav>")]
    links = [a.split('"')[0] for a in nav.split('href="#')[1:]]
    assert links == ["inputs", "in-screen", "in-preferences", "in-loading",
                     "outputs", "out-general", "out-no-shear"]
    for anchor in links:
        assert f'id="{anchor}"' in page
    assert "out-cracking" not in page                      # only the views the record has


def test_missing_pictures_and_old_records():
    page = build(pictures={"window/no-shear": PNG})         # a record from r2x 0.1.0: No Shear
    assert page.count('<img src="data:image/png;base64,') == 1
    assert page.count("No picture") == 3 and "<h3>No Shear view</h3>" in page
    assert "<h3>General view</h3>" not in page


def test_report_says_when_more_detail_refined_the_solve():
    assert "after More Detail" not in build()
    assert "Peak stage 56 of 0–59 after More Detail twice." in build({"more-detail": "2"})
    assert "after More Detail once." in build({"more-detail": "1"})


# -- the Symbol font ------------------------------------------------------------------------------
WINE_SYMBOL = Path("/usr/share/wine/fonts/symbol.ttf")


def test_symbol_font_without_wine_fonts(tmp_path):
    assert "symbol.ttf was not found" in install_symbol_font(tmp_path, sources=[tmp_path / "x"])
    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(not WINE_SYMBOL.is_file(), reason="needs Wine's fonts (fonts-wine)")
def test_symbol_font_maps_the_symbol_range(tmp_path):
    TTFont = pytest.importorskip("fontTools.ttLib").TTFont
    original = TTFont(WINE_SYMBOL)
    assert 0xF065 not in original.getBestCmap()
    assert install_symbol_font(tmp_path / "Fonts", sources=[WINE_SYMBOL.parent]) is None
    patched = TTFont(tmp_path / "Fonts" / "r2x-symbol.ttf")
    symbol = patched["cmap"].getcmap(3, 0).cmap
    latin = original.getBestCmap()
    assert symbol[0xF065] == latin[0x65] == "epsilon" and symbol[0xF066] == "phi"
    assert symbol == {0xF000 + c: g for c, g in latin.items() if 0x20 <= c <= 0xFF}
    assert patched["head"].fontRevision == original["head"].fontRevision + 1
    assert patched["cmap"].getcmap(3, 1).cmap == original["cmap"].getcmap(3, 1).cmap
    # applying it twice keeps one symbol map
    twice = TTFont(io.BytesIO(symbol_encoded((tmp_path / "Fonts/r2x-symbol.ttf").read_bytes())))
    assert sum((t.platformID, t.platEncID) == (3, 0) for t in twice["cmap"].tables) == 1
