from __future__ import annotations

import datetime
import os
import traceback
from copy import copy
from typing import List, Dict, Any, Optional

import google.oauth2.credentials
import google_auth_httplib2
import googleapiclient
import googleapiclient.http
import httplib2
import peewee
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from calensync.api.common import ApiError, number_of_days_to_sync_in_advance
from calensync.database.model import Calendar, CalendarAccount, db, User, SyncRule
from calensync.dataclass import GoogleDatetime, EventExtendedProperty, GoogleCalendar, GoogleEvent, EventStatus, \
    ExtendedProperties
from calensync.libcalendar import EventsModificationHandler, PushToQueueException
from calensync.log import get_logger
from calensync.queries.common import get_sync_rules_from_source
from calensync.sqs import push_update_event_to_queue, prepare_event_to_push
from calensync.utils import get_api_url, utcnow, datetime_to_google_time, format_calendar_text, \
    google_error_handling_with_backoff

logger = get_logger(__file__)


def service_from_account(account: CalendarAccount):
    creds = google.oauth2.credentials.Credentials.from_authorized_user_info(
        account.credentials
    )

    def build_request(http, *args, **kwargs):
        new_http = google_auth_httplib2.AuthorizedHttp(creds, http=httplib2.Http())
        return googleapiclient.http.HttpRequest(new_http, *args, **kwargs)

    authorized_http = google_auth_httplib2.AuthorizedHttp(creds, http=httplib2.Http())
    return build('calendar', 'v3', requestBuilder=build_request, http=authorized_http)


def delete_event(service, calendar_id: str, event_id: str):
    # todo: handle correctly
    service.events().delete(calendarId=calendar_id, eventId=event_id, sendNotifications=None,
                            sendUpdates=None).execute()


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
    logger.debug(f"Updating event {event_id}: {body}")
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

    if 'maxResults' not in kwargs:
        kwargs['maxResults'] = 2500

    if private_extended_properties is None:
        private_extended_properties = {}

    privateExtendedProperty = [f"{k}={v}" for k, v in private_extended_properties.items()]
    # "UCT" is not a spelling mistake, it's the same as UTC

    events_service = service.events()
    request = events_service.list(
        calendarId=google_id, timeMin=start_date_str, timeMax=end_date_str, timeZone="UCT",
        privateExtendedProperty=privateExtendedProperty,
        **kwargs
    )
    events = []
    while request is not None:
        response = request.execute()
        logger.debug(f"{google_id}: {response.get('items', [])}")
        events.extend(GoogleEvent.parse_event_list_response(response))
        request = events_service.list_next(request, response)
        logger.info(f"Fetched {len(events)}")

    return events


def delete_google_watch(service, resource_id: str, channel_id: str):
    logger.info(f"Deleting watch {resource_id}/{channel_id}")
    body = {
        "id": channel_id,
        "resourceId": resource_id,
    }
    try:
        service.channels().stop(body=body).execute()
    except HttpError as e:
        if e.status_code == 404:
            logger.warning(f"Did not find channel {channel_id} for {resource_id}, skipping")
        else:
            raise e


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


