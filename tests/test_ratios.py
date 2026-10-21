"""Ratios: worked-example values, T15 and T16. Expected values are hand calculations."""
from decimal import Decimal as D
from fractions import Fraction

from _builders import analyse, case_a, make_financials, make_opening
from simulator.ratios.analysis import _ratio


def _ratios(result):
    return {r.key: r for r in result.ratios}


def test_case_a_ratios():
    r = _ratios(analyse(case_a(), make_financials()))
    m = r["operating_margin"]  # 91,000 / 500,000 ; 87,400 / 500,000
    assert (m.baseline, m.scenario) == (Fraction(91000, 500000), Fraction(87400, 500000))
    assert (m.display_baseline, m.display_scenario, m.display_change) == (D("18.20"), D("17.48"), D("-0.72"))
    roa = r["return_on_assets"]  # 87,400 / 496,400 = 0.176068 -> 17.61%
    assert (roa.display_baseline, roa.display_scenario, roa.display_change) == (D("18.20"), D("17.61"), D("-0.59"))
    at = r["asset_turnover"]  # 500,000 / 496,400 = 1.00725
    assert (at.display_baseline, at.display_scenario, at.display_change) == (D("1.000"), D("1.007"), D("0.007"))
    assert "not an efficiency gain" in at.explanation
    le = r["liabilities_to_equity"]  # 200,000 / 296,400 = 0.674764
    assert (le.display_baseline, le.display_scenario, le.display_change) == (D("0.667"), D("0.675"), D("0.008"))
    assert all("simplified" in x.name for x in (roa, at, le))
    assert all(x.effect == "indirect" for x in r.values())


def test_margin_uses_operating_profit_not_pbt():
    # other income 5,000, finance costs 2,000: operating profit 91,000 but PBT 94,000.
    # Balance: equity 209,000 + 94,000 = 303,000; assets 500,000 -> liabilities 197,000.
    result = analyse(case_a(), make_financials(other_income=D("5000"), finance_costs=D("2000"),
                                                           liabilities=D("197000")))
    assert result.ok
    b = result.baseline_statements
    assert (b.operating_profit, b.profit_before_tax) == (D("91000.00"), D("94000.00"))
    r = _ratios(result)
    assert r["operating_margin"].display_baseline == D("18.20")   # 91,000 / 500,000
    assert r["return_on_assets"].display_baseline == D("18.80")   # 94,000 / 500,000


# T15 — equity zero (baseline) and negative (revised): not meaningful, no number shown
def test_t15_equity_zero_or_negative():
    # opening equity −91,000; liabilities 500,000. Baseline equity −91,000 + 91,000 = 0 ; revised −3,600.
    # Opening position: 409,000 assets = 500,000 liabilities − 91,000 equity.
    result = analyse(case_a(), make_financials(liabilities=D("500000"), opening_equity=D("-91000")),
                     make_opening(total_assets=D("409000"), total_liabilities=D("500000")))
    assert result.ok
    le = _ratios(result)["liabilities_to_equity"]
    assert le.baseline is None and le.scenario is None and le.change is None
    assert le.display_baseline is None
    assert "zero" in le.baseline_reason and "negative" in le.scenario_reason
    assert "V25" in result.codes()


def test_t15_direct_negative_denominator():
    value, reason = _ratio(D("200000"), D("-50000"), "Equity")
    assert value is None and "negative" in reason


# T16 — revenue zero: margin not meaningful, asset turnover 0.000x (meaningful)
def test_t16_revenue_zero():
    # revenue 0, other opex 0, liabilities 300,000: baseline equity 209,000 − 9,000 = 200,000; assets 500,000
    result = analyse(case_a(), make_financials(revenue=D("0"), other_opex=D("0"),
                                                           liabilities=D("300000")))
    assert result.ok
    r = _ratios(result)
    assert r["operating_margin"].baseline is None and "zero" in r["operating_margin"].baseline_reason
    at = r["asset_turnover"]
    assert (at.display_baseline, at.display_scenario, at.display_change) == (D("0.000"), D("0.000"), D("0.000"))
    roa = r["return_on_assets"]  # −9,000 / 500,000 = −1.80% ; −12,600 / 496,400 = −2.54%
    assert (roa.display_baseline, roa.display_scenario, roa.display_change) == (D("-1.80"), D("-2.54"), D("-0.74"))
