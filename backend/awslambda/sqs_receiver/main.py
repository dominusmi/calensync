from calensync.api.endpoints import received_webhook, patch_calendar
from calensync.database.utils import DatabaseSession
from calensync.dataclass import SQSEvent, QueueEvent, GoogleWebhookEvent, UpdateCalendarStateEvent
from calensync.log import get_logger
from calensync.utils import get_env

logger = get_logger("sqs_receiver")


def handler(event, context):
    """
    Handles all SQS events. For the moment, this only includes
    activation / de-activation of a calendar
    """
    batch_item_failures = []
    sqs_batch_response = {}
    with DatabaseSession(get_env()) as db:
        for record in event["Records"]:
            try:
                sqs_event = SQSEvent.parse_raw(record["body"])
                if sqs_event.kind == QueueEvent.GOOGLE_WEBHOOK:
                    we: GoogleWebhookEvent = GoogleWebhookEvent.parse_obj(sqs_event.data)
                    received_webhook(we.channel_id, we.state, we.resource_id, we.token, db)
                elif sqs_event.kind == QueueEvent.UPDATE_CALENDAR_STATE:
                    e: UpdateCalendarStateEvent = UpdateCalendarStateEvent.parse_obj(sqs_event.data)
                    patch_calendar(e.user_id, e.calendar_id, e.kind, db)
                else:
                    logger.error("Unknown event type")
            except Exception as e:
                logger.error(f"Failed to process record: {e}")
                batch_item_failures.append({"itemIdentifier": record['messageId']})

        sqs_batch_response["batchItemFailures"] = batch_item_failures
        return sqs_batch_response
