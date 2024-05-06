from __future__ import annotations

import datetime
import enum
import os

import boto3

from calensync.database.model import Calendar, SyncRule
from calensync.dataclass import UpdateGoogleEvent, GoogleEvent, QueueEvent, SQSEvent
from calensync.log import get_logger
from calensync.utils import utcnow, is_local, BackoffException

logger = get_logger("sqs")


def send_event(session, content: str):
    queue_url = os.environ["SQS_QUEUE_URL"]
    client = session.client("sqs")
    client.send_message(QueueUrl=queue_url, MessageBody=content)


class SQSEventRun(enum.IntEnum):
    MUST_PROCESS = 0
    DELETE = 1
    RETRY = 2


def check_if_should_run_time_or_wait(calendar_db: Calendar, first_received: datetime.datetime) -> SQSEventRun:
    """
    This function checks the timing of the message and the calendar, and decides whether to return
    an error (in order to retry later), or process the event
    """
    if calendar_db.last_processed > calendar_db.last_received:
        # this implies the previous run finished successfully
        if first_received > calendar_db.last_received.replace(tzinfo=datetime.timezone.utc):
            # must run because could be new event
            return SQSEventRun.MUST_PROCESS
        else:
            # must already have been processed in a previous run
            return SQSEventRun.DELETE
    else:
        # need to check if the previous run failed, or just still running
        delta: datetime.timedelta = utcnow() - calendar_db.last_received.replace(tzinfo=datetime.timezone.utc)
        if delta.seconds > 600:
            # we have to assume the previous run failed, and we run again
            return SQSEventRun.MUST_PROCESS
        else:
            # maybe the previous run is still ongoing, make the event wait for a bit
            return SQSEventRun.RETRY


def push_event_to_queue(event: GoogleEvent, rules: list[SyncRule], session: boto3.Session, db):
    event = UpdateGoogleEvent(event=event, rule_ids=[rule.id for rule in rules])
    sqs_event = SQSEvent(kind=QueueEvent.UPDATED_EVENT, data=event.dict(), first_received=utcnow())
    if is_local():
        from calensync.api.service import handle_sqs_event
        handle_sqs_event(sqs_event=sqs_event, db=db)

    else:
        send_event(session, sqs_event.json())