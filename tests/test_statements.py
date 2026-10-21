"""Statements, accounting equation and reconciliation: T13, T14, T24, T25, T26, T27 part 2.
All expected values are hand calculations from the approved Phase 1 worked example."""
import dataclasses
from decimal import Decimal as D

from _builders import analyse, case_a, case_b, make_financials, make_input, make_opening
from simulator.validation.accounting_checks import check_accounting_equation, check_statement_reconciliation


def _line(result, metric):
    return next(line for line in result.impact if line.metric.startswith(metric))


# T13 — accounting equation holds in both scenarios (Case A)
def test_t13_accounting_equation_case_a():
    r = analyse(case_a(), make_financials())
    assert r.ok
    for fs in (r.baseline_statements, r.scenario_statements):
        assert fs.total_assets - fs.total_liabilities - fs.closing_equity == 0
    # 500,000 − 200,000 − 300,000 = 0 ; 496,400 − 200,000 − 296,400 = 0
    assert (r.baseline_statements.total_assets, r.baseline_statements.closing_equity) == (D("500000"), D("300000"))
    assert (r.scenario_statements.total_assets, r.scenario_statements.closing_equity) == (D("496400"), D("296400"))


# T24 — Case A (1 Jan) journal and statement integrity
def test_t24_case_a_integrity():
    r = analyse(case_a(), make_financials())
    assert r.ok
    b, s = r.baseline_statements, r.scenario_statements
    assert [e.total_debits for e in r.baseline_entries] == [D("9000.00")]
    assert [e.total_debits for e in r.scenario_entries] == [D("12600.00")]
    assert (b.depreciation, s.depreciation) == (D("9000.00"), D("12600.00"))  # statements = journal totals
    assert (b.accumulated_depreciation, s.accumulated_depreciation) == (D("36000.00"), D("39600.00"))
    assert (b.operating_profit, s.operating_profit) == (D("91000.00"), D("87400.00"))
    assert (b.profit_before_tax, s.profit_before_tax) == (D("91000.00"), D("87400.00"))
    for metric in ("Profit before tax", "Closing equity", "Asset carrying amount", "Total assets"):
        assert _line(r, metric).change == D("-3600.00"), metric
    assert _line(r, "Total liabilities").change == 0
    assert _line(r, "Revenue").change == 0


def test_carrying_amount_and_total_assets_are_separate_lines():
    r = analyse(case_a(), make_financials())
    carrying, total = _line(r, "Asset carrying amount"), _line(r, "Total assets")
    assert (carrying.baseline, carrying.scenario) == (D("64000.00"), D("60400.00"))
    assert (total.baseline, total.scenario) == (D("500000.00"), D("496400.00"))


# T25 — Case B (1 Jul) journal and statement integrity
def test_t25_case_b_integrity():
    r = analyse(case_b(), make_financials())
    assert r.ok
    s = r.scenario_statements
    assert [(e.entry_date.isoformat(), e.total_debits) for e in r.scenario_entries] == [
        ("2025-06-30", D("4500.00")), ("2025-12-31", D("6500.00"))]
    assert all(e.is_balanced for e in r.scenario_entries)
    # 500,000 − 400,000 − 11,000 = 89,000 ; 436,000 + 62,000 = 498,000 ; 209,000 + 89,000 = 298,000
    assert (s.depreciation, s.operating_profit, s.profit_before_tax) == (D("11000"), D("89000"), D("89000"))
    assert (s.accumulated_depreciation, s.ppe_carrying_amount) == (D("38000.00"), D("62000.00"))
    assert (s.total_assets, s.total_liabilities, s.closing_equity) == (D("498000"), D("200000"), D("298000"))
    assert s.equation_difference == 0
    for metric in ("Profit before tax", "Closing equity", "Asset carrying amount", "Total assets"):
        assert _line(r, metric).change == D("-2000.00"), metric


