import datetime
import functools
import json
import os
import random
import uuid
from pathlib import Path
from time import sleep

import boto3
import pytest
from _pytest.fixtures import fixture
from moto import mock_aws

from calensync.database.model import User, CalendarAccount, Calendar, EmailDB
from calensync.database.utils import reset_db, DatabaseSession
from calensync.dataclass import GoogleEvent
from calensync.secure import encrypt_credentials

os.environ["ENV"] = "test"
os.environ["AWS_ACCESS_KEY_ID"] = "123"


def wrap_reset_db(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        reset_db()
        return func(*args, **kwargs)

    return wrapper


@fixture
def db():
    with DatabaseSession("test") as db:
        reset_db()
        return db


@fixture
def user(db):
    return User().save_new()


@fixture
def email1_1(user):
    return EmailDB(user=user, email="test1@test.com").save_new()


@fixture
def account1_1(db, user, email1_1):
    return CalendarAccount(user=user, key=email1_1.email,
                           encrypted_credentials=encrypt_credentials({}, None)).save_new()


@fixture
def calendar1_1(db, account1_1):
    return Calendar(account=account1_1, platform_id="platform1", name="name1", active=False).save_new()


@fixture
def account1_2(db, user):
    return CalendarAccount(user=user, key="test2", encrypted_credentials=encrypt_credentials({}, None)).save_new()


@fixture
def calendar1_2(db, account1_2):
    return Calendar(account=account1_2, platform_id="platform2", name="name2", active=False).save_new()


@fixture
def user2(db):
    return User(email="test1@test.com").save_new()


@fixture
def account1_1_2(db, user):
    return CalendarAccount(user=user, key="test2_1", encrypted_credentials=encrypt_credentials({}, None)).save_new()


@fixture
def calendar1_1_2(db, account1_1):
    return Calendar(account=account1_1, platform_id="platform2_1", name="name1", active=False).save_new()


@fixture
def account1_1_3(db, user):
    return CalendarAccount(user=user, key="test2_2", encrypted_credentials=encrypt_credentials({}, None)).save_new()


@fixture
def calendar1_2_2(db, account1_2):
    return Calendar(account=account1_2, platform_id="platform2_2", name="name2", active=False).save_new()


def uuid4():
    return str(uuid.uuid4())


def random_dates():
    start = datetime.datetime.now() + datetime.timedelta(days=random.randint(0, 15), hours=random.randint(0, 24))
    end = start + datetime.timedelta(hours=random.randint(0, 2), minutes=random.randint(30, 59))
    return start, end


@pytest.fixture
def events_fixture():
    with open(Path(__file__).parent.joinpath("list_events.json")) as f:
        data = json.load(f)

    return data


@fixture
def boto_session():
    with mock_aws():
        yield boto3.Session(aws_secret_access_key="123", aws_access_key_id="123", region_name='us-east-1')


@fixture
def queue_url(boto_session):
    sqs = boto_session.client('sqs')
    response = sqs.create_queue(QueueName='Test')
    queue_url = response["QueueUrl"]
    os.environ["SQS_QUEUE_URL"] = queue_url
    return queue_url
