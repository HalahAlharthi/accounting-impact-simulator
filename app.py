"""Accounting Standards Impact Simulator — Streamlit interface.

Run with:  streamlit run app.py

This file only collects inputs and displays results. Every number comes from
the tested engine (`simulator.impact.run_impact_analysis`) via the presentation
layer (`simulator.reporting.presentation`); no accounting calculation happens here.
"""
from __future__ import annotations

import calendar
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))  # use the engine without installing it

import streamlit as st  # noqa: E402

from simulator.impact import COMPLETE, run_impact_analysis  # noqa: E402
from simulator.models import (  # noqa: E402
    AssetInput,
    EntityFinancials,
    EstimateRevision,
    OpeningPosition,
    ReportingPeriod,
    SimulationInput,
)
from simulator.periods import add_months, end_of_month, months_in_range  # noqa: E402
from simulator.reporting import presentation as p  # noqa: E402
from simulator.reporting.export import build_json_report, build_markdown_report  # noqa: E402
from simulator.scenarios import Scenario, list_samples, load_scenario  # noqa: E402

try:
    import plotly.graph_objects as go
except ImportError:  # the tables remain authoritative; the chart is optional
    go = None

st.set_page_config(page_title="Accounting Standards Impact Simulator", page_icon="📘", layout="wide")

SAMPLES = list_samples()
MONTHS = list(calendar.month_name)[1:]

# --------------------------------------------------------------------------- #
# State: the current scenario and a version number that resets the input form
# --------------------------------------------------------------------------- #
if "scenario" not in st.session_state:
    st.session_state.scenario = load_scenario(next(iter(SAMPLES.values())))
    st.session_state.form_version = 0
    st.session_state.preset = next(iter(SAMPLES))


def _num(value, default=0.0) -> float:
    """Widget default from a stored amount (text or Decimal). Display only; the engine re-converts exactly."""
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return default


