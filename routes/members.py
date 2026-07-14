"""Member CRUD + membership management routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from models.database import get_db
from models.db_models import MembershipStatus, PlanType
from models.schemas import (
    MemberCreate,
    MemberOut,
    MemberUpdate,
    MembershipCreate,
    MembershipOut,
    MessageOut,
)
from routes.deps import get_current_user, require_admin
from services import member_service

router = APIRouter(prefix="/members", tags=["Members"])


def _to_out(db: Session, member) -> MemberOut:
    out = MemberOut.model_validate(member)
    out.current_membership_status = member_service.get_current_status(db, member)
    return out


@router.post(
    "",
    response_model=MemberOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user)],
)
def create_member(payload: MemberCreate, db: Session = Depends(get_db)) -> MemberOut:
    member = member_service.create_member(db, payload)
    return _to_out(db, member)


@router.get("", response_model=list[MemberOut], dependencies=[Depends(get_current_user)])
def list_members(
    search: str | None = Query(None, description="Case-insensitive name search"),
    status_filter: MembershipStatus | None = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[MemberOut]:
    members = member_service.list_members(
        db, search=search, status=status_filter, limit=limit, offset=offset
    )
    return [_to_out(db, m) for m in members]


@router.get(
    "/{member_id}", response_model=MemberOut, dependencies=[Depends(get_current_user)]
)
def get_member(member_id: int, db: Session = Depends(get_db)) -> MemberOut:
    member = member_service.get_member(db, member_id)
    return _to_out(db, member)


@router.put(
    "/{member_id}",
    response_model=MemberOut,
    dependencies=[Depends(get_current_user)],
)
def update_member(
    member_id: int, payload: MemberUpdate, db: Session = Depends(get_db)
) -> MemberOut:
    member = member_service.update_member(db, member_id, payload)
    return _to_out(db, member)


@router.delete(
    "/{member_id}", response_model=MessageOut, dependencies=[Depends(require_admin)]
)
def delete_member(member_id: int, db: Session = Depends(get_db)) -> MessageOut:
    member_service.delete_member(db, member_id)
    return MessageOut(detail=f"Member {member_id} deleted.")


# ---------- Memberships ----------


@router.post(
    "/{member_id}/memberships",
    response_model=MembershipOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user)],
)
def create_membership(
    member_id: int, payload: MembershipCreate, db: Session = Depends(get_db)
) -> MembershipOut:
    m = member_service.create_membership(db, member_id, payload)
    return MembershipOut.model_validate(m)


@router.post(
    "/{member_id}/memberships/renew",
    response_model=MembershipOut,
    dependencies=[Depends(get_current_user)],
)
def renew_membership(
    member_id: int,
    plan_type: PlanType = Query(...),
    price: float | None = Query(None, gt=0),
    db: Session = Depends(get_db),
) -> MembershipOut:
    m = member_service.renew_membership(db, member_id, plan_type, price)
    return MembershipOut.model_validate(m)


@router.get(
    "/{member_id}/memberships",
    response_model=list[MembershipOut],
    dependencies=[Depends(get_current_user)],
)
def list_memberships(member_id: int, db: Session = Depends(get_db)) -> list[MembershipOut]:
    return [
        MembershipOut.model_validate(m)
        for m in member_service.list_memberships(db, member_id)
    ]
