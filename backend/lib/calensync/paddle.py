import datetime
import enum
from typing import List

import requests
from pydantic import BaseModel

from calensync.api.common import ApiError
from calensync.utils import get_env


def get_paddle_url():
    if get_env() != "prod":
        return "https://sandbox-api.paddle.com"
    return "https://api.paddle.com"


class PaddleSubscription(BaseModel):
    class ManagementUrls(BaseModel):
        update_payment_method: str
        cancel: str

    class Item(BaseModel):
        class Price(BaseModel):
            class UnitPrice(BaseModel):
                amount: int

            description: str
            unit_price: UnitPrice

        price: Price

    status: str
    next_billed_at: datetime.datetime
    management_urls: ManagementUrls
    items: List[Item]

    @property
    def is_active(self):
        return self.status == "active"


def get_transaction(transaction_id: str, paddle_token: str):
    response = requests.get(
        f"{get_paddle_url()}/transactions/{transaction_id}",
        headers={"Authorization": f'Bearer {paddle_token}'}
    )
    return response


def get_subscription(subscription_id: str, paddle_token: str):
    response = requests.get(
        f"{get_paddle_url()}/subscriptions/{subscription_id}",
        headers={"Authorization": f'Bearer {paddle_token}'}
    )
    print(response.content)
    if not response.ok:
        raise ApiError("Invalid subscription")
    return PaddleSubscription.parse_obj(response.json()["data"])
