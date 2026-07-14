"""Convenience runner. Starts the API with Uvicorn using .env config."""

from __future__ import annotations

import uvicorn

from utils.config import settings


def main() -> None:
    uvicorn.run(
        "app:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_ENV == "development",
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
