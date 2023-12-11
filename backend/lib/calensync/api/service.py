import datetime

import peewee

from calensync.database.model import Calendar, CalendarAccount
from calensync.gwrapper import GoogleCalendarWrapper
from calensync.log import get_logger
from calensync.utils import get_env, is_local

logger = get_logger(__file__)


def activate_calendar(calendar_db: Calendar):
    if calendar_db.active:
        logger.info("Calendar is already active")
        return

    current_google_calendar = GoogleCalendarWrapper(calendar_db)

    # Get all other calendars of user
    calendars_query = current_google_calendar.get_user_calendars(active=True)
    calendars = peewee.prefetch(calendars_query, CalendarAccount)

    active_calendars = [GoogleCalendarWrapper(c) for c in calendars]
    logger.info(f"Found {len(active_calendars)} active calendars")
    if len(active_calendars) > 0:
        start_date = datetime.datetime.utcnow()

        # number of days to sync in the future
        days = 5 if is_local() else 30
        end_date = start_date + datetime.timedelta(days=days)

        current_google_calendar.get_events(start_date, end_date)
        current_google_calendar.save_events_in_database()

        for active_calendar in active_calendars:
            active_calendar.get_events(start_date, end_date)

        # insert all events where needed
        for other_google_calendar in active_calendars:
            current_google_calendar.events_handler.add(other_google_calendar.events)
            other_google_calendar.events_handler.add(current_google_calendar.events)
            other_google_calendar.insert_events()

        current_google_calendar.insert_events()

    # add watch
    logger.info("Creating watch")
    current_google_calendar.create_watch()


def deactivate_calendar(calendar: Calendar):
    current_google_calendar = GoogleCalendarWrapper(calendar)
    current_google_calendar.calendar_db.active = False
    current_google_calendar.calendar_db.save()
    events = list(current_google_calendar.calendar_db.get_synced_events())
    logger.info(f"Found {len(events)} to delete for {calendar.uuid}")
    current_google_calendar.events_handler.delete(events)
    current_google_calendar.delete_events(include_database=True)
    current_google_calendar.delete_watch()
