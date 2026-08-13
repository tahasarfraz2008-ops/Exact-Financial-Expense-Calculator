"""
Database engine/session setup.

WHAT IS IT?
-----------
SQLAlchemy engine, session factory, and ORM table definitions for
persisting calculations and audit entries.

WHY DO WE NEED IT?
------------------
Section 18 asks for MySQL persistence. SQLAlchemy is used as a thin,
well-understood layer over the DB-API driver so that:
  * The same table definitions work against MySQL in production and
    SQLite in local development/tests (no MySQL server required just
    to run the test suite), simply by changing the connection URL.
  * We are not hand-writing raw SQL string concatenation anywhere,
    which removes a whole class of SQL-injection risk.

WHY STORE numerator/denominator INSTEAD OF A DECIMAL COLUMN?
---------------------------------------------------------------
This is the single most important persistence decision in this
project (Section 18 asks it to be explained explicitly):

  Storing only a rounded DECIMAL(x, y) column as "the" result would
  bake a lossy approximation into the system of record. Anyone who
  later reads `33.33` back out of the database has permanently lost
  the fact that the true value was `100/3` -- there is no way to
  recover `100` from `33.33 * 3` read back from storage, for exactly
  the same reason described in the README's core problem statement.

  Storing the numerator and denominator as separate big-integer /
  string columns instead means the exact rational value can always be
  reconstructed losslessly (`Fraction(numerator, denominator)`), no
  matter how many decimal digits it would take to display it.

  ADVANTAGES:
    - No information is ever lost, no matter how a value is later
      displayed, rounded, or recombined with other values.
    - Multiple settlement/rounding views can be derived on demand from
      the same stored exact value, rather than being locked into
      whatever rounding happened at write time.

  DISADVANTAGES:
    - Numerators/denominators for deeply nested calculations can grow
      to many digits, using more storage than a fixed DECIMAL column
      (mitigated here by storing them as TEXT/VARCHAR rather than a
      fixed-width integer type, and by an `OverflowFinancialError`
      safety bound in the domain layer for pathological inputs).
    - Every consumer of the stored value must explicitly decide how to
      display or round it -- there is no single "the" decimal value
      sitting in the column ready to use as-is. This is treated here
      as a feature, not a bug: it forces the same explicit
      display/rounding step this whole engine is built around.

HOW DOES IT WORK?
------------------
`get_engine(database_url)` builds a SQLAlchemy engine. When no URL is
supplied, it defaults to a local SQLite file so the project runs with
zero external setup; supply a `mysql+pymysql://user:pass@host/db` URL
(see README "Database setup") to point the same code at real MySQL.
"""

from __future__ import annotations

import os

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, create_engine
from sqlalchemy.engine import Engine

metadata = MetaData()

calculations_table = Table(
    "calculations",
    metadata,
    Column("calculation_id", String(36), primary_key=True),
    Column("expression", String(2000), nullable=False),
    Column("exact_numerator", String(4000), nullable=False),
    Column("exact_denominator", String(4000), nullable=False),
    Column("display_digits", Integer, nullable=False),
    Column("displayed_result", String(200), nullable=False),
    Column("is_repeating", Integer, nullable=False),  # 0/1 -- MySQL BOOLEAN is TINYINT anyway
    Column("created_at", DateTime, nullable=False),
)

audit_logs_table = Table(
    "audit_logs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("calculation_id", String(36), nullable=False),
    Column("timestamp", DateTime, nullable=False),
    Column("input_expression", String(2000), nullable=False),
    Column("exact_result", String(4000), nullable=False),
    Column("displayed_result", String(200), nullable=False),
    Column("display_digits", Integer, nullable=False),
    Column("is_repeating", Integer, nullable=False),
    Column("user_or_system_id", String(200), nullable=False),
    Column("rounding_policy_name", String(50), nullable=True),
)

# Reference tables described in the spec (Section 18). Kept intentionally
# simple: currencies mirror the domain registry, rounding_policies mirror
# the RoundingPolicy enum, and calculation_operations records the
# individual +,-,*,/ steps of a parsed expression for deep audit needs.

currencies_table = Table(
    "currencies",
    metadata,
    Column("code", String(10), primary_key=True),
    Column("decimal_places", Integer, nullable=False),
    Column("name", String(200), nullable=False),
)

rounding_policies_table = Table(
    "rounding_policies",
    metadata,
    Column("name", String(50), primary_key=True),
    Column("decimal_constant", String(50), nullable=False),
)

calculation_operations_table = Table(
    "calculation_operations",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("calculation_id", String(36), nullable=False),
    Column("sequence_number", Integer, nullable=False),
    Column("operator", String(10), nullable=False),
    Column("operand_numerator", String(4000), nullable=False),
    Column("operand_denominator", String(4000), nullable=False),
)


def get_default_database_url() -> str:
    """Read DATABASE_URL from the environment, defaulting to a local
    SQLite file so the project runs with zero external setup. Example
    MySQL URL: mysql+pymysql://user:password@localhost:3306/financial_engine
    """
    return os.environ.get("DATABASE_URL", "sqlite:///exact_financial_engine.db")


def get_engine(database_url: str | None = None) -> Engine:
    engine = create_engine(database_url or get_default_database_url(), future=True)
    metadata.create_all(engine)
    return engine
