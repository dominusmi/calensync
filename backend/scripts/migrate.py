import os
from copy import copy

import boto3
from playhouse.migrate import migrate, PostgresqlMigrator

from calensync.database.model import Calendar, OAuthState, User, Event, SyncRule, EmailDB, CalendarAccount
from calensync.database.utils import DatabaseSession
from calensync.log import get_logger
from calensync.secure import encrypt_credentials

logger = get_logger(__file__)

if __name__ == "__main__":
    env = 'prod'
    os.environ['ENV'] = env
    os.environ["AWS_PROFILE"] = "opali"
    os.environ['ENCRYPTION_KEY_ARN'] = f'arn:aws:ssm:eu-north-1:071154560691:parameter/calensync-{env}/encryption-key'
    boto_session = boto3.Session()
    with DatabaseSession(env) as db:
        # pass
        migrator = PostgresqlMigrator(db)
        with db.atomic():
            field = copy(CalendarAccount.encrypted_credentials)
            field.null = True
            migrate(
                migrator.add_column(
                    CalendarAccount._meta.name,
                    CalendarAccount.encrypted_credentials.column.name,
                    field
                )
            )
            for account in CalendarAccount.select():
                account: CalendarAccount
                logger.info(f"Updating account {account.id}")
                credentials = account.credentials
                encrypted = encrypt_credentials(credentials, boto_session)
                account.encrypted_credentials = encrypted
                account.save()

            migrate(
                migrator.add_not_null(
                    CalendarAccount._meta.name,
                    CalendarAccount.encrypted_credentials.column.name
                )
            )
            # Event.drop_table()
            # SyncRule.create_table()
            # EmailDB.create_table()
            # for user in User.select():
            #     EmailDB(email=user.email, user=user).save()
            # for ca_group in CalendarAccount.select(CalendarAccount.key, CalendarAccount.user_id):
            #     email_db = EmailDB.get_or_none(email=ca_group.key)
            #     if email_db is None:
            #         EmailDB(email=ca_group.key, user_id=ca_group.user_id).save()
            # migrate(
            #     migrator.drop_column("calendar", "active"),
            #     migrator.drop_column("session", "uuid"),
            #     migrator.add_constraint("calendar", "calendar_platform_id_account_id_key", Calendar._meta.constraints[0]),
            #     migrator.drop_index("user", "user_email"),
            # )
