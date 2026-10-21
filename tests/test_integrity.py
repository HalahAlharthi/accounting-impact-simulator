"""Integrity guards: opening balances identical (T27) and arithmetic reconciliation (V12). Nothing is ever plugged."""
import dataclasses
from decimal import Decimal as D

from _builders import case_a, case_b, make_input
from simulator.ias16 import simulate
from simulator.validation import check_opening_balances_identical, check_period_arithmetic


# T27 (Phase 2 part) — opening balances identical across baseline and revised, including under the T19 override.
# The accounting-equation half of T27 needs the statement builder and is implemented in Phase 3.
def test_t27_opening_balances_identical_all_cases():
    cases = {
        "Case A": (case_a(), D("27000"), D("73000")),
        "Case B": (case_b(), D("27000"), D("73000")),
        "T19 override": (make_input(revised_life=96, opening_ad=D("30000")), D("30000"), D("70000")),
    }
    for name, (inp, opening_ad, opening_ca) in cases.items():
        r = simulate(inp)
        assert r.ok, name
        for pd in (r.baseline, r.scenario):
            assert pd.opening_accumulated_depreciation == opening_ad, name
            assert pd.opening_carrying_amount == opening_ca, name
        assert check_opening_balances_identical(r.baseline, r.scenario) == [], name


def test_t27_guard_rejects_different_opening_balances_without_adjusting():
    r = simulate(case_a())
    tampered = dataclasses.replace(r.scenario, opening_accumulated_depreciation=D("28000"))
    issues = check_opening_balances_identical(r.baseline, tampered)
    assert issues and all(i.code == "V13" for i in issues)
    assert "difference 1000" in issues[0].message
    assert tampered.opening_accumulated_depreciation == D("28000")  # reported, not corrected


def test_arithmetic_check_passes_on_engine_output():
    for inp in (case_a(), case_b(), make_input(revised_life=96, opening_ad=D("30000"))):
        r = simulate(inp)
        assert check_period_arithmetic(r.baseline) == []
        assert check_period_arithmetic(r.scenario) == []


def test_v12_arithmetic_guard_catches_inconsistent_segment():
    r = simulate(case_b())
    seg2 = r.scenario.segments[1]
    bad_seg = dataclasses.replace(seg2, carrying_amount_at_start=D("68600.00"))  # should be 68,500
    bad = dataclasses.replace(r.scenario, segments=(r.scenario.segments[0], bad_seg))
    issues = check_period_arithmetic(bad)
    assert any(i.code == "V12" and "difference 100.00" in i.message for i in issues)


def test_v12_guard_catches_posted_amount_not_matching_exact():
    r = simulate(case_a())
    seg = r.scenario.segments[0]
    bad = dataclasses.replace(r.scenario, segments=(dataclasses.replace(seg, depreciation=D("12600.01")),))
    assert any(i.code == "V12" and "rounded half-up" in i.message for i in check_period_arithmetic(bad))
