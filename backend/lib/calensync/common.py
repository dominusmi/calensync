import datetime
from collections import defaultdict

import boto3

from calensync.database.model import SyncRule
from calensync.dataclass import EventExtendedProperty, EventStatus
from calensync.gwrapper import GoogleCalendarWrapper


def verify_rules_are_synced(
        rule_uuids: list[str], start_date: datetime.datetime, end_date: datetime.datetime, session: boto3.Session
):
    calendar_to_events = {}

    def _cache_calendar_events(calendar_db):
        if calendar_db.uuid not in calendar_to_events:
            wrapper = GoogleCalendarWrapper(calendar_db, session=session)
            events = wrapper.get_events(start_date, end_date)
            calendar_to_events[calendar_db.uuid] = events
        else:
            events = calendar_to_events[calendar_db.uuid]

        return events

    result = defaultdict(list)
    for rule_uuid in rule_uuids:
        sr: SyncRule = SyncRule.get(uuid=rule_uuid)
        if sr.deleted:
            continue

        source_events = _cache_calendar_events(sr.source)
        destination_events = _cache_calendar_events(sr.destination)

        source_id_to_destination = {
            e.extendedProperties.private[EventExtendedProperty.get_source_id_key()]: e
            for e in destination_events
            if e.extendedProperties.private.get(EventExtendedProperty.get_source_id_key()) is not None
        }

        for s_event in source_events:
            if s_event.extendedProperties.private.get(EventExtendedProperty.get_source_id_key()) is not None:
                continue
            if s_event.id in source_id_to_destination:
                t = source_id_to_destination[s_event.id]
                assert s_event.start == t.start
                assert s_event.end == t.end
                assert s_event.status == t.status
                continue

            if s_event.status == EventStatus.cancelled:
                continue

            if s_event.recurrence:
                start = s_event.recurrence[0].find("UNTIL=")
                if start == -1:
                    continue
                start += 6
                date = s_event.recurrence[0][start:start+16]
                if datetime.datetime.today() > datetime.datetime.strptime(date, '%Y%m%dT%H%M%SZ'):
                    continue

            if s_event.id not in source_id_to_destination and not s_event.extendedProperties.private:
                result[str(rule_uuid)].append(s_event)

    return result
