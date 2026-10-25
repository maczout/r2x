import pytest

from r2x.settings import Settings, format_number, format_pair, parse_pair


@pytest.mark.parametrize("text, pair", [("-2000,0", (-2000.0, 0.0)), ("0,1", (0.0, 1.0)),
                                        (" 1.5 , -2e3 ", (1.5, -2000.0))])
def test_parse_pair(text, pair):
    assert parse_pair(text) == pair


@pytest.mark.parametrize("text", ["5", "1,2,3", "a,b", "", "nan,0", "inf,1"])
def test_parse_pair_errors(text):
    with pytest.raises(ValueError):
        parse_pair(text)


@pytest.mark.parametrize("x, text", [(-2000.0, "-2000"), (0.0, "0"), (-0.0, "0"), (1.0, "1"),
                                     (0.738, "0.738"), (1e-5, "0.00001"), (123456.5, "123456.5")])
def test_format_number(x, text):
    assert format_number(x) == text


def test_settings_checks():
    assert format_pair((-2000.0, 0.0)) == "-2000,0"
    with pytest.raises(ValueError, match="0,0"):
        Settings(increment=(0.0, 0.0))
    with pytest.raises(ValueError, match="units"):
        Settings(units="imperial")
    with pytest.raises(ValueError, match="factors"):
        Settings(factors="aci")
