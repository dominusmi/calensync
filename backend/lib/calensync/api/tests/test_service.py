from calensync.api.service import verify_valid_sync_rule
from calensync.database.model import SyncRule
from calensync.tests.fixtures import *
from calensync.utils import utcnow


class TestVerifySyncRule:
    @staticmethod
    def test_valid_case(user, calendar1, calendar2):
        assert verify_valid_sync_rule(user, str(calendar1.uuid), str(calendar2.uuid)) is None

    @staticmethod
    def test_same_calendar(user, calendar1):
        assert verify_valid_sync_rule(user, str(calendar1.uuid), str(calendar1.uuid)) is not None

    @staticmethod
    def test_user_doesnt_own_calendar(user, calendar1):
        user2 = User(email="test@test.com").save_new()
        account21 = CalendarAccount(user=user2, key="key2", credentials={"key": "value"}).save_new()
        calendar21 = Calendar(account=account21, platform_id="platform_id21", name="name21", active=True,
                              last_processed=utcnow(), last_inserted=utcnow()).save_new()

        assert verify_valid_sync_rule(user, str(calendar1.uuid), str(calendar21.uuid)) is not None

    @staticmethod
    def test_rule_already_exists(user, calendar1, calendar2):
        SyncRule(source=calendar1, destination=calendar2, private=True).save()
        assert verify_valid_sync_rule(user, str(calendar1.uuid), str(calendar2.uuid)) is not None

    @staticmethod
    def test_two_way_should_work(user, calendar1, calendar2):
        SyncRule(source=calendar1, destination=calendar2, private=True).save()
        assert verify_valid_sync_rule(user, str(calendar2.uuid), str(calendar1.uuid)) is None
