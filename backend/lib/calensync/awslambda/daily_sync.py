import datetime
import time
import traceback
from typing import Iterable, List

import boto3
import peewee

from calensync.api.common import number_of_days_to_sync_in_advance
from calensync.database.model import User, Calendar, CalendarAccount, SyncRule, EmailDB
from calensync.email import send_trial_ending_email, send_account_to_be_deleted_email
from calensync.gwrapper import GoogleCalendarWrapper, service_from_account
from calensync.log import get_logger
from calensync.utils import utcnow

logger = get_logger("daily_sync.main")


def load_calendars(accounts: List[CalendarAccount], start_date: datetime.datetime, end_date: datetime.datetime
                   ) -> list[GoogleCalendarWrapper]:
    calendars = []
    for account in accounts:
        for calendar in account.calendars:
            # setting this avoid having to re-fetch it from the database to get the credentials
            service = service_from_account(account)
            calendars.append(GoogleCalendarWrapper(calendar, service=service))

    for cal in calendars:
        try:
            cal.get_events(start_date, end_date)
        except Exception as e:
            logger.info(f"Skipping calendar {calendar.uuid} due to {e}")

    return calendars


def execute_update(calendars: List[GoogleCalendarWrapper], db):
    # spooky double loop. Need to save each calendar events in the others
    for i, cal1 in enumerate(calendars):
        for cal2 in calendars[i + 1:]:
            cal1.events_handler.add(cal2.events)
            cal2.events_handler.add(cal1.events)

    with db.atomic():
        for cal in calendars:
            cal.insert_events()


def get_users_query_with_active_sync_rules():
    sub_query = SyncRule.select(User.id).join(Calendar, on=(Calendar.id == SyncRule.source)).join(CalendarAccount).join(
        User)

    query: Iterable[User] = peewee.prefetch(
        User.select().join(CalendarAccount).join(Calendar).where(User.id << sub_query).distinct(),
        CalendarAccount.select(),
        Calendar.select()
    )
    return query


def hard_sync(db):
    """ Only to be used to fix user calendars having issues """
    # users_query = get_users_query_with_active_sync_rules()
    users_query = list(User.select().where(User.id == 217))
    start: datetime.datetime = datetime.datetime.today()
    start_date = datetime.datetime.fromtimestamp(start.timestamp())
    start_date = start_date.replace(hour=0, minute=0, second=0)
    end_date = start_date + datetime.timedelta(days=number_of_days_to_sync_in_advance())

    # because the dates are exclusive in the Google API, this will fetch from 00:00:00 of day, to 23:59:59
    start_date = start_date - datetime.timedelta(seconds=1)
    logger.info(f"Start/end date: {start_date.isoformat()} -> {end_date.isoformat()}")

    for user in users_query:
        try:
            logger.info(f"Syncing {user.uuid}")
            calendar_wrappers = load_calendars(user.accounts, start_date, end_date)
            for wrapper in calendar_wrappers:
                wrapper.solve_update_in_calendar(include_preloaded_events=True)
        except Exception as e:
            logger.error(f"Error occured while updating calendar {user.uuid}: {e}\n\n{traceback.format_exc()}")
            time.sleep(1)


def sync_user_calendars_by_date(db):
    users_query = get_users_query_with_active_sync_rules()
    start: datetime.datetime = datetime.datetime.today() + datetime.timedelta(days=number_of_days_to_sync_in_advance())
    start_date = datetime.datetime.fromtimestamp(start.timestamp())
    start_date = start_date.replace(hour=0, minute=0, second=0)
    end_date = start_date + datetime.timedelta(hours=24)

    # because the dates are exclusive in the Google API, this will fetch from 00:00:00 of day, to 23:59:59
    start_date = start_date - datetime.timedelta(seconds=1)
    logger.info(f"Start/end date: {start_date.isoformat()} -> {end_date.isoformat()}")

    for user in users_query:
        try:
            logger.info(f"Syncing {user.uuid}")
            calendar_wrappers = load_calendars(user.accounts, start_date, end_date)
            for wrapper in calendar_wrappers:
                wrapper.solve_update_in_calendar()
        except Exception as e:
            logger.error(f"Error occured while updating calendar {user.uuid}: {e}\n\n{traceback.format_exc()}")
            time.sleep(1)


def update_watches(db: peewee.Database):
    now = utcnow()
    calendars_db: Iterable[Calendar] = peewee.prefetch(
        Calendar.select()
        .join(SyncRule, on=(Calendar.id == SyncRule.source))
        .where(
            Calendar.expiration.is_null(False),
            Calendar.expiration <= now + datetime.timedelta(hours=36)),
        CalendarAccount.select(),
        User.select()
    )

    for calendar_db in calendars_db:
        iteration = 0
        deleted = False
        while iteration < 3:
            try:
                logger.info(f"Updating watch of calendar {calendar_db.uuid}")
                gcalendar = GoogleCalendarWrapper(calendar_db)

                try:
                    if not deleted:
                        gcalendar.delete_watch()
                    deleted = True
                except Exception as e:
                    logger.error(
                        f"Failed to delete watch of {calendar_db.uuid}: {e}")

                gcalendar.create_watch()
                break

            except Exception as e:
                logger.error(
                    f"Error occured while updating calendar {calendar_db.uuid}: {e}\n\n{traceback.format_exc()}")
                time.sleep(1)
            finally:
                iteration += 1


def get_trial_users_with_create_before_date(start: datetime.datetime):
    # Main query
    user_ids = (User
                .select(User.id).distinct()
                .join(CalendarAccount)
                .join(Calendar)
                .join(SyncRule, on=(SyncRule.source == Calendar.id))
                .where(
        User.date_created < start,
        User.subscription_id.is_null(True),
        # If there were no previous email, or the previous email was sent earlier
        (User.last_email_sent.is_null(True)) | (User.last_email_sent < start)
    )
                .group_by(User.id)
                .having(peewee.fn.COUNT(SyncRule.id) > 0)
                )

    # Get oldest email for user
    EmailAlias = EmailDB.alias()

    subquery = (
        EmailAlias
        .select(
            EmailAlias.user,
            peewee.fn.MIN(EmailAlias.date_created).alias('min_created'))
        .group_by(EmailAlias.user)
        .alias('email_min_subquery'))

    query = (
        EmailDB
        .select(EmailDB).distinct()
        .join(User)
        .switch(EmailDB)
        .join(subquery, on=(
                (EmailDB.date_created == subquery.c.min_created) &
                (EmailDB.user == subquery.c.user_id)))
        .where(EmailDB.user << user_ids)
    )

    return query


def send_trial_finishing_email(session: boto3.Session, db: peewee.Database):
    # just finishing trial
    one_week_ago_end = datetime.datetime.now() - datetime.timedelta(days=7)

    query = get_trial_users_with_create_before_date(one_week_ago_end)
    for email_db in query:
        if send_trial_ending_email(session, email_db.email):
            email_db.user.last_email_sent = utcnow()
            email_db.user.save()

    two_weeks_ago_end = datetime.datetime.now() - datetime.timedelta(days=14)

    query = get_trial_users_with_create_before_date(two_weeks_ago_end)
    for email_db in query:
        if send_account_to_be_deleted_email(session, email_db.email):
            email_db.user.last_email_sent = utcnow()
            email_db.user.save()
