from __future__ import annotations

from typing import List, Tuple

import peewee

from calensync.database.model import User, SyncRule
from calensync.dataclass import GoogleEvent, EventStatus, event_list_to_source_id_map, EventExtendedProperty


# def create_watch(calendar: Calendar, url: str, service, db: peewee.Database, expiration_minutes: int = 120):
#     with db.atomic() as tx:
#         new_expiration = libdatetime.datetime.now() + libdatetime.timedelta(minutes=expiration_minutes)
#         calendar.expiration = new_expiration
#         calendar.save()
#         gwrapper.create_watch(service, calendar, url)
#         # handle error -> tx.rollback()
#         # tx.rollback()


# def renew_watches(db: peewee.Database, service, url):
#     calendars = Calendar.select().where(
#         Calendar.expiration < libdatetime.datetime.utcnow() + libdatetime.timedelta(days=60))
#     for calendar in calendars:
#         create_watch(calendar, url, service, db, expiration_minutes=60 * 24 * 7)


def sync_calendars(user: User, db: peewee.Database):
    # load all events within 4 weeks with last sync greater than current
    # filter out those with extended properties
    # verify that the other appear on the calendars
    pass


def events_to_add(events1: List[GoogleEvent], events2: List[GoogleEvent]) -> List[GoogleEvent]:
    """
    Returns the list of events in calendar 1 not present in calendar 2
    """
    event1_ids = {e.id for e in events1 if e.status != EventStatus.cancelled}
    event2_ids = {e.source_id for e in events2 if e.source_id is not None}
    events_to_add_list = event1_ids.difference(event2_ids)
    return [e for e in events1 if e.id in events_to_add_list]


def events_to_update(events1: List[GoogleEvent], events2: List[GoogleEvent]) -> List[GoogleEvent]:
    """
    Returns the list of events present in events1 with a copy in events2, for which the
    event2 does not have the same start and end time as the respective event1
    """
    ids = set([])
    # only keep events with source_id == None (i.e. which are not original from that calendar)
    copied_events2 = event_list_to_source_id_map(events2)
    for event1 in events1:
        if event1.start == EventStatus.cancelled:
            continue

        event2 = copied_events2.get(event1.id)
        if not event2:
            continue

        same_start = event1.start == event2.start
        same_end = event1.end == event2.end

        if not same_start or not same_end:
            ids.add(event2.id)

    return [e for e in events2 if e.id in ids]


def events_to_delete(events1: List[GoogleEvent], events2: List[GoogleEvent]) -> List[GoogleEvent]:
    """
    Returns list of ids of events in `events2` which are from `events1` and are cancelled
    """
    cancelled_events1 = {event.id for event in events1 if event.status == EventStatus.cancelled}

    # get all generated events from events1 that are not cancelled
    predicate = lambda e: e.source_id and e.status != EventStatus.cancelled  # noqa: E731
    confirmed_events2 = {event.source_id for event in events2 if predicate(event)}

    # the intersection is the events cancelled in events1 that are not cancelled in events2
    events_to_delete_list = cancelled_events1.intersection(confirmed_events2)
    return [e for e in events1 if e.id in events_to_delete_list]


class EventsModificationHandler:
    events_to_add: List[Tuple[GoogleEvent, List[EventExtendedProperty], SyncRule]]
    """ We need both the db event (outdated copy), and the original google event, to be able to update it """
    events_to_update: List[Tuple[GoogleEvent, GoogleEvent, SyncRule]]
    events_to_delete: List[str]

    def __init__(self):
        self.events_to_add = []
        self._added_ids = set([])
        self._updated_ids = set([])
        self.events_to_update = []
        self.events_to_delete = []

    def add(self, events: List[Tuple[GoogleEvent, List[EventExtendedProperty]]], rule: SyncRule, keep_event_id: bool = False):
        for e, ep in events:
            if e.id in self._added_ids:
                continue
            self._added_ids.add(e.id)
            if not keep_event_id:
                e.id = ""
            # recurrent elements should be inserted first, so they're treated first and avoid
            # "race-condition" with potential modified instances
            if e.recurrence is not None:
                self.events_to_add.insert(0, (e, ep, rule))
            else:
                self.events_to_add.append((e, ep, rule))

    def update(self, events: List[Tuple[GoogleEvent, GoogleEvent]], rule: SyncRule, keep_event_id: bool = False):
        for e, ep in events:
            if e.id in self._updated_ids:
                continue
            self._updated_ids.add(e.id)

            if not keep_event_id:
                e.id = ""

            if e.recurrence is not None:
                self.events_to_update.insert(0, (e, ep, rule))
            else:
                self.events_to_update.append((e, ep, rule))

    def delete(self, events: List[GoogleEvent]):
        """
        We want to be absolutely sure that the events we delete have a source id.
        This should already have been checked, but 2 independent checks are better than 1
        """
        for e in events:
            if e.extendedProperties.private.get(EventExtendedProperty.get_source_id_key()) is None:
                continue
            self.events_to_delete.append(e.id)


class PushToQueueException(Exception):
    """
    Exception used to signal that, during processing, something went wrong and an event must be missing
    """
    def __init__(self, event: GoogleEvent):
        super().__init__()
        self.event = event


def set_declined_event_if_necessary(rule: SyncRule, event: GoogleEvent):
    if len(declined_emails := event.get_declined_emails()) > 0:
        # if there's any attendee that have declined, we need to check whether they're the main user
        if rule.source.primary and rule.source.platform_id in declined_emails:
            event.status = EventStatus.declined
        else:
            for calendar in rule.source.account.calendars:
                if not calendar.primary:
                    continue
                if calendar.platform_id in declined_emails:
                    event.status = EventStatus.declined
                break
