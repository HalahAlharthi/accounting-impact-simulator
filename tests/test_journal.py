"""T12 and journal rules J1–J5."""
import dataclasses
from datetime import date
from decimal import Decimal as D

from _builders import analyse, case_a, case_b, make_financials, make_input
from simulator.journal import (
    ACCUMULATED_DEPRECIATION,
    DEPRECIATION_EXPENSE,
    JournalLine,
    build_journal_entries,
    check_journal_entries,
)
from simulator.ias16 import simulate


# T12 — every generated entry balances (Case A, Case B, T19 override, T21)
def test_t12_all_entries_balance():
    inputs = [case_a(), case_b(), make_input(revised_life=96, opening_ad=D("30000")),
              make_input(available=date(2025, 4, 1), opening_ad=D("0"), change_date=date(2025, 10, 1),
                         revised_life=60)]
    for inp in inputs:
        r = simulate(inp)
        for pd in (r.baseline, r.scenario):
            entries = build_journal_entries(pd)
            assert entries
            assert all(e.is_balanced for e in entries)
            assert check_journal_entries(entries) == []


def test_j1_j2_accounts_dates_and_amounts_case_b():
    entries = build_journal_entries(simulate(case_b()).scenario)
    assert [(e.entry_date, e.total_debits) for e in entries] == [
        (date(2025, 6, 30), D("4500.00")), (date(2025, 12, 31), D("6500.00"))]
    for e in entries:
        dr, cr = e.lines
        assert (dr.account, dr.credit) == (DEPRECIATION_EXPENSE, D("0.00"))
        assert (cr.account, cr.debit) == (ACCUMULATED_DEPRECIATION, D("0.00"))
    assert "original estimate" in entries[0].description and "revised estimate" in entries[1].description


def test_j3_no_entry_against_retained_earnings():
    r = analyse(case_a(), make_financials())
    accounts = {ln.account for e in r.baseline_entries + r.scenario_entries for ln in e.lines}
    assert accounts == {DEPRECIATION_EXPENSE, ACCUMULATED_DEPRECIATION}


def test_zero_depreciation_segment_gets_no_entry_and_statements_still_reconcile():
    # T10 inputs: revised residual 75,000 > carrying amount 73,000
    r = analyse(make_input(revised_residual=D("75000")), make_financials())
    assert r.ok
    assert r.scenario_entries == ()
    assert r.scenario_statements.depreciation == D("0.00")
    # hand: assets 436,000 + 73,000 = 509,000; equity 209,000 + 100,000 = 309,000; + liabilities 200,000
    assert r.scenario_statements.total_assets == D("509000.00")
    assert r.scenario_statements.equation_difference == 0


def test_v10_unbalanced_entry_is_reported_not_fixed():
    entry = build_journal_entries(simulate(case_a()).scenario)[0]
    broken = dataclasses.replace(entry, lines=(entry.lines[0],
                                               JournalLine(ACCUMULATED_DEPRECIATION, D("0.00"), D("12599.00"))))
    issues = check_journal_entries((broken,))
    assert [i.code for i in issues] == ["V10"]
    assert "difference 1.00" in issues[0].message
    assert broken.lines[1].credit == D("12599.00")  # untouched
