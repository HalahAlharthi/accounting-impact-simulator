"""Exact money arithmetic.

Why not float?  Floats are binary approximations: 0.1 + 0.2 == 0.30000000000000004.
That is unacceptable in accounting.

How we calculate (approved decision 7):
- Inputs are Decimal amounts (e.g. Decimal("100000.00")).
- Intermediate results are Python Fractions, which are *exact* rational numbers.
  58,500 / 54 is stored as the fraction 3250/3, not as 1083.3333...
- Rounding happens only when an amount is posted (a journal entry) or displayed:
  to 2 decimal places, ROUND HALF UP (0.005 -> 0.01).
"""
from __future__ import annotations

from decimal import Decimal
from fractions import Fraction

CENT = Fraction(1, 100)


def to_fraction(value: Decimal | int | Fraction) -> Fraction:
    """Convert a Decimal/int to an exact Fraction (no precision is lost)."""
    if isinstance(value, Fraction):
        return value
    return Fraction(value)


def round_half_up(value: Fraction | Decimal | int, places: int) -> Decimal:
    """Round an exact value half-up (away from zero at exactly .5) to `places` decimals.

    Implemented with integer arithmetic so the result is exact and
    reproducible on every machine.
    """
    frac = to_fraction(value)
    sign = -1 if frac < 0 else 1
    scaled = abs(frac) * 10**places
    whole, remainder = divmod(scaled.numerator, scaled.denominator)
    if remainder * 2 >= scaled.denominator:  # half or more rounds up
        whole += 1
    return Decimal(sign * whole).scaleb(-places).quantize(Decimal(1).scaleb(-places))


def round_money(value: Fraction | Decimal | int) -> Decimal:
    """Round an exact amount to cents, half-up: the rule for every posted amount."""
    return round_half_up(value, 2)


def fmt(value: Fraction | Decimal | int) -> str:
    """Human-readable money string, e.g. 7571.428571... -> '7,571.43'."""
    return f"{round_money(value):,.2f}"
