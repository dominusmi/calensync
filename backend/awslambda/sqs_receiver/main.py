import datetime
import traceback

import boto3

from calensync.api.service import handle_sqs_event
from calensync.database.utils import DatabaseSession
from calensync.dataclass import SQSEvent
from calensync.libcalendar import PushToQueueException
from calensync.log import get_logger
from calensync.utils import get_env, utcnow, BackoffException

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
                    first_received_timestamp = int(first_received_timestamp) / 1000
                except ValueError:
                    logger.warn(f"Can't parse {first_received_timestamp} as int")
                    first_received_timestamp = utcnow().timestamp()
                sqs_event.first_received = datetime.datetime.utcfromtimestamp(first_received_timestamp).replace(
                    tzinfo=datetime.timezone.utc)
                handle_sqs_event(sqs_event, db, boto3.Session())
            except (BackoffException, PushToQueueException) as e:
                e: Exception
                logger.warn(f"{e.__class__.__name__}")
                batch_item_failures.append({"itemIdentifier": record['messageId']})
            except Exception as e:
                logger.error(f"Failed to process record {e}\n{traceback.format_exc()}")
                batch_item_failures.append({"itemIdentifier": record['messageId']})

        sqs_batch_response["batchItemFailures"] = batch_item_failures
        if len(batch_item_failures) > 0:
            logger.warning(f"Returning SQS Batch response: {sqs_batch_response}")
        return sqs_batch_response
