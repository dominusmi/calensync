import os
import unittest
from collections import defaultdict
from unittest.mock import patch, MagicMock

from calensync.api.tests.util import simulate_sqs_receiver
from calensync.database.model import SyncRule
from calensync.dataclass import GoogleDatetime, EventStatus
from calensync.gwrapper import GoogleCalendarWrapper, make_summary_and_description
from calensync.log import get_logger
from calensync.tests.fixtures import *
from calensync.tests.mock_service import MockedService

logger = get_logger(__file__)


class Mock:
    pass


os.environ["ENV"] = "test"
os.environ["AWS_ACCESS_KEY_ID"] = "123"


def test_google_wrapper_class(db, calendar1_1, events_fixture):
    event_instances = Mock()
    event_instances.execute = lambda: {"items": []}
    service = MagicMock()

    service.events.return_value.list.return_value.execute.return_value = events_fixture
    service.events.return_value.list_next.return_value = None
    wrapper = GoogleCalendarWrapper(calendar_db=calendar1_1, service=service)
    events = wrapper.get_events()
    assert len(events) > 1


def test_get_events_pagination(db, calendar1_1, events_fixture):
    number_of_events_in_fixture = len(events_fixture["items"])
    event_instances = Mock()
    event_instances.execute = lambda: {"items": []}
    service = MagicMock()
    runs = [0]

    def pagination_events(runs):
        if runs[0] < 2:
            items = events_fixture["items"]
            for i, item in enumerate(items):
                item["id"] = f"{i}-{runs[0]}"
            events_fixture["items"] = items
            return events_fixture
        else:
            events_fixture["items"] = []
            return events_fixture

    def pagination_next(runs):
        if runs[0] < 2:
            runs[0] += 1
            mock = MagicMock()
            mock.execute.side_effect = lambda *a, **k: pagination_events(runs)
            return mock
        else:
            return None

    service.events.return_value.list.return_value.execute.side_effect = lambda *a, **k: pagination_events(runs)
    service.events.return_value.list_next.side_effect = lambda *a: pagination_next(runs)
    wrapper = GoogleCalendarWrapper(calendar_db=calendar1_1, service=service)
    events = wrapper.get_events()

    assert len(events) == 2 * number_of_events_in_fixture
    ids = set([])
    for i in range(number_of_events_in_fixture):
        for j in range(2):
            ids.add(f"{i}-{j}")

    assert {e.id for e in events} == ids
    assert len(events) > 1


def test_from_channel_id():
    with DatabaseSession("test"):
        reset_db()
        user = User(email="test1@test.com").save_new()
        account = CalendarAccount(user=user, key="test1", credentials={}).save_new()
        calendar1_1 = Calendar(account=account, platform_id="platform1", name="name1").save_new()

        wrapper = GoogleCalendarWrapper.from_channel_id(calendar1_1.channel_id.__str__())
        assert wrapper.google_id == "platform1"


@mock_aws
def test_solve_update_tentative(db, account1_1, calendar1_1, account1_2, calendar1_2, boto_session, queue_url):
    service = MockedService()
    with patch("calensync.gwrapper.GoogleCalendarWrapper.service", service):
        gcalendar1_1 = GoogleCalendarWrapper(calendar1_1, session=boto_session)
        SyncRule(source=calendar1_1, destination=calendar1_2, private=True).save_new()

        now = datetime.datetime.utcnow()
        now_google = GoogleDatetime(dateTime=now, timeZone="UCT")

        service.add_event(
            GoogleEvent(htmlLink="", start=now_google, end=now_google, id="123", created=now, updated=now,
                        status=EventStatus.tentative, summary="summary"),
            gcalendar1_1.google_id
        )

        gcalendar1_1.solve_update_in_calendar()
        simulate_sqs_receiver(boto_session, queue_url, db)


