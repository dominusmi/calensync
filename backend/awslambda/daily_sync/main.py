import datetime
from typing import Iterable

import peewee

from calensync.database.model import User, Calendar, CalendarAccount
from calensync.database.utils import DatabaseSession
from calensync.gwrapper import GoogleCalendarWrapper
from calensync.log import get_logger
from calensync.utils import get_env

logger = get_logger("daily_sync")


def handler(event, context):
    """
    Is woken up once a day, gets all currently active calendars, fetches
    the event for the furthest in the future, and synchronizes them
    """
    with DatabaseSession(get_env()) as db:

