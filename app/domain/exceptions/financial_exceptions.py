"""
Domain exceptions for the Exact Financial Arithmetic Engine.

WHAT
----
A dedicated exception hierarchy so that every failure mode in the engine
(division by zero, an invalid currency, an accidental float, a silent
rounding attempt, ...) raises something specific and named -- never a
bare ValueError or, worse, a swallowed error.

WHY
---
In a banking context, "something went wrong" is not an acceptable error
message. Support staff, auditors, and calling code all need to know
*exactly* which safety rule was violated. A specific exception type is
also what lets calling code decide, programmatically, whether an error
is retryable, a user input problem, or a serious internal bug.

HOW
---
All exceptions derive from `FinancialEngineError`, so callers can catch
that single base class when they just want "anything went wrong with
the engine," or catch a specific subclass when they need to react
differently (e.g. `InvalidCurrencyError` might trigger a "pick a
supported currency" prompt, while `AccidentalFloatError` should never
happen in production and indicates a programming bug).
"""

from __future__ import annotations


class FinancialEngineError(Exception):
    """Base class for every exception raised by the financial engine.

    Catch this if you want to handle "any engine failure" in one place
    (e.g. to return a generic 400 response from an API layer) without
    accidentally catching unrelated Python exceptions from other code.
    """


class DivisionByZeroFinancialError(FinancialEngineError):
    """Raised when a calculation would divide by zero.

    Python's own ZeroDivisionError is fine for general code, but inside
    a financial engine we want a domain-specific type so that division
    by zero is always treated as a *financial* safety violation, not an
    incidental arithmetic accident.
    """


class InvalidNumberError(FinancialEngineError):
    """Raised when a value cannot be interpreted as an exact number.

    Examples: empty strings, malformed numeric literals, NaN, infinity,
    or any input that is not a finite, well-formed number.
    """


class InvalidExpressionError(FinancialEngineError):
    """Raised when a user-supplied expression cannot be safely parsed
    or evaluated (unbalanced parentheses, unknown tokens, disallowed
    operators, empty expressions, etc.).
    """


class InvalidCurrencyError(FinancialEngineError):
    """Raised when a currency code is unknown or unsupported, or when
    an operation mixes two different currencies without an explicit
    conversion step.
    """


class InvalidRoundingModeError(FinancialEngineError):
    """Raised when a requested rounding policy is not one of the
    supported, explicitly-named rounding modes.
    """


class NegativeValueNotAllowedError(FinancialEngineError):
    """Raised when a business rule forbids a negative value (e.g. an
    account balance floor, a principal amount, an interest rate) but a
    negative value was supplied or produced.
    """


class OverflowFinancialError(FinancialEngineError):
    """Raised when a value exceeds a configured safety bound.

    Arbitrary-precision arithmetic in Python does not overflow the way
    fixed-width integers do, but an unbounded numerator/denominator can
    still indicate a runaway calculation or an attack (e.g. someone
    feeding in an expression engineered to blow up memory/CPU). This
    exception lets calling code enforce a sane upper bound.
    """


class PrecisionLossError(FinancialEngineError):
    """Raised when an operation would silently lose exactness where the
    caller required an exact result (e.g. attempting to force an exact
    Fraction into a terminating Decimal that cannot represent it
    exactly, without acknowledging the loss).
    """


class AccidentalFloatError(FinancialEngineError):
    """Raised when a raw Python `float` is detected where only
    `Fraction` or `Decimal` are permitted.

    This exists purely as a safety net / regression guard: it should be
    structurally impossible to reach, because the type system and the
    parser never accept floats, but this exception documents the rule
    and gives tests something concrete to assert against.
    """


class SilentRoundingError(FinancialEngineError):
    """Raised if code attempts to round a value without going through
    the explicit `RoundingPolicy` API, which always records the
    original exact value alongside the rounded one.
    """
