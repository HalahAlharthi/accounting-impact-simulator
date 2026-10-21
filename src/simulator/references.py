"""Standard references used by the engine, each with an explicit verification status.

Rule (approved): a reference is only labelled CONFIRMED when it was checked
against IFRS Foundation material. AASB text (which keeps IFRS paragraph
numbering) is labelled CORROBORATED, and anything supported only by secondary
sources stays PENDING. tests/test_references.py locks these labels in, so a
status cannot be upgraded by accident.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Status(str, Enum):
    CONFIRMED_IFRS_ORG = "confirmed on ifrs.org"
    CORROBORATED_AASB = "corroborated via AASB equivalent text; IFRS primary text pending"
    PENDING = "pending verification against IFRS primary text"


@dataclass(frozen=True)
class Reference:
    code: str
    supports: str  # our own summary — not quoted standard text
    status: Status


_REFS = [
    Reference("IAS 16.6", "Defines carrying amount (after accumulated depreciation and impairment losses) and "
                           "depreciable amount (cost less residual value), among other terms",
              Status.CONFIRMED_IFRS_ORG),
    Reference("IAS 16.48", "Depreciation charge recognised in profit or loss unless included in another asset's "+
                           "carrying amount", Status.CONFIRMED_IFRS_ORG),
    Reference("IAS 16.50", "Depreciable amount allocated systematically over useful life",
              Status.CONFIRMED_IFRS_ORG),
    Reference("IAS 16.51", "Residual value and useful life reviewed at least each year-end; "
                           "changes treated as changes in estimate", Status.CONFIRMED_IFRS_ORG),
    Reference("IAS 16.53", "Depreciable amount is determined after deducting residual value",
              Status.CONFIRMED_IFRS_ORG),
    Reference("IAS 16.54", "No depreciation while residual value equals or exceeds carrying amount; it resumes "
                           "when residual value falls below carrying amount", Status.CONFIRMED_IFRS_ORG),
    Reference("IAS 16.55", "Depreciation begins when the asset is available for use",
              Status.CONFIRMED_IFRS_ORG),
    Reference("IAS 8.32(d)", "Useful life is an example of an accounting estimate", Status.PENDING),
    Reference("IAS 8.36", "Effect of a change in estimate recognised prospectively in profit or loss",
              Status.CORROBORATED_AASB),
    Reference("IAS 8.37", "Related asset's carrying amount adjusted in the period of change",
              Status.CORROBORATED_AASB),
    Reference("IAS 8.38", "Prospective = from the date of the change; useful-life changes affect current "
                          "and future periods", Status.CORROBORATED_AASB),
    Reference("IAS 8.39-40", "Disclosure of nature and amount of a change in estimate", Status.PENDING),
    Reference("IAS 8.41-49", "Prior-period error identification, retrospective correction and related disclosure",
              Status.PENDING),
    Reference("IFRS 18 effective date", "IFRS 18 effective for annual periods beginning on or after 1 Jan 2027",
              Status.CONFIRMED_IFRS_ORG),
    Reference("IAS 8 title (2027)", "IAS 8 retitled Basis of Preparation of Financial Statements",
              Status.CONFIRMED_IFRS_ORG),
]

REFERENCES: dict[str, Reference] = {r.code: r for r in _REFS}


def label(code: str) -> str:
    """Return a reference label with its explicit verification status."""
    ref = REFERENCES[code]
    return f"{ref.code} ({ref.status.value})"
