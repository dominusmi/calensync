import datetime
import json
import os
import unittest.mock
from unittest.mock import patch
import uuid
from typing import List

from calensync.database.model import Event
from calensync.dataclass import GoogleEvent, GoogleDatetime, EventStatus
from calensync.gwrapper import GoogleCalendarWrapper
from calensync.tests.fixtures import *


class Mock:
    pass


def _list_function(calendarId, timeMin, timeMax, timeZone):
    with open("list_events.json") as f:
        data = json.load(f)
    execute_object = Mock()
    execute_object.execute = lambda: data
    return execute_object


def test_google_wrapper_class(db, calendar1):
    event_instances = Mock()
    event_instances.execute = lambda: {"items": []}
    events = Mock()
    events.list = _list_function
    events.instances = lambda *args, **kwargs: event_instances
    service = Mock()
    service.events = lambda: events

    wrapper = GoogleCalendarWrapper(calendar_db=calendar1, service=service)
    events = wrapper.get_events()
    assert len(events) > 1


def test_from_channel_id():
    with DatabaseSession("test"):
        reset_db()
        user = User(email="test1@test.com").save_new()
        account = CalendarAccount(user=user, key="test1", credentials={}).save_new()
        calendar1 = Calendar(account=account, platform_id="platform1", name="name1").save_new()

        wrapper = GoogleCalendarWrapper.from_channel_id(calendar1.channel_id.__str__())
        assert wrapper.google_id == "platform1"


@patch("calensync.gwrapper.GoogleCalendarWrapper.service", lambda *args, **kwargs: None)
def test_solve_update():
    with DatabaseSession("test"):
        reset_db()
        user = User(email="test1@test.com").save_new()
        account = CalendarAccount(user=user, key="test1", credentials={}).save_new()
        calendar1 = Calendar(account=account, platform_id="platform1", name="name1", active=True).save_new()
        gcalendar1 = GoogleCalendarWrapper(calendar1)

        account = CalendarAccount(user=user, key="test2", credentials={}).save_new()
        calendar2 = Calendar(account=account, platform_id="platform2", name="name2", active=False).save_new()

        # test no active calendars
        with unittest.mock.patch(
                "calensync.gwrapper.GoogleCalendarWrapper.get_updated_events") as get_updated_events:
            gcalendar1.solve_update_in_calendar()
            get_updated_events.assert_not_called()

        # test one active calendar, tentative event
        calendar2.active = True
        calendar2.save()
        now = datetime.datetime.utcnow()
        now_google = GoogleDatetime(dateTime=now, timeZone="UCT")

        original_google_events = [
            GoogleEvent(htmlLink="", start=now_google, end=now_google, id="123", created=now, updated=now,
                        status=EventStatus.tentative)
        ]
        with unittest.mock.patch("calensync.gwrapper.GoogleCalendarWrapper.get_updated_events",
                                 return_value=original_google_events) as get_updated_events:
            counter = gcalendar1.solve_update_in_calendar()
            get_updated_events.assert_called_once()
            assert counter == 0

        # test one active calendar, confirmed (new) event
        original_google_events = [
            GoogleEvent(htmlLink="", start=now_google, end=now_google, id=str(uuid.uuid4()), created=now, updated=now,
                        status=EventStatus.confirmed)
        ]

        def mock_google_insert_event(service, calendar_id, start, end, properties):
            """ Mimics the inset event helper """
            if calendar_id == calendar2.platform_id:
                return {"id": "calendar-2-mock-event"}

        with unittest.mock.patch("calensync.gwrapper.insert_event", mock_google_insert_event):
            with unittest.mock.patch("calensync.gwrapper.GoogleCalendarWrapper.get_updated_events",
                                     return_value=original_google_events) as get_updated_events:
                counter = gcalendar1.solve_update_in_calendar()
                get_updated_events.assert_called_once()
                assert counter == 1
                event_db: Event = Event.get_or_none(source_id=original_google_events[0].id)

                assert event_db is not None
                assert event_db.start == original_google_events[0].start.dateTime
                assert event_db.end == original_google_events[0].end.dateTime
                assert event_db.calendar == calendar2
                assert event_db.event_id == "calendar-2-mock-event"

        # test one active calendar, confirmed (updated) event
        # This mock event has start=now, end=now+5min, whereas the db one has start=end=now
        earlier_than_now = GoogleDatetime(dateTime=now - datetime.timedelta(minutes=5), timeZone="UCT")
        original_google_events = [
            GoogleEvent(htmlLink="", start=earlier_than_now, end=now_google, id=str(uuid.uuid4()),
                        created=earlier_than_now.dateTime, updated=now, status=EventStatus.confirmed)
        ]
        Event(calendar=calendar2, source_id=original_google_events[0].id, event_id=str(uuid.uuid4()), start=now,
              end=now).save()

        with unittest.mock.patch("calensync.gwrapper.update_event") as mock_update_event:
            with unittest.mock.patch(
                    "calensync.gwrapper.GoogleCalendarWrapper.get_updated_events",
                    return_value=original_google_events) as get_updated_events:

                counter = gcalendar1.solve_update_in_calendar()
                get_updated_events.assert_called_once()
                assert counter == 1
                mock_update_event.assert_called_once()
                event_db: List[Event] = list(Event.select().where(Event.source_id == original_google_events[0].id))
                assert len(event_db) == 1
                event_db = event_db[0]
                assert event_db.start == original_google_events[0].start.dateTime
                assert event_db.end == original_google_events[0].end.dateTime


def test_insert_events_normal(db, user, calendar1, calendar2):
    with patch("calensync.gwrapper.insert_event") as insert_event:
        with patch("calensync.gwrapper.GoogleCalendarWrapper.service"):
            insert_event.side_effect = lambda **kwargs: {"id": str(uuid.uuid4())}
            gcalendar = GoogleCalendarWrapper(calendar1)

            now = datetime.datetime.utcnow()
            now_google = GoogleDatetime(dateTime=now, timeZone="UCT")

            original_google_events = [
                GoogleEvent(htmlLink="", start=now_google, end=now_google, id="123", created=now, updated=now,
                            status=EventStatus.confirmed)
            ]
            gcalendar.events_handler.add(original_google_events)
            gcalendar.insert_events()
            insert_event.assert_called_once()
            assert Event.select().where(Event.source_id=="123").count() == 1


def test_insert_events_already_exists(user, calendar1, calendar2):
    with patch("calensync.gwrapper.insert_event") as insert_event:
        with patch("calensync.gwrapper.GoogleCalendarWrapper.service"):
            insert_event.side_effect = lambda **kwargs: {"id": str(uuid.uuid4())}
            gcalendar = GoogleCalendarWrapper(calendar1)

            now = datetime.datetime.utcnow()
            now_google = GoogleDatetime(dateTime=now, timeZone="UCT")

            original_google_events = [
                GoogleEvent(htmlLink="", start=now_google, end=now_google, id="123", created=now, updated=now, status=EventStatus.confirmed),
                GoogleEvent(htmlLink="", start=now_google, end=now_google, id="321", created=now, updated=now, status=EventStatus.confirmed)
            ]
            gcalendar.events_handler.add(original_google_events)

            Event(calendar=calendar1, start=now, end=now, event_id="whatver", source_id="321").save_new()
            gcalendar.insert_events()
            insert_event.assert_called_once()
            assert Event.select().where(Event.source_id=="123").count() == 1