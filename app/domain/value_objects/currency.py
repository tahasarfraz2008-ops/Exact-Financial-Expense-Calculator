"""
Currency -- a value object describing a monetary unit's business rules.

WHAT IS IT?
-----------
`Currency` is not just a three-letter code ("USD", "PKR"); it also
carries the *business rule* for how many decimal places that currency
settles in. USD and PKR settle in 2 decimal places (cents/paisa). Some
real-world currencies differ -- JPY has 0 decimal places, and some
crypto or commodity units use more -- so this must be a lookup, not a
hard-coded constant.

WHY DO WE NEED IT?
------------------
`ExactNumber` can represent `100/3` forever, but real money has to be
settled in a smallest legal unit (a cent, a paisa). That "smallest
unit" is a business rule that belongs to the currency, not to the
arithmetic engine, and not to any individual calculation. Keeping it
here means every part of the system that needs "how many decimals does
this currency use" asks the same authoritative source.

HOW DOES IT WORK?
------------------
A small registry of supported currencies is built in, each with its
ISO 4217 code and decimal-place count. `Currency.of("USD")` looks the
currency up; an unknown code raises `InvalidCurrencyError` rather than
silently defaulting to 2 decimal places (a wrong default is worse than
a loud failure for money).

WHY THIS TECHNOLOGY?
---------------------
A plain, frozen dataclass keyed by an explicit registry dict. No
third-party currency library is used because the requirement here is
narrow (decimal places + code), and the project explicitly avoids
unnecessary dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.exceptions.financial_exceptions import InvalidCurrencyError


@dataclass(frozen=True, slots=True)
class Currency:
    """An ISO-4217-style currency with its settlement decimal places."""

    code: str
    decimal_places: int
    name: str

    @staticmethod
    def of(code: str) -> "Currency":
        """Look up a supported currency by its ISO code (case-insensitive)."""
        normalized = code.strip().upper()
        currency = _CURRENCY_REGISTRY.get(normalized)
        if currency is None:
            raise InvalidCurrencyError(
                f"'{code}' is not a supported currency. "
                f"Supported: {', '.join(sorted(_CURRENCY_REGISTRY))}."
            )
        return currency

    @staticmethod
    def register(code: str, decimal_places: int, name: str) -> "Currency":
        """Register (or override) a currency at application start-up.

        Exists so infrastructure/config code can extend the supported
        currency set without editing this module.
        """
        currency = Currency(code=code.upper(), decimal_places=decimal_places, name=name)
        _CURRENCY_REGISTRY[currency.code] = currency
        return currency

    def __str__(self) -> str:
        return self.code


_CURRENCY_REGISTRY: dict[str, Currency] = {}

for _code, _places, _name in [
    ("USD", 2, "US Dollar"),
    ("PKR", 2, "Pakistani Rupee"),
    ("EUR", 2, "Euro"),
    ("GBP", 2, "British Pound Sterling"),
    ("JPY", 0, "Japanese Yen"),
    ("SAR", 2, "Saudi Riyal"),
    ("AED", 2, "UAE Dirham"),
    ("KWD", 3, "Kuwaiti Dinar"),
]:
    Currency.register(_code, _places, _name)
