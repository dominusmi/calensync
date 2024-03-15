import datetime
from typing import Tuple

import peewee

from calensync.api.common import number_of_days_to_sync_in_advance, ApiError
from calensync.database.model import Calendar, User, SyncRule, EmailDB, CalendarAccount, Session
from calensync.gwrapper import GoogleCalendarWrapper, source_event_tuple
from calensync.log import get_logger
from calensync.utils import utcnow

logger = get_logger(__file__)


def verify_valid_sync_rule(user: User, source_calendar_uuid: str, destination_calendar_uuid: str) -> Tuple[
    Calendar, Calendar]:
    if source_calendar_uuid == destination_calendar_uuid:
        raise ApiError("Source and destination cannot be the same", code=400)

    source: Calendar = Calendar.get_or_none(uuid=source_calendar_uuid)
    destination: Calendar = Calendar.get_or_none(uuid=destination_calendar_uuid)

    if source is None or destination is None:
        raise ApiError("Calendar doesn't exist or you do not own it", code=404)

    if destination.is_read_only:
        raise ApiError(f"Calendar {destination.platform_id} is read only")

    SourceAlias = Calendar.alias()
    DestinationAlias = Calendar.alias()
    n_rules = (
        SyncRule.select()
        .join(SourceAlias, on=(SourceAlias.id == SyncRule.source_id))
        .switch(SyncRule)
        .join(DestinationAlias, on=(DestinationAlias.id == SyncRule.destination_id))
        .where(
            SourceAlias.uuid == source_calendar_uuid,
            DestinationAlias.uuid == destination_calendar_uuid
        ).count())

    if n_rules > 0:
        raise ApiError("Sync rule for the same source and destination already exists", code=400)

    return source, destination


def run_initial_sync(sync_rule_id: int):
    sync_rule = list(peewee.prefetch(
        SyncRule.select().where(SyncRule.id == sync_rule_id).limit(1),
        Calendar.select()
    ))[0]
    source = sync_rule.source
    destination = sync_rule.destination

    source_wrapper = GoogleCalendarWrapper(calendar_db=source)
    start_date = datetime.datetime.now()

    # number of days to sync in the futureÏ
    end_date = start_date + datetime.timedelta(days=number_of_days_to_sync_in_advance())
    events = source_wrapper.get_events(start_date, end_date)

    destination_wrapper = GoogleCalendarWrapper(calendar_db=destination)
    destination_wrapper.events_handler.add([source_event_tuple(e, str(source.uuid)) for e in events])
    destination_wrapper.insert_events(private=sync_rule.private)

    if source.expiration is None:
        source_wrapper.create_watch()


def received_webhook(channel_id: str, state: str, resource_id: str, token: str, db: peewee.Database):
    calendar = Calendar.get_or_none(Calendar.channel_id == channel_id)

    if calendar is None or str(calendar.token) != token:
        logger.warn(f"The token {token} does not match the database token {channel_id} ignoring.")
        return

    if resource_id is not None and resource_id != calendar.resource_id:
        calendar.resource_id = resource_id
        calendar.save()

    if state == "sync":
        # This just means a channel was created
        logger.info("Sync signal")
        return

    if calendar is None:
        logger.warn(f"Received webhook for inexistent calendar with channel {channel_id}")
        return

    calendar.last_received = utcnow()
    calendar.save()

    if (utcnow() - calendar.last_inserted.replace(tzinfo=datetime.timezone.utc)).seconds > 1:
        # process the event immediately
        wrapper = GoogleCalendarWrapper(calendar)
        wrapper.solve_update_in_calendar()

        calendar.last_processed = utcnow()
        calendar.save()
    else:
        logger.info("Time interval too short, not updating")
        # Let google know to retry with exponential back-off
        # you may ask why do we do this? I don't know.
        # I think there might have been some "race condition" but I can't remember
        raise ApiError(message="Service unavailable", code=503)


def merge_users(user1: User, user2: User, db) -> Tuple[User,User]:
    main_user = user1 if user1.id < user2.id else user2
    other_user = user1 if user1.id > user2.id else user2

    with db.atomic():
        emails = list(EmailDB.select().where(EmailDB.user == other_user))
        for email in emails:
            email.user = main_user
            email.save()

        accounts = list(CalendarAccount.select().where(CalendarAccount.user == other_user))
        for account in accounts:
            account.user = main_user
            account.save()

        sessions = list(Session.select().where(Session.user == other_user))
        for session in sessions:
            session.user = main_user
            session.save()

    return main_user, other_user