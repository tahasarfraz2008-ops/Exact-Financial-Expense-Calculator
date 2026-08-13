from decimal import Decimal

import pytest

from app.domain.exceptions.financial_exceptions import InvalidRoundingModeError
from app.domain.services.rounding_service import round_exact_number
from app.domain.value_objects.exact_number import ExactNumber
from app.domain.value_objects.rounding_policy import RoundingPolicy


def test_round_half_up():
    result = round_exact_number(ExactNumber("100") / ExactNumber("3"), 2, RoundingPolicy.HALF_UP)
    assert result.rounded_value == Decimal("33.33")


def test_round_preserves_original_exact_value():
    exact = ExactNumber("100") / ExactNumber("3")
    result = round_exact_number(exact, 2, RoundingPolicy.HALF_UP)
    assert result.original_exact_value == exact
    assert str(result.original_exact_value) == "100/3"


def test_round_records_difference():
    exact = ExactNumber("100") / ExactNumber("3")
    result = round_exact_number(exact, 2, RoundingPolicy.HALF_UP)
    # 33.33 - 100/3 should be negative (rounding down removed value)
    assert result.difference < ExactNumber(0)


def test_round_half_even_vs_half_up():
    half = ExactNumber("5") / ExactNumber("2")  # 2.5
    half_up = round_exact_number(half, 0, RoundingPolicy.HALF_UP)
    half_even = round_exact_number(half, 0, RoundingPolicy.HALF_EVEN)
    assert half_up.rounded_value == Decimal("3")
    assert half_even.rounded_value == Decimal("2")


def test_round_down_and_up():
    value = ExactNumber("10") / ExactNumber("3")  # 3.333...
    down = round_exact_number(value, 2, RoundingPolicy.DOWN)
    up = round_exact_number(value, 2, RoundingPolicy.UP)
    assert down.rounded_value == Decimal("3.33")
    assert up.rounded_value == Decimal("3.34")


def test_round_floor_and_ceiling_negative():
    value = -(ExactNumber("10") / ExactNumber("3"))
    floor = round_exact_number(value, 2, RoundingPolicy.FLOOR)
    ceiling = round_exact_number(value, 2, RoundingPolicy.CEILING)
    assert floor.rounded_value == Decimal("-3.34")
    assert ceiling.rounded_value == Decimal("-3.33")


def test_invalid_rounding_mode_name():
    with pytest.raises(InvalidRoundingModeError):
        RoundingPolicy.from_name("NOT_A_MODE")


def test_negative_decimal_places_rejected():
    with pytest.raises(ValueError):
        round_exact_number(ExactNumber(1), -1, RoundingPolicy.HALF_UP)
