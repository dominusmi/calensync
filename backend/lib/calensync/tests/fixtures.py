import datetime
import functools
import json
import random
import uuid
from pathlib import Path

import pytest
from _pytest.fixtures import fixture

from calensync.database.model import User, CalendarAccount, Calendar
from calensync.database.utils import reset_db, DatabaseSession
from calensync.dataclass import GoogleEvent


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



@fixture
def user2(db):
    return User(email="test1@test.com").save_new()


@fixture
def account2_1(db, user):
    return CalendarAccount(user=user, key="test2_1", credentials={}).save_new()


@fixture
def calendar2_1(db, account1):
    return Calendar(account=account1, platform_id="platform2_1", name="name1", active=False).save_new()


@fixture
def account2_2(db, user):
    return CalendarAccount(user=user, key="test2_2", credentials={}).save_new()


@fixture
def calendar2_2(db, account2):
    return Calendar(account=account2, platform_id="platform2_2", name="name2", active=False).save_new()


def uuid4():
    return str(uuid.uuid4())


def random_dates():
    start = datetime.datetime.now() + datetime.timedelta(days=random.randint(0, 15), hours=random.randint(0, 24))
    end = start + datetime.timedelta(hours=random.randint(0, 2), minutes=random.randint(30, 59))
    return start, end


@pytest.fixture
def events_fixture():
    with open(Path(__file__).parent.joinpath("list_events.json")) as f:
        data = json.load(f)

    return data
