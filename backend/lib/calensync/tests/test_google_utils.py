from calensync.google_utils import get_recurrent_event_id


class TestGetRecurrentEventId:
    @staticmethod
    def test_normal():
        result = get_recurrent_event_id("123_334", '321')
        assert result == "321_334"

    @staticmethod
    def test_ical():
        result = get_recurrent_event_id("_123_334", '321')
        assert result == "321_334"

