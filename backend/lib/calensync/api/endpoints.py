import base64
import datetime
import json
import os
import uuid
from typing import Optional, List

import boto3
import google.oauth2.credentials
import peewee
import starlette.responses

import calensync.api.service
import calensync.paddle as paddle
import calensync.sqs
from calensync import dataclass
from calensync.api.common import ApiError, RedirectResponse, encode_query_message
from calensync.api.response import PostMagicLinkResponse
from calensync.api.service import verify_valid_sync_rule, merge_users, handle_refresh_existing_calendar, \
    handle_delete_sync_rule_event
from calensync.database.model import User, OAuthState, Calendar, OAuthKind, CalendarAccount, Session, SyncRule, EmailDB, \
    MagicLinkDB
from calensync.dataclass import PostSyncRuleBody, PostSyncRuleEvent
from calensync.gwrapper import get_google_email, get_google_calendars
from calensync.log import get_logger
from calensync.secure import encrypt_credentials, decrypt_credentials
from calensync.utils import get_client_secret, get_profile_and_calendar_scopes, get_profile_scopes, is_local, utcnow, \
    get_paddle_token, prefetch_get_or_none, replace_timezone

if os.environ.get("MOCK_GOOGLE"):
    from unittest.mock import MagicMock
    from calensync.dataclass import GoogleCalendar

    google_auth_oauthlib = MagicMock()

    get_google_email = lambda x: f"{uuid.uuid4()}@test.com"

    google.oauth2.credentials.Credentials = MagicMock()
    google.oauth2.credentials.Credentials.from_authorized_user_info.return_value = MagicMock()
    get_google_calendars = lambda credentials: [
        GoogleCalendar(kind="", id=str(uuid.uuid4()), name=f"name-{str(uuid.uuid4())[:5]}"),
        GoogleCalendar(kind="", id=str(uuid.uuid4()), name=f"name-{str(uuid.uuid4())[:5]}")
    ]


    def new_flow(*args, **kwargs):
        flow_manager = MagicMock()
        state = str(uuid.uuid4())
        flow_manager.authorization_url.return_value = (f"http://127.0.0.1:8000/oauth2?state={state}", state)
        # make it return something that has a to_dict() function that returns a dictionary of credentials
        flow_manager.credentials.to_json.return_value = json.dumps({"whatever": "dummy"})

        return flow_manager


    google_auth_oauthlib.flow.Flow.from_client_config = new_flow


else:
    import google_auth_oauthlib.flow

logger = get_logger(__file__)


def get_host_env():
    return os.environ.get("API_ENDPOINT")


def get_frontend_env():
    return os.environ.get("FRONTEND")


def verify_session(session_id: Optional[str]) -> User:
    """ Returns the claimed email """

    if session_id is None:
        raise ApiError("Credentials missing", 404)

    elif session_id == 'null':
        raise ApiError("Credentials missing", 404)

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


def handle_signin_signup(state_db: OAuthState, email: str):
    email_db = EmailDB.get_or_none(email=email)
    session_id = state_db.session_id
    cookie = {"authorization": str(session_id)}
    state_db.delete_instance()
    logger.info(f"State DB session id: {session_id}")

    if state_db.user is None:
        if email_db is None:
            # error case
            logger.info("Login #1")
            user = User(tos=utcnow()).save_new()
            EmailDB(email=email, user=user).save_new()
            Session(session_id=session_id, user=user).save_new()
            return RedirectResponse(location=f"{get_frontend_env()}/dashboard", cookie=cookie)
        else:
            logger.info("Login #2")
            # normal case, create session and return
            Session(session_id=session_id, user=email_db.user).save_new()
            return RedirectResponse(location=f"{get_frontend_env()}/dashboard", cookie=cookie)

    else:
        if email_db is None:
            logger.info("Login #3")
            EmailDB(email=email, user=state_db.user).save_new()
            Session(session_id=session_id, user=state_db.user).save_new()
            return RedirectResponse(location=f"{get_frontend_env()}/dashboard", cookie=cookie)
        else:
            if email_db.user == state_db.user:
                logger.info("Login #4")
                Session(session_id=session_id, user=email_db.user).save_new()
                return RedirectResponse(location=f"{get_frontend_env()}/dashboard", cookie=cookie)
            else:
                logger.info("Login #5")
                # return email-based session
                Session(session_id=session_id, user=email_db.user).save_new()
                return RedirectResponse(location=f"{get_frontend_env()}/dashboard", cookie=cookie)


