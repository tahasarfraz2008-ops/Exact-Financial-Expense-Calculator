"""
ConvertCurrencyUseCase.

WHAT IS IT?
-----------
Application-layer wrapper around the domain's currency conversion
service, backing `POST /api/v1/convert`.

WHY DO WE NEED IT?
------------------
Converts a request DTO (all strings, from JSON) into domain calls, and
maps the result back into a response DTO that shows BOTH the full
exact converted amount and the currency-settled amount, so API
consumers can see the distinction between "the mathematically exact
converted value" and "what would actually be booked/paid" in the
target currency -- exactly the distinction Section 8 asks for.
"""

from __future__ import annotations

from app.application.dto.calculation_dto import ConversionRequestDTO, ConversionResponseDTO
from app.domain.entities.money import Money
from app.domain.services.currency_conversion_service import convert
from app.domain.value_objects.currency import Currency
from app.domain.value_objects.exact_number import ExactNumber


class ConvertCurrencyUseCase:
    def execute(self, request: ConversionRequestDTO) -> ConversionResponseDTO:
        source_money = Money.of(request.amount, Currency.of(request.source_currency))
        rate = ExactNumber(request.exchange_rate)

        conversion = convert(source_money, request.target_currency, rate)
        settlement = conversion.converted_exact.settle()

        return ConversionResponseDTO(
            original_amount=str(source_money.amount),
            source_currency=source_money.currency.code,
            exchange_rate=str(rate),
            converted_exact_amount=str(conversion.converted_exact.amount),
            converted_settled_amount=str(settlement.rounded_value),
            target_currency=conversion.converted_exact.currency.code,
        )
