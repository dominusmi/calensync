import os
from typing import List
from unittest.mock import patch, MagicMock

import pytest

from calensync.api import endpoints
from calensync.api.common import ApiError
from calensync.api.endpoints import process_calendars, delete_sync_rule, get_oauth_token, get_frontend_env
from calensync.api.service import received_webhook
from calensync.calendar import EventsModificationHandler
from calensync.database.model import Event, SyncRule, OAuthState, OAuthKind, EmailDB
from calensync.dataclass import GoogleDatetime, EventStatus, ExtendedProperties, EventExtendedProperty
from calensync.tests.fixtures import *
from calensync.utils import utcnow
import os
from unittest.mock import patch

import pytest

from calensync.api import endpoints
from calensync.api.common import ApiError
from calensync.api.endpoints import process_calendars, delete_sync_rule, get_oauth_token, get_frontend_env
from calensync.api.service import received_webhook
from calensync.database.model import Event, SyncRule, OAuthState, OAuthKind, EmailDB
from calensync.tests.fixtures import *
from calensync.utils import utcnow

os.environ["FRONTEND"] = "http://test.com"
os.environ["ENV"] = "test"


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
        new_inserted_dt = utcnow() - datetime.timedelta(seconds=1)
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

            added_events: List[GoogleEvent] = []

            def mock_events_handler_delete(events):
                added_events.extend(events)

            def mock_delete_events(wrapper_instance):
                assert len(wrapper_instance.return_value.events_handler.events_to_delete) == 1
                assert wrapper_instance.return_value.events_handler.events_to_delete[0] == "id-2"

            gwrapper.return_value.get_events.return_value = [
                GoogleEvent(
                    # Should not delete, doesn't have extended properties
                    htmlLink="", start=GoogleDatetime(dateTime=utcnow()), end=GoogleDatetime(dateTime=utcnow()),
                    id="id-1", status=EventStatus.confirmed, summary="test"
                ),
                GoogleEvent(
                    # Should delete, has extended properties source id
                    htmlLink="", start=GoogleDatetime(dateTime=utcnow()), end=GoogleDatetime(dateTime=utcnow()),
                    id="id-2", status=EventStatus.confirmed, extendedProperties=ExtendedProperties(
                        private=EventExtendedProperty.for_source_id("s-1").to_google_dict()
                    ), summary="test2"
                ),
                # todo: add check for calendar id on top of source id
            ]

            gwrapper.return_value.events_handler = EventsModificationHandler()
            # gwrapper.return_value.events_handler.delete.side_effect = lambda: mock_events_handler_delete
            gwrapper.return_value.delete_events.side_effect = lambda: mock_delete_events(gwrapper)
            delete_sync_rule(user, str(rule.uuid))
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


class TestGetSyncRules:
    @staticmethod
    def test_get_rules(user, calendar1, calendar2):
        SyncRule(source=calendar1, destination=calendar2, private=True).save_new()
        SyncRule(source=calendar2, destination=calendar1, private=True).save_new()

        # add rules of other user
        user2 = User(email="test@test.com").save_new()
        account21 = CalendarAccount(user=user2, key="key2", credentials={"key": "value"}).save_new()
        calendar21 = Calendar(account=account21, platform_id="platform_id21", name="name21", active=True,
                              last_processed=utcnow(), last_inserted=utcnow()).save_new()
        calendar22 = Calendar(account=account21, platform_id="platform_id22", name="name21", active=True,
                              last_processed=utcnow(), last_inserted=utcnow()).save_new()
        SyncRule(source=calendar21, destination=calendar22, private=True).save_new()

        # should not be able to fetch them
        rules = endpoints.get_sync_rules(user)
        assert len(rules) == 2
        assert rules[0]["source"] == "platform1"
        assert rules[0]["destination"] == "platform2"


class TestGetOauthToken:
    @staticmethod
    def test_new_user_through_add_account(db):
        with (
            patch("calensync.api.endpoints.get_client_secret") as get_client_secret,
            patch("calensync.api.endpoints.google_auth_oauthlib") as google_auth_oauthlib,
            patch("calensync.api.endpoints.get_google_email") as get_google_email,
            patch("calensync.api.endpoints.credentials_to_dict") as credentials_to_dict,
            patch("calensync.api.endpoints.refresh_calendars") as refresh_calendars
        ):
            user_db = User(tos=utcnow()).save_new()
            state_db = OAuthState(state=str(uuid4()), kind=OAuthKind.ADD_GOOGLE_ACCOUNT, user=user_db).save_new()
            email = "test@test.com"
            get_google_email.return_value = email
            credentials_to_dict.return_value = {"email": email}
            get_oauth_token(state=str(state_db.state), code="123", error=None, db=db, session=None)

            assert (email_db := EmailDB.get_or_none(email=email)) is not None
            assert email_db.user == user_db
            assert OAuthState.get_or_none(id=state_db.id) is None

    @staticmethod
    def test_normal_login(db):
        with (
            patch("calensync.api.endpoints.get_client_secret") as get_client_secret,
            patch("calensync.api.endpoints.google_auth_oauthlib") as google_auth_oauthlib,
            patch("calensync.api.endpoints.get_google_email") as get_google_email,
            patch("calensync.api.endpoints.credentials_to_dict") as credentials_to_dict,
            patch("calensync.api.endpoints.refresh_calendars") as refresh_calendars
        ):
            email = "test@test.com"
            user_db = User(tos=utcnow()).save_new()
            EmailDB(email=email, user=user_db).save_new()
            state_db = OAuthState(state=str(uuid4()), kind=OAuthKind.GOOGLE_SSO).save_new()
            get_google_email.return_value = email
            credentials_to_dict.return_value = {"email": email}
            result = get_oauth_token(state=str(state_db.state), code="123", error=None, db=db, session=None)

            assert OAuthState.get_or_none(id=state_db.id) is None
            assert result.location == f"{get_frontend_env()}/dashboard"
            assert result.cookie is not None
            assert (authorization := result.cookie.get("authorization")) is not None
            assert isinstance(authorization, str)

    @staticmethod
    def test_login_user_doesnt_exist(db):
        with (
            patch("calensync.api.endpoints.get_client_secret") as get_client_secret,
            patch("calensync.api.endpoints.google_auth_oauthlib") as google_auth_oauthlib,
            patch("calensync.api.endpoints.get_google_email") as get_google_email,
            patch("calensync.api.endpoints.credentials_to_dict") as credentials_to_dict,
            patch("calensync.api.endpoints.refresh_calendars") as refresh_calendars
        ):
            email = "test@test.com"
            state_db = OAuthState(state=str(uuid4()), kind=OAuthKind.GOOGLE_SSO).save_new()
            get_google_email.return_value = email
            credentials_to_dict.return_value = {"email": email}
            result = get_oauth_token(state=str(state_db.state), code="123", error=None, db=db, session=None)

            assert EmailDB.get_or_none(email=email)
            assert OAuthState.get_or_none(id=state_db.id) is None

            assert result.location == f"{get_frontend_env()}/dashboard"
            assert result.cookie is not None
            assert (authorization := result.cookie.get("authorization")) is not None
            assert isinstance(authorization, str)
