import dataclasses
import datetime
from unittest.mock import patch

from calensync.awslambda.daily_sync import sync_user_calendars_by_date, update_watches, \
    get_users_query_with_active_sync_rules
from calensync.database.model import SyncRule
from calensync.dataclass import GoogleDatetime, AbstractGoogleDate, EventStatus
from calensync.tests.fixtures import *
from calensync.utils import utcnow


@dataclasses.dataclass
class MockEvent:
    id: str
    source_id: str
    start: AbstractGoogleDate
    end: AbstractGoogleDate
    status = EventStatus.confirmed


def test_get_users_query_with_active_calendar(user, account1_1, calendar1_1, calendar1_2):
    user2 = User().save_new()
    user2_account = CalendarAccount(key="whauh", credentials="", user=user2).save_new()
    Calendar(account=user2_account, platform_id="platform2_1", name="name2", active=False).save_new()

    query = get_users_query_with_active_sync_rules()
    result = list(query)
    assert len(result) == 0

    SyncRule(source=calendar1_1, destination=calendar1_2, private=True).save_new()

    query = get_users_query_with_active_sync_rules()
    result = list(query)
    assert len(result) == 1
    assert result[0].id == user.id


def test_daily_sync(db, user, account1_1, calendar1_1: Calendar, account1_2, calendar1_2: Calendar):
    with (
        patch("calensync.gwrapper.insert_event") as insert_event,
        patch("calensync.gwrapper.get_events") as get_events,
        patch("calensync.awslambda.daily_sync.service_from_account") as service_from_account
    ):

        calendar1_1.active = True
        calendar1_1.save()
        calendar1_2.active = True
        calendar1_2.save()
        calendar3 = Calendar(account=account1_2, platform_id="platform3", name="name3", active=True).save_new()
        calendar3.save()

        source_ids = ["1", "2", "3"]
        times = [(13, 14), (13, 15), (17, 18)]

        service_from_account.return_value = "fake"

        insert_iteration = [0, 0, 0]

        def mock_insert_event(*args, **kwargs):
            calendar_id = kwargs["calendar_id"]
            if calendar_id == calendar1_1.platform_id:
                insert_iteration[0] += 1
                return {"id": f"e1_{insert_iteration[0]}"}
            elif calendar_id == calendar1_2.platform_id:
                insert_iteration[1] += 1
                return {"id": f"e2_{insert_iteration[1]}"}
            elif calendar_id == calendar3.platform_id:
                insert_iteration[2] += 1
                return {"id": f"e3_{insert_iteration[2]}"}

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

        # events = list(Event.select().where(Event.calendar_id == calendar1_1.id, Event.source.is_null(False)))
        # assert len(events) == 2
        # assert next(filter(lambda x: x.source.event_id == "2", events))
        # assert next(filter(lambda x: x.source.event_id == "3", events))
        #
        # events = list(Event.select().where(Event.calendar_id == calendar1_2.id, Event.source.is_null(False)))
        # assert len(events) == 1
        # assert next(filter(lambda x: x.source.event_id == "1", events))
        #
        # events = list(Event.select().where(Event.calendar_id == calendar3.id, Event.source.is_null(False)))
        # assert len(events) == 3
        # assert next(filter(lambda x: x.source.event_id == "1", events))
        # assert next(filter(lambda x: x.source.event_id == "2", events))
        # assert next(filter(lambda x: x.source.event_id == "3", events))
        #
        # # reset and retry: nothing should happen
        # iteration = [0]
        # insert_iteration = [0, 0, 0]
        # sync_user_calendars_by_date(db)
        # events = list(Event.select().where(Event.calendar_id == calendar1_1.id, Event.source.is_null(False)))
        # assert len(events) == 2
        # events = list(Event.select().where(Event.calendar_id == calendar1_2.id, Event.source.is_null(False)))
        # assert len(events) == 1
        # events = list(Event.select().where(Event.calendar_id == calendar3.id, Event.source.is_null(False)))
        # assert len(events) == 3


