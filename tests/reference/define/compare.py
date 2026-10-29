"""Compare a define case's two files, or their records (check.ps1 and the Wine tests use it).

    py compare.py sections hand.r2t r2x.r2t     same section: the same elements and values,
                                                with the date and the longitudinal layers'
                                                order left out
    py compare.py records hand.r2x.txt r2x.r2x.txt   the same exports, section by section

Exit status 0 when they are the same, 1 when not; one line says which.

The layers' order is left out because Response keeps a section's layers in the order it made
them until it opens the file again, when it sorts them by depth (docs/define.md, Findings): two
files that differ only there are the same section once Response has read either. This compares
the saved text as a test does; r2x itself never reads a section's XML.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

DATE = re.compile(r'date(\s*)="\d{4}/\d{2}/\d{2}"')
LAYER = re.compile(r"\t\t<longreinfx\b.*?/>\r?\n", re.S)


def section_key(path: Path) -> tuple[str, list[str]]:
    """The file without its date, with its layers taken out and sorted."""
    text = DATE.sub(r'date\1="-"', path.read_bytes().decode("latin-1"))
    layers = sorted(LAYER.findall(text))
    return LAYER.sub("", text), layers


def same_sections(a: Path, b: Path) -> bool:
    return section_key(a) == section_key(b)


def same_records(a: Path, b: Path) -> bool:
    from r2x import record
    return record.read(a).sections == record.read(b).sections


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[0] not in ("sections", "records"):
        print(__doc__.split("\n\n")[1])
        return 2
    kind, a, b = argv[0], Path(argv[1]), Path(argv[2])
    same = (same_sections if kind == "sections" else same_records)(a, b)
    what = ("the same section (date and layer order aside)" if kind == "sections"
            else "the same record")
    print(f"{a.name} and {b.name}: {what}" if same else f"{a.name} and {b.name}: not {what}")
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
