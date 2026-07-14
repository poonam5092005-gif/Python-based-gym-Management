"""Analytics + reporting endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from models.database import get_db
from routes.deps import get_current_user
from services import analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary", dependencies=[Depends(get_current_user)])
def analytics_summary(db: Session = Depends(get_db)) -> dict:
    """Headline KPIs: active/expired members, new registrations, revenue, etc."""
    return analytics_service.compute_summary(db)


@router.get("/registrations", dependencies=[Depends(get_current_user)])
def monthly_registrations(
    months: int = Query(12, ge=1, le=60),
    db: Session = Depends(get_db),
) -> list[dict]:
    return analytics_service.monthly_new_registrations(db, months=months)


@router.get("/attendance-trends", dependencies=[Depends(get_current_user)])
def attendance_trends(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> list[dict]:
    return analytics_service.attendance_trends(db, days=days)


@router.get("/popular-workouts", dependencies=[Depends(get_current_user)])
def popular_workouts(
    top: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[dict]:
    return analytics_service.popular_workouts(db, top=top)


@router.get("/revenue", dependencies=[Depends(get_current_user)])
def revenue(
    months: int = Query(12, ge=1, le=60),
    db: Session = Depends(get_db),
) -> list[dict]:
    return analytics_service.monthly_revenue(db, months=months)


@router.get("/plan-distribution", dependencies=[Depends(get_current_user)])
def plan_distribution(db: Session = Depends(get_db)) -> list[dict]:
    return analytics_service.plan_distribution(db)


@router.post("/charts/generate", dependencies=[Depends(get_current_user)])
def generate_charts(db: Session = Depends(get_db)) -> dict:
    """(Re)generate all chart PNGs under data/plots/ and return their paths."""
    return analytics_service.generate_all_charts(db)


@router.get("/charts/{chart_name}", dependencies=[Depends(get_current_user)])
def download_chart(chart_name: str) -> FileResponse:
    """Download a generated chart. Chart names: member_growth, attendance_trends,
    workout_distribution, monthly_revenue, plan_distribution."""
    allowed = {
        "member_growth",
        "attendance_trends",
        "workout_distribution",
        "monthly_revenue",
        "plan_distribution",
    }
    if chart_name not in allowed:
        raise HTTPException(status_code=404, detail=f"Unknown chart '{chart_name}'.")
    path = analytics_service.PLOTS_DIR / f"{chart_name}.png"
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"Chart '{chart_name}' not generated yet. "
                "POST /analytics/charts/generate first."
            ),
        )
    return FileResponse(path, media_type="image/png", filename=Path(path).name)
