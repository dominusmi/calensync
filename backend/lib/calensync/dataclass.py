from __future__ import annotations

import datetime
import traceback
from enum import Enum, IntEnum
from typing import Dict, List, Optional, Union

import pydantic
from pydantic import BaseModel, Field

from calensync.log import get_logger
from calensync.utils import datetime_to_google_time

logger = get_logger("dataclass")


class AbstractGoogleDate(BaseModel):
    def to_google_dict(self) -> Dict:
        raise NotImplementedError()

    def to_datetime(self) -> datetime.datetime:
        raise NotImplementedError()

    @classmethod
    def from_google_dict(cls, body):
        if date := body.get("date"):
            return GoogleDate(date=date)
        else:
            dt = body["dateTime"]
            return datetime.datetime.fromisoformat(dt[:-1])


class GoogleDate(AbstractGoogleDate):
    date: datetime.date

    def to_google_dict(self):
        return {
            "date": self.date.isoformat()
        }

    def to_datetime(self):
        return datetime.datetime(self.date.year, self.date.month, self.date.day)

    def clone(self):
        return GoogleDate(date=self.date)


class GoogleDatetime(AbstractGoogleDate):
    dateTime: datetime.datetime
    timeZone: Optional[str] = None

    def to_google_dict(self):
        return {
            "dateTime": datetime_to_google_time(self.dateTime),
            "timeZone": self.timeZone or "UCT"
        }

    def to_datetime(self) -> datetime.datetime:
        return self.dateTime

    def clone(self):
        return GoogleDatetime(dateTime=self.dateTime, timeZone=self.timeZone)


class GoogleCalendar(BaseModel):
    kind: str
    id: str
    summary: Optional[str]
    timeZone: Optional[str]
    selected: Optional[bool]
    accessRole: Optional[str]
    primary: bool = False

    def is_readonly(self) -> bool:
        if self.accessRole is None:
            return True

        return self.accessRole in ('reader', 'freeBusyReader')


class EventExtendedProperty(BaseModel):
    key: str
    value: str

    @staticmethod
    def list_to_dict(extended_properties: List[EventExtendedProperty]):
        return {e.key: e.value for e in extended_properties}

    def to_google_dict(self):
        return {self.key: self.value}

    @classmethod
    def for_source_id(cls, value):
        return cls(key=cls.get_source_id_key(), value=value)

    @classmethod
    def for_calendar_id(cls, value):
        return cls(key=cls.get_calendar_id_key(), value=value)

    @classmethod
    def for_rule_id(cls, value):
        return cls(key=cls.get_rule_id_key(), value=value)

    @staticmethod
    def get_source_id_key():
        return "source-id"

    @staticmethod
    def get_calendar_id_key():
        return "calendar-id"

    @staticmethod
    def get_rule_id_key():
        return "csync-rule-id"


class EventStatus(Enum):
    confirmed = 'confirmed'
    tentative = 'tentative'
    cancelled = 'cancelled'
    declined = 'declined'


class ExtendedProperties(BaseModel):
    private: Optional[Dict[str, str]] = {}

    @classmethod
    def from_sources(cls, source_event_id, source_calendar_id, sync_rule_id):
        result = cls()
        result.private[EventExtendedProperty.get_source_id_key()] = source_event_id
        result.private[EventExtendedProperty.get_calendar_id_key()] = source_calendar_id
        result.private[EventExtendedProperty.get_rule_id_key()] = sync_rule_id
        return result


class GoogleEventResponseStatus(Enum):
    needsAction = "needsAction"
    declined = "declined"
    tentative = "tentative"
    accepted = "accepted"


class GoogleEventAttendee(BaseModel):
    email: str
    responseStatus: GoogleEventResponseStatus  # The attendee's response status. Possible values are:


class GoogleEvent(BaseModel):
    id: str
    status: EventStatus
    extendedProperties: ExtendedProperties = ExtendedProperties()
    start: Optional[Union[GoogleDatetime, GoogleDate]] = None
    end: Optional[Union[GoogleDatetime, GoogleDate]] = None
    originalStartTime: Optional[Union[GoogleDatetime, GoogleDate]] = None
    created: Optional[datetime.datetime] = None
    updated: Optional[datetime.datetime] = None
    recurrence: Optional[List[str]] = None
    description: Optional[str] = None
    summary: str = None
    htmlLink: Optional[str] = None
    visibility: str = "public"
    recurringEventId: str = None
    attendees: list[GoogleEventAttendee] = Field(default_factory=lambda: [])

    @staticmethod
    def parse_event_list_response(response: Dict) -> List[GoogleEvent]:
        events = []
        for item in response["items"]:
            try:
                events.append(GoogleEvent.parse_obj(item))
            except pydantic.ValidationError:
                logger.error(f"{item}")
                logger.error(f"Couldn't parse item with id {item.get('id')}: {traceback.format_exc()}")
        return events

    @property
    def source_id(self) -> Optional[str]:
        if self.extendedProperties:
            return self.extendedProperties.private.get("source-id")
        return None

    def get_declined_emails(self) -> List[str]:
        return [attendee.email for attendee in self.attendees
                if attendee.responseStatus == GoogleEventResponseStatus.declined]


def event_list_to_map(events: List[GoogleEvent]) -> Dict[str, GoogleEvent]:
    """ Given a list of events, returns a dictionary id->event """
    return {e.id: e for e in events}


def event_list_to_source_id_map(events: List[GoogleEvent]) -> Dict[str, GoogleEvent]:
    """ Given a list of events, returns a dictionary id->event """
    return {e.source_id: e for e in events if e.source_id is not None}


class QueueEvent(IntEnum):
    GOOGLE_WEBHOOK = 1
    POST_SYNC_RULE = 3
    DELETE_SYNC_RULE = 4
    UPDATED_EVENT = 5


class GoogleWebhookEvent(BaseModel):
    channel_id: str
    token: str
    state: str
    resource_id: Optional[str]


class CalendarStateEnum(IntEnum):
    ACTIVE = 1
    INACTIVE = 2


class UpdateCalendarStateEvent(BaseModel):
    kind: CalendarStateEnum
    calendar_id: str
    user_id: int


class PostSyncRuleEvent(BaseModel):
    sync_rule_id: int


class DeleteSyncRuleEvent(BaseModel):
    sync_rule_id: int


class UpdateGoogleEvent(BaseModel):
    event: GoogleEvent
    rule_id: int
    # this is only to be used for the case where we delete a sync rule, not
    # if the event is of type "cancelled". That would be handled in the
    # "normal" flow
    delete: bool


class SQSEvent(BaseModel):
    kind: QueueEvent
    data: Dict
    first_received: Optional[datetime.datetime] = Field(None)


class PatchCalendarBody(BaseModel):
    kind: str


class PostSyncRuleBody(BaseModel):
    source_calendar_id: str
    destination_calendar_id: str
    summary: str
    description: str


class PatchSyncRuleBody(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
