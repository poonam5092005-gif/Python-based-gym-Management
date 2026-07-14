"""Business logic for members and memberships."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models.db_models import (
    Member,
    Membership,
    MembershipStatus,
    PlanType,
)
from models.schemas import (
    MemberCreate,
    MemberUpdate,
    MembershipCreate,
)
from utils.exceptions import ConflictError, NotFoundError, ValidationError
from utils.logger import get_logger

log = get_logger(__name__)


# ---------- Pricing table (customizable) ----------

PLAN_PRICES: dict[PlanType, float] = {
    PlanType.MONTHLY: 1500.0,
    PlanType.QUARTERLY: 4000.0,
    PlanType.YEARLY: 12000.0,
}

PLAN_DURATION_DAYS: dict[PlanType, int] = {
    PlanType.MONTHLY: 30,
    PlanType.QUARTERLY: 90,
    PlanType.YEARLY: 365,
}


def _compute_end_date(start: date, plan: PlanType) -> date:
    return start + timedelta(days=PLAN_DURATION_DAYS[plan])


def _refresh_membership_status(m: Membership) -> Membership:
    """Recompute ACTIVE/EXPIRED based on today's date (won't touch CANCELLED)."""
    if m.status == MembershipStatus.CANCELLED:
        return m
    m.status = (
        MembershipStatus.ACTIVE if m.end_date >= date.today() else MembershipStatus.EXPIRED
    )
    return m


def current_membership(db: Session, member_id: int) -> Optional[Membership]:
    """Return the most recent non-cancelled membership for a member."""
    stmt = (
        select(Membership)
        .where(Membership.member_id == member_id)
        .where(Membership.status != MembershipStatus.CANCELLED)
        .order_by(Membership.end_date.desc())
        .limit(1)
    )
    m = db.execute(stmt).scalar_one_or_none()
    if m is not None:
        _refresh_membership_status(m)
        db.flush()
    return m


# ---------- Members ----------


def create_member(db: Session, payload: MemberCreate) -> Member:
    if payload.email:
        existing = db.execute(
            select(Member).where(Member.email == payload.email)
        ).scalar_one_or_none()
        if existing:
            raise ConflictError(f"A member with email '{payload.email}' already exists.")

    member = Member(
        name=payload.name.strip(),
        age=payload.age,
        gender=payload.gender,
        weight=payload.weight,
        height=payload.height,
        fitness_goal=(payload.fitness_goal or "").strip() or None,
        email=payload.email,
        phone=payload.phone,
        join_date=payload.join_date or date.today(),
    )
    db.add(member)
    db.flush()

    if payload.plan_type is not None:
        create_membership(
            db,
            member.id,
            MembershipCreate(plan_type=payload.plan_type, start_date=member.join_date),
        )

    db.commit()
    db.refresh(member)
    log.info("Member registered id=%s name=%s plan=%s", member.id, member.name, payload.plan_type)
    return member


def update_member(db: Session, member_id: int, payload: MemberUpdate) -> Member:
    member = db.get(Member, member_id)
    if not member:
        raise NotFoundError(f"Member with id {member_id} not found.")

    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"] and data["email"] != member.email:
        clash = db.execute(
            select(Member).where(Member.email == data["email"])
        ).scalar_one_or_none()
        if clash and clash.id != member_id:
            raise ConflictError(f"Email '{data['email']}' is already in use.")

    for field, value in data.items():
        setattr(member, field, value)

    db.commit()
    db.refresh(member)
    log.info("Member updated id=%s fields=%s", member_id, list(data.keys()))
    return member


def delete_member(db: Session, member_id: int) -> None:
    member = db.get(Member, member_id)
    if not member:
        raise NotFoundError(f"Member with id {member_id} not found.")
    db.delete(member)
    db.commit()
    log.info("Member deleted id=%s", member_id)


def get_member(db: Session, member_id: int) -> Member:
    stmt = (
        select(Member)
        .options(selectinload(Member.memberships))
        .where(Member.id == member_id)
    )
    member = db.execute(stmt).scalar_one_or_none()
    if not member:
        raise NotFoundError(f"Member with id {member_id} not found.")
    return member


def list_members(
    db: Session,
    *,
    search: Optional[str] = None,
    status: Optional[MembershipStatus] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Member]:
    stmt = select(Member).options(selectinload(Member.memberships)).order_by(Member.id.desc())
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(Member.name.ilike(like))
    stmt = stmt.limit(limit).offset(offset)
    members = list(db.execute(stmt).scalars().all())

    if status is None:
        return members

    filtered: list[Member] = []
    for m in members:
        current = current_membership(db, m.id)
        current_status = current.status if current else MembershipStatus.EXPIRED
        if current_status == status:
            filtered.append(m)
    return filtered


def get_current_status(db: Session, member: Member) -> MembershipStatus:
    """Convenience: what's the member's *current* membership status right now."""
    current = current_membership(db, member.id)
    if current is None:
        return MembershipStatus.EXPIRED
    return current.status


# ---------- Memberships ----------


def create_membership(
    db: Session, member_id: int, payload: MembershipCreate
) -> Membership:
    member = db.get(Member, member_id)
    if not member:
        raise NotFoundError(f"Member with id {member_id} not found.")

    start = payload.start_date or date.today()
    if start > date.today() + timedelta(days=365):
        raise ValidationError("Start date is too far in the future.")

    price = payload.price if payload.price is not None else PLAN_PRICES[payload.plan_type]

    membership = Membership(
        member_id=member.id,
        plan_type=payload.plan_type,
        start_date=start,
        end_date=_compute_end_date(start, payload.plan_type),
        price=price,
        status=MembershipStatus.ACTIVE,
    )
    _refresh_membership_status(membership)
    db.add(membership)
    db.commit()
    db.refresh(membership)
    log.info(
        "Membership created member_id=%s plan=%s start=%s end=%s",
        member_id,
        payload.plan_type,
        membership.start_date,
        membership.end_date,
    )
    return membership


def renew_membership(
    db: Session, member_id: int, plan_type: PlanType, price: Optional[float] = None
) -> Membership:
    """Renew starting from the day after the last end date (or today, whichever is later)."""
    member = db.get(Member, member_id)
    if not member:
        raise NotFoundError(f"Member with id {member_id} not found.")

    latest = current_membership(db, member_id)
    base = latest.end_date if latest and latest.end_date >= date.today() else date.today() - timedelta(days=1)
    start = base + timedelta(days=1)

    return create_membership(
        db,
        member_id,
        MembershipCreate(
            plan_type=plan_type, start_date=start, price=price
        ),
    )


def list_memberships(db: Session, member_id: int) -> list[Membership]:
    member = db.get(Member, member_id)
    if not member:
        raise NotFoundError(f"Member with id {member_id} not found.")
    stmt = (
        select(Membership)
        .where(Membership.member_id == member_id)
        .order_by(Membership.start_date.desc())
    )
    memberships = list(db.execute(stmt).scalars().all())
    for m in memberships:
        _refresh_membership_status(m)
    db.commit()
    return memberships
