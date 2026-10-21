"""Multi-year rounding tests (Phase 3 condition 2).

T23 hand derivation (independent of the code):
  Exact straight-line charge  = 53,000 / 7 = 7,571.428571... per year.
  Posted charge (years 1-6)   = 7,571.43, so after k years the ledger is ahead by
      k x (7,571.43 - 53,000/7) = k x (5,300,001 - 5,300,000) / 700 = k / 700.
  Year 7 has 12 months left out of 12 remaining, so it charges the whole remaining
  depreciable amount: 27,571.42 - 20,000 = 7,571.42 (already in cents; no rounding).
  Closing carrying amount = 20,000.00 exactly; total = 73,000 - 20,000 = 53,000.00.
"""
from datetime import date
from decimal import Decimal as D
from fractions import Fraction

from _builders import ReportingPeriod, case_b, make_input
from simulator.ias16 import project_revised_schedule
from simulator.ias16.rounding import rounding_reconciliation


def test_t23_year_by_year_hand_figures():
    sched = project_revised_schedule(make_input(revised_residual=D("20000")), 7)
    rows = rounding_reconciliation(sched.periods)
    closing = [r.closing_carrying_amount for r in rows]
    assert closing == [D("65428.57"), D("57857.14"), D("50285.71"), D("42714.28"),
                       D("35142.85"), D("27571.42"), D("20000.00")]
    diffs = [r.cumulative_difference for r in rows]
    assert diffs == [Fraction(k, 700) for k in range(1, 7)] + [Fraction(0)]
    assert rows[-1].cumulative_posted == D("53000.00")
    assert rows[-1].cumulative_exact == 53000


def _invariants(inp, periods_to_run, expected_final_carrying):
    sched = project_revised_schedule(inp, periods_to_run)
    assert sched.ok, [i.message for i in sched.issues if i.severity.value == "error"]
    periods = sched.periods
    # 1. Continuity: each period opens with the previous period's posted closing balance.
    for prev, nxt in zip(periods, periods[1:]):
        assert nxt.opening_accumulated_depreciation == prev.closing_accumulated_depreciation
    # 2. Every ledger figure is in cents.
    for pd in periods:
        assert pd.closing_accumulated_depreciation == pd.closing_accumulated_depreciation.quantize(D("0.01"))
    # 3. Total posted = opening carrying amount - final carrying amount, exactly.
    total = sum(pd.depreciation for pd in periods)
    assert total == periods[0].opening_carrying_amount - periods[-1].closing_carrying_amount
    # 4. The asset ends exactly at its (revised) residual value.
    assert periods[-1].closing_carrying_amount == expected_final_carrying
    # 5. The ledger never drifts more than half a cent per posting from the exact path, and ends with no difference.
    rows = rounding_reconciliation(periods)
    postings = 0
    for pd, row in zip(periods, rows):
        postings += len(pd.segments)
        assert abs(row.cumulative_difference) <= Fraction(5, 1000) * postings
    assert rows[-1].cumulative_difference == 0
    return periods


def test_case_b_to_end_of_life():
    # Revised life 96 months from Jan 2022 ends Dec 2029: five periods 2025-2029, then nothing.
    periods = _invariants(case_b(), 6, D("10000.00"))
    assert periods[-1].depreciation == D("0.00")
    assert periods[-2].period_end == date(2029, 12, 31)


def test_t19_override_to_end_of_life():
    _invariants(make_input(revised_life=96, opening_ad=D("30000")), 5, D("10000.00"))


def test_awkward_amounts_and_mid_year_change():
    # Cost 10,000.01, residual 333.33, life 37 months from 1 Jan 2025; revised to 41 months from 1 Mar 2025.
    inp = make_input(cost=D("10000.01"), residual=D("333.33"), life=37, available=date(2025, 1, 1),
                     opening_ad=D("0"), change_date=date(2025, 3, 1), revised_life=41)
    _invariants(inp, 4, D("333.33"))


def test_awkward_amounts_non_annual_period():
    # Quarterly periods: cost 1,000.00, residual 0, opening 300.00, revised life 97 months from 1 Nov 2025.
    quarter = ReportingPeriod(date(2025, 10, 1), date(2025, 12, 31))
    inp = make_input(cost=D("1000.00"), residual=D("0"), opening_ad=D("300.00"), period=quarter,
                     change_date=date(2025, 11, 1), revised_life=97)
    _invariants(inp, 20, D("0.00"))
