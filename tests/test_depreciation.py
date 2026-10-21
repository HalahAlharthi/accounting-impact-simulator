"""Depreciation engine tests. Expected values are the approved Phase 1 hand calculations."""
from datetime import date
from decimal import Decimal as D

from _builders import case_a, case_b, make_input
from simulator.ias16 import project_revised_schedule, simulate


def _amounts(segments):
    return [s.depreciation for s in segments]


# T01 — zero residual value. 50,000 / 60 x 12 = 10,000
def test_t01_zero_residual_value():
    r = simulate(make_input(cost=D("50000"), residual=D("0"), life=60, available=date(2025, 1, 1),
                            opening_ad=D("0"), revised_life=60))  # revision changes nothing -> V21 warning
    assert r.ok
    assert r.baseline.depreciation == D("10000.00")
    assert r.baseline.closing_carrying_amount == D("40000.00")


# T02 — residual value > 0, no change. 90,000 / 120 x 12 = 9,000
def test_t02_residual_above_zero_no_change():
    r = simulate(make_input(revised_life=120))
    assert r.ok
    assert r.baseline.depreciation == D("9000.00")
    assert r.scenario.depreciation == D("9000.00")
    assert "V21" in r.codes()  # warned: no change in depreciation
    assert r.ok  # a warning, not an error: comparison still shown


def test_v21_not_raised_when_depreciation_changes():
    assert "V21" not in simulate(case_a()).codes()


# T05 — Case A. Baseline 63,000 x 12 / 84 = 9,000; revised 63,000 x 12 / 60 = 12,600
def test_t05_case_a_revision_with_accumulated_depreciation():
    r = simulate(case_a())
    assert r.ok
    assert r.baseline.depreciation == D("9000.00")
    assert r.scenario.depreciation == D("12600.00")
    assert r.baseline.closing_carrying_amount == D("64000.00")
    assert r.scenario.closing_carrying_amount == D("60400.00")
    assert r.change_in_depreciation == D("3600.00")
    seg = r.scenario.segments[0]
    assert (seg.remaining_life_months, seg.remaining_depreciable_amount) == (60, D("63000"))
    assert seg.monthly_rate_exact == 1050


# T06 — Case B. 6 x 750 = 4,500; 58,500 x 6 / 54 = 6,500; total 11,000; closing 62,000
def test_t06_mid_period_revision():
    r = simulate(case_b())
    assert r.ok
    first, second = r.scenario.segments
    assert first.depreciation == D("4500.00")
    assert second.carrying_amount_at_start == D("68500.00")
    assert second.remaining_depreciable_amount == D("58500.00")
    assert second.remaining_life_months == 54
    assert second.depreciation == D("6500.00")
    assert r.scenario.depreciation == D("11000.00")
    assert r.scenario.closing_carrying_amount == D("62000.00")
    assert r.baseline.depreciation == D("9000.00")
    assert r.change_in_depreciation == D("2000.00")


# T07 — residual revised to 20,000, life unchanged. 53,000 x 12 / 84 = 7,571.428... -> 7,571.43
def test_t07_residual_revision_rounding():
    r = simulate(make_input(revised_residual=D("20000")))
    assert r.ok
    assert r.scenario.depreciation == D("7571.43")
    assert r.scenario.segments[0].exact_depreciation * 7 == 53000  # exact value kept, unrounded


# T08 — prospective guard: opening balances untouched, no catch-up in the period total
def test_t08_prospective_treatment():
    r = simulate(case_a())
    for pd in (r.baseline, r.scenario):
        assert pd.opening_accumulated_depreciation == D("27000")
        assert pd.opening_carrying_amount == D("73000")
    # A retrospective method would charge 90,000 x 48/96 - 27,000 = 18,000 in 2025. We must not.
    assert r.scenario.depreciation != D("18000.00")
    assert r.scenario.depreciation == D("12600.00")


# T10 — revised residual 75,000 > carrying amount 73,000 -> zero, V09 info, no negative depreciation
def test_t10_residual_above_carrying_amount():
    r = simulate(make_input(revised_residual=D("75000")))
    assert r.ok
    assert r.scenario.depreciation == D("0.00")
    assert r.scenario.closing_carrying_amount == D("73000.00")
    assert r.scenario.segments[0].remaining_depreciable_amount == D("0")
    assert "V09" in r.codes()
    v09 = next(i for i in r.issues if i.code == "V09")
    assert "IAS 16.54 (confirmed on ifrs.org)" in v09.message


# T10b — boundary: residual exactly equal to carrying amount 73,000 -> zero
def test_t10b_residual_equal_to_carrying_amount():
    r = simulate(make_input(revised_residual=D("73000")))
    assert r.ok
    assert r.scenario.depreciation == D("0.00")
    assert "V09" in r.codes()


