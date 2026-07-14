"""End-to-end smoke tests hitting the FastAPI app in-process.

Run with:
    python -m pytest -q
or simply:
    python tests/test_api.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Use an isolated SQLite DB so tests don't clobber the demo data
os.environ["DATABASE_URL"] = f"sqlite:///{ROOT / 'data' / 'test_gym.db'}"

from fastapi.testclient import TestClient  # noqa: E402

from app import app  # noqa: E402
from models.database import Base, engine  # noqa: E402


client = TestClient(app)


def _login() -> str:
    r = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def run_all() -> None:
    # Clean slate
    Base.metadata.drop_all(bind=engine)

    with client:  # triggers startup -> creates tables + admin
        token = _login()
        h = {"Authorization": f"Bearer {token}"}

        # Health
        assert client.get("/health").json()["status"] == "ok"

        # Create trainer
        r = client.post(
            "/trainers",
            headers=h,
            json={"name": "Coach A", "specialization": "Strength"},
        )
        assert r.status_code == 201, r.text
        trainer_id = r.json()["id"]

        # Create member
        r = client.post(
            "/members",
            headers=h,
            json={
                "name": "Test Member",
                "age": 30,
                "gender": "MALE",
                "weight": 75,
                "fitness_goal": "Endurance",
                "plan_type": "MONTHLY",
            },
        )
        assert r.status_code == 201, r.text
        member_id = r.json()["id"]

        # Attendance
        r = client.post("/attendance", headers=h, json={"member_id": member_id, "duration_minutes": 45})
        assert r.status_code == 201

        # Workout plan
        r = client.post(
            "/workout-plans",
            headers=h,
            json={
                "member_id": member_id,
                "trainer_id": trainer_id,
                "name": "Starter Plan",
                "duration_minutes": 60,
                "exercises": [
                    {"name": "Squat", "sets": 3, "repetitions": 10},
                    {"name": "Bench Press", "sets": 3, "repetitions": 8},
                ],
            },
        )
        assert r.status_code == 201, r.text

        # Analytics summary
        r = client.get("/analytics/summary", headers=h)
        assert r.status_code == 200
        data = r.json()
        assert data["total_members"] >= 1
        assert data["active_members"] >= 1

        # Chart generation
        r = client.post("/analytics/charts/generate", headers=h)
        assert r.status_code == 200

        print("All smoke tests passed.")


if __name__ == "__main__":
    run_all()
