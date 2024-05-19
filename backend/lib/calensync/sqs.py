from __future__ import annotations

import datetime
import enum
import os
from typing import List

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


def send_batched_events(session, contents: List[str]):
    queue_url = os.environ["SQS_QUEUE_URL"]
    client = session.client("sqs")
    client.send_message_batch(QueueUrl=queue_url, Entries=[{"Id": str(i), "MessageBody": content} for i, content in enumerate(contents)])


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


def prepare_event_to_push(event: GoogleEvent, rule_id: int, delete: bool) -> SQSEvent:
    event = UpdateGoogleEvent(event=event, rule_id=rule_id, delete=delete)
    sqs_event = SQSEvent(kind=QueueEvent.UPDATED_EVENT, data=event.dict(), first_received=utcnow())
    return sqs_event


def push_update_event_to_queue(prepared_sqs_events: List[SQSEvent], session: boto3.Session, db):
    if is_local() and os.getenv("SQS_QUEUE_URL") is None:
        from calensync.api.service import handle_sqs_event
        for sqs_event in prepared_sqs_events:
            handle_sqs_event(sqs_event=sqs_event, db=db, boto_session=session)
    else:
        batch_size = 10
        batches = [prepared_sqs_events[i:i + batch_size] for i in range(0, len(prepared_sqs_events), batch_size)]
        for batch_idx, batched_events in enumerate(batches):
            batched_events: List[GoogleEvent]
            logger.info(f"Sending batch {batch_idx} of {len(batches)}")
            send_batched_events(session, [b.json() for b in batched_events])
