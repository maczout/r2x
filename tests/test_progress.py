import pytest

from r2x.progress import Event, note, parse

EVENTS = [
    Event("solving"),
    Event("solved", count=60, stage=56),
    Event("stage", stage=56, done=1, total=1),
    Event("wrote", text="/out/Liping LB1.r2x.txt", seconds=9.1),
    Event("solving", count=12),
    Event("solving", count=1),
    Event("refining", count=116, done=1),
    note("creating Wine prefix (first run only)"),
    Event("failed", "Response shows a dialog 'Invalid File': Not a valid file format"),
    Event("usage", "stage 80 is past the last stage, 59"),
    Event("out-of-scope", "an analysis r2x does not cover"),
]


@pytest.mark.parametrize("event", EVENTS, ids=lambda e: e.kind)
def test_round_trip(event):
    assert parse(event.line()) == event
    assert parse(event.line() + "\r\n") == event


def test_lines_are_readable():
    assert [e.line() for e in EVENTS[:4]] == [
        "r2x: solving",
        "r2x: solved: 60 stages, peak 56",
        "r2x: stage 56 (1/1)",
        "r2x: wrote /out/Liping LB1.r2x.txt in 9.1 s",
    ]
    assert [e.line() for e in EVENTS[4:7]] == [
        "r2x: solving: 12 stages", "r2x: solving: 1 stage", "r2x: more detail 1: 116 stages"]
    assert Event("failed", "two\nlines").line() == "r2x: failed: two lines"


@pytest.mark.parametrize("line", ["Traceback (most recent call last):", "r2x: something else",
                                  "r2x: stage x (1/2)", "", "wine: fixme"])
def test_other_lines_are_not_events(line):
    assert parse(line) is None
