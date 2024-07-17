import copy

from calensync.database.model import SyncRule
from calensync.dataclass import GoogleDatetime, EventStatus, GoogleEventAttendee, GoogleEventResponseStatus
from calensync.libcalendar import set_declined_event_if_necessary
from calensync.tests.fixtures import *

now = datetime.datetime.utcnow()
now_google = GoogleDatetime(dateTime=now, timeZone="UCT")

BASE_EVENT = GoogleEvent(
    htmlLink="",
    start=now_google,
    end=now_google, id="123",
    created=now,
    updated=now,
    status=EventStatus.tentative, summary="summary",
)


class TestSetDeclinedIfNecessary:
    @staticmethod
    def test_no_changes(account1_1, calendar1_1, calendar1_2_2):
        sr = SyncRule(source=calendar1_1, destination=calendar1_2_2).save_new()
        event = copy.deepcopy(BASE_EVENT)
        copied = copy.deepcopy(event)
        set_declined_event_if_necessary(sr, copied)
        assert event == copied

        event.attendees = [
            GoogleEventAttendee(email='123', responseStatus=GoogleEventResponseStatus.needsAction),
            GoogleEventAttendee(email='321', responseStatus=GoogleEventResponseStatus.declined)
        ]

        copied = copy.deepcopy(event)
        set_declined_event_if_necessary(sr, copied)
        assert event == copied

    @staticmethod
    def test_user_declined_with_primary(account1_1, calendar1_1, account1_1_2, calendar1_2_2):
        sr = SyncRule(source=calendar1_1, destination=calendar1_2_2).save_new()
        calendar1_1.primary = True
        calendar1_1.save()

        event = copy.deepcopy(BASE_EVENT)
        copied = copy.deepcopy(event)

        event.attendees = [
            GoogleEventAttendee(email='123', responseStatus=GoogleEventResponseStatus.needsAction),
            GoogleEventAttendee(email='321', responseStatus=GoogleEventResponseStatus.declined)
        ]

        copied = copy.deepcopy(event)
        set_declined_event_if_necessary(sr, copied)
        assert event == copied

        event.attendees.append(
            GoogleEventAttendee(email=calendar1_1.platform_id, responseStatus=GoogleEventResponseStatus.accepted)
        )

        copied = copy.deepcopy(event)
        set_declined_event_if_necessary(sr, copied)
        assert event == copied

        event.attendees[-1].responseStatus = GoogleEventResponseStatus.declined
        copied = copy.deepcopy(event)
        set_declined_event_if_necessary(sr, copied)
        assert event != copied
        assert copied.status == EventStatus.declined

    @staticmethod
    def test_user_declined_with_non_primary(calendar1_1, calendar1_2_2, calendar1_2):
        sr = SyncRule(source=calendar1_1, destination=calendar1_2_2).save_new()
        calendar1_1.primary = True
        calendar1_1.save()

        event = copy.deepcopy(BASE_EVENT)
        event.attendees = [
            GoogleEventAttendee(email='123', responseStatus=GoogleEventResponseStatus.needsAction),
            GoogleEventAttendee(email='321', responseStatus=GoogleEventResponseStatus.declined),
            GoogleEventAttendee(email=calendar1_2.platform_id, responseStatus=GoogleEventResponseStatus.declined),
        ]

        copied = copy.deepcopy(event)
        set_declined_event_if_necessary(sr, copied)
        assert event == copied

    @staticmethod
    def test_no_primary_calendar(calendar1_1, calendar1_2_2):
        sr = SyncRule(source=calendar1_1, destination=calendar1_2_2).save_new()

        event = copy.deepcopy(BASE_EVENT)
        event.attendees = [
            GoogleEventAttendee(email='123', responseStatus=GoogleEventResponseStatus.needsAction),
            GoogleEventAttendee(email='321', responseStatus=GoogleEventResponseStatus.declined),
            GoogleEventAttendee(email=calendar1_1.platform_id, responseStatus=GoogleEventResponseStatus.declined),
        ]

        copied = copy.deepcopy(event)
        set_declined_event_if_necessary(sr, copied)
        assert event == copied
