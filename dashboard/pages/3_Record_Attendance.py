"""Record a gym check-in for an existing member."""

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


configure_page("Record Attendance")
render_api_status_sidebar()
client = get_client()

section_title(
    "Attendance",
    "Record a check-in",
    "One check-in per member per day. Duration is optional but helps the analytics.",
)


# ---------- Load member list for the dropdown ----------
try:
    members = client.list_members(limit=500)
except APIError as exc:
    st.error(f"Could not load members — {exc.detail}")
    st.stop()

if not members:
    st.warning("No members registered yet. Add one on the **Add Member** page first.")
    st.stop()

# Sort alphabetically for a friendlier dropdown
members_sorted = sorted(members, key=lambda m: m["name"].lower())
options = {f"{m['name']}  (#{m['id']})": m["id"] for m in members_sorted}


with st.form("attendance_form", clear_on_submit=True, border=True):
    c1, c2 = st.columns([3, 1])
    selected_label = c1.selectbox("Member *", list(options.keys()))
    duration = c2.number_input(
        "Duration (minutes)", min_value=0, max_value=600, value=60, step=5,
        help="Set to 0 to skip.",
    )

    submitted = st.form_submit_button("Record Check-in", type="primary", use_container_width=True)


if submitted:
    member_id = options[selected_label]
    duration_val = int(duration) if duration and duration > 0 else None
    try:
        entry = client.record_attendance(member_id=member_id, duration_minutes=duration_val)
        st.success(
            f"Check-in recorded for **{selected_label.split('  (')[0]}** on {entry['check_in_date']}"
            + (f" ({entry['duration_minutes']} min)." if entry.get("duration_minutes") else ".")
        )
    except APIError as exc:
        if exc.status == 409:
            st.warning(f"Already checked in today: {exc.detail}")
        else:
            st.error(f"Could not record attendance — {exc.detail}")


# ---------- Recent attendance ----------
section_title("Log", "Recent check-ins", "Newest first.")

try:
    entries = client.list_attendance(limit=25)
except APIError as exc:
    st.warning(f"Could not fetch attendance — {exc.detail}")
    entries = []

if entries:
    member_names = {m["id"]: m["name"] for m in members}
    df = pd.DataFrame(entries)
    df["member_name"] = df["member_id"].map(member_names).fillna("Unknown")
    df = df[["id", "member_name", "member_id", "check_in_date", "check_in_time", "duration_minutes"]]
    df.columns = ["ID", "Member", "Member ID", "Date", "Time", "Duration (min)"]
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No attendance records yet.")
