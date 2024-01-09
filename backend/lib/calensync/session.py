from calensync.database.model import OAuthState, User, Session, EmailDB
from calensync.utils import utcnow, prefetch_get_or_none


def create_session_and_user(state_db: OAuthState, email):
    email_db = prefetch_get_or_none(
        EmailDB.select().where(EmailDB.email == email),
        User.select()
    )

    if email_db is None:
        user_db = User(tos=utcnow()).save_new()
        EmailDB(email=email, user=user_db).save_new()
    else:
        user_db = email_db.user

    Session(session_id=state_db.session_id, user=user_db).save()
    state_db.delete_instance()
