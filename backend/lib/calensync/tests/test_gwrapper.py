import json
import os
from unittest.mock import patch, MagicMock
from typing import List

import pytest

from calensync.database.model import SyncRule
from calensync.dataclass import GoogleEvent, GoogleDatetime, EventStatus
from calensync.gwrapper import GoogleCalendarWrapper
from calensync.tests.fixtures import *
from calensync.tests.mock_service import MockedService


class Mock:
    pass


os.environ["ENV"] = "test"


def test_google_wrapper_class(db, calendar1_1, events_fixture):
    event_instances = Mock()
    event_instances.execute = lambda: {"items": []}
    service = MagicMock()
    service.events.return_value.list.return_value.execute.return_value = events_fixture

    wrapper = GoogleCalendarWrapper(calendar_db=calendar1_1, service=service)
    events = wrapper.get_events()
    assert len(events) > 1


def test_from_channel_id():
    with DatabaseSession("test"):
        reset_db()
        user = User(email="test1@test.com").save_new()
        account = CalendarAccount(user=user, key="test1", credentials={}).save_new()
        calendar1_1 = Calendar(account=account, platform_id="platform1", name="name1").save_new()

        wrapper = GoogleCalendarWrapper.from_channel_id(calendar1_1.channel_id.__str__())
        assert wrapper.google_id == "platform1"


def test_solve_update_tentative(db, account1_1, calendar1_1, account1_2, calendar1_2):
    service = MockedService()
    with patch("calensync.gwrapper.GoogleCalendarWrapper.service", service):
        gcalendar1_1 = GoogleCalendarWrapper(calendar1_1)
        SyncRule(source=calendar1_1, destination=calendar1_2, private=True).save_new()

        now = datetime.datetime.utcnow()
        now_google = GoogleDatetime(dateTime=now, timeZone="UCT")

        service.add_event(
            GoogleEvent(htmlLink="", start=now_google, end=now_google, id="123", created=now, updated=now,
                        status=EventStatus.tentative, summary="summary"),
            gcalendar1_1.google_id
        )

        counter = gcalendar1_1.solve_update_in_calendar()
        assert counter == 0


def test_solve_update_active(db, account1_1, calendar1_1, account1_2, calendar1_2):
    now = datetime.datetime.utcnow()
    now_google = GoogleDatetime(dateTime=now, timeZone="UCT")
    service = MockedService()
    with patch("calensync.gwrapper.GoogleCalendarWrapper.service", service):
        gcalendar1_1 = GoogleCalendarWrapper(calendar1_1)
        SyncRule(source=calendar1_1, destination=calendar1_2, private=True).save_new()

        service.add_event(
            GoogleEvent(htmlLink="", start=now_google, end=now_google, id=str(uuid.uuid4()), created=now, updated=now,
                        status=EventStatus.confirmed, summary="summary"),
            gcalendar1_1.google_id
        )
        counter = gcalendar1_1.solve_update_in_calendar()
        assert counter == 1


@patch("calensync.gwrapper.GoogleCalendarWrapper.service", lambda *args, **kwargs: None)
def test_solve_update_two_active_calendar_confirmed(db, account1_1, calendar1_1, account1_2, calendar1_2):
    service = MockedService()
    with patch("calensync.gwrapper.GoogleCalendarWrapper.service", service):
        gcalendar1_1 = GoogleCalendarWrapper(calendar1_1)
        gcalendar1_2 = GoogleCalendarWrapper(calendar1_2)

        SyncRule(source=calendar1_1, destination=calendar1_2, private=True).save_new()

        now = datetime.datetime.utcnow()
        now_google = GoogleDatetime(dateTime=now, timeZone="UCT")

        # test one active calendar, confirmed (updated) event
        earlier_than_now = GoogleDatetime(dateTime=now - datetime.timedelta(minutes=5), timeZone="UCT")
        service.add_event(
            GoogleEvent(htmlLink="", start=earlier_than_now, end=now_google, id=str(uuid.uuid4()),
                        created=earlier_than_now.dateTime, updated=now, status=EventStatus.confirmed, summary="test"),
            gcalendar1_1.google_id
        )

        counter = gcalendar1_1.solve_update_in_calendar()
        assert counter == 1


