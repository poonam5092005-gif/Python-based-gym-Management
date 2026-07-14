"""Business logic for trainers and workout plans."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models.db_models import Exercise, Member, Trainer, WorkoutPlan
from models.schemas import TrainerCreate, WorkoutPlanCreate
from utils.exceptions import ConflictError, NotFoundError
from utils.logger import get_logger

log = get_logger(__name__)


# ---------- Trainers ----------


def create_trainer(db: Session, payload: TrainerCreate) -> Trainer:
    if payload.email:
        existing = db.execute(
            select(Trainer).where(Trainer.email == payload.email)
        ).scalar_one_or_none()
        if existing:
            raise ConflictError(f"Trainer with email '{payload.email}' already exists.")

    trainer = Trainer(
        name=payload.name.strip(),
        specialization=payload.specialization,
        email=payload.email,
        phone=payload.phone,
    )
    db.add(trainer)
    db.commit()
    db.refresh(trainer)
    log.info("Trainer created id=%s name=%s", trainer.id, trainer.name)
    return trainer


def list_trainers(db: Session) -> list[Trainer]:
    return list(db.execute(select(Trainer).order_by(Trainer.id)).scalars().all())


def get_trainer(db: Session, trainer_id: int) -> Trainer:
    t = db.get(Trainer, trainer_id)
    if not t:
        raise NotFoundError(f"Trainer {trainer_id} not found.")
    return t


# ---------- Workout plans ----------


def assign_workout_plan(db: Session, payload: WorkoutPlanCreate) -> WorkoutPlan:
    if not db.get(Member, payload.member_id):
        raise NotFoundError(f"Member {payload.member_id} not found.")
    if not db.get(Trainer, payload.trainer_id):
        raise NotFoundError(f"Trainer {payload.trainer_id} not found.")

    plan = WorkoutPlan(
        member_id=payload.member_id,
        trainer_id=payload.trainer_id,
        name=payload.name.strip(),
        goal=payload.goal,
        duration_minutes=payload.duration_minutes,
        trainer_notes=payload.trainer_notes,
    )
    for ex in payload.exercises:
        plan.exercises.append(
            Exercise(
                name=ex.name.strip(),
                sets=ex.sets,
                repetitions=ex.repetitions,
                weight_kg=ex.weight_kg,
                notes=ex.notes,
            )
        )

    db.add(plan)
    db.commit()
    db.refresh(plan)
    log.info(
        "Workout plan assigned id=%s member_id=%s trainer_id=%s exercises=%d",
        plan.id,
        plan.member_id,
        plan.trainer_id,
        len(plan.exercises),
    )
    return plan


def get_plan(db: Session, plan_id: int) -> WorkoutPlan:
    stmt = (
        select(WorkoutPlan)
        .options(selectinload(WorkoutPlan.exercises))
        .where(WorkoutPlan.id == plan_id)
    )
    plan = db.execute(stmt).scalar_one_or_none()
    if not plan:
        raise NotFoundError(f"Workout plan {plan_id} not found.")
    return plan


def list_plans_for_member(db: Session, member_id: int) -> list[WorkoutPlan]:
    if not db.get(Member, member_id):
        raise NotFoundError(f"Member {member_id} not found.")
    stmt = (
        select(WorkoutPlan)
        .options(selectinload(WorkoutPlan.exercises))
        .where(WorkoutPlan.member_id == member_id)
        .order_by(WorkoutPlan.assigned_date.desc())
    )
    return list(db.execute(stmt).scalars().all())


def list_all_plans(db: Session, limit: int = 200) -> list[WorkoutPlan]:
    stmt = (
        select(WorkoutPlan)
        .options(selectinload(WorkoutPlan.exercises))
        .order_by(WorkoutPlan.id.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def delete_plan(db: Session, plan_id: int) -> None:
    plan = db.get(WorkoutPlan, plan_id)
    if not plan:
        raise NotFoundError(f"Workout plan {plan_id} not found.")
    db.delete(plan)
    db.commit()
    log.info("Workout plan deleted id=%s", plan_id)


def search_popular_workouts(db: Session, top: int = 5) -> list[tuple[str, int]]:
    """Aggregate popular exercise names across all plans."""
    stmt = select(Exercise.name)
    rows = [row[0] for row in db.execute(stmt).all()]

    counts: dict[str, int] = {}
    for name in rows:
        key = name.strip().title()
        counts[key] = counts.get(key, 0) + 1
    return sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:top]

