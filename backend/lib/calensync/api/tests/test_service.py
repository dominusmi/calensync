import datetime
import unittest.mock
from unittest.mock import MagicMock

from calensync.api.service import activate_calendar, verify_valid_sync_rule
from calensync.database.model import SyncRule
from calensync.dataclass import GoogleEvent, GoogleDatetime, EventStatus
from calensync.gwrapper import GoogleCalendarWrapper
from calensync.tests.fixtures import *
from calensync.utils import utcnow


def test_patch_calendar_calendar_active(db, user, account1, calendar1, calendar2):
    calendar1.active = True
    calendar1.save()
    with unittest.mock.patch("calensync.gwrapper.GoogleCalendarWrapper.get_events") as mocked:
        activate_calendar(calendar1)
    mocked.assert_not_called()


def test_patch_calendar_normal(db, user, account1, calendar1, account2, calendar2):
    calendar2.active = True
    calendar2.save()

    def set_events(self, *args, **kwargs):
        self.events = []

    with unittest.mock.patch("calensync.gwrapper.GoogleCalendarWrapper.get_events", autospec=True) as mock_get_events:
        with unittest.mock.patch("calensync.gwrapper.GoogleCalendarWrapper.create_watch",
                                 autospec=True) as mock_create_watch:
            mock_get_events.side_effect = set_events
            activate_calendar(calendar1)

    assert mock_get_events.call_count == 2


def test_activate_normal_case(db, user, account1, calendar1, account2, calendar2):
    calendar2.active = True
    calendar2.save()

    datetime1 = datetime.datetime.fromisoformat("2022-10-06T12:00:00.000000")
    datetime2 = datetime.datetime.fromisoformat("2022-10-09T14:00:00.000000")
    datetime3 = datetime.datetime.fromisoformat("2022-10-09T14:30:00.000000")
    m30 = datetime.timedelta(minutes=30)
    m60 = datetime.timedelta(minutes=60)

    events1 = [
        GoogleEvent(htmlLink="", id="calendar1-1", start=GoogleDatetime(dateTime=datetime1, timeZone="UCT"),
                    end=GoogleDatetime(dateTime=datetime1 + m30, timeZone="UCT"), created=datetime1,
                    updated=datetime1, status=EventStatus.confirmed.value),
        GoogleEvent(htmlLink="", id="calendar1-2", start=GoogleDatetime(dateTime=datetime2, timeZone="UCT"),
                    end=GoogleDatetime(dateTime=datetime2 + m60, timeZone="UCT"), created=datetime1,
                    updated=datetime1, status=EventStatus.confirmed.value),
        GoogleEvent(htmlLink="", id="calendar1-3", start=GoogleDatetime(dateTime=datetime3, timeZone="UCT"),
                    end=GoogleDatetime(dateTime=datetime3 + m30, timeZone="UCT"), created=datetime1,
                    updated=datetime1, status=EventStatus.confirmed.value),
    ]

    events2 = [
        GoogleEvent(htmlLink="", id="calendar2-1", start=GoogleDatetime(dateTime=datetime1, timeZone="UCT"),
                    end=GoogleDatetime(dateTime=datetime1 + m30, timeZone="UCT"), created=datetime1,
                    updated=datetime1, status=EventStatus.confirmed.value),
        GoogleEvent(htmlLink="", id="calendar2-2", start=GoogleDatetime(dateTime=datetime2, timeZone="UCT"),
                    end=GoogleDatetime(dateTime=datetime2 + m60, timeZone="UCT"), created=datetime1,
                    updated=datetime1, status=EventStatus.confirmed.value),
        GoogleEvent(htmlLink="", id="calendar2-3", start=GoogleDatetime(dateTime=datetime3, timeZone="UCT"),
                    end=GoogleDatetime(dateTime=datetime3 + m30, timeZone="UCT"), created=datetime1,
                    updated=datetime1, status=EventStatus.confirmed.value),
    ]

    def _get_events(self: GoogleCalendarWrapper, start, end):
        if self.google_id == "platform1":
            self.events = events1
            return events1
        if self.google_id == "platform2":
            self.events = events2
            return events2
        raise SystemError()

    def _insert_events(self: GoogleCalendarWrapper):
        assert not self.events_handler.events_to_delete
        assert not self.events_handler.events_to_update

        if self.google_id == "platform1":
            assert {e.id for e in self.events_handler.events_to_add} == {"calendar2-1", "calendar2-2", "calendar2-3"}

        elif self.google_id == "platform2":
            assert {e.id for e in self.events_handler.events_to_add} == {"calendar1-1", "calendar1-2", "calendar1-3"}

        else:
            assert False

    with unittest.mock.patch("calensync.gwrapper.GoogleCalendarWrapper.get_events", autospec=True) as mock_get_events:
        mock_get_events.side_effect = _get_events
        with unittest.mock.patch("calensync.gwrapper.GoogleCalendarWrapper.insert_events", autospec=True) as mock_insert_events:
            mock_insert_events.side_effect = _insert_events
            with unittest.mock.patch("calensync.gwrapper.build", lambda *args, **kwargs: "service"):
                with unittest.mock.patch("calensync.gwrapper.GoogleCalendarWrapper.create_watch",
                                         return_value=None) as mock_create_watch:
                    activate_calendar(calendar1)
                    mock_create_watch.assert_called_once()

    assert mock_insert_events.call_count == 2
    assert mock_get_events.call_count == 2


class TestVerifySyncRule:
    @staticmethod
    def test_valid_case(user, calendar1, calendar2):
        assert verify_valid_sync_rule(user, str(calendar1.uuid), str(calendar2.uuid)) is None

    @staticmethod
    def test_same_calendar(user, calendar1):
        assert verify_valid_sync_rule(user, str(calendar1.uuid), str(calendar1.uuid)) is not None

    @staticmethod
    def test_user_doesnt_own_calendar(user, calendar1):
        user2 = User(email="test@test.com").save_new()
        account21 = CalendarAccount(user=user2, key="key2", credentials={"key": "value"}).save_new()
        calendar21 = Calendar(account=account21, platform_id="platform_id21", name="name21", active=True,
                              last_processed=utcnow(), last_inserted=utcnow()).save_new()

        assert verify_valid_sync_rule(user, str(calendar1.uuid), str(calendar21.uuid)) is not None

    @staticmethod
    def test_rule_already_exists(user, calendar1, calendar2):
        SyncRule(source=calendar1, destination=calendar2, private=True).save()
        assert verify_valid_sync_rule(user, str(calendar1.uuid), str(calendar2.uuid)) is not None

    @staticmethod
    def test_two_way_should_work(user, calendar1, calendar2):
        SyncRule(source=calendar1, destination=calendar2, private=True).save()
        assert verify_valid_sync_rule(user, str(calendar2.uuid), str(calendar1.uuid)) is None
