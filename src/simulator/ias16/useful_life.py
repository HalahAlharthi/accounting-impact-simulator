"""IAS 16 straight-line depreciation with a prospective change in estimate (IAS 8).

The accounting in four lines (Phase 1, section 2). At the date of the change E:

    carrying amount at E          = cost - accumulated depreciation at E
    remaining depreciable amount  = max(0, carrying amount at E - revised residual value)
    remaining life (months)       = revised TOTAL life - months elapsed since available for use
    depreciation for n months     = remaining depreciable amount x n / remaining life

Months before E use the original estimate; months from E use the revised one.
Depreciation already recorded before E is never recalculated, and nothing is
posted to opening retained earnings (prospective treatment).

The baseline uses the same formula with the original estimate throughout
(Phase 1 assumption F8). When opening balances agree with the original
estimate, this gives exactly the original straight-line charge.

References carry their verification status; see simulator/references.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

from simulator.models import (
    EstimateRevision,
    PeriodDepreciation,
    ReportingPeriod,
    Segment,
    Severity,
    SimulationInput,
    SimulationResult,
    TraceStep,
    ValidationIssue,
)
from simulator.money import fmt, round_money
from simulator.periods import add_months, end_of_month, month_index, months_between, months_in_range
from simulator.references import label as ref
from simulator.validation import (
    check_opening_balances_identical,
    check_period_arithmetic,
    normalize_simulation_input,
    validate_inputs,
)

ZERO = Decimal("0.00")


# --------------------------------------------------------------------------- #
# Building blocks
# --------------------------------------------------------------------------- #


def implied_opening_accumulated_depreciation(cost: Decimal, residual_value: Decimal, useful_life_months: int,
                                             available_for_use_date, period_start) -> Decimal:
    """Accumulated depreciation the ORIGINAL estimate implies at the start of the period.

    Used (a) when the user leaves opening accumulated depreciation blank, and
    (b) to warn when the user's figure differs (V08). It never replaces a figure
    the user entered.
    """
    elapsed = max(0, months_between(available_for_use_date, period_start))
    used = min(elapsed, useful_life_months)
    return round_money(Fraction(cost - residual_value) * used / useful_life_months)


def _segment(*, estimate_label: str, start, end_exclusive_index: int, cost: Decimal,
             accumulated_at_start: Decimal, available_for_use_date, useful_life_months: int,
             residual_value: Decimal) -> tuple[Segment | None, list[TraceStep]]:
    """Depreciate from `start` up to (not including) the month `end_exclusive_index`.

    Months are capped at the remaining life, so an asset that reaches the end of
    its life inside the period stops depreciating there.
    """
    months_available = end_exclusive_index - month_index(start)
    elapsed = months_between(available_for_use_date, start)
    remaining_life = useful_life_months - elapsed
    months = max(0, min(months_available, remaining_life))
    if months == 0:
        return None, []

    carrying = cost - accumulated_at_start
    depreciable = max(ZERO, carrying - residual_value)       # IAS 16.53/16.54: never negative
    exact = Fraction(depreciable) * months / remaining_life  # multiply before dividing: exact
    end_date = end_of_month(add_months(start, months - 1))

    seg = Segment(
        estimate_label=estimate_label, start_date=start, end_date=end_date, months=months,
        carrying_amount_at_start=carrying, residual_value=Decimal(residual_value),
        remaining_life_months=remaining_life, remaining_depreciable_amount=depreciable,
        exact_depreciation=exact, depreciation=round_money(exact),
    )
    span = f"{start:%b %Y}–{end_date:%b %Y}"
    trace = [
        TraceStep(f"Carrying amount at {start:%d %b %Y}", "cost − accumulated depreciation",
                  f"{fmt(cost)} − {fmt(accumulated_at_start)}", fmt(carrying), (ref("IAS 16.6"),)),
        TraceStep(f"Remaining useful life at {start:%d %b %Y} ({estimate_label})",
                  "total useful life − months elapsed since available for use",
                  f"{useful_life_months} − {elapsed}", f"{remaining_life} months"),
        TraceStep("Remaining depreciable amount", "max(0, carrying amount − residual value)",
                  f"max(0, {fmt(carrying)} − {fmt(residual_value)})", fmt(depreciable),
                  (ref("IAS 16.53"), ref("IAS 16.54"))),
        TraceStep(f"Depreciation {span} ({estimate_label})",
                  "remaining depreciable amount × months ÷ remaining life",
                  f"{fmt(depreciable)} × {months} ÷ {remaining_life}",
                  f"{fmt(exact)} (exact value {exact}, posted rounded half-up)", (ref("IAS 16.50"),)),
    ]
    return seg, trace


def depreciate_period(*, scenario: str, cost: Decimal, opening_accumulated_depreciation: Decimal,
                      available_for_use_date, period: ReportingPeriod, useful_life_months: int,
                      residual_value: Decimal, change: EstimateRevision | None = None
                      ) -> tuple[PeriodDepreciation, list[ValidationIssue]]:
    """Depreciation for one period. `change=None` gives the baseline."""
    issues: list[ValidationIssue] = []
    depreciation_start = max(period.start_date, available_for_use_date)  # IAS 16.55
    period_end_exclusive = month_index(period.end_date) + 1

    revised_life = useful_life_months
    revised_residual = residual_value
    plan: list[tuple[str, object, int, int, Decimal]] = []
    if change is None:
        plan.append(("original estimate", depreciation_start, period_end_exclusive, useful_life_months, residual_value))
    else:
        revised_life = change.revised_useful_life_months or useful_life_months
        revised_residual = (change.revised_residual_value if change.revised_residual_value is not None
                            else residual_value)
        if change.effective_date > depreciation_start:  # months before the change keep the old rate
            plan.append(("original estimate", depreciation_start, month_index(change.effective_date),
                         useful_life_months, residual_value))
        plan.append(("revised estimate", change.effective_date, period_end_exclusive, revised_life, revised_residual))

    segments: list[Segment] = []
    trace: list[TraceStep] = []
    accumulated = Decimal(opening_accumulated_depreciation)
    for est_label, start, end_excl, life, residual in plan:
        seg, steps = _segment(estimate_label=est_label, start=start, end_exclusive_index=end_excl, cost=cost,
                              accumulated_at_start=accumulated, available_for_use_date=available_for_use_date,
                              useful_life_months=life, residual_value=residual)
        if seg is None:
            continue
        if seg.remaining_depreciable_amount == 0:
            issues.append(ValidationIssue(
                "V09", Severity.INFO,
                f"[{scenario}] From {seg.start_date:%d %b %Y}, residual value ({fmt(seg.residual_value)}) is equal to "
                f"or greater than carrying amount ({fmt(seg.carrying_amount_at_start)}), so depreciation is zero "
                f"until residual value falls below carrying amount. No negative depreciation is recognised. "
                f"Reference: {ref('IAS 16.54')}.",
                "residual_value", "Check that the residual value estimate is supportable."))
        segments.append(seg)
        trace.extend(steps)
        accumulated += seg.depreciation

    result = PeriodDepreciation(
        scenario=scenario, period_start=period.start_date, period_end=period.end_date, cost=Decimal(cost),
        opening_accumulated_depreciation=Decimal(opening_accumulated_depreciation), segments=tuple(segments),
        useful_life_months_after=revised_life, residual_value_after=Decimal(revised_residual), trace=tuple(trace),
    )
    return result, issues


# --------------------------------------------------------------------------- #
# Public entry points
# --------------------------------------------------------------------------- #


def simulate(inp: SimulationInput) -> SimulationResult:
    """Convert inputs to exact types, validate, then calculate baseline and revised depreciation."""
    inp, conversion_issues = normalize_simulation_input(inp)  # floats/strings -> Decimal, at the boundary
    if conversion_issues:
        return SimulationResult(issues=tuple(conversion_issues))
    issues = validate_inputs(inp)
    if any(i.severity is Severity.ERROR for i in issues):
        return SimulationResult(issues=tuple(issues))

    a, p = inp.asset, inp.period
    cost, residual = Decimal(a.cost), Decimal(a.residual_value)
    implied = implied_opening_accumulated_depreciation(cost, residual, a.useful_life_months,
                                                       a.available_for_use_date, p.start_date)

    if inp.opening_accumulated_depreciation is None:
        opening, source = implied, "calculated"
        issues.append(ValidationIssue(
            "V20", Severity.INFO,
            f"Opening accumulated depreciation was not entered. {fmt(implied)} has been CALCULATED from the original "
            f"estimate; it has not been verified against the ledger.",
            "opening_accumulated_depreciation",
            "Enter the balance from the fixed-asset register to use the actual ledger figure."))
    else:
        opening, source = Decimal(inp.opening_accumulated_depreciation), "entered"  # used as entered (decision 4)
        if opening != implied:
            issues.append(ValidationIssue(
                "V08", Severity.WARNING,
                f"Opening accumulated depreciation ({fmt(opening)}) differs from the amount implied by the original "
                f"estimate ({fmt(implied)}) by {fmt(opening - implied)}. Possible causes: an earlier revision, an "
                f"impairment, or input error. Calculations use your figure: opening carrying amount is "
                f"{fmt(cost - opening)} (implied path: {fmt(cost - implied)}). No correcting entry is generated.",
                "opening_accumulated_depreciation",
                "Confirm the figure against the fixed-asset register."))

    common = dict(cost=cost, opening_accumulated_depreciation=opening,
                  available_for_use_date=a.available_for_use_date, period=p,
                  useful_life_months=a.useful_life_months, residual_value=residual)
    baseline, b_issues = depreciate_period(scenario="baseline", **common)
    scenario, s_issues = depreciate_period(scenario="revised", change=inp.revision, **common)
    issues += b_issues + s_issues

    integrity = (check_opening_balances_identical(baseline, scenario)
                 + check_period_arithmetic(baseline) + check_period_arithmetic(scenario))
    if integrity:  # withhold numbers; never adjust them
        return SimulationResult(issues=tuple(issues + integrity), implied_opening_accumulated_depreciation=implied,
                                opening_balance_source=source)

    if scenario.depreciation == baseline.depreciation:
        issues.append(ValidationIssue(
            "V21", Severity.WARNING,
            f"The revision produces no change in depreciation for this period (both {fmt(baseline.depreciation)}). "
            f"Baseline and scenario are still shown for comparison.", "revision",
            "Check the revised useful life, residual value and change date."))

    return SimulationResult(issues=tuple(issues), baseline=baseline, scenario=scenario,
                            implied_opening_accumulated_depreciation=implied, opening_balance_source=source)


@dataclass(frozen=True)
class ScheduleResult:
    issues: tuple[ValidationIssue, ...]
    periods: tuple[PeriodDepreciation, ...] = ()

    @property
    def ok(self) -> bool:
        return not any(i.severity is Severity.ERROR for i in self.issues)


def project_revised_schedule(inp: SimulationInput, number_of_periods: int) -> ScheduleResult:
    """Run the revised scenario forward for several consecutive periods of the same length.

    Each period opens with the previous period's POSTED (rounded) balances, as a
    ledger would, so cent-level rounding is absorbed automatically in later
    periods and the asset ends exactly at its residual value (T23).
    """
    first = simulate(inp)
    if not first.ok:
        return ScheduleResult(issues=first.issues)
    inp, _ = normalize_simulation_input(inp)  # already validated by simulate(); exact types from here

    months = months_in_range(inp.period.start_date, inp.period.end_date)
    periods = [first.scenario]
    issues = list(first.issues)
    for _ in range(number_of_periods - 1):
        prev = periods[-1]
        start = add_months(prev.period_start, months)
        next_period = ReportingPeriod(start, end_of_month(add_months(start, months - 1)))
        pd, p_issues = depreciate_period(
            scenario="revised", cost=prev.cost, opening_accumulated_depreciation=prev.closing_accumulated_depreciation,
            available_for_use_date=inp.asset.available_for_use_date, period=next_period,
            useful_life_months=prev.useful_life_months_after, residual_value=prev.residual_value_after)
        integrity = check_period_arithmetic(pd)
        if integrity:
            return ScheduleResult(issues=tuple(issues + p_issues + integrity), periods=tuple(periods))
        issues += p_issues
        periods.append(pd)
    return ScheduleResult(issues=tuple(issues), periods=tuple(periods))
