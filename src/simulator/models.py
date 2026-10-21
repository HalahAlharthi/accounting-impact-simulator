"""Input and output data structures.

All structures are frozen dataclasses: once created they cannot be changed, which
makes results reproducible and safe to compare (T17).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from fractions import Fraction

# --------------------------------------------------------------------------- #
# Validation messages
# --------------------------------------------------------------------------- #


class Severity(str, Enum):
    ERROR = "error"      # calculation stops; no numbers are released
    WARNING = "warning"  # calculation runs; the user must see the flag
    INFO = "info"        # explanatory note


@dataclass(frozen=True)
class ValidationIssue:
    code: str                 # e.g. "V04"
    severity: Severity
    message: str              # what is wrong, with the amounts involved
    field: str | None = None  # which input it concerns
    fix: str | None = None    # what the user can do about it


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class AssetInput:
    cost: Decimal | None
    residual_value: Decimal | None
    useful_life_months: int | None          # original TOTAL useful life
    available_for_use_date: date | None     # 1st of a month
    method: str = "straight_line"           # the only method supported in the MVP


@dataclass(frozen=True)
class ReportingPeriod:
    start_date: date | None  # 1st of a month
    end_date: date | None    # last day of a month


@dataclass(frozen=True)
class EstimateRevision:
    """A change in accounting estimate (IAS 8), applied prospectively from `effective_date`.

    `effective_date` is the date of the change in estimate — when the new
    information arose (approved decision 3). There is no default.
    A revised field left as None means "unchanged".
    """
    effective_date: date | None
    revised_useful_life_months: int | None = None   # revised TOTAL life (decision 1)
    revised_residual_value: Decimal | None = None


@dataclass(frozen=True)
class SimulationInput:
    asset: AssetInput
    period: ReportingPeriod
    revision: EstimateRevision | None
    # Accumulated depreciation at the start of the period, as recorded in the books.
    # If supplied it is ALWAYS used as entered (decision 4); if None, the engine
    # derives it from the original estimate and says so (info V20).
    opening_accumulated_depreciation: Decimal | None = None


@dataclass(frozen=True)
class EntityFinancials:
    """Rest-of-entity figures for the reporting period (fictional or anonymised).

    They are identical in the baseline and the scenario, so every difference
    between the two comes from depreciation alone (assumption F3).
    Closing equity is not entered: it is derived as opening equity + profit
    before tax (no tax, dividends or OCI in the MVP — assumption F4).
    """
    revenue: Decimal | None
    other_operating_expenses: Decimal | None      # excluding this asset's depreciation
    other_income: Decimal | None                  # signed: a net other expense is negative
    finance_costs: Decimal | None
    other_assets_closing: Decimal | None          # all assets except this asset
    total_liabilities_closing: Decimal | None
    opening_equity: Decimal | None                # may be negative


@dataclass(frozen=True)
class OpeningPosition:
    """Opening statement of financial position (start of the reporting period).

    Opening equity is not repeated here: it is EntityFinancials.opening_equity,
    entered once and used both for this check and for closing equity.
    Opening total assets INCLUDE this asset's opening carrying amount.
    """
    total_assets: Decimal | None
    total_liabilities: Decimal | None


# --------------------------------------------------------------------------- #
# Outputs
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class TraceStep:
    """One line of the visible calculation trail: label, formula, numbers, result."""
    label: str
    formula: str
    substitution: str
    result: str
    references: tuple[str, ...] = ()


@dataclass(frozen=True)
class Segment:
    """A run of months depreciated at one rate.

    A period has one segment, or two when the estimate changes partway through.
    """
    estimate_label: str               # "original estimate" or "revised estimate"
    start_date: date                  # first month of the segment
    end_date: date                    # last day of the segment's final month
    months: int
    carrying_amount_at_start: Decimal
    residual_value: Decimal
    remaining_life_months: int        # remaining life at the segment start
    remaining_depreciable_amount: Decimal  # max(0, carrying amount - residual)
    exact_depreciation: Fraction      # full precision, never rounded
    depreciation: Decimal             # posted amount: exact rounded half-up to cents

    @property
    def monthly_rate_exact(self) -> Fraction:
        if self.remaining_life_months <= 0:
            return Fraction(0)
        return Fraction(self.remaining_depreciable_amount) / self.remaining_life_months


@dataclass(frozen=True)
class PeriodDepreciation:
    """Depreciation for one reporting period under one scenario."""
    scenario: str                     # "baseline" or "revised"
    period_start: date
    period_end: date
    cost: Decimal
    opening_accumulated_depreciation: Decimal
    segments: tuple[Segment, ...]
    useful_life_months_after: int     # the estimate in force at period end
    residual_value_after: Decimal
    trace: tuple[TraceStep, ...] = field(default_factory=tuple)

    @property
    def depreciation(self) -> Decimal:
        return sum((s.depreciation for s in self.segments), Decimal("0.00"))

    @property
    def opening_carrying_amount(self) -> Decimal:
        return self.cost - self.opening_accumulated_depreciation

    @property
    def closing_accumulated_depreciation(self) -> Decimal:
        return self.opening_accumulated_depreciation + self.depreciation

    @property
    def closing_carrying_amount(self) -> Decimal:
        return self.cost - self.closing_accumulated_depreciation


@dataclass(frozen=True)
class SimulationResult:
    issues: tuple[ValidationIssue, ...]
    baseline: PeriodDepreciation | None = None
    scenario: PeriodDepreciation | None = None
    # What the original estimate implies for opening accumulated depreciation.
    # Shown next to the user's figure when the two differ (T19); never substituted.
    implied_opening_accumulated_depreciation: Decimal | None = None
    # "entered" = the user's ledger figure, used as entered;
    # "calculated" = derived from the original estimate, NOT verified against the ledger (V20).
    opening_balance_source: str | None = None

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity is Severity.ERROR)

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity is Severity.WARNING)

    @property
    def ok(self) -> bool:
        return not self.errors

    def codes(self) -> set[str]:
        return {i.code for i in self.issues}

    @property
    def change_in_depreciation(self) -> Decimal | None:
        if self.baseline is None or self.scenario is None:
            return None
        return self.scenario.depreciation - self.baseline.depreciation
