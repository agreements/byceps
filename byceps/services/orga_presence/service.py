# -*- coding: utf-8 -*-

"""
byceps.services.orga_presence.service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Copyright: 2006-2016 Jochen Kupperschmidt
:License: Modified BSD, see LICENSE for details.
"""

from itertools import groupby

from arrow import Arrow

from ...database import db
from ...util.datetime.range import create_adjacent_ranges

from .models import Presence, Task


def get_presences(party_id):
    """Return all presences for that party."""
    return Presence.query \
        .for_party_id(party_id) \
        .options(db.joinedload('orga')) \
        .all()


def get_tasks(party_id):
    """Return all tasks for that party."""
    return Task.query \
        .for_party_id(party_id) \
        .all()


# -------------------------------------------------------------------- #


def get_hour_ranges(party, tasks):
    """Yield our ranges based on the party and tasks."""
    time_slot_ranges = list(_get_time_slot_ranges(party, tasks))
    hour_starts = _get_hour_starts(time_slot_ranges)
    return create_adjacent_ranges(hour_starts)


def _get_time_slot_ranges(party, tasks):
    time_slots = [party] + tasks
    for time_slot in time_slots:
        yield time_slot.range


def _get_hour_starts(dt_ranges):
    min_starts_at = _find_earliest_start(dt_ranges)
    max_ends_at = _find_latest_end(dt_ranges)

    hour_starts_arrow = Arrow.range('hour', min_starts_at, max_ends_at)

    return _to_datetimes_without_tzinfo(hour_starts_arrow)


def _find_earliest_start(dt_ranges):
    return min(dt_range.start for dt_range in dt_ranges)


def _find_latest_end(dt_ranges):
    return max(dt_range.end for dt_range in dt_ranges)


def _to_datetimes_without_tzinfo(arrow_datetimes):
    for arrow_datetime in arrow_datetimes:
        yield arrow_datetime.datetime.replace(tzinfo=None)


def get_days_and_hour_totals(hour_ranges):
    """Yield (day, relevant hours total) pairs."""
    def get_date(dt_range):
        return dt_range.start.date()

    for day, hour_ranges_for_day in groupby(hour_ranges, key=get_date):
        hour_total = len(list(hour_ranges_for_day))
        yield day, hour_total
