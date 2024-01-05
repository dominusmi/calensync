import dataclasses
import json
import traceback
from functools import wraps
from typing import Dict

import pydantic
import starlette.responses
from fastapi.responses import JSONResponse, HTMLResponse


from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEventV2


from calensync.encode import AugmentedEncoder, ISerializable
from calensync.log import get_logger
from calensync.utils import is_local

logger = get_logger(__file__)


def with_proxy_event(f):
    """ Transforms the event into APIGatewayProxyEventV2"""
    @wraps(f)
    def wrapper(event, context):
        event = APIGatewayProxyEventV2(event)
        return f(event, context)

    return wrapper


def json_response(content, status_code: int = 200):
    return HTMLResponse(json.dumps(content, cls=AugmentedEncoder), headers={"Content-Type": "application/json"}, status_code=status_code)


def format_response(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            result = f(*args, **kwargs)

            # avoid any potential null formatting related error
            if result is None:
                result = {}

            elif isinstance(result, RedirectResponse):
                return result.to_response()

            elif isinstance(result, ApiError):
                return JSONResponse({"detail": result.detail}, status_code=result.code)

            elif isinstance(result, pydantic.BaseModel):
                return HTMLResponse(result.json(), headers={"Content-Type": "application/json"})

            elif isinstance(result, starlette.responses.Response):
                return result

            return json_response(result)
        except RedirectResponse as result:
            return result.to_response()
        except ApiError as e:
            # For "expected" errors (ApiError), we still return 200 but set internal
            # info differently
            return json_response({"detail": e.detail}, e.code)
        except Exception as e:
            # instead for generic server error we return 500
            logger.error(traceback.format_exc())
            code = 500
            message = "Internal server error"

        return JSONResponse(json.dumps({"message": message}), status_code=code)

    return wrapper


class Response(ISerializable):
    status: int
    body: Dict

    def __init__(self, status: int, body: Dict):
        self.status = status
        self.body = body

    @classmethod
    def ok(cls):
        cls(200, {})

    def serialize(self):
        return self.body


class RedirectResponse(Exception):
    def __init__(self, location: str, cookie: Dict = None):
        self.location = location
        self.cookie = cookie

    def to_response(self):
        response = starlette.responses.Response(
            content="""<html>If you are not redirected, <a href="{}">please click here</a></html>"""
                .format(self.location),
            headers={"location": self.location},
            status_code=302
        )

        if self.cookie:
            for k, v in self.cookie.items():
                response.set_cookie(k, v, secure=True, httponly=True)
        return response


@dataclasses.dataclass
class Claims:
    email: str


class ApiError(Exception):
    def __init__(self, message: str = 'Invalid request', code: int = 400):
        self.detail = message
        self.code = code
        super().__init__(self.detail, self.code)


def number_of_days_to_sync_in_advance() -> int:
    return 5 if is_local() else 30
