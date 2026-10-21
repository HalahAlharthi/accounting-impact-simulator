"""Runs the real Streamlit app headlessly with Streamlit's official AppTest.

Skipped automatically when Streamlit is not installed (pip install -r requirements.txt installs it).
"""
import calendar
from datetime import date
from pathlib import Path

import pytest

testing = pytest.importorskip("streamlit.testing.v1")

from simulator.impact import run_impact_analysis
from simulator.periods import months_in_range
from simulator.reporting import presentation as p
from simulator.scenarios import SAMPLE_DIR, load_scenario

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def test_app_default_sample_complete():
    at = testing.AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    assert any("Scenario complete" in s.value for s in at.success)
    assert "12,600.00" in [m.value for m in at.metric]  # engine figure shown as a key metric


def test_app_partial_sample_withholds_sections():
    at = testing.AppTest.from_file(APP, default_timeout=60).run()
    t14 = next(o for o in at.selectbox(key="preset_select").options if o.startswith("T14"))
    at.selectbox(key="preset_select").set_value(t14).run()
    assert not at.exception
    assert any("NOT complete" in w.value for w in at.warning)
    assert any(e.value.startswith("Withheld") for e in at.error)


def _assert_sample_inputs_in_widgets(at, scenario):
    version = at.session_state["form_version"]
    asset, period, revision = scenario.inputs.asset, scenario.inputs.period, scenario.inputs.revision
    financials, opening = scenario.financials, scenario.opening
    available_date = date.fromisoformat(asset.available_for_use_date)
    start_date = date.fromisoformat(period.start_date)
    end_date = date.fromisoformat(period.end_date)
    change_date = date.fromisoformat(revision.effective_date) if revision and revision.effective_date else start_date
    revised_residual = (revision.revised_residual_value
                        if revision and revision.revised_residual_value not in (None, "") else asset.residual_value)
    expected = {
        f"cost_{version}": float(asset.cost),
        f"res_{version}": float(asset.residual_value),
        f"life_{version}": int(asset.useful_life_months),
        f"avail_{version}_m": calendar.month_name[available_date.month],
        f"avail_{version}_y": available_date.year,
        f"pstart_{version}_m": calendar.month_name[start_date.month],
        f"pstart_{version}_y": start_date.year,
        f"plen_{version}": months_in_range(start_date, end_date),
        f"useoad_{version}": scenario.inputs.opening_accumulated_depreciation not in (None, ""),
        f"oad_{version}": float(scenario.inputs.opening_accumulated_depreciation or 0),
        f"chg_{version}": change_date,
        f"rlife_{version}": int((revision.revised_useful_life_months if revision else None)
                                 or asset.useful_life_months),
        f"crv_{version}": bool(revision and revision.revised_residual_value not in (None, "")),
        f"rrv_{version}": float(revised_residual),
        f"rev_{version}": float(financials.revenue or 0),
        f"opex_{version}": float(financials.other_operating_expenses or 0),
        f"oi_{version}": float(financials.other_income or 0),
        f"fc_{version}": float(financials.finance_costs or 0),
        f"oa_{version}": float(financials.other_assets_closing or 0),
        f"liab_{version}": float(financials.total_liabilities_closing or 0),
        f"ota_{version}": float(opening.total_assets or 0),
        f"otl_{version}": float(opening.total_liabilities or 0),
        f"oe_{version}": float(financials.opening_equity or 0),
    }
    for key, value in expected.items():
        assert at.get_by_key(key).value == value, key
    assert at.text_input[0].value == scenario.currency


def test_switching_samples_replaces_inputs_and_results():
    at = testing.AppTest.from_file(APP, default_timeout=60).run()
    samples = [
        ("Case B", "case_b_change_1_jul.json", "11,000.00", "complete", ""),
        ("T19", "t19_opening_balance_override.json", "12,000.00", "complete", "V08"),
        ("T14", "t14_unbalanced_statements.json", "12,600.00", "partial", "V11"),
        ("Case A", "case_a_change_1_jan.json", "12,600.00", "complete", ""),
    ]

    for prefix, filename, revised_depreciation, status, issue_code in samples:
        selected = next(option for option in at.selectbox(key="preset_select").options
                        if option.startswith(prefix))
        at.selectbox(key="preset_select").set_value(selected).run()
        assert not at.exception
        expected_scenario = load_scenario(SAMPLE_DIR / filename)
        assert at.session_state["scenario"] == expected_scenario
        assert at.session_state["preset"] == selected
        _assert_sample_inputs_in_widgets(at, expected_scenario)

        expected_result = run_impact_analysis(
            expected_scenario.inputs, expected_scenario.financials, expected_scenario.opening)
        assert at.session_state["scenario"] == expected_scenario
        assert expected_result.status == status
        assert revised_depreciation in [metric.value for metric in at.metric]

        rendered_tables = [element.value for element in at.dataframe]
        assert rendered_tables[0].equals(p.depreciation_table(expected_result))
        assert rendered_tables[1].equals(p.balances_table(expected_result))
        assert rendered_tables[2].equals(p.trace_table(expected_result.depreciation.scenario))
        assert rendered_tables[3].equals(p.trace_table(expected_result.depreciation.baseline))
        assert rendered_tables[4].equals(p.journal_table(expected_result.scenario_entries))
        assert rendered_tables[5].equals(p.journal_table(expected_result.baseline_entries))
        assert rendered_tables[6].equals(p.opening_table(expected_result))

        if status == "complete":
            assert any("Scenario complete" in item.value for item in at.success)
            assert rendered_tables[7].equals(p.impact_table(expected_result))
            assert rendered_tables[8].equals(p.statements_table(expected_result))
            assert rendered_tables[9].equals(p.ratio_table(expected_result))
            reference_index = 10
        else:
            assert any("NOT complete" in item.value for item in at.warning)
            assert any("Withheld" in item.value for item in at.error)
            assert any("Withheld: statements, impact table, ratios" in item.value for item in at.code)
            reference_index = 7

        assert rendered_tables[reference_index].equals(p.references_table())
        if issue_code:
            issues = rendered_tables[reference_index + 1]
            issue = issues.loc[issues["Code"] == issue_code].iloc[0]
            assert issue["Severity"] == ("WARNING" if issue_code == "V08" else "ERROR")
            assert len(rendered_tables) == reference_index + 2
        else:
            assert len(rendered_tables) == reference_index + 1