def handle_add_calendar(state_db: OAuthState, email: str, credentials_dict: dict, db, boto_session: boto3.Session):
    """
    This function create the CalendarAccount object for a new email, as well as calling refresh_calendars.
    There are a couple of tricky cases:
    The normal case is the following: the state db is connected to a user, and we simply add
    the email to that user and be done. However, there are other possible cases, notably someone
    adding an account that was already added previously. In this case, we need to merge the two accounts together


    :param state_db: database model for the Google OAuth State
    :param email: email connected to the Google account which made the OAuth request
    :param credentials_dict: credentials for calendar permissions related to this email
    :param db: database connection
    :param boto_session: boto3 session, used to get the secret key to decrypt credentials
    """
    email_db = prefetch_get_or_none(
        EmailDB.select().where(EmailDB.email == email),
        User.select()
    )

    other_user = None
    delete_secondary_user = False
    main_user = None
    if state_db.user is not None:
        main_user = state_db.user
    if email_db is not None:
        main_user = email_db.user

    if email_db is None:
        if state_db.user is None:
            # this should not be possible
            logger.error("CODEREF #12497")
            msg = encode_query_message(f"You do not appear to have an account, please signup")
            raise RedirectResponse(location=f"{get_frontend_env()}/login?error_msg={msg}")
        else:
            EmailDB(email=email, user=state_db.user).save()

    else:
        if state_db.user is not None and email_db.user != state_db.user:
            state_user_db = prefetch_get_or_none(
                User.select().where(User.id == state_db.user_id),
                EmailDB.select()
            )
            if len(state_user_db.emails) > 0:
                # this means multiple users with at least one email
                # logger.error(f"Users with multiple emails: {email_db.user} and {state_db.user}")
                # msg = encode_query_message(
                #     f"This email is already associated. If you believe an error occured, let us know "
                #     f"by email (support@calensync.live) or with the feedback form.")
                # return RedirectResponse(location=f"{get_frontend_env()}/dashboard?error_msg={msg}")
                # We need to merge the two users
                main_user, other_user = merge_users(email_db.user, state_db.user, db)
            else:
                other_user = state_db.user
            delete_secondary_user = True
            # else:
            #     This means the state_db user can be thought as temporary (since it has no emails attached)
            # therefore we use the email user for the rest of the process
            # user = email_db.user
            # delete_state_user = True
        else:
            main_user = email_db.user

    account_added = False
    account: Optional[CalendarAccount] = CalendarAccount.get_or_none(key=email)

    encrypted_credentials = encrypt_credentials(credentials_dict, boto_session)
    if account is None:
        account = CalendarAccount(encrypted_credentials=encrypted_credentials, user=main_user, key=email)
        account.save()
        account_added = True

    else:
        account.encrypted_credentials = encrypted_credentials
        account.save()

    state_db.delete_instance()
    if delete_secondary_user and other_user is not None:
        other_user.delete_instance()

    refresh_calendars(main_user, account.uuid, db, boto_session)

    Session(session_id=state_db.session_id, user=main_user).save_new()

    redirect = f"{get_frontend_env()}/dashboard"
    if account_added:
        redirect = f"{redirect}?added_calendar=true"
    return RedirectResponse(location=redirect)


def get_oauth_token(state: str, code: str, error: Optional[str], db: peewee.Database, boto_session: boto3.Session):
    state_db: OAuthState = OAuthState.get_or_none(state=state)
    if state_db is None:
        raise ApiError("Invalid state")

    if error is not None:
        msg = base64.b64encode(f"Google error: {error}".encode())
        state_db.delete_instance()
        return RedirectResponse(location=f"{get_frontend_env()}/dashboard?error_msg={msg.decode('utf-8')}")

    client_secret = get_client_secret(boto_session)

    is_login = (state_db.kind == OAuthKind.GOOGLE_SSO)
    logger.info(f"OAuth of kind {state_db.kind}, is_login: {is_login}")

    if is_login:
        scopes = get_profile_scopes()
    else:
        scopes = get_profile_and_calendar_scopes()

    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        client_secret,
        scopes=scopes, state=state, redirect_uri=f'{get_host_env()}/oauth2'
    )

    try:
        flow.fetch_token(code=code)
    except Warning:
        msg = encode_query_message("You must give all the requested permissions")
        response = RedirectResponse(location=f"{get_frontend_env()}/dashboard?error_msg={msg}").to_response()
        if len(state_db.user.emails) == 0:
            response.set_cookie(key="authorization", max_age=-1)
        return response

    credentials = flow.credentials
    logger.info(credentials) if is_local() else None

    email = get_google_email(credentials)
    logger.info(email) if is_local() else None

    credentials_dict = credentials_to_dict(credentials)

    if is_login:
        return handle_signin_signup(state_db, email)
    else:
        return handle_add_calendar(state_db, email, credentials_dict, db, boto_session)


