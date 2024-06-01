import datetime
import os
import random
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
        CalendarAccount(user=user, key=uuid.uuid4().__str__(), encrypted_credentials=encrypt_credentials({"test": 1}, None)).save_new()

        account = CalendarAccount.select().join(User).where(User.uuid == user.uuid).get_or_none()
        assert account is not None


def test_unique_user_account_fails(db, user, account1_1):
    account1_2 = CalendarAccount(user=user, key=account1_1.key, encrypted_credentials=encrypt_credentials({}, None))
    with pytest.raises(peewee.IntegrityError):
        account1_2.save()


def test_unique_user_account_succeeds(db, user, account1_1):
    account1_2 = CalendarAccount(user=user, key=account1_1.key, encrypted_credentials=encrypt_credentials({}, None))
    user2 = User(email="test2@test.com").save_new()
    account1_2.user = user2
    account1_2.save()


def test_is_read_only(db, user, account1_1, calendar1_1):
    assert not calendar1_1.is_read_only
    calendar1_1.platform_id = "whatever@group.v.calendar.google.com"
    calendar1_1.readonly = True
    calendar1_1.save()
    calendar = calendar1_1.refresh()
    assert calendar.is_read_only
