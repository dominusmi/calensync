from __future__ import annotations

import datetime
import os
from typing import List, Dict, Any, Optional

import google.oauth2.credentials
import peewee
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from calensync.api.common import ApiError, number_of_days_to_sync_in_advance
from calensync.queries.common import get_sync_rules_from_source
from calensync.calendar import EventsModificationHandler
from calensync.database.model import Calendar, CalendarAccount, db, User, SyncRule
from calensync.dataclass import GoogleDatetime, EventExtendedProperty, GoogleCalendar, GoogleEvent, EventStatus
from calensync.log import get_logger
from calensync.utils import get_api_url, utcnow, datetime_to_google_time

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
                 properties: List[EventExtendedProperty] = None, display_name="Calensync", summary="Busy",
                 description=None, **kwargs) -> Dict:
    event = {
        "creator": {"displayName": display_name},
        "summary": summary,
        "description": description,
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
        "end": end.to_google_dict(),
        **kwargs
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
    try:
        items = service.calendarList().list().execute()["items"]
        return [GoogleCalendar.parse_obj(item) for item in items]
    except HttpError as e:
        logger.error(e)
        raise ApiError("Failed to process request due to Google credentials error")


def get_events(service, google_id: str, start_date: datetime.datetime, end_date: datetime.datetime,
               private_extended_properties: Optional[Dict] = None, **kwargs):

    start_date_str = datetime_to_google_time(start_date) if start_date is not None else start_date
    end_date_str = datetime_to_google_time(end_date) if end_date is not None else end_date
    if "updatedMin" in kwargs:
        kwargs["updatedMin"] = datetime_to_google_time(kwargs["updatedMin"])

    if private_extended_properties is None:
        private_extended_properties = {}
    privateExtendedProperty = [f"{k}={v}" for k, v in private_extended_properties.items()]
    # "UCT" is not a spelling mistake, it's the same as UTC
    response = service.events().list(
        calendarId=google_id, timeMin=start_date_str, timeMax=end_date_str, timeZone="UCT",
        privateExtendedProperty=privateExtendedProperty,
        **kwargs
    ).execute()
    logger.info(f"{google_id}: {response.get('items',[])}")
    events = GoogleEvent.parse_event_list_response(response)
    return events


def delete_google_watch(service, resource_id: str, channel_id: str):
    logger.info(f"Deleting watch {resource_id}/{channel_id}")
    body = {
        "id": channel_id,
        "resourceId": resource_id,
    }
    service.channels().stop(body=body).execute()


def source_event_tuple(source_event: GoogleEvent, source_calendar_id: str):
    return (
        source_event, [
            EventExtendedProperty.for_source_id(source_event.id),
            EventExtendedProperty.for_calendar_id(source_calendar_id)
        ]
    )


def create_google_watch(service, calendar_db: Calendar):
    body = {
        "id": calendar_db.channel_id.__str__(),
        "address": (os.environ.get("WATCH_URL") or get_api_url()) + "/webhook",
        "expiration": int(calendar_db.expiration.timestamp() * 1000),
        "type": "webhook",
        "token": calendar_db.token.__str__()
    }
    logger.info(body)
    response = service.events().watch(calendarId=str(calendar_db.platform_id), body=body).execute()
    logger.info(f"Created watch for calendar {calendar_db.uuid}")
    if (resource_id := response.get("resourceId")) is not None:
        logger.info(f"New watch has resource_id: {resource_id}")
        calendar_db.resource_id = resource_id
        calendar_db.save()
        return resource_id


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
                   private_extended_properties: Dict = None, **kwargs):

        kwargs = {} if kwargs is None else kwargs
        # start_date = start_date if start_date is not None else datetime.datetime.utcnow()
        # end_date = end_date if end_date is not None else datetime.datetime.utcnow() + datetime.timedelta(
        #     days=number_of_days_to_sync_in_advance())

        events = get_events(self.service, self.google_id, start_date, end_date, private_extended_properties, **kwargs)
        self.events = events
        return self.events

    def add_watch(self, watch_id: str, token: str, expiration: datetime.datetime, url: str):
        body = {
            "id": watch_id,
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

    def create_watch(self, expiration_minutes=60 * 24 * 14):
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

            create_google_watch(self.service, self.calendar_db)
        return None

    def delete_watch(self):
        if self.calendar_db.is_read_only:
            return

        if self.calendar_db.resource_id is None:
            logger.info(f"Couldn't delete watch for calendar {self.calendar_db.uuid} - resource_id is None")
            return

        channel_id = self.calendar_db.channel_id.__str__()
        resource_id = self.calendar_db.resource_id
        with db.atomic() as tx:
            self.calendar_db.expiration = None
            self.calendar_db.active = False
            self.calendar_db.resource_id = None
            self.calendar_db.save()
            delete_google_watch(self.service, resource_id, channel_id)

    def insert_events(self, private=True):
        if self.calendar_db.is_read_only:
            return

        self.calendar_db.last_inserted = utcnow()
        self.calendar_db.save()

        while self.events_handler.events_to_add:
            (event, properties) = self.events_handler.events_to_add.pop()
            if event.extendedProperties.private.get("source-id") is not None:
                # never copy an event created by us
                continue

            if private:
                response = insert_event(service=self.service, calendar_id=self.google_id,
                                        start=event.start, end=event.end, properties=properties, recurrence=event.recurrence)
            else:
                response = insert_event(service=self.service, calendar_id=self.google_id,
                                        start=event.start, end=event.end, properties=properties,
                                        summary=event.summary, description=event.description, recurrence=event.recurrence)

    def update_events(self):
        """ Only used to update start/end datetime"""
        if self.calendar_db.is_read_only:
            return

        for (source_event, to_update) in self.events_handler.events_to_update:
            start = GoogleDatetime(dateTime=source_event.start.dateTime, timeZone="UCT")
            end = GoogleDatetime(dateTime=source_event.end.dateTime, timeZone="UCT")
            try:
                with db.atomic():
                    logger.info(source_event)
                    update_event(service=self.service, calendar_id=self.google_id, event_id=to_update.id,
                                 start=start, end=end, summary=source_event.summary,
                                 description=source_event.description)
            except Exception as e:
                logger.warn(f"Failed to process event {to_update.id}: {e}")

    def delete_events(self):
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
            event_id = self.events_handler.events_to_delete.pop()
            logger.info(f"Deleting event {event_id} in {self.google_id}")
            delete_event(self.service, self.google_id, event_id)

    def get_updated_events(self) -> List[GoogleEvent]:
        """ Returns the events updated since last_processed """
        updated_min = datetime.datetime.now() - datetime.timedelta(minutes=1)
        start_date = utcnow()
        end_date = utcnow() + datetime.timedelta(days=number_of_days_to_sync_in_advance())
        events = self.get_events(start_date=start_date, end_date=end_date, updatedMin=updated_min, orderBy="updated",
                                 showDeleted=True, maxResults=200)

        logger.info(f"Found updated events: {[(e.id, e.start, e.end) for e in events]}")
        return [event for event in events if event.source_id is None]

    @staticmethod
    def __solve_event_update(event: GoogleEvent, sync_rules: List[SyncRule]) -> int:
        """
        Solves a single event update (by updating all other calendars where this event exists)
        """
        counter_event_changed = 0
        if event.status == EventStatus.tentative:
            # this means an invitation was received, but not yet accepted, so nothing to do
            return 0

        # for some reason the created and updated time are not exactly the same, even when the event is new
        # it looks like google doesn't use a transaction. Bad google. So 1 second threshold for equality
        elif (
                event.created is not None
                and event.updated is not None
                and (event.updated - event.created).seconds < 1
        ):
            # new event, we don't need to check anything more
            logger.info(f"Potential new event")

            for rule in sync_rules:
                c = GoogleCalendarWrapper(rule.destination)
                c.get_events(
                    private_extended_properties=EventExtendedProperty.for_source_id(event.id).to_google_dict()
                )
                if len(c.events) > 0:
                    continue

                c.events_handler.add([source_event_tuple(event, str(sync_rules[0].source.uuid))])
                c.insert_events(private=rule.private)
                counter_event_changed += 1
        else:
            # check status
            if event.status == EventStatus.cancelled:
                # need to delete
                logger.info(f"Found event to delete")
                for rule in sync_rules:
                    c = GoogleCalendarWrapper(rule.destination)
                    fetched_events = c.get_events(
                        private_extended_properties=EventExtendedProperty.for_source_id(event.id).to_google_dict()
                    )
                    c.events_handler.delete(fetched_events)
                    c.delete_events()
                    counter_event_changed += 1

            elif event.status == EventStatus.confirmed:
                # This means it's an updated events. Therefore, all the user-associated calendars
                # must have a version of this event in the database, which we can find through the source_id
                # We then update each of this events with the new time
                logger.info(f"Found confirmed event, updating")
                for rule in sync_rules:
                    c = GoogleCalendarWrapper(rule.destination)
                    c.get_events(
                        private_extended_properties=EventExtendedProperty.for_source_id(event.id).to_google_dict()
                    )
                    if len(c.events) == 0:
                        logger.info(f"In update but need to create event")
                        c.events_handler.add([source_event_tuple(event, str(sync_rules[0].source.uuid))])
                        c.insert_events(private=rule.private)
                        counter_event_changed += 1
                    else:
                        c.events_handler.update([(event, to_update) for to_update in c.events])
                        c.update_events()
                        counter_event_changed += 1
            else:
                logger.error(f"Event status error, doesn't match any case: {event.status}, {event.id}")
        return counter_event_changed

    def solve_update_in_calendar(self) -> int:
        """ Called when we receive a webhook event saying the calendar requires an update """
        sync_rules = list(get_sync_rules_from_source(self.calendar_db))
        counter_event_changed = 0

        logger.info(f"Found {(n_sync := len(sync_rules))} active SyncRules for {self.calendar_db.uuid}")
        if n_sync == 0:
            return 0

        events = self.get_updated_events()

        logger.info(f"Updated events: {[e.id for e in events]}")
        if not events:
            logger.info(f"No updates found for channel {self.calendar_db.channel_id}")
            return 0

        for event in events:
            counter_event_changed += self.__solve_event_update(event, sync_rules)

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
