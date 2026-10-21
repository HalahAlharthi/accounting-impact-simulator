"""Opening position checks (V26, V27) and partial results after validation failures (decisions 1 and 2).

Worked-example opening position (hand figures): total assets 409,000 = liabilities 200,000 + equity 209,000;
of which this asset 73,000 (100,000 − 27,000) and other assets 336,000.
"""
import dataclasses
from decimal import Decimal as D

import simulator.impact as impact_module
from _builders import analyse, case_a, make_financials, make_input, make_opening
from simulator.journal import JournalLine
from simulator.impact import COMPLETE, FAILED, PARTIAL

ALL = ("depreciation", "journal entries", "opening position", "statements", "impact table", "ratios")


def _assert_not_reported_as_success(r):
    assert not r.ok and r.status != COMPLETE
    assert "complete:" not in r.summary.lower().replace("not complete", "")
    assert r.baseline_statements is None and r.scenario_statements is None
    assert r.impact == () and r.ratios == ()


# O1 — opening position balances in the worked example; full result released
def test_o1_opening_position_worked_example():
    r = analyse(case_a())
    assert r.status == COMPLETE and r.released_sections == ALL and r.withheld_sections == ()
    o = r.opening_statement
    assert (o.total_assets, o.asset_carrying_amount, o.other_assets) == (D("409000"), D("73000"), D("336000"))
    assert (o.total_liabilities, o.equity, o.equation_difference) == (D("200000"), D("209000"), 0)
    assert r.summary == "Scenario complete: all validation checks passed."


# O2 — opening assets ≠ liabilities + equity: V26, difference 1,000, no plug, partial result
def test_o2_opening_equation_fails():
    r = analyse(case_a(), opening=make_opening(total_assets=D("410000")))
    _assert_not_reported_as_success(r)
    assert r.status == PARTIAL
    assert r.released_sections == ("depreciation", "journal entries")
    assert r.withheld_sections == ("opening position", "statements", "impact table", "ratios")
    v26 = next(i for i in r.errors if i.code == "V26")
    assert "410,000.00" in v26.message and "409,000.00" in v26.message and "1,000.00" in v26.message
    assert "No balancing figure" in v26.message
    assert r.opening_statement is None
    assert v26.message in r.summary  # the exact error is shown


# O3 — opening total assets smaller than this asset's opening carrying amount: V27
def test_o3_opening_assets_exclude_the_asset():
    # 50,000 = 200,000 + (−150,000) balances, but the asset alone is 73,000: shortfall 23,000
    r = analyse(case_a(), make_financials(opening_equity=D("-150000")), make_opening(total_assets=D("50000")))
    _assert_not_reported_as_success(r)
    v27 = next(i for i in r.errors if i.code == "V27")
    assert "73,000.00" in v27.message and "23,000.00" in v27.message
    assert "V26" not in r.codes()


# O3b — asset not yet in use at the period start (T21): V27 not applied, info V28; opening equation still checked
def test_o3b_asset_not_in_use_at_period_start():
    from datetime import date
    t21 = make_input(available=date(2025, 4, 1), opening_ad=D("0"), change_date=date(2025, 10, 1), revised_life=60)
    # opening 50,000 = 200,000 + (−150,000): would fail V27 if the 100,000 asset had to be included
    r = analyse(t21, make_financials(opening_equity=D("-150000"), other_assets=D("50000")),
                make_opening(total_assets=D("50000")))
    assert "V27" not in r.codes() and "V28" in r.codes()
    assert r.opening_statement.asset_carrying_amount is None and r.opening_statement.other_assets is None
    bad = analyse(t21, opening=make_opening(total_assets=D("409001")))
    assert "V26" in bad.codes()  # the equation itself is still enforced


# O4 — opening position missing: V14, partial
def test_o4_opening_position_missing():
    r = analyse(case_a(), opening=make_opening(total_assets=None))
    _assert_not_reported_as_success(r)
    assert any(i.code == "V14" and i.field == "opening_total_assets" for i in r.errors)


# O5 — closing statements fail (T14) after the opening check passed: opening position also released
def test_o5_closing_failure_releases_validated_sections_only():
    r = analyse(case_a(), make_financials(other_assets=D("435000")))
    _assert_not_reported_as_success(r)
    assert r.status == PARTIAL
    assert r.released_sections == ("depreciation", "journal entries", "opening position")
    assert r.withheld_sections == ("statements", "impact table", "ratios")
    assert r.depreciation.scenario.depreciation == D("12600.00")  # still visible
    assert [e.total_debits for e in r.scenario_entries] == [D("12600.00")]
    assert r.opening_statement.equation_difference == 0
    assert "Validated independently and shown: depreciation, journal entries, opening position" in r.summary
    assert "Withheld: statements, impact table, ratios" in r.summary
    assert all(f"{i.code}: {i.message}" in r.summary for i in r.errors)


# O6 — journal entry fails V10: only depreciation released; journals withheld
def test_o6_journal_failure_withholds_journals(monkeypatch):
    real_build = impact_module.build_journal_entries

    def broken(pd):
        entries = real_build(pd)
        e = entries[0]
        bad = dataclasses.replace(e, lines=(e.lines[0], JournalLine(e.lines[1].account, D("0.00"), D("1.00"))))
        return (bad,) + entries[1:]

    monkeypatch.setattr(impact_module, "build_journal_entries", broken)
    r = analyse(case_a())
    _assert_not_reported_as_success(r)
    assert r.released_sections == ("depreciation",)
    assert r.baseline_entries == () and r.scenario_entries == ()
    assert "V10" in r.codes()


# O7 — depreciation inputs invalid: FAILED, nothing released
def test_o7_depreciation_failure_releases_nothing():
    r = analyse(make_input(revised_life=36))  # T09
    assert r.status == FAILED and r.released_sections == ()
    assert r.summary.startswith("Scenario FAILED")
    assert r.depreciation.baseline is None and r.scenario_entries == ()


# O8 — statement-input failure (V24) is partial, never complete
def test_o8_statement_input_failure_is_partial():
    r = analyse(case_a(), make_financials(revenue=D("-1")))
    _assert_not_reported_as_success(r)
    assert r.status == PARTIAL and r.released_sections == ("depreciation", "journal entries")
