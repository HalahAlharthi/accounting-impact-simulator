"""Opening statement of financial position check (Phase 3 decision 2).

Kept separate from the depreciation engine: it only reads the asset's opening
carrying amount, which is identical in both scenarios (prospective treatment).

Inputs
  opening total assets       (OpeningPosition, includes this asset)
  opening total liabilities  (OpeningPosition)
  opening equity             (EntityFinancials.opening_equity — entered once)

Checks (they report; they never adjust)
  V14  missing opening total assets / liabilities
  V24  opening total assets or liabilities negative
  V26  opening assets = opening liabilities + opening equity, exactly
  V27  opening total assets must be at least this asset's opening carrying
       amount (the asset is part of them), so implied other assets >= 0.
       Not applied (info V28) when the asset was not yet in use at the period start.

Worked example: opening equity 209,000; opening liabilities 200,000; opening
total assets 409,000, of which this asset 73,000 and other assets 336,000.
(Other assets then rise to 436,000 at year-end: +100,000 = revenue 500,000
- other operating expenses 400,000, assuming those were settled in cash.
This roll-forward is illustrative only; it is not checked, because other
balance-sheet movements are not collected.)
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from simulator.models import OpeningPosition, Severity, ValidationIssue
from simulator.money import fmt


@dataclass(frozen=True)
class OpeningStatement:
    total_assets: Decimal
    asset_carrying_amount: Decimal | None  # this asset; None if it was not yet in use at the period start
    other_assets: Decimal | None           # derived: total assets - this asset
    total_liabilities: Decimal
    equity: Decimal

    @property
    def equation_difference(self) -> Decimal:
        return self.total_assets - (self.total_liabilities + self.equity)


def _err(code, message, field=None, fix=None):
    return ValidationIssue(code=code, severity=Severity.ERROR, message=message, field=field, fix=fix)


def validate_opening_inputs(opening: OpeningPosition) -> list[ValidationIssue]:
    labels = {"total_assets": "opening_total_assets", "total_liabilities": "opening_total_liabilities"}
    issues = [_err("V14", f"Missing required input: {label}.", label, f"Enter '{label}' from the opening trial balance.")
              for attr, label in labels.items() if getattr(opening, attr) is None]
    if issues:
        return issues
    return [_err("V24", f"'{label}' must not be negative (entered {getattr(opening, attr)}).", label)
            for attr, label in labels.items() if getattr(opening, attr) < 0]


def check_opening_position(opening: OpeningPosition, opening_equity: Decimal,
                           asset_opening_carrying_amount: Decimal | None
                           ) -> tuple[OpeningStatement, list[ValidationIssue]]:
    """`asset_opening_carrying_amount=None` means the asset was not yet available for use at the
    period start: whether its cost was already in opening assets (e.g. awaiting installation) or it
    was acquired during the period is not collected, so V27 is not applied and info V28 says so."""
    in_position = asset_opening_carrying_amount is not None
    stmt = OpeningStatement(
        total_assets=opening.total_assets, asset_carrying_amount=asset_opening_carrying_amount,
        other_assets=opening.total_assets - asset_opening_carrying_amount if in_position else None,
        total_liabilities=opening.total_liabilities, equity=opening_equity,
    )
    issues = []
    if not in_position:
        issues.append(ValidationIssue(
            "V28", Severity.INFO,
            "The asset was not yet available for use at the start of the period. Whether its cost was already "
            "included in opening total assets is not collected, so the V27 check is not applied.",
            "opening_total_assets"))
    if stmt.equation_difference != 0:
        issues.append(_err(
            "V26", f"Opening position does not balance: total assets {fmt(stmt.total_assets)} vs liabilities "
                   f"{fmt(stmt.total_liabilities)} + equity {fmt(stmt.equity)} = "
                   f"{fmt(stmt.total_liabilities + stmt.equity)}; difference (assets − liabilities − equity) "
                   f"{fmt(stmt.equation_difference)}. No balancing figure has been posted.",
            "opening_position", "Take opening assets, liabilities and equity from the same opening trial balance."))
    if in_position and stmt.other_assets < 0:
        issues.append(_err(
            "V27", f"Opening total assets ({fmt(stmt.total_assets)}) are less than this asset's opening carrying "
                   f"amount ({fmt(asset_opening_carrying_amount)}), which they must include; shortfall "
                   f"{fmt(-stmt.other_assets)}.",
            "opening_total_assets", "Opening total assets must include this asset at its opening carrying amount."))
    return stmt, issues
