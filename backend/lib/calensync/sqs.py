import os

from calensync.api.service import run_initial_sync, received_webhook
from calensync.dataclass import SQSEvent, QueueEvent, GoogleWebhookEvent, UpdateCalendarStateEvent, PostSyncRuleEvent
from calensync.log import get_logger

logger = get_logger("sqs")


def send_event(session, content: str):
    queue_url = os.environ["SQS_QUEUE_URL"]
    client = session.client("sqs")
    client.send_message(QueueUrl=queue_url, MessageBody=content)


def handle_sqs_event(sqs_event: SQSEvent, db):
    if sqs_event.kind == QueueEvent.GOOGLE_WEBHOOK:
        we: GoogleWebhookEvent = GoogleWebhookEvent.parse_obj(sqs_event.data)
        logger.info(f"Processing {we.token} calendar")
        received_webhook(we.channel_id, we.state, we.resource_id, we.token, db)
    elif sqs_event.kind == QueueEvent.POST_SYNC_RULE:
        e: PostSyncRuleEvent = PostSyncRuleEvent.parse_obj(sqs_event.data)
        run_initial_sync(e.sync_rule_id)
    else:
        logger.error("Unknown event type")
