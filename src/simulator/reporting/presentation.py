"""Display-ready tables built from an ImpactResult.

This layer turns engine results into pandas DataFrames of formatted strings.
It performs NO accounting calculations: every number shown is formatted
directly from an engine value, so tests can prove the UI shows what the engine
calculated. Both the Streamlit app and the report export use these tables.
"""
from __future__ import annotations

from decimal import Decimal

import pandas as pd

from simulator.impact import COMPLETE, FAILED, ImpactResult
from simulator.journal.entries import JournalEntry
from simulator.models import PeriodDepreciation, Severity
from simulator.money import fmt
from simulator.ratios.analysis import PERCENT, RatioResult
from simulator.references import REFERENCES

DISCLAIMER = (
    "Educational tool only. Results depend on the inputs and on the stated assumptions; they are not accounting, "
    "audit or tax advice. Whether a change is a change in accounting estimate, a correction of an error or a change "
    "in accounting policy depends on the facts and circumstances and requires professional judgment."
)
VALIDATED_INDEPENDENTLY = "Validated independently — shown although the scenario is not complete."


def money(value: Decimal | None) -> str:
    return "—" if value is None else fmt(value)


def signed(value: Decimal) -> str:
    return f"+{fmt(value)}" if value > 0 else fmt(value)


# --------------------------------------------------------------------------- #
# Status
# --------------------------------------------------------------------------- #


def status_banner(result: ImpactResult) -> tuple[str, str, str]:
    """(level, title, body) — level is 'success', 'warning' or 'error'."""
    if result.status == COMPLETE:
        return "success", "Scenario complete", "All validation checks passed."
    if result.status == FAILED:
        return "error", "Scenario failed — no results released", "Correct the errors listed under Validation Results."
    return ("warning", "Scenario NOT complete — partial result",
            f"Shown (validated independently): {', '.join(result.released_sections)}. "
            f"Withheld: {', '.join(result.withheld_sections)}. See Validation Results for the exact errors.")


def section_note(result: ImpactResult, section: str) -> tuple[str, str] | None:
    """How to label a section: None (complete), ('info', validated-independently note) or ('withheld', reason)."""
    if result.status == COMPLETE:
        return None
    if section in result.released_sections:
        return "info", VALIDATED_INDEPENDENTLY
    first_error = result.errors[0] if result.errors else None
    reason = f"{first_error.code}: {first_error.message}" if first_error else "an earlier check failed"
    return "withheld", f"Withheld because a validation check failed — {reason}"


def key_figures(result: ImpactResult) -> dict[str, str] | None:
    dep = result.depreciation
    if dep.baseline is None:
        return None
    return {
        "Depreciation — baseline": fmt(dep.baseline.depreciation),
        "Depreciation — revised": fmt(dep.scenario.depreciation),
        "Change in depreciation": signed(dep.change_in_depreciation),
        "Closing carrying amount — baseline": fmt(dep.baseline.closing_carrying_amount),
        "Closing carrying amount — revised": fmt(dep.scenario.closing_carrying_amount),
    }


def executive_summary(result: ImpactResult) -> list[str]:
    dep = result.depreciation
    if dep.baseline is None:
        return ["No figures are available: the depreciation inputs failed validation."]
    b, s = dep.baseline, dep.scenario
    lines = [
        f"Depreciation for the period changes from {fmt(b.depreciation)} to {fmt(s.depreciation)} "
        f"({signed(s.depreciation - b.depreciation)}), applied prospectively from the date of the change.",
        f"The asset's closing carrying amount changes from {fmt(b.closing_carrying_amount)} to "
        f"{fmt(s.closing_carrying_amount)}.",
        f"Opening accumulated depreciation of {fmt(b.opening_accumulated_depreciation)} is "
        + ("taken from your ledger entry." if dep.opening_balance_source == "entered"
           else "CALCULATED from the original estimate and not verified against the ledger."),
    ]
    if result.baseline_statements is not None:
        bs, ss = result.baseline_statements, result.scenario_statements
        lines.append(f"Profit before tax changes by {signed(ss.profit_before_tax - bs.profit_before_tax)}; "
                     f"total assets and closing equity change by the same amount (pre-tax model).")
    else:
        lines.append("Statements, the impact table and ratios are withheld: see Validation Results.")
    return lines


# --------------------------------------------------------------------------- #
# Tables
# --------------------------------------------------------------------------- #


def depreciation_table(result: ImpactResult) -> pd.DataFrame:
    rows = []
    for pd_ in (result.depreciation.baseline, result.depreciation.scenario):
        if pd_ is None:
            continue
        for seg in pd_.segments:
            rows.append({
                "Scenario": pd_.scenario.capitalize(),
                "Months": f"{seg.start_date:%b %Y}–{seg.end_date:%b %Y} ({seg.months})",
                "Estimate": seg.estimate_label,
                "Carrying amount at start": fmt(seg.carrying_amount_at_start),
                "Residual value": fmt(seg.residual_value),
                "Remaining life (months)": str(seg.remaining_life_months),
                "Remaining depreciable amount": fmt(seg.remaining_depreciable_amount),
                "Depreciation": fmt(seg.depreciation),
            })
    return pd.DataFrame(rows)


