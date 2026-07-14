"""ORM models: Member, Trainer, Membership, Attendance, WorkoutPlan, Exercise, User."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.database import Base


# ---------- Enumerations ----------


class Gender(str, PyEnum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


class PlanType(str, PyEnum):
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"


class MembershipStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class UserRole(str, PyEnum):
    ADMIN = "ADMIN"
    TRAINER = "TRAINER"


# ---------- Models ----------


class User(Base):
    """Auth user (admin / trainer login for the API)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.ADMIN, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Trainer(Base):
    """Gym trainers who create workout plans."""

    __tablename__ = "trainers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    specialization: Mapped[str | None] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(120), unique=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    workout_plans: Mapped[list["WorkoutPlan"]] = relationship(
        back_populates="trainer", cascade="all, delete-orphan"
    )


class Member(Base):
    """Gym member profile + core fitness data."""

    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[Gender] = mapped_column(Enum(Gender), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    height: Mapped[float | None] = mapped_column(Float)  # cm, optional
    fitness_goal: Mapped[str | None] = mapped_column(String(255))
    join_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    email: Mapped[str | None] = mapped_column(String(120), unique=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="member", cascade="all, delete-orphan"
    )
    attendance: Mapped[list["Attendance"]] = relationship(
        back_populates="member", cascade="all, delete-orphan"
    )
    workout_plans: Mapped[list["WorkoutPlan"]] = relationship(
        back_populates="member", cascade="all, delete-orphan"
    )


class Membership(Base):
    """Membership subscription record. A member can have multiple over time."""

    __tablename__ = "memberships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"))
    plan_type: Mapped[PlanType] = mapped_column(Enum(PlanType), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[MembershipStatus] = mapped_column(
        Enum(MembershipStatus), default=MembershipStatus.ACTIVE, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    member: Mapped[Member] = relationship(back_populates="memberships")


class Attendance(Base):
    """Daily check-in for a member. Unique per (member, day)."""

    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("member_id", "check_in_date", name="uq_member_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"))
    check_in_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    check_in_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    duration_minutes: Mapped[int | None] = mapped_column(Integer)

    member: Mapped[Member] = relationship(back_populates="attendance")


class WorkoutPlan(Base):
    """A named workout program assigned by a trainer to a member."""

    __tablename__ = "workout_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"))
    trainer_id: Mapped[int] = mapped_column(ForeignKey("trainers.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    goal: Mapped[str | None] = mapped_column(String(255))
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    trainer_notes: Mapped[str | None] = mapped_column(Text)
    assigned_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)

    member: Mapped[Member] = relationship(back_populates="workout_plans")
    trainer: Mapped[Trainer] = relationship(back_populates="workout_plans")
    exercises: Mapped[list["Exercise"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )


class Exercise(Base):
    """Individual exercise inside a workout plan."""

    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("workout_plans.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    sets: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    repetitions: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)

    plan: Mapped[WorkoutPlan] = relationship(back_populates="exercises")
