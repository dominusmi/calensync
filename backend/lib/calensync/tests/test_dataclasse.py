import json

from calensync.dataclass import GoogleEvent
from calensync.tests.fixtures import events_fixture


def test_no_created_attribute(events_fixture):
    data = events_fixture

    before = len(data["items"])
    data["items"][0].pop("created")
    events = GoogleEvent.parse_event_list_response(data)
    after = len(events)
    assert before == after


def test_no_updated_attribute(events_fixture):
    data = events_fixture

    before = len(data["items"])
    data["items"][0].pop("updated")
    events = GoogleEvent.parse_event_list_response(data)
    after = len(events)
    assert before == after