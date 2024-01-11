import datetime
import uuid

from calensync.database.model import OAuthState, OAuthKind, User, Session, EmailDB
from calensync.session import create_session_and_user
from calensync.tests.fixtures import db


class TestCreateSessionAndUser:

    @staticmethod
    def test_signup(db):
        session_id = str(uuid.uuid4())
        email = "test@testing.com"
        state_db = OAuthState(state="whatever", kind=OAuthKind.GOOGLE_SSO, session_id=session_id, tos=True).save_new()

        create_session_and_user(state_db, email)

        user = User.from_email(email)
        assert user.tos is not None
        seconds = (datetime.datetime.utcnow() - user.tos).seconds
        assert seconds < 1

        sessions = list(Session.select().where(Session.user == user))
        assert len(sessions) == 1
        assert str(sessions[0].session_id) == session_id

    @staticmethod
    def test_existing_account_without_tos(db):
        session_id = str(uuid.uuid4())
        email = "test@testing.com"
        user_db = User().save_new()
        EmailDB(email=email, user=user_db).save_new()
        state_db = OAuthState(state="whatever", kind=OAuthKind.GOOGLE_SSO, session_id=session_id, tos=True).save_new()

        create_session_and_user(state_db, email)

        updated_user = User.from_email(email)
        assert updated_user.tos is not None
        seconds = (datetime.datetime.utcnow() - updated_user.tos).seconds
        assert seconds < 1

        sessions = list(Session.select().where(Session.user == updated_user))
        assert len(sessions) == 1
        assert str(sessions[0].session_id) == session_id
