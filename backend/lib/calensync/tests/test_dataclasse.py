import json

from calensync.dataclass import GoogleEvent


def test_parse_event():
    with open("list_events.json") as f:
        data = json.load(f)

    events = GoogleEvent.parse_event_list_response(data)
    assert len(events) > 1
