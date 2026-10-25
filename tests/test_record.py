"""The raw record format (docs/raw-format.md), without Wine."""
from pathlib import Path

import pytest

from r2x import record
from r2x.record import RecordError

REF = Path(__file__).parent / "reference" / "newbeam"

HEADER = {"r2x-version": "0.0.1", "input-name": "Bé am.r2t", "stage-count": "60",
          "peak-stage": "56", "detail-stages": "56"}


def sections():
    return [("control/moment_ex", (REF / "control/moment_ex.txt").read_bytes()),
            ("control/moment_phi", (REF / "control/moment_phi.txt").read_bytes()),
            ("stage/56/longitudinal_strain",
             (REF / "stages/056/longitudinal_strain.txt").read_bytes()),
            ("stage/56/empty", b""),
            ("stage/56/no_final_newline", b"a\r\nb")]


def test_round_trip_is_byte_for_byte():
    data = record.encode(HEADER, sections())
    rec = record.decode(data)
    assert rec.version == record.VERSION
    assert rec.header == HEADER
    assert list(rec.sections.items()) == sections()
    assert rec.control("moment_phi") == (REF / "control/moment_phi.txt").read_bytes()
    assert rec.stage(56, "no_final_newline") == b"a\r\nb"
    assert rec.stages() == [56]


def test_layout():
    data = record.encode({"a": "1"}, [("x", b"AB\r\n")])
    assert data == b"r2x-raw 1\r\na: 1\r\n\r\nsection x 4\r\nAB\r\n\r\nend\r\n"
    assert record.decode(record.encode({}, [])).sections == {}


def test_read_file(tmp_path):
    p = tmp_path / "x.r2x.txt"
    p.write_bytes(record.encode(HEADER, sections()))
    assert record.read(p).header["input-name"] == "Bé am.r2t"


def test_rewritten_line_endings_are_caught():
    data = record.encode(HEADER, sections())
    with pytest.raises(RecordError):
        record.decode(data.replace(b"\r\n", b"\n"))
    lf_bodies = data.replace(b"\r\n   ", b"\n   ")   # data rows only; framing intact
    with pytest.raises(RecordError, match="not .* bytes followed by CRLF"):
        record.decode(lf_bodies)


def test_truncated_or_padded():
    data = record.encode(HEADER, sections())
    for cut in (len(data) - 3, len(data) // 2, 40):
        with pytest.raises(RecordError):
            record.decode(data[:cut])
    with pytest.raises(RecordError, match="after 'end'"):
        record.decode(data + b"x")


def test_newer_version_refused():
    data = record.encode({}, []).replace(b"r2x-raw 1", b"r2x-raw 2")
    with pytest.raises(RecordError, match="newer than this reader"):
        record.decode(data)
    with pytest.raises(RecordError, match="not an r2x raw record"):
        record.decode(b"  Data from Graph\r\n")


def test_unknown_keys_and_sections_are_kept():
    rec = record.decode(record.encode({"future-key": "v"}, [("future/section", b"z")]))
    assert rec.header["future-key"] == "v" and rec.sections["future/section"] == b"z"


@pytest.mark.parametrize("header, secs", [
    ({"Bad": "x"}, []),
    ({"a b": "x"}, []),
    ({"key": "two\r\nlines"}, []),
    ({}, [("has space", b"")]),
    ({}, [("x", b""), ("x", b"")]),
])
def test_encode_rejects(header, secs):
    with pytest.raises(RecordError):
        record.encode(header, secs)


def test_decode_rejects_duplicates():
    with pytest.raises(RecordError, match="appears twice"):
        record.decode(b"r2x-raw 1\r\na: 1\r\na: 2\r\n\r\nend\r\n")
    with pytest.raises(RecordError, match="appears twice"):
        record.decode(b"r2x-raw 1\r\n\r\nsection x 0\r\n\r\nsection x 0\r\n\r\nend\r\n")
