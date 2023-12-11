import dataclasses
import datetime
from unittest.mock import patch

from calensync.awslambda.daily_sync import sync_user_calendars_by_date
from calensync.database.model import Event
from calensync.dataclass import GoogleDatetime, AbstractGoogleDate
from calensync.tests.fixtures import *


@dataclasses.dataclass
class MockEvent:
    id: str
    source_id: str
    start: AbstractGoogleDate
    end: AbstractGoogleDate


def test_daily_sync(db, user, account1, calendar1: Calendar, account2, calendar2: Calendar):
    with (
        patch("calensync.gwrapper.insert_event") as insert_event,
        patch("calensync.gwrapper.get_events") as get_events,
        patch("calensync.awslambda.daily_sync.service_from_account") as service_from_account
    ):
        calendar1.active = True
        calendar1.save()
        calendar2.active = True
        calendar2.save()
        calendar3 = Calendar(account=account2, platform_id="platform3", name="name3", active=True).save_new()
        calendar3.save()

        source_ids = ["1", "2", "3"]
        times = [(13, 14), (13, 15), (17, 18)]

        service_from_account.return_value = "fake"

        insert_iteration = [0, 0, 0]

        def mock_insert_event(*args, **kwargs):
            calendar_id = kwargs["calendar_id"]
            if calendar_id == calendar1.platform_id:
                insert_iteration[0] += 1
                return {"id": f"e1_{insert_iteration[0]}"}
            elif calendar_id == calendar2.platform_id:
                insert_iteration[1] += 1
                return {"id": f"e2_{insert_iteration[0]}"}
            elif calendar_id == calendar3.platform_id:
                insert_iteration[2] += 1
                return {"id": f"e3_{insert_iteration[0]}"}

        insert_event.side_effect = mock_insert_event

        # use an array instead of int because updating an int would only update the reference
        iteration = [0]

        def mock_get_events(_, __, s, ___, ____):
            def make_event(source_id, time):
                event_start = datetime.datetime.fromtimestamp(s.timestamp())
                event_start.replace(hour=time[0])
                event_end = datetime.datetime.fromtimestamp(s.timestamp())
                event_end.replace(hour=time[1])

                return MockEvent(source_id, "source_" + source_id, GoogleDatetime(dateTime=event_start),
                                 GoogleDatetime(dateTime=event_end))

            if iteration[0] == 0:
                events = [make_event(source_ids[0], times[0])]
            elif iteration[0] == 1:
                events = [make_event(s, t) for s, t in zip(source_ids[1:], times[1:])]
            else:
                events = []
            iteration[0] += 1
            return events

        get_events.side_effect = mock_get_events

        sync_user_calendars_by_date(db)

        events = list(Event.select().where(Event.calendar_id == calendar1.id))
        assert len(events) == 2
        assert next(filter(lambda x: x.source_id == "2", events))
        assert next(filter(lambda x: x.source_id == "3", events))

        events = list(Event.select().where(Event.calendar_id == calendar2.id))
        assert len(events) == 1
        assert next(filter(lambda x: x.source_id == "1", events))

        events = list(Event.select().where(Event.calendar_id == calendar3.id))
        assert len(events) == 3
        assert next(filter(lambda x: x.source_id == "1", events))
        assert next(filter(lambda x: x.source_id == "2", events))
        assert next(filter(lambda x: x.source_id == "3", events))

        # reset and retry: nothing should happen
        iteration = [0]
        insert_iteration = [0, 0, 0]
        sync_user_calendars_by_date(db)
        events = list(Event.select().where(Event.calendar_id == calendar1.id))
        assert len(events) == 2
        events = list(Event.select().where(Event.calendar_id == calendar2.id))
        assert len(events) == 1
        events = list(Event.select().where(Event.calendar_id == calendar3.id))
        assert len(events) == 3
