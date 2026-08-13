"""
ExactNumber -- the core exact/rational value object.

WHAT IS IT?
-----------
`ExactNumber` wraps Python's `fractions.Fraction` so that every value
inside the engine is an exact rational number: a numerator over a
denominator, both arbitrary-precision integers. `100 / 3` is stored as
the pair (100, 3) -- never as a rounded decimal, and never as a binary
float.

WHY DO WE NEED IT?
------------------
Binary floats (Python's `float`, IEEE-754 double precision) cannot
represent most decimal fractions exactly, and repeated arithmetic on
them accumulates rounding error. Rounding a value like `100 / 3` to
`33.33` *before* the calculation is finished throws away information
permanently -- there is no way to recover `100` from `33.33 * 3`.
`Fraction` has no such problem: it is exact by construction, and stays
exact through any number of +, -, *, / operations, because a fraction
of integers, combined with another fraction of integers, is always
representable as a fraction of integers.

HOW DOES IT WORK?
------------------
Every `ExactNumber` holds a `Fraction`. Arithmetic operators delegate
directly to `Fraction`'s own arithmetic, which always returns an
automatically-reduced fraction (so `10/6` really is stored as `5/3`,
not `10/6`). Conversion to a *display* string is a completely separate,
explicit step (see `app.domain.services.decimal_display`) -- it never
mutates or replaces the underlying exact value.

WHY THIS TECHNOLOGY?
---------------------
`fractions.Fraction` is in the Python standard library, is
arbitrary-precision (backed by Python's arbitrary-precision `int`), is
well-tested, and directly models "a numerator over a denominator" --
exactly what we need. Reaching for a third-party arbitrary-precision
math library (e.g. `sympy`, `mpmath`) would add a large dependency for
capability the standard library already provides for this domain.

WHAT GOES WRONG IF THIS IS IMPLEMENTED INCORRECTLY?
-----------------------------------------------------
If `ExactNumber` were backed by `float` instead of `Fraction`, then
`ExactNumber("100") / ExactNumber("3") * ExactNumber("3")` would produce
`99.99999999999999` instead of exactly `100`, and every downstream
calculation (interest, balances, settlements) could silently drift.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from numbers import Rational
from typing import Union

from app.domain.exceptions.financial_exceptions import (
    AccidentalFloatError,
    DivisionByZeroFinancialError,
    InvalidNumberError,
)

# What is legally allowed to construct an ExactNumber. `float` is
# deliberately excluded -- see `_reject_float` below.
_AllowedInput = Union[int, str, Fraction, Decimal, "ExactNumber"]


def _reject_float(value: object) -> None:
    """Raise AccidentalFloatError if `value` is a raw Python float.

    This is the single choke point that enforces "no floats" for every
    ExactNumber constructor path. bool is a subclass of int in Python,
    so it is deliberately allowed through (booleans are not floats).
    """
    if isinstance(value, float):
        raise AccidentalFloatError(
            f"Refusing to construct ExactNumber from a raw float ({value!r}). "
            "Pass an int, a decimal/fraction string such as '100' or '1/3', "
            "a Fraction, or a Decimal instead."
        )


@dataclass(frozen=True, slots=True)
class ExactNumber:
    """An immutable, exact rational number.

    Immutability (`frozen=True`) matters here for the same reason it
    matters for `Decimal` and `Fraction` themselves: a value object
    that could be mutated in place would make it unsafe to share a
    single ExactNumber across multiple calculations, audit entries, or
    threads.
    """

    value: Fraction

    # ----- construction -------------------------------------------------

    def __init__(self, value: _AllowedInput) -> None:
        _reject_float(value)

        if isinstance(value, ExactNumber):
            fraction_value = value.value
        elif isinstance(value, Fraction):
            fraction_value = value
        elif isinstance(value, Decimal):
            fraction_value = Fraction(value)
        elif isinstance(value, int):
            fraction_value = Fraction(value)
        elif isinstance(value, str):
            fraction_value = self._parse_string(value)
        else:
            raise InvalidNumberError(
                f"Cannot construct ExactNumber from type {type(value).__name__}."
            )

        object.__setattr__(self, "value", fraction_value)

    @staticmethod
    def _parse_string(text: str) -> Fraction:
        """Parse a string such as '100', '1/3', '-5/7', or '33.33'.

        Decimal-looking strings ('33.33') are parsed via Decimal first
        so that the *textual* decimal digits are preserved exactly
        (Fraction('33.33') would otherwise go through a float-like
        parse path for some inputs); Fraction natively supports the
        'n/d' form directly.
        """
        stripped = text.strip()
        if not stripped:
            raise InvalidNumberError("Cannot construct ExactNumber from an empty string.")
        try:
            if "/" in stripped:
                return Fraction(stripped)
            return Fraction(Decimal(stripped))
        except (ValueError, ArithmeticError) as exc:
            raise InvalidNumberError(f"'{text}' is not a valid exact number.") from exc

    # ----- arithmetic -----------------------------------------------------

    def __add__(self, other: "ExactNumber") -> "ExactNumber":
        return ExactNumber(self.value + self._coerce(other))

    def __sub__(self, other: "ExactNumber") -> "ExactNumber":
        return ExactNumber(self.value - self._coerce(other))

    def __mul__(self, other: "ExactNumber") -> "ExactNumber":
        return ExactNumber(self.value * self._coerce(other))

    def __truediv__(self, other: "ExactNumber") -> "ExactNumber":
        divisor = self._coerce(other)
        if divisor == 0:
            raise DivisionByZeroFinancialError(
                f"Cannot divide {self.value} by zero."
            )
        return ExactNumber(self.value / divisor)

    def __neg__(self) -> "ExactNumber":
        return ExactNumber(-self.value)

    def __abs__(self) -> "ExactNumber":
        return ExactNumber(abs(self.value))

    @staticmethod
    def _coerce(other: "ExactNumber | Fraction | int") -> Fraction | int:
        if isinstance(other, ExactNumber):
            return other.value
        if isinstance(other, (Fraction, int)) and not isinstance(other, bool):
            return other
        if isinstance(other, float):
            raise AccidentalFloatError(
                f"Refusing to combine ExactNumber with a raw float ({other!r})."
            )
        raise InvalidNumberError(
            f"Cannot combine ExactNumber with type {type(other).__name__}."
        )

    # ----- comparisons ------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ExactNumber):
            return self.value == other.value
        if isinstance(other, (Fraction, int)) and not isinstance(other, bool):
            return self.value == other
        return NotImplemented

    def __lt__(self, other: "ExactNumber") -> bool:
        return self.value < self._coerce(other)

    def __le__(self, other: "ExactNumber") -> bool:
        return self.value <= self._coerce(other)

    def __gt__(self, other: "ExactNumber") -> bool:
        return self.value > self._coerce(other)

    def __ge__(self, other: "ExactNumber") -> bool:
        return self.value >= self._coerce(other)

    def __hash__(self) -> int:
        return hash(self.value)

    # ----- introspection ------------------------------------------------

    @property
    def numerator(self) -> int:
        return self.value.numerator

    @property
    def denominator(self) -> int:
        return self.value.denominator

    def is_integer(self) -> bool:
        return self.value.denominator == 1

    def is_terminating_decimal(self) -> bool:
        """True if the fraction's reduced denominator has only 2 and 5
        as prime factors -- i.e. it terminates in base 10 (e.g. 1/4,
        1/8, 3/20) rather than repeating forever (e.g. 1/3, 1/7).
        """
        denominator = self.value.denominator
        for prime in (2, 5):
            while denominator % prime == 0:
                denominator //= prime
        return denominator == 1

    def as_fraction(self) -> Fraction:
        """Escape hatch for interop with other Fraction-based code."""
        return self.value

    def __repr__(self) -> str:
        return f"ExactNumber({self.value.numerator}/{self.value.denominator})"

    def __str__(self) -> str:
        if self.value.denominator == 1:
            return str(self.value.numerator)
        return f"{self.value.numerator}/{self.value.denominator}"


Numeric = Union[ExactNumber, Rational, int]
