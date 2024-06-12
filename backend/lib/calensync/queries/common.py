import peewee

from calensync.database.model import Calendar, SyncRule


def get_sync_rules_from_source(calendar: Calendar):
    """ Returns valid SyncRules of a calendar """
    Destination = Calendar.alias()
    return peewee.prefetch(
        SyncRule.select().join(Destination, on=(SyncRule.destination_id == Destination.id))
        .where(SyncRule.source == calendar)
        .where(~SyncRule.deleted)
        .where(Destination.paused.is_null()),
        Calendar.select()
    )
