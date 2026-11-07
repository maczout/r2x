"""The user's own Response-2000 program folder, which r2x links rather than bundles.

The command line checks the folder at `r2x setup` and before every run; the worker checks it
again inside the container, which mounts it read-only at /opt/response. Only the files
Response reads are hashed and copied into each job (PROGRAM_SUFFIXES): Response.ini (its list
of recent files, rewritten by every session on Windows) and the sections people keep beside the
program are left out, so using Response on Windows does not change what r2x runs.
Standard library only.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

EXE = "r2k.exe"

# Builds of r2k.exe that r2x's exports have been checked against on Windows (docs: what has
# been verified). Response's splash screen says 1.9.6 (beta), Help > About 1.9.7.
VERIFIED_EXE = {
    "bbf4bc595ee80167ea73a76d597b2223cbc5e9c47d97d452025cde4bb85e4e74": "1.9.7",
}

# The verified program folder's files, for naming what differs in a user's folder. Different
# rebar.dat or shape.dat (Response's bar and shape lists) are allowed: people edit them.
VERIFIED_FILES = {
    "api-ms-win-crt-runtime-l1-1-0.dll":
        "d16db68b4020287bb6ce701b71312a9d887874c0d26b9ebd82c3c9b965029562",
    "msvcp140.dll": "c09b126e7d4c1e6efb3ffcda2358252ce37383572c78e56ca97497a7f7c793e4",
    "owl-6.42-v14-x86-t.dll": "68d2a83e20ddfbbe4d0f2a025f2fce8d9d54ce7342f9baad411b25b64f5d3668",
    "r2k.exe": "bbf4bc595ee80167ea73a76d597b2223cbc5e9c47d97d452025cde4bb85e4e74",
    "r3g.dtd": "6ae556eb32162a8a35e2e4ba2dacf3e493c329f3991fbf567bd6f51c5e2dd3d7",
    "rebar.dat": "5cd5ed9af99327855f02e22a9eb6aa8e702317aefa0a9623a168d5a501539aaa",
    "shape.dat": "138299df3a72e1f3975d64b6965c4970ee2c1db1d40a757a2641817dace5393b",
    "vcruntime140.dll": "b7c13f8519340257ba6ae3129afce961f137e394dde3e4e41971b9f912355f5e",
}

# The files Response reads: the program and its libraries, the bar and shape lists, the XML
# format's DTD and, if there is one, r2k.r2k (the template for a new section).
PROGRAM_SUFFIXES = (".exe", ".dll", ".dat", ".dtd", ".r2k")

# Set to 1 by `r2x setup --allow-unverified` (or by hand) to run another build of r2k.exe.
ALLOW_ENV = "R2X_ALLOW_UNVERIFIED"


class ResponseError(Exception):
    """No usable Response-2000 program folder."""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def program_files(folder: Path) -> list[Path]:
    """The files in folder that Response reads, by name (case ignored)."""
    return sorted((p for p in Path(folder).iterdir()
                   if p.is_file() and p.suffix.lower() in PROGRAM_SUFFIXES),
                  key=lambda p: p.name.lower())


def files_sha256(hashes: dict[str, str]) -> str:
    """One hash for the program files: SHA-256 of the lines `HASH  name` (as sha256sum prints
    them), sorted by name with case ignored, each ending in a line feed."""
    lines = "".join(f"{hashes[n]}  {n}\n" for n in sorted(hashes, key=str.lower))
    return hashlib.sha256(lines.encode("utf-8")).hexdigest()


@dataclass
class Program:
    folder: Path
    hashes: dict[str, str]          # file name -> SHA-256, for the files Response reads

    @property
    def exe_sha256(self) -> str:
        return self.hashes[EXE]

    @property
    def verified(self) -> bool:
        return self.exe_sha256 in VERIFIED_EXE

    @property
    def files_sha256(self) -> str:
        return files_sha256(self.hashes)

    def differences(self) -> list[str]:
        """Files that are not the verified folder's: changed, added or missing."""
        changed = [n for n, h in self.hashes.items() if VERIFIED_FILES.get(n) != h]
        missing = [n for n in VERIFIED_FILES if n not in self.hashes]
        return sorted(changed, key=str.lower) + [f"{n} (missing)" for n in missing]

    def describe(self) -> str:
        """One line for r2x health and setup."""
        if self.verified:
            what = f"r2k.exe verified (Response {VERIFIED_EXE[self.exe_sha256]})"
        else:
            what = f"r2k.exe NOT verified (SHA-256 {self.exe_sha256[:16]}...)"
        diff = self.differences()
        others = [d for d in diff if not d.startswith(EXE)]
        if others:
            what += "; differs from the verified folder: " + ", ".join(others)
        return what


def read_program(folder: Path | str) -> Program:
    """Check that folder is a Response-2000 program folder and hash the files it reads."""
    folder = Path(folder)
    if not folder.is_dir():
        raise ResponseError(f"no folder {folder}")
    if not (folder / EXE).is_file():
        # Windows file names ignore case; the folder may hold R2K.EXE.
        if not any(p.name.lower() == EXE for p in folder.iterdir()):
            raise ResponseError(f"{folder} has no {EXE}: give Response-2000's program folder")
    hashes = {p.name.lower() if p.name.lower() == EXE else p.name: sha256(p)
              for p in program_files(folder)}
    return Program(folder, hashes)


def unverified_message(program: Program) -> str:
    return (f"{program.folder / EXE} is not a build of Response-2000 that r2x has been checked "
            f"against (SHA-256 {program.exe_sha256}). r2x setup --response FOLDER "
            f"--allow-unverified runs it anyway, and every record says so.")
