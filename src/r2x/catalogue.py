"""Response-2000's dialogs that r2x define drives: the catalogue in dialogs.json.

Each noun of `define` (quick, general, materials, ...) is one of Response's dialogs; its fields
are listed in the dialog's own order, with their control IDs, so the questions, the help, the
worker and the tests all read the same list. Standard library only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

KINDS = {"text", "number", "integer", "check", "choice", "shape", "radio", "bar", "first-line",
         "other-lines"}
LIST_ACTIONS = ("add", "modify", "delete")


class CatalogueError(ValueError):
    """A define command that names no dialog or action r2x knows."""


@dataclass(frozen=True)
class Option:
    id: int
    text: str


@dataclass(frozen=True)
class Field:
    key: str                     # r2x's name for the field
    kind: str                    # one of KINDS
    question: str                # the words r2x asks with when the dialog has no label for it
    id: int | None = None        # control ID (none for a radio group: see options)
    label: int | None = None     # control showing the field's label, read when asking
    prefix: str = ""             # put before a label read from the dialog ("Top, ")
    unit: int | None = None      # control showing the field's unit
    unless: int | None = None    # skip the field while this check box is ticked
    xml: str = ""                # where Response saves it, for reference
    options: tuple[Option, ...] = ()   # radio buttons


@dataclass(frozen=True)
class Page:
    title: str | None            # a wizard page's window title, or a sheet page's tab title
    fields: tuple[Field, ...]


@dataclass(frozen=True)
class ListControls:
    box: int                     # the list box of named items
    name: int                    # the Name edit box
    add: int
    modify: int
    delete: int


@dataclass(frozen=True)
class Dialog:
    noun: str                    # define NOUN
    menu: int                    # main-menu command that opens it
    kind: str                    # wizard, sheet, dialog or list
    title: str                   # window title
    summary: str                 # one line for the help
    pages: tuple[Page, ...]
    item: str = ""               # list dialogs: what an item is called (layer, stirrup type)
    list: ListControls | None = None

    @property
    def fields(self) -> tuple[Field, ...]:
        return tuple(f for p in self.pages for f in p.fields)


def _field(d: dict) -> Field:
    if d["kind"] not in KINDS:
        raise CatalogueError(f"field {d['key']}: unknown kind {d['kind']!r}")
    return Field(d["key"], d["kind"], d["question"], d.get("id"), d.get("label"),
                 d.get("prefix", ""), d.get("unit"), d.get("unless"), d.get("xml", ""),
                 tuple(Option(o["id"], o["text"]) for o in d.get("options", ())))


def _load() -> tuple[Dialog, ...]:
    data = json.loads(Path(__file__).with_name("dialogs.json").read_text(encoding="utf-8"))
    out = []
    for d in data["dialogs"]:
        pages = tuple(Page(p.get("title"), tuple(_field(f) for f in p["fields"]))
                      for p in d["pages"])
        lst = ListControls(**d["list"]) if "list" in d else None
        out.append(Dialog(d["noun"], d["menu"], d["kind"], d["title"], d["summary"], pages,
                          d.get("item", ""), lst))
    return tuple(out)


DIALOGS = _load()
BY_NOUN = {d.noun: d for d in DIALOGS}
NOUNS = tuple(BY_NOUN)


@dataclass(frozen=True)
class Step:
    """One define step: the dialog, and for a list dialog the action and the item's name."""
    dialog: Dialog
    action: str | None = None    # add, modify or delete (list dialogs)
    name: str | None = None      # the item's name (list dialogs), None: ask
    args: list[str] = field(default_factory=list)

    @property
    def noun(self) -> str:
        return self.dialog.noun

    def words(self) -> list[str]:
        """The step as the worker's command line takes it."""
        out = [self.noun]
        if self.action:
            out.append(self.action)
        if self.name is not None:
            out.append(self.name)
        return out


def parse_step(words: list[str]) -> Step:
    """define NOUN [ACTION [NAME]] -> Step. Raises CatalogueError."""
    if not words:
        raise CatalogueError(f"define what? One of: {', '.join(NOUNS)}")
    noun = words[0].lower()
    if noun not in BY_NOUN:
        raise CatalogueError(f"no dialog {words[0]!r} to define; one of: {', '.join(NOUNS)}")
    dialog = BY_NOUN[noun]
    rest = words[1:]
    if dialog.kind != "list":
        if rest:
            raise CatalogueError(f"define {noun} takes no more words (got {' '.join(rest)!r})")
        return Step(dialog)
    action = rest[0].lower() if rest else None
    if action is not None and action not in LIST_ACTIONS:
        raise CatalogueError(f"define {noun} {rest[0]!r}: use add, modify or delete, then the "
                             f"{dialog.item}'s name")
    if len(rest) > 2:
        raise CatalogueError(f"define {noun} {action} takes one name (got {' '.join(rest[1:])!r};"
                             " quote a name with spaces)")
    return Step(dialog, action, rest[1] if len(rest) == 2 else None)


def help_text(dialog: Dialog) -> str:
    """What define NOUN asks, in the dialog's order, for the help."""
    lines = [f"define {dialog.noun}"
             + (f" add|modify|delete [NAME]" if dialog.kind == "list" else "")
             + f"  —  {dialog.summary}"]
    if dialog.kind == "list":
        lines.append(f"  Asks for the {dialog.item}'s name if not given, then its fields;")
        lines.append(f"  delete asks nothing more. Names are as Response lists them.")
    for page in dialog.pages:
        if dialog.kind == "wizard" and page.title:
            lines.append(f"  {page.title}:")
        for f in page.fields:
            extra = "  (labels from the dialog)" if f.label else ""
            lines.append(f"    {f.question}{extra}")
    return "\n".join(lines)
