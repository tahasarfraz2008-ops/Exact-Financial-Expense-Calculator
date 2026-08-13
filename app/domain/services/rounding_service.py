"""
Rounding service -- the ONLY sanctioned way to round an exact value.

WHAT IS IT?
-----------
A pure function, `round_exact_number`, that takes an `ExactNumber`, a
number of decimal places, and a `RoundingPolicy`, and returns a
`RoundingResult` -- a small record holding the *original exact value*,
the *rounded value*, the rounding policy that was used, and the
*difference* the rounding introduced.

WHY DO WE NEED IT?
------------------
Section 7 of the specification is explicit: "Never silently round
values." If rounding happened as a side effect scattered across the
codebase (`some_value.round(2)` called ad hoc in ten different places),
there would be no single place to guarantee that the original exact
value is preserved and the rounding difference is recorded. Centralising
rounding here makes "silent rounding" structurally difficult -- any
code that wants a rounded number must go through this function and
therefore must retain the full `RoundingResult`, not just a bare
rounded number.

HOW DOES IT WORK?
------------------
1. Convert the exact `Fraction` to a `Decimal` using Python's
   `decimal.Context` with enough working precision to represent the
   requested number of places plus a safety margin (so the conversion
   itself introduces no additional error beyond the explicit rounding
   step).
2. Quantize that `Decimal` to the requested number of decimal places
   using the caller's chosen `RoundingPolicy`.
3. Compute the difference as an exact `ExactNumber`
   (`rounded - original`), so callers can see precisely how much value
   was gained or lost by rounding.

WHY THIS TECHNOLOGY?
---------------------
`decimal.Decimal.quantize` is the standard-library primitive that
implements exact, explicitly-rounded fixed-point decimal arithmetic --
it is the correct tool for "produce a decimal with exactly N places,
rounded a specific named way."

WHAT GOES WRONG IF IMPLEMENTED INCORRECTLY?
---------------------------------------------
If a rounding function returned only the rounded value and discarded
the original exact value, a settlement/allocation step downstream
would have no way to reconcile "why does the sum of the rounded parts
not exactly equal the exact total" -- which is precisely the scenario
Section 8 (Transaction splitting) and Section 25 (settlement vs
calculation) require the system to explain.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Context, Decimal, localcontext

from app.domain.value_objects.exact_number import ExactNumber
from app.domain.value_objects.rounding_policy import RoundingPolicy

# Working precision used only for the Fraction -> Decimal conversion step,
# before quantization. Generous enough that the conversion itself never
# introduces error beyond what quantize() explicitly performs.
_CONVERSION_PRECISION = 60


@dataclass(frozen=True, slots=True)
class RoundingResult:
    """The full, auditable outcome of a single rounding operation."""

    original_exact_value: ExactNumber
    rounded_value: Decimal
    decimal_places: int
    policy: RoundingPolicy
    difference: ExactNumber  # rounded_value - original_exact_value, exactly

    def __str__(self) -> str:
        return (
            f"Exact: {self.original_exact_value} -> "
            f"Rounded({self.decimal_places}dp, {self.policy.name}): {self.rounded_value} "
            f"(difference: {self.difference})"
        )


def _fraction_to_decimal(value: ExactNumber, working_precision: int) -> Decimal:
    """Convert an exact Fraction-backed value to a high-precision Decimal
    without rounding away information the caller asked to keep (the
    working precision is chosen far beyond the requested display/round
    precision).
    """
    context = Context(prec=working_precision)
    numerator = Decimal(value.numerator)
    denominator = Decimal(value.denominator)
    with localcontext(context):
        return numerator / denominator


def round_exact_number(
    value: ExactNumber,
    decimal_places: int,
    policy: RoundingPolicy,
) -> RoundingResult:
    """Round `value` to `decimal_places` using `policy`, returning a full
    `RoundingResult` that preserves the original exact value and records
    the rounding difference. This is the only function in the codebase
    permitted to perform financial rounding.
    """
    if decimal_places < 0:
        raise ValueError("decimal_places must be zero or a positive integer.")

    working_precision = max(_CONVERSION_PRECISION, decimal_places + 20)
    high_precision_decimal = _fraction_to_decimal(value, working_precision)

    quantum = Decimal(1).scaleb(-decimal_places)
    with localcontext(Context(prec=working_precision, rounding=policy.decimal_constant)):
        rounded_value = high_precision_decimal.quantize(quantum)

    difference = ExactNumber(rounded_value) - value

    return RoundingResult(
        original_exact_value=value,
        rounded_value=rounded_value,
        decimal_places=decimal_places,
        policy=policy,
        difference=difference,
    )
