"""The raw record: everything one solve exported, in one text file. Layout: docs/raw-format.md.

Read records as bytes. Section bodies are Response's clipboard text, byte for byte, and their
lengths count bytes, so reading in text mode (which rewrites line endings) breaks them.
Standard library only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

FORMAT = "r2x-raw"
VERSION = 1
EOL = b"\r\n"

_KEY = re.compile(r"[a-z][a-z0-9-]*")
_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]*")
_SECTION = re.compile(rb"section (\S+) (0|[1-9][0-9]*)")


class RecordError(ValueError):
    """Not a raw record, a newer format version, or damaged (e.g. line endings rewritten)."""


@dataclass
class Record:
    version: int
    header: dict[str, str] = field(default_factory=dict)
    sections: dict[str, bytes] = field(default_factory=dict)

    def control(self, key: str) -> bytes:
        return self.sections[control_section(key)]

    def stage(self, stage: int, key: str) -> bytes:
        return self.sections[stage_section(stage, key)]

    def stages(self) -> list[int]:
        """Stage numbers that have detail-view sections, ascending."""
        return sorted({int(name.split("/")[1]) for name in self.sections
                       if name.startswith("stage/")})


def control_section(key: str) -> str:
    return f"control/{key}"


def stage_section(stage: int, key: str) -> str:
    return f"stage/{stage}/{key}"


# -- writing ------------------------------------------------------------------------------------
def encode(header: dict[str, str], sections: Iterable[tuple[str, bytes]]) -> bytes:
    out = [f"{FORMAT} {VERSION}".encode() + EOL]
    for key, value in header.items():
        value = str(value)
        if not _KEY.fullmatch(key):
            raise RecordError(f"bad header key {key!r}")
        if "\r" in value or "\n" in value:
            raise RecordError(f"header {key}: value has a line break")
        out.append(f"{key}: {value}".encode("utf-8") + EOL)
    out.append(EOL)
    seen = set()
    for name, body in sections:
        if not _NAME.fullmatch(name):
            raise RecordError(f"bad section name {name!r}")
        if name in seen:
            raise RecordError(f"section {name} appears twice")
        seen.add(name)
        out += [f"section {name} {len(body)}".encode() + EOL, bytes(body), EOL]
    out.append(b"end" + EOL)
    return b"".join(out)


# -- reading ------------------------------------------------------------------------------------
def decode(data: bytes) -> Record:
    pos = 0

    def line() -> bytes:
        nonlocal pos
        end = data.find(EOL, pos)
        if end < 0:
            raise RecordError(f"byte {pos}: line has no CRLF ending (truncated, or line endings "
                              "rewritten?)")
        text, pos = data[pos:end], end + len(EOL)
        return text

    first = line()
    fmt, _, version = first.partition(b" ")
    if fmt != FORMAT.encode() or not version.isdigit():
        raise RecordError(f"not an r2x raw record (first line {first[:40]!r})")
    record = Record(int(version))
    if record.version > VERSION:
        raise RecordError(f"record format version {record.version} is newer than this reader "
                          f"({VERSION}); update r2x")

    while True:
        at = pos
        text = line()
        if not text:
            break
        key, sep, value = text.decode("utf-8").partition(": ")
        if not sep or not _KEY.fullmatch(key):
            raise RecordError(f"byte {at}: bad header line {text[:60]!r}")
        if key in record.header:
            raise RecordError(f"byte {at}: header {key} appears twice")
        record.header[key] = value

    while True:
        at = pos
        text = line()
        if text == b"end":
            break
        m = _SECTION.fullmatch(text)
        if not m:
            raise RecordError(f"byte {at}: expected a section line or 'end', found {text[:60]!r}")
        name, size = m.group(1).decode(), int(m.group(2))
        body = data[pos:pos + size]
        if len(body) != size or data[pos + size:pos + size + len(EOL)] != EOL:
            raise RecordError(f"byte {at}: section {name} is not {size} bytes followed by CRLF "
                              "(truncated, or line endings rewritten?)")
        if name in record.sections:
            raise RecordError(f"byte {at}: section {name} appears twice")
        record.sections[name] = body
        pos += size + len(EOL)
    if pos != len(data):
        raise RecordError(f"byte {pos}: {len(data) - pos} bytes after 'end'")
    return record


def read(path: str | Path) -> Record:
    return decode(Path(path).read_bytes())
