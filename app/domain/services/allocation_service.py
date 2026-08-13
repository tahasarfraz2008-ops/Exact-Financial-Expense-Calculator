"""
Allocation service -- splitting an exact amount into real, payable parts.

WHAT IS IT?
-----------
`allocate(total, parts, currency)` takes a `Money` total (e.g. `100.00
USD`) and a number of parts (e.g. 3), and returns a list of `Money`
values in the currency's real settlement precision (e.g.
`[33.33, 33.33, 33.34]`) that sum EXACTLY to the original total -- no
cent is created or lost.

WHY DO WE NEED IT?
------------------
This is precisely Section 8's "Transaction splitting" and Section 25's
"exact calculation vs financial settlement" requirement. The exact
mathematical answer to `100.00 / 3` is `33.3333...` repeating forever --
you cannot pay someone a repeating decimal number of cents. A bank must
decide, as an explicit business rule, how the leftover fraction of a
cent gets distributed among the parts. Naively rounding each share
independently (`33.33`, `33.33`, `33.33`) would lose one cent overall
(`99.99` instead of `100.00`) -- an unacceptable, auditable discrepancy
in a banking system.

HOW DOES IT WORK?
------------------
This uses the "largest remainder" allocation method, which is standard
in accounting/apportionment systems:
1. Compute the exact, unrounded share for each part
   (`total.amount / parts`, still a Fraction).
2. Round every share DOWN to the currency's precision, and note how
   much of the true share got left over as a "remainder" for that part.
3. The rounded-down shares almost certainly sum to slightly less than
   the true total (unless it happened to divide evenly). Distribute the
   leftover smallest-currency-units one at a time to the parts with the
   largest remainders, until the rounded parts sum EXACTLY to the
   original total.

This guarantees, by construction, that `sum(allocate(total, n)) ==
total` exactly, while every individual part is a valid, payable amount
at the currency's precision.

WHY THIS TECHNOLOGY?
---------------------
Pure integer/Fraction arithmetic on "smallest currency units" (cents),
so the reconciliation step is exact integer bookkeeping, not another
opportunity for floating-point drift.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.entities.money import Money
from app.domain.value_objects.exact_number import ExactNumber
from app.domain.value_objects.rounding_policy import RoundingPolicy
from app.domain.services.rounding_service import round_exact_number


@dataclass(frozen=True, slots=True)
class AllocationResult:
    """The full, auditable outcome of splitting a total into parts."""

    exact_total: ExactNumber
    exact_share_per_part: ExactNumber  # before settlement rounding
    settled_parts: list[Money]

    def settled_total(self) -> ExactNumber:
        total = ExactNumber(0)
        for part in self.settled_parts:
            total = total + part.amount
        return total


def allocate(total: Money, parts: int) -> AllocationResult:
    """Split `total` into `parts` real, payable Money amounts that sum
    exactly to `total`, using the largest-remainder allocation method.
    """
    if parts <= 0:
        raise ValueError("parts must be a positive integer.")

    decimal_places = total.currency.decimal_places
    unit = ExactNumber(Decimal(1).scaleb(-decimal_places))  # smallest currency unit, e.g. 0.01

    exact_share = total.amount / ExactNumber(parts)

    # Step 1: round every share down to whole smallest-units, keep the remainder.
    shares_in_units: list[int] = []
    remainders: list[ExactNumber] = []
    for _ in range(parts):
        rounded_down = round_exact_number(exact_share, decimal_places, RoundingPolicy.DOWN)
        units = int(rounded_down.rounded_value.scaleb(decimal_places))
        shares_in_units.append(units)
        remainders.append(exact_share - ExactNumber(rounded_down.rounded_value))

    total_units = int(
        round_exact_number(total.amount, decimal_places, RoundingPolicy.HALF_UP)
        .rounded_value.scaleb(decimal_places)
    )
    leftover_units = total_units - sum(shares_in_units)

    # Step 2: hand out the leftover smallest-units to the largest remainders first.
    order = sorted(range(parts), key=lambda i: remainders[i], reverse=True)
    for i in order[:leftover_units]:
        shares_in_units[i] += 1

    settled_parts = [
        Money.of(ExactNumber(units) * unit, total.currency) for units in shares_in_units
    ]

    return AllocationResult(
        exact_total=total.amount,
        exact_share_per_part=exact_share,
        settled_parts=settled_parts,
    )
