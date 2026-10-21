"""Invalid and missing inputs: the engine must stop with a specific, actionable error and release no numbers."""
from datetime import date
from decimal import Decimal as D

from _builders import make_input
from simulator.ias16 import simulate
from simulator.models import ReportingPeriod


def _assert_blocked(result, code, field=None):
    assert not result.ok
    assert result.baseline is None and result.scenario is None  # no partial numbers
    matching = [i for i in result.errors if i.code == code]
    assert matching, f"expected {code}, got {[i.code for i in result.issues]}"
    if field:
        assert any(i.field == field for i in matching)
    return matching[0]


# T03 — useful life = 0
def test_t03_zero_useful_life():
    _assert_blocked(simulate(make_input(life=0, revised_life=96)), "V03", "useful_life_months")


def test_t03b_zero_revised_useful_life():
    _assert_blocked(simulate(make_input(revised_life=0)), "V03", "revised_useful_life_months")


# T04 — residual value greater than cost
def test_t04_residual_above_cost():
    _assert_blocked(simulate(make_input(residual=D("120000"), revised_life=96)), "V02", "residual_value")


def test_t04b_revised_residual_above_cost():
    _assert_blocked(simulate(make_input(revised_residual=D("100000.01"))), "V02", "revised_residual_value")


# T09 — revised total life 36 months when 36 have elapsed: 36 - 36 = 0 remaining
def test_t09_revised_life_already_elapsed():
    issue = _assert_blocked(simulate(make_input(revised_life=36)), "V04", "revised_useful_life_months")
    assert "36 months already elapsed" in issue.message
    assert "IAS 36" in issue.fix


# T18 — cost missing
def test_t18_missing_cost():
    issue = _assert_blocked(simulate(make_input(cost=None, revised_life=96)), "V14", "cost")
    assert "cost" in issue.message


def test_missing_revision_and_dates():
    _assert_blocked(simulate(make_input(revision=None)), "V14", "revision")
    _assert_blocked(simulate(make_input(available=None, revised_life=96)), "V14", "available_for_use_date")


def test_v01_cost_not_positive():
    _assert_blocked(simulate(make_input(cost=D("0"), residual=D("0"), opening_ad=None, revised_life=96)), "V01")


def test_v05_change_date_outside_period():
    _assert_blocked(simulate(make_input(change_date=date(2026, 1, 1), revised_life=96)), "V05")


def test_v06_period_ends_before_start():
    bad = ReportingPeriod(date(2025, 12, 1), date(2025, 1, 31))
    _assert_blocked(simulate(make_input(period=bad, revised_life=96)), "V06")


def test_v06_asset_not_available_during_period():
    _assert_blocked(simulate(make_input(available=date(2026, 3, 1), opening_ad=D("0"),
                                        change_date=date(2025, 1, 1), revised_life=96)), "V06")


def test_v07_opening_accumulated_depreciation_above_depreciable_amount():
    _assert_blocked(simulate(make_input(opening_ad=D("90000.01"), revised_life=96)), "V07")


def test_v07_negative_opening_accumulated_depreciation():
    _assert_blocked(simulate(make_input(opening_ad=D("-1"), revised_life=96)), "V07")


def test_v15_dates_must_follow_monthly_convention():
    _assert_blocked(simulate(make_input(change_date=date(2025, 7, 15), revised_life=96)), "V15")
    bad_end = ReportingPeriod(date(2025, 1, 1), date(2025, 12, 30))
    _assert_blocked(simulate(make_input(period=bad_end, revised_life=96)), "V15", "period_end_date")


def test_v16_unsupported_method():
    _assert_blocked(simulate(make_input(method="reducing_balance", revised_life=96)), "V16")


def test_v17_change_dated_before_available():
    _assert_blocked(simulate(make_input(available=date(2025, 4, 1), opening_ad=D("0"),
                                        change_date=date(2025, 2, 1), revised_life=60)), "V17")


def test_v18_original_life_ended_before_period():
    _assert_blocked(simulate(make_input(life=36, opening_ad=D("90000"), revised_life=60)), "V18")


def test_v19_accumulated_depreciation_for_asset_not_yet_in_use():
    _assert_blocked(simulate(make_input(available=date(2025, 4, 1), opening_ad=D("500"),
                                        change_date=date(2025, 10, 1), revised_life=60)), "V19")


def test_v20_opening_balance_derived_when_blank_and_labelled_calculated():
    r = simulate(make_input(opening_ad=None, revised_life=96))
    assert r.ok and "V20" in r.codes()
    assert r.opening_balance_source == "calculated"
    assert r.baseline.opening_accumulated_depreciation == D("27000.00")
    v20 = next(i for i in r.issues if i.code == "V20")
    assert "CALCULATED" in v20.message and "not been verified against the ledger" in v20.message


def test_entered_opening_balance_is_labelled_entered():
    r = simulate(make_input(revised_life=96))
    assert r.opening_balance_source == "entered"
    assert "V20" not in r.codes()


def test_v18_message_says_out_of_scope():
    r = simulate(make_input(life=36, opening_ad=D("90000"), revised_life=60))
    issue = next(i for i in r.errors if i.code == "V18")
    assert "outside the MVP scope" in issue.fix
