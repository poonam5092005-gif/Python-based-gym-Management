"""Assign a workout plan to a member — with a dynamic list of exercises."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.api_client import APIError, get_client, render_api_status_sidebar  # noqa: E402
from dashboard.ui_theme import configure_page, section_title  # noqa: E402


configure_page("Workout Plans")
render_api_status_sidebar()
client = get_client()

section_title(
    "Workout plans",
    "Assign a training program",
    "Build a plan exercise-by-exercise and hand it to any member. Add rows in the table below to grow the plan.",
)


# ---------- Fetch dropdown data ----------
try:
    members = client.list_members(limit=500)
    trainers = client.list_trainers()
except APIError as exc:
    st.error(f"Could not load reference data — {exc.detail}")
    st.stop()

if not members:
    st.warning("No members yet. Register at least one on the **Add Member** page.")
    st.stop()
if not trainers:
    st.warning("No trainers yet. Add one on the **Trainers** page first.")
    st.stop()

member_options = {f"{m['name']}  (#{m['id']})": m["id"] for m in sorted(members, key=lambda x: x["name"].lower())}
trainer_options = {f"{t['name']}  (#{t['id']})": t["id"] for t in trainers}


# ---------- Editable exercise table lives in session_state ----------
if "wp_exercises_df" not in st.session_state:
    st.session_state.wp_exercises_df = pd.DataFrame(
        [
            {"name": "Squat", "sets": 4, "repetitions": 10, "weight_kg": 40.0, "notes": ""},
            {"name": "Bench Press", "sets": 3, "repetitions": 8, "weight_kg": 30.0, "notes": ""},
            {"name": "Plank", "sets": 3, "repetitions": 1, "weight_kg": 0.0, "notes": "60 sec hold"},
        ]
    )


col_a, col_b = st.columns(2)
selected_member = col_a.selectbox("Member *", list(member_options.keys()))
selected_trainer = col_b.selectbox("Trainer *", list(trainer_options.keys()))

col_c, col_d, col_e = st.columns([2, 1, 1])
plan_name = col_c.text_input("Plan name *", placeholder="e.g. Beginner Full-Body")
goal = col_d.selectbox(
    "Goal",
    ["Muscle gain", "Weight loss", "Endurance", "Strength training", "General fitness", "Flexibility"],
)
duration = col_e.number_input("Duration per session (min)", min_value=15, max_value=300, value=60, step=5)

trainer_notes = st.text_area(
    "Trainer notes",
    value="Focus on form. Increase weight gradually every week.",
    placeholder="Anything the member needs to know about form, progression, rest days, etc.",
    height=90,
)

st.markdown("#### Exercises")
st.caption("Add, edit, or remove rows below. Every plan needs at least one exercise.")

edited_df = st.data_editor(
    st.session_state.wp_exercises_df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "name": st.column_config.TextColumn("Exercise", required=True, max_chars=120),
        "sets": st.column_config.NumberColumn("Sets", min_value=1, max_value=20, step=1, default=3),
        "repetitions": st.column_config.NumberColumn("Reps", min_value=1, max_value=200, step=1, default=10),
        "weight_kg": st.column_config.NumberColumn("Weight (kg)", min_value=0.0, max_value=500.0, step=0.5),
        "notes": st.column_config.TextColumn("Notes"),
    },
    key="wp_editor",
)


assign = st.button("Assign Plan", type="primary", use_container_width=True)


if assign:
    if not plan_name.strip():
        st.error("Plan name is required.")
        st.stop()

    exercises: list[dict] = []
    for _, row in edited_df.iterrows():
        name_val = str(row.get("name", "")).strip()
        if not name_val:
            continue
        exercises.append(
            {
                "name": name_val,
                "sets": int(row.get("sets") or 3),
                "repetitions": int(row.get("repetitions") or 10),
                "weight_kg": float(row["weight_kg"]) if pd.notna(row.get("weight_kg")) and row.get("weight_kg") not in (None, "") else None,
                "notes": (str(row["notes"]).strip() or None) if pd.notna(row.get("notes")) else None,
            }
        )

    if not exercises:
        st.error("Add at least one exercise before assigning the plan.")
        st.stop()

    payload = {
        "member_id": member_options[selected_member],
        "trainer_id": trainer_options[selected_trainer],
        "name": plan_name.strip(),
        "goal": goal,
        "duration_minutes": int(duration),
        "trainer_notes": trainer_notes.strip() or None,
        "exercises": exercises,
    }

    try:
        plan = client.create_workout_plan(payload)
        st.success(
            f"Plan **{plan['name']}** (ID #{plan['id']}) with {len(plan['exercises'])} "
            f"exercises assigned to {selected_member.split('  (')[0]}."
        )
        st.balloons()
        # Reset the editor for the next plan
        st.session_state.wp_exercises_df = pd.DataFrame(
            [{"name": "", "sets": 3, "repetitions": 10, "weight_kg": 0.0, "notes": ""}]
        )
    except APIError as exc:
        st.error(f"Could not assign plan — {exc.detail}")


# ---------- Existing plans ----------
section_title("Library", "Recent workout plans", "Newest plans first, across every trainer and member.")

try:
    plans = client.list_workout_plans()
except APIError as exc:
    st.warning(f"Could not fetch plans — {exc.detail}")
    plans = []

if plans:
    rows = []
    member_names = {m["id"]: m["name"] for m in members}
    trainer_names = {t["id"]: t["name"] for t in trainers}
    for p in plans[:30]:
        rows.append(
            {
                "ID": p["id"],
                "Member": member_names.get(p["member_id"], f"#{p['member_id']}"),
                "Trainer": trainer_names.get(p["trainer_id"], f"#{p['trainer_id']}"),
                "Plan": p["name"],
                "Goal": p.get("goal") or "-",
                "Duration": f"{p['duration_minutes']} min",
                "Exercises": len(p.get("exercises") or []),
                "Assigned": p["assigned_date"],
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.info("No plans yet. Assign the first one above.")
