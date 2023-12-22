from calensync.awslambda import daily_sync
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
        daily_sync.sync_user_calendars_by_date(db)
        daily_sync.update_watches(db)

