"""Thin, session-cached HTTP client for talking to the FastAPI backend.

Every Streamlit page imports `get_client()` and calls typed helpers instead of
building URLs / headers manually. Authentication happens once on demand and the
JWT is cached in Streamlit's session_state so subsequent page navigations don't
re-authenticate.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.config import settings  # noqa: E402


DEFAULT_BASE_URL = os.environ.get("GYM_API_URL", f"http://localhost:{settings.APP_PORT}")


class APIError(RuntimeError):
    """Raised when the backend returns a non-2xx response."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(f"[{status}] {detail}")
        self.status = status
        self.detail = detail


@dataclass
class APIClient:
    base_url: str
    token: str | None = None

    def _headers(self) -> dict[str, str]:
        h = {"Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _request(
        self, method: str, path: str, *, json: Any = None, params: dict | None = None, timeout: int = 15
    ) -> Any:
        url = f"{self.base_url.rstrip('/')}{path}"
        try:
            resp = requests.request(
                method, url, headers=self._headers(), json=json, params=params, timeout=timeout
            )
        except requests.exceptions.ConnectionError as exc:
            raise APIError(
                0,
                f"Could not reach the IronPulse API at {self.base_url}. "
                "Start it in another terminal with:  python main.py",
            ) from exc

        if resp.status_code >= 400:
            try:
                payload = resp.json()
                detail = payload.get("detail") or payload.get("error") or resp.text
                if isinstance(detail, list):
                    detail = "; ".join(str(d) for d in detail)
            except ValueError:
                detail = resp.text or resp.reason
            raise APIError(resp.status_code, str(detail))

        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    def login(self, username: str, password: str) -> dict:
        data = self._request("POST", "/auth/login", json={"username": username, "password": password})
        self.token = data["access_token"]
        return data

    def health(self) -> dict:
        return self._request("GET", "/health")

    # ---------- Members ----------
    def list_members(self, limit: int = 100, search: str | None = None, status: str | None = None) -> list[dict]:
        params: dict[str, Any] = {"limit": limit}
        if search:
            params["search"] = search
        if status:
            params["status"] = status
        return self._request("GET", "/members", params=params) or []

    def create_member(self, payload: dict) -> dict:
        return self._request("POST", "/members", json=payload)

    def renew_membership(self, member_id: int, plan_type: str) -> dict:
        return self._request(
            "POST", f"/members/{member_id}/memberships/renew", params={"plan_type": plan_type}
        )

    # ---------- Attendance ----------
    def record_attendance(self, member_id: int, duration_minutes: int | None) -> dict:
        payload: dict[str, Any] = {"member_id": member_id}
        if duration_minutes is not None:
            payload["duration_minutes"] = duration_minutes
        return self._request("POST", "/attendance", json=payload)

    def list_attendance(self, member_id: int | None = None, limit: int = 200) -> list[dict]:
        params: dict[str, Any] = {"limit": limit}
        if member_id is not None:
            params["member_id"] = member_id
        return self._request("GET", "/attendance", params=params) or []

    # ---------- Trainers ----------
    def list_trainers(self) -> list[dict]:
        return self._request("GET", "/trainers") or []

    def create_trainer(self, payload: dict) -> dict:
        return self._request("POST", "/trainers", json=payload)

    # ---------- Workout plans ----------
    def list_workout_plans(self, member_id: int | None = None) -> list[dict]:
        params = {"member_id": member_id} if member_id else None
        return self._request("GET", "/workout-plans", params=params) or []

    def create_workout_plan(self, payload: dict) -> dict:
        return self._request("POST", "/workout-plans", json=payload)

    # ---------- Analytics ----------
    def summary(self) -> dict:
        return self._request("GET", "/analytics/summary")

    def registrations(self, months: int = 12) -> list[dict]:
        return self._request("GET", "/analytics/registrations", params={"months": months}) or []

    def attendance_trends(self, days: int = 30) -> list[dict]:
        return self._request("GET", "/analytics/attendance-trends", params={"days": days}) or []

    def popular_workouts(self, top: int = 10) -> list[dict]:
        return self._request("GET", "/analytics/popular-workouts", params={"top": top}) or []

    def revenue(self, months: int = 12) -> list[dict]:
        return self._request("GET", "/analytics/revenue", params={"months": months}) or []

    def plan_distribution(self) -> list[dict]:
        return self._request("GET", "/analytics/plan-distribution") or []

    def generate_charts(self) -> dict:
        return self._request("POST", "/analytics/charts/generate")


def _bootstrap_login(client: APIClient) -> None:
    """Auto-login as the default admin so the demo works out of the box."""
    try:
        client.login(settings.ADMIN_USERNAME, settings.ADMIN_PASSWORD)
        st.session_state["gym_username"] = settings.ADMIN_USERNAME
    except APIError as exc:
        st.session_state["gym_login_error"] = exc.detail


def get_client() -> APIClient:
    """Return a session-scoped, authenticated APIClient."""
    if "gym_api_client" not in st.session_state:
        client = APIClient(base_url=DEFAULT_BASE_URL)
        _bootstrap_login(client)
        st.session_state["gym_api_client"] = client
    return st.session_state["gym_api_client"]


def render_api_status_sidebar() -> None:
    """Small status widget + brand block shown on every page's sidebar."""
    from dashboard.ui_theme import render_sidebar_brand  # avoid circular import

    render_sidebar_brand()
    client = get_client()
    with st.sidebar:
        if client.token:
            username = st.session_state.get("gym_username", "admin")
            st.success(f"Signed in as **{username}**")
        else:
            err = st.session_state.get("gym_login_error", "Not connected")
            st.error(f"API offline\n\n{err}")
        st.caption(f"API: {client.base_url}")
        if st.button("Reconnect", use_container_width=True):
            st.session_state.pop("gym_api_client", None)
            st.rerun()
