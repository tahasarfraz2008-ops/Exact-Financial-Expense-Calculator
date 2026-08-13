"""
These are the minimum tests explicitly required by the specification
(Section 19), plus regression tests specifically designed to catch any
accidental conversion to `float` anywhere in the engine.
"""

from fractions import Fraction

import pytest

from app.domain.exceptions.financial_exceptions import AccidentalFloatError
from app.domain.services.expression_evaluator import evaluate_expression
from app.domain.value_objects.exact_number import ExactNumber


def test_100_div_3_equals_fraction_100_over_3():
    assert evaluate_expression("100 / 3") == ExactNumber("100/3")


def test_100_div_3_times_3_equals_100():
    assert evaluate_expression("(100 / 3) * 3") == ExactNumber(100)
    assert evaluate_expression("100 / 3 * 3") == ExactNumber(100)


def test_one_third_three_times_equals_one():
    assert evaluate_expression("1/3 + 1/3 + 1/3") == ExactNumber(1)


def test_10_div_6_equals_5_over_3():
    assert evaluate_expression("10 / 6") == ExactNumber("5/3")


def test_1000_div_7_times_7_equals_1000():
    assert evaluate_expression("1000 / 7 * 7") == ExactNumber(1000)


def test_100_div_3_three_times_summed_equals_100():
    assert evaluate_expression("100 / 3 + 100 / 3 + 100 / 3") == ExactNumber(100)


# --- additional required coverage: 0, negatives, large/small, zero div, ---
# --- repeating/terminating decimals, nested expressions, precedence -----

def test_zero():
    assert evaluate_expression("0 * 5") == ExactNumber(0)


def test_negative_numbers():
    assert evaluate_expression("-10 / 4") == ExactNumber("-5/2")


def test_large_numbers():
    assert evaluate_expression("1000000000000 / 3 * 3") == ExactNumber(1000000000000)


def test_small_fraction():
    assert evaluate_expression("1 / 1000000000000") == ExactNumber(1) / ExactNumber(1000000000000)


def test_division_by_zero_is_a_domain_error():
    from app.domain.exceptions.financial_exceptions import DivisionByZeroFinancialError

    with pytest.raises(DivisionByZeroFinancialError):
        evaluate_expression("1 / 0")


def test_repeating_decimal_1_over_7():
    result = evaluate_expression("1 / 7")
    assert result == ExactNumber("1/7")
    assert not result.is_terminating_decimal()


def test_terminating_decimal_1_over_8():
    result = evaluate_expression("1 / 8")
    assert result.is_terminating_decimal()


def test_nested_expression_and_precedence():
    assert evaluate_expression("(100 / 3 + 1) * 3 - 1") == ExactNumber(102)


# --- float-conversion regression guards ----------------------------------

def test_exact_number_never_backed_by_python_float():
    result = evaluate_expression("100 / 3")
    assert isinstance(result.as_fraction(), Fraction)
    assert not isinstance(result.value, float)


def test_constructing_exact_number_from_float_is_rejected():
    with pytest.raises(AccidentalFloatError):
        ExactNumber(33.33)  # type: ignore[arg-type]


def test_arithmetic_with_float_operand_is_rejected():
    value = ExactNumber(1)
    with pytest.raises(AccidentalFloatError):
        value + 1.5  # type: ignore[operator]
