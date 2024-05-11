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
    if first_received > calendar_db.last_received.replace(tzinfo=datetime.timezone.utc):
        # must run because could be new event
        return SQSEventRun.MUST_PROCESS
    else:
        # must already have been processed in a previous run
        return SQSEventRun.DELETE


def push_update_event_to_queue(event: GoogleEvent, rule_id: int, delete: bool, session: boto3.Session, db):
    event = UpdateGoogleEvent(event=event, rule_id=rule_id, delete=delete)
    sqs_event = SQSEvent(kind=QueueEvent.UPDATED_EVENT, data=event.dict(), first_received=utcnow())
    if is_local() and os.getenv("SQS_QUEUE_URL") is None:
        from calensync.api.service import handle_sqs_event
        handle_sqs_event(sqs_event=sqs_event, db=db, boto_session=session)
    else:
        send_event(session, sqs_event.json())
