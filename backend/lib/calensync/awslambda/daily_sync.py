import datetime
from typing import Iterable, List

import peewee

from calensync.database.model import User, Calendar, CalendarAccount
from calensync.gwrapper import GoogleCalendarWrapper, service_from_account
from calensync.log import get_logger

logger = get_logger("daily_sync.main")


def load_calendars(accounts: List[CalendarAccount], start_date: datetime.datetime, end_date: datetime.datetime):
    calendars = []
    for account in accounts:
        for calendar in account.calendars:
            # setting this avoid having to re-fetch it from the database to get the credentials
            service = service_from_account(account)
            calendars.append(GoogleCalendarWrapper(calendar, service=service))

    for cal in calendars:
        cal.get_events(start_date, end_date)

    return calendars


def execute_update(calendars: List[GoogleCalendarWrapper], db):
    # spooky double loop. Need to save each calendar events in the others
    for i, cal1 in enumerate(calendars):
        cal1.save_events_in_database()
        for cal2 in calendars[i+1:]:
            cal1.events_handler.add(cal2.events)
            cal2.events_handler.add(cal1.events)

    with db.atomic():
        for cal in calendars:
            cal.insert_events()


def sync_user_calendars_by_date(db):
    query: Iterable[User] = peewee.prefetch(
        User.select(),
        CalendarAccount.select(),
        Calendar.select().where(Calendar.active == True)
    )

    start: datetime.datetime = (datetime.datetime.today() + datetime.timedelta(days=30))
    start_date = datetime.datetime.fromtimestamp(start.timestamp())
    start_date = start_date.replace(hour=0, minute=0, second=0)
    end_date = start_date + datetime.timedelta(hours=24)

    # because the dates are exclusive in the Google API, this will fetch from 00:00:00 of day, to 23:59:59
    start_date = start_date - datetime.timedelta(seconds=1)
    logger.info(f"Start/end date: {start_date.isoformat()} -> {end_date.isoformat()}")

    for user in query:
        logger.info(f"Syncing {user.uuid}")
        calendars = load_calendars(user.accounts, start_date, end_date)
        execute_update(calendars, db)
