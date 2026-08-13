"""
Application-layer DTOs (Data Transfer Objects).

WHAT ARE THEY?
--------------
Plain, serialisation-friendly objects that carry data across the
boundary between the outside world (an HTTP request, a CLI argument)
and the domain layer. They deliberately hold only strings/primitives --
never `ExactNumber`, `Fraction`, or domain entities directly.

WHY DO WE NEED THEM?
---------------------
Clean Architecture's dependency rule: the domain layer must not know
anything about HTTP, JSON, or FastAPI. DTOs are how the presentation
layer (Section 17's REST API) and the application layer talk to each
other without either one leaking its concerns into the domain. A DTO
also gives every API response a single, predictable shape that is
decoupled from however the domain entities are internally structured --
so changing a domain entity's internals does not automatically change
the API's wire format.

HOW DO THEY WORK?
------------------
Simple dataclasses with only `str`, `int`, `bool`, and `list`/`dict` of
those. Use cases build these from domain entities on the way out, and
convert incoming DTOs into domain calls on the way in.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CalculationRequestDTO:
    expression: str
    display_digits: int = 20


@dataclass(frozen=True, slots=True)
class CalculationResponseDTO:
    calculation_id: str
    expression: str
    exact_result: str
    decimal_result: str
    is_exact: bool
    is_repeating: bool


@dataclass(frozen=True, slots=True)
class RoundingRequestDTO:
    exact_value: str  # e.g. "100/3" or "33.5"
    decimal_places: int
    rounding_mode: str  # e.g. "HALF_UP"


@dataclass(frozen=True, slots=True)
class RoundingResponseDTO:
    original_exact_value: str
    rounded_value: str
    decimal_places: int
    rounding_mode: str
    difference: str


@dataclass(frozen=True, slots=True)
class ConversionRequestDTO:
    amount: str
    source_currency: str
    target_currency: str
    exchange_rate: str


@dataclass(frozen=True, slots=True)
class ConversionResponseDTO:
    original_amount: str
    source_currency: str
    exchange_rate: str
    converted_exact_amount: str
    converted_settled_amount: str
    target_currency: str
