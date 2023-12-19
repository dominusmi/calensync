import datetime
import json
import os
import uuid
from typing import Optional, Dict, List

import boto3
import google.oauth2.credentials
import google_auth_oauthlib.flow
import peewee
import starlette.responses
from google.oauth2.credentials import Credentials

from calensync import dataclass
from calensync.api.common import ApiError, RedirectResponse
from calensync.api.service import activate_calendar, deactivate_calendar
from calensync.database.model import User, OAuthState, Calendar, OAuthKind, CalendarAccount, Session
from calensync.gwrapper import get_google_email, get_google_calendars, GoogleCalendarWrapper
from calensync.log import get_logger
import calensync.paddle as paddle
from calensync.session import create_session_and_user
from calensync.utils import get_client_secret, get_scopes, get_google_sso_scopes, is_local, utcnow, get_paddle_token

logger = get_logger(__file__)


def get_host_env():
    return os.environ.get("API_ENDPOINT")


def get_frontend_env():
    return os.environ.get("FRONTEND")


def verify_session(session_id: Optional[str]) -> User:
    """ Returns the claimed email """

    if session_id is None:
        raise ApiError("Credentials missing", 403)

    elif session_id == 'null':
        raise ApiError("Credentials missing", 403)

    query = peewee.prefetch(Session.select().where(Session.session_id == session_id).limit(1), User.select())
    result: List[Session] = list(query)

    if not result:
        logger.debug(f"No session found for {session_id}")
        raise ApiError("Invalid or expired credentials", 403)

    user: User = result[0].user
    if not user.tos:
        logger.info("User has not accepted tos")
        # raise RedirectResponse("tos.html")

    return user


def credentials_to_dict(credentials: google.oauth2.credentials.Credentials):
    return json.loads(credentials.to_json())


def get_oauth_token(state: str, code: str, db: peewee.Database, session):
    state_db: OAuthState = OAuthState.get_or_none(state=state)
    if state_db is None:
        raise ApiError("Invalid state")

    client_secret = get_client_secret(session)

    is_login = (state_db.kind == OAuthKind.GOOGLE_SSO)
    logger.info(f"OAuth of kind {state_db.kind}, is_login: {is_login}")

    if is_login:
        # add calendar event
        scopes = get_google_sso_scopes()
    else:
        scopes = get_scopes()

    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        client_secret,
        scopes=scopes, state=state, redirect_uri=f'{get_host_env()}/oauth2'
    )

    flow.fetch_token(code=code)

    credentials = flow.credentials
    logger.info(credentials) if is_local() else None

    email = get_google_email(credentials)
    logger.info(email) if is_local() else None

    credentials_dict = credentials_to_dict(credentials)

    if is_login:
        with db.atomic():
            create_session_and_user(email, state_db)
        return RedirectResponse(location=f"{get_frontend_env()}/dashboard", cookie={"authorization": state_db.session_id})

    else:
        account: Optional[CalendarAccount] = CalendarAccount.get_or_none(key=email)
        if account is None:
            account = CalendarAccount(credentials=credentials_dict, user=state_db.user, key=email)
            account.save()

        else:
            if account.user == state_db.user:
                account.credentials = credentials_dict
                account.save()
            else:
                logger.error("Same calendar account key, but different user")
                raise ApiError("This calendar is associated with another account, please contact support if you need "
                               "help.")

        state_db.delete_instance()
        refresh_calendars(state_db.user, account.uuid, db)
        return RedirectResponse(f"{get_frontend_env()}/dashboard")


