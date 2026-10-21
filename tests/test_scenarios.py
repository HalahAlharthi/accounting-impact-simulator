"""Sample scenario files load and give the approved hand-calculated results."""
from decimal import Decimal as D

from simulator.impact import run_impact_analysis
from simulator.scenarios import SAMPLE_DIR, list_samples, load_scenario


def _run(name):
    sc = load_scenario(SAMPLE_DIR / f"{name}.json")
    return sc, run_impact_analysis(sc.inputs, sc.financials, sc.opening)


def test_four_samples_present():
    assert len(list_samples()) == 4


def test_sample_case_a():
    _, r = _run("case_a_change_1_jan")
    assert r.status == "complete"
    assert (r.depreciation.baseline.depreciation, r.depreciation.scenario.depreciation) == (D("9000.00"), D("12600.00"))


def test_sample_case_b():
    _, r = _run("case_b_change_1_jul")
    assert r.status == "complete" and r.depreciation.scenario.depreciation == D("11000.00")


def test_sample_t19_override_balances_with_warning():
    _, r = _run("t19_opening_balance_override")
    assert r.status == "complete" and "V08" in r.codes()
    assert r.depreciation.scenario.depreciation == D("12000.00")


def test_sample_t14_is_partial():
    _, r = _run("t14_unbalanced_statements")
    assert r.status == "partial" and "V11" in r.codes()
