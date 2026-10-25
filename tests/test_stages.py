import pytest

from r2x.stages import ALL, PEAK, StageError, StageSpec, format_ranges, parse_stages


@pytest.mark.parametrize("text, spec", [
    ("peak", PEAK),
    ("all", ALL),
    ("PEAK", PEAK),
    ("0", StageSpec(numbers=frozenset({0}))),
    ("0,10,20-22", StageSpec(numbers=frozenset({0, 10, 20, 21, 22}))),
    ("peak,0-2", StageSpec(peak=True, numbers=frozenset({0, 1, 2}))),
    (" peak , 3 ", StageSpec(peak=True, numbers=frozenset({3}))),
    ("5-5,056", StageSpec(numbers=frozenset({5, 56}))),
    ("all,peak,3", ALL),
])
def test_parse(text, spec):
    assert parse_stages(text) == spec


@pytest.mark.parametrize("text, message", [
    ("", "empty item"),
    ("1,,2", "empty item"),
    ("3,", "empty item"),
    ("-3", "'-3'"),
    ("30-20", "runs backwards"),
    ("x", "'x'"),
    ("1.5", "'1.5'"),
    ("1-2-3", "'1-2-3'"),
    ("100000", "out of range"),
    ("0-100000", "out of range"),
])
def test_parse_errors(text, message):
    with pytest.raises(StageError, match=message):
        parse_stages(text)


@pytest.mark.parametrize("text", ["peak", "all", "0-5,56", "peak,3,7-9", "12"])
def test_canonical_form_round_trips(text):
    assert str(parse_stages(text)) == text
    assert parse_stages(str(parse_stages(text))) == parse_stages(text)


def test_resolve():
    assert PEAK.resolve(60, 56) == [56]
    assert ALL.resolve(3, 1) == [0, 1, 2]
    assert parse_stages("peak,0-2").resolve(60, 56) == [0, 1, 2, 56]
    assert parse_stages("56,peak").resolve(60, 56) == [56]
    assert parse_stages("59").resolve(60, 56) == [59]


def test_resolve_past_last_stage():
    with pytest.raises(StageError, match="stage 60 is past the last stage, 59"):
        parse_stages("60").resolve(60, 56)
    with pytest.raises(StageError, match="stages 58-61 are past the last stage, 57"):
        parse_stages("0,58-61").resolve(58, 30)


def test_format_ranges():
    assert format_ranges([]) == ""
    assert format_ranges([5]) == "5"
    assert format_ranges([7, 0, 1, 2, 5, 8, 2]) == "0-2,5,7-8"
