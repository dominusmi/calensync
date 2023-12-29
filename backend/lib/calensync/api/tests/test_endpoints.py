import datetime
from unittest.mock import patch, MagicMock
import uuid

import pytest

from calensync.api.common import ApiError
from calensync.api.endpoints import patch_calendar, received_webhook, process_calendars, delete_sync_rule
from calensync.database.model import Event, SyncRule
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
        with patch("calensync.gwrapper.GoogleCalendarWrapper.get_events") as mock_get_events:
            with patch("calensync.gwrapper.GoogleCalendarWrapper.create_watch") as mock_create_watch:
                patch_calendar(user, str(calendar1.uuid), CalendarStateEnum.ACTIVE, db)
                mock_get_events.assert_not_called()
                mock_create_watch.assert_called_once()


class TestWebhook:
    @staticmethod
    def test_no_recent_insertion(db, user: User, calendar1: Calendar):
        calendar1.last_inserted = utcnow() - datetime.timedelta(seconds=187)
        calendar1.save()
        with patch("calensync.gwrapper.GoogleCalendarWrapper.solve_update_in_calendar") as mocked:
            received_webhook(str(calendar1.channel_id), "", "resource1", str(calendar1.token), db)
            mocked.assert_called_once()
            c = calendar1.refresh()
            assert (utcnow() - c.last_received.replace(tzinfo=datetime.timezone.utc)).seconds < 5

    @staticmethod
    def test_with_recent_insertion(db, user, calendar1):
        new_inserted_dt = utcnow() - datetime.timedelta(seconds=10)
        calendar1.last_inserted = new_inserted_dt
        calendar1.save()
        with patch("calensync.gwrapper.GoogleCalendarWrapper.solve_update_in_calendar") as mocked:
            with pytest.raises(ApiError):
                received_webhook(str(calendar1.channel_id), "", "resource1", str(calendar1.token), db)
            mocked.assert_not_called()
            c = calendar1.refresh()
            # last received should be updated, but not last inserted no
            assert (utcnow() - c.last_received.replace(tzinfo=datetime.timezone.utc)).seconds < 5
            assert c.last_inserted.replace(tzinfo=datetime.timezone.utc) == new_inserted_dt


class TestProcessCalendar:
    @staticmethod
    def test_process_calendar(db, user, calendar1, calendar2):
        now = utcnow()
        three_minutes_ago = now - datetime.timedelta(seconds=180)
        calendar1.active = True
        calendar1.last_inserted = three_minutes_ago
        calendar1.last_processed = three_minutes_ago
        calendar1.save()

        user2 = User(email="test@test.com").save_new()
        account21 = CalendarAccount(user=user2, key="key2", credentials={"key": "value"}).save_new()
        calendar21 = Calendar(account=account21, platform_id="platform_id21", name="name21", active=True,
                              last_processed=three_minutes_ago, last_inserted=three_minutes_ago).save_new()

        with patch("calensync.gwrapper.GoogleCalendarWrapper.solve_update_in_calendar") as mocked:
            process_calendars()
            assert mocked.call_count == 2


class TestDeleteSyncRule:
    @staticmethod
    def test_normal_case(user, calendar1, calendar2):
        with (
            patch("calensync.api.endpoints.GoogleCalendarWrapper") as gwrapper,
            patch("calensync.gwrapper.delete_event") as delete_event
        ):
            start, end = random_dates()

            rule2 = SyncRule(source=calendar2, destination=calendar1, private=True).save_new()
            source2_1 = Event(calendar=calendar2, event_id=uuid4(), start=start, end=end).save_new()
            copy2_1to1 = Event(calendar=calendar1, event_id=uuid4(), start=start, end=end, source=source2_1,
                               source_rule=rule2).save_new()

            rule = SyncRule(source=calendar1, destination=calendar2, private=True).save_new()
            source1_1 = Event(calendar=calendar1, event_id=uuid4(), start=start, end=end).save_new()
            copy1_1to2 = Event(calendar=calendar2, event_id=uuid4(), start=start, end=end, source=source1_1,
                               source_rule=rule).save_new()

            source1_2 = Event(calendar=calendar1, event_id=uuid4(), start=start, end=end).save_new()
            copy1_2to2 = Event(calendar=calendar2, event_id=uuid4(), start=start, end=end, source=source1_2,
                               source_rule=rule).save_new()

            source2_1 = Event(calendar=calendar2, event_id=uuid4(), start=start, end=end).save_new()

            added_events = []

            def mock_events_handler_delete(events):
                added_events.extend(events)

            def mock_delete_events():
                for event in added_events:
                    event.delete_instance()
                    event.delete_instance()

            gwrapper.return_value.events_handler.delete.side_effect = mock_events_handler_delete
            gwrapper.return_value.delete_events.side_effect = mock_delete_events
            delete_sync_rule(user, str(rule.uuid))
            assert Event.get_or_none(id=copy1_1to2.id) is None
            assert Event.get_or_none(id=copy1_2to2.id) is None
            assert Event.get_or_none(id=source2_1.id) is not None
            assert Event.get_or_none(id=copy2_1to1.id) is not None
            assert SyncRule.get_or_none(id=rule.id) is None
            assert SyncRule.get_or_none(id=rule2.id) is not None
            assert gwrapper.return_value.delete_watch.call_count == 1

    @staticmethod
    def test_delete_watch_with_other_source(user, account1, calendar1, calendar2):
        with (
            patch("calensync.api.endpoints.GoogleCalendarWrapper") as gwrapper,
            patch("calensync.gwrapper.delete_event") as delete_event
        ):
            start, end = random_dates()

            rule = SyncRule(source=calendar1, destination=calendar2, private=True).save_new()
            source1_1 = Event(calendar=calendar1, event_id=uuid4(), start=start, end=end).save_new()
            copy1_1to2 = Event(calendar=calendar2, event_id=uuid4(), start=start, end=end, source=source1_1,
                               source_rule=rule).save_new()

            calendar3 = Calendar(account=account1, platform_id="platform3", name="name3", active=False).save_new()
            rule2 = SyncRule(source=calendar1, destination=calendar3, private=False).save_new()

            # needed to avoid integrity error
            gwrapper.return_value.delete_events.side_effect = lambda: copy1_1to2.delete_instance()

            delete_sync_rule(user, str(rule.uuid))

            assert gwrapper.return_value.delete_watch.call_count == 0
            assert SyncRule.get_or_none(id=rule.id) is None
            assert SyncRule.get_or_none(id=rule2.id) is not None

    @staticmethod
    def test_user_doesnt_have_permission(user, calendar1, calendar2):
        with patch("calensync.gwrapper.GoogleCalendarWrapper") as gwrapper:
            rule = SyncRule(source=calendar1, destination=calendar2, private=True).save_new()
            start, end = random_dates()
            source1_1 = Event(calendar=calendar1, event_id=uuid4(), start=start, end=end).save_new()
            copy1_1to2 = Event(calendar=calendar2, event_id=uuid4(), start=start, end=end, source=source1_1,
                               source_rule=rule).save_new()

            new_user = User(email="test2@test.com").save_new()
            with pytest.raises(ApiError):
                delete_sync_rule(new_user, str(rule.uuid))
