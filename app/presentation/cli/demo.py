"""
CLI demonstration screen (Section 20).

WHAT IS IT?
-----------
A runnable script (`python -m app.presentation.cli.demo`) that shows,
in plain text, the exact scenario this whole project exists to solve:
`100 / 3`, its exact value, its decimal display, and what happens when
you multiply that result back by 3 -- both the WRONG way (rounding
first) and the RIGHT way (staying exact throughout).

WHY DO WE NEED IT?
------------------
Section 20 explicitly asks for a demonstration screen and a
side-by-side comparison panel. A CLI is the fastest, dependency-free
way to give a self-contained demo that runs anywhere Python runs, in
addition to the interactive `/docs` page FastAPI provides.

HOW DOES IT WORK?
------------------
Uses only the domain layer (`evaluate_expression`, `to_display_string`,
`round_exact_number`) -- exactly the same functions the API and use
cases call -- so the demo is guaranteed to reflect the real engine's
behaviour, not a separate hand-written example.
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.services.decimal_display import to_display_string
from app.domain.services.expression_evaluator import evaluate_expression
from app.domain.services.rounding_service import round_exact_number
from app.domain.value_objects.exact_number import ExactNumber
from app.domain.value_objects.rounding_policy import RoundingPolicy


def _section(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def run_demo() -> None:
    _section("INPUT: 100 / 3")
    exact_100_over_3 = evaluate_expression("100 / 3")
    display = to_display_string(exact_100_over_3, digits=24)
    print(f"Exact value:        {exact_100_over_3}")
    print(f"Decimal display:    {display.text}")
    rounded = round_exact_number(exact_100_over_3, 2, RoundingPolicy.HALF_UP)
    print(f"Rounded to 2dp:     {rounded.rounded_value}")

    _section("THEN: (100 / 3) * 3")
    exact_result = evaluate_expression("(100 / 3) * 3")
    print(f"Result:             {exact_result}")
    print(f"Status:             {'EXACT' if exact_result == ExactNumber(100) else 'APPROXIMATE'}"
          " -- no intermediate rounding")

    _section("COMPARISON PANEL")
    incorrect = Decimal("33.33") * Decimal("3")
    print(f"Incorrect floating/rounded approach: 33.33 * 3 = {incorrect}")
    print(f"Exact approach:                       100/3 * 3 = {exact_result}")

    _section("INPUT: 1/3 + 1/3 + 1/3")
    one_third_sum = evaluate_expression("1 / 3 + 1 / 3 + 1 / 3")
    print(f"Result: {one_third_sum} "
          f"({'EXACT' if one_third_sum == ExactNumber(1) else 'APPROXIMATE'})")


if __name__ == "__main__":
    run_demo()
