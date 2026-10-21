"""Month arithmetic (approved decision 2: monthly time basis).

Convention: the asset's available-for-use date, the reporting-period start and the
date of a change in estimate are all the 1st of a month; a period ends on the last
day of a month. Validation enforces this before any calculation runs.
"""
from __future__ import annotations

import calendar
from datetime import date


def month_index(d: date) -> int:
    """A running month number, so month differences are simple subtraction."""
    return d.year * 12 + (d.month - 1)


def months_between(start: date, end: date) -> int:
    """Whole months from `start` up to (not including) `end`.

    months_between(1 Jan 2022, 1 Jan 2025) == 36.
    """
    return month_index(end) - month_index(start)


def months_in_range(first_month: date, last_day: date) -> int:
    """Months from a 1st-of-month date through the month containing `last_day`, inclusive."""
    return month_index(last_day) - month_index(first_month) + 1


def add_months(d: date, n: int) -> date:
    """1st of the month that is `n` months after the month of `d`."""
    idx = month_index(d) + n
    return date(idx // 12, idx % 12 + 1, 1)


def end_of_month(d: date) -> date:
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def is_first_of_month(d: date) -> bool:
    return d.day == 1


def is_end_of_month(d: date) -> bool:
    return d == end_of_month(d)