def received_webhook(channel_id: str, state: str, resource_id: str, token: str, db: peewee.Database):
    calendar = Calendar.get_or_none(Calendar.channel_id == channel_id)

    if calendar is None or str(calendar.token) != token:
        logger.warn(f"The token {token} does not match the database token {channel_id} ignoring.")
        return

    if calendar.resource_id is None and resource_id is not None:
        calendar.resource_id = resource_id
        calendar.save()

    if state == "sync":
        # This just means a channel was created
        logger.info("Sync signal")
        return

    if calendar is None:
        logger.warn(f"Received webhook for inexistent calendar with channel {channel_id}")
        return

    calendar.last_received = utcnow()
    calendar.save()

    if (utcnow() - calendar.last_inserted.replace(tzinfo=datetime.timezone.utc)).seconds > 1:
        # process the event immediately
        wrapper = GoogleCalendarWrapper(calendar)
        wrapper.solve_update_in_calendar()

        calendar.last_processed = utcnow()
        calendar.save()
    else:
        logger.info("Time interval too short, not updating")
        # Let google know to retry with exponential back-off
        # you may ask why do we do this? I don't know. 
        # I think there might have been some "race condition" but I can't remember
        raise ApiError(message="Service unavailable", code=503)


def prepare_calendar_oauth(user: User, db: peewee.Database, session):
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        get_client_secret(session),
        scopes=get_scopes())

    flow.redirect_uri = f'{get_host_env()}/oauth2'

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        approval_prompt='force'
    )

    with db.atomic():
        OAuthState(user=user, state=state, kind=OAuthKind.ADD_GOOGLE_ACCOUNT).save()

    return {"url": authorization_url}


def prepare_google_sso_oauth(tos: int, db: peewee.Database, boto3_session):
    """
    Function used for login / signup purposes. Creates and anonymous OAuthState model
    object to keep track of the state reason.
    """
    scopes = get_google_sso_scopes()
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        get_client_secret(boto3_session),
        scopes=scopes)

    logger.info(f"Scopes: {scopes}")
    flow.redirect_uri = f'{get_host_env()}/oauth2'

    authorization_url, state = flow.authorization_url(
        access_type='offline')

    with db.atomic():
        oauth_state = OAuthState(state=state, kind=OAuthKind.GOOGLE_SSO, session_id=uuid.uuid4())
        if tos:
            oauth_state.tos = True
        oauth_state.save()

    response = starlette.responses.JSONResponse(content={"url": authorization_url})
    response.set_cookie("authorization", oauth_state.session_id, secure=True, httponly=True, max_age=3600, domain="127.0.0.1:8080")
    return response


def get_calendar_accounts(user: User, db: peewee.Database):
    accounts: List[CalendarAccount] = list(CalendarAccount.select().join(User).where(User.id == user.id))
    return [{"key": account.key, "uuid": account.uuid} for account in accounts]


def get_calendars(user: User, account_id: str, db: peewee.Database) -> List[Calendar]:
    calendars: List[Calendar] = list(Calendar.select()
                                     .join(CalendarAccount)
                                     .join(User)
                                     .where(User.id == user.id, CalendarAccount.uuid == account_id))

    return calendars


def get_calendar(user: User, calendar_id: str, db: peewee.Database) -> Calendar:
    calendars = peewee.prefetch(
        Calendar.select().where(Calendar.uuid == calendar_id),
        CalendarAccount.select(),
        User.select()
    )

    calendar_user = next((c.account.user for c in calendars))

    if calendar_user is None or calendar_user.id != user.id:
        raise ApiError("Calendar not found", 404)

    return calendars[0]


def refresh_calendars(user: User, account_id: str, db: peewee.Database):
    """
    Gets all the calendars for the account, and saves the new one to the db.
    Returns a list of the calendars
    """
    account: CalendarAccount = (
        CalendarAccount.select().join(User)
        .where(User.id == User.id, CalendarAccount.uuid == account_id)
    ).get_or_none()

    if account is None:
        raise ApiError("Account doesn't exist or user doesn't have access to it")

    credentials = Credentials.from_authorized_user_info(account.credentials)
    calendars = get_google_calendars(credentials)

    calendars_db: List[Calendar] = list(
        Calendar.select()
        .join(CalendarAccount)
        .join(User)
        .where(User.id == user.id, CalendarAccount.uuid == account_id)
    )

    new_calendars_db = []
    platform_ids = {cdb.platform_id for cdb in calendars_db}
    for calendar in calendars:
        if calendar.id in platform_ids:
            continue

        new_calendars_db.append(
            Calendar(account=account, platform_id=calendar.id)
        )

    with db.atomic():
        for new_calendar in new_calendars_db:
            new_calendar.save()

    calendars_db.extend(new_calendars_db)
    return [{"uuid": c.uuid, "name": c.friendly_name, "active": c.active} for c in calendars_db]


