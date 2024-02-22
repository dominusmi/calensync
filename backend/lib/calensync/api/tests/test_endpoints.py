import os
from typing import List
from unittest.mock import patch

import boto3
import jwt
import moto
import starlette.responses
from moto import mock_aws

from calensync.api import endpoints
from calensync.api.common import ApiError
from calensync.api.endpoints import process_calendars, delete_sync_rule, get_oauth_token, get_frontend_env, reset_user
from calensync.api.service import received_webhook
from calensync.calendar import EventsModificationHandler
from calensync.database.model import Event, SyncRule, OAuthState, OAuthKind, EmailDB
from calensync.database.model import Session
from calensync.dataclass import GoogleDatetime, EventStatus, ExtendedProperties, EventExtendedProperty, GoogleCalendar
from calensync.tests.fixtures import *
from calensync.utils import utcnow

os.environ["FRONTEND"] = "http://test.com"
os.environ["ENV"] = "test"


class TestWebhook:
    @staticmethod
    def test_no_recent_insertion(db, user: User, calendar1_1: Calendar):
        calendar1_1.last_inserted = utcnow() - datetime.timedelta(seconds=187)
        calendar1_1.save()
        with patch("calensync.gwrapper.GoogleCalendarWrapper.solve_update_in_calendar") as mocked:
            received_webhook(str(calendar1_1.channel_id), "", "resource1", str(calendar1_1.token), db)
            mocked.assert_called_once()
            c = calendar1_1.refresh()
            assert (utcnow() - c.last_received.replace(tzinfo=datetime.timezone.utc)).seconds < 5

    @staticmethod
    def test_with_recent_insertion(db, user, calendar1_1):
        new_inserted_dt = utcnow() - datetime.timedelta(seconds=1)
        calendar1_1.last_inserted = new_inserted_dt
        calendar1_1.save()
        with patch("calensync.gwrapper.GoogleCalendarWrapper.solve_update_in_calendar") as mocked:
            with pytest.raises(ApiError):
                received_webhook(str(calendar1_1.channel_id), "", "resource1", str(calendar1_1.token), db)
            mocked.assert_not_called()
            c = calendar1_1.refresh()
            # last received should be updated, but not last inserted no
            assert (utcnow() - c.last_received.replace(tzinfo=datetime.timezone.utc)).seconds < 5
            assert c.last_inserted.replace(tzinfo=datetime.timezone.utc) == new_inserted_dt


class TestProcessCalendar:
    @staticmethod
    def test_process_calendar(db, user, calendar1_1, calendar1_2):
        now = utcnow()
        three_minutes_ago = now - datetime.timedelta(seconds=180)
        calendar1_1.active = True
        calendar1_1.last_inserted = three_minutes_ago
        calendar1_1.last_processed = three_minutes_ago
        calendar1_1.save()

        user2 = User(email="test@test.com").save_new()
        account1_21 = CalendarAccount(user=user2, key="key2", credentials={"key": "value"}).save_new()
        calendar1_21 = Calendar(account=account1_21, platform_id="platform_id21", name="name21", active=True,
                                last_processed=three_minutes_ago, last_inserted=three_minutes_ago).save_new()

        with patch("calensync.gwrapper.GoogleCalendarWrapper.solve_update_in_calendar") as mocked:
            process_calendars()
            assert mocked.call_count == 2


class TestDeleteSyncRule:
    @staticmethod
    def test_normal_case(user, calendar1_1, calendar1_2):
        with (
            patch("calensync.api.endpoints.GoogleCalendarWrapper") as gwrapper,
            patch("calensync.gwrapper.delete_event") as delete_event
        ):
            rule = SyncRule(source=calendar1_1, destination=calendar1_2, private=True).save_new()
            rule2 = SyncRule(source=calendar1_2, destination=calendar1_1, private=True).save_new()

            added_events: List[GoogleEvent] = []

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
    def test_delete_watch_with_other_source(user, account1_1, calendar1_1, calendar1_2):
        with (
            patch("calensync.api.endpoints.GoogleCalendarWrapper") as gwrapper,
            patch("calensync.gwrapper.delete_event") as delete_event
        ):
            rule = SyncRule(source=calendar1_1, destination=calendar1_2, private=True).save_new()

            calendar3 = Calendar(account=account1_1, platform_id="platform3", name="name3", active=False).save_new()
            rule2 = SyncRule(source=calendar1_1, destination=calendar3, private=False).save_new()

            delete_sync_rule(user, str(rule.uuid))

            assert gwrapper.return_value.delete_watch.call_count == 0
            assert SyncRule.get_or_none(id=rule.id) is None
            assert SyncRule.get_or_none(id=rule2.id) is not None

    @staticmethod
    def test_user_doesnt_have_permission(user, calendar1_1, calendar1_2):
        with patch("calensync.gwrapper.GoogleCalendarWrapper") as gwrapper:
            rule = SyncRule(source=calendar1_1, destination=calendar1_2, private=True).save_new()

            new_user = User(email="test2@test.com").save_new()
            with pytest.raises(ApiError):
                delete_sync_rule(new_user, str(rule.uuid))


