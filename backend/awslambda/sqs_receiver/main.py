from calensync.api.service import received_webhook
from calensync.database.utils import DatabaseSession
from calensync.dataclass import SQSEvent, QueueEvent, GoogleWebhookEvent, UpdateCalendarStateEvent
from calensync.log import get_logger
from calensync.sqs import handle_sqs_event
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
                handle_sqs_event(sqs_event, db)
            except Exception as e:
                logger.error(f"Failed to process record: {e}")
                batch_item_failures.append({"itemIdentifier": record['messageId']})

        sqs_batch_response["batchItemFailures"] = batch_item_failures
        return sqs_batch_response
