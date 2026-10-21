"""Engine boundary: convert user-entered values to exact types (approved change to V22).

A user interface often hands numbers over as floats (e.g. 100000.0) or strings
("100,000"). Those are ordinary inputs and are ACCEPTED here, then converted
once to Decimal. After this point the engine never sees a float.

How a float is converted: Decimal(repr(x)). repr gives the shortest text that
round-trips, so 1234.56 becomes Decimal("1234.56"), not the binary
approximation 1234.55999999999994543031789362430572509765625.

Rejected (with a clear message, nothing is guessed):
- V22: not a number (text that does not parse, NaN, infinity, True/False);
       months that are not whole (96.5).
- V23: an amount with more than 2 decimal places (e.g. 100.005). Amounts must be
       in cents so that posted balances can reconcile exactly (rounding policy).
"""
from __future__ import annotations

import dataclasses
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from simulator.models import EntityFinancials, OpeningPosition, Severity, SimulationInput, ValidationIssue

CENTS = Decimal("0.01")


def _bad(code: str, field: str, message: str, fix: str) -> ValidationIssue:
    return ValidationIssue(code=code, severity=Severity.ERROR, message=message, field=field, fix=fix)


def _parse_number(value, field: str) -> tuple[Decimal | None, ValidationIssue | None]:
    if value is None:
        return None, None
    if isinstance(value, bool):
        return None, _bad("V22", field, f"'{field}' must be a number, got {value!r}.", "Enter a numeric value.")
    if isinstance(value, Decimal):
        d = value
    elif isinstance(value, int):
        d = Decimal(value)
    elif isinstance(value, float):
        d = Decimal(repr(value))  # shortest round-trip text, never the binary expansion
    elif isinstance(value, str):
        text = value.strip().replace(",", "")
        if text == "":
            return None, None  # blank behaves like missing (V14 or a documented default)
        try:
            d = Decimal(text)
        except InvalidOperation:
            return None, _bad("V22", field, f"'{field}' is not a number: {value!r}.", "Enter digits only, e.g. 100000.")
    else:
        return None, _bad("V22", field, f"'{field}' must be a number, got {type(value).__name__}.",
                          "Enter a numeric value.")
    if not d.is_finite():
        return None, _bad("V22", field, f"'{field}' must be a finite number, got {value!r}.", "Enter a real amount.")
    return d, None


def to_amount(value, field: str) -> tuple[Decimal | None, ValidationIssue | None]:
    d, issue = _parse_number(value, field)
    if d is None:
        return None, issue
    if d != d.quantize(CENTS):
        return None, _bad("V23", field, f"'{field}' has more than 2 decimal places ({d}).",
                          "Enter amounts in cents (2 decimal places at most).")
    return d.quantize(CENTS), None


def to_months(value, field: str) -> tuple[int | None, ValidationIssue | None]:
    d, issue = _parse_number(value, field)
    if d is None:
        return None, issue
    if d != d.to_integral_value():
        return None, _bad("V22", field, f"'{field}' must be a whole number of months, got {value!r}.",
                          "Enter whole months, e.g. 96.")
    return int(d), None


def to_date(value, field: str) -> tuple[date | None, ValidationIssue | None]:
    if value is None:
        return None, None
    if isinstance(value, datetime):
        return value.date(), None
    if isinstance(value, date):
        return value, None
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip()), None
        except ValueError:
            pass
    return None, _bad("V22", field, f"'{field}' must be a date (YYYY-MM-DD), got {value!r}.", "Enter a date.")


def normalize_simulation_input(inp: SimulationInput) -> tuple[SimulationInput, list[ValidationIssue]]:
    issues: list[ValidationIssue] = []

    def take(converter, value, field):
        converted, issue = converter(value, field)
        if issue:
            issues.append(issue)
        return converted

    a = inp.asset
    asset = dataclasses.replace(
        a,
        cost=take(to_amount, a.cost, "cost"),
        residual_value=take(to_amount, a.residual_value, "residual_value"),
        useful_life_months=take(to_months, a.useful_life_months, "useful_life_months"),
        available_for_use_date=take(to_date, a.available_for_use_date, "available_for_use_date"),
    )
    period = dataclasses.replace(
        inp.period,
        start_date=take(to_date, inp.period.start_date, "period_start_date"),
        end_date=take(to_date, inp.period.end_date, "period_end_date"),
    )
    revision = inp.revision
    if revision is not None:
        revision = dataclasses.replace(
            revision,
            effective_date=take(to_date, revision.effective_date, "revision_effective_date"),
            revised_useful_life_months=take(to_months, revision.revised_useful_life_months,
                                            "revised_useful_life_months"),
            revised_residual_value=take(to_amount, revision.revised_residual_value, "revised_residual_value"),
        )
    opening = take(to_amount, inp.opening_accumulated_depreciation, "opening_accumulated_depreciation")
    normalized = SimulationInput(asset=asset, period=period, revision=revision,
                                 opening_accumulated_depreciation=opening)
    return normalized, issues


FINANCIAL_FIELDS = ("revenue", "other_operating_expenses", "other_income", "finance_costs",
                    "other_assets_closing", "total_liabilities_closing", "opening_equity")


def normalize_financials(fin: EntityFinancials) -> tuple[EntityFinancials, list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    values = {}
    for name in FINANCIAL_FIELDS:
        converted, issue = to_amount(getattr(fin, name), name)
        if issue:
            issues.append(issue)
        values[name] = converted
    return EntityFinancials(**values), issues


OPENING_FIELDS = {"total_assets": "opening_total_assets", "total_liabilities": "opening_total_liabilities"}


def normalize_opening(opening: OpeningPosition) -> tuple[OpeningPosition, list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    values = {}
    for attr, label in OPENING_FIELDS.items():
        converted, issue = to_amount(getattr(opening, attr), label)
        if issue:
            issues.append(issue)
        values[attr] = converted
    return OpeningPosition(**values), issues
