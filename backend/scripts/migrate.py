import os

from playhouse.migrate import migrate, PostgresqlMigrator

from calensync.database.model import Calendar, OAuthState, User
from calensync.database.utils import DatabaseSession

if __name__ == "__main__":
    os.environ["AWS_PROFILE"] = "opali"
    with DatabaseSession("prod") as db:
        # pass
        migrator = PostgresqlMigrator(db)
        migrate(
            migrator.add_column(User._meta.table_name, 'marketing', User.marketing),
        )