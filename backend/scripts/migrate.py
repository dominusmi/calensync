import os

from playhouse.migrate import migrate, PostgresqlMigrator

from calensync.database.model import Calendar, OAuthState, User, Event, SyncRule, EmailDB, CalendarAccount
from calensync.database.utils import DatabaseSession

if __name__ == "__main__":
    os.environ["AWS_PROFILE"] = "opali"
    with DatabaseSession("prod") as db:
        # pass
        migrator = PostgresqlMigrator(db)
        with db.atomic():
            # Event.drop_table()
            # SyncRule.create_table()
            # EmailDB.create_table()
            # for user in User.select():
            #     EmailDB(email=user.email, user=user).save()
            for ca_group in CalendarAccount.select(CalendarAccount.key, CalendarAccount.user_id):
                email_db = EmailDB.get_or_none(email=ca_group.key)
                if email_db is None:
                    EmailDB(email=ca_group.key, user_id=ca_group.user_id).save()
            # migrate(
            #     migrator.drop_column("calendar", "active"),
            #     migrator.drop_column("session", "uuid"),
            #     migrator.add_constraint("calendar", "calendar_platform_id_account_id_key", Calendar._meta.constraints[0]),
            #     migrator.drop_index("user", "user_email"),
            # )

