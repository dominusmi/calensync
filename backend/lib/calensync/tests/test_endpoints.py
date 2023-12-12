from unittest.mock import patch

import pytest

from calensync.api.common import ApiError
from calensync.api.endpoints import get_calendar
from calensync.api.service import deactivate_calendar
from calensync.database.model import Event
from calensync.tests.fixtures import *


def test_get_calendar_valid(db, user, calendar1):
    c = get_calendar(user, str(calendar1.uuid), db)
    assert c == calendar1


def test_get_calendar_invalid_user(db, calendar1):
    user = User(email="test2@test.com").save_new()
    with pytest.raises(ApiError):
        get_calendar(user, str(calendar1.uuid), db)


def test_deactivate_calendars(db, calendar1, calendar2):
    with (
        patch("calensync.gwrapper.delete_event") as delete_event,
        patch("calensync.gwrapper.GoogleCalendarWrapper.service") as service
    ):
        service.return_value = "fake"

        start, end = random_dates()
        source1_1 = Event(calendar=calendar1, event_id=uuid4(), start=start, end=end).save_new()
        event1to2 = Event(calendar=calendar2, source=source1_1, event_id=uuid4(), start=start, end=end).save_new()

        start, end = random_dates()
        source2_1 = Event(calendar=calendar2, event_id=uuid4(), start=start, end=end).save_new()
        event2to1 = Event(calendar=calendar1, source=source2_1, event_id=uuid4(), start=start, end=end).save_new()

        deactivate_calendar(calendar2)

        assert delete_event.call_count == 2
        assert next(filter(lambda x: x.args[2] == event1to2.event_id, delete_event.call_args_list))
        assert next(filter(lambda x: x.args[2] == event2to1.event_id, delete_event.call_args_list))

        calendar2 = calendar2.refresh()
        assert not calendar2.active

        assert Event.get(id=source1_1) is not None
        assert Event.get_or_none(id=event1to2) is None
        assert Event.get_or_none(id=source2_1) is None
        assert Event.get_or_none(id=event2to1) is None