def patch_calendar(user_id: int, calendar_uuid: str, kind: dataclass.CalendarStateEnum, db: peewee.Database):
    query = (
        Calendar.select().join(CalendarAccount).join(User)
        .where(User.id == user_id, Calendar.uuid == calendar_uuid)
    )
    calendars: List[Calendar] = peewee.prefetch(query, CalendarAccount)

    if len(calendars) == 0:
        raise ApiError("The calendar does not exist or you dot not have permissions to access it")

    if kind == dataclass.CalendarStateEnum.ACTIVE:
        logger.info(f"Activating {calendars[0].uuid}")
        return activate_calendar(calendars[0])

    elif kind == dataclass.CalendarStateEnum.INACTIVE:
        logger.info(f"De-activating {calendars[0].uuid}")
        return deactivate_calendar(calendars[0])


def delete_account(user: User, account_id: str):
    calendars: List[Calendar] = list(Calendar.select()
                                     .join(CalendarAccount)
                                     .join(User)
                                     .where(User.id == user.id, CalendarAccount.uuid == account_id))
    for calendar in calendars:
        deactivate_calendar(calendar)
        calendar.delete_instance()
        CalendarAccount.get(uuid=account_id).delete_instance()


def accept_tos(user: User, db: peewee.Database):
    user.tos = utcnow()
    user.save()
    return


def paddle_verify_transaction(user: User, transaction_id: str, session: boto3.Session):
    logger.info(f"Verifying transaction {transaction_id}")
    response = paddle.get_transaction(transaction_id, get_paddle_token(session))
    if response.status_code != 200:
        logger.error(f"Couldn't confirm transaction {transaction_id} for user {user.uuid}")
        raise ApiError("Couldn't confirm payment", code=500)

    data = response.json()["data"]
    print(data)
    if data["status"] not in ["paid", "completed"]:
        raise ApiError(f"The transaction is not completed. Status: {data['status']}")

    customer_id = data["customer_id"]
    subscription_id = data["subscription_id"]

    if user.customer_id is not None and user.customer_id != customer_id:
        logger.error(f"User {user.uuid} had customer_id {user.customer_id} and now has {customer_id}")
        user.customer_id = customer_id

    if user.customer_id is None:
        user.customer_id = customer_id

    if user.transaction_id is not None:
        logger.info(f"User {user.uuid} transaction updated from {user.transaction_id} to {transaction_id}")
    user.transaction_id = transaction_id

    if user.subscription_id is not None:
        # apparently, the subscription_id is null if I buy another product after the first one
        # this shouldn't be possible, but good to know
        logger.info(f"User {user.uuid} subscription updated from {user.subscription_id} to {subscription_id}")
    user.subscription_id = subscription_id

    user.save()
    return


def get_paddle_subscription(user: User, session: boto3.Session):
    response = paddle.get_subscription(user.subscription_id, get_paddle_token(session))
    return response


def process_calendars():
    now = datetime.datetime.utcnow()
    query = Calendar.select().where(
        now - datetime.timedelta(seconds=60) > Calendar.last_inserted,
        Calendar.last_received > Calendar.last_processed
    )
    for calendar in query:
        gcalendar = GoogleCalendarWrapper(calendar)
        gcalendar.solve_update_in_calendar()
        calendar.last_processed = datetime.datetime.utcnow()
        calendar.save()
