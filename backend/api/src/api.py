from typing import Annotated, Union, Dict
import os

import boto3
import starlette.responses
from fastapi import FastAPI, Request, Query, Body, Cookie, Header
from fastapi.middleware.cors import CORSMiddleware

from mangum import Mangum

import calensync.api.service
from calensync import sqs
from calensync.api.common import format_response, ApiError
import calensync.api.endpoints as edp
from calensync.api.response import PostMagicLinkResponse
from calensync.database.utils import DatabaseSession
from calensync.dataclass import GoogleWebhookEvent, SQSEvent, QueueEvent, PostSyncRuleBody, PatchSyncRuleBody
from calensync.log import get_logger
from calensync.utils import get_env, utcnow

app = FastAPI(title="Calensync")  # Here is the magic
logger = get_logger("api")


@app.post("/webhook")
@format_response
def post__webhook(event: Request):
    channel_id = event.headers["X-Goog-Channel-Id"]
    token = event.headers["X-Goog-Channel-Token"]
    state = event.headers["X-Goog-Resource-State"]
    resource_id = event.headers.get("X-Goog-Resource-Id")
    with DatabaseSession(os.environ["ENV"]) as db:
        webhook_event = GoogleWebhookEvent(channel_id=channel_id, token=token, state=state, resource_id=resource_id)
        sqs_event = SQSEvent(kind=QueueEvent.GOOGLE_WEBHOOK, data=webhook_event)
        if get_env() in ["prod", "dev"]:
            sqs.send_event(boto3.session.Session(), sqs_event.json())
        else:
            calensync.api.service.handle_sqs_event(sqs_event, db, boto3.Session())


@app.get("/paddle/verify_transaction")
@format_response
def post__paddle_verify_transaction(authorization: Annotated[Union[str, None], Cookie()] = None,
                                    transaction_id: str = Query()):
    with DatabaseSession(os.environ["ENV"]) as db:
        user = edp.verify_session(authorization)
        edp.paddle_verify_transaction(user, transaction_id, boto3.Session())


@app.get('/oauth2')
@format_response
def get__oauth2(state: str = Query(), code: str = Query(None), error: str = Query(None)):
    """
    Process new OAuth request. Can be either login or add calendar. See `OAuthKind`
    """
    with DatabaseSession(os.environ["ENV"]) as db:
        return edp.get_oauth_token(state, code, error, db, boto3.Session())


@app.get("/google/sso/prepare")
@format_response
def get__prepare_google_sso_oauth(tos: int = Query(0)):
    """
    Create unique authorization URL
    todo: only signin/signup or also for calendar?
    """
    with DatabaseSession(os.environ["ENV"]) as db:
        return edp.prepare_google_sso_oauth(tos, db, boto3.Session())


@app.get('/google/calendar/prepare')
@format_response
def get__prepare_google_calendar_oauth(authorization: Annotated[Union[str, None], Cookie()] = None):
    """
    Create unique authorization URL
    todo: only signin/signup or also for calendar?
    """
    with DatabaseSession(os.environ["ENV"]) as db:
        if authorization:
            user = edp.verify_session(authorization)
            return edp.prepare_calendar_oauth(user, db, boto3.Session())
        else:
            return edp.prepare_calendar_oauth_without_user(db, boto3.Session())


@app.get('/accounts')
@format_response
def get__calendar_accounts(authorization: Annotated[Union[str, None], Cookie()] = None):
    with DatabaseSession(os.environ["ENV"]) as db:
        user = edp.verify_session(authorization)
        return edp.get_calendar_accounts(user, db)


@app.get('/accounts/{calendar_account_id}/calendars')
@format_response
def get__calendars(calendar_account_id: str, authorization: Annotated[Union[str, None], Cookie()] = None):
    with DatabaseSession(os.environ["ENV"]) as db:
        user = edp.verify_session(authorization)
        calendars = edp.get_calendars(user, calendar_account_id, db)
        return [{"uuid": c.uuid, "name": c.friendly_name, "readonly": c.readonly} for c in calendars]


@app.post('/accounts/{calendar_account_id}/calendars/refresh')
@format_response
def post__refresh_calendars(calendar_account_id: str, authorization: Annotated[Union[str, None], Cookie()] = None):
    with DatabaseSession(os.environ["ENV"]) as db:
        user = edp.verify_session(authorization)
        return edp.refresh_calendars(user, calendar_account_id, db, boto3.Session())


@app.post('/calendars/{calendar_uuid}/resync')
@format_response
def post__resync_calendar(calendar_uuid: str, authorization: Annotated[Union[str, None], Cookie()] = None):
    with DatabaseSession(os.environ["ENV"]) as db:
        user = edp.verify_session(authorization)
        return edp.resync_calendar(user, calendar_uuid, boto3.Session(), db)


@app.post('/tos')
@format_response
def post__tos(authorization: Annotated[Union[str, None], Cookie()] = None):
    with DatabaseSession(os.environ["ENV"]) as db:
        user = edp.verify_session(authorization)
        return edp.accept_tos(user, db)


@app.get('/sync')
@format_response
def get__sync_rules(authorization: Annotated[Union[str, None], Cookie()] = None):
    with DatabaseSession(os.environ["ENV"]) as db:
        user = edp.verify_session(authorization)
        return [sr for sr in edp.get_sync_rules(user) if not sr.get('deleted', False)]


