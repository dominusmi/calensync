import base64
import datetime
import json
import os
import uuid
from typing import Optional, List

import boto3
import google.oauth2.credentials
import google_auth_oauthlib.flow
import peewee
import starlette.responses
from google.oauth2.credentials import Credentials

from calensync import dataclass
import calensync.sqs
from calensync.api.common import ApiError, RedirectResponse
from calensync.api.service import verify_valid_sync_rule, run_initial_sync
from calensync.database.model import User, OAuthState, Calendar, OAuthKind, CalendarAccount, Session, SyncRule
from calensync.database.utils import DatabaseSession
from calensync.dataclass import PostSyncRuleBody, EventExtendedProperty, PostSyncRuleEvent
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
        raise RedirectResponse(f"{get_frontend_env()}/tos")
    logger.info(f"Verified {user.uuid}")
    return user


def credentials_to_dict(credentials: google.oauth2.credentials.Credentials):
    return json.loads(credentials.to_json())


def get_oauth_token(state: str, code: str, error: Optional[str], db: peewee.Database, session):
    state_db: OAuthState = OAuthState.get_or_none(state=state)
    if state_db is None:
        raise ApiError("Invalid state")

    if error is not None:
        msg = base64.b64encode(f"Google error: {error}".encode())
        state_db.delete_instance()
        return RedirectResponse(location=f"{get_frontend_env()}/dashboard?error_msg={msg.decode('utf-8')}")

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

    try:
        flow.fetch_token(code=code)
    except Warning:
        msg = base64.b64encode("You must give all the requested permissions")
        return RedirectResponse(location=f"{get_frontend_env()}/dashboard?error_msg={msg}")

    credentials = flow.credentials
    logger.info(credentials) if is_local() else None

    email = get_google_email(credentials)
    logger.info(email) if is_local() else None

    credentials_dict = credentials_to_dict(credentials)

    if is_login:
        with db.atomic():
            create_session_and_user(email, state_db)
        return RedirectResponse(location=f"{get_frontend_env()}/dashboard",
                                cookie={"authorization": state_db.session_id})

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
    response.set_cookie("authorization", oauth_state.session_id, secure=True, httponly=True, max_age=3600,
                        domain="127.0.0.1:8080")
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


def unsubscribe(user_id: str):
    user = User.get_or_none(uuid=user_id)
    if user:
        user.marketing = False
        user.save()
        return starlette.responses.HTMLResponse("""
                <html>
                <body>
                    <h1>You have successfully been unsubscribed.</h1> 
                    You should be redirected. If you're not, please <a href="https://calensync.live">click here</a>
                </body>
                <script>
                    window.setTimeout(function(){
                        window.location.href = "https://calensync.live";
                    }, 2500);
                </script>
                </html>""")
    else:
        logger.error(f"No user with if {user_id}")
        return starlette.responses.HTMLResponse(status_code=404)


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


if __name__ == "__main__":
    os.environ["ENV"] = "local"
    with DatabaseSession("local") as db:
        rule = SyncRule.get(uuid='1bf21cd0-112a-4bec-b4e7-7d548dbb1cea')
        run_initial_sync(rule.id)


def create_sync_rule(payload: PostSyncRuleBody, user: User, db: peewee.Database):
    """
    Verifies the input and create the SyncRule database entry. Pushes and SQS
    event which will then call run_initial_sync
    """
    with db.atomic():
        source, destination = verify_valid_sync_rule(user, payload.source_calendar_id, payload.destination_calendar_id)
        sync_rule = SyncRule(source=source, destination=destination, private=payload.private).save_new()

        event = PostSyncRuleEvent(sync_rule_id=sync_rule.id)
        sqs_event = dataclass.SQSEvent(kind=dataclass.QueueEvent.POST_SYNC_RULE, data=event)
        if is_local():
            calensync.sqs.handle_sqs_event(sqs_event, db)
        else:
            calensync.sqs.send_event(boto3.Session(), sqs_event.json())


def delete_sync_rule(user: User, sync_id: str):
    sync_rules = list(
        SyncRule.select(SyncRule.id, SyncRule.source, Calendar)
        .join(Calendar, on=(SyncRule.destination_id == Calendar.id))
        .join(CalendarAccount)
        .join(User)
        .where(SyncRule.uuid == sync_id, User.id == user.id)
    )

    if len(sync_rules) == 0:
        raise ApiError("Synchronization doesn't exist or is not owned by you", code=404)
    sync_rule: SyncRule = sync_rules[0]

    destination_wrapper = GoogleCalendarWrapper(calendar_db=sync_rule.destination)
    events = destination_wrapper.get_events(
        private_extended_properties=EventExtendedProperty.for_calendar_id(str(sync_rule.source.uuid)).to_google_dict(),
        start_date=datetime.datetime.now(),
        end_date=datetime.datetime.now() + datetime.timedelta(days=35),
        showDeleted=False
    )
    destination_wrapper.events_handler.delete([e.id for e in events])
    destination_wrapper.delete_events()

    # check if calendar has other rule sync rules, otherwise delete watch
    other_rules_same_source = list(
        SyncRule.select().where(SyncRule.source == sync_rule.source, SyncRule.id != sync_rule.id))
    if not other_rules_same_source:
        GoogleCalendarWrapper(sync_rule.source).delete_watch()

    sync_rule.delete_instance()


def get_sync_rules(user: User):
    Source = Calendar.alias()
    Destination = Calendar.alias()

    return list(
        SyncRule.select(
            SyncRule.uuid,
            Source.platform_id.alias("source"),
            Destination.platform_id.alias("destination"),
            SyncRule.private
        )
        .join(Source, on=(Source.id == SyncRule.source_id))
        .switch(SyncRule)
        .join(Destination, on=(Destination.id == SyncRule.destination_id))
        .switch(Source)
        .join(CalendarAccount)
        .where(CalendarAccount.user_id == user.id)
        .dicts()
    )
