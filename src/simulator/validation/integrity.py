"""Integrity checks on calculated results.

These re-check the engine's own output from first principles. They NEVER fix
anything: a failed check returns an error describing both sides and the
difference, and the result is withheld. No balancing figure ("plug") is ever
created — not in equity, not in any other account.

V12 — arithmetic/reconciliation integrity of one scenario.
V13 — opening balances must be identical in baseline and scenario (the
      prospective-treatment guard: a change in estimate never touches opening
      balances; IAS 8.36–38, corroborated via AASB 108, IFRS primary text pending).
"""
from __future__ import annotations

from decimal import Decimal

from simulator.models import PeriodDepreciation, Severity, ValidationIssue
from simulator.money import round_money
from simulator.periods import months_in_range


def _err(code: str, message: str, fix: str | None = None) -> ValidationIssue:
    return ValidationIssue(code=code, severity=Severity.ERROR, message=message, fix=fix)


def check_opening_balances_identical(baseline: PeriodDepreciation,
                                     scenario: PeriodDepreciation) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    pairs = {
        "cost": (baseline.cost, scenario.cost),
        "opening accumulated depreciation": (baseline.opening_accumulated_depreciation,
                                             scenario.opening_accumulated_depreciation),
        "opening carrying amount": (baseline.opening_carrying_amount, scenario.opening_carrying_amount),
        "period start": (baseline.period_start, scenario.period_start),
    }
    for name, (b, s) in pairs.items():
        if b != s:
            diff = f"; difference {s - b}" if isinstance(b, Decimal) else ""
            issues.append(_err("V13", f"Opening {name} differs between baseline ({b}) and scenario ({s}){diff}. "
                                      "A change in estimate is prospective and must not alter opening balances.",
                               "Check the opening inputs; nothing has been adjusted."))
    return issues


def check_period_arithmetic(pd: PeriodDepreciation) -> list[ValidationIssue]:
    """Recompute each segment from its own inputs and reconcile the period totals."""
    issues: list[ValidationIssue] = []
    label = f"[{pd.scenario}]"
    running_ad = pd.opening_accumulated_depreciation
    total_months = 0

    for i, seg in enumerate(pd.segments, start=1):
        expected_ca = pd.cost - running_ad
        if seg.carrying_amount_at_start != expected_ca:
            issues.append(_err("V12", f"{label} Segment {i}: carrying amount at start is {seg.carrying_amount_at_start}"
                                      f" but cost - accumulated depreciation = {expected_ca}; difference "
                                      f"{seg.carrying_amount_at_start - expected_ca}."))
        expected_depreciable = max(Decimal("0"), seg.carrying_amount_at_start - seg.residual_value)
        if seg.remaining_depreciable_amount != expected_depreciable:
            issues.append(_err("V12", f"{label} Segment {i}: remaining depreciable amount is "
                                      f"{seg.remaining_depreciable_amount}, expected {expected_depreciable}."))
        if seg.remaining_life_months > 0:
            expected_exact = seg.monthly_rate_exact * seg.months
            if seg.exact_depreciation != expected_exact:
                issues.append(_err("V12", f"{label} Segment {i}: exact depreciation does not equal "
                                          "remaining depreciable amount x months / remaining life."))
        if seg.depreciation != round_money(seg.exact_depreciation):
            issues.append(_err("V12", f"{label} Segment {i}: posted amount {seg.depreciation} is not the exact "
                                      f"amount rounded half-up ({round_money(seg.exact_depreciation)})."))
        if seg.months != months_in_range(seg.start_date, seg.end_date):
            issues.append(_err("V12", f"{label} Segment {i}: {seg.months} months does not match its dates."))
        running_ad += seg.depreciation
        total_months += seg.months

    period_months = months_in_range(pd.period_start, pd.period_end)
    if total_months > period_months:
        issues.append(_err("V12", f"{label} Segments cover {total_months} months but the period has {period_months}."))
    if running_ad != pd.closing_accumulated_depreciation:
        issues.append(_err("V12", f"{label} Closing accumulated depreciation {pd.closing_accumulated_depreciation} "
                                  f"does not reconcile to opening + segment postings ({running_ad})."))
    if pd.closing_carrying_amount < 0:
        issues.append(_err("V12", f"{label} Closing carrying amount is negative ({pd.closing_carrying_amount})."))
    return issues
