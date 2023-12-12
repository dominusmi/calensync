from __future__ import annotations

import datetime
import os
from typing import List, Dict, Any, Optional

import google.oauth2.credentials
import peewee
from googleapiclient.discovery import build

from calensync.calendar import EventsModificationHandler
from calensync.database.model import Calendar, CalendarAccount, db, User, Event
from calensync.dataclass import GoogleDatetime, EventExtendedProperty, GoogleCalendar, GoogleEvent, EventStatus
from calensync.log import get_logger
from calensync.utils import get_api_url, utcnow

logger = get_logger(__file__)


def service_from_account(account: CalendarAccount):
    creds = google.oauth2.credentials.Credentials.from_authorized_user_info(
        account.credentials
    )
    return build('calendar', 'v3', credentials=creds)


def delete_event(service, calendar_id: str, event_id: str):
    try:
        # todo: handle correctly
        service.events().delete(calendarId=calendar_id, eventId=event_id, sendNotifications=None,
                                sendUpdates=None).execute()
    except Exception as e:
        logger.warn(f"Failed to delete event: {e}")
        pass


def insert_event(service, calendar_id: str, start: GoogleDatetime, end: GoogleDatetime,
                 properties: List[EventExtendedProperty] = None, display_name="Calensync", summary="Blocker",
                 **kwargs) -> Dict:
    event = {
        "creator": {"displayName": display_name},
        "summary": summary,
        "description": "Blocker event created by Calensync.",
        "start": start.to_google_dict(),
        "end": end.to_google_dict(),
        "extendedProperties": {"private": EventExtendedProperty.list_to_dict(properties)},
        "reminders": {"useDefault": False},
        **kwargs
    }
    logger.info(f"Sending {event}")
    return service.events().insert(calendarId=calendar_id, body=event).execute()


def update_event(service, calendar_id: str, event_id: str, start: GoogleDatetime, end: GoogleDatetime, **kwargs):
    body = {
        "start": start.to_google_dict(),
        "end": end.to_google_dict()
    }
    logger.info(f"Updating event {event_id}: {body}")
    service.events().patch(calendarId=calendar_id, eventId=event_id, body=body).execute()


def get_google_email(credentials):
    oauth2_client = build(
        'oauth2', 'v2',
        credentials=credentials)

    return oauth2_client.userinfo().get().execute()["email"]


def get_google_calendars(credentials) -> List[GoogleCalendar]:
    service = build('calendar', 'v3', credentials=credentials)
    items = service.calendarList().list().execute()["items"]
    return [GoogleCalendar.parse_obj(item) for item in items]


def datetime_to_google_time(dt: datetime.datetime) -> str:
    return dt.isoformat() + "Z"


def find_calendar_from_event(calendars: List[GoogleCalendarWrapper], event: Event) -> GoogleCalendarWrapper:
    """ Given a list of calendars and a database event, return the calendar to which this event belongs """
    return next(filter(lambda x: x.google_id == event.calendar.platform_id, calendars), None)


def get_events(service, google_id: str, start_date: datetime.datetime, end_date: datetime.datetime, query_kwargs: Dict):
    start_date_str = datetime_to_google_time(start_date)
    end_date_str = datetime_to_google_time(end_date)

    # "UCT" is not a spelling mistake, it's the same as UTC
    response = service.events().list(
        calendarId=google_id, timeMin=start_date_str, timeMax=end_date_str, timeZone="UCT",
        **query_kwargs
    ).execute()

    events = GoogleEvent.parse_event_list_response(response)

    # handle recurrent events
    recurrent_events = []
    indexes = [i for i in range(len(events)) if events[i].recurrence is not None]
    for index in sorted(indexes, reverse=True):
        recurrent_events.append(events.pop(index))

    for event in recurrent_events:
        recurrent_response = service.events().instances(
            calendarId=google_id, eventId=event.id,
            timeMin=start_date_str, timeMax=end_date_str, timeZone="UCT"
        ).execute()
        events.extend(GoogleEvent.parse_event_list_response(recurrent_response))

    return events


