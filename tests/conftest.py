"""Every test runs with a linked Response-2000 and a settings file of its own.

The command line needs a linked program folder (r2x setup). With $R2X_RESPONSE_DIR (the Wine
tests' Response folder) that folder is linked, as a user would link theirs; without it, a stand-in
folder whose r2k.exe is not a real build, allowed as `r2x setup --allow-unverified` allows it.
"""
import os

import pytest


@pytest.fixture(scope="session")
def stand_in_response(tmp_path_factory):
    folder = tmp_path_factory.mktemp("Response")
    (folder / "r2k.exe").write_bytes(b"not Response-2000")
    (folder / "rebar.dat").write_bytes(b"bars\r\n")
    return folder


@pytest.fixture(autouse=True)
def linked_response(tmp_path, monkeypatch, stand_in_response):
    monkeypatch.setenv("R2X_CONFIG", str(tmp_path / "r2x-config.json"))
    real = os.environ.get("R2X_RESPONSE_DIR")
    if real:
        monkeypatch.setenv("R2X_RESPONSE", real)
        monkeypatch.delenv("R2X_ALLOW_UNVERIFIED", raising=False)
    else:
        monkeypatch.setenv("R2X_RESPONSE", str(stand_in_response))
        monkeypatch.setenv("R2X_ALLOW_UNVERIFIED", "1")
