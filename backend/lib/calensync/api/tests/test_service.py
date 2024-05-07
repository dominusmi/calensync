import datetime
import os
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

from calensync.api.common import ApiError
from calensync.api.service import verify_valid_sync_rule, received_webhook, handle_sqs_event
from calensync.database.model import SyncRule
from calensync.dataclass import SQSEvent, QueueEvent, UpdateGoogleEvent, EventStatus, PostSyncRuleEvent, \
    DeleteSyncRuleEvent
from calensync.sqs import SQSEventRun, check_if_should_run_time_or_wait
from calensync.tests.fixtures import *
from calensync.utils import utcnow, BackoffException

os.environ["ENV"] = "test"


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
    def test_normal(db, calendar1_1: Calendar, boto_session, queue_url):
        calendar1_1.last_received = utcnow() - datetime.timedelta(minutes=30)
        calendar1_1.last_processed = utcnow() - datetime.timedelta(minutes=25)
        calendar1_1.token = uuid4()
        calendar1_1.save()
        received_webhook(
            calendar1_1.channel_id, "not-sync", calendar1_1.resource_id, calendar1_1.token,
            utcnow(), boto_session, db
        )
        updated_c = Calendar.get_by_id(calendar1_1.id)
        assert updated_c.last_received.replace(tzinfo=datetime.timezone.utc) > utcnow() - datetime.timedelta(seconds=5)
        assert updated_c.last_processed.replace(tzinfo=datetime.timezone.utc) == calendar1_1.last_received.replace(tzinfo=datetime.timezone.utc)

    @staticmethod
    def test_timestamp_format(db, calendar1_1: Calendar, boto_session, queue_url):
        calendar1_1.last_received = utcnow() - datetime.timedelta(minutes=30)
        calendar1_1.last_processed = utcnow() - datetime.timedelta(minutes=25)
        calendar1_1.token = uuid4()
        calendar1_1.save()
        received_webhook(
            calendar1_1.channel_id, "not-sync", calendar1_1.resource_id, calendar1_1.token,
            datetime.datetime.utcfromtimestamp(1545082649185 / 1000).replace(tzinfo=datetime.timezone.utc),
            boto_session, db
        )
        updated_c = Calendar.get_by_id(calendar1_1.id)
        assert updated_c.last_received.replace(tzinfo=datetime.timezone.utc) == calendar1_1.last_received
        assert updated_c.last_processed.replace(tzinfo=datetime.timezone.utc) == calendar1_1.last_processed

    @staticmethod
    def test_should_delete(db, calendar1_1: Calendar, boto_session, queue_url):
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
                utcnow(), boto_session, db
            )
            assert wrapper.call_count == 0
            updated_c = Calendar.get_by_id(calendar1_1.id)
            assert updated_c.last_received.replace(tzinfo=datetime.timezone.utc) == calendar1_1.last_received
            assert updated_c.last_processed.replace(tzinfo=datetime.timezone.utc) == calendar1_1.last_processed

    @staticmethod
    def test_should_retry(db, calendar1_1: Calendar, boto_session, queue_url):
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
                    utcnow(), boto_session, db
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
        assert check_if_should_run_time_or_wait(calendar1_1, utcnow()) == SQSEventRun.MUST_PROCESS

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


