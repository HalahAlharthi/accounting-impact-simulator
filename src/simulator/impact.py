"""End-to-end impact analysis: depreciation -> journal entries -> opening check -> statements -> ratios.

This is the single function the user interface (Phase 4) will call.

Order of work, and what is released when something fails (nothing is ever plugged):
1. Depreciation (simulate). Errors -> status FAILED; nothing is released.
2. Journal entries + V10. Errors -> status PARTIAL; only depreciation is released.
3. Rest-of-entity and opening-position inputs: conversion (V22/V23), missing (V14),
   negative by field type (V24). Errors -> status PARTIAL.
4. Opening position: V26 opening A = L + E, V27 opening assets include this asset.
   Errors -> status PARTIAL.
5. Closing statements for both scenarios: V12 line reconciliation, V11 accounting
   equation, V12 scenario reconciliation. Errors -> status PARTIAL.
Only when every step passes is the status COMPLETE.

In a PARTIAL result, only the sections that passed their own checks are released
(`released_sections`: depreciation, then journal entries if V10 passed, then the
opening position if V26/V27 passed), each labelled "validated independently".
Everything after the failing step is withheld, and `summary` quotes the exact
errors. A PARTIAL result is never reported as a successful scenario.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from simulator.ias16.useful_life import simulate
from simulator.journal.entries import JournalEntry, build_journal_entries, check_journal_entries
from simulator.models import (
    EntityFinancials,
    OpeningPosition,
    Severity,
    SimulationInput,
    SimulationResult,
    ValidationIssue,
)
from simulator.ratios.analysis import RatioResult, calculate_ratios
from simulator.statements.builder import FinancialStatements, build_statements
from simulator.statements.opening import OpeningStatement, check_opening_position, validate_opening_inputs
from simulator.validation.accounting_checks import (
    check_accounting_equation,
    check_scenario_reconciliation,
    check_statement_reconciliation,
    validate_financials,
)
from simulator.validation.coerce import normalize_financials, normalize_opening

DIRECT, UNCHANGED = "direct effect", "unchanged input"
COMPLETE, PARTIAL, FAILED = "complete", "partial", "failed"
SECTIONS = ("depreciation", "journal entries", "opening position", "statements", "impact table", "ratios")


@dataclass(frozen=True)
class ImpactLine:
    metric: str
    baseline: Decimal
    scenario: Decimal
    effect: str
    explanation: str

    @property
    def change(self) -> Decimal:
        return self.scenario - self.baseline


@dataclass(frozen=True)
class ImpactResult:
    issues: tuple[ValidationIssue, ...]
    depreciation: SimulationResult
    baseline_entries: tuple[JournalEntry, ...] = ()
    scenario_entries: tuple[JournalEntry, ...] = ()
    opening_statement: OpeningStatement | None = None
    baseline_statements: FinancialStatements | None = None
    scenario_statements: FinancialStatements | None = None
    impact: tuple[ImpactLine, ...] = field(default_factory=tuple)
    ratios: tuple[RatioResult, ...] = field(default_factory=tuple)
    released_sections: tuple[str, ...] = ()

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity is Severity.ERROR)

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def status(self) -> str:
        if self.ok:
            return COMPLETE
        return PARTIAL if self.released_sections else FAILED

    @property
    def withheld_sections(self) -> tuple[str, ...]:
        return tuple(s for s in SECTIONS if s not in self.released_sections)

    @property
    def summary(self) -> str:
        if self.status == COMPLETE:
            return "Scenario complete: all validation checks passed."
        errors = " | ".join(f"{i.code}: {i.message}" for i in self.errors)
        if self.status == FAILED:
            return f"Scenario FAILED: no results released. Errors — {errors}"
        return (f"Scenario NOT complete. Validated independently and shown: {', '.join(self.released_sections)}. "
                f"Withheld: {', '.join(self.withheld_sections)}. Errors — {errors}")

    def codes(self) -> set[str]:
        return {i.code for i in self.issues}


def _impact_lines(b: FinancialStatements, s: FinancialStatements) -> tuple[ImpactLine, ...]:
    return (
        ImpactLine("Revenue", b.revenue, s.revenue, UNCHANGED, "Input; identical in both scenarios."),
        ImpactLine("Depreciation expense", b.depreciation, s.depreciation, DIRECT,
                   "Prospective change in estimate: current period only, no catch-up."),
        ImpactLine("Operating profit", b.operating_profit, s.operating_profit, DIRECT,
                   "Moves by the change in depreciation."),
        ImpactLine("Profit before tax", b.profit_before_tax, s.profit_before_tax, DIRECT,
                   "Moves by the change in depreciation (pre-tax model)."),
        ImpactLine("Asset carrying amount (this asset)", b.ppe_carrying_amount, s.ppe_carrying_amount, DIRECT,
                   "Cost − accumulated depreciation for the revised asset only."),
        ImpactLine("Total assets", b.total_assets, s.total_assets, DIRECT,
                   "Other assets are an unchanged input, so total assets move by the carrying-amount change. "
                   "With tax, deferred tax would make these differ."),
        ImpactLine("Total liabilities", b.total_liabilities, s.total_liabilities, UNCHANGED,
                   "Depreciation is non-cash; no tax modelled."),
        ImpactLine("Retained earnings movement (profit for the period)", b.retained_earnings_movement,
                   s.retained_earnings_movement, DIRECT, "Profit before tax; no tax, dividends or OCI."),
        ImpactLine("Closing equity", b.closing_equity, s.closing_equity, DIRECT, "Opening equity + profit before tax."),
    )


def run_impact_analysis(inp: SimulationInput, fin: EntityFinancials, opening: OpeningPosition) -> ImpactResult:
    # 1. Depreciation
    dep = simulate(inp)
    if not dep.ok:
        return ImpactResult(issues=dep.issues, depreciation=dep)
    issues = list(dep.issues)
    released = ["depreciation"]

    def partial(extra: list[ValidationIssue], **kw) -> ImpactResult:
        return ImpactResult(issues=tuple(issues + extra), depreciation=dep, released_sections=tuple(released), **kw)

    # 2. Journal entries
    base_entries = build_journal_entries(dep.baseline)
    scen_entries = build_journal_entries(dep.scenario)
    journal_issues = check_journal_entries(base_entries) + check_journal_entries(scen_entries)
    if journal_issues:
        return partial(journal_issues)
    released.append("journal entries")
    entries = dict(baseline_entries=base_entries, scenario_entries=scen_entries)

    # 3. Statement inputs (rest of entity + opening position)
    fin, fin_conv = normalize_financials(fin)
    opening, open_conv = normalize_opening(opening)
    input_issues = fin_conv + open_conv
    if not input_issues:
        input_issues = validate_financials(fin) + validate_opening_inputs(opening)
    if input_issues:
        return partial(input_issues, **entries)

    # 4. Opening position (independent of the depreciation calculation)
    # Depreciation starts at max(period start, available-for-use date), so the asset was in use at the
    # period start exactly when its first segment starts on the period start.
    first = dep.baseline.segments[0] if dep.baseline.segments else None
    in_use_at_start = first is None or first.start_date == dep.baseline.period_start
    opening_stmt, opening_issues = check_opening_position(
        opening, fin.opening_equity, dep.baseline.opening_carrying_amount if in_use_at_start else None)
    if any(i.severity is Severity.ERROR for i in opening_issues):
        return partial(opening_issues, **entries)
    issues += opening_issues  # e.g. info V28
    released.append("opening position")
    entries["opening_statement"] = opening_stmt

    # 5. Closing statements
    base_fs = build_statements(dep.baseline, base_entries, fin)
    scen_fs = build_statements(dep.scenario, scen_entries, fin)
    override = None
    if dep.opening_balance_source == "entered":
        override = dep.baseline.opening_accumulated_depreciation - dep.implied_opening_accumulated_depreciation
    statement_issues = (check_statement_reconciliation(base_fs, dep.baseline, base_entries)
                        + check_statement_reconciliation(scen_fs, dep.scenario, scen_entries)
                        + check_accounting_equation(base_fs, override)
                        + check_accounting_equation(scen_fs, override)
                        + check_scenario_reconciliation(base_fs, scen_fs))
    if statement_issues:
        return partial(statement_issues, **entries)

    ratios = calculate_ratios(base_fs, scen_fs)
    for ratio in (r for r in ratios if r.baseline is None or r.scenario is None):
        issues.append(ValidationIssue("V25", Severity.INFO, f"{ratio.name}: not meaningful "
                                      f"({ratio.baseline_reason or ratio.scenario_reason}). No number is shown."))
    return ImpactResult(
        issues=tuple(issues), depreciation=dep,
        baseline_statements=base_fs, scenario_statements=scen_fs, impact=_impact_lines(base_fs, scen_fs),
        ratios=ratios, released_sections=SECTIONS, **entries,
    )
