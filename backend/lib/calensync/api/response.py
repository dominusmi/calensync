from pydantic import BaseModel


class PostMagicLinkResponse(BaseModel):
    uuid: str
