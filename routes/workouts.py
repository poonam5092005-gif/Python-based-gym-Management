"""Trainer + workout plan routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from models.database import get_db
from models.schemas import (
    MessageOut,
    TrainerCreate,
    TrainerOut,
    WorkoutPlanCreate,
    WorkoutPlanOut,
)
from routes.deps import get_current_user, require_admin
from services import workout_service


trainer_router = APIRouter(prefix="/trainers", tags=["Trainers"])
plan_router = APIRouter(prefix="/workout-plans", tags=["Workout Plans"])


# ---------- Trainers ----------


@trainer_router.post(
    "",
    response_model=TrainerOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user)],
)
def create_trainer(payload: TrainerCreate, db: Session = Depends(get_db)) -> TrainerOut:
    return TrainerOut.model_validate(workout_service.create_trainer(db, payload))


@trainer_router.get(
    "", response_model=list[TrainerOut], dependencies=[Depends(get_current_user)]
)
def list_trainers(db: Session = Depends(get_db)) -> list[TrainerOut]:
    return [TrainerOut.model_validate(t) for t in workout_service.list_trainers(db)]


@trainer_router.get(
    "/{trainer_id}",
    response_model=TrainerOut,
    dependencies=[Depends(get_current_user)],
)
def get_trainer(trainer_id: int, db: Session = Depends(get_db)) -> TrainerOut:
    return TrainerOut.model_validate(workout_service.get_trainer(db, trainer_id))


# ---------- Workout plans ----------


@plan_router.post(
    "",
    response_model=WorkoutPlanOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user)],
)
def assign_plan(payload: WorkoutPlanCreate, db: Session = Depends(get_db)) -> WorkoutPlanOut:
    plan = workout_service.assign_workout_plan(db, payload)
    return WorkoutPlanOut.model_validate(plan)


@plan_router.get(
    "",
    response_model=list[WorkoutPlanOut],
    dependencies=[Depends(get_current_user)],
)
def list_plans(
    member_id: int | None = Query(None),
    db: Session = Depends(get_db),
) -> list[WorkoutPlanOut]:
    if member_id is not None:
        plans = workout_service.list_plans_for_member(db, member_id)
    else:
        plans = workout_service.list_all_plans(db)
    return [WorkoutPlanOut.model_validate(p) for p in plans]


@plan_router.get(
    "/{plan_id}",
    response_model=WorkoutPlanOut,
    dependencies=[Depends(get_current_user)],
)
def get_plan(plan_id: int, db: Session = Depends(get_db)) -> WorkoutPlanOut:
    return WorkoutPlanOut.model_validate(workout_service.get_plan(db, plan_id))


@plan_router.delete(
    "/{plan_id}", response_model=MessageOut, dependencies=[Depends(require_admin)]
)
def delete_plan(plan_id: int, db: Session = Depends(get_db)) -> MessageOut:
    workout_service.delete_plan(db, plan_id)
    return MessageOut(detail=f"Workout plan {plan_id} deleted.")
