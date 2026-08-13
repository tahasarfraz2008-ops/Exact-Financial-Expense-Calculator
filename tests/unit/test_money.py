from decimal import Decimal

import pytest

from app.domain.entities.money import Money
from app.domain.exceptions.financial_exceptions import InvalidCurrencyError
from app.domain.services.currency_conversion_service import convert
from app.domain.value_objects.currency import Currency
from app.domain.value_objects.exact_number import ExactNumber
from app.domain.value_objects.rounding_policy import RoundingPolicy


def test_money_settle_rounds_to_currency_precision():
    money = Money.of(ExactNumber("100") / ExactNumber("3"), "USD")
    settlement = money.settle(RoundingPolicy.HALF_UP)
    assert settlement.rounded_value == Decimal("33.33")
    # the exact amount inside Money is untouched by settling
    assert str(money.amount) == "100/3"


def test_cannot_add_different_currencies():
    usd = Money.of("10", "USD")
    pkr = Money.of("10", "PKR")
    with pytest.raises(InvalidCurrencyError):
        usd + pkr


def test_unknown_currency_rejected():
    with pytest.raises(InvalidCurrencyError):
        Currency.of("ZZZ")


def test_jpy_has_zero_decimal_places():
    assert Currency.of("JPY").decimal_places == 0


def test_currency_conversion_keeps_full_precision_before_settlement():
    usd = Money.of("100", "USD")
    rate = ExactNumber("278.4563")
    result = convert(usd, "PKR", rate)
    assert result.converted_exact.amount == ExactNumber("278.4563") * ExactNumber(100)
    settlement = result.converted_exact.settle()
    assert settlement.decimal_places == 2
