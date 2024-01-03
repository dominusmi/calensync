from __future__ import annotations

import enum
import uuid
from abc import ABC
from typing import Type, TypeVar, Iterable, List

import peewee
from peewee import Model, AutoField, CharField, DateTimeField, ForeignKeyField, UUIDField, IntegerField
from playhouse.postgres_ext import PostgresqlExtDatabase, JSONField

from calensync.encode import ISerializable
from calensync.utils import utcnow

db = PostgresqlExtDatabase(None)

TBaseModel = TypeVar("TBaseModel", bound="BaseModel")


class OAuthKind(enum.IntEnum):
    GOOGLE_SSO = 1
    ADD_GOOGLE_ACCOUNT = 2


class EnumField(IntegerField, ABC):
    """
    This class enable an Enum like field for Peewee
    """

    def __init__(self, enum: Type[enum.Enum], *args, **kwargs):
        super(IntegerField, self).__init__(*args, **kwargs)
        self.enum = enum

    def db_value(self, value):
        return value.value

    def python_value(self, value):
        return self.enum(value)


class BaseModel(Model, ISerializable):
    id = AutoField()
    date_created = DateTimeField(default=utcnow)
    date_modified = DateTimeField(default=utcnow)

    def save(self, *args, **kwargs):
        self.date_modified = utcnow()
        return super(BaseModel, self).save(*args, **kwargs)

    def save_new(self):
        super().save()
        return self

    def serialize(self):
        return self.__data__

    def refresh(self: TBaseModel) -> TBaseModel:
        return type(self).get(self._pk_expr())

    def get_update_fields(self):
        """
        Given an instance, returns the fields to be used for an insert_many onconflict update
        Can't find a good name for this function.
        """
        data = self.__data__
        if "id" in data:
            raise RuntimeError("If id is defined, it means this element already exists")
        data.pop("date_created")
        return data

    class Meta:
        database = db


class UUIDBaseModel(BaseModel):
    uuid = UUIDField(default=uuid.uuid4)


class User(UUIDBaseModel):
    email = CharField(unique=True)
    is_admin = peewee.BooleanField(default=False)
    tos = peewee.DateTimeField(default=None, null=True)
    customer_id = CharField(null=True, default=None)
    transaction_id = CharField(null=True, default=None)
    subscription_id = CharField(null=True, default=None)
    marketing = peewee.BooleanField(default=True)

    @staticmethod
    def from_email(email: str) -> User:
        return User.get(email=email)


class CalendarAccount(UUIDBaseModel):
    user = ForeignKeyField(User, backref='accounts')
    key = CharField()
    credentials = JSONField()

    class Meta:
        constraints = [peewee.SQL('UNIQUE (user_id, key)')]


class Calendar(UUIDBaseModel):
    account = ForeignKeyField(CalendarAccount, backref='calendars')
    platform_id = CharField(help_text="This is the id provided by the service (e.g. the google id for the calendar)")
    name = CharField(null=True)
    channel_id = UUIDField(default=uuid.uuid4)
    resource_id = CharField(null=True)
    token = UUIDField(default=uuid.uuid4)
    expiration = DateTimeField(null=True)
    last_sync = DateTimeField(null=True)
    last_inserted = DateTimeField(default=utcnow)
    last_received = DateTimeField(default=utcnow)
    last_processed = DateTimeField(default=utcnow)

    @property
    def friendly_name(self):
        return self.name if self.name is not None else self.platform_id

    @property
    def is_read_only(self) -> bool:
        return "@group.v.calendar.google.com" in self.platform_id


class SyncRule(UUIDBaseModel):
    source = ForeignKeyField(Calendar)
    destination = ForeignKeyField(Calendar)
    private = peewee.BooleanField()

    class Meta:
        constraints = [peewee.SQL('UNIQUE (source_id, destination_id)')]


class OAuthState(BaseModel):
    user = ForeignKeyField(User, null=True)
    state = CharField()
    kind = EnumField(enum=OAuthKind)
    session_id = UUIDField(null=True)
    tos = peewee.BooleanField(null=True)


class Session(UUIDBaseModel):
    user = ForeignKeyField(User, null=True)
    session_id = UUIDField(null=True, unique=True)


MODELS = [Session, OAuthState, SyncRule, Calendar, CalendarAccount, User]