def make_summary_and_description(source_event: GoogleEvent, rule: SyncRule):
    summary = None
    description = None
    if source_event.summary is not None and rule.summary is not None:
        summary = format_calendar_text(source_event.summary, rule.summary)

    if source_event.description is not None:
        if rule.description is None or len(rule.description) == 0:
            description = None
        else:
            description = format_calendar_text(source_event.description, rule.description)

    if summary is None:
        summary = 'Blocker'

    return summary, description


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

    def __init__(self, calendar_db: Calendar, service=None, db=None, session=None):
        self._service = None
        self.calendar_db = calendar_db
        self.user_db = calendar_db.account.user
        self.db = db
        self.session = session

        if service:
            self._service = service

        self.events_handler = EventsModificationHandler()
        self.events = []

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
        try:
            events = get_events(self.service, self.google_id, start_date, end_date, private_extended_properties,
                                **kwargs)

            self.events = events
        except googleapiclient.errors.HttpError as e:
            if e.status_code == 403 and e.reason == "You need to have writer access to this calendar.":
                self.calendar_db.paused = utcnow()
                self.calendar_db.paused_reason = e.reason
                self.calendar_db.save()
            self.events = []
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

    def insert_events(self):
        if self.calendar_db.is_read_only:
            return
        elif self.calendar_db.paused is not None:
            logger.info(f"Skipping insert in calendar {self.calendar_db.uuid} due to paused")
            return

        self.calendar_db.last_inserted = utcnow()
        self.calendar_db.save()

        while self.events_handler.events_to_add:
            # order of popping is important for recurrence race condition
            (event, properties, rule) = self.events_handler.events_to_add.pop(0)
            try:
                if event.extendedProperties.private.get("source-id") is not None:
                    # never copy an event created by us
                    continue

                summary, description = make_summary_and_description(event, rule)

                kwargs = {}
                if event.id:
                    logger.info(f"Keeping id for event {event.id}")
                    kwargs['id'] = event.id
                if event.originalStartTime is not None:
                    kwargs['originalStartTime'] = event.originalStartTime.to_google_dict()
                if event.recurringEventId is not None:
                    kwargs['recurringEventId'] = event.recurringEventId

                def _inner():
                    insert_event(
                        service=self.service, calendar_id=self.google_id,
                        start=event.start, end=event.end, properties=properties, recurrence=event.recurrence,
                        summary=summary, description=description, **kwargs
                    )

                return google_error_handling_with_backoff(_inner, self.calendar_db)

            except Exception as e:
                logger.error(f"Failed to insert {event.id} with rule {rule.id}: {e}\n{traceback.format_exc()}")

    def update_events(self):
        """ Only used to update start/end datetime"""
        if self.calendar_db.is_read_only:
            return

        for (source_event, to_update, rule) in self.events_handler.events_to_update:
            source_event: GoogleEvent
            to_update: GoogleEvent
            rule: SyncRule
            start = source_event.start.clone()
            end = source_event.end.clone()
            try:
                with db.atomic():
                    if rule.destination.paused:
                        logger.warning(f"Skipping update on sync rule {rule.id} - paused calendar")
                        continue

                    summary, description = make_summary_and_description(source_event, rule)

                    inner = lambda: update_event(service=self.service,
                                                 calendar_id=self.google_id,
                                                 event_id=to_update.id,
                                                 start=start, end=end,
                                                 summary=summary,
                                                 description=description,
                                                 recurrence=source_event.recurrence,
                                                 status=source_event.status.value
                                                 )

                    google_error_handling_with_backoff(inner, self.calendar_db)

            except Exception as e:
                # todo: non-retryable exceptions should throw the error
                logger.warn(f"Failed to process event {to_update.id}: {e}. {traceback.format_exc()}")

    def delete_events(self):
        """
        Calls google API to delete events stored in self.events_handler.
        """
        if self.calendar_db.is_read_only:
            return

        deleted_events = 0
        while self.events_handler.events_to_delete:
            event_id = self.events_handler.events_to_delete.pop()
            try:
                logger.info(f"Deleting event {event_id} in {self.google_id}")
                inner = lambda: delete_event(self.service, self.google_id, event_id)
                if google_error_handling_with_backoff(inner, self.calendar_db):
                    deleted_events += 1
            except Exception as e:
                logger.error(f"Failed to delete event {event_id} in calendar {self.calendar_db.id}: {e}")
        logger.info(f"Deleted {deleted_events} events")

    def get_updated_events(self) -> List[GoogleEvent]:
        """ Returns the events updated since last_processed """
        updated_min = max(self.calendar_db.last_processed.replace(tzinfo=datetime.timezone.utc),
                          utcnow() - datetime.timedelta(days=3))

        start_date = utcnow() - datetime.timedelta(days=30)
        end_date = utcnow() + datetime.timedelta(days=number_of_days_to_sync_in_advance())
        events = self.get_events(start_date=start_date, end_date=end_date, updatedMin=updated_min, orderBy="updated",
                                 showDeleted=True, maxResults=200)

        logger.debug(f"Found updated events: {[(e.id, e.start, e.end) for e in events]}")
        return events

    @staticmethod
    def push_event_to_rule(event: GoogleEvent, rule: SyncRule) -> int:
        """
        Solves a single event update (by updating all other calendars where this event exists)
        """
        logger.info(f"Pushing event {event.id} to rule {rule.id}")
        counter_event_changed = 0
        if len(event.extendedProperties.private) > 0:
            logger.info("Found private extended properties, ignoring")
            return 0

        if event.status == EventStatus.tentative:
            # this means an invitation was received, but not yet accepted, so nothing to do
            return 0

        elif event.status == EventStatus.cancelled:
            # need to delete
            logger.info(f"Found event to delete")
            c = GoogleCalendarWrapper(rule.destination)
            if event.recurringEventId is not None:
                logger.info("Event part of recurrent sequence")
                fetched_events = c.get_events(
                    private_extended_properties=EventExtendedProperty.for_source_id(
                        event.recurringEventId).to_google_dict()
                )
                if len(fetched_events) == 0:
                    logger.info(f"Did not find recurrent source with source id {event.recurringEventId}")
                    raise PushToQueueException(event)

                for fetched_event in fetched_events:
                    if "_" in fetched_event.id:
                        # for events with _R, you don't want to try and delete id_R{date}_{date},
                        # so we re-write the event correctly
                        event_id_to_delete = f'{fetched_event.id.split("_")[0]}_{event.id.split("_")[1]}'
                    else:
                        event_id_to_delete = f'{fetched_event.id}_{event.id.split("_")[1]}'
                    fetched_event.id = event_id_to_delete
                    c.events_handler.delete([fetched_event])
                    c.delete_events()
                    counter_event_changed += 1
            else:
                logger.info("Event not part of recurring sequence")
                fetched_events = c.get_events(
                    private_extended_properties=EventExtendedProperty.for_source_id(event.id).to_google_dict()
                )
                if len(fetched_events) == 0:
                    logger.info(f"Did not find source with source id {event.id}")
                    raise PushToQueueException(event)

                c.events_handler.delete(fetched_events)
                c.delete_events()
                counter_event_changed += 1
        # for some reason the created and updated time are not exactly the same, even when the event is new
        # it looks like google doesn't use a transaction. Bad google. So 1 second threshold for equality
        elif (
                event.created is not None
                and event.updated is not None
                and (event.updated - event.created).seconds < 1
        ):
            # new event, we don't need to check anything more
            logger.info(f"Potential new event")

            source_calendar_uuid = str(rule.source.uuid)
            c = GoogleCalendarWrapper(rule.destination)
            c.get_events(
                private_extended_properties=EventExtendedProperty.for_source_id(event.id).to_google_dict()
            )

            if len(c.events) > 0:
                return 0
            c.events_handler.add([source_event_tuple(event, source_calendar_uuid)], rule)
            if c.insert_events():
                counter_event_changed += 1
        else:
            if event.status == EventStatus.confirmed:
                # This means it's an updated events. Therefore, all the user-associated calendars
                # must have a version of this event in the database, which we can find through the source_id
                # We then update each of this events with the new time
                logger.info(f"Found confirmed event, updating")
                is_recurrence_instance = event.recurringEventId is not None

                c = GoogleCalendarWrapper(rule.destination)
                events = c.get_events(
                    private_extended_properties=EventExtendedProperty.for_source_id(event.id).to_google_dict()
                )

                found_event = None
                skip_normal_update = False
                if len(events) > 0:
                    found_event = events[0]

                    # Sometimes, when recurrent events are changed, depending on the exact manipulation
                    # the event may become cancelled, but later updated. In that case, it will be found
                    # by get_events. This case needs to be handled exactly as if it was never inserted and cancelled
                    if event.recurringEventId is not None and found_event.status == EventStatus.cancelled:
                        skip_normal_update = True

                if found_event and not skip_normal_update:
                    # normal update
                    c.events_handler.update([(event, to_update) for to_update in events], rule)
                    c.update_events()
                    counter_event_changed += 1
                    return counter_event_changed

                elif not is_recurrence_instance:
                    logger.info(f"In update but need to create event")
                    c.events_handler.add([source_event_tuple(event, str(rule.source.uuid))], rule)
                    c.insert_events()
                    counter_event_changed += 1

                else:
                    # i.e. is_recurrence_instance == True
                    logger.info("Verifying that recurrence root exists")
                    recurrence_source_exists = c.get_events(
                        private_extended_properties=EventExtendedProperty.for_source_id(
                            event.recurringEventId).to_google_dict()
                    )
                    if not recurrence_source_exists:
                        # This signals that the root recurrence is missing, and so the instance of the
                        # recurrence update can't be correctly handled
                        missing_recurrence = copy(event)
                        missing_recurrence.id = missing_recurrence.id.split("_")[0]
                        raise PushToQueueException(event)

                    recurrence_source: GoogleEvent = recurrence_source_exists[0]
                    existing_event = copy(event)
                    existing_event.recurringEventId = recurrence_source.id
                    originalStartTime = copy(recurrence_source.start)
                    originalStartTime = originalStartTime.dateTime.replace(
                        year=event.originalStartTime.dateTime.year,
                        month=event.originalStartTime.dateTime.month,
                        day=event.originalStartTime.dateTime.day,
                        hour=event.originalStartTime.dateTime.hour,
                        minute=event.originalStartTime.dateTime.minute
                    )
                    existing_event.originalStartTime = GoogleDatetime(dateTime=originalStartTime,
                                                                      timeZone=recurrence_source.start.timeZone)
                    c.events_handler.add([source_event_tuple(existing_event, str(rule.source.uuid))], rule)
                    c.insert_events()
                    counter_event_changed += 1

            else:
                logger.error(f"Event status error, doesn't match any case: {event.status}, {event.id}")
        return counter_event_changed

    def solve_update_in_calendar(self, preloaded_events: list[GoogleEvent] = None) -> int:
        """ Called when we receive a webhook event saying the calendar requires an update """
        sync_rules = list(get_sync_rules_from_source(self.calendar_db))

        logger.info(f"Found {(n_sync := len(sync_rules))} active SyncRules for {self.calendar_db.uuid}")
        if n_sync == 0:
            return 0

        events = self.get_updated_events()
        events = [event for event in events if len(event.extendedProperties.private) == 0]
        if preloaded_events:
            events.extend(preloaded_events)

        logger.info(f"Found events to update: {len(events)}")
        if not events:
            logger.info(f"No updates found for channel {self.calendar_db.channel_id}")
            return 0

        # sorts them so that even that have a recurrence are handled first
        events.sort(key=lambda x: x.recurrence is None)
        prepared_events = []
        for event in events:
            # go towards a really micro-service architecture: sync rules are handled separately
            for sr in sync_rules:
                prepared_events.append(
                    prepare_event_to_push(event, sr.id, False)
                )
        push_update_event_to_queue(prepared_events, self.session, self.db)

        return len(events)

    @classmethod
    def from_channel_id(cls, channel_id: str):
        calendars = peewee.prefetch(
            Calendar.select().join(CalendarAccount).join(User).where(Calendar.channel_id == channel_id),
            CalendarAccount.select(), User.select())
        assert len(calendars) == 1
        calendar = calendars[0]
        return cls(calendar)