# T14 — unbalanced inputs: V11 with the 1,000 difference; nothing plugged; no statements or ratios released
def test_t14_unbalanced_inputs_no_plug():
    r = analyse(case_a(), make_financials(other_assets=D("435000")))
    assert not r.ok
    v11 = [i for i in r.errors if i.code == "V11"]
    assert len(v11) == 2  # baseline and revised each checked
    assert "total assets 499,000.00" in v11[0].message and "= 500,000.00" in v11[0].message
    assert "-1,000.00" in v11[0].message and "No balancing figure" in v11[0].message
    assert "equity 300,000.00" in v11[0].message  # equity reported as calculated, not adjusted
    assert r.baseline_statements is None and r.scenario_statements is None
    assert r.ratios == () and r.impact == ()
    assert r.depreciation.ok and r.scenario_entries  # depreciation and journals were valid on their own


# T26 — statement-level inconsistency: V12 with the 100 difference; nothing adjusted
def test_t26_statement_inconsistency_reported():
    r = analyse(case_a(), make_financials())
    tampered = dataclasses.replace(r.baseline_statements, ppe_carrying_amount=D("64100.00"))
    issues = check_statement_reconciliation(tampered, r.depreciation.baseline, r.baseline_entries)
    messages = [i.message for i in issues if i.code == "V12"]
    assert any("carrying amount vs cost − accumulated depreciation" in m and "difference 100.00" in m for m in messages)
    assert any("total assets vs other assets + carrying amount" in m and "difference -100.00" in m for m in messages)
    # The accounting equation alone would NOT catch this (total assets were left unchanged),
    # which is why the line-by-line V12 reconciliation exists.
    assert check_accounting_equation(tampered) == []
    assert tampered.ppe_carrying_amount == D("64100.00")  # untouched


# T27 part 2 — accounting equation validated under the T19 override
def test_t27_override_with_inputs_prepared_on_implied_balance_raises_v11():
    r = analyse(make_input(revised_life=96, opening_ad=D("30000")), make_financials())
    assert not r.ok
    v11 = [i for i in r.errors if i.code == "V11"]
    # baseline: assets 436,000 + 61,428.57 = 497,428.57; L + E = 200,000 + 209,000 + 91,428.57 = 500,428.57
    assert "497,428.57" in v11[0].message and "500,428.57" in v11[0].message and "-3,000.00" in v11[0].message
    assert "override" in v11[0].fix
    assert r.baseline_statements is None and r.ratios == ()
    dep = r.depreciation  # opening balances still identical and as entered
    assert dep.baseline.opening_accumulated_depreciation == dep.scenario.opening_accumulated_depreciation == D("30000")


def test_t27_override_with_consistent_inputs_balances():
    # Opening equity prepared on the same ledger as the 30,000 balance: 209,000 − 3,000 = 206,000.
    # Opening position on that ledger: assets 406,000 (this asset 70,000 + other 336,000) = 200,000 + 206,000.
    r = analyse(make_input(revised_life=96, opening_ad=D("30000")), make_financials(opening_equity=D("206000")),
                make_opening(total_assets=D("406000")))
    assert r.ok, [i.message for i in r.errors]
    assert (r.opening_statement.asset_carrying_amount, r.opening_statement.other_assets) == (D("70000"), D("336000"))
    b, s = r.baseline_statements, r.scenario_statements
    # baseline: 436,000 + 61,428.57 = 497,428.57 = 200,000 + (206,000 + 91,428.57)
    assert (b.total_assets, b.closing_equity) == (D("497428.57"), D("297428.57"))
    # revised: 436,000 + 58,000 = 494,000 = 200,000 + (206,000 + 88,000)
    assert (s.total_assets, s.closing_equity) == (D("494000.00"), D("294000.00"))
    assert b.equation_difference == s.equation_difference == 0
    # opening balances identical: closing accumulated depreciation − period postings = 30,000 in both
    assert b.accumulated_depreciation - b.depreciation == s.accumulated_depreciation - s.depreciation == D("30000")
    assert "V08" in r.codes()  # the override warning is still shown


def test_financial_inputs_missing_or_negative():
    r = analyse(case_a(), make_financials(revenue=None))
    assert "V14" in r.codes() and r.baseline_statements is None
    r = analyse(case_a(), make_financials(liabilities=D("-1")))
    assert "V24" in r.codes() and r.baseline_statements is None


def test_financial_inputs_accept_ui_floats():
    r = analyse(case_a(), make_financials(revenue=500000.0, other_assets="436,000", opening_equity=209000))
    assert r.ok and r.scenario_statements.total_assets == D("496400.00")
