import boto3

from calensync.awslambda import daily_sync
from calensync.awslambda.daily_sync import send_trial_finishing_email
from calensync.database.utils import DatabaseSession
from calensync.log import get_logger
from calensync.utils import get_env

logger = get_logger("daily_sync")


def handler(event, context):
    """
    Is woken up once a day, gets all currently active calendars, fetches
    the event for the furthest in the future, and synchronizes them
    """
    with DatabaseSession(get_env()) as db:
        boto_session = boto3.Session()
        daily_sync.sync_user_calendars_by_date(db, boto_session)
        daily_sync.update_watches(db)

        # send emails to people who are finishing their trial
        session = boto3.Session()
        try:
            logger.info("Starting send trial emails")
            send_trial_finishing_email(session, db)
        except Exception as e:
            logger.error(f"Something happened to email sending: {e}")
