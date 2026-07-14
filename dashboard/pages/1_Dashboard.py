"""Live analytics dashboard — interactive Plotly charts + custom KPI cards.

Reads live data from the FastAPI backend so any entry made on the other pages
becomes visible on the next rerun.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.api_client import APIError, get_client, render_api_status_sidebar  # noqa: E402
from dashboard.ui_theme import (  # noqa: E402
    COLOR,
    PLOTLY_COLORWAY,
    configure_page,
    format_revenue,
    kpi_card,
    kpi_grid,
    section_title,
)


configure_page("Dashboard")
render_api_status_sidebar()
client = get_client()


# ---------- Sidebar controls ----------

with st.sidebar:
    st.markdown("### Controls")
    trend_days = st.slider("Attendance window (days)", 7, 180, 60, step=1)
    reg_months = st.slider("Growth window (months)", 3, 24, 12, step=1)
    auto_refresh = st.toggle("Auto-refresh every 10s", value=False, key="auto_refresh")
    refresh_now = st.button("Refresh now", type="primary", use_container_width=True)
    if refresh_now:
        st.rerun()
    st.divider()
    if st.button("Regenerate PNG exports", use_container_width=True):
        with st.spinner("Rendering PNG charts..."):
            try:
                results = client.generate_charts()
                st.success("Saved to data/plots/")
                st.json(results, expanded=False)
            except APIError as exc:
                st.error(f"Failed: {exc.detail}")


# ---------- Header ----------

section_title(
    "Live analytics",
    "Real-time gym overview",
    "Every number below is queried from the running API. Toggle auto-refresh in the sidebar to watch it tick.",
)


# ---------- Fetch data ----------

try:
    summary = client.summary()
    registrations = client.registrations(months=reg_months)
    trend = client.attendance_trends(days=trend_days)
    popular = client.popular_workouts(top=10)
    revenue = client.revenue(months=reg_months)
    plans = client.plan_distribution()
except APIError as exc:
    st.error(
        f"Cannot reach the API — {exc.detail}\n\n"
        "In a separate terminal run:\n\n"
        "    .\\.venv\\Scripts\\activate\n"
        "    python main.py"
    )
    st.stop()


# ---------- KPI grid (custom HTML cards — no more truncation) ----------

rev_display, rev_sub = format_revenue(summary["total_revenue"])

# Compute helpful percentages / deltas
total = max(summary["total_members"], 1)
active_pct = summary["active_members"] / total * 100
expired_pct = summary["expired_members"] / total * 100
avg_daily = summary["attendance_last_7_days"] / 7 if summary["attendance_last_7_days"] else 0

kpi_grid(
    [
        kpi_card(
            "Total Members",
            summary["total_members"],
            icon="users",
            tint="primary",
            sub=f"{summary['new_registrations_this_month']} joined this month",
        ),
        kpi_card(
            "Active Memberships",
            summary["active_members"],
            icon="zap",
            tint="green",
            sub=f"{active_pct:.0f}% of total",
            delta=f"{active_pct:.0f}% share",
            delta_up=True,
        ),
        kpi_card(
            "Expired",
            summary["expired_members"],
            icon="clock",
            tint="red",
            sub=f"{expired_pct:.0f}% of total",
            delta=f"{expired_pct:.0f}%",
            delta_up=False,
        ),
        kpi_card(
            "Total Revenue",
            rev_display,
            icon="rupee",
            tint="purple",
            prefix="&#8377;",
            sub=rev_sub,
            variant="kpi-card--wide",
        ),
    ]
)

kpi_grid(
    [
        kpi_card(
            "Check-ins (7d)",
            f"{summary['attendance_last_7_days']:,}",
            icon="calendar",
            tint="blue",
            sub=f"~{avg_daily:.0f} per day average",
        ),
        kpi_card(
            "New This Month",
            summary["new_registrations_this_month"],
            icon="trending",
            tint="green",
            sub="Fresh registrations",
        ),
        kpi_card(
            "Avg Member Age",
            summary["average_age"],
            icon="target",
            tint="yellow",
            sub="Years",
        ),
        kpi_card(
            "Avg Weight",
            f"{summary['average_weight_kg']:.1f}",
            icon="activity",
            tint="primary",
            sub="Kilograms",
        ),
    ]
)


# ---------- Shared Plotly layout ----------

def _plotly_layout(title: str = "") -> dict:
    return dict(
        title=dict(
            text=f"<b>{title}</b>" if title else "",
            font=dict(family="Inter", size=15, color=COLOR["navy"]),
            x=0.01, xanchor="left",
        ),
        margin=dict(l=10, r=10, t=45 if title else 10, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Inter", color=COLOR["navy"]),
        hoverlabel=dict(
            bgcolor=COLOR["navy"],
            font=dict(color="white", family="Inter", size=12),
            bordercolor=COLOR["navy"],
        ),
        colorway=PLOTLY_COLORWAY,
        xaxis=dict(gridcolor="#f1f5f9", zeroline=False, showline=False),
        yaxis=dict(gridcolor="#f1f5f9", zeroline=False, showline=False),
        showlegend=False,
    )


PLOTLY_CONFIG = {
    "displayModeBar": True,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
    "toImageButtonOptions": {"format": "png", "filename": "ironpulse_chart", "scale": 2},
}


# ---------- Tabbed charts ----------

st.markdown("")
tabs = st.tabs(["Overview", "Members", "Revenue", "Workouts & Engagement"])


# ---- Overview tab: two headline charts ----
with tabs[0]:
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("##### Monthly new registrations")
        if registrations:
            df = pd.DataFrame(registrations)
            fig = go.Figure(
                data=go.Bar(
                    x=df["month"],
                    y=df["new_members"],
                    marker=dict(
                        color=df["new_members"],
                        colorscale=[[0, COLOR["primary_light"]], [1, COLOR["primary_dark"]]],
                        line=dict(width=0),
                    ),
                    hovertemplate="<b>%{x}</b><br>%{y} new members<extra></extra>",
                )
            )
            fig.update_layout(**_plotly_layout(), height=340, bargap=0.35)
            fig.update_traces(marker_line_width=0)
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            st.info("No registrations yet.")

    with c2:
        st.markdown("##### Attendance trend")
        if trend:
            df = pd.DataFrame(trend)
            df["check_in_date"] = pd.to_datetime(df["check_in_date"])
            fig = go.Figure(
                data=go.Scatter(
                    x=df["check_in_date"],
                    y=df["check_ins"],
                    mode="lines",
                    line=dict(color=COLOR["info"], width=3, shape="spline"),
                    fill="tozeroy",
                    fillcolor="rgba(14,165,233,0.15)",
                    hovertemplate="<b>%{x|%b %d}</b><br>%{y} check-ins<extra></extra>",
                )
            )
            fig.update_layout(**_plotly_layout(), height=340)
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            st.info("No attendance yet.")


# ---- Members tab: plan mix + status + age distribution ----
with tabs[1]:
    c1, c2 = st.columns([1, 1])

    with c1:
        st.markdown("##### Membership plan mix")
        if plans:
            df = pd.DataFrame(plans)
            fig = go.Figure(
                data=go.Pie(
                    labels=df["plan_type"],
                    values=df["members"],
                    hole=0.55,
                    marker=dict(
                        colors=[COLOR["primary"], COLOR["info"], COLOR["purple"]],
                        line=dict(color="white", width=3),
                    ),
                    textinfo="label+percent",
                    textfont=dict(family="Inter", size=13, color="white"),
                    hovertemplate="<b>%{label}</b><br>%{value} members (%{percent})<extra></extra>",
                )
            )
            fig.update_layout(
                **_plotly_layout(),
                height=360,
                annotations=[
                    dict(
                        text=f"<b>{summary['total_members']}</b><br><span style='font-size:11px;color:#64748b'>members</span>",
                        showarrow=False,
                        font=dict(size=22, color=COLOR["navy"], family="Bebas Neue"),
                    )
                ],
            )
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            st.info("No plan data yet.")

    with c2:
        st.markdown("##### Active vs. expired")
        active = summary["active_members"]
        expired = summary["expired_members"]
        others = max(summary["total_members"] - active - expired, 0)
        status_df = pd.DataFrame({
            "Status": ["Active", "Expired", "Other"],
            "Members": [active, expired, others],
        })
        fig = go.Figure(
            data=go.Bar(
                x=status_df["Members"],
                y=status_df["Status"],
                orientation="h",
                marker=dict(
                    color=[COLOR["success"], COLOR["danger"], COLOR["muted"]],
                    line=dict(width=0),
                ),
                text=status_df["Members"],
                textposition="outside",
                textfont=dict(family="Inter", size=14, color=COLOR["navy"]),
                hovertemplate="<b>%{y}</b><br>%{x} members<extra></extra>",
            )
        )
        fig.update_layout(**_plotly_layout(), height=360, bargap=0.5)
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)


# ---- Revenue tab ----
with tabs[2]:
    st.markdown("##### Monthly membership revenue")
    if revenue:
        df = pd.DataFrame(revenue)

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=df["month"],
                y=df["revenue"],
                marker=dict(
                    color=df["revenue"],
                    colorscale=[[0, "#c084fc"], [1, "#7c3aed"]],
                ),
                hovertemplate="<b>%{x}</b><br>₹ %{y:,.0f}<extra></extra>",
                name="Revenue",
            )
        )
        # Add rolling average as a line overlay
        if len(df) >= 3:
            df["rolling"] = df["revenue"].rolling(3, min_periods=1).mean()
            fig.add_trace(
                go.Scatter(
                    x=df["month"],
                    y=df["rolling"],
                    mode="lines+markers",
                    line=dict(color=COLOR["primary"], width=3, shape="spline"),
                    marker=dict(color=COLOR["primary_dark"], size=8),
                    hovertemplate="<b>%{x}</b><br>3-month avg: ₹ %{y:,.0f}<extra></extra>",
                    name="3-month avg",
                )
            )
        fig.update_layout(**_plotly_layout(), height=420, bargap=0.35)
        fig.update_layout(
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        fig.update_yaxes(tickprefix="₹ ", tickformat=",.0f")
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

        total_rev = df["revenue"].sum()
        avg_rev = df["revenue"].mean()
        best_month = df.loc[df["revenue"].idxmax()]
        c1, c2, c3 = st.columns(3)
        c1.markdown(
            kpi_card(
                "Window Total", f"{int(total_rev):,}", icon="rupee", tint="purple", prefix="&#8377;",
                sub=f"across {len(df)} months",
            ),
            unsafe_allow_html=True,
        )
        c2.markdown(
            kpi_card(
                "Monthly Average", f"{int(avg_rev):,}", icon="trending", tint="blue", prefix="&#8377;",
                sub="Per month",
            ),
            unsafe_allow_html=True,
        )
        c3.markdown(
            kpi_card(
                "Best Month", best_month["month"], icon="star", tint="yellow",
                sub=f"₹ {int(best_month['revenue']):,}",
            ),
            unsafe_allow_html=True,
        )
    else:
        st.info("No revenue data yet.")


# ---- Workouts tab ----
with tabs[3]:
    c1, c2 = st.columns([3, 2])

    with c1:
        st.markdown("##### Top assigned exercises")
        if popular:
            df = pd.DataFrame(popular).sort_values("times_assigned")
            fig = go.Figure(
                data=go.Bar(
                    x=df["times_assigned"],
                    y=df["exercise"],
                    orientation="h",
                    marker=dict(
                        color=df["times_assigned"],
                        colorscale=[[0, "#fbbf24"], [1, COLOR["primary_dark"]]],
                        line=dict(width=0),
                    ),
                    text=df["times_assigned"],
                    textposition="outside",
                    textfont=dict(family="Inter", size=12, color=COLOR["navy"]),
                    hovertemplate="<b>%{y}</b><br>Assigned %{x} times<extra></extra>",
                )
            )
            fig.update_layout(**_plotly_layout(), height=460, bargap=0.35)
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            st.info("No workout plans assigned yet.")

    with c2:
        st.markdown("##### Engagement snapshot")
        st.markdown(
            kpi_card(
                "Check-ins per active member",
                f"{(summary['attendance_last_7_days'] / max(summary['active_members'],1)):.1f}",
                icon="activity",
                tint="green",
                sub="Last 7 days",
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            kpi_card(
                "Popular workout count",
                len(popular),
                icon="dumbbell",
                tint="primary",
                sub="Unique exercises in top list",
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            kpi_card(
                "Plan variety",
                len(plans),
                icon="target",
                tint="blue",
                sub="Distinct membership plans in use",
            ),
            unsafe_allow_html=True,
        )


# ---------- Raw snapshot ----------
with st.expander("Raw KPI snapshot (JSON)", expanded=False):
    st.json(summary)

st.caption(f"Generated at {summary['generated_at']}  ·  API {client.base_url}")


# ---------- Auto-refresh loop ----------
if auto_refresh:
    time.sleep(10)
    st.rerun()