class GoogleCalendarWrapper:
    user_db: User
    calendar_db: Calendar
    credentials: Dict
    """ google service """
    service: Any
    """ cached automatically when get_events is called """
    events: Optional[List[GoogleEvent]]

    """ Keeps track of event changes to apply """
    events_handler: EventsModificationHandler

    """ Cache of service. Avoids creating a service during __init__"""
    _service: Any

    def __init__(self, calendar_db: Calendar, service=None):
        self._service = None
        self.calendar_db = calendar_db
        self.user_db = calendar_db.account.user

        if service:
            self._service = service

        self.events_handler = EventsModificationHandler()

    @property
    def service(self):
        """ Lazy service loader with cache """
        if self._service is None:
            self._service = service_from_account(self.calendar_db.account)
        return self._service

    @property
    def db_id(self):
        return str(self.calendar_db.uuid)

    @property
    def google_id(self):
        return self.calendar_db.platform_id

    def get_events(self, start_date: datetime.datetime = None, end_date: datetime.datetime = None,
                   query_kwargs: Dict = None):
        query_kwargs = {} if query_kwargs is None else query_kwargs
        start_date = start_date if start_date is not None else datetime.datetime.utcnow()
        end_date = end_date if end_date is not None else datetime.datetime.utcnow()
        events = get_events(self.service, self.google_id, start_date, end_date, query_kwargs)
        self.events = events
        return self.events

    def add_watch(self, id: str, token: str, expiration: datetime.datetime, url: str):
        body = {
            "id": id,
            "address": url,
            "expiration": int(expiration.timestamp() * 1000),
            "type": "webhook",
            "token": token
        }
        return self.service.events().watch(calendarId=self.google_id, body=body).execute()

    def get_user_calendars(self, active=None):
        query = (
            Calendar.select().join(CalendarAccount).join(User)
            .where(User.id == self.user_db.id, Calendar.id != self.calendar_db.id)
        )
        if active is not None:
            query = query.where(Calendar.active == active)

        return query

    def create_watch(self, expiration_minutes=60 * 24 * 7):
        env = os.environ["ENV"]
        if env == "local" or env == "test":
            expiration_minutes = 60

        with db.atomic() as tx:
            new_expiration = datetime.datetime.now() + datetime.timedelta(minutes=expiration_minutes)
            self.calendar_db.expiration = new_expiration
            self.calendar_db.active = True
            self.calendar_db.save()
            if self.calendar_db.is_read_only:
                return

            body = {
                "id": self.calendar_db.channel_id.__str__(),
                "address": get_api_url() + "/webhook",
                "expiration": int(self.calendar_db.expiration.timestamp() * 1000),
                "type": "webhook",
                "token": self.calendar_db.token.__str__()
            }
            if env != "local" and env != "test":
                self.service.events().watch(calendarId=str(self.google_id), body=body).execute()

    def delete_watch(self):
        if self.calendar_db.is_read_only:
            return

        if self.calendar_db.resource_id is None:
            logger.info(f"Couldn't delete watch for calendar {self.calendar_db.uuid} - resource_id is None")
            return

        channel_id = self.calendar_db.channel_id.__str__()
        resource_id = self.calendar_db.resource_id
        with db.atomic() as tx:
            self.calendar_db.expiration = datetime.datetime.utcnow()
            self.calendar_db.active = False
            self.calendar_db.resource_id = None
            self.calendar_db.save()
            body = {
                "id": channel_id,
                "resourceId": resource_id,
            }
            self.service.channels().stop(body=body).execute()

    def insert_events(self):
        if self.calendar_db.is_read_only:
            return

        self.calendar_db.last_inserted = utcnow()
        self.calendar_db.save()

        existing_event_ids = [
            e.source.event_id for e in
            Event.select(Event.source).where(Event.source.is_null(False), Event.calendar == self.calendar_db)
        ]

        while self.events_handler.events_to_add:
            event = self.events_handler.events_to_add.pop()
            if event.id in existing_event_ids:
                logger.info(f"Skipping event {event.id}")
                continue

            properties = [
                EventExtendedProperty.for_source_id(event.id)
            ]

            # todo: should be inside a transaction
            response = insert_event(service=self.service, calendar_id=self.google_id,
                                    start=event.start, end=event.end, properties=properties)

            Event(calendar=self.calendar_db, event_id=response["id"],
                  source=Event.select(Event.id).where(Event.event_id == event.id),
                  start=event.start.to_datetime(), end=event.end.to_datetime()).save()

    def update_events(self):
        """ Only used to update start/end datetime"""
        if self.calendar_db.is_read_only:
            return

        for (event, source_event) in self.events_handler.events_to_update:
            event.start = source_event.start.dateTime
            event.end = source_event.end.dateTime
            start = GoogleDatetime(dateTime=event.start, timeZone="UCT")
            end = GoogleDatetime(dateTime=event.end, timeZone="UCT")
            with db.atomic():
                event.save()
                update_event(service=self.service, calendar_id=self.google_id, event_id=event.event_id, start=start,
                             end=end)

    def delete_events(self, include_database: bool = False):
        """
        Calls google API to delete events stored in self.events_handler.
         :param include_database:
            the event can be either completely deleted, or marked in the
            database as deleted. The reason to allow both is that when a calendar is
            deactivated, we can safely delete all the events. However, if the
            event is "deleted" (as in the original event is deleted), we want to
            keep track of it to avoid trying to delete it multiple times in a row.
        """
        if self.calendar_db.is_read_only:
            return

        while self.events_handler.events_to_delete:
            event = self.events_handler.events_to_delete.pop()
            if event.deleted:
                continue
            if event.source is not None:
                # we only delete non-source events from actual calendar
                logger.info(f"Deleting event {event.id} in {self.google_id} from source {event.source.id}")
                delete_event(self.service, self.google_id, event.event_id)

            if include_database:
                event.delete_instance()
            else:
                # We keep a log of the deleted events to avoid doing extra api calls each time
                event.deleted = True
                event.save()

    def get_updated_events(self) -> List[GoogleEvent]:
        """ Returns the events updated since last_processed """
        updated_min = (self.calendar_db.last_processed - datetime.timedelta(minutes=1)).isoformat() + "Z"

        response = (
            self.service.events()
            .list(calendarId=self.google_id, orderBy="updated",
                  maxResults=200, showDeleted=True, updatedMin=updated_min)
            .execute()
        )
        events = GoogleEvent.parse_event_list_response(response)
        return [event for event in events if event.source_id is None]

    def save_events_in_database(self):
        """
        Used to save events that are currently in self.events in the database
        """
        rows = []
        for event in self.events:
            if event.status not in [EventStatus.tentative]:
                rows.append(
                    Event(calendar=self.calendar_db, event_id=event.id, start=event.start.to_datetime(),
                          deleted=(event.status == EventStatus.cancelled),
                          end=event.end.to_datetime()).get_update_fields()
                )

        Event.insert_many(rows).on_conflict(
            conflict_target=[Event.event_id],
            preserve=(Event.date_created,)

        ).execute()

    @staticmethod
    def __solve_event_update(event: GoogleEvent, other_calendars: List[GoogleCalendarWrapper]) -> int:
        """
        Solves a single event update (by updating all other calendars where this event exists)
        """
        counter_event_changed = 0
        if event.status == EventStatus.tentative:
            # this means an invitation was received, but not yet accepted, so nothing to do
            return 0

        # for some reason the created and updated time are not exactly the same, even when the event is new
        # it looks like google doesn't use a transaction. Bad google. So 1 second threshold for equality
        elif (event.updated - event.created).seconds < 1:
            # new event, we don't need to check anything more
            logger.info(f"Add new event: {event}")

            for c in other_calendars:
                c.events_handler.add([event])
                c.insert_events()
                counter_event_changed += 1
        else:
            # check status
            if event.status == EventStatus.cancelled:
                # need to delete
                query, Source = Event.get_self_reference_query()
                fetched_events = list(query.where(Source.event_id == event.id))
                for fetched_event in fetched_events:
                    cal = find_calendar_from_event(other_calendars, fetched_event)
                    if cal is None:
                        continue
                    cal.events_handler.delete([fetched_event])
                    cal.delete_events()
                    return 1

            elif event.status == EventStatus.confirmed:
                # This means it's an updated events. Therefore, all the user-associated calendars
                # must have a version of this event in the database, which we can find through the source_id
                # We then update each of this events with the new time
                query, Source = Event.get_self_reference_query()
                query.where(Source.id == event.id)

                fetched_events: List[Event] = peewee.prefetch(query, Calendar.select())
                if fetched_events:
                    # If updated, then we should find the events in the database
                    for fetched_event in fetched_events:
                        same_start = fetched_event.start == event.start.dateTime
                        same_end = fetched_event.end == event.end.dateTime
                        if same_start and same_end:
                            # time was not modified, ignore
                            continue

                        fetched_event_cal = find_calendar_from_event(other_calendars, fetched_event)
                        if fetched_event_cal is None:
                            continue

                        # Update event
                        fetched_event_cal.events_handler.update([(fetched_event, event)])
                        fetched_event_cal.update_events()
                        counter_event_changed += 1

                else:
                    # new event, simply insert
                    for c in other_calendars:
                        c.events_handler.add([event])
                        c.insert_events()
                        counter_event_changed += 1

            else:
                logger.error(f"Event status error, doesn't match any case: {event.status}, {event.id}")
        return counter_event_changed

    def solve_update_in_calendar(self) -> int:
        """ Called when we receive a webhook event saying the calendar requires an update """
        other_calendars = [GoogleCalendarWrapper(c) for c in self.get_user_calendars(active=True)]
        counter_event_changed = 0

        if not other_calendars:
            # No need to do anything
            logger.info("no calendars for user, exiting without changes")
            return counter_event_changed

        logger.info(f"Found {len(other_calendars)} other active calendars for user")

        events = self.get_updated_events()
        logger.info(f"Updated events: {[e.dict() for e in events]}")
        if not events:
            logger.error(f"Something went wrong: no updates found for channel {self.calendar_db.channel_id}")
            return 0

        # auto-update existing
        self.events = events
        self.save_events_in_database()

        for event in events:
            counter_event_changed += self.__solve_event_update(event, other_calendars)

        logger.info(f"Event changed: {counter_event_changed}")
        return counter_event_changed

    @classmethod
    def from_channel_id(cls, channel_id: str):
        calendars = peewee.prefetch(
            Calendar.select().join(CalendarAccount).join(User).where(Calendar.channel_id == channel_id),
            CalendarAccount.select(), User.select())
        assert len(calendars) == 1
        calendar = calendars[0]
        return cls(calendar)
