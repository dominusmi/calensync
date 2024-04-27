import copy
import datetime
import uuid
from collections import defaultdict
from typing import List, Union, Set, Dict
from unittest.mock import MagicMock

from calensync.dataclass import GoogleEvent, EventStatus, GoogleDatetime, AbstractGoogleDate
from calensync.utils import utcnow, datetime_to_google_time


class MockedServiceEvents:
    service: 'MockedService'
    events: Dict[str, List[GoogleEvent]]

    def __init__(self, service):
        self.service = service
        self.events = defaultdict(list)

    def filter_events(self, calendarId: str = None, timeMin: str = None, timeMax: str = None,
             privateExtendedProperties: Union[str, List[str]] = None,
             timeZone: str = None, updatedMin: datetime.datetime = None, **kwargs):

        if calendarId not in self.events:
            return []

        results = copy.deepcopy(self.events[calendarId])
        if timeMin is not None:
            results = [e for e in results if
                       e.end.to_datetime().replace(tzinfo=datetime.timezone.utc) >
                       datetime.datetime.fromisoformat(timeMin[:-1]).replace(tzinfo=datetime.timezone.utc)]

        if timeMax is not None:
            results = [e for e in results if
                       e.start.to_datetime().replace(tzinfo=datetime.timezone.utc) < datetime.datetime.fromisoformat(
                           timeMax[:-1]).replace(
                           tzinfo=datetime.timezone.utc)]

        if updatedMin is not None:
            results = [e for e in results if
                       e.updated > datetime.datetime.fromisoformat(updatedMin[:-1])]

        if privateExtendedProperties:
            if isinstance(privateExtendedProperties, list):
                for pep in privateExtendedProperties:
                    key, value = pep.split("=")
                    results = [e for e in results if e.extendedProperties.private.get(key) == value]
        return results

    def list(self, **kwargs):
        events = self.filter_events(**kwargs)
        mocked_result = MagicMock()
        mocked_result.execute.side_effect = lambda: {"items": events}
        return mocked_result

    def insert(self, calendarId: str, body: Dict):
        body["htmlLink"] = str(uuid.uuid4())
        body["id"] = str(uuid.uuid4())
        body["status"] = EventStatus.confirmed

        event = GoogleEvent.parse_obj(body)
        self.events[calendarId].append(event)
        mocked_result = MagicMock()
        return mocked_result

    def patch(self, calendarId, event_id: str, start: str = None, end: str = None, summary: str = None, description: str = None):
        event: GoogleEvent = next(filter(lambda x: x.id == event_id, self.events[calendarId]))
        if start:
            event.start = AbstractGoogleDate.from_google_dict(start)
        if end:
            event.end = AbstractGoogleDate.from_google_dict(end)
        if summary:
            event.summary = summary
        if description:
            event.description = description

    @staticmethod
    def list_next(*args):
        return None


class MockedService:
    _events_service: MockedServiceEvents

    def __init__(self):
        self.calendars = set([])
        self._events = MockedServiceEvents(self)
        self.events = MagicMock()
        self.events.return_value = self._events

    def add_calendar(self, calendar_id: str):
        self.calendars.add(calendar_id)

    def add_event(self, event: GoogleEvent, calendar_id: str):
        self._events.events[calendar_id].append(event)

    def reset(self):
        self.calendars = set([])
        self._events = MockedServiceEvents(self)
        self.events = MagicMock()
        self.events.return_value = self._events
        # super().__init__()


def test_service():
    calendarId = "test"
    service = MockedService()
    event1 = GoogleEvent(
        htmlLink="link",
        id=str(uuid.uuid4()),
        status=EventStatus.confirmed,
        summary="summary1",
        start=GoogleDatetime(dateTime=utcnow() - datetime.timedelta(minutes=30)),
        end=GoogleDatetime(dateTime=utcnow() - datetime.timedelta(minutes=5)),
    )
    service.add_event(event1, calendarId)

    event2 = GoogleEvent(
        htmlLink="link",
        id=str(uuid.uuid4()),
        status=EventStatus.confirmed,
        summary="summary1",
        start=GoogleDatetime(dateTime=utcnow() + datetime.timedelta(minutes=5)),
        end=GoogleDatetime(dateTime=utcnow() + datetime.timedelta(minutes=30)),
    )
    service.add_event(event2, calendarId)

    events = service.events().list(
        calendarId=calendarId,
        timeMin=datetime_to_google_time(utcnow() + datetime.timedelta(minutes=5)),
        timeMax=datetime_to_google_time(utcnow() + datetime.timedelta(minutes=35))
    ).execute()
    assert events["items"][0].id == event2.id
