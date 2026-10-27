"""The HTML report, the BMP-to-PNG conversion and the Symbol font fix (no Wine needed)."""
import html
import io
import struct
import zlib
from pathlib import Path

import pytest

from r2x import record, report
from r2x.views import ALL, BY_NAME, record_order
from r2x.worker.images import bmp_to_png
from r2x.worker.prefix import install_symbol_font, symbol_encoded

REFS = Path(__file__).parent / "reference"
HEADER = {"r2x-version": "0.1.0", "input-name": "Newbeam <1>.r2t", "units": "si",
          "factors": "0.65,0.85,0.90", "initial": "-2000.00,0.00,0.00",
          "increment": "0.00,1.00,0.00", "stage-count": "60", "peak-stage": "56",
          "detail-stages": "56"}


def reference_record(case, **header):
    root = REFS / case
    sections = []
    for p in sorted(root.rglob("*.txt")):
        parts = p.relative_to(root).parts
        name = f"control/{p.stem}" if parts[0] == "control" else f"stage/{int(parts[1])}/{p.stem}"
        sections.append((name, p.read_bytes()))
    stage = next((root / "stages").iterdir()).name
    h = dict(HEADER, **{"peak-stage": str(int(stage)), "detail-stages": str(int(stage))}, **header)
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


@pytest.mark.parametrize("text, expected", [
    ("|e_x Strain (mm/m)", "ε<sub>x</sub> Strain (mm/m)"),
    ("Control : Moment - |f", "Control : Moment - φ"),
    ("f_s_c_r_a_c_k (MPa)", "f<sub>scrack</sub> (MPa)"),
    ("Curvature (rad/10^3inch)", "Curvature (rad/10<sup>3</sup>inch)"),
    ("Shrinkage & Thermal Strain", "Shrinkage &amp; Thermal Strain"),
    ("a | b", "a | b"),
])
def test_markup(text, expected):
    assert report.markup(text) == expected


def test_parse_export():
    data = (REFS / "newbeam/stages/056/shrinkage_thermal_strain.txt").read_bytes()
    chart = report.parse_export(data)
    assert chart.title == "Shrinkage & Thermal Strain" and chart.y_title == "Beam Depth (mm)"
    assert [t for t, _ in chart.series] == ["0", "4"]
    from r2x.worker.session import export_points
    points = [pt for _, pts in chart.series for pt in pts]
    assert [pt for pt in points if pt] == [tuple(line.split()) for line in data.decode().splitlines()
                                          if len(line.split()) == 2 and "Line" not in line]
    assert len([pt for pt in points if pt]) == len(export_points(data))
    assert points.count(None) == data.count(b"New Line") > 0


NO_SHEAR = [c.key for c in BY_NAME["no-shear"].charts]


def test_report_has_every_picture_beside_its_data():
    """A record from r2x 0.1.0 (no views key): the No Shear view, as 0.1.0 captured it."""
    rec = reference_record("newbeam")
    keys = ["window/no-shear", "moment_ex", "moment_phi", *NO_SHEAR]
    page = report.build(rec, {k: PNG for k in keys})
    assert page.startswith("<!doctype html>") and page.endswith("</html>\n")
    assert page.count('<img src="data:image/png;base64,') == 8 and "No picture" not in page
    assert page.count('<article class="panel"') == 7
    for name, body in rec.sections.items():         # every export, verbatim in its panel
        assert html.escape(body.decode("latin-1")) in page, name
    assert "<h1>Newbeam &lt;1&gt;.r2t</h1>" in page
    assert "Peak stage 56 of 0–59" in page and "No Shear view at stage 56" in page
    assert "concrete 0.65 · steel 0.85 · prestress 0.90" in page
    assert "N -2000.00 kN · M 0.00 kN·m · V 0.00 kN" in page
    assert "<script" not in page and "http" not in page.replace("http-equiv", "")  # self-contained
    order = [page.index(f"<h3>{report.markup(report.parse_export(rec.sections[n]).title)}</h3>")
             for n in ("control/moment_ex", "control/moment_phi",
                       *(f"stage/56/{k}" for k in NO_SHEAR))]
    assert order == sorted(order)


def export_text(title: str) -> bytes:
    return (f"Data from Graph\r\nTitle : {title}\r\nX Axis Title : x\r\nY Axis Title : y\r\n"
            "Line type: 0\r\n1.0 2.0\r\n").encode("latin-1")


def test_report_of_every_view():
    """Each view: its window, then each chart not shown under an earlier view."""
    sections = [("control/moment_ex", (REFS / "newbeam/control/moment_ex.txt").read_bytes())]
    sections += [(f"stage/56/{c.key}", export_text(c.title)) for c in record_order(ALL)]
    rec = record.decode(record.encode(dict(HEADER, views="general,cracking,reinforcement,"
                                           "no-shear"), sections))
    pictures = {f"window/{v.name}": PNG for v in ALL}
    pictures.update({c.key: PNG for c in record_order(ALL)})
    page = report.build(rec, pictures)
    assert page.count('<article class="panel"') == 1 + 21
    assert page.count('<img src="data:image/png;base64,') == 4 + 21 and "No picture" in page
    heads = [page.index(f"<h2>{v.response} view at stage 56</h2>") for v in ALL]
    assert heads == sorted(heads)
    no_shear = page[heads[-1]:]
    assert no_shear.count('<article class="panel"') == 2       # the other three come earlier
    assert ('Also in this view: <a href="#chart-longitudinal_strain">Longitudinal Strain</a> '
            "(under General)") in no_shear
    assert '<a href="#view-reinforcement">Reinforcement view</a>' in page


def test_report_axial_only_and_us_units():
    page = report.build(reference_record("newbeam-axial-only"), {})
    assert page.count('<article class="panel"') == 6        # one control chart
    assert "Control : Axial Load - ε<sub>x</sub>" in page
    assert page.count("No picture") == 7
    page = report.build(reference_record("newbeam-us", units="us"), {})
    assert "US customary" in page and "M 1.00 kip·ft" in page
    assert "Curvature (rad/10<sup>3</sup>inch)" in page


def test_report_needs_the_peak_stage():
    rec = reference_record("newbeam")
    rec.header["peak-stage"] = "12"
    with pytest.raises(KeyError):
        report.build(rec, {})


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
