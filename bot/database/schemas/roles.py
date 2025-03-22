from pydantic import BaseModel


class UserId(BaseModel):
    tg_id: int


class UserTgId(BaseModel):
    user_tg_id: int


class ProhibitedRoleSchema(UserTgId):
    role: str | None = None


class OrderOfRolesSchema(UserTgId):
    role: str
    number: int
