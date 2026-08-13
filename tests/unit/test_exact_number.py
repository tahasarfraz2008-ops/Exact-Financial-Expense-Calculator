import pytest

from app.domain.exceptions.financial_exceptions import (
    AccidentalFloatError,
    DivisionByZeroFinancialError,
    InvalidNumberError,
)
from app.domain.value_objects.exact_number import ExactNumber


def test_from_int():
    assert str(ExactNumber(100)) == "100"


def test_from_fraction_string():
    assert str(ExactNumber("1/3")) == "1/3"


def test_division_stays_exact():
    result = ExactNumber(100) / ExactNumber(3)
    assert str(result) == "100/3"


def test_division_then_multiplication_recovers_original():
    result = (ExactNumber(100) / ExactNumber(3)) * ExactNumber(3)
    assert result == ExactNumber(100)


def test_reduces_fraction():
    result = ExactNumber(10) / ExactNumber(6)
    assert str(result) == "5/3"


def test_rejects_raw_float_construction():
    with pytest.raises(AccidentalFloatError):
        ExactNumber(33.33)  # type: ignore[arg-type]


def test_rejects_float_in_arithmetic():
    value = ExactNumber(100)
    with pytest.raises(AccidentalFloatError):
        value * 3.0  # type: ignore[operator]


def test_division_by_zero_raises_domain_exception():
    with pytest.raises(DivisionByZeroFinancialError):
        ExactNumber(1) / ExactNumber(0)


def test_empty_string_is_invalid():
    with pytest.raises(InvalidNumberError):
        ExactNumber("")


def test_negative_numbers():
    assert str(-ExactNumber(5)) == "-5"
    assert str(ExactNumber(-5)) == "-5"


def test_large_numbers_stay_exact():
    huge = ExactNumber(10 ** 30) / ExactNumber(3)
    assert (huge * ExactNumber(3)) == ExactNumber(10 ** 30)


def test_small_fractions():
    tiny = ExactNumber(1) / ExactNumber(10 ** 12)
    assert tiny * ExactNumber(10 ** 12) == ExactNumber(1)


def test_is_terminating_decimal():
    assert ExactNumber("1/4").is_terminating_decimal() is True
    assert ExactNumber("1/3").is_terminating_decimal() is False


def test_equality_with_zero():
    assert ExactNumber(0) == ExactNumber("0/5")


def test_comparisons():
    assert ExactNumber(1) < ExactNumber(2)
    assert ExactNumber(2) >= ExactNumber(2)
