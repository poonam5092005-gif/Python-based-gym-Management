"""User authentication and admin bootstrap logic."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.db_models import User, UserRole
from models.schemas import UserCreate
from utils.config import settings
from utils.exceptions import AuthError, ConflictError
from utils.logger import get_logger
from utils.security import (
    create_access_token,
    hash_password,
    verify_password,
)

log = get_logger(__name__)


def create_user(db: Session, payload: UserCreate) -> User:
    existing = db.execute(
        select(User).where(
            (User.username == payload.username) | (User.email == payload.email)
        )
    ).scalar_one_or_none()
    if existing:
        raise ConflictError("Username or email already registered.")

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log.info("User created id=%s username=%s role=%s", user.id, user.username, user.role)
    return user


def authenticate(db: Session, username: str, password: str) -> tuple[User, str]:
    user = db.execute(
        select(User).where(User.username == username)
    ).scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        raise AuthError("Invalid username or password.")

    token = create_access_token(subject=user.username, extra_claims={"role": user.role.value})
    log.info("User authenticated username=%s", user.username)
    return user, token


def ensure_default_admin(db: Session) -> None:
    """Create a default admin user on first startup if no users exist yet."""
    any_user = db.execute(select(User).limit(1)).scalar_one_or_none()
    if any_user is not None:
        return
    admin = User(
        username=settings.ADMIN_USERNAME,
        email=settings.ADMIN_EMAIL,
        hashed_password=hash_password(settings.ADMIN_PASSWORD),
        role=UserRole.ADMIN,
    )
    db.add(admin)
    db.commit()
    log.warning(
        "Bootstrapped default admin user '%s'. Change the password in production!",
        settings.ADMIN_USERNAME,
    )
