import os

from calensync.api.endpoints import received_webhook, patch_calendar
from calensync.dataclass import SQSEvent, QueueEvent, GoogleWebhookEvent, UpdateCalendarStateEvent
from calensync.log import get_logger

logger = get_logger("sqs")


def send_event(session, content: str):
    queue_url = os.environ["SQS_QUEUE_URL"]
    client = session.client("sqs")
    client.send_message(QueueUrl=queue_url, MessageBody=content)


def handle_sqs_event(sqs_event: SQSEvent, db):
    if sqs_event.kind == QueueEvent.GOOGLE_WEBHOOK:
        we: GoogleWebhookEvent = GoogleWebhookEvent.parse_obj(sqs_event.data)
        received_webhook(we.channel_id, we.state, we.resource_id, we.token, db)
    elif sqs_event.kind == QueueEvent.UPDATE_CALENDAR_STATE:
        e: UpdateCalendarStateEvent = UpdateCalendarStateEvent.parse_obj(sqs_event.data)
        patch_calendar(e.user_id, e.calendar_id, e.kind, db)
    else:
        logger.error("Unknown event type")