class TestReceiveUpdateEvent:
    @staticmethod
    @mock_aws
    def test_normal_update(db, calendar1_1, calendar1_2, calendar1_2_2):
        # receive update, calls the update function on the right number of calendars
        # with the right event id. Finishes cleanly
        rule1 = SyncRule(source=calendar1_1, destination=calendar1_2).save_new()
        rule2 = SyncRule(source=calendar1_1, destination=calendar1_2_2).save_new()
        SyncRule(source=calendar1_2_2, destination=calendar1_1).save_new()
        event = GoogleEvent(id="123", status=EventStatus.confirmed)

        sqs_event = SQSEvent(
            kind=QueueEvent.UPDATED_EVENT,
            data=UpdateGoogleEvent(event=event, rule_ids=[rule1.id, rule2.id], delete=False).dict(),
            delete=False
        )
        with patch("calensync.gwrapper.GoogleCalendarWrapper.push_event_to_rules") as push_event_to_rules:
            handle_sqs_event(sqs_event, db, boto3.Session())
            assert push_event_to_rules.call_count == 1
            arg_event, sync_rules = push_event_to_rules.call_args_list[0].args
            assert arg_event.id == event.id
            assert arg_event.status == event.status

            assert len(sync_rules) == 2
            assert {sr.id for sr in sync_rules} == {rule1.id, rule2.id}

    @staticmethod
    @mock_aws
    def test_backoff(db, calendar1_1, calendar1_2, calendar1_2_2, boto_session, queue_url):
        # receive update, calls the update function, however the google call fails
        # needs to raise BackOff exception
        rule1 = SyncRule(source=calendar1_1, destination=calendar1_2).save_new()
        SyncRule(source=calendar1_2_2, destination=calendar1_1).save_new()
        event = GoogleEvent(id="123", status=EventStatus.confirmed)

        sqs = boto_session.client('sqs')
        sqs_event = SQSEvent(
            kind=QueueEvent.UPDATED_EVENT,
            data=UpdateGoogleEvent(event=event, rule_ids=[rule1.id], delete=False).dict(),
            delete=False
        )

        with (
            patch("calensync.gwrapper.GoogleCalendarWrapper.push_event_to_rules") as push_event_to_rules,
        ):
            def _raise_backoff(*args, **kwargs):
                raise BackoffException(60)

            push_event_to_rules.side_effect = _raise_backoff
            with pytest.raises(BackoffException):
                handle_sqs_event(sqs_event, db, boto_session)

            # assert push_event_to_rules.call_count == 1
            # response = sqs.receive_message(
            #     QueueUrl=queue_url,
            #     AttributeNames=[
            #         'SentTimestamp'
            #     ],
            #     MaxNumberOfMessages=1,
            #     MessageAttributeNames=[
            #         'All'
            #     ],
            #     VisibilityTimeout=0,
            #     WaitTimeSeconds=0
            # )
            # assert len(response["Messages"]) == 1
            # sqs.delete_message(
            #     QueueUrl=queue_url,
            #     ReceiptHandle=response["Messages"][0]['ReceiptHandle']
            # )
            #
            # # do again, but this time with `delete` flag. Check if flag is passed over
            # sqs_event = SQSEvent(
            #     kind=QueueEvent.UPDATED_EVENT,
            #     data=UpdateGoogleEvent(event=event, rule_ids=[rule1.id], delete=True).dict(),
            #     delete=False
            # )
            # handle_sqs_event(sqs_event, db, boto_session)
            #
            # response = sqs.receive_message(
            #     QueueUrl=queue_url,
            #     AttributeNames=[
            #         'SentTimestamp'
            #     ],
            #     MaxNumberOfMessages=1,
            #     MessageAttributeNames=[
            #         'All'
            #     ],
            #     VisibilityTimeout=0,
            #     WaitTimeSeconds=0
            # )
            # parsed_sqs = SQSEvent.parse_raw(response["Messages"][0]['Body'])
            # update_event = UpdateGoogleEvent.parse_obj(parsed_sqs.data)
            # assert update_event.delete

    @staticmethod
    @mock_aws
    def test_delete_event(db, calendar1_1, calendar1_2, calendar1_2_2):
        # receive update but with delete flag set. Should call the delete function on all
        # the sync rules, and finish cleanly
        rule1 = SyncRule(source=calendar1_1, destination=calendar1_2).save_new()
        rule2 = SyncRule(source=calendar1_1, destination=calendar1_2_2).save_new()
        SyncRule(source=calendar1_2_2, destination=calendar1_1).save_new()
        event = GoogleEvent(id="123", status=EventStatus.confirmed)

        sqs_event = SQSEvent(
            kind=QueueEvent.UPDATED_EVENT,
            data=UpdateGoogleEvent(event=event, rule_ids=[rule1.id, rule2.id], delete=True).dict(),
            delete=False
        )
        with patch("calensync.gwrapper.GoogleCalendarWrapper.push_event_to_rules") as push_event_to_rules:
            handle_sqs_event(sqs_event, db, boto3.Session())
            assert push_event_to_rules.call_count == 1
            arg_event, sync_rules = push_event_to_rules.call_args_list[0].args
            assert arg_event.id == event.id
            assert arg_event.status == EventStatus.cancelled

            assert len(sync_rules) == 2
            assert {sr.id for sr in sync_rules} == {rule1.id, rule2.id}