def test_sync_user_calendars_by_date_multiple_users(db, user, account1_1, calendar1_1: Calendar, account1_2,
                                                    calendar1_2: Calendar):
    user2 = User(email="tes@t.io", is_admin=True, tos=datetime.datetime.now()).save_new()
    account1_2_1 = CalendarAccount(user=user2, key="wat", credentials={}).save_new()
    c2_1 = Calendar(account=account1_2_1, platform_id="platform2_1", name="name2_1").save_new()
    c2_2 = Calendar(account=account1_2_1, platform_id="platform2_2", name="name2_2").save_new()
    SyncRule(source=c2_1, destination=c2_2, private=True).save_new()
    SyncRule(source=calendar1_1, destination=calendar1_2, private=True).save_new()

    with (
        patch("calensync.awslambda.daily_sync.load_calendars") as load_calendars,
        patch("calensync.awslambda.daily_sync.execute_update") as execute_update
    ):
        load_calendars.return_value = []
        sync_user_calendars_by_date(db)
        assert load_calendars.call_count == 2
        assert execute_update.call_count == 2


class TestUpdateWatches:
    @staticmethod
    def test_normal_case(db, calendar1_1: Calendar, calendar1_2: Calendar, calendar1_1_2: Calendar):
        calendar1_1.expiration = utcnow() + datetime.timedelta(hours=38)
        calendar1_1.save()

        calendar1_2.expiration = utcnow() + datetime.timedelta(hours=35)
        calendar1_2.save()

        SyncRule(source=calendar1_1, destination=calendar1_2, private=True).save_new()
        SyncRule(source=calendar1_2, destination=calendar1_1, private=True).save_new()


        with (
            patch("calensync.gwrapper.GoogleCalendarWrapper.create_watch") as create_watch,
            patch("calensync.gwrapper.GoogleCalendarWrapper.delete_watch") as delete_watch,
        ):
            update_watches(db)
            assert create_watch.call_count == 1
            assert delete_watch.call_count == 1

    @staticmethod
    def test_create_fail_twice(db, calendar1_1: Calendar, calendar1_2: Calendar):
        calendar1_1.expiration = utcnow() + datetime.timedelta(hours=38)
        calendar1_1.save()

        calendar1_2.expiration = utcnow() + datetime.timedelta(hours=35)
        calendar1_2.save()

        SyncRule(source=calendar1_1, destination=calendar1_2, private=True).save_new()
        SyncRule(source=calendar1_2, destination=calendar1_1, private=True).save_new()

        with (
            patch("calensync.gwrapper.GoogleCalendarWrapper.create_watch") as create_watch,
            patch("calensync.gwrapper.GoogleCalendarWrapper.delete_watch") as delete_watch,
            patch("time.sleep") as sleep
        ):
            v = [0]

            def side_effect(v, *args, **kwargs):
                if v[0] < 2:
                    v[0] += 1
                    raise Exception("Error")

            create_watch.side_effect = lambda *args, **kwargs: side_effect(v, *args, **kwargs)
            update_watches(db)
            assert create_watch.call_count == 3
            assert delete_watch.call_count == 1
            assert sleep.call_count == 2

    @staticmethod
    def test_create_fail_delete(db, calendar1_1: Calendar, calendar1_2: Calendar):
        calendar1_1.expiration = utcnow() + datetime.timedelta(hours=38)
        calendar1_1.save()

        calendar1_2.expiration = utcnow() + datetime.timedelta(hours=35)
        calendar1_2.save()

        SyncRule(source=calendar1_1, destination=calendar1_2, private=True).save_new()
        SyncRule(source=calendar1_2, destination=calendar1_1, private=True).save_new()

        with (
            patch("calensync.gwrapper.GoogleCalendarWrapper.create_watch") as create_watch,
            patch("calensync.gwrapper.GoogleCalendarWrapper.delete_watch") as delete_watch,
        ):
            def side_effect(*args, **kwargs):
                raise Exception("error")

            delete_watch.side_effect = lambda *args, **kwargs: side_effect(v, *args, **kwargs)
            update_watches(db)
            assert create_watch.call_count == 1
            assert delete_watch.call_count == 1
