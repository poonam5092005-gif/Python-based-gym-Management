"""FastAPI application entrypoint.

Boot order:
    1. Configure logging.
    2. Create DB tables (if missing).
    3. Bootstrap default admin user (only if no users exist).
    4. Mount routers.
    5. Register global exception handlers so domain exceptions map cleanly
       to structured JSON responses.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from models.database import SessionLocal, init_db
from routes.analytics import router as analytics_router
from routes.attendance import router as attendance_router
from routes.auth import router as auth_router
from routes.members import router as members_router
from routes.workouts import plan_router, trainer_router
from services.auth_service import ensure_default_admin
from utils.config import settings
from utils.exceptions import GymSystemError
from utils.logger import get_logger

log = get_logger("gym_system")


@asynccontextmanager
async def lifespan(_: FastAPI):
    log.info("Booting %s (env=%s)", settings.APP_NAME, settings.APP_ENV)
    init_db()
    with SessionLocal() as db:
        ensure_default_admin(db)
    log.info("Startup complete. Docs at http://%s:%s/docs", settings.APP_HOST, settings.APP_PORT)
    yield
    log.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "REST API for a full-featured gym management platform: members, "
        "memberships, attendance, workout plans, and rich analytics with "
        "auto-generated Matplotlib/Seaborn visualizations."
    ),
    version="1.0.0",
    lifespan=lifespan,
    contact={"name": "Gym Ops", "email": "ops@gym.local"},
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Request logging middleware ----------


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    log.info(
        "%s %s -> %s (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


# ---------- Exception handlers ----------


@app.exception_handler(GymSystemError)
async def gym_error_handler(_: Request, exc: GymSystemError) -> JSONResponse:
    log.warning("Domain error [%s]: %s", exc.__class__.__name__, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.__class__.__name__, "detail": exc.message},
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": "ValidationError",
            "detail": "One or more fields failed validation.",
            "errors": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
    log.exception("Unhandled server error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "ServerError",
            "detail": "Something went wrong. Check server logs for details.",
        },
    )


# ---------- Root + health ----------


@app.get("/", tags=["Meta"])
def root() -> dict:
    return {
        "app": settings.APP_NAME,
        "version": app.version,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "health": "/health",
    }


@app.get("/health", tags=["Meta"])
def health() -> dict:
    return {"status": "ok"}


# ---------- Routers ----------

app.include_router(auth_router)
app.include_router(members_router)
app.include_router(attendance_router)
app.include_router(trainer_router)
app.include_router(plan_router)
app.include_router(analytics_router)
