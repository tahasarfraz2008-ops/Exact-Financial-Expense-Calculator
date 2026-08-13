"""
SQLAlchemy-backed repository implementations.

WHAT ARE THEY?
--------------
`SqlCalculationRepository` and `SqlAuditLogRepository` implement the
application layer's repository ports (Section 18) against a real
relational database (MySQL in production, SQLite in local dev, per
`app.infrastructure.persistence.database`).

WHY DO WE NEED THEM?
---------------------
The application/domain layers must not know whether persistence is a
Python dict, SQLite, or MySQL -- see the repository interface's own
docstring. These classes are the concrete adapter Clean Architecture
calls "infrastructure": they translate between domain entities and
database rows, and nothing above this layer needs to know that
translation exists.

HOW DO THEY WORK?
------------------
Each domain value is decomposed into primitive columns before writing
(e.g. an `ExactNumber` becomes a `(numerator, denominator)` string
pair -- see `database.py` for why), and reassembled into domain/DTO-ish
values on the way out. No raw SQL string formatting is used anywhere --
all queries go through SQLAlchemy's parameterised Core API, which is
what prevents SQL injection.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.engine import Engine

from app.application.interfaces.repositories import AuditLogRepository, CalculationRepository
from app.domain.entities.calculation import (
    CalculationAudit,
    CalculationResult,
    FinancialCalculation,
)
from app.domain.services.decimal_display import to_display_string
from app.domain.value_objects.exact_number import ExactNumber
from app.infrastructure.persistence.database import audit_logs_table, calculations_table


class SqlCalculationRepository(CalculationRepository):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save(self, result: CalculationResult) -> None:
        with self._engine.begin() as connection:
            connection.execute(
                calculations_table.insert().values(
                    calculation_id=result.calculation.calculation_id,
                    expression=result.calculation.expression,
                    exact_numerator=str(result.exact_result.numerator),
                    exact_denominator=str(result.exact_result.denominator),
                    display_digits=result.display.digits,
                    displayed_result=result.display.text,
                    is_repeating=int(result.display.is_repeating),
                    created_at=datetime.now(timezone.utc),
                )
            )

    def get_by_id(self, calculation_id: str) -> CalculationResult | None:
        with self._engine.connect() as connection:
            row = connection.execute(
                select(calculations_table).where(
                    calculations_table.c.calculation_id == calculation_id
                )
            ).fetchone()

        if row is None:
            return None

        exact_result = ExactNumber(int(row.exact_numerator)) / ExactNumber(int(row.exact_denominator))
        calculation = FinancialCalculation(
            expression=row.expression,
            calculation_id=row.calculation_id,
            requested_display_digits=row.display_digits,
        )
        display = to_display_string(exact_result, row.display_digits)
        return CalculationResult(calculation=calculation, exact_result=exact_result, display=display)


class SqlAuditLogRepository(AuditLogRepository):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def record(self, audit: CalculationAudit) -> None:
        with self._engine.begin() as connection:
            connection.execute(
                audit_logs_table.insert().values(
                    calculation_id=audit.calculation_id,
                    timestamp=audit.timestamp,
                    input_expression=audit.input_expression,
                    exact_result=audit.exact_result,
                    displayed_result=audit.displayed_result,
                    display_digits=audit.display_digits,
                    is_repeating=int(audit.is_repeating),
                    user_or_system_id=audit.user_or_system_id,
                    rounding_policy_name=audit.rounding_policy_name,
                )
            )

    def get_by_calculation_id(self, calculation_id: str) -> list[CalculationAudit]:
        with self._engine.connect() as connection:
            rows = connection.execute(
                select(audit_logs_table).where(
                    audit_logs_table.c.calculation_id == calculation_id
                )
            ).fetchall()

        return [
            CalculationAudit(
                calculation_id=row.calculation_id,
                timestamp=row.timestamp,
                input_expression=row.input_expression,
                exact_result=row.exact_result,
                displayed_result=row.displayed_result,
                display_digits=row.display_digits,
                is_repeating=bool(row.is_repeating),
                user_or_system_id=row.user_or_system_id,
                rounding_policy_name=row.rounding_policy_name,
            )
            for row in rows
        ]
