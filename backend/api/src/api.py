import boto3
from fastapi import FastAPI, Request, Query, Header, Body
from mangum import Mangum
from pydantic import BaseModel

from calensync import sqs
from calensync.api.common import format_response
from calensync.api.endpoints import *
from calensync.database.utils import DatabaseSession
from calensync.dataclass import GoogleWebhookEvent, SQSEvent, QueueEvent

app = FastAPI(title="Calensync")  # Here is the magic


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
        sqs.send_event(boto3.session.Session(), sqs_event.json())


@app.get("/paddle/verify_transaction")
@format_response
def post__paddle_verify_transaction(authorization: str = Header(None), transaction_id: str = Query()):
    with DatabaseSession(os.environ["ENV"]) as db:
        user = verify_session(authorization)
        paddle_verify_transaction(user, transaction_id)


@app.get('/oauth2')
@format_response
def get__oauth2(state: str = Query(), code: str = Query()):
    """
    Process new OAuth request. Can be either login or add calendar. See `OAuthKind`
    """
    with DatabaseSession(os.environ["ENV"]) as db:
        return get_oauth_token(state, code, db, boto3.Session())


@format_response
@app.get("/google/sso/prepare")
def get__prepare_google_sso_oauth(authorization: str = Header(None)):
    """
    Create unique authorization URL
    todo: only signin/signup or also for calendar?
    """
    session_id = authorization
    if session_id is None:
        raise ApiError("Session ID must be defined")
    with DatabaseSession(os.environ["ENV"]) as db:
        return prepare_google_sso_oauth(session_id, db, boto3.Session())


@format_response
@app.get('/google/calendar/prepare')
def get__prepare_google_calendar_oauth(authorization: str = Header(None)):
    """
    Create unique authorization URL
    todo: only signin/signup or also for calendar?
    """
    with DatabaseSession(os.environ["ENV"]) as db:
        user = verify_session(authorization)
        return prepare_calendar_oauth(user, db, boto3.Session())


@format_response
@app.get('/accounts')
def get__calendar_accounts(authorization: str = Header(None)):
    with DatabaseSession(os.environ["ENV"]) as db:
        user = verify_session(authorization)
        return get_calendar_accounts(user, db)


@format_response
@app.get('/accounts/{calendar_account_id}/calendars')
def get__calendars(calendar_account_id: str, authorization: str = Header(None)):
    with DatabaseSession(os.environ["ENV"]) as db:
        user = verify_session(authorization)
        calendars = get_calendars(user, calendar_account_id, db)
        return [{"uuid": c.uuid, "name": c.friendly_name, "active": c.active} for c in calendars]


@app.post('/accounts/{calendar_account_id}/calendars/refresh')
@format_response
def post__refresh_calendars(calendar_account_id: str, authorization: str = Header(None)):
    with DatabaseSession(os.environ["ENV"]) as db:
        user = verify_session(authorization)
        return refresh_calendars(user, calendar_account_id, db)


@app.post('/tos')
@format_response
def post__tos(authorization: str = Header(None)):
    with DatabaseSession(os.environ["ENV"]) as db:
        user = verify_session(authorization)
        return accept_tos(user, db)


class PatchCalendarBody(BaseModel):
    kind: str


@app.patch('/calendars/{calendar_id}')
@format_response
def patch__calendar(calendar_id: str, body: PatchCalendarBody, authorization: str = Header(None)):
    """
    Update a calendar. Used to set a calendar as active.
    """
    with DatabaseSession(os.environ["ENV"]) as db:
        user = verify_session(authorization)
        event = dataclass.UpdateCalendarStateEvent(kind=dataclass.CalendarStateEnum.ACTIVE, calendar_id=calendar_id,
                                                   user_id=user.id)
        if body.kind == "activate":
            pass
        elif body.kind == "deactivate":
            event.kind = dataclass.CalendarStateEnum.INACTIVE
        else:
            raise ApiError()

        sqs_event = dataclass.SQSEvent(kind=dataclass.QueueEvent.UPDATE_CALENDAR_STATE, data=event)
        sqs.send_event(boto3.Session(), sqs_event.json())


@app.delete('/calendars/{account_id}')
@format_response
def delete__calendar(account_id: str, authorization: str = Header(None), body: Dict[str, str] = Body(...)):
    """
    Update a calendar. Used to set a calendar as active.
    """
    with DatabaseSession(os.environ["ENV"]) as db:
        user = verify_session(authorization)
        return delete_account(user, account_id)


@app.get('/calendars/{calendar_id}')
@format_response
def get__calendar(calendar_id: str, authorization: str = Header(None)):
    with DatabaseSession(os.environ["ENV"]) as db:
        user = verify_session(authorization)
        c = get_calendar(user, calendar_id, db)
        return {"uuid": c.uuid, "name": c.friendly_name, "active": c.active}


@app.get('/whoami')
@format_response
def get__whoami(authorization: str = Header(None)):
    """
    Should return profile information, right now only checks
    the session
    """
    with DatabaseSession(os.environ["ENV"]) as db:
        user = verify_session(authorization)
        if user.tos is None:
            raise ApiError('', code=309)
        return {"customer_id": user.customer_id, "date_created": user.date_created,
                "subscription_id": user.subscription_id}


@app.get('/paddle/subscription')
@format_response
def get__paddle_subscription(authorization: str = Header(None)):
    """
    Should return profile information, right now only checks
    the session
    """
    with DatabaseSession(os.environ["ENV"]) as db:
        user = verify_session(authorization)
        return get_paddle_subscription(user)


from fastapi.middleware.cors import CORSMiddleware

origins = ["http://localhost:8000", "http://127.0.0.1:8080"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn
    from pathlib import Path

    dir = Path().expanduser().resolve().parent
    env_path = dir.joinpath("../.env").resolve()
    reload_dir = dir.joinpath("../").resolve()
    uvicorn.run(app, host="127.0.0.1", port=8000, env_file=str(env_path), reload_dirs=[str(reload_dir)])
