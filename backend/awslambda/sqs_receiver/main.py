import datetime
import traceback

from calensync.api.service import received_webhook, handle_sqs_event
from calensync.database.utils import DatabaseSession
from calensync.dataclass import SQSEvent, QueueEvent, GoogleWebhookEvent, UpdateCalendarStateEvent
from calensync.log import get_logger
from calensync.utils import get_env, utcnow

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
                first_received_timestamp = record.get("attributes", {}).get("ApproximateFirstReceiveTimestamp", "nan")
                try:
                    first_received_timestamp = int(first_received_timestamp / 1000)
                except ValueError:
                    logger.warn(f"Can't parse {first_received_timestamp} as int")
                    first_received_timestamp = utcnow().timestamp()
                sqs_event.first_received = datetime.datetime.utcfromtimestamp(first_received_timestamp)
                handle_sqs_event(sqs_event, db)
            except Exception as e:
                logger.warn(f"Failed to process record: {e}\n{traceback.format_exc()}")
                batch_item_failures.append({"itemIdentifier": record['messageId']})

        sqs_batch_response["batchItemFailures"] = batch_item_failures
        return sqs_batch_response