@app.post('/sync')
@format_response
def post__sync_rule(body: PostSyncRuleBody, authorization: Annotated[Union[str, None], Cookie()] = None):
    """
    Create a sync rule
    """
    with DatabaseSession(os.environ["ENV"]) as db:
        user = edp.verify_session(authorization)
        edp.create_sync_rule(body, user, boto3.Session(), db)


@app.delete('/sync/{sync_id}')
@format_response
def delete__sync_rule(sync_id: str, authorization: Annotated[Union[str, None], Cookie()] = None):
    """
    Update a calendar. Used to set a calendar as active.
    """
    with DatabaseSession(os.environ["ENV"]) as db:
        user = edp.verify_session(authorization)
        edp.delete_sync_rule(user, sync_id, boto3.Session(), db)


@app.patch('/sync/{sync_id}')
@format_response
def patch__sync_rule(sync_id: str, payload: PatchSyncRuleBody,
                     authorization: Annotated[Union[str, None], Cookie()] = None):
    """
    Update a calendar. Used to set a calendar as active.
    """
    with DatabaseSession(os.environ["ENV"]) as db:
        user = edp.verify_session(authorization)
        edp.patch_sync_rule(user, sync_id, payload, boto3.Session(), db)


@app.delete('/calendars/{account_id}')
@format_response
def delete__calendar(account_id: str, authorization: Annotated[Union[str, None], Cookie()] = None,
                     body: Dict[str, str] = Body(...)):
    """
    Update a calendar. Used to set a calendar as active.
    """
    with DatabaseSession(os.environ["ENV"]) as db:
        user = edp.verify_session(authorization)
        return edp.delete_account(user, account_id)


@app.get('/calendars/{calendar_id}')
@format_response
def get__calendar(calendar_id: str, authorization: Annotated[Union[str, None], Cookie()] = None):
    with DatabaseSession(os.environ["ENV"]) as db:
        user = edp.verify_session(authorization)
        c = edp.get_calendar(user, calendar_id, db)
        return {"uuid": c.uuid, "name": c.friendly_name, "active": c.active}


@app.get('/whoami')
@format_response
def get__whoami(authorization: Annotated[Union[str, None], Cookie()] = None):
    """
    Should return profile information, right now only checks
    the session
    """
    with DatabaseSession(os.environ["ENV"]) as db:
        user = edp.verify_session(authorization)
        if user.tos is None:
            raise ApiError('', code=309)
        return {"customer_id": user.customer_id, "date_created": user.date_created,
                "subscription_id": user.subscription_id, "transaction_id": user.transaction_id,
                "uuid": str(user.uuid)}


@app.get('/logout')
@format_response
def get__logout(authorization: Annotated[Union[str, None], Cookie()] = None):
    """
    Should return profile information, right now only checks
    the session
    """
    response = starlette.responses.Response()
    response.set_cookie("authorization", httponly=True, secure=True, expires=utcnow())
    return response


@app.get('/paddle/subscription')
@format_response
def get__paddle_subscription(authorization: Annotated[Union[str, None], Cookie()] = None):
    """
    Should return profile information, right now only checks
    the session
    """
    with DatabaseSession(os.environ["ENV"]) as db:
        user = edp.verify_session(authorization)

        return edp.get_paddle_subscription(user, boto3.Session())


@app.put('/console-error')
@format_response
def put__console_error(error: Dict):
    """
    Should return profile information, right now only checks
    the session
    """
    logger.error(error)


@app.get('/user/{user_id}/unsubscribe')
@format_response
def get__unsubscribe(user_id: str):
    """
    Should return profile information, right now only checks
    the session
    """
    with DatabaseSession(os.environ["ENV"]) as db:
        return edp.unsubscribe(user_id)


@app.get('/user/{user_id}/reset')
@format_response
def reset__user(user_uuid: str, session_id: str = Header(None),
                authorization: Annotated[Union[str, None], Cookie()] = None):
    with DatabaseSession(os.environ["ENV"]) as db:
        auth = session_id if session_id is not None else authorization
        if auth is None:
            raise ApiError("Forbidden", 403)

        caller = edp.verify_session(auth)
        edp.reset_user(caller, user_uuid, boto3.Session(), db)


@app.post('/magic-link', response_model=PostMagicLinkResponse)
@format_response
def post__magic_link(authorization: Annotated[Union[str, None], Cookie()] = None) -> PostMagicLinkResponse:
    """
    Returns a magic link
    """
    with DatabaseSession(os.environ["ENV"]) as db:
        user = edp.verify_session(authorization)
        return edp.handle_post_magic_link(user)


@app.get('/magic-link/{link_uuid}')
@format_response
def get__magic_link(link_uuid: str):
    """
    Returns a magic link
    """
    with DatabaseSession(os.environ["ENV"]) as db:
        return edp.handle_use_magic_link(link_uuid)


origins = ["http://localhost:8000", "http://127.0.0.1:8080"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"{request.url.path}")

    response = await call_next(request)
    logger.info(f"{response.status_code}")

    return response


handler = Mangum(app, lifespan='off')