def prepare_calendar_oauth_without_user(db: peewee.Database, session):
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        get_client_secret(session),
        scopes=get_profile_and_calendar_scopes())

    flow.redirect_uri = f'{get_host_env()}/oauth2'

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        approval_prompt='force'
    )

    with db.atomic():
        user = User(tos=utcnow()).save_new()
        oauth_state = OAuthState(state=state, kind=OAuthKind.ADD_GOOGLE_ACCOUNT, user=user)
        oauth_state.save()

    response = starlette.responses.JSONResponse(
        content={"url": authorization_url},
    )
    response.set_cookie("authorization", oauth_state.session_id, secure=True, httponly=True)
    return response


def prepare_calendar_oauth(user: User, db: peewee.Database, session):
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        get_client_secret(session),
        scopes=get_profile_and_calendar_scopes())

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
    scopes = get_profile_scopes()
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        get_client_secret(boto3_session),
        scopes=scopes)

    logger.info(f"Scopes: {scopes}")
    flow.redirect_uri = f'{get_host_env()}/oauth2'

    logger.info("Getting authorization")
    authorization_url, state = flow.authorization_url(
        access_type='offline')

    logger.info("Opening db connection")
    with db.atomic():
        logger.info("Saving state in database")
        oauth_state = OAuthState(state=state, kind=OAuthKind.GOOGLE_SSO, session_id=uuid.uuid4())
        if tos:
            oauth_state.tos = True
        oauth_state.save()

    logger.info("Preparing response")
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


def resync_calendar(user: User, calendar_uuid: str, boto_session: boto3.Session, db: peewee.Database):
    calendar = list(
        peewee.prefetch(
            Calendar.select()
            .join(CalendarAccount)
            .join(SyncRule, on=(SyncRule.source_id == Calendar.id))
            .where(
                Calendar.uuid == calendar_uuid,
                CalendarAccount.user_id == user.id
            )
            .limit(1),
            SyncRule.select()
        )
    )
    if not calendar:
        raise ApiError("Calendar doesn't exist or is not owned by you", 404)
    calendar = calendar[0]

    if calendar.last_resync is not None and (utcnow() - replace_timezone(calendar.last_resync)).total_seconds() / 60 < 30:
        raise ApiError("Syncing can take a few minutes time! You can only trigger a manual re-sync once every 30 "
                       "minutes", 429)

    logger.info(f"Found {len(calendar.source_rules)} to resync")
    for sync_rule in calendar.source_rules:
        event = PostSyncRuleEvent(sync_rule_id=sync_rule.id)
        sqs_event = dataclass.SQSEvent(kind=dataclass.QueueEvent.POST_SYNC_RULE, data=event)
        if is_local():
            calensync.api.service.handle_sqs_event(sqs_event, db, boto_session)
        else:
            calensync.sqs.send_event(boto3.Session(), sqs_event.json())


def refresh_calendars(user: User, account_uuid: str, db: peewee.Database, boto_session: boto3.Session):
    """
    Gets all the calendars for the account, and saves the new one to the db.
    Returns a list of the calendars
    """
    account: CalendarAccount = (
        CalendarAccount.select().join(User)
        .where(User.id == User.id, CalendarAccount.uuid == account_uuid)
    ).get_or_none()

    if account is None:
        raise ApiError("Account doesn't exist or user doesn't have access to it")

    credentials_dict = decrypt_credentials(account.encrypted_credentials, boto_session)
    credentials = google.oauth2.credentials.Credentials.from_authorized_user_info(credentials_dict)
    calendars = get_google_calendars(credentials)

    calendars_db: List[Calendar] = list(
        Calendar.select()
        .join(CalendarAccount)
        .join(User)
        .where(User.id == user.id, CalendarAccount.uuid == account_uuid)
    )

    new_calendars_db = []
    platform_ids = {cdb.platform_id: cdb for cdb in calendars_db}
    for calendar in calendars:
        name = (calendar.summary or calendar.id)
        if calendar.id in platform_ids:
            calendar_db: Calendar = platform_ids[calendar.id]
            handle_refresh_existing_calendar(calendar, calendar_db, name)
        else:
            readonly = (calendar.accessRole == 'reader')
            new_calendars_db.append(
                Calendar(account=account, platform_id=calendar.id, name=name, readonly=readonly)
            )

    with db.atomic():
        for new_calendar in new_calendars_db:
            new_calendar.save()

    calendars_db.extend(new_calendars_db)
    return [{"uuid": c.uuid, "name": c.friendly_name} for c in calendars_db]


