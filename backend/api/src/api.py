import fastapi.responses
import uvicorn
from fastapi import FastAPI, Request, Query, Header, Body
from mangum import Mangum

from calensync.api.common import format_response
from calensync.api.endpoints import *
from calensync.database.utils import DatabaseSession

app = FastAPI(title="Calensync")  # Here is the magic


@format_response
@app.post("/webhook")
def post__webhook(event: Request):
    channel_id = event.headers["X-Goog-Channel-Id"]
    token = event.headers["X-Goog-Channel-Token"]
    state = event.headers["X-Goog-Resource-State"]
    resource_id = event.headers.get("X-Goog-Resource-Id")
    with DatabaseSession(os.environ["ENV"]) as db:
        received_webhook(channel_id, state, resource_id, token, db)


@app.get('/oauth2')
@format_response
def get__oauth2(state: str = Query(), code: str = Query()):
    """
    Process new OAuth request. Can be either login or add calendar. See `OAuthKind`
    """
    with DatabaseSession(os.environ["ENV"]) as db:
        return get_oauth_token(state, code, db)


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
        return prepare_google_sso_oauth(session_id, db)


@format_response
@app.get('/google/calendar/prepare')
def get__prepare_google_calendar_oauth(authorization: str = Header(None)):
    """
    Create unique authorization URL
    todo: only signin/signup or also for calendar?
    """
    with DatabaseSession(os.environ["ENV"]) as db:
        user = verify_session(authorization)
        return prepare_calendar_oauth(user, db)


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


@format_response
@app.post('/accounts/{calendar_account_id}/calendars/refresh')
def post__refresh_calendars(calendar_account_id: str, authorization: str = Header(None)):
    with DatabaseSession(os.environ["ENV"]) as db:
        user = verify_session(authorization)
        return refresh_calendars(user, calendar_account_id, db)


@format_response
@app.post('/tos')
def post__tos(authorization: str = Header(None)):
    with DatabaseSession(os.environ["ENV"]) as db:
        user = verify_session(authorization)
        return accept_tos(user, db)


@format_response
@app.patch('/calendars/{calendar_id}')
def patch__calendar(calendar_id: str, authorization: str = Header(None), body: Dict[str, str] = Body(...)):
    """
    Update a calendar. Used to set a calendar as active.
    """
    with DatabaseSession(os.environ["ENV"]) as db:
        user = verify_session(authorization)
        return patch_calendar(user, calendar_id, body, db)


@format_response
@app.delete('/calendars/{account_id}')
def delete__calendar(account_id: str, authorization: str = Header(None), body: Dict[str, str] = Body(...)):
    """
    Update a calendar. Used to set a calendar as active.
    """
    with DatabaseSession(os.environ["ENV"]) as db:
        user = verify_session(authorization)
        return delete_account(user, account_id)


@format_response
@app.get('/calendars/{calendar_id}')
def get__calendar(calendar_id: str, authorization: str = Header(None)):
    with DatabaseSession(os.environ["ENV"]) as db:
        user = verify_session(authorization)
        c = get_calendar(user, calendar_id, db)
        return {"uuid": c.uuid, "name": c.friendly_name, "active": c.active}


@format_response
@app.get('/whoami')
def get__whoami(authorization: str = Header(None)):
    """
    Should return profile information, right now only checks
    the session
    """
    with DatabaseSession(os.environ["ENV"]) as db:
        user = verify_session(authorization)
        if user.tos is None:
            return fastapi.responses.Response(status_code=309)
        return {}


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
    from pathlib import Path
    dir = Path().expanduser().resolve().parent
    env_path = dir.joinpath("../.env").resolve()
    reload_dir = dir.joinpath("../").resolve()
    uvicorn.run(app, host="127.0.0.1", port=8000, env_file=str(env_path), reload_dirs=[str(reload_dir)])
