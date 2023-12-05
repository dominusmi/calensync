import os
import uuid

import peewee
import pytest

from calensync.database.model import OAuthState, OAuthKind
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