class TestGetSyncRules:
    @staticmethod
    def test_get_rules(user, calendar1_1, calendar1_2):
        SyncRule(source=calendar1_1, destination=calendar1_2, private=True).save_new()
        SyncRule(source=calendar1_2, destination=calendar1_1, private=True).save_new()

        # add rules of other user
        user2 = User(email="test@test.com").save_new()
        account1_21 = CalendarAccount(user=user2, key="key2", credentials={"key": "value"}).save_new()
        calendar1_21 = Calendar(account=account1_21, platform_id="platform_id21", name="name21", active=True,
                                last_processed=utcnow(), last_inserted=utcnow()).save_new()
        calendar1_22 = Calendar(account=account1_21, platform_id="platform_id22", name="name22", active=True,
                                last_processed=utcnow(), last_inserted=utcnow()).save_new()
        SyncRule(source=calendar1_21, destination=calendar1_22, private=True).save_new()

        # should not be able to fetch them
        rules = endpoints.get_sync_rules(user)
        assert len(rules) == 2
        assert rules[0]["source"] == "name1"
        assert rules[0]["destination"] == "name2"


class TestGetOauthToken:
    @staticmethod
    def test_new_user_through_add_account(db):
        with (
            patch("calensync.api.endpoints.get_client_secret") as get_client_secret,
            patch("calensync.api.endpoints.google_auth_oauthlib") as google_auth_oauthlib,
            patch("calensync.api.endpoints.get_google_email") as get_google_email,
            patch("calensync.api.endpoints.credentials_to_dict") as credentials_to_dict,
            patch("calensync.api.endpoints.get_google_calendars") as get_google_calendars,
            patch("calensync.api.endpoints.google") as google,
        ):
            get_google_calendars.return_value = [GoogleCalendar(kind="123", id="321")]

            # check for bad select getting first email instead of where clause
            useless = User(tos=utcnow()).save_new()
            EmailDB(email="123", user=useless).save_new()

            user_db = User(tos=utcnow()).save_new()
            state_db = OAuthState(state=str(uuid4()), kind=OAuthKind.ADD_GOOGLE_ACCOUNT, user=user_db).save_new()
            email = "test@test.com"
            get_google_email.return_value = email
            credentials_to_dict.return_value = {"email": email}
            get_oauth_token(state=str(state_db.state), code="123", error=None, db=db, session=None)

            assert (email_db := EmailDB.get_or_none(email=email)) is not None
            assert email_db.user == user_db
            assert OAuthState.get_or_none(id=state_db.id) is None
            assert (session := Session.get_or_none(session_id=state_db.session_id)) is not None
            assert session.user == user_db

    @staticmethod
    def test_normal_login(db):
        with (
            patch("calensync.api.endpoints.get_client_secret") as get_client_secret,
            patch("calensync.api.endpoints.google_auth_oauthlib") as google_auth_oauthlib,
            patch("calensync.api.endpoints.get_google_email") as get_google_email,
            patch("calensync.api.endpoints.credentials_to_dict") as credentials_to_dict,
            patch("calensync.api.endpoints.google") as google,
            patch("calensync.api.endpoints.get_google_calendars") as get_google_calendars
        ):
            get_google_calendars.return_value = [GoogleCalendar(kind="123", id="321")]

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
            patch("calensync.api.endpoints.google") as google,
            patch("calensync.api.endpoints.get_google_calendars") as get_google_calendars
        ):
            get_google_calendars.return_value = [GoogleCalendar(kind="123", id="321")]

            email = "test@test.com"
            state_db = OAuthState(state=str(uuid4()), kind=OAuthKind.GOOGLE_SSO).save_new()
            get_google_email.return_value = email
            credentials_to_dict.return_value = {"email": email}
            result = get_oauth_token(state=str(state_db.state), code="123", error=None, db=db, session=None)

            assert EmailDB.get_or_none(email=email) is not None
            assert OAuthState.get_or_none(id=state_db.id) is None

            assert result.location.startswith(f"{get_frontend_env()}/dashboard")
            assert result.cookie is not None

    @staticmethod
    def test_signin_statedb_user_is_none_email_exists(db, user):
        with (
            patch("calensync.api.endpoints.get_client_secret") as get_client_secret,
            patch("calensync.api.endpoints.google_auth_oauthlib") as google_auth_oauthlib,
            patch("calensync.api.endpoints.get_google_email") as get_google_email,
            patch("calensync.api.endpoints.credentials_to_dict") as credentials_to_dict,
            patch("calensync.api.endpoints.google") as google,
            patch("calensync.api.endpoints.get_google_calendars") as get_google_calendars
        ):
            get_google_calendars.return_value = [GoogleCalendar(kind="123", id="321")]

            email = "test@testing.com"
            EmailDB(email=email, user=user).save_new()
            state_db = OAuthState(state=str(uuid4()), kind=OAuthKind.GOOGLE_SSO).save_new()
            get_google_email.return_value = email
            credentials_to_dict.return_value = {"email": email}
            result = get_oauth_token(state=str(state_db.state), code="123", error=None, db=db, session=None)

            assert EmailDB.get_or_none(email=email) is not None
            assert OAuthState.get_or_none(id=state_db.id) is None
            assert (session := Session.get(session_id=state_db.session_id)) is not None
            assert session.user_id == user.id
            assert result.location == f"{get_frontend_env()}/dashboard"
            assert result.cookie is not None
            assert (authorization := result.cookie.get("authorization")) is not None
            assert isinstance(authorization, str)

    @staticmethod
    def test_email_already_associated(db, user, user2):
        """
        Basically a temporary state used with a know email
        """
        with (
            patch("calensync.api.endpoints.get_client_secret") as get_client_secret,
            patch("calensync.api.endpoints.google_auth_oauthlib") as google_auth_oauthlib,
            patch("calensync.api.endpoints.get_google_email") as get_google_email,
            patch("calensync.api.endpoints.credentials_to_dict") as credentials_to_dict,
            patch("calensync.api.endpoints.google") as google,
            patch("calensync.api.endpoints.get_google_calendars") as get_google_calendars
        ):
            get_google_calendars.return_value = [GoogleCalendar(kind="123", id="321")]

            email = "test@testing.com"
            EmailDB(email=email, user=user).save_new()
            EmailDB(email="random", user=user2)
            state_db = OAuthState(state=str(uuid4()), kind=OAuthKind.ADD_GOOGLE_ACCOUNT, user=user2).save_new()
            get_google_email.return_value = email
            credentials_to_dict.return_value = {"email": email}

            result = get_oauth_token(state=str(state_db.state), code="123", error=None, db=db, session=None)
            assert "error_msg" not in result.location
            assert User.get_or_none(id=state_db.user_id) is None

    @staticmethod
    def test_email_already_associated_but_not_state(db, user, user2):
        """
        Can happen if a user has created two accounts (mistakenly) and is now trying
        to add the account of one email, due the other
        """
        with (
            patch("calensync.api.endpoints.get_client_secret") as get_client_secret,
            patch("calensync.api.endpoints.google_auth_oauthlib") as google_auth_oauthlib,
            patch("calensync.api.endpoints.get_google_email") as get_google_email,
            patch("calensync.api.endpoints.credentials_to_dict") as credentials_to_dict,
            patch("calensync.api.endpoints.google") as google,
            patch("calensync.api.endpoints.refresh_calendars") as refresh_calendars
        ):
            email = "test@testing.com"
            EmailDB(email=email, user=user).save_new()
            EmailDB(email="random", user=user2).save_new()
            state_db = OAuthState(state=str(uuid4()), kind=OAuthKind.ADD_GOOGLE_ACCOUNT, user=user2).save_new()
            get_google_email.return_value = email
            credentials_to_dict.return_value = {"email": email}

            result = get_oauth_token(state=str(state_db.state), code="123", error=None, db=db, session=None)
            assert "error_msg" in result.location

    @staticmethod
    def test_add_account_user_did_not_give_permissions(db, user, user2):
        """
        If a new user has a permission issue when adding an account, we need to
        delete the authorization cookie otherwise they may get stuck in a "Session expired" loop
        """
        with (
            patch("calensync.api.endpoints.get_client_secret") as get_client_secret,
            patch("calensync.api.endpoints.google_auth_oauthlib") as google_auth_oauthlib,
            patch("calensync.api.endpoints.get_google_email") as get_google_email,
            patch("calensync.api.endpoints.credentials_to_dict") as credentials_to_dict,
            patch("calensync.api.endpoints.google") as google,
            patch("calensync.api.endpoints.refresh_calendars") as refresh_calendars
        ):
            def _raise_warning():
                raise Warning("error")

            flow = google_auth_oauthlib.flow.Flow.from_client_config.return_value
            flow.fetch_token.side_effect = lambda *args, **kwargs: _raise_warning()

            email = "test@testing.com"
            state_db = OAuthState(state=str(uuid4()), kind=OAuthKind.ADD_GOOGLE_ACCOUNT, user=user).save_new()
            get_google_email.return_value = email
            credentials_to_dict.return_value = {"email": email}

            response = get_oauth_token(state=str(state_db.state), code="123", error=None, db=db, session=None)
            assert isinstance(response, starlette.responses.Response)
            assert "Max-Age=-1" in response.headers["set-cookie"]

            EmailDB(email=email, user=user).save_new()
            response = get_oauth_token(state=str(state_db.state), code="123", error=None, db=db, session=None)
            assert "Max-Age=-1" not in response.headers.get("set-cookie", "")


