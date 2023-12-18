import datetime
import uuid

from calensync.database.model import OAuthState, OAuthKind, User, Session
from calensync.session import create_session_and_user
from calensync.utils import utcnow

from fixtures import db


class TestCreateSessionAndUser:

    @staticmethod
    def test_signup(db):
        session_id = str(uuid.uuid4())
        email = "test@testing.com"
        state_db = OAuthState(state="whatever", kind=OAuthKind.GOOGLE_SSO, session_id=session_id, tos=True).save_new()

        create_session_and_user(email, state_db)

        user = User.get(email=email)
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
        User(email=email).save_new()
        state_db = OAuthState(state="whatever", kind=OAuthKind.GOOGLE_SSO, session_id=session_id, tos=True).save_new()

        create_session_and_user(email, state_db)

        user = User.get(email=email)
        assert user.tos is not None
        seconds = (datetime.datetime.utcnow() - user.tos).seconds
        assert seconds < 1

        sessions = list(Session.select().where(Session.user == user))
        assert len(sessions) == 1
        assert str(sessions[0].session_id) == session_id