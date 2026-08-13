"""
Interest and loan calculation services.

WHAT ARE THEY?
--------------
Pure functions implementing the standard banking formulas -- simple
interest (`Principal x Rate x Time`), compound interest, and a loan
amortization schedule -- entirely on `ExactNumber`/`Money`, with zero
`float` involved anywhere in the computation path.

WHY DO WE NEED THEM?
---------------------
Section 8 explicitly calls for interest and loan calculations as
banking use cases, and explicitly forbids floating-point arithmetic for
them. Interest calculations are a textbook example of where rounding
too early causes real financial harm: a bank that rounds each month's
interest before it compounds will, over years, pay or collect a
noticeably different amount than one that keeps every month's interest
exact until the final statement is settled.

HOW DO THEY WORK?
------------------
- `simple_interest(principal, annual_rate, time_in_years)` computes
  `principal * annual_rate * time_in_years` directly on exact values.
- `compound_interest(principal, annual_rate, periods_per_year,
  time_in_years)` computes
  `principal * (1 + rate/periods_per_year) ** (periods_per_year *
  time_in_years) - principal`, using `Fraction.__pow__`, which is exact
  for integer exponents (this project deliberately restricts periods
  and years to values that produce an integer number of compounding
  periods, so the exponent is always an integer, and the power
  operation stays exact).
- `build_amortization_schedule(...)` walks the loan period by period,
  computing each period's interest portion, principal portion, and
  remaining balance, keeping everything as `ExactNumber` and settling
  to `Money` only for the values placed into the returned schedule
  rows (matching Section 6's calculation-precision vs monetary-
  precision separation).

WHY THIS TECHNOLOGY?
---------------------
`Fraction` supports exact integer exponentiation directly
(`Fraction(21, 20) ** 12` is exact), so compound interest with a whole
number of compounding periods needs no additional machinery.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.money import Money
from app.domain.value_objects.exact_number import ExactNumber
from app.domain.value_objects.rounding_policy import RoundingPolicy


def simple_interest(
    principal: ExactNumber, annual_rate: ExactNumber, time_in_years: ExactNumber
) -> ExactNumber:
    """Principal x Rate x Time, kept fully exact."""
    return principal * annual_rate * time_in_years


def compound_interest(
    principal: ExactNumber,
    annual_rate: ExactNumber,
    periods_per_year: int,
    time_in_years: int,
) -> ExactNumber:
    """Exact compound interest for a whole number of years and an
    integer number of compounding periods per year, so the exponent in
    the compounding formula is always an exact integer.
    """
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be a positive integer.")
    if time_in_years < 0:
        raise ValueError("time_in_years must not be negative.")

    total_periods = periods_per_year * time_in_years
    rate_per_period = annual_rate / ExactNumber(periods_per_year)
    growth_factor = (ExactNumber(1) + rate_per_period).as_fraction() ** total_periods
    final_amount = principal * ExactNumber(growth_factor)
    return final_amount - principal


@dataclass(frozen=True, slots=True)
class AmortizationRow:
    period: int
    payment: Money
    interest_portion: Money
    principal_portion: Money
    remaining_balance_exact: ExactNumber  # kept exact between rows -- see module docstring
    remaining_balance_settled: Money


def build_amortization_schedule(
    principal: Money,
    annual_rate: ExactNumber,
    periods_per_year: int,
    number_of_payments: int,
) -> list[AmortizationRow]:
    """Build a standard fixed-payment loan amortization schedule.

    The running balance is kept as an exact `ExactNumber` between rows
    (never re-derived from a previously rounded/settled value), so
    rounding error cannot accumulate period over period. Each row also
    exposes a currency-settled version of the balance for display and
    booking purposes -- the two are always kept explicitly distinct.
    """
    if number_of_payments <= 0:
        raise ValueError("number_of_payments must be a positive integer.")

    rate_per_period = annual_rate / ExactNumber(periods_per_year)

    if rate_per_period == 0:
        payment_amount = principal.amount / ExactNumber(number_of_payments)
    else:
        growth_factor = (ExactNumber(1) + rate_per_period).as_fraction() ** number_of_payments
        growth = ExactNumber(growth_factor)
        payment_amount = (
            principal.amount * rate_per_period * growth
        ) / (growth - ExactNumber(1))

    schedule: list[AmortizationRow] = []
    remaining_balance = principal.amount

    for period in range(1, number_of_payments + 1):
        interest_portion = remaining_balance * rate_per_period
        principal_portion = payment_amount - interest_portion

        # Final payment absorbs any tiny exact remainder so the balance
        # reaches precisely zero rather than an infinitesimal leftover
        # fraction caused by dividing a non-terminating rate evenly.
        if period == number_of_payments:
            principal_portion = remaining_balance
            actual_payment = interest_portion + principal_portion
        else:
            actual_payment = payment_amount

        remaining_balance = remaining_balance - principal_portion

        schedule.append(
            AmortizationRow(
                period=period,
                payment=Money(actual_payment, principal.currency),
                interest_portion=Money(interest_portion, principal.currency),
                principal_portion=Money(principal_portion, principal.currency),
                remaining_balance_exact=remaining_balance,
                remaining_balance_settled=Money(
                    ExactNumber(
                        Money(remaining_balance, principal.currency)
                        .settle(RoundingPolicy.HALF_UP)
                        .rounded_value
                    ),
                    principal.currency,
                ),
            )
        )

    return schedule
