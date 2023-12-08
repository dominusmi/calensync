import dataclasses
import json
import traceback
from functools import wraps
from typing import Dict

import pydantic
from fastapi.responses import JSONResponse, HTMLResponse


from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEventV2


from calensync.encode import AugmentedEncoder, ISerializable
from calensync.log import get_logger

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
                return HTMLResponse(**result.to_response())

            elif isinstance(result, ApiError):
                return JSONResponse({"detail": result.detail}, status_code=result.code)

            elif isinstance(result, pydantic.BaseModel):
                return HTMLResponse(result.json(), headers={"Content-Type": "application/json"})

            return json_response(result)
        except RedirectResponse as result:
            return HTMLResponse(**result.to_response())
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
    def __init__(self, location: str):
        self.location = location

    def to_response(self):
        return {
            "status_code": 302,
            "headers": {"location": self.location, "Content-Type": "text/html; charset=UTF-8"},
            "content": """<html>If you are not redirected, <a href="{}">please click here</a></html>"""
                .format(self.location)
        }


@dataclasses.dataclass
class Claims:
    email: str


class ApiError(Exception):
    def __init__(self, message: str = 'Invalid request', code: int = 400):
        self.detail = message
        self.code = code
        super().__init__(self.detail, self.code)

