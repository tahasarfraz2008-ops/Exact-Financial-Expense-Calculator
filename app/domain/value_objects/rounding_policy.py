"""
RoundingPolicy -- an explicit, named rounding rule.

WHAT IS IT?
-----------
A small enum-backed value object wrapping Python's `decimal` rounding
modes (`ROUND_HALF_UP`, `ROUND_HALF_EVEN`, `ROUND_DOWN`, `ROUND_UP`,
`ROUND_FLOOR`, `ROUND_CEILING`). It exists so that "how do we round
this value" is always a named, explicit choice passed into a function
-- never an implicit default buried in a library call.

WHY DO WE NEED IT?
------------------
Different banking business rules require different rounding behaviour.
Regulatory interest calculations often mandate ROUND_HALF_UP. Some
accounting systems require ROUND_HALF_EVEN ("banker's rounding") to
avoid systematic bias when rounding many values. A settlement/payout
step might need ROUND_DOWN so a system never pays out more than it
holds. If rounding mode were hard-coded, none of these business rules
could be satisfied, and worse, a wrong default could silently apply
the wrong rule to real money.

HOW DOES IT WORK?
------------------
`RoundingPolicy` is an `Enum` whose members map 1:1 to `decimal`
module constants. `RoundingPolicy.apply(...)` is the *only* sanctioned
way to round an `ExactNumber`/`Fraction` value in this codebase --
see `app.domain.services.rounding_service` for the actual rounding
logic and the `RoundingResult` that records the before/after/difference
triple required by the spec.

WHY THIS TECHNOLOGY?
---------------------
Python's built-in `decimal.ROUND_*` constants are the industry-standard
implementations of these exact rounding rules and are already
correctly implemented and tested by the standard library -- there is
no reason to reinvent them.
"""

from __future__ import annotations

from decimal import (
    ROUND_CEILING,
    ROUND_DOWN,
    ROUND_FLOOR,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    ROUND_UP,
)
from enum import Enum

from app.domain.exceptions.financial_exceptions import InvalidRoundingModeError


class RoundingPolicy(Enum):
    """Supported, explicitly-named rounding modes."""

    HALF_UP = ROUND_HALF_UP
    HALF_EVEN = ROUND_HALF_EVEN
    DOWN = ROUND_DOWN
    UP = ROUND_UP
    FLOOR = ROUND_FLOOR
    CEILING = ROUND_CEILING

    @staticmethod
    def from_name(name: str) -> "RoundingPolicy":
        """Look up a policy by its name (case-insensitive), e.g. 'half_up'."""
        normalized = name.strip().upper()
        try:
            return RoundingPolicy[normalized]
        except KeyError as exc:
            supported = ", ".join(p.name for p in RoundingPolicy)
            raise InvalidRoundingModeError(
                f"'{name}' is not a supported rounding mode. Supported: {supported}."
            ) from exc

    @property
    def decimal_constant(self) -> str:
        """The underlying `decimal` module rounding constant string."""
        return self.value
