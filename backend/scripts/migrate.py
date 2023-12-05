from playhouse.migrate import migrate, PostgresqlMigrator

from calensync.database.model import Calendar, Sync
from calensync.database.utils import DatabaseSession

if __name__ == "__main__":
    with DatabaseSession("local") as db:
        pass
        # migrator = PostgresqlMigrator(db)
        # migrate(
        #     migrator.add_column(Calendar._meta.table_name, 'active', Calendar.active),
        # )