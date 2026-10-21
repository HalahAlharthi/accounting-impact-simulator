"""Report export: same figures as the screen; withheld sections are stated, never silently dropped."""
import json

from simulator.impact import run_impact_analysis
from simulator.reporting.export import build_json_report, build_markdown_report
from simulator.scenarios import SAMPLE_DIR, load_scenario


def _sample(name):
    sc = load_scenario(SAMPLE_DIR / f"{name}.json")
    return sc, run_impact_analysis(sc.inputs, sc.financials, sc.opening)


def test_markdown_report_complete():
    sc, r = _sample("case_a_change_1_jan")
    md = build_markdown_report(sc, r)
    assert "## Status: Scenario complete" in md
    assert "Educational tool only" in md
    assert "| Revised | Jan 2025–Dec 2025 (12) | revised estimate | 73,000.00 | 10,000.00 | 60 | 63,000.00 | 12,600.00 |" in md
    assert "**Withheld.**" not in md
    assert "pending verification against IFRS primary text" in md


def test_markdown_report_partial_states_withheld_sections():
    sc, r = _sample("t14_unbalanced_statements")
    md = build_markdown_report(sc, r)
    assert "NOT complete" in md
    assert md.count("**Withheld.**") == 3  # statements, impact table, ratios
    assert "Validated independently" in md and "V11" in md
    assert "12,600.00" in md  # depreciation still shown


def test_json_report():
    sc, r = _sample("t14_unbalanced_statements")
    data = json.loads(build_json_report(sc, r))
    assert data["status"] == "partial"
    assert data["withheld_sections"] == ["statements", "impact table", "ratios"]
    assert data["statements"] is None and data["ratios"] is None
    seg = data["depreciation"]["revised"]["segments"][0]
    assert seg["depreciation"] == "12600.00" and isinstance(seg["depreciation"], str)  # exact text, no float

    sc, r = _sample("case_b_change_1_jul")
    data = json.loads(build_json_report(sc, r))
    assert data["status"] == "complete"
    assert [e["entry_date"] for e in data["journal_entries"]["revised"]] == ["2025-06-30", "2025-12-31"]
    assert data["statements"]["revised"]["total_assets"] == "498000.00"
