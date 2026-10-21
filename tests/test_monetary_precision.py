"""Monetary precision (decision 3): inputs and posted amounts have at most 2 decimals;
internal calculations keep full precision; excess decimals are rejected, never silently rounded."""
from datetime import date
from decimal import Decimal as D
from fractions import Fraction

import pytest

from _builders import analyse, case_a, case_b, make_financials, make_input, make_opening
from simulator.validation.coerce import to_amount

ASSET_FIELDS = {
    "cost": lambda v: make_input(cost=v, revised_life=96),
    "residual_value": lambda v: make_input(residual=v, revised_life=96),
    "revised_residual_value": lambda v: make_input(revised_residual=v),
    "opening_accumulated_depreciation": lambda v: make_input(opening_ad=v, revised_life=96),
}
FINANCIAL_KWARGS = {"revenue": "revenue", "other_operating_expenses": "other_opex", "other_income": "other_income",
                    "finance_costs": "finance_costs", "other_assets_closing": "other_assets",
                    "total_liabilities_closing": "liabilities", "opening_equity": "opening_equity"}
OPENING_KWARGS = {"opening_total_assets": "total_assets", "opening_total_liabilities": "total_liabilities"}


@pytest.mark.parametrize("field", list(ASSET_FIELDS))
def test_p1_asset_amounts_with_three_decimals_rejected(field):
    r = analyse(ASSET_FIELDS[field](D("1000.005")))
    assert r.status == "failed"
    assert any(i.code == "V23" and i.field == field for i in r.errors)


@pytest.mark.parametrize("field", list(FINANCIAL_KWARGS))
def test_p2_financial_amounts_with_three_decimals_rejected(field):
    r = analyse(case_a(), make_financials(**{FINANCIAL_KWARGS[field]: D("1000.005")}))
    assert r.status == "partial" and r.baseline_statements is None
    assert any(i.code == "V23" and i.field == field for i in r.errors)


@pytest.mark.parametrize("field", list(OPENING_KWARGS))
def test_p3_opening_amounts_with_three_decimals_rejected(field):
    r = analyse(case_a(), opening=make_opening(**{OPENING_KWARGS[field]: D("409000.001")}))
    assert r.status == "partial" and r.opening_statement is None
    assert any(i.code == "V23" and i.field == field for i in r.errors)


def test_p4_two_decimals_accepted():
    # cost 100,000.01 -> depreciable 90,000.01; 63,000.01 left after 27,000 ; x 12 / 60 = 12,600.002 -> 12,600.00
    r = analyse(make_input(cost=D("100000.01"), revised_life=96),
                opening=make_opening(total_assets=D("409000.01"), total_liabilities=D("200000.01")))
    assert r.depreciation.ok
    assert r.depreciation.scenario.depreciation == D("12600.00")


def test_p5_float_artefact_rejected_not_silently_rounded():
    value, issue = to_amount(0.1 + 0.2, "cost")  # 0.30000000000000004
    assert value is None and issue.code == "V23"


@pytest.mark.parametrize("inp,other_assets", [
    (case_a(), D("436000")), (case_b(), D("436000")), (make_input(revised_residual=D("20000")), D("436000")),
    # T21: asset in use from 1 Apr 2025, opening AD 0. Hand balance: baseline CA 93,250 and equity
    # 209,000 + 100,000 − 6,750 = 302,250, so other assets = 200,000 + 302,250 − 93,250 = 409,000.
    (make_input(available=date(2025, 4, 1), opening_ad=D("0"), change_date=date(2025, 10, 1), revised_life=60),
     D("409000")),
], ids=["case_a", "case_b", "t07", "t21"])
def test_p6_every_posted_and_reported_amount_has_two_decimals_at_most(inp, other_assets):
    r = analyse(inp, make_financials(other_assets=other_assets))
    assert r.status == "complete", r.summary
    amounts = [ln.debit for e in r.baseline_entries + r.scenario_entries for ln in e.lines]
    amounts += [ln.credit for e in r.baseline_entries + r.scenario_entries for ln in e.lines]
    for pd in (r.depreciation.baseline, r.depreciation.scenario):
        amounts += [pd.depreciation, pd.closing_accumulated_depreciation, pd.closing_carrying_amount]
        amounts += [s.depreciation for s in pd.segments]
    for fs in (r.baseline_statements, r.scenario_statements):
        amounts += [fs.depreciation, fs.profit_before_tax, fs.total_assets, fs.closing_equity]
    assert amounts
    assert all(a == a.quantize(D("0.01")) for a in amounts)


def test_p7_internal_precision_retained():
    seg = analyse(make_input(revised_residual=D("20000"))).depreciation.scenario.segments[0]
    assert seg.exact_depreciation == Fraction(53000, 7)    # 7,571.428571... kept exactly
    assert seg.depreciation == D("7571.43")                # rounded only when posted
