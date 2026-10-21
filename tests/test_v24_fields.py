"""V24 field rules (decision 4): which statement inputs may be negative."""
from decimal import Decimal as D

import pytest

from _builders import analyse, case_a, make_financials, make_opening
from simulator.validation.accounting_checks import MAY_BE_NEGATIVE, NON_NEGATIVE
from simulator.validation.coerce import FINANCIAL_FIELDS

KWARG = {"revenue": "revenue", "other_operating_expenses": "other_opex", "finance_costs": "finance_costs",
         "other_assets_closing": "other_assets", "total_liabilities_closing": "liabilities"}


@pytest.mark.parametrize("field", NON_NEGATIVE)
def test_v24_negative_rejected(field):
    r = analyse(case_a(), make_financials(**{KWARG[field]: D("-0.01")}))
    assert r.status == "partial" and r.baseline_statements is None
    assert any(i.code == "V24" and i.field == field for i in r.errors)


@pytest.mark.parametrize("field", NON_NEGATIVE)
def test_v24_zero_allowed(field):
    r = analyse(case_a(), make_financials(**{KWARG[field]: D("0")}))
    assert "V24" not in r.codes()  # other checks (e.g. V11) may still apply


@pytest.mark.parametrize("label,kwarg", [("opening_total_assets", "total_assets"),
                                         ("opening_total_liabilities", "total_liabilities")])
def test_v24_opening_fields_negative_rejected(label, kwarg):
    r = analyse(case_a(), opening=make_opening(**{kwarg: D("-1")}))
    assert any(i.code == "V24" and i.field == label for i in r.errors)
    assert r.opening_statement is None


def test_other_income_may_be_negative():
    # net other expense 5,000: PBT 91,000 − 5,000 = 86,000; equity 295,000; assets 500,000 -> liabilities 205,000
    r = analyse(case_a(), make_financials(other_income=D("-5000"), liabilities=D("205000")))
    assert r.ok and "V24" not in r.codes()
    assert r.baseline_statements.profit_before_tax == D("86000.00")


def test_opening_equity_may_be_negative():
    # accumulated losses: opening equity −91,000; opening 409,000 = 500,000 − 91,000
    r = analyse(case_a(), make_financials(liabilities=D("500000"), opening_equity=D("-91000")),
                make_opening(total_liabilities=D("500000")))
    assert r.ok and "V24" not in r.codes()


def test_every_financial_field_has_a_documented_sign_rule():
    assert set(NON_NEGATIVE) | set(MAY_BE_NEGATIVE) == set(FINANCIAL_FIELDS)
    assert not set(NON_NEGATIVE) & set(MAY_BE_NEGATIVE)
