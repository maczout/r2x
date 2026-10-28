"""Questions between the define worker and the command line.

A define step runs in the container, where Response's dialog is open; the person answering is at
the command line. The worker writes one JSON object per line on stdout and, after a question,
reads one JSON line of answer on stdin:

    {"ask": {...Question...}}          a question; the answer follows on stdin
    {"say": "text"}                    something to show: a message from Response, a note
    {"set": [[label, value], ...]}     what the step set, read back from the dialog
    {"show": [[label, value], ...]}    a dialog's values (show)
    {"done": {...}}                    the step's outcome (saved file, title)

    stdin: {"answer": "text"}  or  {"answer": null}  (Enter: keep the value the dialog has)

End of input on stdin means the person gave up: the worker stops without saving. Progress and
errors still go to stderr in the form of r2x.progress. Standard library only.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from typing import IO

YES, NO = "y", "n"


@dataclass
class Question:
    key: str                         # the field's key (dialogs.json), or a key of r2x's own
    text: str                        # the question, in the dialog's words
    kind: str                        # text number integer check choice shape radio bar yesno
    value: str = ""                  # what the dialog holds now (Enter keeps it)
    unit: str = ""
    choices: list[str] = field(default_factory=list)
    keep: bool = True                # whether Enter keeps the value (False: an answer is needed)
    hint: str = ""                   # shown on ?: the dialog's example, the choices' source

    def prompt(self) -> str:
        unit = f" ({self.unit})" if self.unit else ""
        shown = self.value
        if self.kind in ("check", "yesno") and self.keep:
            shown = YES if self.value == YES else NO
        default = f" [{shown}]" if self.keep else ""
        return f"  {self.text}{unit}{default}: "


class AnswerError(ValueError):
    """An answer that is not of the question's kind; the question is asked again."""


def check_answer(q: Question, text: str) -> str | None:
    """The answer to send for what was typed: None keeps the value; raises AnswerError.

    r2x checks only the form: a number is a number, a choice is one of the choices. Response
    checks the values themselves.
    """
    text = text.strip()
    if text == "":
        if not q.keep:
            raise AnswerError("an answer is needed")
        return None
    if q.kind in ("number", "integer"):
        try:
            x = float(text)
        except ValueError:
            raise AnswerError(f"{text!r} is not a number") from None
        if math.isnan(x) or math.isinf(x):
            raise AnswerError(f"{text!r} is not a number")
        if q.kind == "integer" and x != int(x):
            raise AnswerError(f"{text!r} is not a whole number")
        return text
    if q.kind in ("check", "yesno"):
        t = text.lower()
        if t in ("y", "yes"):
            return YES
        if t in ("n", "no"):
            return NO
        raise AnswerError("answer y or n")
    if q.kind in ("choice", "shape", "radio"):
        return pick(q.choices, text)
    try:
        text.encode("latin-1")
    except UnicodeEncodeError:
        raise AnswerError("Response takes only Western European letters (Latin-1)") from None
    return text


def pick(choices: list[str], text: str) -> str:
    """A choice by its number (1, 2, ...), its text, or the start of a word in it, if only one
    choice matches."""
    t = text.strip().lower()
    if t.isdigit() and 1 <= int(t) <= len(choices):
        return choices[int(t) - 1]
    exact = [c for c in choices if c.lower() == t]
    if exact:
        return exact[0]
    starts = [c for c in choices if c.lower().startswith(t)]
    if len(starts) == 1:
        return starts[0]
    words = [c for c in choices if any(w.startswith(t) for w in c.lower().split())]
    if len(words) == 1:
        return words[0]
    if not starts and not words:
        raise AnswerError(f"{text!r} is none of the choices")
    raise AnswerError(f"{text!r} could be {' or '.join(starts or words)}")


def format_choices(choices: list[str], width: int = 76) -> list[str]:
    """The choices numbered, wrapped into lines of at most width."""
    lines, cur = [], ""
    for i, c in enumerate(choices, 1):
        item = f"{i}) {c}"
        if cur and len(cur) + 2 + len(item) > width:
            lines.append(cur)
            cur = item
        else:
            cur = f"{cur}  {item}" if cur else item
    return lines + ([cur] if cur else [])


# -- the wire -----------------------------------------------------------------------------------
def write(stream: IO[str], **message):
    stream.write(json.dumps(message, ensure_ascii=False) + "\n")
    stream.flush()


def question_message(q: Question) -> dict:
    return {"ask": asdict(q)}


def read_question(data: dict) -> Question:
    return Question(**data)


def read_line(line: str) -> dict:
    data = json.loads(line)
    if not isinstance(data, dict) or len(data) != 1:
        raise ValueError(f"not a define message: {line[:80]!r}")
    return data
