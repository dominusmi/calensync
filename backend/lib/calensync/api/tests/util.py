import os

from calensync.api.service import handle_sqs_event
from calensync.dataclass import SQSEvent


def simulate_sqs_receiver(boto_session, queue_url, db):
    sqs = boto_session.client("sqs")

    while True:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            AttributeNames=[
                'SentTimestamp'
            ],
            MaxNumberOfMessages=1,
            MessageAttributeNames=[
                'All'
            ],
            VisibilityTimeout=0,
            WaitTimeSeconds=0
        )
        if "Messages" not in response or len(response["Messages"]) == 0:
            break
        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=response["Messages"][0]['ReceiptHandle']
        )
        for msg in response["Messages"]:
            parsed_sqs_event = SQSEvent.parse_raw(msg['Body'])
            handle_sqs_event(parsed_sqs_event, db, boto_session)
