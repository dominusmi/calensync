import logging
logging.root.setLevel(logging.DEBUG)
import peewee
peewee.logger.setLevel(logging.DEBUG)
from calensync.tests.fixtures import db, user
from calensync.database.model import User, EmailDB
from calensync.utils import prefetch_get_or_none


class TestPrefetchOrNone:
    @staticmethod
    def test_exists(db):
        user_db = User().save_new()
        EmailDB(email="test@test.com", user=user_db).save_new()

        result = prefetch_get_or_none(
            EmailDB.select().where(EmailDB.email == "test@test.com"),
            User.select()
        )
        assert isinstance(result, EmailDB)

    @staticmethod
    def test_doesnt_exists(db):
        user_db = User().save_new()
        EmailDB(email="test@test.com", user=user_db).save_new()

        result = prefetch_get_or_none(
            EmailDB.select().where(EmailDB.email == "testing@test.com"),
            User.select()
        )
        assert result is None
