from app.application.dto.calculation_dto import (
    CalculationRequestDTO,
    ConversionRequestDTO,
    RoundingRequestDTO,
)
from app.application.use_cases.convert_currency import ConvertCurrencyUseCase
from app.application.use_cases.evaluate_expression import EvaluateExpressionUseCase
from app.application.use_cases.round_value import RoundValueUseCase
from app.infrastructure.repositories.in_memory_repositories import (
    InMemoryAuditLogRepository,
    InMemoryCalculationRepository,
)


def test_evaluate_expression_use_case_persists_and_audits():
    calc_repo = InMemoryCalculationRepository()
    audit_repo = InMemoryAuditLogRepository()
    use_case = EvaluateExpressionUseCase(calc_repo, audit_repo)

    response = use_case.execute(CalculationRequestDTO(expression="100 / 3 * 3"))

    assert response.exact_result == "100"
    assert response.is_exact is True

    stored = calc_repo.get_by_id(response.calculation_id)
    assert stored is not None
    assert str(stored.exact_result) == "100"

    audits = audit_repo.get_by_calculation_id(response.calculation_id)
    assert len(audits) == 1
    assert audits[0].input_expression == "100 / 3 * 3"


def test_evaluate_expression_flags_repeating_decimal():
    calc_repo = InMemoryCalculationRepository()
    audit_repo = InMemoryAuditLogRepository()
    use_case = EvaluateExpressionUseCase(calc_repo, audit_repo)

    response = use_case.execute(CalculationRequestDTO(expression="100 / 3", display_digits=10))

    assert response.exact_result == "100/3"
    assert response.is_repeating is True
    assert response.decimal_result.endswith("...")


def test_round_value_use_case_returns_full_audit_triple():
    use_case = RoundValueUseCase()
    response = use_case.execute(
        RoundingRequestDTO(exact_value="100/3", decimal_places=2, rounding_mode="HALF_UP")
    )
    assert response.original_exact_value == "100/3"
    assert response.rounded_value == "33.33"
    assert response.rounding_mode == "HALF_UP"
    assert response.difference != "0"


def test_convert_currency_use_case():
    use_case = ConvertCurrencyUseCase()
    response = use_case.execute(
        ConversionRequestDTO(
            amount="100.00",
            source_currency="USD",
            target_currency="PKR",
            exchange_rate="278.4563",
        )
    )
    # 100.00 * 278.4563 = 27845.6300 exactly, kept as an unreduced exact
    # fraction (2784563/100) rather than collapsed to a decimal string --
    # the settled amount below is where currency-precision rounding happens.
    assert response.converted_exact_amount == "2784563/100"
    assert response.converted_settled_amount == "27845.63"
    assert response.target_currency == "PKR"
