"""Attendance routes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from models.database import get_db
from models.schemas import AttendanceCreate, AttendanceOut
from routes.deps import get_current_user
from services import attendance_service

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.post(
    "",
    response_model=AttendanceOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user)],
)
def record_attendance(payload: AttendanceCreate, db: Session = Depends(get_db)) -> AttendanceOut:
    return AttendanceOut.model_validate(attendance_service.record_attendance(db, payload))


@router.get(
    "",
    response_model=list[AttendanceOut],
    dependencies=[Depends(get_current_user)],
)
def list_attendance(
    member_id: int | None = Query(None),
    start: date | None = Query(None, description="Inclusive start date"),
    end: date | None = Query(None, description="Inclusive end date"),
    limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db),
) -> list[AttendanceOut]:
    rows = attendance_service.list_attendance(
        db, member_id=member_id, start=start, end=end, limit=limit
    )
    return [AttendanceOut.model_validate(a) for a in rows]
