import datetime
from unittest.mock import patch

import pytest

from calensync.api.common import ApiError
from calensync.api.service import verify_valid_sync_rule, received_webhook
from calensync.database.model import SyncRule
from calensync.sqs import SQSEventRun, check_if_should_run_time_or_wait
from calensync.tests.fixtures import *
from calensync.utils import utcnow


class TestVerifySyncRule:
    @staticmethod
    def test_valid_case(user, calendar1_1, calendar1_2):
        assert verify_valid_sync_rule(user, str(calendar1_1.uuid), str(calendar1_2.uuid)) is not None

    @staticmethod
    def test_same_calendar(user, calendar1_1):
        with pytest.raises(ApiError):
            verify_valid_sync_rule(user, str(calendar1_1.uuid), str(calendar1_1.uuid))

    @staticmethod
    def test_user_doesnt_own_calendar(user, calendar1_1):
        user2 = User(email="test@test.com").save_new()
        account1_21 = CalendarAccount(user=user2, key="key2", credentials={"key": "value"}).save_new()
        calendar1_21 = Calendar(account=account1_21, platform_id="platform_id21", name="name21", active=True,
                                last_processed=utcnow(), last_inserted=utcnow()).save_new()

        assert verify_valid_sync_rule(user, str(calendar1_1.uuid), str(calendar1_21.uuid)) is not None

    @staticmethod
    def test_rule_already_exists(user, calendar1_1, calendar1_2):
        SyncRule(source=calendar1_1, destination=calendar1_2, private=True).save()
        with pytest.raises(ApiError):
            verify_valid_sync_rule(user, str(calendar1_1.uuid), str(calendar1_2.uuid))

    @staticmethod
    def test_two_way_should_work(user, calendar1_1, calendar1_2):
        SyncRule(source=calendar1_1, destination=calendar1_2, private=True).save()
        assert verify_valid_sync_rule(user, str(calendar1_2.uuid), str(calendar1_1.uuid)) is not None


class TestReceivedWebhook:
    @staticmethod
    def test_normal(db, calendar1_1: Calendar):
        calendar1_1.last_received = utcnow() - datetime.timedelta(minutes=30)
        calendar1_1.last_processed = utcnow() - datetime.timedelta(minutes=25)
        calendar1_1.token = uuid4()
        calendar1_1.save()
        received_webhook(
            calendar1_1.channel_id, "not-sync", calendar1_1.resource_id, calendar1_1.token,
            utcnow(), db
        )
        updated_c = Calendar.get_by_id(calendar1_1.id)
        assert updated_c.last_received.replace(tzinfo=datetime.timezone.utc) > utcnow() - datetime.timedelta(seconds=5)
        assert updated_c.last_processed.replace(tzinfo=datetime.timezone.utc) > utcnow() - datetime.timedelta(seconds=5)

    @staticmethod
    def test_should_delete(db, calendar1_1: Calendar):
        calendar1_1.last_received = utcnow() - datetime.timedelta(minutes=30)
        calendar1_1.last_processed = utcnow() - datetime.timedelta(minutes=25)
        calendar1_1.token = uuid4()
        calendar1_1.save()
        with (
            patch("calensync.api.service.check_if_should_run_time_or_wait") as checker,
            patch("calensync.api.service.GoogleCalendarWrapper") as wrapper
        ):
            checker.return_value = SQSEventRun.DELETE
            received_webhook(
                calendar1_1.channel_id, "not-sync", calendar1_1.resource_id, calendar1_1.token,
                utcnow(), db
            )
            assert wrapper.call_count == 0
            updated_c = Calendar.get_by_id(calendar1_1.id)
            assert updated_c.last_received.replace(tzinfo=datetime.timezone.utc) == calendar1_1.last_received
            assert updated_c.last_processed.replace(tzinfo=datetime.timezone.utc) == calendar1_1.last_processed

    @staticmethod
    def test_should_retry(db, calendar1_1: Calendar):
        calendar1_1.last_received = utcnow() - datetime.timedelta(minutes=30)
        calendar1_1.last_processed = utcnow() - datetime.timedelta(minutes=25)
        calendar1_1.token = uuid4()
        calendar1_1.save()
        with (
            patch("calensync.api.service.check_if_should_run_time_or_wait") as checker,
            patch("calensync.api.service.GoogleCalendarWrapper") as wrapper
        ):
            checker.return_value = SQSEventRun.RETRY
            with pytest.raises(ApiError):
                received_webhook(
                    calendar1_1.channel_id, "not-sync", calendar1_1.resource_id, calendar1_1.token,
                    utcnow(), db
                )
            assert wrapper.call_count == 0
            updated_c = Calendar.get_by_id(calendar1_1.id)
            assert updated_c.last_received.replace(tzinfo=datetime.timezone.utc) == calendar1_1.last_received
            assert updated_c.last_processed.replace(tzinfo=datetime.timezone.utc) == calendar1_1.last_processed


class TestCheckIfShouldRunTimeOrWait:
    @staticmethod
    def test_normal(calendar1_1):
        calendar1_1.last_received = utcnow() - datetime.timedelta(minutes=30)
        calendar1_1.last_processed = utcnow() - datetime.timedelta(minutes=25)
        calendar1_1.save()
        assert check_if_should_run_time_or_wait(calendar1_1, utcnow()) == SQSEventRun.MUST_PROCESS

    @staticmethod
    def test_event_is_processing(calendar1_1):
        calendar1_1.last_received = utcnow() - datetime.timedelta(minutes=5)
        calendar1_1.last_processed = utcnow() - datetime.timedelta(minutes=6)
        calendar1_1.save()
        assert check_if_should_run_time_or_wait(calendar1_1, utcnow()) == SQSEventRun.RETRY

    @staticmethod
    def test_last_process_failed(calendar1_1):
        calendar1_1.last_received = utcnow() - datetime.timedelta(minutes=14)
        calendar1_1.last_processed = utcnow() - datetime.timedelta(minutes=15)
        calendar1_1.save()
        assert check_if_should_run_time_or_wait(calendar1_1, utcnow()) == SQSEventRun.MUST_PROCESS

    @staticmethod
    def test_already_ran(calendar1_1):
        calendar1_1.last_received = utcnow() - datetime.timedelta(minutes=5)
        calendar1_1.last_processed = utcnow() - datetime.timedelta(minutes=2)
        calendar1_1.save()
        received = utcnow() - datetime.timedelta(minutes=6)
        assert check_if_should_run_time_or_wait(calendar1_1, received) == SQSEventRun.DELETE
