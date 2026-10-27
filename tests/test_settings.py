import pytest

from r2x.settings import (MORE_DETAIL_MAX, Settings, format_loads, format_number, parse_loads,
                          parse_more_detail)


@pytest.mark.parametrize("text, loads", [("-2000,0,0", (-2000.0, 0.0, 0.0)),
                                         ("0,1,1", (0.0, 1.0, 1.0)),
                                         ("0,0,0", (0.0, 0.0, 0.0)),
                                         (" 1.5 , -2e3 ,4", (1.5, -2000.0, 4.0))])
def test_parse_loads(text, loads):
    assert parse_loads(text) == loads


@pytest.mark.parametrize("text", ["5", "1,2,3,4", "a,b,c", "", "nan,0,0", "inf,1,0", "1,,2"])
def test_parse_loads_errors(text):
    with pytest.raises(ValueError, match="expected"):
        parse_loads(text)


def test_two_values_say_to_add_v():
    """Loads were N,M before r2x 0.3.0; two values are an error that says to add V."""
    with pytest.raises(ValueError, match=r"add V, e\.g\. -2000,0,0"):
        parse_loads("-2000,0")


@pytest.mark.parametrize("x, text", [(-2000.0, "-2000"), (0.0, "0"), (-0.0, "0"), (1.0, "1"),
                                     (0.738, "0.738"), (1e-5, "0.00001"), (123456.5, "123456.5")])
def test_format_number(x, text):
    assert format_number(x) == text


def test_settings_checks():
    assert format_loads((-2000.0, 0.0, 12.5)) == "-2000,0,12.5"
    assert Settings(increment=(0.0, 0.0, 0.0)).increment == (0, 0, 0)     # allowed
    with pytest.raises(ValueError, match="N,M,V"):
        Settings(increment=(0.0, 1.0))
    with pytest.raises(ValueError, match="units"):
        Settings(units="imperial")
    with pytest.raises(ValueError, match="factors"):
        Settings(factors="aci")


@pytest.mark.parametrize("text, value", [("0", 0), ("3", 3), (" 12 ", 12), ("max", MORE_DETAIL_MAX),
                                         ("MAX", MORE_DETAIL_MAX)])
def test_parse_more_detail(text, value):
    assert parse_more_detail(text) == value


@pytest.mark.parametrize("text", ["-1", "two", "", "1.5", "all"])
def test_parse_more_detail_errors(text):
    with pytest.raises(ValueError, match="whole number of presses"):
        parse_more_detail(text)
