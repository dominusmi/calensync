import datetime

import peewee

from calensync.database.model import Calendar, CalendarAccount
from calensync.gwrapper import GoogleCalendarWrapper
from calensync.log import get_logger
from calensync.utils import get_env

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
    if len(active_calendars) > 0:
        start_date = datetime.datetime.utcnow()
        end_date = start_date + datetime.timedelta(days=5)
        current_google_calendar.get_events(start_date, end_date)

        # get all events for next 3 months for all calendars
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
    if get_env() != "local":
        current_google_calendar.create_watch()


def deactivate_calendar(calendar: Calendar):
    current_google_calendar = GoogleCalendarWrapper(calendar)
    current_google_calendar.calendar_db.active = False
    current_google_calendar.calendar_db.save()
    events = list(current_google_calendar.calendar_db.get_synced_events())
    current_google_calendar.events_handler.delete(events)
    current_google_calendar.delete_events(include_database=True)
    current_google_calendar.delete_watch()
