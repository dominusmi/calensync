from unittest.mock import patch, MagicMock

import google.auth.exceptions

from calensync.api.tests.util import simulate_sqs_receiver
from calensync.database.model import SyncRule
from calensync.dataclass import GoogleDatetime, EventStatus, ExtendedProperties, EventExtendedProperty
from calensync.gwrapper import GoogleCalendarWrapper, make_summary_and_description, handle_refresh_error
from calensync.libcalendar import PushToQueueException
from calensync.log import get_logger
from calensync.tests.fixtures import *
from calensync.tests.mock_service import MockedService
from calensync.utils import utcnow, INVALID_GRANT_ERROR

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


def test_from_channel_id(boto_session):
    with DatabaseSession("test"):
        reset_db()
        user = User(email="test1@test.com").save_new()
        account = CalendarAccount(user=user, key="test1",
                                  encrypted_credentials=encrypt_credentials({}, boto_session)).save_new()
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


def test_solve_update_two_active_calendar_confirmed(db, account1_1, calendar1_1, account1_2, calendar1_2, boto_session,
                                                    queue_url):
    service = MockedService()
    real_push_event_to_rule = GoogleCalendarWrapper.push_event_to_rule
    with (
        patch("calensync.gwrapper.GoogleCalendarWrapper.service", service),
        patch("calensync.gwrapper.GoogleCalendarWrapper.push_event_to_rule") as push_event_to_rule
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

        def _push_event_to_rule_side_effect(*args, **kwargs):
            counter[0] += real_push_event_to_rule(*args, **kwargs)

        push_event_to_rule.side_effect = _push_event_to_rule_side_effect

        simulate_sqs_receiver(boto_session, queue_url, db)
        assert counter[0] == 1


class TestPushEventToRules:

    @staticmethod
    def test_normal_insert(calendar1_1, calendar1_2):
        rule = SyncRule(source_id=calendar1_1.id, destination_id=calendar1_2.id).save_new()
        start = utcnow() + datetime.timedelta(days=1)
        end = utcnow() + datetime.timedelta(days=1, hours=1)
        event = GoogleEvent(
            id="123", status=EventStatus.confirmed,
            start=GoogleDatetime(dateTime=start), end=GoogleDatetime(dateTime=end),
            created=utcnow(), updated=utcnow(),
        )
        with (
            patch("calensync.gwrapper.GoogleCalendarWrapper.get_events") as get_events,
            patch("calensync.gwrapper.GoogleCalendarWrapper.service"),
            patch("calensync.gwrapper.insert_event") as insert_event
        ):
            get_events.return_value = []
            GoogleCalendarWrapper.push_event_to_rule(event, rule)
            assert get_events.call_count == 1
            assert insert_event.call_count == 1

    @staticmethod
    def test_normal_update(calendar1_1, calendar1_2):
        rule = SyncRule(source_id=calendar1_1.id, destination_id=calendar1_2.id).save_new()
        start = utcnow() + datetime.timedelta(days=1)
        end = utcnow() + datetime.timedelta(days=1, hours=1)
        event = GoogleEvent(
            id="123", status=EventStatus.confirmed,
            start=GoogleDatetime(dateTime=start), end=GoogleDatetime(dateTime=end),
            created=utcnow() - datetime.timedelta(minutes=5), updated=utcnow(),
        )
        with (
            patch("calensync.gwrapper.GoogleCalendarWrapper.get_events") as get_events,
            patch("calensync.gwrapper.GoogleCalendarWrapper.service"),
            patch("calensync.gwrapper.insert_event") as insert_event,
            patch("calensync.gwrapper.update_event") as update_event
        ):
            get_events.return_value = [
                GoogleEvent(
                    id="321", status=EventStatus.confirmed,
                    start=GoogleDatetime(dateTime=start), end=GoogleDatetime(dateTime=end),
                    created=utcnow(), updated=utcnow(), extendedProperties=ExtendedProperties.from_sources(
                        event.id, calendar1_1.id
                    )
                )
            ]
            GoogleCalendarWrapper.push_event_to_rule(event, rule)
            assert get_events.call_count == 1
            assert insert_event.call_count == 0
            assert update_event.call_count == 1

    @staticmethod
    def test_update_but_doesnt_exist_so_insert(calendar1_1, calendar1_2):
        rule = SyncRule(source_id=calendar1_1.id, destination_id=calendar1_2.id).save_new()
        start = utcnow() + datetime.timedelta(days=1)
        end = utcnow() + datetime.timedelta(days=1, hours=1)
        event = GoogleEvent(
            id="123", status=EventStatus.confirmed,
            start=GoogleDatetime(dateTime=start), end=GoogleDatetime(dateTime=end),
            created=utcnow() - datetime.timedelta(minutes=5), updated=utcnow(),
        )
        with (
            patch("calensync.gwrapper.GoogleCalendarWrapper.get_events") as get_events,
            patch("calensync.gwrapper.GoogleCalendarWrapper.service"),
            patch("calensync.gwrapper.insert_event") as insert_event,
            patch("calensync.gwrapper.update_event") as update_event
        ):
            get_events.return_value = []
            GoogleCalendarWrapper.push_event_to_rule(event, rule)
            assert get_events.call_count == 1
            assert insert_event.call_count == 1
            assert update_event.call_count == 0

    @staticmethod
    def test_recurrent_instance_update_but_source_not_there(calendar1_1, calendar1_2):
        rule = SyncRule(source_id=calendar1_1.id, destination_id=calendar1_2.id).save_new()
        start = utcnow() + datetime.timedelta(days=1)
        end = utcnow() + datetime.timedelta(days=1, hours=1)
        event = GoogleEvent(
            id="123_321", status=EventStatus.confirmed,
            start=GoogleDatetime(dateTime=start), end=GoogleDatetime(dateTime=end),
            created=utcnow() - datetime.timedelta(minutes=5), updated=utcnow(),
            recurringEventId="123"
        )
        with (
            patch("calensync.gwrapper.GoogleCalendarWrapper.get_events") as get_events,
            patch("calensync.gwrapper.GoogleCalendarWrapper.service"),
            patch("calensync.gwrapper.insert_event") as insert_event,
            patch("calensync.gwrapper.update_event") as update_event
        ):
            get_events.return_value = []
            with pytest.raises(PushToQueueException):
                GoogleCalendarWrapper.push_event_to_rule(event, rule)
            assert get_events.call_count == 2
            assert insert_event.call_count == 0
            assert update_event.call_count == 0

    @staticmethod
    def test_recurrent_instance_insert(calendar1_1, calendar1_2):
        rule = SyncRule(source_id=calendar1_1.id, destination_id=calendar1_2.id).save_new()
        start = utcnow() + datetime.timedelta(days=1)
        end = utcnow() + datetime.timedelta(days=1, hours=1)
        recurrent_source = GoogleEvent(
            id="123", status=EventStatus.confirmed,
            start=GoogleDatetime(dateTime=start), end=GoogleDatetime(dateTime=end),
            created=utcnow() - datetime.timedelta(minutes=5), updated=utcnow()
        )
        recurrent_instance = GoogleEvent(
            id="123_321", status=EventStatus.confirmed,
            start=GoogleDatetime(dateTime=start), end=GoogleDatetime(dateTime=end),
            created=utcnow() - datetime.timedelta(minutes=5), updated=utcnow(),
            recurringEventId="123", originalStartTime=GoogleDatetime(dateTime=start)
        )
        with (
            patch("calensync.gwrapper.GoogleCalendarWrapper.get_events") as get_events,
            patch("calensync.gwrapper.GoogleCalendarWrapper.service"),
            patch("calensync.gwrapper.insert_event") as insert_event,
            patch("calensync.gwrapper.update_event") as update_event
        ):
            def simulate_get_events(**kwargs):
                extended_properties = kwargs['private_extended_properties']
                if extended_properties[EventExtendedProperty.get_source_id_key()] == "123_321":
                    return []
                elif extended_properties[EventExtendedProperty.get_source_id_key()] == "123":
                    return [recurrent_source]
                else:
                    raise RuntimeError("Shouldn't happen in this test")

            get_events.side_effect = simulate_get_events
            GoogleCalendarWrapper.push_event_to_rule(recurrent_instance, rule)
            assert get_events.call_count == 2
            assert insert_event.call_count == 1
            assert update_event.call_count == 0

    @staticmethod
    def test_recurrent_instance_update(calendar1_1, calendar1_2):
        rule = SyncRule(source_id=calendar1_1.id, destination_id=calendar1_2.id).save_new()
        start = utcnow() + datetime.timedelta(days=1)
        end = utcnow() + datetime.timedelta(days=1, hours=1)
        recurrent_source = GoogleEvent(
            id="123", status=EventStatus.confirmed,
            start=GoogleDatetime(dateTime=start), end=GoogleDatetime(dateTime=end),
            created=utcnow() - datetime.timedelta(minutes=5), updated=utcnow()
        )
        recurrent_instance = GoogleEvent(
            id="123_321", status=EventStatus.confirmed,
            start=GoogleDatetime(dateTime=start), end=GoogleDatetime(dateTime=end),
            created=utcnow() - datetime.timedelta(minutes=5), updated=utcnow(),
            recurringEventId="123", originalStartTime=GoogleDatetime(dateTime=start)
        )
        with (
            patch("calensync.gwrapper.GoogleCalendarWrapper.get_events") as get_events,
            patch("calensync.gwrapper.GoogleCalendarWrapper.service"),
            patch("calensync.gwrapper.insert_event") as insert_event,
            patch("calensync.gwrapper.update_event") as update_event
        ):
            def simulate_get_events(**kwargs):
                extended_properties = kwargs['private_extended_properties']
                if extended_properties[EventExtendedProperty.get_source_id_key()] == "123_321":
                    return [recurrent_instance]
                elif extended_properties[EventExtendedProperty.get_source_id_key()] == "123":
                    return [recurrent_source]
                else:
                    raise RuntimeError("Shouldn't happen in this test")

            get_events.side_effect = simulate_get_events
            GoogleCalendarWrapper.push_event_to_rule(recurrent_instance, rule)
            assert get_events.call_count == 1
            assert insert_event.call_count == 0
            assert update_event.call_count == 1

    @staticmethod
    def test_delete_event(calendar1_1, calendar1_2):
        rule = SyncRule(source_id=calendar1_1.id, destination_id=calendar1_2.id).save_new()
        start = utcnow() + datetime.timedelta(days=1)
        end = utcnow() + datetime.timedelta(days=1, hours=1)
        event = GoogleEvent(
            id="123", status=EventStatus.cancelled,
            start=GoogleDatetime(dateTime=start), end=GoogleDatetime(dateTime=end),
            created=utcnow() - datetime.timedelta(minutes=5), updated=utcnow()
        )

        copied_event = GoogleEvent(
            id="321", status=EventStatus.confirmed,
            start=GoogleDatetime(dateTime=start), end=GoogleDatetime(dateTime=end),
            created=utcnow() - datetime.timedelta(minutes=5), updated=utcnow(),
            extendedProperties=ExtendedProperties.from_sources("123", calendar1_1.id, rule.uuid.__str__())
        )

        with (
            patch("calensync.gwrapper.GoogleCalendarWrapper.get_events") as get_events,
            patch("calensync.gwrapper.GoogleCalendarWrapper.service"),
            patch("calensync.gwrapper.insert_event") as insert_event,
            patch("calensync.gwrapper.update_event") as update_event,
            patch("calensync.gwrapper.delete_event") as delete_event
        ):
            def simulate_get_events(**kwargs):
                extended_properties = kwargs['private_extended_properties']
                if extended_properties[EventExtendedProperty.get_source_id_key()] == event.id:
                    return [copied_event]
                else:
                    raise RuntimeError("Shouldn't happen in this test")

            get_events.side_effect = simulate_get_events
            GoogleCalendarWrapper.push_event_to_rule(event, rule)
            assert get_events.call_count == 1
            assert insert_event.call_count == 0
            assert update_event.call_count == 0
            assert delete_event.call_count == 1

    @staticmethod
    def test_do_not_delete_event_which_doesnt_have_extended_properties_source_id(calendar1_1, calendar1_2):
        rule = SyncRule(source_id=calendar1_1.id, destination_id=calendar1_2.id).save_new()
        start = utcnow() + datetime.timedelta(days=1)
        end = utcnow() + datetime.timedelta(days=1, hours=1)
        event = GoogleEvent(
            id="123", status=EventStatus.cancelled,
            start=GoogleDatetime(dateTime=start), end=GoogleDatetime(dateTime=end),
            created=utcnow() - datetime.timedelta(minutes=5), updated=utcnow()
        )

        copied_event = GoogleEvent(
            id="321", status=EventStatus.confirmed,
            start=GoogleDatetime(dateTime=start), end=GoogleDatetime(dateTime=end),
            created=utcnow() - datetime.timedelta(minutes=5), updated=utcnow()
        )

        with (
            patch("calensync.gwrapper.GoogleCalendarWrapper.get_events") as get_events,
            patch("calensync.gwrapper.GoogleCalendarWrapper.service"),
            patch("calensync.gwrapper.insert_event") as insert_event,
            patch("calensync.gwrapper.update_event") as update_event,
            patch("calensync.gwrapper.delete_event") as delete_event
        ):
            def simulate_get_events(**kwargs):
                extended_properties = kwargs['private_extended_properties']
                if extended_properties[EventExtendedProperty.get_source_id_key()] == event.id:
                    return [copied_event]
                else:
                    raise RuntimeError("Shouldn't happen in this test")

            get_events.side_effect = simulate_get_events
            GoogleCalendarWrapper.push_event_to_rule(event, rule)
            assert get_events.call_count == 1
            assert insert_event.call_count == 0
            assert update_event.call_count == 0
            assert delete_event.call_count == 0

    @staticmethod
    def test_delete_recurrent_instance(calendar1_1, calendar1_2):
        rule = SyncRule(source_id=calendar1_1.id, destination_id=calendar1_2.id).save_new()
        start = utcnow() + datetime.timedelta(days=1)
        end = utcnow() + datetime.timedelta(days=1, hours=1)
        event = GoogleEvent(
            id="123_20241201Z", status=EventStatus.cancelled,
            start=GoogleDatetime(dateTime=start), end=GoogleDatetime(dateTime=end),
            created=utcnow() - datetime.timedelta(minutes=5), updated=utcnow(),
            recurringEventId="123"
        )

        copied_recurrence_source = GoogleEvent(
            id="321", status=EventStatus.cancelled,
            start=GoogleDatetime(dateTime=start), end=GoogleDatetime(dateTime=end),
            created=utcnow() - datetime.timedelta(minutes=5), updated=utcnow(),
            extendedProperties=ExtendedProperties.from_sources("123", calendar1_1.id)
        )

        with (
            patch("calensync.gwrapper.GoogleCalendarWrapper.get_events") as get_events,
            patch("calensync.gwrapper.GoogleCalendarWrapper.service"),
            patch("calensync.gwrapper.insert_event") as insert_event,
            patch("calensync.gwrapper.update_event") as update_event,
            patch("calensync.gwrapper.delete_event") as delete_event
        ):
            def simulate_get_events(**kwargs):
                extended_properties = kwargs['private_extended_properties']
                if extended_properties[EventExtendedProperty.get_source_id_key()] == "123":
                    return [copied_recurrence_source]
                else:
                    raise RuntimeError("Shouldn't happen in this test")

            get_events.side_effect = simulate_get_events
            GoogleCalendarWrapper.push_event_to_rule(event, rule)
            assert get_events.call_count == 1
            assert insert_event.call_count == 0
            assert update_event.call_count == 0
            assert delete_event.call_count == 1
            (service, google_id, deleted_event_id) = delete_event.call_args_list[0].args
            assert deleted_event_id == "321_20241201Z"


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


class TestHandleRefreshError:
    @staticmethod
    def test_normal(calendar1_1):
        assert calendar1_1.paused is None
        exc = google.auth.exceptions.RefreshError(None, {'error': INVALID_GRANT_ERROR})
        handle_refresh_error(calendar1_1, exc)
        assert calendar1_1.paused is not None