# T11 — available 1 Jul 2025, no change: 6 x 750 = 4,500
def test_t11_asset_available_mid_period():
    r = simulate(make_input(available=date(2025, 7, 1), opening_ad=D("0"), change_date=date(2025, 7, 1),
                            revised_life=120))
    assert r.ok
    assert r.baseline.depreciation == D("4500.00")
    assert r.baseline.segments[0].start_date == date(2025, 7, 1)


# T17 — reproducibility
def test_t17_reproducible():
    assert simulate(case_b()) == simulate(case_b())


# T19 — opening accumulated depreciation override 30,000 (implied 27,000)
def test_t19_opening_accumulated_depreciation_override():
    r = simulate(make_input(revised_life=96, opening_ad=D("30000")))
    assert r.ok
    # input kept as entered, implied figure reported alongside, never substituted
    assert r.baseline.opening_accumulated_depreciation == D("30000")
    assert r.scenario.opening_accumulated_depreciation == D("30000")
    assert r.implied_opening_accumulated_depreciation == D("27000.00")
    assert r.baseline.opening_carrying_amount == D("70000")
    # 60,000 x 12 / 84 = 8,571.428... ; 60,000 x 12 / 60 = 12,000
    assert r.baseline.depreciation == D("8571.43")
    assert r.scenario.depreciation == D("12000.00")
    assert r.baseline.closing_carrying_amount == D("61428.57")
    assert r.scenario.closing_carrying_amount == D("58000.00")
    v08 = [i for i in r.warnings if i.code == "V08"]
    assert len(v08) == 1
    assert "30,000.00" in v08[0].message and "27,000.00" in v08[0].message and "3,000.00" in v08[0].message
    assert "No correcting entry" in v08[0].message


# T20 — multiple rate segments in one period (Case B)
def test_t20_two_rate_segments():
    r = simulate(case_b())
    segs = r.scenario.segments
    assert [s.estimate_label for s in segs] == ["original estimate", "revised estimate"]
    assert [s.months for s in segs] == [6, 6]
    assert [(s.start_date, s.end_date) for s in segs] == [
        (date(2025, 1, 1), date(2025, 6, 30)), (date(2025, 7, 1), date(2025, 12, 31))]
    assert _amounts(segs) == [D("4500.00"), D("6500.00")]
    assert sum(_amounts(segs)) == D("11000.00")


# T21 — start of use and revision in the same year
# Apr-Sep 6 x 750 = 4,500; CA 1 Oct 95,500; remaining 60 - 6 = 54; Oct-Dec 85,500 x 3 / 54 = 4,750
def test_t21_available_and_revised_in_same_period():
    r = simulate(make_input(available=date(2025, 4, 1), opening_ad=D("0"), change_date=date(2025, 10, 1),
                            revised_life=60))
    assert r.ok
    assert r.baseline.depreciation == D("6750.00")  # 9 x 750
    first, second = r.scenario.segments
    assert (first.start_date, first.months, first.depreciation) == (date(2025, 4, 1), 6, D("4500.00"))
    assert (second.carrying_amount_at_start, second.remaining_life_months) == (D("95500.00"), 54)
    assert (second.months, second.depreciation) == (3, D("4750.00"))
    assert r.scenario.depreciation == D("9250.00")
    assert r.scenario.closing_carrying_amount == D("90750.00")


# T22 — full precision: 6,500.00 exactly, not 1,083.33 x 6 = 6,499.98
def test_t22_full_precision_not_rounded_rate():
    second = simulate(case_b()).scenario.segments[1]
    assert second.depreciation == D("6500.00")
    assert second.depreciation != D("1083.33") * 6
    assert second.exact_depreciation == 6500


# T23 — run T07 to the end of life (7 years); display rounding absorbed in the final year
def test_t23_full_life_schedule():
    sched = project_revised_schedule(make_input(revised_residual=D("20000")), 7)
    assert sched.ok
    yearly = [p.depreciation for p in sched.periods]
    assert yearly == [D("7571.43")] * 6 + [D("7571.42")]
    assert sum(yearly) == D("53000.00")
    assert sched.periods[-1].closing_carrying_amount == D("20000.00")
    assert sched.periods[-1].period_end == date(2031, 12, 31)


def test_schedule_stops_at_end_of_life():
    sched = project_revised_schedule(case_a(), 6)  # 60 months remaining -> 2025..2029, then nothing
    assert [p.depreciation for p in sched.periods] == [D("12600.00")] * 5 + [D("0.00")]
    assert sched.periods[4].closing_carrying_amount == D("10000.00")


def test_trace_shows_formula_and_numbers():
    steps = simulate(case_a()).scenario.trace
    labels = [s.label for s in steps]
    assert any("Remaining useful life" in lab for lab in labels)
    dep = steps[-1]
    assert dep.substitution == "63,000.00 × 12 ÷ 60"
    assert dep.result.startswith("12,600.00")
