"""Attendance business logic."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.db_models import Attendance, Member
from models.schemas import AttendanceCreate
from utils.exceptions import ConflictError, NotFoundError
from utils.logger import get_logger

log = get_logger(__name__)


def record_attendance(db: Session, payload: AttendanceCreate) -> Attendance:
    if not db.get(Member, payload.member_id):
        raise NotFoundError(f"Member {payload.member_id} not found.")

    entry = Attendance(
        member_id=payload.member_id,
        check_in_date=payload.check_in_date or date.today(),
        check_in_time=datetime.now(),
        duration_minutes=payload.duration_minutes,
    )
    db.add(entry)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            f"Attendance for member {payload.member_id} on {entry.check_in_date} already recorded."
        ) from exc
    db.refresh(entry)
    log.info(
        "Attendance recorded member_id=%s date=%s duration=%s",
        payload.member_id,
        entry.check_in_date,
        entry.duration_minutes,
    )
    return entry


def list_attendance(
    db: Session,
    *,
    member_id: Optional[int] = None,
    start: Optional[date] = None,
    end: Optional[date] = None,
    limit: int = 500,
) -> list[Attendance]:
    stmt = select(Attendance).order_by(Attendance.check_in_date.desc())
    if member_id is not None:
        stmt = stmt.where(Attendance.member_id == member_id)
    if start is not None:
        stmt = stmt.where(Attendance.check_in_date >= start)
    if end is not None:
        stmt = stmt.where(Attendance.check_in_date <= end)
    return list(db.execute(stmt.limit(limit)).scalars().all())
