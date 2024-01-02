import datetime

import peewee

from calensync.database.model import User, CalendarAccount, Calendar


def get_users_with_no_calendar_account(min_date_created: datetime.datetime):
    return (
        User.select()
        .join(CalendarAccount, join_type=peewee.JOIN.LEFT_OUTER)
        .where(
            User.id.not_in(CalendarAccount.select(CalendarAccount.user)),
            User.date_created >= min_date_created
        )
    )


def get_users_with_only_one_calendar_active(min_date_created: datetime.datetime):
    subquery = (
        Calendar
        .select(Calendar.account.user)
        .join(CalendarAccount)
        .join(User)
        .where(Calendar.active)
        .group_by(Calendar.account.user)
        .having(peewee.fn.Count("*") == 1)
    )
    query = (
        User
        .select()
        .join(CalendarAccount)
        .join(Calendar)
        .where(User.id.in_(subquery), User.date_created >= min_date_created)
        .distinct()
    )
    return query
