import pytest

from calensync.api.common import ApiError
from calensync.api.endpoints import get_calendar, unsubscribe
from calensync.tests.fixtures import *


def test_get_calendar_valid(db, user, calendar1):
    c = get_calendar(user, str(calendar1.uuid), db)
    assert c == calendar1


def test_get_calendar_invalid_user(db, calendar1):
    user = User(email="test2@test.com").save_new()
    with pytest.raises(ApiError):
        get_calendar(user, str(calendar1.uuid), db)

class TestUnsubscribe:
    @staticmethod
    def test_valid(user: User):
        assert user.marketing
        response = unsubscribe(str(user.uuid))
        assert response.status_code == 200
        user1 = user.refresh()
        assert not user1.marketing

    @staticmethod
    def test_invalid(db):
        response = unsubscribe(uuid4().__str__())
        assert response.status_code == 404
