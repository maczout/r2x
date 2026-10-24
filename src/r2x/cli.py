"""Command-line entry point. Commands are declared here; none are implemented yet."""

from __future__ import annotations

import argparse
import sys

from r2x import __version__


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="r2x", description="Run Response-2000 from the command line.")
    p.add_argument("--version", action="version", version=f"r2x {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    solve = sub.add_parser("solve", help="solve .r2t files and export their data")
    solve.add_argument("inputs", nargs="+", help="one or more .r2t files, or a glob")
    solve.add_argument("--out", help="output directory (default: next to each input)")

    sub.add_parser("health", help="show server, Wine and Response-2000 versions")

    config = sub.add_parser("config", help="get or set client settings")
    config_sub = config.add_subparsers(dest="action", required=True)
    config_set = config_sub.add_parser("set")
    config_set.add_argument("key", choices=["server", "token"])
    config_set.add_argument("value")

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(f"r2x {args.command}: not implemented yet", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
