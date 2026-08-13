import pytest

from app.domain.exceptions.financial_exceptions import InvalidExpressionError
from app.domain.services.expression_evaluator import evaluate_expression
from app.domain.value_objects.exact_number import ExactNumber


def test_simple_division():
    assert str(evaluate_expression("100 / 3")) == "100/3"


def test_operator_precedence_multiplication_over_addition():
    assert evaluate_expression("2 + 3 * 4") == ExactNumber(14)


def test_parentheses_override_precedence():
    assert evaluate_expression("(2 + 3) * 4") == ExactNumber(20)


def test_nested_expression():
    assert evaluate_expression("((1 + 2) * (3 + 4))") == ExactNumber(21)


def test_division_then_multiplication_is_exact():
    assert evaluate_expression("100 / 3 * 3") == ExactNumber(100)
    assert evaluate_expression("(100 / 3) * 3") == ExactNumber(100)


def test_unary_minus():
    assert evaluate_expression("-5 + 3") == ExactNumber(-2)


def test_empty_expression_rejected():
    with pytest.raises(InvalidExpressionError):
        evaluate_expression("")


def test_unbalanced_parentheses_rejected():
    with pytest.raises(InvalidExpressionError):
        evaluate_expression("(1 + 2")


def test_unknown_character_rejected():
    with pytest.raises(InvalidExpressionError):
        evaluate_expression("1 + a")


def test_malformed_number_rejected():
    with pytest.raises(InvalidExpressionError):
        evaluate_expression("1..2 + 3")


def test_no_eval_no_code_execution():
    # A classic eval() payload must be rejected as an invalid expression,
    # not executed.
    with pytest.raises(InvalidExpressionError):
        evaluate_expression("__import__('os')")
