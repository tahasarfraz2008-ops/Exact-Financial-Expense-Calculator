"""
EvaluateExpressionUseCase.

WHAT IS IT?
-----------
Orchestrates: parse a user-supplied expression -> get an exact result
-> build a `CalculationResult` -> persist it -> record an audit entry
-> return a DTO. This is the application-layer "verb" behind
`POST /api/v1/calculations`.

WHY DO WE NEED IT?
------------------
Keeps the presentation layer (FastAPI route handlers, Section 17) thin.
A route handler should only translate HTTP <-> DTOs and call a use
case; it should never contain business logic or talk to the domain
layer's value objects/services directly. That separation is what makes
it possible to add a second frontend (a CLI, Section 20's demonstration
screen) that calls the exact same use case without duplicating any
logic.

HOW DOES IT WORK?
------------------
1. `evaluate_expression` (domain service) parses and computes the
   exact `ExactNumber` result -- this is the only place `float` could
   sneak in, and it structurally cannot, per that module's docstring.
2. Wrap it in `CalculationResult.from_exact_value`, which also builds
   the display string via the decimal-display service.
3. Persist via the injected `CalculationRepository`.
4. Record a `CalculationAudit` via the injected `AuditLogRepository`.
5. Map to `CalculationResponseDTO` for the caller.
"""

from __future__ import annotations

from app.application.dto.calculation_dto import CalculationRequestDTO, CalculationResponseDTO
from app.application.interfaces.repositories import AuditLogRepository, CalculationRepository
from app.domain.entities.calculation import (
    CalculationAudit,
    CalculationResult,
    FinancialCalculation,
)
from app.domain.services.expression_evaluator import evaluate_expression


class EvaluateExpressionUseCase:
    def __init__(
        self,
        calculation_repository: CalculationRepository,
        audit_log_repository: AuditLogRepository,
    ) -> None:
        self._calculation_repository = calculation_repository
        self._audit_log_repository = audit_log_repository

    def execute(
        self, request: CalculationRequestDTO, user_or_system_id: str = "anonymous"
    ) -> CalculationResponseDTO:
        calculation = FinancialCalculation(
            expression=request.expression,
            requested_display_digits=request.display_digits,
        )

        exact_result = evaluate_expression(calculation.expression)
        result = CalculationResult.from_exact_value(calculation, exact_result)

        self._calculation_repository.save(result)
        audit = CalculationAudit.from_result(result, user_or_system_id)
        self._audit_log_repository.record(audit)

        return CalculationResponseDTO(
            calculation_id=calculation.calculation_id,
            expression=calculation.expression,
            exact_result=str(exact_result),
            decimal_result=result.display.text,
            is_exact=result.is_exact,
            is_repeating=result.display.is_repeating,
        )
