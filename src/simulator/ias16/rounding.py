"""Rounding reconciliation for multi-period schedules.

Rounding policy (approved, decision 7 and Phase 3 condition 2):
1. The engine calculates with exact fractions.
2. Each posted journal entry is rounded half-up to 2 decimals, and ledger balances
   are the sum of posted entries, so every ledger balance is in cents.
3. Each period re-derives its charge from the POSTED carrying amount:
       charge = (posted carrying amount - residual) x months / remaining months
   so any rounding left in the ledger is spread over the remaining months, not
   accumulated.
4. In the final period, months = remaining months, so the charge is exactly the
   remaining depreciable amount. That amount is already in cents (a difference of
   two cent amounts), so rounding changes nothing and the asset closes at exactly
   its residual value.

This module shows, period by period, how far the posted ledger is from the
unrounded (exact) path, so no cumulative difference is left unexplained.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from fractions import Fraction

from simulator.models import PeriodDepreciation


@dataclass(frozen=True)
class RoundingRow:
    period_end: date
    posted_depreciation: Decimal              # what the journal entries record
    exact_depreciation: Fraction              # same periods, with no rounding anywhere
    cumulative_posted: Decimal
    cumulative_exact: Fraction
    cumulative_difference: Fraction           # posted - exact, explained by cent rounding only
    closing_carrying_amount: Decimal


def rounding_reconciliation(periods: tuple[PeriodDepreciation, ...]) -> tuple[RoundingRow, ...]:
    """Re-run the same segments with exact (unrounded) balances and compare with the ledger."""
    if not periods:
        return ()
    cost = Fraction(periods[0].cost)
    exact_accumulated = Fraction(periods[0].opening_accumulated_depreciation)
    cumulative_posted = Decimal("0.00")
    cumulative_exact = Fraction(0)
    rows = []
    for pd in periods:
        period_exact = Fraction(0)
        for seg in pd.segments:
            depreciable = max(Fraction(0), cost - exact_accumulated - Fraction(seg.residual_value))
            amount = depreciable * seg.months / seg.remaining_life_months
            exact_accumulated += amount
            period_exact += amount
        cumulative_posted += pd.depreciation
        cumulative_exact += period_exact
        rows.append(RoundingRow(
            period_end=pd.period_end, posted_depreciation=pd.depreciation, exact_depreciation=period_exact,
            cumulative_posted=cumulative_posted, cumulative_exact=cumulative_exact,
            cumulative_difference=Fraction(cumulative_posted) - cumulative_exact,
            closing_carrying_amount=pd.closing_carrying_amount,
        ))
    return tuple(rows)
