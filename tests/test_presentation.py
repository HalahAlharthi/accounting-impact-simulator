"""The displayed tables agree with the engine (every shown figure is the engine figure, formatted).

Also checks status banners and partial-result labelling (decision 1)."""
from decimal import Decimal as D

import pytest

from _builders import analyse, case_a, case_b, make_financials, make_input, make_opening
from simulator.money import fmt
from simulator.reporting import presentation as p

CASES = {"case_a": lambda: analyse(case_a()), "case_b": lambda: analyse(case_b()),
         "t19": lambda: analyse(make_input(revised_life=96, opening_ad=D("30000")),
                                make_financials(opening_equity=D("206000")),
                                make_opening(total_assets=D("406000")))}


@pytest.mark.parametrize("case", list(CASES))
def test_depreciation_table_matches_engine(case):
    r = CASES[case]()
    rows = p.depreciation_table(r).to_dict("records")
    segments = list(r.depreciation.baseline.segments) + list(r.depreciation.scenario.segments)
    assert len(rows) == len(segments)
    for row, seg in zip(rows, segments):
        assert row["Depreciation"] == fmt(seg.depreciation)
        assert row["Carrying amount at start"] == fmt(seg.carrying_amount_at_start)
        assert row["Remaining life (months)"] == str(seg.remaining_life_months)


@pytest.mark.parametrize("case", list(CASES))
def test_impact_and_statements_tables_match_engine(case):
    r = CASES[case]()
    for row, line in zip(p.impact_table(r).to_dict("records"), r.impact):
        assert (row["Baseline"], row["Revised"]) == (fmt(line.baseline), fmt(line.scenario))
        assert row["Change"].lstrip("+") == fmt(line.change)
    st = {row["Line"]: row for row in p.statements_table(r).to_dict("records")}
    assert st["Profit before tax"]["Revised"] == fmt(r.scenario_statements.profit_before_tax)
    assert st["Total assets"]["Baseline"] == fmt(r.baseline_statements.total_assets)
    assert st["Check: assets − liabilities − equity"]["Revised"] == "0.00"


@pytest.mark.parametrize("case", list(CASES))
def test_journal_table_matches_entries(case):
    r = CASES[case]()
    rows = p.journal_table(r.scenario_entries).to_dict("records")
    debits = [row["Debit"] for row in rows if row["Debit"]]
    assert debits == [fmt(e.total_debits) for e in r.scenario_entries]


def test_case_a_displayed_ratios():
    rows = {row["Ratio"].split(" (")[0]: row for row in p.ratio_table(analyse(case_a())).to_dict("records")}
    assert (rows["Operating profit margin"]["Baseline"], rows["Operating profit margin"]["Revised"],
            rows["Operating profit margin"]["Change"]) == ("18.20%", "17.48%", "-0.72 pp")
    assert (rows["Asset turnover"]["Revised"], rows["Asset turnover"]["Change"]) == ("1.007×", "+0.007×")


def test_not_meaningful_ratio_shows_no_number():
    r = analyse(case_a(), make_financials(liabilities=D("500000"), opening_equity=D("-91000")),
                make_opening(total_liabilities=D("500000")))
    row = next(x for x in p.ratio_table(r).to_dict("records") if x["Ratio"].startswith("Liabilities"))
    assert (row["Baseline"], row["Revised"], row["Change"]) == ("Not meaningful",) * 3
    assert row["Why it changed"].startswith("Not meaningful:")


def test_key_figures_and_summary_match_engine():
    r = analyse(case_b())
    figures = p.key_figures(r)
    assert figures["Depreciation — revised"] == "11,000.00" == fmt(r.depreciation.scenario.depreciation)
    assert figures["Change in depreciation"] == "+2,000.00"
    assert any("not verified" in line for line in p.executive_summary(analyse(make_input(revised_life=96,
                                                                                         opening_ad=None))))


def test_status_banners_and_section_notes():
    assert p.status_banner(analyse(case_a()))[0] == "success"
    assert p.section_note(analyse(case_a()), "ratios") is None

    partial = analyse(case_a(), make_financials(other_assets=D("435000")))  # T14
    level, title, body = p.status_banner(partial)
    assert level == "warning" and "NOT complete" in title
    assert "Withheld: statements, impact table, ratios" in body
    assert p.section_note(partial, "depreciation") == ("info", p.VALIDATED_INDEPENDENTLY)
    kind, text = p.section_note(partial, "ratios")
    assert kind == "withheld" and "V11" in text

    failed = analyse(make_input(revised_life=36))
    assert p.status_banner(failed)[0] == "error"
    assert p.depreciation_table(failed).empty and p.key_figures(failed) is None


def test_issues_and_references_tables():
    r = analyse(make_input(revised_life=96, opening_ad=D("30000")))  # V08 warning + V11 errors
    issues = p.issues_table(r)
    assert list(issues["Severity"])[0] == "ERROR"  # errors first
    assert set(issues["Code"]) == r.codes()
    refs = p.references_table()
    assert refs.loc[refs["Reference"] == "IAS 16.54", "Verification status"].item() == "confirmed on ifrs.org"
