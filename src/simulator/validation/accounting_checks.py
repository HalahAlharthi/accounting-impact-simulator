"""Checks on journal-driven statements. They report; they never adjust.

V11 — accounting equation: assets = liabilities + equity, exactly, in each scenario.
V12 — reconciliation: statements agree with the depreciation result and the
      journal entries, and the baseline-to-scenario differences are explained
      by depreciation alone.
V14 / V24 — missing or negative rest-of-entity inputs.
"""
from __future__ import annotations

from decimal import Decimal

from simulator.journal.entries import JournalEntry, expense_total
from simulator.models import EntityFinancials, PeriodDepreciation, Severity, ValidationIssue
from simulator.money import fmt
from simulator.statements.builder import FinancialStatements
from simulator.validation.coerce import FINANCIAL_FIELDS

# V24 field rules (approved). Under the MVP assumptions these cannot be negative.
# other_income (a net other expense is negative) and opening_equity (accumulated
# losses) MAY be negative. Any further exception must be documented in
# docs/assumptions_and_limitations.md before being allowed.
NON_NEGATIVE = ("revenue", "other_operating_expenses", "finance_costs", "other_assets_closing",
                "total_liabilities_closing")
MAY_BE_NEGATIVE = ("other_income", "opening_equity")


def _err(code: str, message: str, field: str | None = None, fix: str | None = None) -> ValidationIssue:
    return ValidationIssue(code=code, severity=Severity.ERROR, message=message, field=field, fix=fix)


def validate_financials(fin: EntityFinancials) -> list[ValidationIssue]:
    issues = [_err("V14", f"Missing required input: {name}.", name, f"Enter a value for '{name}' (0 if none).")
              for name in FINANCIAL_FIELDS if getattr(fin, name) is None]
    if issues:
        return issues
    for name in NON_NEGATIVE:
        if getattr(fin, name) < 0:
            issues.append(_err("V24", f"'{name}' must not be negative (entered {getattr(fin, name)}).", name))
    return issues


def check_accounting_equation(fs: FinancialStatements, override_difference: Decimal | None = None
                              ) -> list[ValidationIssue]:
    """V11. `override_difference` = entered minus implied opening accumulated depreciation, if any.

    When the imbalance equals that override, the most likely cause is that the
    statement inputs (e.g. opening equity) were prepared on the implied balance,
    not on the ledger balance the user entered; the message says so.
    """
    diff = fs.equation_difference
    if diff == 0:
        return []
    message = (f"[{fs.scenario}] Accounting equation does not balance: total assets {fmt(fs.total_assets)} vs "
               f"liabilities {fmt(fs.total_liabilities)} + equity {fmt(fs.closing_equity)} = "
               f"{fmt(fs.total_liabilities + fs.closing_equity)}; difference (assets − liabilities − equity) "
               f"{fmt(diff)}. No balancing figure has been posted; statements and ratios are withheld.")
    fix = "Check other assets, liabilities and opening equity against the same trial balance."
    if override_difference and abs(diff) == abs(override_difference):
        fix = (f"The difference equals your opening accumulated depreciation override ({fmt(override_difference)} "
               f"versus the implied balance). Opening equity or other balances may still reflect the implied "
               f"figure; enter all balances from the same ledger.")
    return [_err("V11", message, "statement_inputs", fix)]


def check_statement_reconciliation(fs: FinancialStatements, pd: PeriodDepreciation,
                                   entries: tuple[JournalEntry, ...]) -> list[ValidationIssue]:
    """V12: recompute each derived line and compare with the engine and journal totals."""
    s = f"[{fs.scenario}]"
    checks = [
        ("depreciation vs journal entries", fs.depreciation, expense_total(entries)),
        ("depreciation vs depreciation engine", fs.depreciation, pd.depreciation),
        ("accumulated depreciation vs engine closing balance", fs.accumulated_depreciation,
         pd.closing_accumulated_depreciation),
        ("carrying amount vs cost − accumulated depreciation", fs.ppe_carrying_amount,
         fs.ppe_cost - fs.accumulated_depreciation),
        ("total assets vs other assets + carrying amount", fs.total_assets, fs.other_assets + fs.ppe_carrying_amount),
        ("operating profit vs revenue − other operating expenses − depreciation", fs.operating_profit,
         fs.revenue - fs.other_operating_expenses - fs.depreciation),
        ("profit before tax vs operating profit + other income − finance costs", fs.profit_before_tax,
         fs.operating_profit + fs.other_income - fs.finance_costs),
        ("closing equity vs opening equity + profit before tax", fs.closing_equity,
         fs.opening_equity + fs.profit_before_tax),
    ]
    return [_err("V12", f"{s} {name}: {fmt(shown)} vs {fmt(expected)}; difference {fmt(shown - expected)}.",
                 fix="Nothing has been adjusted.")
            for name, shown, expected in checks if shown != expected]


def check_scenario_reconciliation(base: FinancialStatements, scen: FinancialStatements) -> list[ValidationIssue]:
    """V12: the only cause of difference between the scenarios is depreciation."""
    d_dep = scen.depreciation - base.depreciation
    checks = [
        ("revenue", scen.revenue - base.revenue, Decimal(0)),
        ("other assets", scen.other_assets - base.other_assets, Decimal(0)),
        ("liabilities", scen.total_liabilities - base.total_liabilities, Decimal(0)),
        ("profit before tax", scen.profit_before_tax - base.profit_before_tax, -d_dep),
        ("carrying amount", scen.ppe_carrying_amount - base.ppe_carrying_amount, -d_dep),
        ("total assets", scen.total_assets - base.total_assets, -d_dep),
        ("closing equity", scen.closing_equity - base.closing_equity, -d_dep),
    ]
    return [_err("V12", f"Change in {name} ({fmt(actual)}) is not explained by the change in depreciation "
                        f"(expected {fmt(expected)}).", fix="Nothing has been adjusted.")
            for name, actual, expected in checks if actual != expected]
