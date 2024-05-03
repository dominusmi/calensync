import boto3

from calensync.api.service import handle_sqs_event
from calensync.database.model import SyncRule
from calensync.dataclass import GoogleEvent, UpdateGoogleEvent, SQSEvent, QueueEvent
from calensync.sqs import send_event
from calensync.utils import is_local, utcnow


def push_event_to_queue(event: GoogleEvent, rules: list[SyncRule], session: boto3.Session, db):
    event = UpdateGoogleEvent(event=event, rules=[rule.id for rule in rules])
    sqs_event = SQSEvent(kind=QueueEvent.UPDATED_EVENT, data=event.dict(), first_received=utcnow())
    if is_local():
        handle_sqs_event(sqs_event=sqs_event, db=db)
    else:
        send_event(session, sqs_event.json())