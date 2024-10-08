from __future__ import annotations

import datetime
import json
import os
import random
from time import sleep
import pathlib

import boto3
import googleapiclient.errors
import peewee

from calensync.log import get_logger

logger = get_logger(__file__)


def get_env():
    return os.environ["ENV"]


def get_client_secret(session=None):
    if is_local():
        path = pathlib.Path(__file__).parent.parent.parent.resolve()
        with open(path.joinpath("client_secret.json")) as f:
            return json.load(f)
    else:
        client = session.client("secretsmanager")
        response = client.get_secret_value(SecretId="calensync-google-secret")
        return json.loads(response['SecretString'])


def get_profile_and_calendar_scopes():
    return [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        'https://www.googleapis.com/auth/calendar.calendarlist.readonly',
        'https://www.googleapis.com/auth/calendar.events',
    ]


def get_profile_scopes():
    return [
        "https://www.googleapis.com/auth/userinfo.email",
        # "https://www.googleapis.com/auth/userinfo.profile",
        "openid"
    ]


def get_api_url() -> str:
    return os.environ["API_ENDPOINT"]


def is_local() -> bool:
    env = get_env()
    if env in ("local", "test"):
        return True
    return False


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def get_paddle_token(session: boto3.Session = None):
    if is_local():
        return os.environ["PADDLE_TOKEN"]

    env = get_env()
    if (token := os.environ.get("PADDLE_TOKEN")) is not None:
        return token
    client = session.client("secretsmanager")
    response = client.get_secret_value(SecretId="paddle_token")
    secret_value = json.loads(response['SecretString'])
    token = secret_value[env]
    os.environ["PADDLE_TOKEN"] = token
    return token


def get_product_id():
    return os.environ["PRODUCT_ID"]


def datetime_to_google_time(dt: datetime.datetime) -> str:
    return dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z"


def prefetch_get_or_none(query, *sub_queries):
    result = peewee.prefetch(query.limit(1), *sub_queries)
    if result:
        return result[0]
    return None


def format_calendar_text(original, template):
    if original is None:
        return original
    return template.replace("%original%", original)


class BackoffException(Exception):
    def __init__(self, delay: int):
        self.delay = delay
        super().__init__()


def google_error_handling_with_backoff(function, calendar_db=None):
    for i in range(4):
        try:
            return function()
        except googleapiclient.errors.HttpError as e:
            # the reason is always set to something, but can be a text (why the fuck google?) or an enum like text
            # normally there's always a json representation
            reason = e.reason
            if e.resp.get('content-type', '').startswith('application/json'):
                errors = json.loads(e.content).get('error', {}).get('errors', {})
                if errors:
                    reason = errors[0].get('reason')
                else:
                    logger.error(f"Couldn't parse error: {e.content}")

            if e.status_code == 403:
                if e.reason == "You need to have writer access to this calendar.":
                    if calendar_db:
                        calendar_db.paused = utcnow()
                        calendar_db.paused_reason = e.reason
                        calendar_db.save()
                    logger.info(f"Did not insert event - You need to have writer access to this calendar on "
                                f"calendar {calendar_db.id}")
                    return False

            if (
                    e.status_code == 429
                    or (e.status_code == 403 and reason in ["userRateLimitExceeded", 'Rate Limit Exceeded',
                                                            "rateLimitExceeded", "quotaExceeded",
                                                            'Calendar usage limits exceeded.'])
            ):
                sleep_delay = 2 ** i + random.random()
                logger.info(f"Sleeping for {sleep_delay} seconds")
                sleep(sleep_delay)
            else:
                logger.info(f"Uncaught google error in backoff: {e}. Reason parsed: {reason}")
                raise e

    raise BackoffException(60)


def replace_timezone(dt: datetime.datetime):
    return dt.replace(tzinfo=datetime.timezone.utc)


INVALID_GRANT_ERROR = 'invalid_grant'
