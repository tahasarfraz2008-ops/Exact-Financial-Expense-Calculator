"""
Application logging configuration.

WHAT IS IT?
-----------
Standard Python `logging` setup for operational logs (startup, request
handling, errors) -- distinct from the `CalculationAudit` financial
audit trail, which is domain data, not a log line.

WHY DO WE NEED IT?
------------------
It is important not to conflate "operational logging" (useful for
debugging and ops, safe to rotate/discard) with "financial audit
trail" (a regulatory/business record that must be queryable and
retained). Keeping them as two separate concerns, in two separate
modules, avoids a common real-world mistake where an audit trail ends
up scattered across unstructured log files instead of living in a
proper, queryable store (`app/infrastructure/repositories`).

HOW DOES IT WORK?
------------------
A single `configure_logging()` call sets a sane root-logger format;
application code gets loggers via `logging.getLogger(__name__)` as
usual.
"""

from __future__ import annotations

import logging


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
