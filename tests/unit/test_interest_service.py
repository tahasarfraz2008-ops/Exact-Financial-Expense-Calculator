from decimal import Decimal

from app.domain.entities.money import Money
from app.domain.services.interest_service import (
    build_amortization_schedule,
    compound_interest,
    simple_interest,
)
from app.domain.value_objects.exact_number import ExactNumber


def test_simple_interest_exact():
    principal = ExactNumber("1000")
    rate = ExactNumber("1") / ExactNumber("20")  # 5%
    time = ExactNumber(2)
    interest = simple_interest(principal, rate, time)
    assert interest == ExactNumber(100)


def test_compound_interest_matches_hand_calculation():
    principal = ExactNumber(1000)
    annual_rate = ExactNumber("1") / ExactNumber("20")  # 5%
    interest = compound_interest(principal, annual_rate, periods_per_year=1, time_in_years=2)
    # 1000 * 1.05^2 - 1000 = 102.5 exactly
    assert interest == ExactNumber("102.5")


def test_amortization_schedule_final_balance_is_zero():
    principal = Money.of("1200.00", "USD")
    annual_rate = ExactNumber("1") / ExactNumber("10")  # 10%
    schedule = build_amortization_schedule(
        principal, annual_rate, periods_per_year=12, number_of_payments=12
    )
    assert schedule[-1].remaining_balance_exact == ExactNumber(0)
    assert len(schedule) == 12


def test_amortization_schedule_zero_rate_splits_evenly():
    principal = Money.of("300.00", "USD")
    schedule = build_amortization_schedule(
        principal, ExactNumber(0), periods_per_year=3, number_of_payments=3
    )
    for row in schedule:
        assert row.interest_portion.amount == ExactNumber(0)
    assert schedule[-1].remaining_balance_exact == ExactNumber(0)