# def test_insert_events_normal(db, calendar1_1, calendar1_2):
#     with patch("calensync.gwrapper.insert_event") as insert_event:
#         with patch("calensync.gwrapper.GoogleCalendarWrapper.service"):
#             insert_event.side_effect = lambda **kwargs: {"id": str(uuid.uuid4())}
#             gcalendar = GoogleCalendarWrapper(calendar1_1)
#
#             now = datetime.datetime.utcnow()
#             now_google = GoogleDatetime(dateTime=now, timeZone="UCT")
#
#             original_google_events = [
#                 GoogleEvent(htmlLink="", start=now_google, end=now_google, id="123", created=now, updated=now,
#                             status=EventStatus.confirmed)
#             ]
#             event_db = Event(calendar=calendar1_2, source=None, event_id=original_google_events[0].id, start=now,
#                              end=now).save_new()
#
#             gcalendar.events_handler.add(original_google_events)
#             gcalendar.insert_events()
#             insert_event.assert_called_once()
#             assert Event.select().where(Event.source == event_db, Event.calendar == calendar1_1).count() == 1
#
#
# def test_insert_events_already_exists(calendar1_1, calendar1_2):
#     service = MockedService()
#     with patch("calensync.gwrapper.GoogleCalendarWrapper.service", service):
#         gcalendar = GoogleCalendarWrapper(calendar1_1)
#
#         now = datetime.datetime.utcnow()
#         now_google = GoogleDatetime(dateTime=now, timeZone="UCT")
#
#         original_google_events = [
#             GoogleEvent(htmlLink="", start=now_google, end=now_google, id="123", created=now, updated=now,
#                         status=EventStatus.confirmed, summary="symmary"),
#         ]
#         gcalendar.events_handler.add(original_google_events)
#
#         event_db = Event(calendar=calendar1_2, start=now, end=now, event_id="123").save_new()
#         Event(calendar=calendar1_1, start=now, end=now, event_id=str(uuid.uuid4()), source=event_db).save_new()
#
#         gcalendar.insert_events()
#         insert_event.assert_not_called()
#         assert Event.select().where(Event.event_id == "123").count() == 1
#         query, Source = Event.get_self_reference_query()
#         assert query.where(Source.event_id == "123").count() == 1
#
#
# def test_insert_events_source_doesnt_exist(calendar1_1, calendar1_2):
#     with (
#         patch("calensync.gwrapper.insert_event") as insert_event,
#         patch("calensync.gwrapper.GoogleCalendarWrapper.service")
#     ):
#         # shouldn't insert an event if there's no source as it's not supposed to happen
#         insert_event.side_effect = lambda **kwargs: {"id": str(uuid.uuid4())}
#         gcalendar = GoogleCalendarWrapper(calendar1_1)
#
#         now = datetime.datetime.utcnow()
#         now_google = GoogleDatetime(dateTime=now, timeZone="UCT")
#
#         original_google_events = [
#             GoogleEvent(htmlLink="", start=now_google, end=now_google, id="123", created=now, updated=now,
#                         status=EventStatus.confirmed),
#         ]
#         gcalendar.events_handler.add(original_google_events)
#
#         gcalendar.insert_events()
#         insert_event.assert_called_once()
#         assert Event.select().where(Event.event_id == "123").count() == 0
#         query, Source = Event.get_self_reference_query()
#         assert query.where(Source.event_id == "123").count() == 0
#
#
# class TestDeleteEvents:
#     @staticmethod
#     def test_normal_events(calendar1_1, calendar1_2):
#         with patch("calensync.gwrapper.delete_event") as delete_event:
#             start, end = random_dates()
#             source1_1 = Event(calendar=calendar1_1, event_id=uuid4(), start=start, end=end).save_new()
#             copy1to2 = Event(calendar=calendar1_2, event_id=uuid4(), start=start, end=end, source=source1_1).save_new()
#
#             cal2 = GoogleCalendarWrapper(calendar1_2, service="fake")
#             cal2.events_handler.events_to_delete = [copy1to2]
#             cal2.delete_events()
#
#             delete_event.assert_called_once()
#             assert delete_event.call_args[0][2] == copy1to2.event_id
#             refreshed = copy1to2.refresh()
#             assert refreshed.deleted
#
#     @staticmethod
#     def test_includes_a_source(calendar1_1, calendar1_2):
#         with patch("calensync.gwrapper.delete_event") as delete_event:
#             start, end = random_dates()
#             source1_1 = Event(calendar=calendar1_1, event_id=uuid4(), start=start, end=end).save_new()
#             copy1to2 = Event(calendar=calendar1_2, event_id=uuid4(), start=start, end=end, source=source1_1).save_new()
#
#             start, end = random_dates()
#             source2 = Event(calendar=calendar1_1, event_id=uuid4(), start=start, end=end).save_new()
#
#             cal2 = GoogleCalendarWrapper(calendar1_2, service="fake")
#             cal2.events_handler.events_to_delete = [copy1to2, source2]
#             cal2.delete_events()
#
#             assert delete_event.call_count == 1
#             assert delete_event.call_args[0][2] == copy1to2.event_id
#             refreshed = copy1to2.refresh()
#             assert refreshed.deleted
#             refreshed_source = source2.refresh()
#             assert refreshed_source.deleted
#
#     @staticmethod
#     def test_include_database(calendar1_1, calendar1_2):
#         with patch("calensync.gwrapper.delete_event") as delete_event:
#             start, end = random_dates()
#             source1_1 = Event(calendar=calendar1_1, event_id=uuid4(), start=start, end=end).save_new()
#             copy1to2 = Event(calendar=calendar1_2, event_id=uuid4(), start=start, end=end, source=source1_1).save_new()
#
#             start, end = random_dates()
#             source2 = Event(calendar=calendar1_1, event_id=uuid4(), start=start, end=end).save_new()
#
#             cal2 = GoogleCalendarWrapper(calendar1_2, service="fake")
#             cal2.events_handler.events_to_delete = [copy1to2, source2]
#             cal2.delete_events(include_database=True)
#
#             assert delete_event.call_count == 1
#             assert delete_event.call_args[0][2] == copy1to2.event_id
#             assert Event.get_or_none(id=copy1to2.id) is None
#             assert Event.get_or_none(id=source2.id) is None


