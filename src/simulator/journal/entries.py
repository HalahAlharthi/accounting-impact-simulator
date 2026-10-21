"""Journal entries for depreciation (assumptions J1–J5).

J1  The only entry is Dr Depreciation expense / Cr Accumulated depreciation.
J2  One summarised entry per rate segment, dated the segment's last day
    (a mid-period change gives two entries: 30 Jun and 31 Dec).
J3  No entry for the revision itself and none against opening retained earnings:
    a change in estimate is prospective (IAS 8.36–38, corroborated via AASB 108;
    IFRS primary text pending).
J4  No tax or deferred tax entries (pre-tax MVP).
J5  Every entry must balance; check_journal_entries() reports V10 otherwise and
    nothing is adjusted.
A segment with zero depreciation (e.g. residual value >= carrying amount) gets no entry.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from simulator.models import PeriodDepreciation, Severity, ValidationIssue

DEPRECIATION_EXPENSE = "Depreciation expense — PPE"
ACCUMULATED_DEPRECIATION = "Accumulated depreciation — PPE"


@dataclass(frozen=True)
class JournalLine:
    account: str
    debit: Decimal
    credit: Decimal


@dataclass(frozen=True)
class JournalEntry:
    scenario: str
    entry_date: date
    description: str
    lines: tuple[JournalLine, ...]

    @property
    def total_debits(self) -> Decimal:
        return sum((ln.debit for ln in self.lines), Decimal("0.00"))

    @property
    def total_credits(self) -> Decimal:
        return sum((ln.credit for ln in self.lines), Decimal("0.00"))

    @property
    def is_balanced(self) -> bool:
        return self.total_debits == self.total_credits


def build_journal_entries(pd: PeriodDepreciation) -> tuple[JournalEntry, ...]:
    entries = []
    for seg in pd.segments:
        if seg.depreciation == 0:
            continue
        description = (f"Depreciation {seg.start_date:%d %b %Y}–{seg.end_date:%d %b %Y} "
                       f"({seg.months} months, {seg.estimate_label})")
        entries.append(JournalEntry(
            scenario=pd.scenario, entry_date=seg.end_date, description=description,
            lines=(JournalLine(DEPRECIATION_EXPENSE, seg.depreciation, Decimal("0.00")),
                   JournalLine(ACCUMULATED_DEPRECIATION, Decimal("0.00"), seg.depreciation)),
        ))
    return tuple(entries)


def check_journal_entries(entries: tuple[JournalEntry, ...]) -> list[ValidationIssue]:
    """V10: every entry must have debits equal to credits, and no negative amounts."""
    issues = []
    for e in entries:
        if not e.is_balanced:
            issues.append(ValidationIssue(
                "V10", Severity.ERROR,
                f"[{e.scenario}] Entry dated {e.entry_date} does not balance: debits {e.total_debits}, credits "
                f"{e.total_credits}, difference {e.total_debits - e.total_credits}.",
                fix="Nothing has been adjusted; the entry must be corrected at source."))
        if any(ln.debit < 0 or ln.credit < 0 for ln in e.lines):
            issues.append(ValidationIssue("V10", Severity.ERROR,
                                          f"[{e.scenario}] Entry dated {e.entry_date} has a negative amount."))
    return issues


def expense_total(entries: tuple[JournalEntry, ...]) -> Decimal:
    return sum((ln.debit for e in entries for ln in e.lines if ln.account == DEPRECIATION_EXPENSE), Decimal("0.00"))


def accumulated_depreciation_credits(entries: tuple[JournalEntry, ...]) -> Decimal:
    return sum((ln.credit for e in entries for ln in e.lines if ln.account == ACCUMULATED_DEPRECIATION),
               Decimal("0.00"))
