"""Analytics module — Pandas/NumPy-powered insights + Matplotlib/Seaborn charts."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # headless-safe backend for the API server

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.db_models import (
    Attendance,
    Exercise,
    Member,
    Membership,
    MembershipStatus,
    PlanType,
    WorkoutPlan,
)
from utils.config import BASE_DIR
from utils.logger import get_logger

log = get_logger(__name__)

PLOTS_DIR = BASE_DIR / "data" / "plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", palette="deep")


# ---------- DataFrame builders ----------


def members_df(db: Session) -> pd.DataFrame:
    rows = db.execute(select(Member)).scalars().all()
    if not rows:
        return pd.DataFrame(
            columns=[
                "id", "name", "age", "gender", "weight", "height",
                "fitness_goal", "join_date", "email",
            ]
        )
    return pd.DataFrame(
        [
            {
                "id": m.id,
                "name": m.name,
                "age": m.age,
                "gender": m.gender.value,
                "weight": m.weight,
                "height": m.height,
                "fitness_goal": m.fitness_goal,
                "join_date": pd.to_datetime(m.join_date),
                "email": m.email,
            }
            for m in rows
        ]
    )


def memberships_df(db: Session) -> pd.DataFrame:
    rows = db.execute(select(Membership)).scalars().all()
    if not rows:
        return pd.DataFrame(
            columns=[
                "id", "member_id", "plan_type", "start_date", "end_date",
                "price", "status",
            ]
        )
    df = pd.DataFrame(
        [
            {
                "id": m.id,
                "member_id": m.member_id,
                "plan_type": m.plan_type.value,
                "start_date": pd.to_datetime(m.start_date),
                "end_date": pd.to_datetime(m.end_date),
                "price": m.price,
                "status": m.status.value,
            }
            for m in rows
        ]
    )
    # Recompute "live" status without touching the DB
    today = pd.Timestamp(date.today())
    df["live_status"] = np.where(
        df["status"] == MembershipStatus.CANCELLED.value,
        MembershipStatus.CANCELLED.value,
        np.where(
            df["end_date"] >= today,
            MembershipStatus.ACTIVE.value,
            MembershipStatus.EXPIRED.value,
        ),
    )
    return df


def attendance_df(db: Session) -> pd.DataFrame:
    rows = db.execute(select(Attendance)).scalars().all()
    if not rows:
        return pd.DataFrame(
            columns=["id", "member_id", "check_in_date", "duration_minutes"]
        )
    return pd.DataFrame(
        [
            {
                "id": a.id,
                "member_id": a.member_id,
                "check_in_date": pd.to_datetime(a.check_in_date),
                "duration_minutes": a.duration_minutes or 0,
            }
            for a in rows
        ]
    )


def exercises_df(db: Session) -> pd.DataFrame:
    stmt = select(Exercise, WorkoutPlan.member_id).join(
        WorkoutPlan, Exercise.plan_id == WorkoutPlan.id
    )
    result = db.execute(stmt).all()
    if not result:
        return pd.DataFrame(columns=["exercise", "sets", "repetitions", "member_id"])
    return pd.DataFrame(
        [
            {
                "exercise": ex.name.title().strip(),
                "sets": ex.sets,
                "repetitions": ex.repetitions,
                "member_id": member_id,
            }
            for ex, member_id in result
        ]
    )


# ---------- KPI summary ----------


def compute_summary(db: Session) -> dict[str, Any]:
    """Headline metrics used by /analytics/summary and dashboards."""
    m_df = members_df(db)
    ms_df = memberships_df(db)
    a_df = attendance_df(db)

    total_members = int(len(m_df))

    if ms_df.empty:
        active_members = 0
        expired_members = 0
        revenue_total = 0.0
        plan_counts: dict[str, int] = {}
    else:
        # Take each member's most recent membership to classify them
        latest = (
            ms_df.sort_values("end_date")
            .groupby("member_id")
            .tail(1)
        )
        active_members = int((latest["live_status"] == MembershipStatus.ACTIVE.value).sum())
        expired_members = int((latest["live_status"] == MembershipStatus.EXPIRED.value).sum())
        revenue_total = float(ms_df["price"].sum())
        plan_counts = latest["plan_type"].value_counts().to_dict()

    # New registrations this month
    new_this_month = 0
    if not m_df.empty:
        this_month = pd.Timestamp(date.today().replace(day=1))
        new_this_month = int((m_df["join_date"] >= this_month).sum())

    # Attendance in last 7 days
    attendance_7d = 0
    if not a_df.empty:
        cutoff = pd.Timestamp(date.today() - timedelta(days=7))
        attendance_7d = int((a_df["check_in_date"] >= cutoff).shape[0])

    avg_age = float(m_df["age"].mean()) if not m_df.empty else 0.0
    avg_weight = float(m_df["weight"].mean()) if not m_df.empty else 0.0

    return {
        "total_members": total_members,
        "active_members": active_members,
        "expired_members": expired_members,
        "new_registrations_this_month": new_this_month,
        "attendance_last_7_days": attendance_7d,
        "total_revenue": round(revenue_total, 2),
        "average_age": round(avg_age, 1),
        "average_weight_kg": round(avg_weight, 1),
        "plan_distribution": plan_counts,
        "generated_at": pd.Timestamp.now().isoformat(timespec="seconds"),
    }


# ---------- Table-shaped analytics (JSON-friendly) ----------


def monthly_new_registrations(db: Session, months: int = 12) -> list[dict[str, Any]]:
    df = members_df(db)
    if df.empty:
        return []
    df["month"] = df["join_date"].dt.to_period("M").dt.to_timestamp()
    grouped = df.groupby("month").size().reset_index(name="new_members")
    grouped = grouped.sort_values("month").tail(months)
    grouped["month"] = grouped["month"].dt.strftime("%Y-%m")
    return grouped.to_dict(orient="records")


def attendance_trends(db: Session, days: int = 30) -> list[dict[str, Any]]:
    df = attendance_df(db)
    if df.empty:
        return []
    cutoff = pd.Timestamp(date.today() - timedelta(days=days))
    df = df[df["check_in_date"] >= cutoff]
    if df.empty:
        return []
    trend = df.groupby(df["check_in_date"].dt.date).size().reset_index(name="check_ins")
    trend["check_in_date"] = trend["check_in_date"].astype(str)
    return trend.to_dict(orient="records")


def popular_workouts(db: Session, top: int = 10) -> list[dict[str, Any]]:
    df = exercises_df(db)
    if df.empty:
        return []
    counts = (
        df.groupby("exercise")
        .size()
        .reset_index(name="times_assigned")
        .sort_values("times_assigned", ascending=False)
        .head(top)
    )
    return counts.to_dict(orient="records")


def monthly_revenue(db: Session, months: int = 12) -> list[dict[str, Any]]:
    df = memberships_df(db)
    if df.empty:
        return []
    df["month"] = df["start_date"].dt.to_period("M").dt.to_timestamp()
    grouped = df.groupby("month")["price"].sum().reset_index(name="revenue")
    grouped = grouped.sort_values("month").tail(months)
    grouped["month"] = grouped["month"].dt.strftime("%Y-%m")
    grouped["revenue"] = grouped["revenue"].round(2)
    return grouped.to_dict(orient="records")


def plan_distribution(db: Session) -> list[dict[str, Any]]:
    df = memberships_df(db)
    if df.empty:
        return []
    latest = df.sort_values("end_date").groupby("member_id").tail(1)
    dist = latest["plan_type"].value_counts().reset_index()
    dist.columns = ["plan_type", "members"]
    return dist.to_dict(orient="records")


# ---------- Chart generation (saves PNGs, returns file paths) ----------


def _save(fig: plt.Figure, filename: str) -> Path:
    path = PLOTS_DIR / filename
    fig.tight_layout()
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    log.info("Chart saved -> %s", path)
    return path


def chart_member_growth(db: Session) -> Path | None:
    df = members_df(db)
    if df.empty:
        return None
    growth = (
        df.sort_values("join_date")
        .assign(count=1)
        .groupby(df["join_date"].dt.to_period("M").dt.to_timestamp())["count"]
        .sum()
        .cumsum()
        .reset_index(name="cumulative_members")
    )
    growth.columns = ["month", "cumulative_members"]

    fig, ax = plt.subplots(figsize=(9, 5))
    sns.lineplot(data=growth, x="month", y="cumulative_members", marker="o", ax=ax)
    ax.set_title("Member Growth Over Time", fontsize=14, fontweight="bold")
    ax.set_xlabel("Month")
    ax.set_ylabel("Cumulative Members")
    fig.autofmt_xdate()
    return _save(fig, "member_growth.png")


def chart_attendance_trends(db: Session, days: int = 30) -> Path | None:
    df = attendance_df(db)
    if df.empty:
        return None
    cutoff = pd.Timestamp(date.today() - timedelta(days=days))
    df = df[df["check_in_date"] >= cutoff]
    if df.empty:
        return None
    trend = df.groupby(df["check_in_date"].dt.date).size().reset_index(name="check_ins")

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=trend, x="check_in_date", y="check_ins", ax=ax, color="#4C72B0")
    ax.set_title(f"Daily Attendance — Last {days} Days", fontsize=14, fontweight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Check-ins")
    fig.autofmt_xdate()
    return _save(fig, "attendance_trends.png")


def chart_workout_distribution(db: Session, top: int = 10) -> Path | None:
    df = exercises_df(db)
    if df.empty:
        return None
    counts = (
        df.groupby("exercise")
        .size()
        .reset_index(name="times_assigned")
        .sort_values("times_assigned", ascending=False)
        .head(top)
    )

    fig, ax = plt.subplots(figsize=(9, 6))
    sns.barplot(
        data=counts,
        y="exercise",
        x="times_assigned",
        hue="exercise",
        palette="viridis",
        legend=False,
        ax=ax,
    )
    ax.set_title(f"Top {top} Assigned Exercises", fontsize=14, fontweight="bold")
    ax.set_xlabel("Times Assigned")
    ax.set_ylabel("Exercise")
    return _save(fig, "workout_distribution.png")


def chart_monthly_revenue(db: Session) -> Path | None:
    df = memberships_df(db)
    if df.empty:
        return None
    df["month"] = df["start_date"].dt.to_period("M").dt.to_timestamp()
    rev = df.groupby("month")["price"].sum().reset_index()

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.lineplot(data=rev, x="month", y="price", marker="o", color="#2CA02C", ax=ax)
    ax.fill_between(rev["month"], rev["price"], alpha=0.2, color="#2CA02C")
    ax.set_title("Monthly Membership Revenue", fontsize=14, fontweight="bold")
    ax.set_xlabel("Month")
    ax.set_ylabel("Revenue")
    fig.autofmt_xdate()
    return _save(fig, "monthly_revenue.png")


def chart_plan_distribution(db: Session) -> Path | None:
    df = memberships_df(db)
    if df.empty:
        return None
    latest = df.sort_values("end_date").groupby("member_id").tail(1)
    dist = latest["plan_type"].value_counts()

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(
        dist.values,
        labels=dist.index,
        autopct="%1.1f%%",
        startangle=140,
        colors=sns.color_palette("Set2", n_colors=len(dist)),
        wedgeprops={"edgecolor": "white"},
    )
    ax.set_title("Membership Plan Distribution", fontsize=14, fontweight="bold")
    return _save(fig, "plan_distribution.png")


def generate_all_charts(db: Session) -> dict[str, str]:
    """Regenerate every chart file. Returns a mapping of chart_name -> file path."""
    results: dict[str, str] = {}
    mapping = {
        "member_growth": chart_member_growth,
        "attendance_trends": chart_attendance_trends,
        "workout_distribution": chart_workout_distribution,
        "monthly_revenue": chart_monthly_revenue,
        "plan_distribution": chart_plan_distribution,
    }
    for key, fn in mapping.items():
        try:
            path = fn(db)
            results[key] = str(path) if path else "no_data"
        except Exception as exc:  # noqa: BLE001
            log.exception("Failed to render %s: %s", key, exc)
            results[key] = f"error: {exc}"
    return results
