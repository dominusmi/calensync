import functools

from _pytest.fixtures import fixture

from calensync.database.model import User, CalendarAccount, Calendar
from calensync.database.utils import reset_db, DatabaseSession


def wrap_reset_db(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        reset_db()
        return func(*args, **kwargs)

    return wrapper


@fixture
def db():
    with DatabaseSession("test") as db:
        reset_db()
        return db


@fixture
def user(db):
    return User(email="test1@test.com").save_new()


@fixture
def account1(db, user):
    return CalendarAccount(user=user, key="test1", credentials={}).save_new()


@fixture
def calendar1(db, account1):
    return Calendar(account=account1, platform_id="platform1", name="name1", active=False).save_new()


@fixture
def account2(db, user):
    return CalendarAccount(user=user, key="test2", credentials={}).save_new()


@fixture
def calendar2(db, account2):
    return Calendar(account=account2, platform_id="platform2", name="name2", active=False).save_new()