def _as_date(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def month_picker(label: str, default: date, key: str) -> date:
    c1, c2 = st.columns([2, 1])
    month = c1.selectbox(f"{label} — month", MONTHS, index=default.month - 1, key=f"{key}_m")
    year = c2.number_input(f"{label} — year", min_value=1950, max_value=2100, value=default.year, step=1,
                           key=f"{key}_y")
    return date(int(year), MONTHS.index(month) + 1, 1)


def money_input(label: str, value, key: str, help: str | None = None, min_value: float | None = 0.0) -> float:
    return st.number_input(label, value=_num(value), min_value=min_value, step=1000.0, format="%.2f", key=key,
                           help=help)


def _load_selected_sample() -> None:
    selected = st.session_state.preset_select
    st.session_state.scenario = load_scenario(SAMPLES[selected])
    st.session_state.preset = selected
    st.session_state.form_version += 1


# --------------------------------------------------------------------------- #
# Sidebar: presets
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("Scenario")
    preset = st.selectbox("Sample scenario (fictional data)", list(SAMPLES), key="preset_select",
                          on_change=_load_selected_sample)
    sc: Scenario = st.session_state.scenario
    st.caption(sc.description)
    currency = st.text_input("Currency label (display only)", value=sc.currency or "SAR",
                             key=f"currency_{st.session_state.form_version}")
    st.divider()
    st.caption(p.DISCLAIMER)

st.title("Accounting Standards Impact Simulator")
st.caption("IAS 16 — change in useful life or residual value (change in accounting estimate, IAS 8). "
           f"All amounts in {currency}.")
st.info(p.DISCLAIMER, icon="ℹ️")

tabs = st.tabs(["Executive Summary", "Scenario Setup", "Accounting Calculations", "Journal Entries",
                "Financial Statement Impact", "Ratio Analysis", "Rationale & References", "Validation Results",
                "Export Report"])
(t_summary, t_setup, t_calc, t_journal, t_impact, t_ratios, t_refs, t_valid, t_export) = tabs

# --------------------------------------------------------------------------- #
# Scenario Setup (inputs). Submitting replaces the current scenario.
# --------------------------------------------------------------------------- #
with t_setup:
    v = st.session_state.form_version
    a, per, rev = sc.inputs.asset, sc.inputs.period, sc.inputs.revision
    f, o = sc.financials, sc.opening
    with st.form(f"setup_{v}"):
        st.subheader("1. Asset")
        c1, c2, c3 = st.columns(3)
        with c1:
            cost = money_input("Cost", a.cost, f"cost_{v}")
        with c2:
            residual = money_input("Residual value (original estimate)", a.residual_value, f"res_{v}")
        with c3:
            life = st.number_input("Original TOTAL useful life (months)", min_value=0, step=1,
                                   value=int(_num(a.useful_life_months, 120)), key=f"life_{v}")
        available = month_picker("Available for use (depreciation starts this month)",
                                 _as_date(a.available_for_use_date), f"avail_{v}")
        st.caption("Method: straight-line (the only method in the MVP).")

        st.subheader("2. Reporting period and opening balance")
        c1, c2 = st.columns(2)
        with c1:
            period_start = month_picker("Period starts", _as_date(per.start_date), f"pstart_{v}")
        with c2:
            lengths = [12, 6, 3, 1]
            current_len = months_in_range(_as_date(per.start_date), _as_date(per.end_date))
            period_len = st.selectbox("Period length (months)", lengths,
                                      index=lengths.index(current_len) if current_len in lengths else 0,
                                      key=f"plen_{v}")
        period_end = end_of_month(add_months(period_start, period_len - 1))
        has_oad = sc.inputs.opening_accumulated_depreciation not in (None, "")
        use_ledger = st.checkbox("Enter opening accumulated depreciation from the ledger", value=has_oad,
                                 key=f"useoad_{v}",
                                 help="If unticked, it is CALCULATED from the original estimate and labelled as "
                                      "not verified against the ledger (V20).")
        opening_ad = money_input("Opening accumulated depreciation (ledger)",
                                 sc.inputs.opening_accumulated_depreciation, f"oad_{v}")

        st.subheader("3. Change in estimate (applied prospectively)")
        change_months = [add_months(period_start, i) for i in range(period_len)]
        default_change = _as_date(rev.effective_date) if rev and rev.effective_date else period_start
        change_date = st.selectbox(
            "Date of the change in estimate (when the new information arose)", change_months,
            index=change_months.index(default_change) if default_change in change_months else 0,
            format_func=lambda d: d.strftime("%d %b %Y"), key=f"chg_{v}")
        c1, c2 = st.columns(2)
        with c1:
            revised_life = st.number_input("Revised TOTAL useful life (months)", min_value=0, step=1,
                                           value=int(_num((rev.revised_useful_life_months if rev else None) or
                                                          a.useful_life_months, 120)), key=f"rlife_{v}")
        with c2:
            change_rv = st.checkbox("Also revise residual value",
                                    value=bool(rev and rev.revised_residual_value not in (None, "")), key=f"crv_{v}")
            revised_rv = money_input("Revised residual value", (rev.revised_residual_value if rev else None)
                                     or a.residual_value, f"rrv_{v}")

        st.subheader("4. Rest of the entity — same in both scenarios")
        c1, c2, c3 = st.columns(3)
        with c1:
            revenue = money_input("Revenue", f.revenue, f"rev_{v}")
            other_opex = money_input("Other operating expenses (excl. this depreciation)",
                                     f.other_operating_expenses, f"opex_{v}")
        with c2:
            other_income = money_input("Other income (negative = net expense)", f.other_income, f"oi_{v}",
                                       min_value=None)
            finance_costs = money_input("Finance costs", f.finance_costs, f"fc_{v}")
        with c3:
            other_assets = money_input("Other assets — closing (excl. this asset)", f.other_assets_closing,
                                       f"oa_{v}")
            liabilities = money_input("Total liabilities — closing", f.total_liabilities_closing, f"liab_{v}")

        st.subheader("5. Opening statement of financial position")
        c1, c2, c3 = st.columns(3)
        with c1:
            opening_assets = money_input("Opening total assets (incl. this asset)", o.total_assets, f"ota_{v}")
        with c2:
            opening_liabilities = money_input("Opening total liabilities", o.total_liabilities, f"otl_{v}")
        with c3:
            opening_equity = money_input("Opening equity (may be negative)", f.opening_equity, f"oe_{v}",
                                         min_value=None)

        if st.form_submit_button("Calculate", type="primary"):
            # Floats from the widgets are converted exactly to Decimal at the engine boundary.
            st.session_state.scenario = Scenario(
                title=f"{st.session_state.preset} (edited)", description="Inputs edited in the app.",
                currency=currency,
                inputs=SimulationInput(
                    asset=AssetInput(cost, residual, int(life), available),
                    period=ReportingPeriod(period_start, period_end),
                    revision=EstimateRevision(change_date, int(revised_life), revised_rv if change_rv else None),
                    opening_accumulated_depreciation=opening_ad if use_ledger else None),
                financials=EntityFinancials(revenue, other_opex, other_income, finance_costs, other_assets,
                                            liabilities, opening_equity),
                opening=OpeningPosition(opening_assets, opening_liabilities))
            st.rerun()

sc = st.session_state.scenario
result = run_impact_analysis(sc.inputs, sc.financials, sc.opening)
level, title, body = p.status_banner(result)
banner = {"success": st.success, "warning": st.warning, "error": st.error}[level]


def section_header(section: str) -> bool:
    """Show the section's status note. Returns False when the section is withheld."""
    note = p.section_note(result, section)
    if note is None:
        return True
    kind, text = note
    if kind == "withheld":
        st.error(text, icon="⛔")
        return False
    st.info(text, icon="✅")
    return True


def table(df):
    st.dataframe(df, hide_index=True, use_container_width=True)


# --------------------------------------------------------------------------- #
# Executive Summary
# --------------------------------------------------------------------------- #
with t_summary:
    banner(f"**{title}** — {body}")
    st.markdown(f"**Scenario:** {sc.title}")
    for line in p.executive_summary(result):
        st.markdown(f"- {line}")
    figures = p.key_figures(result)
    if figures:
        cols = st.columns(len(figures))
        for col, (label, value) in zip(cols, figures.items()):
            col.metric(label, value)

# --------------------------------------------------------------------------- #
# Accounting Calculations
# --------------------------------------------------------------------------- #
with t_calc:
    banner(f"**{title}**")
    st.markdown(
        "**How the change is applied (prospectively).** At the date of the change E:\n\n"
        "- carrying amount at E = cost − accumulated depreciation at E\n"
        "- remaining depreciable amount = max(0, carrying amount at E − revised residual value)\n"
        "- remaining life = revised **total** life − months already elapsed\n"
        "- depreciation = remaining depreciable amount × months ÷ remaining life\n\n"
        "Months before E keep the original estimate. Depreciation already recorded is not recalculated, and "
        "nothing is posted to opening retained earnings.")
    if result.depreciation.baseline is not None and section_header("depreciation"):
        st.markdown("**Rate segments**")
        table(p.depreciation_table(result))
        st.markdown("**Balances**")
        table(p.balances_table(result))
        for label, pd_ in (("Calculation trail — revised", result.depreciation.scenario),
                           ("Calculation trail — baseline", result.depreciation.baseline)):
            with st.expander(label):
                table(p.trace_table(pd_))
    elif result.depreciation.baseline is None:
        st.error("No calculation: the depreciation inputs failed validation. See Validation Results.")

# --------------------------------------------------------------------------- #
# Journal Entries
# --------------------------------------------------------------------------- #
with t_journal:
    if section_header("journal entries"):
        st.caption("One entry per rate segment, dated at the segment end. There is no entry for the revision itself "
                   "and none against opening retained earnings (prospective treatment). No tax entries.")
        st.markdown("**Revised scenario**")
        table(p.journal_table(result.scenario_entries))
        st.markdown("**Baseline (original estimate)**")
        table(p.journal_table(result.baseline_entries))

# --------------------------------------------------------------------------- #
# Financial Statement Impact
# --------------------------------------------------------------------------- #
with t_impact:
    st.markdown("#### Opening statement of financial position")
    if section_header("opening position"):
        table(p.opening_table(result))
    st.markdown("#### Baseline vs revised")
    if section_header("impact table"):
        table(p.impact_table(result))
        st.caption("The asset's carrying amount and total assets are shown separately. They move by the same amount "
                   "here only because other assets are an unchanged input and no tax is modelled.")
        if go is not None:
            keys = ["Depreciation expense", "Profit before tax", "Asset carrying amount (this asset)",
                    "Total assets", "Closing equity"]
            lines = [ln for ln in result.impact if ln.metric in keys]
            fig = go.Figure([
                # float() is used for drawing only; the table above is the authoritative figure.
                go.Bar(name="Baseline", x=[ln.metric for ln in lines], y=[float(ln.baseline) for ln in lines]),
                go.Bar(name="Revised", x=[ln.metric for ln in lines], y=[float(ln.scenario) for ln in lines]),
            ])
            fig.update_layout(barmode="group", height=380, margin=dict(t=30, b=10),
                              yaxis_title=currency, legend_orientation="h")
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("#### Financial statements")
        table(p.statements_table(result))

# --------------------------------------------------------------------------- #
# Ratio Analysis
# --------------------------------------------------------------------------- #
with t_ratios:
    if section_header("ratios"):
        st.caption("Ratios are indirect effects of the depreciation change. 'Simplified' ratios use closing (not "
                   "average) assets and total liabilities (not interest-bearing debt).")
        table(p.ratio_table(result))
        for issue in result.issues:
            if issue.code == "V25":
                st.info(issue.message, icon="ℹ️")

# --------------------------------------------------------------------------- #
# Rationale & References
# --------------------------------------------------------------------------- #
with t_refs:
    st.markdown(
        "**Is this a change in accounting estimate?** The simulator assumes it is: new information or "
        "developments changed the expected useful life or residual value. If the original estimate ignored "
        "information that was available at the time, it is a prior-period error (retrospective restatement), "
        "which is outside this tool. A change of depreciation method or measurement model is also outside the MVP.\n\n"
        "**Prospective treatment.** The effect is recognised in the period of the change and later periods; "
        "earlier depreciation is not restated.\n\n"
        "**Residual value at or above carrying amount.** Depreciation is zero until the residual value falls "
        "below the carrying amount; no negative depreciation is recognised.\n\n"
        "**Verification status.** References are labelled honestly: 'pending' means not yet checked against the "
        "IFRS Foundation's primary text. Confirmed entries were checked against the official issued-standard text; "
        "AASB-corroborated entries are not marked as IFRS-confirmed.\n\n"
        "**Official sources checked (2026 issued text):** [IAS 16](https://www.ifrs.org/content/dam/ifrs/publications/html-standards/english/2026/issued/ias16.html) · "
        "[IAS 8](https://www.ifrs.org/content/dam/ifrs/publications/html-standards/english/2026/issued/ias8.html) · "
        "[IFRS 18 overview](https://www.ifrs.org/issued-standards/list-of-standards/ifrs-18-presentation-and-disclosure-in-financial-statements/).")
    table(p.references_table())

# --------------------------------------------------------------------------- #
# Validation Results
# --------------------------------------------------------------------------- #
with t_valid:
    banner(f"**{title}** — {body}")
    if result.status != COMPLETE:
        st.code(result.summary, language=None)
    issues = p.issues_table(result)
    if issues.empty:
        st.success("No errors, warnings or notes.")
    else:
        table(issues)

# --------------------------------------------------------------------------- #
# Export Report
# --------------------------------------------------------------------------- #
with t_export:
    export_sc = Scenario(sc.title, sc.description, currency, sc.inputs, sc.financials, sc.opening)
    markdown_report = build_markdown_report(export_sc, result)
    st.markdown(f"Status in the report: **{result.status}**. Withheld sections are stated as withheld.")
    c1, c2 = st.columns(2)
    c1.download_button("Download report (Markdown)", markdown_report, file_name="impact_report.md",
                       mime="text/markdown", use_container_width=True)
    c2.download_button("Download data (JSON)", build_json_report(export_sc, result), file_name="impact_report.json",
                       mime="application/json", use_container_width=True)
    with st.expander("Preview report"):
        st.markdown(markdown_report)
