"""Shared FastAPI dependencies: DB session + JWT auth guards."""

from __future__ import annotations

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.database import get_db
from models.db_models import User, UserRole
from utils.exceptions import AuthError, ForbiddenError
from utils.security import decode_access_token


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Extract and validate the bearer token, then load the user."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("Missing bearer token. Login at /auth/login to obtain one.")

    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    username = payload.get("sub")
    if not username:
        raise AuthError("Token is missing subject claim.")

    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if not user:
        raise AuthError("User no longer exists.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise ForbiddenError("Admin privileges required for this action.")
    return user
