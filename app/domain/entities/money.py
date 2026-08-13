"""
Money -- a currency-bound monetary amount.

WHAT IS IT?
-----------
`Money` pairs an exact value with a `Currency`. Unlike `ExactNumber`
(which is a pure mathematical rational number with no notion of "2
decimal places" or "which currency"), `Money` always knows what unit it
is denominated in and what that currency's settlement precision is.

WHY DO WE NEED IT?
------------------
Section 6 of the specification asks for a clear separation between
*exact mathematical values* (`100/3`) and *monetary values*
(`100.00 USD`). Blindly using `Fraction` for every banking operation
would mean the system never actually decides how many decimal places a
real payment settles in -- and blindly using `Decimal` for every
internal calculation would reintroduce the precision-loss problem this
whole project exists to avoid. `Money` is where those two worlds meet:
it is built from an `ExactNumber` (so *how* it was calculated can stay
lossless right up until this point) but it is always currency-aware.

HOW DOES IT WORK?
------------------
Internally `Money` keeps its `ExactNumber` amount, which may or may not
already be an exact multiple of the currency's smallest unit. Two
`Money` instances can only be combined (added/subtracted) if they share
a `Currency` -- otherwise `InvalidCurrencyError` is raised, because
"1 USD + 1 PKR" is not a valid mathematical operation until an explicit
exchange-rate conversion happens (see `CurrencyConversionService`).
`Money.settle()` produces the actual rounded, currency-precision
amount that would be transferred/booked, via the rounding service --
never implicitly.

WHY THIS TECHNOLOGY?
---------------------
A frozen dataclass composed of an `ExactNumber` and a `Currency`,
following the same "value object" pattern as the rest of the domain
layer -- consistent, immutable, and easy to reason about.

WHAT GOES WRONG IF IMPLEMENTED INCORRECTLY?
---------------------------------------------
If `Money` allowed two different currencies to be added directly, an
application bug could silently add "5 USD" and "500 PKR" as if they
were the same unit, producing a nonsensical balance. Requiring an
explicit conversion step is what makes that class of bug structurally
impossible.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.exceptions.financial_exceptions import InvalidCurrencyError
from app.domain.services.rounding_service import RoundingResult, round_exact_number
from app.domain.value_objects.currency import Currency
from app.domain.value_objects.exact_number import ExactNumber
from app.domain.value_objects.rounding_policy import RoundingPolicy


@dataclass(frozen=True, slots=True)
class Money:
    """A currency-bound amount, internally backed by an exact value."""

    amount: ExactNumber
    currency: Currency

    @staticmethod
    def of(amount: "ExactNumber | int | str | Decimal", currency: "Currency | str") -> "Money":
        """Convenience constructor: `Money.of("100.00", "USD")`."""
        resolved_currency = currency if isinstance(currency, Currency) else Currency.of(currency)
        resolved_amount = amount if isinstance(amount, ExactNumber) else ExactNumber(amount)
        return Money(amount=resolved_amount, currency=resolved_currency)

    def _require_same_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise InvalidCurrencyError(
                f"Cannot combine {self.currency.code} with {other.currency.code} "
                "directly -- convert one of them first via an explicit "
                "currency-conversion step."
            )

    def __add__(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def multiply(self, factor: ExactNumber) -> "Money":
        """Scale this Money by an exact, unitless factor (e.g. a rate)."""
        return Money(self.amount * factor, self.currency)

    def divide(self, divisor: ExactNumber) -> "Money":
        """Divide this Money by an exact, unitless divisor."""
        return Money(self.amount / divisor, self.currency)

    def settle(self, policy: RoundingPolicy = RoundingPolicy.HALF_UP) -> RoundingResult:
        """Produce the actual, currency-precision settlement amount.

        This is the explicit, auditable boundary between "exact
        calculation" and "money that could actually be transferred" --
        see Section 25 of the specification. The exact amount stored in
        this Money object is never mutated by calling this method.
        """
        return round_exact_number(self.amount, self.currency.decimal_places, policy)

    def __str__(self) -> str:
        settlement = self.settle()
        return f"{settlement.rounded_value} {self.currency.code}"
