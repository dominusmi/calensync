import json

from calensync.dataclass import GoogleEvent


def test_parse_event():
    with open("list_events.json") as f:
        data = json.load(f)

    events = GoogleEvent.parse_event_list_response(data)
    assert len(events) > 1


def test_no_created_attribute():
    with open("list_events.json") as f:
        data = json.load(f)

    before = len(data["items"])
    data["items"][0].pop("created")
    events = GoogleEvent.parse_event_list_response(data)
    after = len(events)
    assert before == after


def test_no_updated_attribute():
    with open("list_events.json") as f:
        data = json.load(f)

    before = len(data["items"])
    data["items"][0].pop("updated")
    events = GoogleEvent.parse_event_list_response(data)
    after = len(events)
    assert before == after