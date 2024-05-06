import boto3

from calensync.database.model import SyncRule
from calensync.dataclass import GoogleEvent, UpdateGoogleEvent, SQSEvent, QueueEvent
from calensync.sqs import send_event
from calensync.utils import is_local, utcnow


