"""
RoundValueUseCase.

WHAT IS IT?
-----------
Application-layer wrapper around the domain's `round_exact_number`
service, exposed as the `POST /api/v1/round` endpoint's business logic.

WHY DO WE NEED IT?
------------------
Rounding is deliberately never automatic anywhere else in this codebase
(Section 7: "Never silently round values"). This use case is the one
explicit, intentional place a caller asks for a rounded value, and it
always returns the full before/after/difference triple -- never just
the rounded number on its own.
"""

from __future__ import annotations

from app.application.dto.calculation_dto import RoundingRequestDTO, RoundingResponseDTO
from app.domain.services.rounding_service import round_exact_number
from app.domain.value_objects.exact_number import ExactNumber
from app.domain.value_objects.rounding_policy import RoundingPolicy


class RoundValueUseCase:
    def execute(self, request: RoundingRequestDTO) -> RoundingResponseDTO:
        exact_value = ExactNumber(request.exact_value)
        policy = RoundingPolicy.from_name(request.rounding_mode)

        result = round_exact_number(exact_value, request.decimal_places, policy)

        return RoundingResponseDTO(
            original_exact_value=str(result.original_exact_value),
            rounded_value=str(result.rounded_value),
            decimal_places=result.decimal_places,
            rounding_mode=result.policy.name,
            difference=str(result.difference),
        )
