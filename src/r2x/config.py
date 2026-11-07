"""The command line's settings file: which Response-2000 program folder r2x is linked to.

`r2x setup --response FOLDER` writes it once. It lives in %APPDATA%\\r2x\\config.json on Windows
and ~/.config/r2x/config.json elsewhere ($R2X_CONFIG names another file). $R2X_RESPONSE, if set,
names the folder instead, and $R2X_ALLOW_UNVERIFIED=1 allows another build of r2k.exe, as
--allow-unverified does. Standard library only.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from r2x.response import ALLOW_ENV


def config_path() -> Path:
    if os.environ.get("R2X_CONFIG"):
        return Path(os.environ["R2X_CONFIG"])
    if os.name == "nt" and os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"]) / "r2x" / "config.json"
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "r2x" / "config.json"


def load() -> dict:
    path = config_path()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as e:
        raise ValueError(f"cannot read {path}: {e}")


def save(settings: dict) -> Path:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


@dataclass
class Link:
    folder: Path | None         # None: not linked
    allow_unverified: bool
    source: str                 # where the folder came from, for messages


def link() -> Link:
    """The linked Response folder: $R2X_RESPONSE, else the settings file."""
    settings = load()
    allow = os.environ.get(ALLOW_ENV) == "1" or bool(settings.get("allow_unverified"))
    if os.environ.get("R2X_RESPONSE"):
        return Link(Path(os.environ["R2X_RESPONSE"]), allow, "$R2X_RESPONSE")
    if settings.get("response"):
        return Link(Path(settings["response"]), allow, str(config_path()))
    return Link(None, allow, "")
