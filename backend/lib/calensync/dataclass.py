from __future__ import annotations

import datetime
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel


class AbstractGoogleDate(BaseModel):
    def to_google_dict(self) -> Dict:
        raise NotImplementedError()

    def to_datetime(self) -> datetime.datetime:
        raise NotImplementedError()


class GoogleDate(AbstractGoogleDate):
    date: datetime.date

    def to_google_dict(self):
        return {
            "date": self.date.isoformat()
        }

    def to_datetime(self):
        return datetime.datetime(self.date.year, self.date.month, self.date.day)


class GoogleDatetime(AbstractGoogleDate):
    dateTime: datetime.datetime
    timeZone: Optional[str] = None  # deprecated

    def to_google_dict(self):
        return {
            "dateTime": self.dateTime.astimezone().isoformat(timespec="seconds"),
        }

    def to_datetime(self) -> datetime.datetime:
        return self.dateTime


class GoogleCalendar(BaseModel):
    kind: str
    id: str
    summary: str
    timeZone: str
    selected: bool
    accessRole: str
    primary: bool = False


class EventExtendedProperty(BaseModel):
    key: str
    value: str

    @staticmethod
    def list_to_dict(extended_properties: List[EventExtendedProperty]):
        return {e.key: e.value for e in extended_properties}

    @classmethod
    def for_source_id(cls, value):
        return cls(key="source-id", value=value)

    @classmethod
    def for_calendar_id(cls, value):
        return cls(key="calendar-id", value=value)


class EventStatus(str, Enum):
    confirmed = 'confirmed'
    tentative = 'tentative'
    cancelled = 'cancelled'


class GoogleEvent(BaseModel):
    extendedProperties: Optional[Dict[str, Dict[str, str]]]
    htmlLink: str
    start: Union[GoogleDatetime, GoogleDate]
    end: Union[GoogleDatetime, GoogleDate]
    id: str
    created: datetime.datetime
    updated: datetime.datetime
    status: EventStatus
    recurrence: Optional[List[str]] = None

    @staticmethod
    def parse_event_list_response(response: Dict) -> List[GoogleEvent]:
        events = []
        for item in response["items"]:
            events.append(GoogleEvent.parse_obj(item))

        return events

    @property
    def source_id(self) -> Optional[str]:
        if self.extendedProperties:
            return self.extendedProperties.get("private", {}).get("source-id")
        return None


def event_list_to_map(events: List[GoogleEvent]) -> Dict[str, GoogleEvent]:
    """ Given a list of events, returns a dictionary id->event """
    return {e.id: e for e in events}


def event_list_to_source_id_map(events: List[GoogleEvent]) -> Dict[str, GoogleEvent]:
    """ Given a list of events, returns a dictionary id->event """
    return {e.source_id: e for e in events if e.source_id is not None}


