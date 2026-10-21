"""V22 change request: ordinary numeric inputs are accepted at the engine boundary and converted to Decimal;
no float ever reaches the calculation engine."""
import dataclasses
from datetime import date
from decimal import Decimal as D
from fractions import Fraction

from _builders import case_b, make_input
from simulator.ias16 import simulate
from simulator.validation.coerce import to_amount, to_date, to_months


def _no_floats(obj, path="result"):
    """Walk every value in a (nested) dataclass result; fail on any float."""
    if isinstance(obj, float):
        raise AssertionError(f"float found at {path}: {obj!r}")
    if dataclasses.is_dataclass(obj):
        for f in dataclasses.fields(obj):
            _no_floats(getattr(obj, f.name), f"{path}.{f.name}")
    elif isinstance(obj, (tuple, list)):
        for i, item in enumerate(obj):
            _no_floats(item, f"{path}[{i}]")
    else:
        assert obj is None or isinstance(obj, (D, Fraction, int, str, date)) or hasattr(obj, "value"), \
            f"unexpected type at {path}: {type(obj).__name__}"


def test_float_inputs_accepted_and_give_identical_results():
    from_floats = simulate(make_input(cost=100000.0, residual=10000.0, life=120.0, opening_ad=27000.0,
                                      change_date=date(2025, 7, 1), revised_life=96.0))
    from_decimals = simulate(case_b())
    assert from_floats.ok
    assert from_floats.scenario == from_decimals.scenario
    assert from_floats.baseline == from_decimals.baseline


def test_string_inputs_with_thousands_separators_accepted():
    r = simulate(make_input(cost="100,000", residual=" 10000.00 ", opening_ad="27,000",
                            change_date="2025-07-01", revised_life="96"))
    assert r.ok
    assert r.scenario.depreciation == D("11000.00")


def test_no_float_anywhere_in_engine_output():
    r = simulate(make_input(cost=100000.0, residual=10000.0, opening_ad=27000.0,
                            change_date=date(2025, 7, 1), revised_life=96))
    _no_floats(r)


def test_float_converted_by_shortest_repr_not_binary_expansion():
    assert to_amount(1234.56, "x") == (D("1234.56"), None)
    assert to_amount(0.1, "x") == (D("0.10"), None)


def test_v22_rejects_non_numbers():
    for bad in ("abc", float("nan"), float("inf"), True, [1]):
        value, issue = to_amount(bad, "cost")
        assert value is None and issue.code == "V22", bad
    r = simulate(make_input(cost="12a", revised_life=96))
    assert not r.ok and r.baseline is None and "V22" in r.codes()


def test_v23_rejects_more_than_two_decimals():
    value, issue = to_amount(D("100.005"), "cost")
    assert value is None and issue.code == "V23"
    assert to_amount(D("100.500"), "cost") == (D("100.50"), None)  # trailing zero is fine


def test_months_must_be_whole():
    assert to_months(96.0, "life") == (96, None)
    assert to_months("96", "life") == (96, None)
    value, issue = to_months(96.5, "life")
    assert value is None and issue.code == "V22"


def test_dates_accept_iso_text():
    assert to_date("2025-07-01", "d") == (date(2025, 7, 1), None)
    assert to_date("01/07/2025", "d")[1].code == "V22"


def test_blank_string_treated_as_missing():
    r = simulate(make_input(opening_ad="", revised_life=96))
    assert r.ok and r.opening_balance_source == "calculated"
