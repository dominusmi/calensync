from __future__ import annotations

import datetime
import traceback
from typing import Tuple

import boto3
import peewee

from calensync.api.common import number_of_days_to_sync_in_advance, ApiError
from calensync.database.model import Calendar, User, SyncRule, EmailDB, CalendarAccount, Session
from calensync.dataclass import EventExtendedProperty, DeleteSyncRuleEvent, GoogleCalendar, SQSEvent, QueueEvent, \
    GoogleWebhookEvent, PostSyncRuleEvent, UpdateGoogleEvent, EventStatus, ExtendedProperties, PatchSyncRuleBody
from calensync.gwrapper import GoogleCalendarWrapper, delete_events_for_sync_rule
from calensync.libcalendar import PushToQueueException
from calensync.log import get_logger
from calensync.sqs import SQSEventRun, check_if_should_run_time_or_wait, push_update_event_to_queue, \
    prepare_event_to_push
from calensync.utils import utcnow, BackoffException

logger = get_logger(__file__)


def verify_valid_sync_rule(user: User, source_calendar_uuid: str, destination_calendar_uuid: str
                           ) -> Tuple[Calendar, Calendar]:
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
            DestinationAlias.uuid == destination_calendar_uuid,
            SyncRule.deleted == False
        ).count())

    if n_rules > 0:
        raise ApiError("Sync rule for the same source and destination already exists")

    return source, destination


def run_initial_sync(sync_rule_id: int, session: boto3.Session, db):
    logger.info(f"Running first sync on {sync_rule_id}")
    sync_rule = list(peewee.prefetch(
        SyncRule.select().where(SyncRule.id == sync_rule_id).limit(1),
        Calendar.select()
    ))[0]
    source: Calendar = sync_rule.source
    destination: Calendar = sync_rule.destination

    source_wrapper = GoogleCalendarWrapper(calendar_db=source, session=session)
    start_date = datetime.datetime.now()

    source.last_received = utcnow()
    source.save()

    # number of days to sync in the future
    end_date = start_date + datetime.timedelta(days=number_of_days_to_sync_in_advance())
    events = source_wrapper.get_events(start_date, end_date)

    # sorts them so that even that have a recurrence are handled first
    events.sort(key=lambda x: x.recurrence is None)

    events = list(filter(lambda x: len(x.extendedProperties.private) == 0, events))
    logger.info(f"Found {len(events)} events, pushing to queue")
    prepared_events = [prepare_event_to_push(e, sync_rule.id, False) for e in events]
    push_update_event_to_queue(prepared_events, session, db)

    source.last_processed = utcnow()
    source.save()

    if source.expiration is None:
        source_wrapper.create_watch()


def received_webhook(channel_id: str, state: str, resource_id: str, token: str,
                     approximate_first_received: datetime.datetime,
                     boto_session: boto3.Session, db: peewee.Database):
    calendar = Calendar.get_or_none(Calendar.channel_id == channel_id)

    if calendar is None or str(calendar.token) != token:
        logger.warn(f"The token {token} does not match the database token {channel_id} ignoring.")
        return None

    if resource_id is not None and resource_id != calendar.resource_id:
        calendar.resource_id = resource_id
        calendar.save()

    if state == "sync":
        # This just means a channel was created
        logger.info("Sync signal")
        return None

    if calendar is None:
        logger.warn(f"Received webhook for non-existent calendar with channel {channel_id}")
        return None

    logger.info(f"Processing event first received at {(utcnow() - approximate_first_received).seconds} seconds ago")

    sqs_event_run = check_if_should_run_time_or_wait(calendar, approximate_first_received)

    if sqs_event_run == SQSEventRun.RETRY:
        logger.info("Event set for retry")
        raise ApiError(message="Service unavailable", code=503)
    elif sqs_event_run == SQSEventRun.DELETE:
        logger.info("Event already processed")
        return True
    else:
        with db.atomic():
            # db atomic so that if solve_update_in_calendar fails for any reason,
            # we assume we didn't push the event to the queue
            calendar.last_processed = calendar.last_received
            calendar.last_received = utcnow()
            wrapper = GoogleCalendarWrapper(calendar, session=boto_session)
            wrapper.solve_update_in_calendar()
            calendar.save()
    return None


def merge_users(user1: User, user2: User, db) -> Tuple[User, User]:
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


def delete_calensync_events(destination_wrapper: 'GoogleCalendarWrapper', source_calendar_uuid: str):
    events = destination_wrapper.get_events(
        private_extended_properties=EventExtendedProperty.for_calendar_id(source_calendar_uuid).to_google_dict(),
        start_date=datetime.datetime.now(),
        end_date=datetime.datetime.now() + datetime.timedelta(days=number_of_days_to_sync_in_advance()),
        showDeleted=False
    )
    destination_wrapper.events_handler.delete(events)
    destination_wrapper.delete_events()


