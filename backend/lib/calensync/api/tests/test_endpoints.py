import datetime
import unittest.mock
import uuid

import pytest

from calensync.api.common import ApiError
from calensync.api.endpoints import patch_calendar, received_webhook, process_calendars
from calensync.dataclass import CalendarStateEnum
from calensync.tests.fixtures import *
from calensync.utils import utcnow


class TestPatchCalendar:
    @staticmethod
    def test_doesnt_exist(db, user):
        with pytest.raises(ApiError):
            patch_calendar(user.id, uuid4(), CalendarStateEnum.ACTIVE, db)

    @staticmethod
    def test_user_doesnt_own_calendar(db, user, calendar1):
        other_user = User(email="random@test.com").save_new()
        with pytest.raises(ApiError):
            patch_calendar(other_user.id, str(calendar1.uuid), CalendarStateEnum.ACTIVE, db)

    @staticmethod
    def test_no_active_calendars(db, user, account1, calendar1, calendar2):
        with unittest.mock.patch("calensync.gwrapper.GoogleCalendarWrapper.get_events") as mock_get_events:
            with unittest.mock.patch("calensync.gwrapper.GoogleCalendarWrapper.create_watch") as mock_create_watch:
                patch_calendar(user, str(calendar1.uuid), CalendarStateEnum.ACTIVE, db)
                mock_get_events.assert_not_called()
                mock_create_watch.assert_called_once()


class TestWebhook:
    @staticmethod
    def test_no_recent_insertion(db, user: User, calendar1: Calendar):
        calendar1.last_inserted = utcnow() - datetime.timedelta(seconds=187)
        calendar1.save()
        with unittest.mock.patch("calensync.gwrapper.GoogleCalendarWrapper.solve_update_in_calendar") as mocked:
            received_webhook(str(calendar1.channel_id), "", "resource1", str(calendar1.token), db)
            mocked.assert_called_once()
            c = calendar1.refresh()
            assert (utcnow() - c.last_received.replace(tzinfo=datetime.timezone.utc)).seconds < 5

    @staticmethod
    def test_with_recent_insertion(db, user, calendar1):
        new_inserted_dt = utcnow() - datetime.timedelta(seconds=10)
        calendar1.last_inserted = new_inserted_dt
        calendar1.save()
        with unittest.mock.patch("calensync.gwrapper.GoogleCalendarWrapper.solve_update_in_calendar") as mocked:
            with pytest.raises(ApiError):
                received_webhook(str(calendar1.channel_id), "", "resource1", str(calendar1.token), db)
            mocked.assert_not_called()
            c = calendar1.refresh()
            # last received should be updated, but not last inserted no
            assert (utcnow() - c.last_received.replace(tzinfo=datetime.timezone.utc)).seconds < 5
            assert c.last_inserted.replace(tzinfo=datetime.timezone.utc) == new_inserted_dt


class TestProcessCalendar:
    def test_process_calendar(db, user, calendar1, calendar2):
        now = utcnow()
        three_minutes_ago = now - datetime.timedelta(seconds=180)
        calendar1.active = True
        calendar1.last_inserted = three_minutes_ago
        calendar1.last_processed = three_minutes_ago
        calendar1.save()

        user2 = User(email="test@test.com").save_new()
        account21 = CalendarAccount(user=user2, key="key2", credentials={"key": "value"}).save_new()
        calendar21 = Calendar(account=account21, platform_id="platform_id21", name="name21", active=True, last_processed=three_minutes_ago, last_inserted=three_minutes_ago).save_new()

        with unittest.mock.patch("calensync.gwrapper.GoogleCalendarWrapper.solve_update_in_calendar") as mocked:
            process_calendars()
            assert mocked.call_count == 2




