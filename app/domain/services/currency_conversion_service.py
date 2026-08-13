"""
Currency conversion service.

WHAT IS IT?
-----------
`convert(money, target_currency, exchange_rate)` converts a `Money`
value from one currency to another using an exact exchange rate,
returning the *unrounded* converted amount plus, separately, the
settled (currency-precision) amount.

WHY DO WE NEED IT?
------------------
Section 8 asks the engine to "demonstrate how exchange-rate
calculations can preserve precision before final currency rounding."
An exchange rate itself is rarely a clean 2-decimal number (e.g.
1 USD = 278.4563 PKR), and multiplying by it should not be rounded
until the very end -- otherwise successive conversions (USD -> EUR ->
GBP -> USD) would accumulate rounding error that would not exist if
each conversion carried its full precision forward.

HOW DOES IT WORK?
------------------
The exchange rate is itself an `ExactNumber` (never a float). The
unrounded amount is `money.amount * rate`, kept exact. Only when the
caller explicitly asks for a settlable amount (`.settle()` on the
resulting `Money`) does actual currency-precision rounding occur --
identical pattern to every other monetary operation in this engine.

WHY THIS TECHNOLOGY?
---------------------
No third-party FX library is used because this project does not source
live exchange rates -- it only needs to apply an already-known rate
exactly. Introducing a live-rates dependency would be out of scope for
an arithmetic engine and is left to a separate infrastructure concern.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.money import Money
from app.domain.value_objects.currency import Currency
from app.domain.value_objects.exact_number import ExactNumber


@dataclass(frozen=True, slots=True)
class ConversionResult:
    original: Money
    exchange_rate: ExactNumber
    converted_exact: Money  # full precision, not yet settled


def convert(money: Money, target_currency: "Currency | str", exchange_rate: ExactNumber) -> ConversionResult:
    """Convert `money` into `target_currency` using `exchange_rate`
    (units of target currency per one unit of source currency), keeping
    full precision. Call `.settle()` on `converted_exact` to obtain a
    real, payable amount in the target currency.
    """
    resolved_currency = (
        target_currency if isinstance(target_currency, Currency) else Currency.of(target_currency)
    )
    converted_amount = money.amount * exchange_rate
    converted_money = Money(amount=converted_amount, currency=resolved_currency)
    return ConversionResult(
        original=money,
        exchange_rate=exchange_rate,
        converted_exact=converted_money,
    )
