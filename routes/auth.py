"""Authentication routes: register (admin-only) + login."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models.database import get_db
from models.schemas import TokenOut, UserCreate, UserOut
from routes.deps import require_admin
from services import auth_service
from utils.config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    user, token = auth_service.authenticate(db, payload.username, payload.password)
    return TokenOut(
        access_token=token,
        expires_in_minutes=settings.JWT_EXPIRE_MINUTES,
        role=user.role,
        username=user.username,
    )


@router.post(
    "/register",
    response_model=UserOut,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
def register_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserOut:
    user = auth_service.create_user(db, payload)
    return UserOut.model_validate(user)
