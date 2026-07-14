"""Pydantic schemas for request/response validation."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from models.db_models import Gender, MembershipStatus, PlanType, UserRole


# ---------- Members ----------


class MemberBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    age: int = Field(..., ge=10, le=100)
    gender: Gender
    weight: float = Field(..., gt=20, lt=400, description="Weight in kilograms")
    height: Optional[float] = Field(None, gt=80, lt=260, description="Height in cm")
    fitness_goal: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)


class MemberCreate(MemberBase):
    """Payload used when registering a new member. Optionally include a plan."""

    plan_type: Optional[PlanType] = Field(
        default=PlanType.MONTHLY,
        description="If provided, an initial membership is created automatically.",
    )
    join_date: Optional[date] = None


class MemberUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    age: Optional[int] = Field(None, ge=10, le=100)
    gender: Optional[Gender] = None
    weight: Optional[float] = Field(None, gt=20, lt=400)
    height: Optional[float] = Field(None, gt=80, lt=260)
    fitness_goal: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)


class MemberOut(MemberBase):
    id: int
    join_date: date
    created_at: datetime
    current_membership_status: MembershipStatus = MembershipStatus.EXPIRED

    model_config = ConfigDict(from_attributes=True)


# ---------- Memberships ----------


class MembershipCreate(BaseModel):
    plan_type: PlanType
    start_date: Optional[date] = None
    price: Optional[float] = Field(
        None,
        gt=0,
        description="If omitted, a default price is applied per plan type.",
    )


class MembershipOut(BaseModel):
    id: int
    member_id: int
    plan_type: PlanType
    start_date: date
    end_date: date
    price: float
    status: MembershipStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- Attendance ----------


class AttendanceCreate(BaseModel):
    member_id: int
    check_in_date: Optional[date] = None
    duration_minutes: Optional[int] = Field(None, ge=1, le=600)


class AttendanceOut(BaseModel):
    id: int
    member_id: int
    check_in_date: date
    check_in_time: datetime
    duration_minutes: Optional[int]

    model_config = ConfigDict(from_attributes=True)


# ---------- Trainers ----------


class TrainerCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    specialization: Optional[str] = Field(None, max_length=120)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)


class TrainerOut(BaseModel):
    id: int
    name: str
    specialization: Optional[str]
    email: Optional[EmailStr]
    phone: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- Workout plans & exercises ----------


class ExerciseIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    sets: int = Field(3, ge=1, le=20)
    repetitions: int = Field(10, ge=1, le=200)
    weight_kg: Optional[float] = Field(None, ge=0, le=500)
    notes: Optional[str] = None


class ExerciseOut(ExerciseIn):
    id: int
    plan_id: int

    model_config = ConfigDict(from_attributes=True)


class WorkoutPlanCreate(BaseModel):
    member_id: int
    trainer_id: int
    name: str = Field(..., min_length=2, max_length=120)
    goal: Optional[str] = Field(None, max_length=255)
    duration_minutes: int = Field(60, ge=5, le=300)
    trainer_notes: Optional[str] = None
    exercises: list[ExerciseIn] = Field(default_factory=list)

    @field_validator("exercises")
    @classmethod
    def _non_empty(cls, value: list[ExerciseIn]) -> list[ExerciseIn]:
        if not value:
            raise ValueError("A workout plan must contain at least one exercise.")
        return value


class WorkoutPlanOut(BaseModel):
    id: int
    member_id: int
    trainer_id: int
    name: str
    goal: Optional[str]
    duration_minutes: int
    trainer_notes: Optional[str]
    assigned_date: date
    exercises: list[ExerciseOut] = []

    model_config = ConfigDict(from_attributes=True)


# ---------- Auth ----------


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    role: UserRole = UserRole.ADMIN


class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: UserRole
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    role: UserRole
    username: str


# ---------- Generic ----------


class MessageOut(BaseModel):
    detail: str
