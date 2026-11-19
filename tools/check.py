#!/usr/bin/env python3
"""Checks to run before pushing (and in CI): is the record of the work in order?

    python tools/check.py

1. CLAUDE.md and docs/status.md exist.
2. Every session log in docs/log has the sections docs/log/TEMPLATE.md asks for.

Exit status 0 when all pass, 1 when one fails.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_SECTIONS = ("## Goal", "## Done", "## Tried and dropped", "## Decisions",
                "## Open questions for the owner")


def main() -> int:
    bad = 0
    for rel in ("CLAUDE.md", "docs/status.md"):
        if not (ROOT / rel).exists():
            print(f"FAIL  {rel} missing")
            bad += 1
    logs = sorted((ROOT / "docs" / "log").glob("2*.md"))
    for p in logs:
        text = p.read_text(encoding="utf-8")
        missing = [s for s in LOG_SECTIONS if s not in text]
        if missing:
            print(f"FAIL  {p.relative_to(ROOT)}: missing {', '.join(missing)}")
            bad += 1
    if not bad:
        print(f"ok    CLAUDE.md, docs/status.md, {len(logs)} session log(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