def balances_table(result: ImpactResult) -> pd.DataFrame:
    dep = result.depreciation
    if dep.baseline is None:
        return pd.DataFrame()
    def row(label, getter):
        b, s = getter(dep.baseline), getter(dep.scenario)
        return {"Item": label, "Baseline": fmt(b), "Revised": fmt(s), "Change": signed(s - b)}
    return pd.DataFrame([
        row("Opening accumulated depreciation", lambda p: p.opening_accumulated_depreciation),
        row("Opening carrying amount", lambda p: p.opening_carrying_amount),
        row("Depreciation for the period", lambda p: p.depreciation),
        row("Closing accumulated depreciation", lambda p: p.closing_accumulated_depreciation),
        row("Closing carrying amount", lambda p: p.closing_carrying_amount),
    ])


def trace_table(pd_: PeriodDepreciation) -> pd.DataFrame:
    return pd.DataFrame([{"Step": t.label, "Formula": t.formula, "Calculation": t.substitution, "Result": t.result,
                          "Reference": "; ".join(t.references)} for t in pd_.trace])


def journal_table(entries: tuple[JournalEntry, ...]) -> pd.DataFrame:
    rows = []
    for e in entries:
        for ln in e.lines:
            rows.append({"Date": e.entry_date.isoformat(), "Account": ln.account,
                         "Debit": fmt(ln.debit) if ln.debit else "", "Credit": fmt(ln.credit) if ln.credit else "",
                         "Narrative": e.description})
    return pd.DataFrame(rows)


def opening_table(result: ImpactResult) -> pd.DataFrame:
    o = result.opening_statement
    if o is None:
        return pd.DataFrame()
    return pd.DataFrame([
        {"Item": "Opening total assets", "Amount": fmt(o.total_assets)},
        {"Item": "  of which this asset (opening carrying amount)", "Amount": money(o.asset_carrying_amount)},
        {"Item": "  of which other assets (derived)", "Amount": money(o.other_assets)},
        {"Item": "Opening total liabilities", "Amount": fmt(o.total_liabilities)},
        {"Item": "Opening equity", "Amount": fmt(o.equity)},
        {"Item": "Check: assets − liabilities − equity", "Amount": fmt(o.equation_difference)},
    ])


def statements_table(result: ImpactResult) -> pd.DataFrame:
    b, s = result.baseline_statements, result.scenario_statements
    if b is None:
        return pd.DataFrame()
    lines = [
        ("Income statement", None), ("Revenue", "revenue"), ("Other operating expenses", "other_operating_expenses"),
        ("Depreciation", "depreciation"), ("Operating profit", "operating_profit"), ("Other income", "other_income"),
        ("Finance costs", "finance_costs"), ("Profit before tax", "profit_before_tax"),
        ("Statement of financial position (closing)", None), ("PPE — cost", "ppe_cost"),
        ("PPE — accumulated depreciation", "accumulated_depreciation"),
        ("PPE — carrying amount (this asset)", "ppe_carrying_amount"), ("Other assets", "other_assets"),
        ("Total assets", "total_assets"), ("Total liabilities", "total_liabilities"),
        ("Opening equity", "opening_equity"), ("Closing equity", "closing_equity"),
        ("Check: assets − liabilities − equity", "equation_difference"),
    ]
    rows = []
    for label, attr in lines:
        if attr is None:
            rows.append({"Line": label, "Baseline": "", "Revised": "", "Change": ""})
            continue
        bv, sv = getattr(b, attr), getattr(s, attr)
        rows.append({"Line": label, "Baseline": fmt(bv), "Revised": fmt(sv), "Change": signed(sv - bv)})
    return pd.DataFrame(rows)


def impact_table(result: ImpactResult) -> pd.DataFrame:
    return pd.DataFrame([{"Metric": ln.metric, "Baseline": fmt(ln.baseline), "Revised": fmt(ln.scenario),
                          "Change": signed(ln.change), "Effect": ln.effect, "Why": ln.explanation}
                         for ln in result.impact])


def _ratio_value(r: RatioResult, value) -> str:
    shown = r._display(value)
    if shown is None:
        return "Not meaningful"
    return f"{shown}%" if r.unit == PERCENT else f"{shown}×"


def ratio_table(result: ImpactResult) -> pd.DataFrame:
    rows = []
    for r in result.ratios:
        if r.change is None:
            change = "Not meaningful"
        else:
            d = r.display_change
            change = f"{'+' if d > 0 else ''}{d} pp" if r.unit == PERCENT else f"{'+' if d > 0 else ''}{d}×"
        note = r.baseline_reason or r.scenario_reason
        rows.append({"Ratio": r.name, "Formula": r.formula, "Baseline": _ratio_value(r, r.baseline),
                     "Revised": _ratio_value(r, r.scenario), "Change": change,
                     "Why it changed": r.explanation if note is None else f"Not meaningful: {note}"})
    return pd.DataFrame(rows)


def issues_table(result: ImpactResult) -> pd.DataFrame:
    order = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2}
    return pd.DataFrame([{"Severity": i.severity.value.upper(), "Code": i.code, "Field": i.field or "",
                          "Message": i.message, "What to do": i.fix or ""}
                         for i in sorted(result.issues, key=lambda i: order[i.severity])])


def references_table() -> pd.DataFrame:
    return pd.DataFrame([{"Reference": r.code, "What it supports (our summary)": r.supports,
                          "Verification status": r.status.value} for r in REFERENCES.values()])
