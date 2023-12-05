import pytest

from calensync.api.common import ApiError
from calensync.api.endpoints import get_calendar
from calensync.tests.fixtures import *


def test_get_calendar_valid(db, user, calendar1):
    c = get_calendar(user, str(calendar1.uuid), db)
    assert c == calendar1


def test_get_calendar_invalid_user(db, calendar1):
    user = User(email="test2@test.com").save_new()
    with pytest.raises(ApiError):
        get_calendar(user, str(calendar1.uuid), db)
