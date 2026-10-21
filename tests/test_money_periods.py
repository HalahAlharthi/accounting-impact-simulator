from datetime import date
from decimal import Decimal as D
from fractions import Fraction

from simulator.money import round_money
from simulator.periods import add_months, end_of_month, months_between, months_in_range


def test_round_half_up_to_cents():
    assert round_money(Fraction(757142857, 100000)) == D("7571.43")  # 7,571.42857
    assert round_money(Fraction(7571425, 1000)) == D("7571.43")      # exactly .425 rounds up
    assert round_money(Fraction(7571424, 1000)) == D("7571.42")
    assert round_money(Fraction(-1, 200)) == D("-0.01")              # symmetric for negatives
    assert round_money(0) == D("0.00")


def test_exact_fraction_division():
    assert Fraction(58500) / 54 * 6 == 6500  # no float drift


def test_month_arithmetic():
    assert months_between(date(2022, 1, 1), date(2025, 1, 1)) == 36
    assert months_between(date(2022, 1, 1), date(2025, 7, 1)) == 42
    assert months_in_range(date(2025, 1, 1), date(2025, 12, 31)) == 12
    assert add_months(date(2025, 11, 1), 3) == date(2026, 2, 1)
    assert end_of_month(date(2024, 2, 1)) == date(2024, 2, 29)
