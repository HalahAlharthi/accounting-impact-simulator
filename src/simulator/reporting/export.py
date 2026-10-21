"""Structured report export: Markdown (to read or print) and JSON (machine-readable).

Both are built from the same presentation tables the app shows, so the export
cannot disagree with the screen. Withheld sections are stated as withheld,
never left out silently.
"""
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from fractions import Fraction

import pandas as pd

from simulator.impact import ImpactResult
from simulator.reporting import presentation as p
from simulator.scenarios import Scenario


def _md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_None._"
    cols = list(df.columns)
    esc = lambda v: str(v).replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(esc(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join(lines)


def _inputs_table(sc: Scenario) -> pd.DataFrame:
    a, per, r = sc.inputs.asset, sc.inputs.period, sc.inputs.revision
    f, o = sc.financials, sc.opening
    rows = [
        ("Cost", a.cost), ("Residual value", a.residual_value), ("Original useful life (months)", a.useful_life_months),
        ("Available for use", a.available_for_use_date), ("Method", a.method),
        ("Reporting period", f"{per.start_date} to {per.end_date}"),
        ("Opening accumulated depreciation", sc.inputs.opening_accumulated_depreciation
         if sc.inputs.opening_accumulated_depreciation not in (None, "") else "not entered (calculated)"),
        ("Date of change in estimate", r.effective_date if r else None),
        ("Revised total useful life (months)", (r.revised_useful_life_months if r else None) or "unchanged"),
        ("Revised residual value", (r.revised_residual_value if r else None) or "unchanged"),
        ("Revenue", f.revenue), ("Other operating expenses", f.other_operating_expenses),
        ("Other income", f.other_income), ("Finance costs", f.finance_costs),
        ("Other assets (closing)", f.other_assets_closing), ("Total liabilities (closing)", f.total_liabilities_closing),
        ("Opening equity", f.opening_equity), ("Opening total assets", o.total_assets),
        ("Opening total liabilities", o.total_liabilities),
    ]
    return pd.DataFrame([{"Input": k, "Value": "—" if v is None else str(v)} for k, v in rows])


def build_markdown_report(sc: Scenario, result: ImpactResult) -> str:
    level, title, body = p.status_banner(result)
    out = [f"# Accounting Standards Impact Simulator — report", "",
           f"**Scenario:** {sc.title}", "", f"**Currency:** {sc.currency or 'not stated'}", "",
           f"> {p.DISCLAIMER}", "", f"## Status: {title}", "", body, "",
           "## Executive summary", "", *[f"- {line}" for line in p.executive_summary(result)], "",
           "## Inputs", "", _md_table(_inputs_table(sc)), ""]

    def section(name: str, heading: str, *tables: pd.DataFrame):
        out.extend([f"## {heading}", ""])
        note = p.section_note(result, name)
        if note and note[0] == "withheld":
            out.extend([f"**Withheld.** {note[1]}", ""])
            return
        if note:
            out.extend([f"_{note[1]}_", ""])
        for t in tables:
            out.extend([_md_table(t), ""])

    dep = result.depreciation
    section("depreciation", "Depreciation", p.depreciation_table(result), p.balances_table(result))
    if dep.scenario is not None:
        out.extend(["### Calculation trace (revised)", "", _md_table(p.trace_table(dep.scenario)), ""])
    section("journal entries", "Journal entries — revised", p.journal_table(result.scenario_entries))
    section("opening position", "Opening statement of financial position", p.opening_table(result))
    section("statements", "Financial statements", p.statements_table(result))
    section("impact table", "Financial statement impact", p.impact_table(result))
    section("ratios", "Ratio analysis", p.ratio_table(result))
    out.extend(["## Validation results", "", _md_table(p.issues_table(result)), "",
                "## References and verification status", "", _md_table(p.references_table()), ""])
    return "\n".join(out)


def _plain(obj):
    if isinstance(obj, (Decimal, Fraction)):
        return str(obj)
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if is_dataclass(obj):
        return {k: _plain(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    return obj


def build_json_report(sc: Scenario, result: ImpactResult) -> str:
    """Amounts are strings (exact). Withheld sections are null and listed in 'withheld_sections'."""
    data = {
        "scenario": sc.title, "currency": sc.currency, "disclaimer": p.DISCLAIMER,
        "status": result.status, "released_sections": list(result.released_sections),
        "withheld_sections": list(result.withheld_sections), "summary": result.summary,
        "inputs": {"asset": sc.inputs, "financials": sc.financials, "opening_position": sc.opening},
        "depreciation": {"baseline": result.depreciation.baseline, "revised": result.depreciation.scenario,
                         "opening_balance_source": result.depreciation.opening_balance_source},
        "journal_entries": {"baseline": result.baseline_entries, "revised": result.scenario_entries}
        if "journal entries" in result.released_sections else None,
        "opening_position": result.opening_statement,
        "statements": {"baseline": result.baseline_statements, "revised": result.scenario_statements}
        if result.baseline_statements is not None else None,
        "ratios": [{"name": r.name, "baseline": r.display_baseline, "revised": r.display_scenario,
                    "change": r.display_change, "unit": r.unit,
                    "not_meaningful_reason": r.baseline_reason or r.scenario_reason} for r in result.ratios] or None,
        "issues": result.issues,
    }
    return json.dumps(_plain(data), indent=2, ensure_ascii=False)
