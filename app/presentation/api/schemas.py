"""
Pydantic schemas for the REST API.

WHAT ARE THEY?
--------------
FastAPI/Pydantic request and response models -- the outermost,
HTTP-facing shape of the API, separate from the application layer's
DTOs.

WHY DO WE NEED THEM SEPARATE FROM THE DTOs?
---------------------------------------------
Keeping Pydantic models here (presentation) and plain dataclass DTOs in
`app/application/dto` means the application layer has zero dependency
on FastAPI/Pydantic. If the API framework were ever swapped (e.g. for
Flask or a gRPC service), only this file and the route handlers would
change -- the use cases would not need to move or be rewritten.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CalculationRequest(BaseModel):
    expression: str = Field(..., examples=["100 / 3 * 3"])
    display_digits: int = Field(default=20, ge=0, le=200)


class CalculationResponse(BaseModel):
    calculation_id: str
    expression: str
    exact_result: str
    decimal_result: str
    is_exact: bool
    is_repeating: bool


class RoundingRequest(BaseModel):
    exact_value: str = Field(..., examples=["100/3"])
    decimal_places: int = Field(..., ge=0, le=200)
    rounding_mode: str = Field(default="HALF_UP", examples=["HALF_UP"])


class RoundingResponse(BaseModel):
    original_exact_value: str
    rounded_value: str
    decimal_places: int
    rounding_mode: str
    difference: str


class ConversionRequest(BaseModel):
    amount: str = Field(..., examples=["100.00"])
    source_currency: str = Field(..., examples=["USD"])
    target_currency: str = Field(..., examples=["PKR"])
    exchange_rate: str = Field(..., examples=["278.4563"])


class ConversionResponse(BaseModel):
    original_amount: str
    source_currency: str
    exchange_rate: str
    converted_exact_amount: str
    converted_settled_amount: str
    target_currency: str


class HealthResponse(BaseModel):
    status: str
