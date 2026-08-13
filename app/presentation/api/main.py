"""
FastAPI application entry point.

WHAT IS IT?
-----------
Wires HTTP routes (Section 17) to application-layer use cases:

    POST /api/v1/calculations
    GET  /api/v1/calculations/{id}
    POST /api/v1/round
    POST /api/v1/convert
    GET  /api/v1/health

WHY DO WE NEED IT?
------------------
This is the outermost "presentation" layer in Clean Architecture. It
translates HTTP requests into DTOs, calls a use case, and translates
the result back into an HTTP response -- and it is the layer where
domain exceptions get mapped to sensible HTTP status codes, since HTTP
status codes are an HTTP concept the domain layer must not know about.

WHY FASTAPI?
------------
FastAPI gives request/response validation (via Pydantic), automatic
OpenAPI docs, and async support out of the box, with a small,
explicit dependency footprint -- a good fit for a project that wants a
real, documented REST API without hand-rolling request validation.

HOW DOES IT WORK?
------------------
A single dependency-injection function (`get_use_cases`) builds the
use cases with in-memory repositories by default (see
`app/infrastructure/repositories/in_memory_repositories.py`); swapping
to the SQL-backed repositories only requires changing this wiring,
never the use cases or routes themselves.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from fastapi import FastAPI, HTTPException

from app.application.dto.calculation_dto import (
    CalculationRequestDTO,
    ConversionRequestDTO,
    RoundingRequestDTO,
)
from app.application.use_cases.convert_currency import ConvertCurrencyUseCase
from app.application.use_cases.evaluate_expression import EvaluateExpressionUseCase
from app.application.use_cases.round_value import RoundValueUseCase
from app.domain.exceptions.financial_exceptions import FinancialEngineError
from app.infrastructure.logging.logging_config import configure_logging
from app.infrastructure.repositories.in_memory_repositories import (
    InMemoryAuditLogRepository,
    InMemoryCalculationRepository,
)
from app.presentation.api.schemas import (
    CalculationRequest,
    CalculationResponse,
    ConversionRequest,
    ConversionResponse,
    HealthResponse,
    RoundingRequest,
    RoundingResponse,
)

configure_logging()

app = FastAPI(
    title="Exact Financial Arithmetic Engine",
    description=(
        "A lossless, rational-arithmetic financial calculation engine. "
        "See /docs for interactive API documentation."
    ),
    version="1.0.0",
)


@dataclass(frozen=True, slots=True)
class _UseCases:
    evaluate_expression: EvaluateExpressionUseCase
    round_value: RoundValueUseCase
    convert_currency: ConvertCurrencyUseCase
    calculation_repository: InMemoryCalculationRepository


@lru_cache(maxsize=1)
def get_use_cases() -> _UseCases:
    calculation_repository = InMemoryCalculationRepository()
    audit_log_repository = InMemoryAuditLogRepository()
    return _UseCases(
        evaluate_expression=EvaluateExpressionUseCase(calculation_repository, audit_log_repository),
        round_value=RoundValueUseCase(),
        convert_currency=ConvertCurrencyUseCase(),
        calculation_repository=calculation_repository,
    )


@app.get("/api/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/api/v1/calculations", response_model=CalculationResponse)
def create_calculation(request: CalculationRequest) -> CalculationResponse:
    use_cases = get_use_cases()
    try:
        result = use_cases.evaluate_expression.execute(
            CalculationRequestDTO(
                expression=request.expression, display_digits=request.display_digits
            )
        )
    except FinancialEngineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return CalculationResponse(
        calculation_id=result.calculation_id,
        expression=result.expression,
        exact_result=result.exact_result,
        decimal_result=result.decimal_result,
        is_exact=result.is_exact,
        is_repeating=result.is_repeating,
    )


@app.get("/api/v1/calculations/{calculation_id}", response_model=CalculationResponse)
def get_calculation(calculation_id: str) -> CalculationResponse:
    use_cases = get_use_cases()
    stored = use_cases.calculation_repository.get_by_id(calculation_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Calculation not found.")

    return CalculationResponse(
        calculation_id=stored.calculation.calculation_id,
        expression=stored.calculation.expression,
        exact_result=str(stored.exact_result),
        decimal_result=stored.display.text,
        is_exact=stored.is_exact,
        is_repeating=stored.display.is_repeating,
    )


@app.post("/api/v1/round", response_model=RoundingResponse)
def round_value(request: RoundingRequest) -> RoundingResponse:
    use_cases = get_use_cases()
    try:
        result = use_cases.round_value.execute(
            RoundingRequestDTO(
                exact_value=request.exact_value,
                decimal_places=request.decimal_places,
                rounding_mode=request.rounding_mode,
            )
        )
    except FinancialEngineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return RoundingResponse(
        original_exact_value=result.original_exact_value,
        rounded_value=result.rounded_value,
        decimal_places=result.decimal_places,
        rounding_mode=result.rounding_mode,
        difference=result.difference,
    )


@app.post("/api/v1/convert", response_model=ConversionResponse)
def convert_currency(request: ConversionRequest) -> ConversionResponse:
    use_cases = get_use_cases()
    try:
        result = use_cases.convert_currency.execute(
            ConversionRequestDTO(
                amount=request.amount,
                source_currency=request.source_currency,
                target_currency=request.target_currency,
                exchange_rate=request.exchange_rate,
            )
        )
    except FinancialEngineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ConversionResponse(
        original_amount=result.original_amount,
        source_currency=result.source_currency,
        exchange_rate=result.exchange_rate,
        converted_exact_amount=result.converted_exact_amount,
        converted_settled_amount=result.converted_settled_amount,
        target_currency=result.target_currency,
    )
