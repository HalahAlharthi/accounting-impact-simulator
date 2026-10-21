"""Simplified financial statements for one scenario (assumptions F1–F9).

Every line has a stated source:
  revenue, other operating expenses, other income, finance costs,
  other assets, liabilities, opening equity    -> user inputs (same in both scenarios)
  depreciation                                 -> sum of the scenario's journal entries
  accumulated depreciation                     -> opening + journal credits
  carrying amount                              -> cost - accumulated depreciation
  operating profit  = revenue - other operating expenses - depreciation
  profit before tax = operating profit + other income - finance costs
  total assets      = other assets + carrying amount
  closing equity    = opening equity + profit before tax  (no tax, dividends or OCI)

The statements are built from the inputs as given. They are never forced to
balance: the accounting equation is CHECKED afterwards (V11), and a failure
withholds the statements instead of creating a balancing figure.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from simulator.journal.entries import JournalEntry, accumulated_depreciation_credits, expense_total
from simulator.models import EntityFinancials, PeriodDepreciation


@dataclass(frozen=True)
class FinancialStatements:
    scenario: str
    # income statement
    revenue: Decimal
    other_operating_expenses: Decimal
    depreciation: Decimal
    operating_profit: Decimal
    other_income: Decimal
    finance_costs: Decimal
    profit_before_tax: Decimal
    # statement of financial position (closing)
    ppe_cost: Decimal
    accumulated_depreciation: Decimal
    ppe_carrying_amount: Decimal
    other_assets: Decimal
    total_assets: Decimal
    total_liabilities: Decimal
    opening_equity: Decimal
    closing_equity: Decimal

    @property
    def retained_earnings_movement(self) -> Decimal:
        """Profit for the period added to retained earnings (no tax or dividends in the MVP)."""
        return self.profit_before_tax

    @property
    def equation_difference(self) -> Decimal:
        """Assets - (liabilities + equity). Must be exactly zero."""
        return self.total_assets - (self.total_liabilities + self.closing_equity)


def build_statements(pd: PeriodDepreciation, entries: tuple[JournalEntry, ...],
                     fin: EntityFinancials) -> FinancialStatements:
    depreciation = expense_total(entries)
    accumulated = pd.opening_accumulated_depreciation + accumulated_depreciation_credits(entries)
    carrying = pd.cost - accumulated
    operating_profit = fin.revenue - fin.other_operating_expenses - depreciation
    pbt = operating_profit + fin.other_income - fin.finance_costs
    return FinancialStatements(
        scenario=pd.scenario,
        revenue=fin.revenue, other_operating_expenses=fin.other_operating_expenses, depreciation=depreciation,
        operating_profit=operating_profit, other_income=fin.other_income, finance_costs=fin.finance_costs,
        profit_before_tax=pbt,
        ppe_cost=pd.cost, accumulated_depreciation=accumulated, ppe_carrying_amount=carrying,
        other_assets=fin.other_assets_closing, total_assets=fin.other_assets_closing + carrying,
        total_liabilities=fin.total_liabilities_closing, opening_equity=fin.opening_equity,
        closing_equity=fin.opening_equity + pbt,
    )
