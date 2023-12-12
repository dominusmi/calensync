import datetime
import os
import random
import uuid

import peewee
import pytest

from calensync.database.model import OAuthState, OAuthKind, Event
from calensync.tests.fixtures import *


def test_OAuthState():
    with DatabaseSession("test") as db:
        reset_db()
        user: User = User(email="whatver").save_new()
        state = OAuthState(user=user, state="whatver", kind=OAuthKind.GOOGLE_SSO)
        state.save()

        state = OAuthState.get_by_id(state.id)
        assert state.kind == OAuthKind.GOOGLE_SSO


def test_multiple_accounts():
    with DatabaseSession("test") as db:
        reset_db()
        user = User(email="test@test.com").save_new()
        CalendarAccount(user=user, key=uuid.uuid4().__str__(), credentials={"test": 1}).save_new()

        account = CalendarAccount.select().join(User).where(User.uuid == user.uuid).get_or_none()
        assert account is not None


def test_unique_user_account_fails(db, user, account1):
    account2 = CalendarAccount(user=user, key=account1.key, credentials={})
    with pytest.raises(peewee.IntegrityError):
        account2.save()


def test_unique_user_account_succeeds(db, user, account1):
    account2 = CalendarAccount(user=user, key=account1.key, credentials={})
    user2 = User(email="test2@test.com").save_new()
    account2.user = user2
    account2.save()


def test_is_read_only(db, user, account1, calendar1):
    assert not calendar1.is_read_only
    calendar1.platform_id = "whatever@group.v.calendar.google.com"
    calendar1.save()
    calendar = calendar1.refresh()
    assert calendar.is_read_only


def test_get_synced(db, account1, account2, calendar1: Calendar, calendar2: Calendar):
    def uuid4():
        return str(uuid.uuid4())

    def random_dates():
        start = datetime.datetime.now() + datetime.timedelta(days=random.randint(0,15), hours=random.randint(0,24))
        end = start + datetime.timedelta(hours=random.randint(0, 2), minutes=random.randint(30,59))
        return start, end

    calendar3 = Calendar(account=account2, platform_id="platform3", name="name3", active=True).save_new()

    start, end = random_dates()
    source1_1 = Event(calendar=calendar1, event_id=uuid4(), start=start, end=end).save_new()
    copy1to2 = Event(calendar=calendar2, event_id=uuid4(), start=start, end=end, source=source1_1).save_new()
    copy1to3 = Event(calendar=calendar3, event_id=uuid4(), start=start, end=end, source=source1_1).save_new()

    source1_2 = Event(calendar=calendar1, event_id=uuid4(), start=start, end=end, deleted=True).save_new()
    copy1_2to2 = Event(calendar=calendar2, event_id=uuid4(), start=start, end=end, source=source1_2, deleted=True).save_new()
    copy1_2to3 = Event(calendar=calendar3, event_id=uuid4(), start=start, end=end, source=source1_2, deleted=True).save_new()

    start, end = random_dates()
    source2_1 = Event(calendar=calendar2, event_id=uuid4(), start=start, end=end).save_new()
    copy2to1 = Event(calendar=calendar2, event_id=uuid4(), start=start, end=end, source=source2_1).save_new()

    events = list(calendar1.get_synced_events())
    assert len(events) == 2
    assert next(filter(lambda x: x.event_id == copy1to2.event_id, events))
    assert next(filter(lambda x: x.event_id == copy1to3.event_id, events))
