"""Input validation: runs BEFORE any calculation, on inputs already converted by coerce.py.

If any ERROR is found, the engine releases no numbers at all — a partial result
could be mistaken for a correct one.

Issue codes used in Phase 2 (full list in docs/test_cases.md):
V01 cost, V02 residual value, V03 useful life, V04 revised life already elapsed,
V05 change date outside period, V06 period/availability dates, V07 opening
accumulated depreciation out of range, V14 missing input, V15 date convention,
V16 unsupported method, V17 change dated before the asset was available,
V18 original life ended before the period, V19 accumulated depreciation supplied
for an asset not yet in use, V22 invalid value (defensive: coerce.py converts or
rejects values first, so a float can never reach the engine).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from simulator.models import Severity, SimulationInput, ValidationIssue
from simulator.periods import (
    is_end_of_month,
    is_first_of_month,
    months_between,
)

E = Severity.ERROR


def _issue(code, severity, message, field=None, fix=None) -> ValidationIssue:
    return ValidationIssue(code=code, severity=severity, message=message, field=field, fix=fix)


def _is_amount(value) -> bool:
    """A finite Decimal or int (bool excluded, float rejected on purpose)."""
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return isinstance(value, Decimal) and value.is_finite()


def _is_months(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_inputs(inp: SimulationInput) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    a, p, r = inp.asset, inp.period, inp.revision

    # ---- V14: missing required inputs (checked first; later checks need them) --
    required = {
        "cost": a.cost,
        "residual_value": a.residual_value,
        "useful_life_months": a.useful_life_months,
        "available_for_use_date": a.available_for_use_date,
        "period_start_date": p.start_date,
        "period_end_date": p.end_date,
        "revision": r,
        "revision_effective_date": r.effective_date if r is not None else "n/a",
    }
    for name, value in required.items():
        if value is None:
            issues.append(_issue("V14", E, f"Missing required input: {name}.", name,
                                 f"Enter a value for '{name}'."))
    if issues:
        return issues

    # ---- V22: wrong value types -------------------------------------------------
    amounts = {"cost": a.cost, "residual_value": a.residual_value}
    if r.revised_residual_value is not None:
        amounts["revised_residual_value"] = r.revised_residual_value
    if inp.opening_accumulated_depreciation is not None:
        amounts["opening_accumulated_depreciation"] = inp.opening_accumulated_depreciation
    for name, value in amounts.items():
        if not _is_amount(value):
            issues.append(_issue("V22", E, f"'{name}' must be a finite Decimal amount, got {value!r}.",
                                 name, "Enter amounts as Decimal (e.g. Decimal('100000')), not float."))
    lives = {"useful_life_months": a.useful_life_months}
    if r.revised_useful_life_months is not None:
        lives["revised_useful_life_months"] = r.revised_useful_life_months
    for name, value in lives.items():
        if not _is_months(value):
            issues.append(_issue("V22", E, f"'{name}' must be a whole number of months, got {value!r}.", name))
    dates = {
        "available_for_use_date": a.available_for_use_date,
        "period_start_date": p.start_date,
        "period_end_date": p.end_date,
        "revision_effective_date": r.effective_date,
    }
    for name, value in dates.items():
        if not isinstance(value, date):
            issues.append(_issue("V22", E, f"'{name}' must be a date, got {value!r}.", name))
    if issues:
        return issues

    # ---- V16: unsupported assumption ---------------------------------------------
    if a.method != "straight_line":
        issues.append(_issue("V16", E, f"Depreciation method '{a.method}' is not supported in the MVP.",
                             "method", "Use 'straight_line'. Other methods are a future enhancement."))

    # ---- V01 / V02 / V03: amounts and lives ------------------------------------
    cost = Decimal(a.cost)
    if cost <= 0:
        issues.append(_issue("V01", E, f"Cost must be greater than zero (entered {cost}).", "cost"))
    for name, rv in (("residual_value", a.residual_value), ("revised_residual_value", r.revised_residual_value)):
        if rv is None:
            continue
        if rv < 0 or rv > cost:
            issues.append(_issue("V02", E, f"{name} must be between 0 and cost {cost} (entered {rv}).", name,
                                 "A residual value above cost would mean negative depreciation."))
    for name, life in lives.items():
        if life <= 0:
            issues.append(_issue("V03", E, f"{name} must be greater than zero (entered {life}).", name))

    # ---- V15: date convention (monthly basis, decision 2) -----------------------
    for name in ("available_for_use_date", "period_start_date", "revision_effective_date"):
        if not is_first_of_month(dates[name]):
            issues.append(_issue("V15", E, f"{name} must be the 1st of a month (entered {dates[name]}).", name,
                                 "The MVP uses a monthly basis; daily pro-rata is a future enhancement."))
    if not is_end_of_month(p.end_date):
        issues.append(_issue("V15", E, f"period_end_date must be the last day of a month (entered {p.end_date}).",
                             "period_end_date"))

    # ---- V06: period and availability ------------------------------------------
    if p.end_date <= p.start_date:
        issues.append(_issue("V06", E, "The reporting period must end after it starts.", "period_end_date"))
    if a.available_for_use_date > p.end_date:
        issues.append(_issue("V06", E, "The asset is not available for use before the period ends, "
                                       "so there is nothing to depreciate.", "available_for_use_date"))

    # ---- V05 / V17: date of the change in estimate -----------------------------
    if not (p.start_date <= r.effective_date <= p.end_date):
        issues.append(_issue("V05", E, f"The change in estimate ({r.effective_date}) must fall within the "
                                       f"reporting period ({p.start_date} to {p.end_date}).",
                             "revision_effective_date"))
    if r.effective_date < a.available_for_use_date:
        issues.append(_issue("V17", E, "The change in estimate is dated before the asset was available for use.",
                             "revision_effective_date"))

    if any(i.severity is E for i in issues):
        return issues

    # ---- V07 / V19: opening accumulated depreciation ---------------------------
    depreciable = cost - a.residual_value
    oad = inp.opening_accumulated_depreciation
    if oad is not None:
        if oad < 0 or oad > depreciable:
            issues.append(_issue("V07", E, f"Opening accumulated depreciation ({oad}) must be between 0 and the "
                                           f"depreciable amount {depreciable} (cost - residual value).",
                                 "opening_accumulated_depreciation"))
        if a.available_for_use_date >= p.start_date and oad != 0:
            issues.append(_issue("V19", E, "Opening accumulated depreciation must be 0: the asset was not yet "
                                           "available for use at the start of the period.",
                                 "opening_accumulated_depreciation"))

    # ---- V18: original life already over (out of MVP scope) --------------------
    elapsed_open = max(0, months_between(a.available_for_use_date, p.start_date))
    if elapsed_open >= a.useful_life_months:
        issues.append(_issue("V18", E, f"The original useful life ({a.useful_life_months} months) had ended before "
                                       f"the period began ({elapsed_open} months elapsed).", "useful_life_months",
                             "Fully depreciated assets are outside the MVP scope."))

    # ---- V04: revised total life must exceed the life already elapsed ----------
    revised_life = r.revised_useful_life_months or a.useful_life_months
    elapsed_at_change = months_between(a.available_for_use_date, r.effective_date)
    if revised_life <= elapsed_at_change:
        issues.append(_issue("V04", E, f"Revised total life ({revised_life} months) is not more than the "
                                       f"{elapsed_at_change} months already elapsed at {r.effective_date}.",
                             "revised_useful_life_months",
                             "The revision implies the asset is already fully consumed; consider derecognition "
                             "or an impairment review (IAS 36 — outside the MVP) instead."))
    # V21 (revision with no effect on depreciation) is raised after calculation, in the engine.
    return issues
