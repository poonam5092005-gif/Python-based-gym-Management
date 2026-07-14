"""Seed the database with realistic sample data for demos.

Usage:
    python seed.py            # creates ~40 members, 4 trainers, 6 months of activity
    python seed.py --reset    # wipes existing data first
"""

from __future__ import annotations

import argparse
import random
from datetime import date, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from models.database import SessionLocal, init_db
from models.db_models import (
    Attendance,
    Exercise,
    Gender,
    Member,
    Membership,
    MembershipStatus,
    PlanType,
    Trainer,
    User,
    WorkoutPlan,
)
from services.auth_service import ensure_default_admin
from services.member_service import PLAN_DURATION_DAYS, PLAN_PRICES
from utils.logger import get_logger

log = get_logger(__name__)

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Rohan", "Karan", "Ishaan", "Kabir", "Riya",
    "Ananya", "Isha", "Meera", "Priya", "Diya", "Nisha", "Sneha", "Aisha",
    "Arjun", "Rahul", "Neha", "Pooja", "Sameer", "Tanvi", "Yash", "Zoya",
    "Deepa", "Manish", "Kavya", "Om", "Ritu", "Saurabh",
]
LAST_NAMES = [
    "Sharma", "Verma", "Iyer", "Patel", "Reddy", "Nair", "Rao", "Menon",
    "Gupta", "Singh", "Kapoor", "Chopra", "Malhotra", "Bose", "Das",
]
FITNESS_GOALS = [
    "Weight loss", "Muscle gain", "Endurance", "General fitness",
    "Strength training", "Flexibility", "Sports performance",
]
TRAINERS = [
    ("Ravi Kumar", "Strength & Conditioning"),
    ("Neha Sinha", "Yoga & Flexibility"),
    ("Aman Verma", "CrossFit"),
    ("Priya Nair", "Cardio & HIIT"),
]
EXERCISES = [
    ("Bench Press", 4, 8, 40),
    ("Squat", 4, 10, 60),
    ("Deadlift", 3, 6, 80),
    ("Pull Ups", 3, 8, None),
    ("Push Ups", 3, 15, None),
    ("Plank", 3, 1, None),
    ("Lunges", 3, 12, 20),
    ("Bicep Curl", 3, 12, 12),
    ("Shoulder Press", 3, 10, 20),
    ("Treadmill Run", 1, 1, None),
    ("Cycling", 1, 1, None),
    ("Yoga Flow", 1, 1, None),
    ("Burpees", 3, 15, None),
    ("Jumping Jacks", 3, 30, None),
    ("Leg Press", 4, 10, 100),
]


def _random_person() -> tuple[str, Gender, int, float, float]:
    name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
    gender = random.choice(list(Gender))
    age = random.randint(18, 55)
    weight = round(random.uniform(50, 105), 1)
    height = round(random.uniform(150, 190), 1)
    return name, gender, age, weight, height


def wipe(db: Session) -> None:
    log.warning("Wiping existing gym data...")
    # Delete children first
    for table in (Exercise, WorkoutPlan, Attendance, Membership, Member, Trainer, User):
        db.execute(delete(table))
    db.commit()


def seed(db: Session) -> None:
    ensure_default_admin(db)

    # Trainers
    trainer_objs: list[Trainer] = []
    for name, spec in TRAINERS:
        t = Trainer(
            name=name,
            specialization=spec,
            email=f"{name.lower().replace(' ', '.')}.{random.randint(100, 9999)}@example.com",
            phone=f"+91-9{random.randint(100000000, 999999999)}",
        )
        db.add(t)
        trainer_objs.append(t)
    db.flush()
    log.info("Inserted %d trainers", len(trainer_objs))

    # Members + memberships (spread joins over the last ~10 months)
    today = date.today()
    members: list[Member] = []
    for i in range(40):
        name, gender, age, weight, height = _random_person()
        joined = today - timedelta(days=random.randint(1, 300))
        m = Member(
            name=name,
            age=age,
            gender=gender,
            weight=weight,
            height=height,
            fitness_goal=random.choice(FITNESS_GOALS),
            join_date=joined,
            email=f"member{i+1}@example.com",
            phone=f"+91-8{random.randint(100000000, 999999999)}",
        )
        db.add(m)
        members.append(m)
    db.flush()
    log.info("Inserted %d members", len(members))

    for m in members:
        plan = random.choices(
            list(PlanType), weights=[5, 3, 2], k=1
        )[0]
        # Give some members a stale plan so we get expired counts
        start = m.join_date
        if random.random() < 0.3:
            start = start - timedelta(days=PLAN_DURATION_DAYS[plan] + random.randint(1, 60))
        end = start + timedelta(days=PLAN_DURATION_DAYS[plan])
        status = MembershipStatus.ACTIVE if end >= today else MembershipStatus.EXPIRED
        db.add(
            Membership(
                member_id=m.id,
                plan_type=plan,
                start_date=start,
                end_date=end,
                price=PLAN_PRICES[plan],
                status=status,
            )
        )
    db.flush()
    log.info("Inserted memberships")

    # Attendance: for the last 90 days, each member has 50% chance to attend
    attendance_records = 0
    for m in members:
        for offset in range(90):
            day = today - timedelta(days=offset)
            if day < m.join_date:
                continue
            if random.random() < 0.35:  # ~35% of days
                db.add(
                    Attendance(
                        member_id=m.id,
                        check_in_date=day,
                        duration_minutes=random.randint(30, 120),
                    )
                )
                attendance_records += 1
    db.flush()
    log.info("Inserted %d attendance records", attendance_records)

    # Workout plans: 1-2 per member
    plans_created = 0
    for m in members:
        for _ in range(random.randint(1, 2)):
            trainer = random.choice(trainer_objs)
            plan = WorkoutPlan(
                member_id=m.id,
                trainer_id=trainer.id,
                name=random.choice([
                    "Beginner Full-Body", "Upper Body Split", "Lower Body Split",
                    "HIIT Circuit", "Fat Burn Program", "Strength Foundation",
                    "Endurance Builder", "Mobility & Core",
                ]),
                goal=m.fitness_goal,
                duration_minutes=random.choice([45, 60, 75, 90]),
                trainer_notes="Focus on form. Increase weight gradually every week.",
                assigned_date=m.join_date + timedelta(days=random.randint(0, 30)),
            )
            picks = random.sample(EXERCISES, k=random.randint(4, 7))
            for name, sets, reps, weight in picks:
                plan.exercises.append(
                    Exercise(
                        name=name,
                        sets=sets,
                        repetitions=reps,
                        weight_kg=weight,
                        notes=None,
                    )
                )
            db.add(plan)
            plans_created += 1
    db.commit()
    log.info("Inserted %d workout plans", plans_created)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the gym database.")
    parser.add_argument("--reset", action="store_true", help="Delete existing rows first.")
    args = parser.parse_args()

    random.seed(42)  # reproducible demo data

    init_db()
    with SessionLocal() as db:
        if args.reset:
            wipe(db)
        seed(db)

    print("Seeding complete. Start the API with:  python main.py")


if __name__ == "__main__":
    main()
