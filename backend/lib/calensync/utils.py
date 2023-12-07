import datetime
import json
import os


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


def get_scopes():
    return [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        'https://www.googleapis.com/auth/calendar.calendarlist.readonly',
        # 'https://www.googleapis.com/auth/calendar.settings.readonly',
        # 'https://www.googleapis.com/auth/calendar.freebusy',
        'https://www.googleapis.com/auth/calendar.calendars',
        'https://www.googleapis.com/auth/calendar.calendars.readonly',
        'https://www.googleapis.com/auth/calendar.events',
        'https://www.googleapis.com/auth/calendar.events.owned',
        'https://www.googleapis.com/auth/calendar.events.readonly'
    ]


def get_google_sso_scopes():
    return [
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
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


def get_paddle_token():
    return os.environ["PADDLE_TOKEN"]


def get_product_id():
    return os.environ["PRODUCT_ID"]
