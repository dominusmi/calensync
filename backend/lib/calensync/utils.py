from __future__ import annotations

import datetime
import json
import os

import boto3


def get_env():
    return os.environ["ENV"]


def get_client_secret(session=None):
    if is_local():
        import pathlib
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
    if env == "local" or env == "test":
        return True
    return False


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def get_paddle_token(session: boto3.Session = None):
    env = get_env()
    if env == "test" or env == "local":
        return os.environ["PADDLE_TOKEN"]

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
