"""Ratio analysis (approved decision 6). All ratios are INDIRECT effects of the depreciation change.

Definitions (labelled "simplified" where they depart from common practice):
  Operating profit margin     = operating profit ÷ revenue
  Return on assets (simpl.)   = profit before tax ÷ closing total assets
  Asset turnover (simpl.)     = revenue ÷ closing total assets
  Liabilities-to-equity (simplified D/E) = total liabilities ÷ closing equity

A ratio is "not meaningful" (value None, with a reason) when its denominator is
zero or negative. A zero numerator is still meaningful (e.g. 0.000x turnover).
Values are exact fractions; display rounding is half-up: percentages to 2 dp,
multiples to 3 dp.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

from simulator.money import fmt, round_half_up
from simulator.statements.builder import FinancialStatements

PERCENT, TIMES = "percent", "times"


@dataclass(frozen=True)
class RatioResult:
    key: str
    name: str
    formula: str
    unit: str
    baseline: Fraction | None
    scenario: Fraction | None
    baseline_reason: str | None   # why the baseline is not meaningful, if it isn't
    scenario_reason: str | None
    explanation: str
    effect: str = "indirect"

    @property
    def change(self) -> Fraction | None:
        if self.baseline is None or self.scenario is None:
            return None
        return self.scenario - self.baseline

    def _display(self, value: Fraction | None) -> Decimal | None:
        if value is None:
            return None
        return round_half_up(value * 100, 2) if self.unit == PERCENT else round_half_up(value, 3)

    @property
    def display_baseline(self) -> Decimal | None:
        return self._display(self.baseline)

    @property
    def display_scenario(self) -> Decimal | None:
        return self._display(self.scenario)

    @property
    def display_change(self) -> Decimal | None:
        """Percentage points for percentages; plain difference for multiples."""
        return self._display(self.change)


def _ratio(numerator: Decimal, denominator: Decimal, what: str) -> tuple[Fraction | None, str | None]:
    if denominator == 0:
        return None, f"{what} is zero: the ratio cannot be calculated."
    if denominator < 0:
        return None, f"{what} is negative: the ratio is not meaningful."
    return Fraction(numerator) / Fraction(denominator), None


def _direction(delta: Decimal, up: str, down: str, same: str) -> str:
    return up if delta > 0 else down if delta < 0 else same


def calculate_ratios(base: FinancialStatements, scen: FinancialStatements) -> tuple[RatioResult, ...]:
    d_dep = scen.depreciation - base.depreciation
    d_op = scen.operating_profit - base.operating_profit
    d_pbt = scen.profit_before_tax - base.profit_before_tax
    d_ta = scen.total_assets - base.total_assets
    d_eq = scen.closing_equity - base.closing_equity
    results = []

    b, br = _ratio(base.operating_profit, base.revenue, "Revenue")
    s, sr = _ratio(scen.operating_profit, scen.revenue, "Revenue")
    results.append(RatioResult(
        "operating_margin", "Operating profit margin", "operating profit ÷ revenue", PERCENT, b, s, br, sr,
        f"Revenue is unchanged; depreciation {_direction(d_dep, 'rises', 'falls', 'is unchanged')} by "
        f"{fmt(abs(d_dep))}, so operating profit changes by {fmt(d_op)}."))

    b, br = _ratio(base.profit_before_tax, base.total_assets, "Total assets")
    s, sr = _ratio(scen.profit_before_tax, scen.total_assets, "Total assets")
    results.append(RatioResult(
        "return_on_assets", "Return on assets (simplified: PBT ÷ closing total assets)",
        "profit before tax ÷ closing total assets", PERCENT, b, s, br, sr,
        f"Profit before tax changes by {fmt(d_pbt)} and closing total assets by {fmt(d_ta)}; both changes come "
        f"from depreciation alone."))

    b, br = _ratio(base.revenue, base.total_assets, "Total assets")
    s, sr = _ratio(scen.revenue, scen.total_assets, "Total assets")
    results.append(RatioResult(
        "asset_turnover", "Asset turnover (simplified: closing total assets)", "revenue ÷ closing total assets",
        TIMES, b, s, br, sr,
        f"Revenue is unchanged; total assets change by {fmt(d_ta)}. "
        + _direction(-d_ta, "Turnover rises mechanically because the asset base is smaller — an accounting "
                            "effect, not an efficiency gain.",
                     "Turnover falls mechanically because the asset base is larger.",
                     "Turnover is unchanged.")))

    b, br = _ratio(base.total_liabilities, base.closing_equity, "Equity")
    s, sr = _ratio(scen.total_liabilities, scen.closing_equity, "Equity")
    results.append(RatioResult(
        "liabilities_to_equity", "Liabilities-to-equity (simplified D/E: total liabilities ÷ closing equity)",
        "total liabilities ÷ closing equity", TIMES, b, s, br, sr,
        f"Liabilities are unchanged; equity changes by {fmt(d_eq)} through profit."))
    return tuple(results)
