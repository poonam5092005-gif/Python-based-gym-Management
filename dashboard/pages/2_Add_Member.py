"""Register a new gym member.

Submits to the FastAPI backend at /members, so validation, logging, and any
future business rules live in one place (the service layer) — this page is
purely a UI on top.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.api_client import APIError, get_client, render_api_status_sidebar  # noqa: E402
from dashboard.ui_theme import configure_page, section_title  # noqa: E402


configure_page("Add Member")
render_api_status_sidebar()
client = get_client()

section_title(
    "Add Member",
    "Register a new member",
    "Fill the form below. The new record appears on the dashboard the moment you hit submit.",
)

FITNESS_GOALS = [
    "Weight loss",
    "Muscle gain",
    "Endurance",
    "General fitness",
    "Strength training",
    "Flexibility",
    "Sports performance",
]


with st.form("new_member_form", clear_on_submit=True, border=True):
    st.markdown("#### Personal Details")
    r1c1, r1c2, r1c3 = st.columns([2, 1, 1])
    name = r1c1.text_input("Full name *", placeholder="e.g. Ajay Kumar")
    age = r1c2.number_input("Age *", min_value=10, max_value=100, value=25, step=1)
    gender = r1c3.selectbox("Gender *", ["MALE", "FEMALE", "OTHER"])

    r2c1, r2c2, r2c3 = st.columns(3)
    weight = r2c1.number_input("Weight (kg) *", min_value=20.0, max_value=400.0, value=70.0, step=0.5)
    height = r2c2.number_input("Height (cm)", min_value=80.0, max_value=260.0, value=170.0, step=0.5)
    join_date = r2c3.date_input("Join date", value=date.today())

    st.markdown("#### Contact")
    r3c1, r3c2 = st.columns(2)
    email = r3c1.text_input("Email (optional)", placeholder="member@example.com")
    phone = r3c2.text_input("Phone (optional)", placeholder="+91-...")

    st.markdown("#### Goal & Plan")
    r4c1, r4c2 = st.columns([2, 1])
    goal = r4c1.selectbox("Fitness goal", FITNESS_GOALS, index=1)
    plan = r4c2.selectbox("Membership plan *", ["MONTHLY", "QUARTERLY", "YEARLY"], index=0)

    submitted = st.form_submit_button("Register Member", type="primary", use_container_width=True)


if submitted:
    if not name.strip():
        st.error("Name is required.")
    else:
        payload = {
            "name": name.strip(),
            "age": int(age),
            "gender": gender,
            "weight": float(weight),
            "height": float(height),
            "fitness_goal": goal,
            "plan_type": plan,
            "join_date": join_date.isoformat(),
        }
        if email.strip():
            payload["email"] = email.strip()
        if phone.strip():
            payload["phone"] = phone.strip()

        try:
            created = client.create_member(payload)
            st.success(
                f"Member **{created['name']}** registered with ID #{created['id']} "
                f"on a **{plan}** plan. The dashboard KPIs are already updated."
            )
            st.balloons()
        except APIError as exc:
            st.error(f"Could not register member — {exc.detail}")


# ---------- Recent members table ----------
section_title("Roster", "Recent members", "Newest registrations first.")

try:
    members = client.list_members(limit=15)
except APIError as exc:
    st.warning(f"Could not fetch members — {exc.detail}")
    members = []

if members:
    df = pd.DataFrame(members)[
        [
            "id", "name", "age", "gender", "weight", "fitness_goal",
            "join_date", "current_membership_status", "email",
        ]
    ]
    df.columns = ["ID", "Name", "Age", "Gender", "Weight (kg)", "Goal", "Joined", "Status", "Email"]
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No members registered yet. Fill out the form above to add the first one.")
