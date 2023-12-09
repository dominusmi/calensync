from calensync.log import get_logger

logger = get_logger("sqs_receiver")


def handler(event, context):
    """
    Handles all SQS events. For the moment, this only includes
    activation / de-activation of a calendar
    """
    batch_item_failures = []
    sqs_batch_response = {}

    logger.info(f"Processing {len(event['Records'])} events")
    for record in event["Records"]:
        try:
            payload = record["body"]
        except Exception as e:
            logger.error(f"Failed to process record: {e}")
            batch_item_failures.append({"itemIdentifier": record['messageId']})

    sqs_batch_response["batchItemFailures"] = batch_item_failures
    return sqs_batch_response