class TestReceiveCreateRuleEvent:
    @staticmethod
    @mock_aws
    def test_normal(db, calendar1_1, calendar1_2, calendar1_2_2):
        rule1 = SyncRule(source=calendar1_1, destination=calendar1_2).save_new()

        sqs_event = SQSEvent(
            kind=QueueEvent.POST_SYNC_RULE,
            data=PostSyncRuleEvent(sync_rule_id=rule1.id).dict(),
        )

        boto_session = boto3.Session(aws_secret_access_key="123", aws_access_key_id="123", region_name='eu-north-1')
        sqs = boto_session.client('sqs')
        response = sqs.create_queue(QueueName='Test')
        queue_url = response["QueueUrl"]
        os.environ["SQS_QUEUE_URL"] = queue_url

        with (
            patch("calensync.api.service.GoogleCalendarWrapper") as GoogleCalendarWrapper,
        ):

            GoogleCalendarWrapper.return_value.get_events.return_value = [
                GoogleEvent(id="1", status=EventStatus.confirmed, summary="Test1"),
                GoogleEvent(id="2", status=EventStatus.confirmed, summary="Test2"),
                GoogleEvent(id="3", status=EventStatus.cancelled, summary="Test3"),
            ]
            handle_sqs_event(sqs_event, db, boto_session)

            assert GoogleCalendarWrapper.return_value.create_watch.call_count == 1

            messages = []
            for i in range(3):
                response = sqs.receive_message(
                    QueueUrl=queue_url,
                    AttributeNames=[
                        'SentTimestamp'
                    ],
                    MaxNumberOfMessages=1,
                    MessageAttributeNames=[
                        'All'
                    ],
                    VisibilityTimeout=0,
                    WaitTimeSeconds=0
                )
                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=response["Messages"][0]['ReceiptHandle']
                )
                assert len(response["Messages"]) == 1
                messages.append(response["Messages"][0])

            ids = {"1", "2", "3"}
            for msg in messages:
                parsed_sqs_event = SQSEvent.parse_raw(msg['Body'])
                assert parsed_sqs_event.kind == QueueEvent.UPDATED_EVENT
                update_event: UpdateGoogleEvent = UpdateGoogleEvent.parse_obj(parsed_sqs_event.data)
                assert not update_event.delete
                assert update_event.event.summary == f"Test{update_event.event.id}"
                ids.remove(update_event.event.id)

            assert len(ids) == 0

    @staticmethod
    @mock_aws
    def test_delete_sync_rule(db, calendar1_1, calendar1_2, calendar1_2_2, boto_session, queue_url):
        rule1 = SyncRule(source=calendar1_1, destination=calendar1_2).save_new()
        rule2 = SyncRule(source=calendar1_1, destination=calendar1_2_2).save_new()
        rule3 = SyncRule(source=calendar1_2, destination=calendar1_1).save_new()

        sqs_event = SQSEvent(
            kind=QueueEvent.DELETE_SYNC_RULE,
            data=DeleteSyncRuleEvent(sync_rule_id=rule1.id).dict(),
        )
        sqs = boto_session.client('sqs')
        with (
            patch("calensync.api.service.GoogleCalendarWrapper") as GoogleCalendarWrapper,
        ):

            GoogleCalendarWrapper.return_value.get_events.return_value = [
                GoogleEvent(id="1", status=EventStatus.confirmed, summary="Test1"),
                GoogleEvent(id="2", status=EventStatus.confirmed, summary="Test2"),
                GoogleEvent(id="3", status=EventStatus.cancelled, summary="Test3"),
            ]
            handle_sqs_event(sqs_event, db, boto_session)

            assert SyncRule.get_or_none(id=rule1.id) is None
            assert GoogleCalendarWrapper.return_value.delete_watch.call_count == 0

            messages = []
            for i in range(3):
                response = sqs.receive_message(
                    QueueUrl=queue_url,
                    AttributeNames=[
                        'SentTimestamp'
                    ],
                    MaxNumberOfMessages=1,
                    MessageAttributeNames=[
                        'All'
                    ],
                    VisibilityTimeout=0,
                    WaitTimeSeconds=0
                )
                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=response["Messages"][0]['ReceiptHandle']
                )
                assert len(response["Messages"]) == 1
                messages.append(response["Messages"][0])

            ids = {"1", "2", "3"}
            for msg in messages:
                parsed_sqs_event = SQSEvent.parse_raw(msg['Body'])
                assert parsed_sqs_event.kind == QueueEvent.UPDATED_EVENT
                update_event: UpdateGoogleEvent = UpdateGoogleEvent.parse_obj(parsed_sqs_event.data)
                assert update_event.delete
                assert update_event.event.summary == f"Test{update_event.event.id}"
                ids.remove(update_event.event.id)

            assert len(ids) == 0
