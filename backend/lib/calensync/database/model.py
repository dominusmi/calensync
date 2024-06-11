from __future__ import annotations

import enum
import uuid
from abc import ABC
from typing import Type, TypeVar, Iterable, List, Optional

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

    def __init__(self, enum_type: Type[enum.Enum], *args, **kwargs):
        super(IntegerField, self).__init__(*args, **kwargs)
        self.enum = enum_type

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
        return super().save(*args, **kwargs)

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
    is_admin = peewee.BooleanField(default=False)
    tos = peewee.DateTimeField(default=None, null=True)
    customer_id = CharField(null=True, default=None)
    transaction_id = CharField(null=True, default=None)
    subscription_id = CharField(null=True, default=None)
    marketing = peewee.BooleanField(default=True)
    last_email_sent = peewee.DateTimeField(default=None, null=True)
    # deprecated
    email = CharField(null=True, default=None)

    @staticmethod
    def from_email(email: str) -> Optional[User]:
        emails = list(
            EmailDB.select(User).join(User)
            .where(EmailDB.email == email)
            .limit(1)
        )
        if emails:
            return emails[0].user
        return None


class EmailDB(BaseModel):
    user_id: int
    email = peewee.CharField(unique=True)
    user = peewee.ForeignKeyField(User, backref='emails')

    class Meta:
        table_name = "email"


class CalendarAccount(UUIDBaseModel):
    user_id: int
    user = ForeignKeyField(User, backref='accounts')
    key = CharField()
    credentials = JSONField(null=True)
    encrypted_credentials = peewee.TextField()

    class Meta:
        constraints = [peewee.SQL('UNIQUE (user_id, key)')]


class Calendar(UUIDBaseModel):
    account_id: int
    account = ForeignKeyField(CalendarAccount, backref='calendars')
    platform_id = CharField(help_text="This is the id provided by the service (e.g. the google id for the calendar)")
    name = CharField(null=True)
    channel_id = UUIDField(default=uuid.uuid4)
    resource_id = CharField(null=True)
    token = UUIDField(default=uuid.uuid4)
    expiration = DateTimeField(null=True)
    last_sync = DateTimeField(null=True)
    last_inserted = DateTimeField(default=utcnow)
    # last received and process alternate, basically each time an event is received,
    # last processed <- last received and
    # last received <- now
    # this allows us to always cover the entire timeline, and be able to set a good updateMin
    last_received = DateTimeField(default=utcnow)
    last_processed = DateTimeField(default=utcnow)
    last_resync = DateTimeField(default=utcnow)
    paused = DateTimeField(null=True, default=None)
    paused_reason = CharField(null=True, default=None)
    readonly = peewee.BooleanField(default=False)

    @property
    def friendly_name(self):
        return self.name if self.name is not None else self.platform_id

    @property
    def is_read_only(self) -> bool:
        return bool(self.readonly)

    class Meta:
        constraints = [peewee.SQL('UNIQUE (platform_id, account_id)')]


# deprecated
class Event(BaseModel):
    calendar_id: int
    calendar = ForeignKeyField(Calendar,
                               help_text="Calendar of this particular copy of the event (not the original calendar)",
                               backref="events")
    source = ForeignKeyField('self', null=True, default=None)
    event_id = CharField(null=False, unique=True)
    start = DateTimeField(null=False)
    end = DateTimeField(null=False)
    deleted = peewee.BooleanField(default=False)

    @staticmethod
    def get_self_reference_query():
        """
        WARNING: do not use this in conjuction with prefetch, it doesn't work. If you
        need to use prefetch, then you can't use this function but instead but do the
        aliasing in the same scope
        """
        SourceEvent = Event.alias()
        return (
            Event
            .select().join(SourceEvent, on=(Event.source == SourceEvent.id))
        ), SourceEvent


class SyncRule(UUIDBaseModel):
    source_id: int
    destination_id: int
    source = ForeignKeyField(Calendar, backref="source_rules")
    destination = ForeignKeyField(Calendar, backref="destination_rules")
    summary = CharField(null=True, default=None)
    description = CharField(null=True, default=None)
    deleted: bool = peewee.BooleanField(default=False)

    class Meta:
        constraints = [peewee.SQL('UNIQUE (source_id, destination_id)')]


class OAuthState(BaseModel):
    user_id: int
    user = ForeignKeyField(User, null=True)
    state = CharField()
    kind = EnumField(enum_type=OAuthKind)
    session_id = UUIDField(null=True, default=uuid.uuid4)
    tos = peewee.BooleanField(null=True)


class Session(BaseModel):
    user_id: int
    user = ForeignKeyField(User, null=True)
    session_id = UUIDField(null=True, unique=True, default=uuid.uuid4)


class MagicLinkDB(UUIDBaseModel):
    user_id: int
    user = ForeignKeyField(User)
    used = IntegerField(default=0)


MODELS = [MagicLinkDB, Session, OAuthState, EmailDB, SyncRule, Calendar, CalendarAccount, User]
