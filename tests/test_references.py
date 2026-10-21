"""Locks in reference verification labels so nothing is upgraded to 'confirmed' by accident."""
from simulator.references import REFERENCES, Status

MUST_STAY_PENDING = ["IAS 8.32(d)", "IAS 8.39-40", "IAS 8.41-49"]


def test_unverified_references_are_pending():
    for code in MUST_STAY_PENDING:
        assert REFERENCES[code].status is Status.PENDING, code


def test_aasb_corroborated_references_are_not_labelled_confirmed():
    for code in ["IAS 8.36", "IAS 8.37", "IAS 8.38"]:
        assert REFERENCES[code].status is Status.CORROBORATED_AASB, code


def test_only_ifrs_org_items_are_confirmed():
    confirmed = {c for c, r in REFERENCES.items() if r.status is Status.CONFIRMED_IFRS_ORG}
    assert confirmed == {
        "IAS 16.6", "IAS 16.48", "IAS 16.50", "IAS 16.51", "IAS 16.53", "IAS 16.54", "IAS 16.55",
        "IFRS 18 effective date", "IAS 8 title (2027)",
    }


def test_ias_16_paragraph_summaries_preserve_exceptions_and_conditions():
    assert "unless included in another asset's carrying amount" in REFERENCES["IAS 16.48"].supports
    assert "at least each year-end" in REFERENCES["IAS 16.51"].supports
    assert "falls below carrying amount" in REFERENCES["IAS 16.54"].supports
