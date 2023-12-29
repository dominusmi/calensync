import datetime
import time
from typing import Iterable, List

import peewee

from calensync.database.model import User, Calendar, CalendarAccount
from calensync.gwrapper import GoogleCalendarWrapper, service_from_account, delete_google_watch
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
        for cal2 in calendars[i + 1:]:
            cal1.events_handler.add(cal2.events)
            cal2.events_handler.add(cal1.events)

    with db.atomic():
        for cal in calendars:
            cal.insert_events()


def get_users_query_with_active_calendar():
    sub_query = Calendar.select(User.id).join(CalendarAccount).join(User).where(Calendar.active)

    query: Iterable[User] = peewee.prefetch(
        User.select().join(CalendarAccount).join(Calendar).where(User.id << sub_query),
        CalendarAccount.select(),
        Calendar.select().where(Calendar.active)
    )
    return query


def sync_user_calendars_by_date(db):
    users_query = get_users_query_with_active_calendar()
    start: datetime.datetime = (datetime.datetime.today() + datetime.timedelta(days=30))
    start_date = datetime.datetime.fromtimestamp(start.timestamp())
    start_date = start_date.replace(hour=0, minute=0, second=0)
    end_date = start_date + datetime.timedelta(hours=24)

    # because the dates are exclusive in the Google API, this will fetch from 00:00:00 of day, to 23:59:59
    start_date = start_date - datetime.timedelta(seconds=1)
    logger.info(f"Start/end date: {start_date.isoformat()} -> {end_date.isoformat()}")

    for user in users_query:
        logger.info(f"Syncing {user.uuid}")
        calendars = load_calendars(user.accounts, start_date, end_date)
        execute_update(calendars, db)


def update_watches(db: peewee.Database):
    now = datetime.datetime.now()
    calendars_db: Iterable[Calendar] = peewee.prefetch(
        Calendar.select().where(
            Calendar.expiration.is_null(False),
            Calendar.expiration <= now + datetime.timedelta(hours=36),
            Calendar.active),
        CalendarAccount.select(),
        User.select()
    )

    for calendar_db in calendars_db:
        iteration = 0
        deleted = False
        while iteration < 3:
            try:
                logger.info(f"Updating watch of calendar {calendar_db.uuid}")
                gcalendar = GoogleCalendarWrapper(calendar_db)

                try:
                    if not deleted:
                        gcalendar.delete_watch()
                    deleted = True
                except Exception as e:
                    logger.error(
                        f"Failed to delete watch of {calendar_db.uuid}: {e}")

                gcalendar.create_watch()
                break

            except Exception as e:
                logger.error(f"Error occured while updating calendar {calendar_db.uuid}: {e}")
                time.sleep(1)
            finally:
                iteration += 1
