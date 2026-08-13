"""
In-memory repository implementations.

WHAT ARE THEY?
--------------
`InMemoryCalculationRepository` and `InMemoryAuditLogRepository`
implement the application layer's repository interfaces using plain
Python dicts/lists held in process memory.

WHY DO WE NEED THEM?
---------------------
Two reasons:
1. **Tests**: unit and integration tests should not need a running
   MySQL server just to exercise a use case. These fakes let tests
   inject a real (if trivial) implementation of the port instead of a
   mock, exercising the actual save/retrieve contract.
2. **Zero-dependency default**: the demonstration CLI/API (Section 20)
   can run immediately after `pip install -r requirements.txt` with no
   database set up at all, using this as the default repository.

HOW DO THEY WORK?
------------------
Nothing fancy -- a `dict[str, CalculationResult]` keyed by calculation
id, and a `dict[str, list[CalculationAudit]]` keyed the same way. Not
thread-safe beyond what the GIL already gives single operations; not
intended for production use.
"""

from __future__ import annotations

from app.application.interfaces.repositories import AuditLogRepository, CalculationRepository
from app.domain.entities.calculation import CalculationAudit, CalculationResult


class InMemoryCalculationRepository(CalculationRepository):
    def __init__(self) -> None:
        self._store: dict[str, CalculationResult] = {}

    def save(self, result: CalculationResult) -> None:
        self._store[result.calculation.calculation_id] = result

    def get_by_id(self, calculation_id: str) -> CalculationResult | None:
        return self._store.get(calculation_id)


class InMemoryAuditLogRepository(AuditLogRepository):
    def __init__(self) -> None:
        self._store: dict[str, list[CalculationAudit]] = {}

    def record(self, audit: CalculationAudit) -> None:
        self._store.setdefault(audit.calculation_id, []).append(audit)

    def get_by_calculation_id(self, calculation_id: str) -> list[CalculationAudit]:
        return list(self._store.get(calculation_id, []))
