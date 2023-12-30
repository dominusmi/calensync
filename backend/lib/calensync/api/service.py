import datetime

import peewee

from calensync.api.common import number_of_days_to_sync_in_advance
from calensync.database.model import Calendar, CalendarAccount
from calensync.gwrapper import GoogleCalendarWrapper
from calensync.log import get_logger
from calensync.utils import is_local

logger = get_logger(__file__)


def activate_calendar(calendar_db: Calendar):
    if calendar_db.active:
        logger.info("Calendar is already active")
        return
    calendar_db.active = True
    calendar_db.save()

    current_google_calendar = GoogleCalendarWrapper(calendar_db)

    # Get all other calendars of user
    calendars_query = current_google_calendar.get_user_calendars(active=True)
    calendars = peewee.prefetch(calendars_query, CalendarAccount)

    active_calendars = [GoogleCalendarWrapper(c) for c in calendars]
    logger.info(f"Found {len(active_calendars)} active calendars")

    start_date = datetime.datetime.now()

    # number of days to sync in the future
    days = number_of_days_to_sync_in_advance()
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
    groups = {}
    for e in events:
        if (cal_id := e.calendar.id) not in groups:
            groups[cal_id] = []
        groups[cal_id].append(e)

    # need to do two passes, one to remove all the non-source, and then remove the source
    def _delete_events(events, is_source):
        if is_source:
            copied_events = list(filter(lambda x: x.source is None, events))
        else:
            copied_events = list(filter(lambda x: x.source is not None, events))

        if not copied_events:
            return
        logger.info(f"Found {len(copied_events)} to delete for {copied_events[0].calendar.uuid}")
        wrapper = GoogleCalendarWrapper(copied_events[0].calendar)
        wrapper.events_handler.delete(copied_events)
        wrapper.delete_events()

    for events in groups.values():
        _delete_events(events, is_source=False)

    for events in groups.values():
        _delete_events(events, is_source=True)

    current_google_calendar.delete_watch()