def delete_account(user: User, account_id: str):
    calendars: List[Calendar] = list(Calendar.select()
                                     .join(CalendarAccount)
                                     .join(User)
                                     .where(User.id == user.id, CalendarAccount.uuid == account_id))
    for calendar in calendars:
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


def create_sync_rule(payload: PostSyncRuleBody, user: User, boto_session: boto3.Session, db: peewee.Database):
    """
    Verifies the input and create the SyncRule database entry. Pushes and SQS
    event which will then call run_initial_sync
    """
    if len(payload.summary) == 0:
        raise ApiError("Title cannot be empty", 400)
    with db.atomic():
        source, destination = verify_valid_sync_rule(user, payload.source_calendar_id, payload.destination_calendar_id)
        sync_rule = SyncRule(source=source, destination=destination, summary=payload.summary,
                             description=payload.description).save_new()

        calensync.api.service.run_initial_sync(sync_rule.id, boto_session, db)


def delete_sync_rule(user: User, sync_uuid: str, boto_session, db):
    with db.atomic():
        sync_rules = list(
            SyncRule.select(SyncRule.id, SyncRule.source, Calendar)
            .join(Calendar, on=(SyncRule.destination_id == Calendar.id))
            .join(CalendarAccount)
            .join(User)
            .where(SyncRule.uuid == sync_uuid, User.id == user.id)
        )

        if len(sync_rules) == 0:
            raise ApiError("Synchronization doesn't exist or is not owned by you", code=404)
        sync_rule: SyncRule = sync_rules[0]

        handle_delete_sync_rule_event(sync_rule.id, boto_session, db)


def get_sync_rules(user: User):
    Source = Calendar.alias()
    Destination = Calendar.alias()

    return list(
        SyncRule.select(
            SyncRule.uuid,
            Source.name.alias("source"),
            Source.platform_id.alias("source_id"),
            Destination.name.alias("destination"),
            Destination.platform_id.alias("destination_id"),
            SyncRule.summary,
            SyncRule.description
        )
        .join(Source, on=(Source.id == SyncRule.source_id))
        .switch(SyncRule)
        .join(Destination, on=(Destination.id == SyncRule.destination_id))
        .switch(Source)
        .join(CalendarAccount)
        .where(CalendarAccount.user_id == user.id)
        .dicts()
    )


def reset_user(caller: User, user_uuid: str, boto_session: boto3.Session, db):
    if not caller.is_admin:
        raise ApiError("Forbidden", 403)
    user = User.get_or_none(uuid=user_uuid)
    if user is None:
        return

    sync_rules = get_sync_rules(user)
    for rule in sync_rules:
        delete_sync_rule(user, rule["uuid"], boto_session, db)


def handle_post_magic_link(user_db: User) -> PostMagicLinkResponse:
    links = list(MagicLinkDB.select().where(MagicLinkDB.user_id == user_db.id))
    if links:
        expiration = utcnow() - datetime.timedelta(days=1)
        for expired_link in filter(lambda x: replace_timezone(x.date_created) < expiration, links):
            logger.info(f"Deleting link {expired_link.id}")
            expired_link.delete_instance()

        valid_links = list(filter(lambda x: replace_timezone(x.date_created) > expiration, links))
        if valid_links:
            return PostMagicLinkResponse(uuid=str(valid_links[0].uuid))

    magic_link = MagicLinkDB(user=user_db).save_new()
    return PostMagicLinkResponse(uuid=str(magic_link.uuid))


def handle_use_magic_link(link_uuid: str):
    try:
        magic_link = list(peewee.prefetch(
            MagicLinkDB.select().where(MagicLinkDB.uuid == link_uuid).limit(1),
            User.select()
        ))
    except Exception:
        msg = encode_query_message(f"The magic link is invalid")
        return RedirectResponse(f"https://calensync.live/login?error_msg={msg}")

    if not magic_link:
        msg = encode_query_message(f"The magic link is invalid")
        return RedirectResponse(f"https://calensync.live/login?error_msg={msg}")

    magic_link = magic_link[0]
    if replace_timezone(magic_link.date_created) < utcnow() - datetime.timedelta(days=1):
        msg = encode_query_message(f"The magic link has expired")
        return RedirectResponse(f"https://calensync.live/login?error_msg={msg}")

    magic_link.used += 1
    magic_link.save()
    session = Session(user=magic_link.user).save_new()
    cookie = {"authorization": str(session.session_id)}
    return RedirectResponse(location=f"{get_frontend_env()}/dashboard", cookie=cookie)
