"""
Repository and audit-logger interfaces (ports).

WHAT ARE THEY?
--------------
Abstract base classes describing *what* persistence operations the
application needs ("save this calculation," "fetch a calculation by
id," "record this audit entry") without saying *how* they are
implemented (SQLite for local dev, MySQL for production, or an
in-memory dict for tests).

WHY DO WE NEED THEM?
---------------------
This is the Dependency Inversion half of SOLID and the core mechanism
of Clean Architecture's "infrastructure depends on application, not
the other way around" rule. Use cases in `app/application/use_cases`
depend only on these interfaces, never on a concrete database driver.
That means:
  * Tests can supply a trivial in-memory fake instead of a real MySQL
    server.
  * Swapping MySQL for another database later touches only the
    `app/infrastructure` layer, not the use cases.

HOW DO THEY WORK?
------------------
Standard Python `abc.ABC` + `@abstractmethod`. Concrete
implementations live in `app/infrastructure/repositories` and
`app/infrastructure/logging`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.calculation import CalculationAudit, CalculationResult


class CalculationRepository(ABC):
    """Persists and retrieves calculation results."""

    @abstractmethod
    def save(self, result: CalculationResult) -> None: ...

    @abstractmethod
    def get_by_id(self, calculation_id: str) -> CalculationResult | None: ...


class AuditLogRepository(ABC):
    """Persists audit trail entries for financial calculations."""

    @abstractmethod
    def record(self, audit: CalculationAudit) -> None: ...

    @abstractmethod
    def get_by_calculation_id(self, calculation_id: str) -> list[CalculationAudit]: ...