def delete_events_for_sync_rule(sync_rule: SyncRule, boto_session, db, use_queue=True):
    destination_wrapper = GoogleCalendarWrapper(calendar_db=sync_rule.destination)

    events = destination_wrapper.get_events(
        private_extended_properties=EventExtendedProperty.for_calendar_id(str(sync_rule.source.uuid)).to_google_dict(),
        start_date=datetime.datetime.now() - datetime.timedelta(days=14),
        end_date=datetime.datetime.now() + datetime.timedelta(days=number_of_days_to_sync_in_advance()),
        showDeleted=False
    )
    logger.info(f"Setting {len(events)} for deletion")

    if use_queue:
        prepared_events = []
        for event in events:
            if (source_event_id := event.extendedProperties.private.get(EventExtendedProperty.get_source_id_key())) is None:
                logger.warn("Shouldn't be possible to have a copied event without source id")
                continue

            event.id = source_event_id
            event.extendedProperties = ExtendedProperties()
            event.status = EventStatus.cancelled
            prepared_events.append(
                prepare_event_to_push(event, sync_rule.id, True)
            )

        push_update_event_to_queue(prepared_events, session=boto_session, db=db)
    else:
        # for i, event in enumerate(events):
        def _inner(event):
            try:
                GoogleCalendarWrapper.push_event_to_rule(event, sync_rule)
            except Exception as e:
                logger.error(e)

        for i, event in enumerate(events):
            if i % 50 == 0:
                logger.info(f"Sent {i}/{len(event)} events")
            _inner(event)
        # with ThreadPool(8) as p:
        #     print(p.map(_inner, events))
