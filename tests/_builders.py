"""Shared test inputs (fictional data only).

Base asset from the approved worked example: cost 100,000; residual 10,000;
120-month life; available 1 Jan 2022; FY2025; opening accumulated depreciation 27,000.

Only INPUTS live here. Every EXPECTED figure is written by hand in the test that
uses it, from the Phase 1 hand calculations — never produced by the code under test.
"""
from datetime import date
from decimal import Decimal

from simulator.models import AssetInput, EstimateRevision, ReportingPeriod, SimulationInput

__all__ = ["make_input", "case_a", "case_b", "make_financials", "make_opening", "analyse", "FY2025", "ReportingPeriod"]

D = Decimal
FY2025 = ReportingPeriod(date(2025, 1, 1), date(2025, 12, 31))
_MISSING = object()


def make_input(*, cost=D("100000"), residual=D("10000"), life=120, available=date(2022, 1, 1),
               period=FY2025, opening_ad=_MISSING, change_date=date(2025, 1, 1),
               revised_life=None, revised_residual=None, method="straight_line", revision=_MISSING):
    if opening_ad is _MISSING:
        opening_ad = D("27000")
    if revision is _MISSING:
        revision = EstimateRevision(change_date, revised_life, revised_residual)
    return SimulationInput(
        asset=AssetInput(cost, residual, life, available, method),
        period=period,
        revision=revision,
        opening_accumulated_depreciation=opening_ad,
    )


def make_financials(*, revenue=D("500000"), other_opex=D("400000"), other_income=D("0"), finance_costs=D("0"),
                    other_assets=D("436000"), liabilities=D("200000"), opening_equity=D("209000")):
    """Rest-of-entity figures from the approved worked example."""
    from simulator.models import EntityFinancials
    return EntityFinancials(revenue, other_opex, other_income, finance_costs, other_assets, liabilities,
                            opening_equity)


def make_opening(*, total_assets=D("409000"), total_liabilities=D("200000")):
    """Opening position consistent with the worked example:
    409,000 = 200,000 liabilities + 209,000 equity; includes this asset at 73,000 (other assets 336,000)."""
    from simulator.models import OpeningPosition
    return OpeningPosition(total_assets, total_liabilities)


def analyse(inp, fin=None, opening=None):
    """run_impact_analysis with the worked-example financials/opening position unless given."""
    from simulator.impact import run_impact_analysis
    return run_impact_analysis(inp, fin if fin is not None else make_financials(),
                               opening if opening is not None else make_opening())


def case_a():
    """Revised total life 96 months, change dated 1 Jan 2025."""
    return make_input(revised_life=96, change_date=date(2025, 1, 1))


def case_b():
    """Revised total life 96 months, change dated 1 Jul 2025."""
    return make_input(revised_life=96, change_date=date(2025, 7, 1))