class TestResetUser:
    @staticmethod
    def create_token_secret_and_signature():
        session = boto3.Session(profile_name="test")
        client = session.client('secretsmanager')
        response = client.create_secret(
            Name='appsmith-jwt-key',
            Description='',
            SecretString='{"key":"my-key"}'
        )
        return jwt.encode({}, "my-key", algorithm="HS256")

    @staticmethod
    def test_valid(user, account1_1, calendar1_1, calendar1_2, user2, calendar1_1_2, calendar1_2_2):
        with (
            patch("calensync.api.endpoints.delete_sync_rule") as delete_sync_rule,
            mock_aws()
        ):
            user.is_admin = True
            user.save()

            SyncRule(source=calendar1_1, destination=calendar1_2, private=True).save_new()
            SyncRule(source=calendar1_1_2, destination=calendar1_2_2, private=True).save_new()
            SyncRule(source=calendar1_2_2, destination=calendar1_1_2, private=True).save_new()

            account2_1 = CalendarAccount(user=user2, key="test3", credentials={}).save_new()
            calendar2_1 = Calendar(account=account2_1, platform_id="platform2_1", name="name1", active=False).save_new()
            calendar2_2 = Calendar(account=account2_1, platform_id="platform2_2", name="name1", active=False).save_new()

            sr1 = SyncRule(source=calendar2_1, destination=calendar2_2, private=True).save_new()
            sr2 = SyncRule(source=calendar2_2, destination=calendar2_1, private=True).save_new()

            signature = TestResetUser.create_token_secret_and_signature()

            reset_user(str(user2.uuid), signature, boto3.Session(profile_name="test"))
            assert delete_sync_rule.call_count == 2
            assert delete_sync_rule.call_args_list[0].args[1] == sr1.uuid
            assert delete_sync_rule.call_args_list[1].args[1] == sr2.uuid

    @staticmethod
    def test_not_admin(user, user2):
        with (
            patch("calensync.api.endpoints.delete_sync_rule") as delete_sync_rule,
            mock_aws()
        ):
            _ = TestResetUser.create_token_secret_and_signature()
            signature = jwt.encode({}, "wrong-key", algorithm="HS256")
            with pytest.raises(ApiError):
                reset_user(str(user2.uuid), signature, boto3.Session(profile_name="test"))