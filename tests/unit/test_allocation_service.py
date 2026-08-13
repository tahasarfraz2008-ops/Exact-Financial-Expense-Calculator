from decimal import Decimal

from app.domain.entities.money import Money
from app.domain.services.allocation_service import allocate
from app.domain.value_objects.exact_number import ExactNumber


def test_split_100_into_3_sums_exactly():
    total = Money.of("100.00", "USD")
    result = allocate(total, 3)

    parts = sorted(p.settle().rounded_value for p in result.settled_parts)
    assert parts == [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")]
    assert sum(parts) == Decimal("100.00")


def test_allocation_exact_share_is_preserved_for_audit():
    total = Money.of("100.00", "USD")
    result = allocate(total, 3)
    assert result.exact_share_per_part == ExactNumber("100") / ExactNumber("3")


def test_allocation_evenly_divisible_total():
    total = Money.of("90.00", "USD")
    result = allocate(total, 3)
    parts = [p.settle().rounded_value for p in result.settled_parts]
    assert parts == [Decimal("30.00"), Decimal("30.00"), Decimal("30.00")]


def test_settled_total_matches_settled_original():
    total = Money.of("10.00", "USD")
    result = allocate(total, 7)
    settled_total = sum((p.settle().rounded_value for p in result.settled_parts), Decimal("0"))
    assert settled_total == total.settle().rounded_value
