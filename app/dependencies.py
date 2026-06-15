import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.controllers import GameController
from app.db import get_session
from app.exceptions import NotAuthenticatedError
from app.repositories import GameRepository


class CurrentUser:
    def __init__(self, user_id: str, login: str, premium: bool = False):
        self.user_id = user_id
        self.login = login
        self.premium = premium


bearer = HTTPBearer(auto_error=False)


def get_controller(
    session: AsyncSession = Depends(get_session),
) -> GameController:
    return GameController(GameRepository(session))


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> CurrentUser:
    if creds is None:
        raise NotAuthenticatedError()
    try:
        payload = jwt.decode(
            creds.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError:
        raise NotAuthenticatedError()
    return CurrentUser(
        payload["sub"], payload["login"], payload.get("premium", False)
    )


def decode_token(token: str) -> CurrentUser | None:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError:
        return None
    return CurrentUser(
        payload["sub"], payload["login"], payload.get("premium", False)
    )
