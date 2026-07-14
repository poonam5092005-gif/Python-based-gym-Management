<h1 align="center">IronPulse Fitness</h1>

<p align="center">
  <strong>Data-Driven Gym Management &amp; Fitness Analytics System</strong><br/>
  <em>Where Every Rep Counts.</em>
</p>

<p align="center">
  <img src="dashboard/assets/hero.png" alt="IronPulse Fitness hero" width="80%"/>
</p>

A production-style Python project that helps a gym manage its members, memberships, attendance, and workout plans — and turn every entry into rich, real-time analytics.

Built with **FastAPI + SQLAlchemy** on the backend, a **multi-page Streamlit web app** on the frontend (with a custom UI theme, hero landing page, and interactive **Plotly** dashboard), plus **Pandas / NumPy / Matplotlib / Seaborn** for analytics, **JWT auth** for security, and **Docker** for deployment.

> Ready to demo. Ships with seed data (40 members, 4 trainers, 65 workout plans, 1,000+ attendance records), a Postman collection, generated chart exports, real UI screenshots, and end-to-end tests.

---

## Table of Contents

1. [What It Does](#what-it-does)
2. [Screenshots](#screenshots)
3. [System Architecture](#system-architecture)
4. [Data Model](#data-model)
5. [Folder Structure](#folder-structure)
6. [Quick Start (Local)](#quick-start-local)
7. [Quick Start (Docker)](#quick-start-docker)
8. [Default Credentials](#default-credentials)
9. [API Reference](#api-reference)
10. [Testing with Postman](#testing-with-postman)
11. [Analytics & Visualizations](#analytics--visualizations)
12. [IronPulse Web App](#ironpulse-web-app)
13. [Logging & Error Handling](#logging--error-handling)
14. [Configuration](#configuration)
15. [Tech Stack](#tech-stack)
16. [Development Notes](#development-notes)
17. [Roadmap](#roadmap)

---

## What It Does

| Module | Capability |
| --- | --- |
| Member Management | Register, update, search members. Track monthly / quarterly / yearly memberships. Renew plans in one click. Live status (ACTIVE / EXPIRED). |
| Workout Tracking | Trainers assign workout plans containing exercises with sets, reps, weight, and notes. |
| Attendance | Daily check-ins with duration. Enforced unique-per-day. Filter reports by member and date range. |
| Analytics | Active vs expired members, monthly growth, attendance trends, revenue, popular workouts, plan distribution. |
| REST API | Fully documented FastAPI backend, JWT-secured, `/docs` Swagger UI. |
| Web App | Multi-page Streamlit site — landing hero, live dashboard with interactive Plotly charts, and forms for every core action. |

---

## Screenshots

**Landing page (IronPulse hero)**

![Landing page](docs/images/screenshots/home.png)

**Live analytics dashboard (custom KPI cards + interactive Plotly charts)**

![Dashboard](docs/images/screenshots/dashboard.png)

**Register a new member**

![Add Member form](docs/images/screenshots/add_member.png)

**Assign a workout plan (editable exercise grid)**

![Workout Plans page](docs/images/screenshots/workouts.png)

**Record attendance**

![Attendance page](docs/images/screenshots/attendance.png)

**Trainers page**

![Trainers page](docs/images/screenshots/trainers.png)

**Swagger UI — auto-generated REST API docs**

![Swagger docs](docs/images/screenshots/swagger.png)

---

## System Architecture

Layered, decoupled design so the UI and API can evolve independently:

![Architecture diagram](docs/images/architecture.png)

- **Clients** — Streamlit web app, Postman, or any HTTP client.
- **API layer (FastAPI)** — routers, middleware, JWT auth, CORS, and global exception handlers.
- **Service layer** — pure business logic (members, attendance, workouts, analytics, auth). No HTTP concerns leak in.
- **Data layer** — SQLAlchemy ORM models. SQLite by default, swappable to MySQL / Postgres by changing `DATABASE_URL`.

Design principles:

- **Separation of concerns.** Routes only handle HTTP. Services own business rules. Models own persistence.
- **Reusable analytics.** The same functions power the REST API, PNG chart exports, and the Streamlit dashboard.
- **Configurable.** Everything sensitive/tweakable lives in `.env`.
- **Extensible storage.** SQLite → MySQL by changing one env var.

---

## Data Model

![ER diagram](docs/images/er_diagram.png)

Relationships:

- One `Member` → many `Memberships` (renewals stack up over time).
- One `Member` → many `Attendance` records (unique per day).
- One `Member` → many `WorkoutPlans`.
- One `Trainer` → many `WorkoutPlans`.
- One `WorkoutPlan` → many `Exercises`.
- `User` = admin/trainer login accounts for the API.

---

## Folder Structure

```
python-gym-system/
├── app.py                          FastAPI app + startup + global error handlers
├── main.py                         Uvicorn runner
├── seed.py                         Demo data generator (40 members, 4 trainers, 65 plans, 1000+ check-ins)
├── requirements.txt
├── .env.example  .gitignore  Dockerfile  docker-compose.yml
│
├── models/                         Data layer
│   ├── database.py                 Engine, Session, get_db dependency
│   ├── db_models.py                SQLAlchemy ORM models
│   └── schemas.py                  Pydantic request/response models
│
├── services/                       Business logic layer
│   ├── member_service.py
│   ├── attendance_service.py
│   ├── workout_service.py
│   ├── analytics_service.py        Pandas + NumPy + Matplotlib / Seaborn
│   └── auth_service.py
│
├── routes/                         FastAPI routers grouped by resource
│   ├── auth.py members.py attendance.py workouts.py analytics.py
│   └── deps.py                     Shared JWT / role dependencies
│
├── utils/                          config · logger · security (JWT + bcrypt) · exceptions
│
├── dashboard/                      Streamlit web app
│   ├── streamlit_app.py            Landing / hero page
│   ├── ui_theme.py                 Brand, CSS, SVG icons, KPI cards, section titles
│   ├── api_client.py               Session-cached HTTP client → FastAPI
│   ├── assets/hero.png             Cinematic hero image
│   └── pages/
│       ├── 1_Dashboard.py          Interactive Plotly dashboard
│       ├── 2_Add_Member.py
│       ├── 3_Record_Attendance.py
│       ├── 4_Workout_Plans.py
│       └── 5_Trainers.py
│
├── postman/GymAPI.postman_collection.json
├── tests/                          test_api.py · test_dashboard_pages.py (Streamlit AppTest)
├── docs/                           generate_diagrams.py · images/ · screenshots/
├── data/                           gym.db · plots/*.png (auto-generated chart exports)
└── logs/                           rotating log files
```

---

## Quick Start (Local)

```bash
# 1. Create + activate a virtual environment
python -m venv .venv
.venv\Scripts\activate               # Windows
# source .venv/bin/activate          # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy env template
copy .env.example .env               # cp on macOS / Linux

# 4. Seed the database with demo data
python seed.py --reset

# 5. Start the API (terminal 1)
python main.py

# 6. Start the Streamlit web app (terminal 2)
streamlit run dashboard/streamlit_app.py
```

Open:

- **IronPulse Web App:** <http://localhost:8501>
- **Swagger API docs:**    <http://localhost:8000/docs>
- **Health check:**        <http://localhost:8000/health>

---

## Quick Start (Docker)

```bash
copy .env.example .env
docker compose up --build
```

Services exposed:

- FastAPI:  <http://localhost:8000/docs>
- Web app:  <http://localhost:8501>

---

## Default Credentials

On first boot, if no users exist, an admin is auto-created from `.env`:

```
Username: admin
Password: admin123
```

Change these before deploying anywhere real.

---

## API Reference

Full interactive documentation with try-it-out: <http://localhost:8000/docs>

| Category | Method | Path |
| --- | --- | --- |
| Auth | POST | `/auth/login` |
| Auth | POST | `/auth/register` (admin only) |
| Members | POST | `/members` |
| Members | GET  | `/members?search=&status=&limit=&offset=` |
| Members | GET  | `/members/{id}` |
| Members | PUT  | `/members/{id}` |
| Members | DELETE | `/members/{id}` (admin only) |
| Memberships | POST | `/members/{id}/memberships` |
| Memberships | POST | `/members/{id}/memberships/renew?plan_type=` |
| Memberships | GET  | `/members/{id}/memberships` |
| Attendance | POST | `/attendance` |
| Attendance | GET  | `/attendance?member_id=&start=&end=` |
| Trainers | POST/GET | `/trainers` |
| Trainers | GET  | `/trainers/{id}` |
| Workout Plans | POST/GET | `/workout-plans` |
| Workout Plans | GET  | `/workout-plans/{id}` |
| Workout Plans | DELETE | `/workout-plans/{id}` (admin only) |
| Analytics | GET  | `/analytics/summary` |
| Analytics | GET  | `/analytics/registrations?months=` |
| Analytics | GET  | `/analytics/attendance-trends?days=` |
| Analytics | GET  | `/analytics/popular-workouts?top=` |
| Analytics | GET  | `/analytics/revenue?months=` |
| Analytics | GET  | `/analytics/plan-distribution` |
| Analytics | POST | `/analytics/charts/generate` |
| Analytics | GET  | `/analytics/charts/{name}` |

---

## Testing with Postman

1. Import `postman/GymAPI.postman_collection.json`.
2. Run **Auth / Login** — the test script auto-saves the JWT into `{{token}}`.
3. Every other request uses that token via collection-level bearer auth.

Recommended demo order: Login → Create Member → Create Trainer → Assign Plan → Record Attendance → Analytics Summary → Generate All Charts.

---

## Analytics & Visualizations

The analytics service (`services/analytics_service.py`) builds Pandas DataFrames directly from the ORM so all KPIs are computed in one place. Interactive Plotly charts are rendered live on the dashboard; PNG exports are produced by the API endpoint below.

Auto-generated PNGs saved under `data/plots/`:

| File | Chart |
| --- | --- |
| `member_growth.png`        | Cumulative member growth over time |
| `attendance_trends.png`    | Daily check-ins for the last 30 days |
| `workout_distribution.png` | Top assigned exercises |
| `monthly_revenue.png`      | Membership revenue over months |
| `plan_distribution.png`    | Pie chart of active plan mix |

Regenerate anytime:

```bash
# From the dashboard: sidebar "Regenerate PNG exports"
# Or via the API:
curl -X POST http://localhost:8000/analytics/charts/generate -H "Authorization: Bearer <TOKEN>"
```

---

## IronPulse Web App

A multi-page Streamlit site with a custom design system.

- **Home** — cinematic hero, live KPI strip, quick-action buttons, 6-card feature grid, 3-step "how it works" section, testimonials, CTA banner.
- **Dashboard** — 8 custom KPI cards (with gradient icons, delta chips, and Indian-format numbers so nothing truncates), four Plotly tabs:
  - **Overview** — registrations bar + attendance area chart.
  - **Members** — donut plan-mix + horizontal status bars.
  - **Revenue** — revenue bars + 3-month rolling average overlay + summary KPIs.
  - **Workouts & Engagement** — top exercises + engagement mini-KPIs.
- **Add Member** — validated form → `POST /members` → row appears in the "Recent Members" table.
- **Record Attendance** — member dropdown + duration → `POST /attendance`. Handles duplicate-day conflicts.
- **Workout Plans** — member + trainer dropdowns, editable data grid for exercises, `POST /workout-plans`.
- **Trainers** — add trainer form + full roster.

Every form goes through the API, so validation, logging, and error handling live in a single place. New entries appear on the dashboard immediately (or you can toggle **Auto-refresh every 10s** to watch it tick live).

---

## Logging & Error Handling

- **Rotating logs** at `logs/gym_system.log` (2 MB × 5 backups) plus stdout.
- Every API request is logged with method, path, status, and latency.
- Domain events logged: member registrations, updates, deletions, membership creations & renewals, attendance check-ins, workout-plan assignments, user creations & logins, chart generations.
- **Central error handling** in `app.py`:
  - `NotFoundError` → 404 JSON
  - `ConflictError` → 409 JSON (duplicate email, duplicate attendance)
  - `ValidationError` (services) or `RequestValidationError` (Pydantic) → 422 with structured field errors
  - `AuthError` → 401 · `ForbiddenError` → 403
  - Any unhandled exception → generic 500 with logged traceback (nothing internal ever leaks)

---

## Configuration

All settings live in `.env`. See `.env.example` for the full list.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_HOST` / `APP_PORT` | `0.0.0.0 / 8000` | Uvicorn bind address |
| `APP_ENV` | `development` | Enables auto-reload |
| `DATABASE_URL` | `sqlite:///./data/gym.db` | Any SQLAlchemy URL |
| `JWT_SECRET_KEY` | `change-me...` | HMAC signing key |
| `JWT_EXPIRE_MINUTES` | `1440` | Access-token lifetime |
| `ADMIN_USERNAME` | `admin` | Bootstrap admin username |
| `ADMIN_PASSWORD` | `admin123` | Bootstrap admin password |
| `LOG_LEVEL` | `INFO` | DEBUG / INFO / WARNING / ERROR |
| `LOG_FILE` | `logs/gym_system.log` | Log destination |

---

## Tech Stack

| Layer | Library |
| --- | --- |
| Web framework | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.x |
| Validation | Pydantic v2 + Pydantic Settings + email-validator |
| Auth | python-jose (JWT) + bcrypt |
| Analytics | Pandas + NumPy |
| Static charts | Matplotlib + Seaborn |
| Interactive charts | Plotly |
| Web UI | Streamlit (multi-page) |
| Storage | SQLite (default) · MySQL / Postgres ready |
| Tooling | Docker + docker-compose · Playwright (for docs screenshots) |

---

## Development Notes

- **Testing:**
  - `python tests/test_api.py` — end-to-end HTTP smoke test using FastAPI's `TestClient` (login → members → trainers → workouts → attendance → analytics → charts).
  - `python tests/test_dashboard_pages.py` — loads every Streamlit page with `AppTest` and fails on any runtime exception.
- **Docs pipeline:**
  - `python docs/generate_diagrams.py` — regenerate architecture + ER PNGs.
  - `python docs/take_screenshots.py` — regenerate all UI screenshots (requires both servers running + Playwright chromium installed).
- **Deliverables:**
  - `docs/IronPulse_Presentation.pptx` — final-year project slide deck.
  - `docs/IronPulse_Project_Report.docx` — full written project report.

---

## Roadmap

Shipped:

- Docker + docker-compose deployment
- Multi-page Streamlit web app with custom UI theme
- Interactive Plotly dashboard
- JWT authentication with admin / trainer roles
- Auto-generated Postman collection
- End-to-end smoke tests

Nice-to-add next:

- Automated email / SMS reminders for expiring memberships (Celery + Redis)
- Cloud deploy templates (Render / Railway / AWS ECS)
- Google Sheets / Excel export of analytics
- Multi-branch / multi-gym support
- Trainer-facing mobile app on the same API

---

<p align="center">
  <strong>Where Every Rep Counts.</strong><br/>
  Built with FastAPI · SQLAlchemy · Pandas · Plotly · Streamlit.
</p>
