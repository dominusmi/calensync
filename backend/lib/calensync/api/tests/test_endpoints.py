from typing import List
from unittest.mock import patch

import starlette.responses

from calensync.api import endpoints
from calensync.api.common import ApiError, RedirectResponse
from calensync.api.endpoints import delete_sync_rule, get_oauth_token, get_frontend_env, reset_user, \
    handle_add_calendar, resync_calendar, patch_sync_rule, resync_rule
from calensync.api.tests.util import simulate_sqs_receiver
from calensync.database.model import Session
from calensync.database.model import SyncRule, OAuthState, OAuthKind
from calensync.dataclass import (GoogleDatetime, EventStatus, ExtendedProperties, EventExtendedProperty,
                                 GoogleCalendar, PostSyncRuleEvent, PatchSyncRuleBody)
from calensync.libcalendar import EventsModificationHandler
from calensync.tests.fixtures import *
from calensync.utils import utcnow

os.environ["FRONTEND"] = "http://test.com"
os.environ["ENV"] = "test"


def dummy_boto_session():
    return boto3.Session(aws_access_key_id="123", aws_secret_access_key="123")


@mock_aws
class TestDeleteSyncRule:
    @staticmethod
    def test_normal_case(db, user, calendar1_1, calendar1_2, boto_session, queue_url):
        with (
            patch("calensync.api.service.GoogleCalendarWrapper") as gwrapper,
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
            delete_sync_rule(user, str(rule.uuid), boto_session, db)

            simulate_sqs_receiver(boto_session, queue_url, db)

            assert SyncRule.get(id=rule.id).deleted
            assert not SyncRule.get(id=rule2.id).deleted
            assert gwrapper.return_value.delete_watch.call_count == 1

    @staticmethod
    def test_delete_watch_with_other_source(db, user, account1_1, calendar1_1, calendar1_2, boto_session, queue_url):
        with (
            patch("calensync.api.service.GoogleCalendarWrapper") as MockGoogleCalendarWrapper,
            patch("calensync.gwrapper.delete_event") as delete_event
        ):
            rule = SyncRule(source=calendar1_1, destination=calendar1_2, private=True).save_new()

            calendar3 = Calendar(account=account1_1, platform_id="platform3", name="name3", active=False).save_new()
            rule2 = SyncRule(source=calendar1_1, destination=calendar3, private=False).save_new()

            delete_sync_rule(user, str(rule.uuid), boto_session, db)

            simulate_sqs_receiver(boto_session, queue_url, db)
            assert MockGoogleCalendarWrapper.return_value.delete_watch.call_count == 0
            assert SyncRule.get(id=rule.id).deleted
            assert not SyncRule.get(id=rule2.id).deleted

    @staticmethod
    def test_user_doesnt_have_permission(db, user, calendar1_1, calendar1_2, boto_session, queue_url):
        with patch("calensync.gwrapper.GoogleCalendarWrapper") as gwrapper:
            rule = SyncRule(source=calendar1_1, destination=calendar1_2, private=True).save_new()

            new_user = User(email="test2@test.com").save_new()
            with pytest.raises(ApiError):
                delete_sync_rule(new_user, str(rule.uuid), boto_session, db)


class TestGetSyncRules:
    @staticmethod
    def test_get_rules(user, calendar1_1, calendar1_2, boto_session):
        SyncRule(source=calendar1_1, destination=calendar1_2, private=True).save_new()
        SyncRule(source=calendar1_2, destination=calendar1_1, private=True).save_new()

        # add rules of other user
        user2 = User(email="test@test.com").save_new()
        account1_21 = CalendarAccount(
            user=user2, key="key2",
            encrypted_credentials=encrypt_credentials({"key": "value"}, boto_session)).save_new()
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
    def test_new_user_through_add_account(db, boto_session):
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
            get_oauth_token(state=str(state_db.state), code="123", error=None, db=db, boto_session=boto_session)

            assert (email_db := EmailDB.get_or_none(email=email)) is not None
            assert email_db.user == user_db
            assert OAuthState.get_or_none(id=state_db.id) is None
            assert (session := Session.get_or_none(session_id=state_db.session_id)) is not None
            assert session.user == user_db

    @staticmethod
    def test_normal_login(db, boto_session):
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
            result = get_oauth_token(state=str(state_db.state), code="123", error=None, db=db,
                                     boto_session=boto_session)

            assert OAuthState.get_or_none(id=state_db.id) is None
            assert result.location == f"{get_frontend_env()}/dashboard"
            assert result.cookie is not None
            assert (authorization := result.cookie.get("authorization")) is not None
            assert isinstance(authorization, str)

    @staticmethod
    def test_login_user_doesnt_exist(db, boto_session):
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
            result = get_oauth_token(state=str(state_db.state), code="123", error=None, db=db,
                                     boto_session=boto_session)

            assert EmailDB.get_or_none(email=email) is not None
            assert OAuthState.get_or_none(id=state_db.id) is None

            assert result.location.startswith(f"{get_frontend_env()}/dashboard")
            assert result.cookie is not None

    @staticmethod
    def test_signin_statedb_user_is_none_email_exists(db, user, boto_session):
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
            result = get_oauth_token(state=str(state_db.state), code="123", error=None, db=db,
                                     boto_session=boto_session)

            assert EmailDB.get_or_none(email=email) is not None
            assert OAuthState.get_or_none(id=state_db.id) is None
            assert (session := Session.get(session_id=state_db.session_id)) is not None
            assert session.user_id == user.id
            assert result.location == f"{get_frontend_env()}/dashboard"
            assert result.cookie is not None
            assert (authorization := result.cookie.get("authorization")) is not None
            assert isinstance(authorization, str)

    @staticmethod
    def test_email_already_associated(db, user, user2, email1_1, boto_session):
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

            state_db = OAuthState(state=str(uuid4()), kind=OAuthKind.ADD_GOOGLE_ACCOUNT, user=user2).save_new()
            get_google_email.return_value = email1_1.email
            credentials_to_dict.return_value = {"email": email1_1.email}

            result = get_oauth_token(state=str(state_db.state), code="123", error=None, db=db,
                                     boto_session=boto_session)
            assert "error_msg" not in result.location
            assert User.get_or_none(id=user2.id) is None

    @staticmethod
    def test_email_already_associated_but_not_state(db, user, user2, boto_session):
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

            result = get_oauth_token(state=str(state_db.state), code="123", error=None, db=db,
                                     boto_session=boto_session)
            assert User.get_or_none(id=user2.id) is None

    @staticmethod
    def test_add_account_user_did_not_give_permissions(db, user, user2, boto_session):
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

            response = get_oauth_token(state=str(state_db.state), code="123", error=None, db=db,
                                       boto_session=boto_session)
            assert isinstance(response, starlette.responses.Response)
            assert "Max-Age=-1" in response.headers["set-cookie"]

            EmailDB(email=email, user=user).save_new()
            response = get_oauth_token(state=str(state_db.state), code="123", error=None, db=db,
                                       boto_session=boto_session)
            assert "Max-Age=-1" not in response.headers.get("set-cookie", "")


class TestResetUser:
    @staticmethod
    def test_valid(db, user, account1_1, calendar1_1, calendar1_2, user2, calendar1_1_2, calendar1_2_2, boto_session,
                   queue_url):
        with (
            patch("calensync.api.endpoints.delete_sync_rule") as delete_sync_rule,
        ):
            user.is_admin = True
            user.save()

            SyncRule(source=calendar1_1, destination=calendar1_2, private=True).save_new()
            SyncRule(source=calendar1_1_2, destination=calendar1_2_2, private=True).save_new()
            SyncRule(source=calendar1_2_2, destination=calendar1_1_2, private=True).save_new()

            account2_1 = CalendarAccount(
                user=user2, key="test3",
                encrypted_credentials=encrypt_credentials({"key": "value"}, boto_session)).save_new()
            calendar2_1 = Calendar(account=account2_1, platform_id="platform2_1", name="name1", active=False).save_new()
            calendar2_2 = Calendar(account=account2_1, platform_id="platform2_2", name="name1", active=False).save_new()

            sr1 = SyncRule(source=calendar2_1, destination=calendar2_2, private=True).save_new()
            sr2 = SyncRule(source=calendar2_2, destination=calendar2_1, private=True).save_new()

            reset_user(user, str(user2.uuid), boto_session, db)
            assert delete_sync_rule.call_count == 2
            assert delete_sync_rule.call_args_list[0].args[1] == sr1.uuid
            assert delete_sync_rule.call_args_list[1].args[1] == sr2.uuid

    @staticmethod
    def test_not_admin(db, user, user2, boto_session, queue_url):
        with (
            patch("calensync.api.endpoints.delete_sync_rule") as delete_sync_rule,
        ):
            with pytest.raises(ApiError):
                reset_user(user, str(user2.uuid), boto_session, db)


class TestHandleAddCalendar():
    @staticmethod
    def test_state_exists_email_not(db, user, account1_1, email1_1, boto_session):
        with (
            patch("calensync.api.endpoints.refresh_calendars") as refresh_calendars
        ):
            state_db = OAuthState(user=user, state="", kind=OAuthKind.ADD_GOOGLE_ACCOUNT).save_new()
            handle_add_calendar(state_db, "random@email.com", {}, db, boto_session)

        emails = list(EmailDB.select().where(EmailDB.user == user))
        assert len(emails) == 2
        assert "random@email.com" in {email.email for email in emails}

        accounts = list(CalendarAccount.select().where(CalendarAccount.user == user))
        assert len(accounts) == 2
        assert "random@email.com" in {acc.key for acc in accounts}

    @staticmethod
    def test_state_and_email_user_not_the_same(db, user, email1_1, account1_1, boto_session):
        with (
            patch("calensync.api.endpoints.refresh_calendars") as refresh_calendars
        ):
            other_user = User().save_new()
            other_user_email1 = EmailDB(email="test2", user=other_user).save_new()
            other_user_email2 = EmailDB(email="test3", user=other_user).save_new()
            other_user_account1 = CalendarAccount(
                user=other_user, key="test2",
                encrypted_credentials=encrypt_credentials({"key": "value"}, boto_session)).save_new()
            other_user_account2 = CalendarAccount(
                user=other_user, key="test3",
                encrypted_credentials=encrypt_credentials({"key": "value"}, boto_session)).save_new()

            state_db = OAuthState(user=other_user, state="", kind=OAuthKind.ADD_GOOGLE_ACCOUNT).save_new()
            handle_add_calendar(state_db, email1_1.email, {}, db, boto_session)

            emails = list(EmailDB.select().where(EmailDB.user == user))
            assert len(emails) == 3
            assert other_user_email1.email in {email.email for email in emails}
            assert other_user_email2.email in {email.email for email in emails}

            accounts = list(CalendarAccount.select().where(CalendarAccount.user == user))
            assert len(accounts) == 3
            assert other_user_account1.key in {acc.key for acc in accounts}
            assert other_user_account2.key in {acc.key for acc in accounts}

            assert User.get_or_none(id=other_user.id) is None

    @staticmethod
    def test_state_user_and_email_dont_exist(db, user, boto_session):
        with (
            patch("calensync.api.endpoints.refresh_calendars") as refresh_calendars
        ):
            state_db = OAuthState(user=None, state="", kind=OAuthKind.ADD_GOOGLE_ACCOUNT).save_new()
            with pytest.raises(RedirectResponse):
                handle_add_calendar(state_db, "testing@email.com", {}, db, boto_session)


class TestRefreshCalendars:
    @staticmethod
    @patch("calensync.api.endpoints.google.oauth2.credentials.Credentials.from_authorized_user_info", return_value=None)
    def test_normal(db, user, account1_1, calendar1_1, calendar1_1_2, boto_session):
        with patch("calensync.api.endpoints.get_google_calendars") as patch_get_google_calendars:
            patch_get_google_calendars.return_value = [
                GoogleCalendar(
                    kind="calendar#calendarListEntry",
                    id=calendar1_1.platform_id,
                    summary=calendar1_1.name,
                    timeZone='Europe/Paris',
                    selected=True,
                    accessRole="owner",
                    primary=True
                ),
                GoogleCalendar(
                    kind="calendar#calendarListEntry",
                    id=calendar1_1_2.platform_id,
                    summary=calendar1_1_2.name,
                    timeZone='Europe/Paris',
                    selected=True,
                    accessRole="reader",
                    primary=False
                ),
                GoogleCalendar(
                    kind="calendar#calendarListEntry",
                    id="new-calendar",
                    summary="new-calendar-summary",
                    timeZone='Europe/Paris',
                    selected=True,
                    accessRole="owner",
                    primary=False
                )
            ]
            endpoints.refresh_calendars(user, account1_1.uuid, db, boto_session)

            c1 = Calendar.get_by_id(calendar1_1.id)
            c2 = Calendar.get_by_id(calendar1_1_2.id)

            assert not c1.readonly
            assert c2.readonly

            c3 = Calendar.get(platform_id="new-calendar")
            assert not c3.readonly


class TestResyncCalendar:
    def test_normal(self, db, user, calendar1_1, calendar1_2, calendar1_2_2, boto_session):
        calendar1_1.last_resync = utcnow() - datetime.timedelta(days=3)
        calendar1_1.save()
        rule = SyncRule(source=calendar1_1, destination=calendar1_2).save_new()
        rule2 = SyncRule(source=calendar1_1, destination=calendar1_2_2).save_new()

        with patch("calensync.api.service.handle_sqs_event") as handle_sqs_event:
            resync_calendar(user, calendar1_1.uuid, boto_session, db)
            assert handle_sqs_event.call_count == 2
            event = PostSyncRuleEvent.parse_obj(handle_sqs_event.call_args_list[0].args[0].data)
            assert event.sync_rule_id == rule.id

            event = PostSyncRuleEvent.parse_obj(handle_sqs_event.call_args_list[1].args[0].data)
            assert event.sync_rule_id == rule2.id

    def test_not_owner(self, db, user, user2, calendar1_1, calendar1_2, calendar1_2_2, boto_session):
        rule = SyncRule(source=calendar1_1, destination=calendar1_2).save_new()
        rule2 = SyncRule(source=calendar1_1, destination=calendar1_2_2).save_new()

        with pytest.raises(ApiError):
            resync_calendar(user2, calendar1_1.uuid, boto_session, db)

    def test_already_re_synced(self, db, user, calendar1_1, calendar1_2, calendar1_2_2, boto_session):
        rule = SyncRule(source=calendar1_1, destination=calendar1_2).save_new()
        rule2 = SyncRule(source=calendar1_1, destination=calendar1_2_2).save_new()

        calendar1_1.last_resync = utcnow() - datetime.timedelta(minutes=15)
        with pytest.raises(ApiError) as exc:
            resync_calendar(user, calendar1_1.uuid, boto_session, db)

        assert exc.value.code == 429


class TestResyncRule:
    def test_normal(self, db, user, calendar1_1, calendar1_2, calendar1_2_2, boto_session):
        rule = SyncRule(source=calendar1_1, destination=calendar1_2).save_new()
        rule2 = SyncRule(source=calendar1_1, destination=calendar1_2_2).save_new()

        (
            SyncRule
            .update({SyncRule.date_modified: utcnow() - datetime.timedelta(days=3)})
            .where(SyncRule.id == rule.id)
        ).execute()

        with patch("calensync.api.endpoints._launch_resync_rule_event") as patch_launch_resync_rule_event:
            resync_rule(user, rule.uuid.__str__(), boto_session, db)
            assert patch_launch_resync_rule_event.call_count == 1
            assert patch_launch_resync_rule_event.call_args_list[0].args[0] == rule

    def test_not_owner(self, db, user, user2, calendar1_1, calendar1_2, calendar1_2_2, boto_session):
        rule = SyncRule(source=calendar1_1, destination=calendar1_2).save_new()
        rule2 = SyncRule(source=calendar1_1, destination=calendar1_2_2).save_new()

        (
            SyncRule
            .update({SyncRule.date_modified: utcnow() - datetime.timedelta(days=3)})
            .where(SyncRule.id == rule.id)
        ).execute()

        with pytest.raises(ApiError):
            resync_rule(user2, rule.uuid.__str__(), boto_session, db)

    def test_already_re_synced(self, db, user, calendar1_1, calendar1_2, calendar1_2_2, boto_session):
        rule = SyncRule(source=calendar1_1, destination=calendar1_2).save_new()
        rule2 = SyncRule(source=calendar1_1, destination=calendar1_2_2).save_new()

        (
            SyncRule
            .update({SyncRule.date_modified: utcnow() - datetime.timedelta(days=3)})
            .where(SyncRule.id == rule.id)
        ).execute()

        with patch("calensync.api.endpoints._launch_resync_rule_event") as patch_launch_resync_rule_event:
            resync_rule(user, rule.uuid.__str__(), boto_session, db)
            assert patch_launch_resync_rule_event.call_count == 1
            assert patch_launch_resync_rule_event.call_args_list[0].args[0] == rule

            with pytest.raises(ApiError) as exc:
                resync_rule(user, rule.uuid.__str__(), boto_session, db)

        assert exc.value.code == 429


@mock_aws
class TestPatchSyncRule:
    @staticmethod
    def test_normal_case(db, user, calendar1_1, calendar1_2, boto_session):
        with (
            patch("calensync.api.endpoints.handle_update_sync_rule_event") as mock_handle_update,
        ):
            rule = SyncRule(source=calendar1_1, destination=calendar1_2, private=True).save_new()
            rule2 = SyncRule(source=calendar1_2, destination=calendar1_1, private=True).save_new()

            payload = PatchSyncRuleBody(summary="test")
            patch_sync_rule(user, rule.uuid.__str__(), payload, boto_session, db)
            mock_handle_update.assert_called_once()
            m_sync_rule, m_payload, m_boto_session, m_db = mock_handle_update.call_args_list[0].args
            assert m_sync_rule.id == rule.id
            assert m_payload == payload
            assert m_boto_session == boto_session
            assert m_db == db

    @staticmethod
    def test_summary_none(db, user, calendar1_1, calendar1_2, boto_session):
        with (
            patch("calensync.api.endpoints.handle_update_sync_rule_event") as mock_handle_update,
        ):
            rule = SyncRule(source=calendar1_1, destination=calendar1_2, private=True).save_new()

            payload = PatchSyncRuleBody(description="test")
            with pytest.raises(ApiError) as e:
                patch_sync_rule(user, rule.uuid.__str__(), payload, boto_session, db)
            assert e.value.code == 400

    @staticmethod
    def test_user_not_owner(db, user, user2, calendar1_1, calendar1_2, boto_session):
        with (
            patch("calensync.api.endpoints.handle_update_sync_rule_event") as mock_handle_update,
        ):
            rule = SyncRule(source=calendar1_1, destination=calendar1_2, private=True).save_new()

            payload = PatchSyncRuleBody(summary="test")
            with pytest.raises(ApiError) as e:
                patch_sync_rule(user2, rule.uuid.__str__(), payload, boto_session, db)
            assert e.value.code == 404

    @staticmethod
    def test_same_summary_and_description(db, user, calendar1_1, calendar1_2, boto_session):
        with (
            patch("calensync.api.endpoints.handle_update_sync_rule_event") as mock_handle_update,
        ):
            rule = SyncRule(source=calendar1_1, destination=calendar1_2, private=True, summary='summary',
                            description='description').save_new()

            payload = PatchSyncRuleBody(summary="summary", description='description')
            with pytest.raises(ApiError) as e:
                patch_sync_rule(user, rule.uuid.__str__(), payload, boto_session, db)
            assert e.value.code == 400
            assert 'identical' in e.value.detail
