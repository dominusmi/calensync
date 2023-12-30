import peewee

from calensync.database.model import Calendar, SyncRule


def get_sync_rules_from_source(calendar: Calendar):
    return peewee.prefetch(
        SyncRule.select().where(SyncRule.source == calendar),
        Calendar.select()
    )
