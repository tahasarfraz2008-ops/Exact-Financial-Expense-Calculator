"""
FinancialCalculation, CalculationResult, and CalculationAudit entities.

WHAT ARE THEY?
--------------
- `FinancialCalculation`: represents a single request to evaluate an
  expression -- "what was asked."
- `CalculationResult`: represents the outcome -- "what was found,"
  including the exact result, a decimal display rendering, and whether
  the result is exact or only a displayed approximation.
- `CalculationAudit`: a full audit record tying a calculation and its
  result together with metadata required for regulatory/explainability
  purposes (Section 16): who ran it, when, and with what parameters.

WHY DO WE NEED THEM?
---------------------
Section 16 requires that "it must be possible to explain how a
financial result was obtained." A bare `ExactNumber` answer, on its
own, cannot answer "who asked for this, when, and what exactly did they
ask." These entities exist to carry that context as first-class domain
concepts rather than bolting logging onto the arithmetic engine as an
afterthought.

They are true *entities* (not value objects) because they have an
identity (`calculation_id`) that persists even if two calculations
happen to produce numerically identical results -- unlike, say, two
`Money` objects of the same amount and currency, which are
interchangeable.

HOW DO THEY WORK?
------------------
Plain, well-typed dataclasses. `CalculationResult.is_exact` is `True`
whenever no information-losing operation happened during the
calculation (i.e. the parser and evaluator never truncated anything);
it becomes `False` only once an explicit rounding/settlement step
(handled elsewhere, e.g. `RoundingResult`) has been applied on top of
this calculation's result.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.domain.services.decimal_display import DisplayResult, to_display_string
from app.domain.value_objects.exact_number import ExactNumber


@dataclass(frozen=True, slots=True)
class FinancialCalculation:
    """A single request to evaluate a financial expression."""

    expression: str
    calculation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    requested_display_digits: int = 20


@dataclass(frozen=True, slots=True)
class CalculationResult:
    """The outcome of evaluating a FinancialCalculation."""

    calculation: FinancialCalculation
    exact_result: ExactNumber
    display: DisplayResult
    is_exact: bool = True  # always True at this stage -- no rounding has occurred yet

    @staticmethod
    def from_exact_value(
        calculation: FinancialCalculation, exact_result: ExactNumber
    ) -> "CalculationResult":
        display = to_display_string(exact_result, calculation.requested_display_digits)
        return CalculationResult(
            calculation=calculation,
            exact_result=exact_result,
            display=display,
            is_exact=True,
        )


@dataclass(frozen=True, slots=True)
class CalculationAudit:
    """A full, explainable audit record of one calculation."""

    calculation_id: str
    timestamp: datetime
    input_expression: str
    exact_result: str
    displayed_result: str
    display_digits: int
    is_repeating: bool
    user_or_system_id: str
    rounding_policy_name: str | None = None

    @staticmethod
    def from_result(result: CalculationResult, user_or_system_id: str) -> "CalculationAudit":
        return CalculationAudit(
            calculation_id=result.calculation.calculation_id,
            timestamp=datetime.now(timezone.utc),
            input_expression=result.calculation.expression,
            exact_result=str(result.exact_result),
            displayed_result=result.display.text,
            display_digits=result.display.digits,
            is_repeating=result.display.is_repeating,
            user_or_system_id=user_or_system_id,
            rounding_policy_name=None,
        )