def handle_delete_sync_rule_event(sync_rule_id: int, boto_session: boto3.Session, db):
    sync_rule: SyncRule = SyncRule.get_or_none(id=sync_rule_id)
    if sync_rule is None:
        logger.warning(f"Sync rule {sync_rule_id} doesn't exist")
        return

    try:
        delete_events_for_sync_rule(sync_rule, boto_session, db)
    except Exception as e:
        logger.error(f"Failed to delete events for sync rule {sync_rule}: {e}\n\n{traceback.format_exc()}")

    # check if calendar has other rule sync rules, otherwise delete watch
    other_rules_same_source = list(
        SyncRule.select().where(SyncRule.source == sync_rule.source, SyncRule.id != sync_rule.id))
    if not other_rules_same_source:
        GoogleCalendarWrapper(sync_rule.source, session=boto_session).delete_watch()

    sync_rule.deleted = True
    sync_rule.save()


def handle_update_sync_rule_event(sync_rule: SyncRule, payload: PatchSyncRuleBody, boto_session: boto3.Session, db):
    sync_rule.summary = payload.summary
    sync_rule.description = payload.description
    sync_rule.save()

    start_date = utcnow() - datetime.timedelta(days=1)
    end_date = utcnow() + datetime.timedelta(days=number_of_days_to_sync_in_advance())
    private_extended_props = {EventExtendedProperty.get_rule_id_key(): sync_rule.uuid}

    wrapper = GoogleCalendarWrapper(sync_rule.destination, session=boto_session)
    events = wrapper.get_events(start_date=start_date, end_date=end_date,
                                private_extended_properties=private_extended_props)

    if len(events) == 0:
        # we assume that it's a case where the rule was created before the rule_id private extended
        # property was added. So instead of using that as filter, we simply run an initial sync
        logger.info(f"No events found with extended property of rule {sync_rule.uuid}. Running initial sync instead")
        run_initial_sync(sync_rule.id, boto_session, db)
        return

    double_check = []
    for event in events:
        if event.extendedProperties.private.get(EventExtendedProperty.get_rule_id_key()) == str(sync_rule.uuid):
            double_check.append(event)

    if len(double_check) != len(events):
        logger.warning(f"wrapper.get_events with private extended properties filter failed: "
                       f"{len(events)} vs {len(double_check)}")

    prepared_events = []
    for event in double_check:
        # go towards a microservice architecture: sync rules are handled separately
        prepared_events.append(
            prepare_event_to_push(event, sync_rule.id, False)
        )
    push_update_event_to_queue(prepared_events, boto_session, db)


def handle_refresh_existing_calendar(calendar: GoogleCalendar, calendar_db: Calendar, name: str):
    updated = False
    if calendar.accessRole == 'reader':
        # these are calendars imported from another account, they're read only
        if not calendar_db.readonly:
            calendar_db.readonly = True
            updated = True

    if calendar_db.name != name:
        calendar_db.name = name
        updated = True

    if updated:
        calendar_db.save()


def handle_sqs_event(sqs_event: SQSEvent, db, boto_session: boto3.Session):
    if sqs_event.kind == QueueEvent.GOOGLE_WEBHOOK:
        we: GoogleWebhookEvent = GoogleWebhookEvent.parse_obj(sqs_event.data)
        logger.info(f"Processing calendar with token {we.token} ")
        received_webhook(we.channel_id, we.state, we.resource_id, we.token, sqs_event.first_received, boto_session, db)

    elif sqs_event.kind == QueueEvent.POST_SYNC_RULE:
        logger.info("Adding sync rule")
        e: PostSyncRuleEvent = PostSyncRuleEvent.parse_obj(sqs_event.data)
        run_initial_sync(e.sync_rule_id, boto_session, db)

    elif sqs_event.kind == QueueEvent.DELETE_SYNC_RULE:
        logger.info("Deleting sync rule")
        e: DeleteSyncRuleEvent = DeleteSyncRuleEvent.parse_obj(sqs_event.data)
        handle_delete_sync_rule_event(e.sync_rule_id, boto_session, db)

    elif sqs_event.kind == QueueEvent.UPDATED_EVENT:
        e: UpdateGoogleEvent = UpdateGoogleEvent.parse_obj(sqs_event.data)

        # error catching is handled in the lambda handler function
        handle_updated_event(e)

    else:
        logger.error("Unknown event type")


def handle_updated_event(e: UpdateGoogleEvent):
    rules = list(SyncRule.select().where(SyncRule.id == e.rule_id))
    if len(rules) == 0:
        logger.warn(f"No rules found for update event: {e.event.id} - rule id: {e.rule_id}")

    event = e.event

    if e.delete:
        # we mark the event as if it was cancelled, so that all the event update logic
        # is handled in the same function and makes things simpler
        event.status = EventStatus.cancelled

    GoogleCalendarWrapper.push_event_to_rule(event, rules[0])