class TestDeleteWatch:
    @staticmethod
    def test_all_good(calendar1_1: Calendar):
        calendar1_1.resource_id = "something"
        calendar1_1.save()

        with patch("calensync.gwrapper.delete_google_watch") as delete_google_watch:
            current_google_calendar = GoogleCalendarWrapper(calendar1_1)
            current_google_calendar._service = "whatveer"
            current_google_calendar.delete_watch()
            assert delete_google_watch.call_count == 1
            updated = calendar1_1.refresh()
            assert updated.resource_id is None
            assert updated.expiration is None

    @staticmethod
    def test_read_only(calendar1_1: Calendar):
        calendar1_1.platform_id = "whatever@group.v.calendar.google.com"
        calendar1_1.resource_id = "something"
        calendar1_1.save()
        with patch("calensync.gwrapper.delete_google_watch") as delete_google_watch:
            current_google_calendar = GoogleCalendarWrapper(calendar1_1)
            current_google_calendar.delete_watch()
            assert delete_google_watch.call_count == 0

    @staticmethod
    def test_resource_id_is_none(calendar1_1):
        with patch("calensync.gwrapper.delete_google_watch") as delete_google_watch:
            current_google_calendar = GoogleCalendarWrapper(calendar1_1)
            current_google_calendar.delete_watch()
            assert delete_google_watch.call_count == 0

    @staticmethod
    def test_google_error(calendar1_1: Calendar):
        calendar1_1.resource_id = "something"
        calendar1_1.expiration = datetime.datetime.now()
        calendar1_1.save()
        current_google_calendar = GoogleCalendarWrapper(calendar1_1)
        current_google_calendar._service = "whatveer"

        with patch("calensync.gwrapper.delete_google_watch") as delete_google_watch:
            def side_effect(*args, **kwargs):
                raise Exception("test")

            delete_google_watch.side_effect = side_effect

            with pytest.raises(Exception):
                current_google_calendar.delete_watch()

            assert delete_google_watch.call_count == 1
            updated = calendar1_1.refresh()
            assert updated.resource_id == "something"
            assert updated.expiration is not None
