import copy
import datetime
import uuid
from typing import List

from calensync.libcalendar import events_to_add, events_to_update, events_to_delete
from calensync.dataclass import GoogleEvent, EventStatus, \
    ExtendedProperties
from calensync.tests.fixtures import events_fixture


def make_virtual_events(events_fixture):
    new_events = copy.deepcopy(events_fixture)
    for e in new_events:
        e.extendedProperties = ExtendedProperties(private={"source-id": e.id})
        e.id = uuid.uuid4().__str__()

    return new_events


def test_find_events_to_add(events_fixture):
    events = GoogleEvent.parse_event_list_response(events_fixture)
    calendar_1 = copy.deepcopy(events)
    calendar_2 = make_virtual_events(calendar_1)
    assert not events_to_add(calendar_1, calendar_2)

    # make last one missing
    calendar_2 = make_virtual_events(calendar_1)
    calendar_2[-1].extendedProperties.private["source-id"] = uuid.uuid4().__str__()

    result = events_to_add(calendar_1, calendar_2)
    assert len(result) == 1
    assert result[0].id == calendar_1[-1].id


def test_find_events_to_update(events_fixture):
    events = GoogleEvent.parse_event_list_response(events_fixture)
    events1 = copy.deepcopy(events)
    events2 = make_virtual_events(events1)

    result = events_to_update(events1, events2)
    assert not result

    events2[3].start.dateTime = events2[3].start.dateTime + datetime.timedelta(minutes=30)
    events2[3].end.dateTime = events2[3].end.dateTime + datetime.timedelta(minutes=30)

    result = events_to_update(events1, events2)
    assert len(result) == 1
    assert result[0].id == events2[3].id


def test_find_cancelled_events(events_fixture):
    events = GoogleEvent.parse_event_list_response(events_fixture)
    events1 = copy.deepcopy(events)
    events2 = make_virtual_events(events1)

    events1[1].status = EventStatus.cancelled
    events1[3].status = EventStatus.cancelled

    events = events_to_delete(events1, events2)
    assert {e.id for e in events} == {events1[1].id, events1[3].id}
