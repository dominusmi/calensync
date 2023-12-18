from calensync.database.model import OAuthState, User, Session
from calensync.utils import utcnow


def create_session_and_user(email: str, state_db: OAuthState):
    user = User.get_or_none(email=email)
    if user is None:
        user = User(email=email)
        if state_db.tos:
            user.tos = utcnow()
        user = user.save_new()

    elif user.tos is None and state_db.tos is not None:
        user.tos = utcnow()
        user = user.save_new()

    Session(session_id=state_db.session_id, user=user).save()
    state_db.delete_instance()