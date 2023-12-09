from unittest.mock import patch


def test_sync_calendars_on_day():
    with (
        patch("calensync.gwrapper.insert_event") as insert_event,
        patch("calensync.wrapper.GoogleCalendarWrapper.service")
    ):
        pass