@mock_aws
def test_solve_update_active(db, account1_1, calendar1_1, account1_2, calendar1_2, boto_session, queue_url):
    now = datetime.datetime.utcnow()
    now_google = GoogleDatetime(dateTime=now, timeZone="UCT")
    service = MockedService()
    real_push_event_to_rules = GoogleCalendarWrapper.push_event_to_rules
    with (
        patch("calensync.gwrapper.GoogleCalendarWrapper.service", service),
        patch("calensync.gwrapper.GoogleCalendarWrapper.push_event_to_rules") as push_event_to_rules
    ):
        gcalendar1_1 = GoogleCalendarWrapper(calendar1_1, session=boto_session)
        SyncRule(source=calendar1_1, destination=calendar1_2, private=True).save_new()

        service.add_event(
            GoogleEvent(htmlLink="", start=now_google, end=now_google, id=str(uuid.uuid4()), created=now, updated=now,
                        status=EventStatus.confirmed, summary="summary"),
            gcalendar1_1.google_id
        )
        gcalendar1_1.solve_update_in_calendar()

        counter = [0]

        def _push_event_to_rules_side_effect(*args, **kwargs):
            counter[0] += real_push_event_to_rules(*args, **kwargs)

        push_event_to_rules.side_effect = _push_event_to_rules_side_effect

        simulate_sqs_receiver(boto_session, queue_url, db)
        assert counter[0] == 1


def test_solve_update_two_active_calendar_confirmed(db, account1_1, calendar1_1, account1_2, calendar1_2, boto_session, queue_url):
    service = MockedService()
    real_push_event_to_rules = GoogleCalendarWrapper.push_event_to_rules
    with (
        patch("calensync.gwrapper.GoogleCalendarWrapper.service", service),
        patch("calensync.gwrapper.GoogleCalendarWrapper.push_event_to_rules") as push_event_to_rules
    ):

        gcalendar1_1 = GoogleCalendarWrapper(calendar1_1, session=boto_session)
        gcalendar1_2 = GoogleCalendarWrapper(calendar1_2, session=boto_session)

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

        gcalendar1_1.solve_update_in_calendar()
        counter = [0]

        def _push_event_to_rules_side_effect(*args, **kwargs):
            counter[0] += real_push_event_to_rules(*args, **kwargs)

        push_event_to_rules.side_effect = _push_event_to_rules_side_effect

        simulate_sqs_receiver(boto_session, queue_url, db)
        assert counter[0] == 1


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
        calendar1_1.readonly = True
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


class TestMakeSummaryAndDescription:
    @staticmethod
    def test_normal(calendar1_1, calendar1_2):
        event = GoogleEvent(id="1", status=EventStatus.confirmed,
                            summary="test", description="description"
                            )
        rule = SyncRule(source=calendar1_1, destination=calendar1_2, summary="%original%", description="%original%")

        summary, description = make_summary_and_description(event, rule)
        assert summary == "test"
        assert description == "description"

    @staticmethod
    def test_template(calendar1_1, calendar1_2):
        event = GoogleEvent(id="1", status=EventStatus.confirmed,
                            summary="test", description="description"
                            )
        rule = SyncRule(source=calendar1_1, destination=calendar1_2,
                        summary="Copy: %original%",
                        description="Description: %original%"
                        )

        summary, description = make_summary_and_description(event, rule)
        assert summary == "Copy: test"
        assert description == "Description: description"

    @staticmethod
    def test_event_summary_description_none(calendar1_1, calendar1_2):
        event = GoogleEvent(id="1", status=EventStatus.confirmed,
                            summary=None, description=None
                            )
        rule = SyncRule(source=calendar1_1, destination=calendar1_2,
                        summary="%original%",
                        description="%original%"
                        )

        summary, description = make_summary_and_description(event, rule)
        assert summary == "Blocker"
        assert description is None

    @staticmethod
    def test_rule_template_none(calendar1_1, calendar1_2):
        event = GoogleEvent(id="1", status=EventStatus.confirmed,
                            summary="test", description="description"
                            )
        rule = SyncRule(source=calendar1_1, destination=calendar1_2,
                        summary=None,
                        description=None
                        )

        summary, description = make_summary_and_description(event, rule)
        assert summary == "Blocker"
        assert description is None

    @staticmethod
    def test_overwritten(calendar1_1, calendar1_2):
        event = GoogleEvent(id="1", status=EventStatus.confirmed,
                            summary="Something", description="some"
                            )
        rule = SyncRule(source=calendar1_1, destination=calendar1_2,
                        summary="Title",
                        description="Description"
                        )

        summary, description = make_summary_and_description(event, rule)
        assert summary == "Title"
        assert description == "Description"
