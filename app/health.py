import asyncio
from time import monotonic

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.database import engine

POLL_FRESHNESS_SECONDS = 45


def setup_health_app(app: FastAPI):
    @app.get("/healthz")
    async def health_check():
        try:
            async with asyncio.timeout(3), engine.connect() as connection:
                await connection.execute(text("SELECT version_num FROM alembic_version"))
            database_ok = True
        except Exception:
            database_ok = False

        task = getattr(app.state, "polling_task", None)
        last_poll = getattr(app.state, "last_poll", float("-inf"))
        polling_ok = (
            task is not None
            and not task.done()
            and monotonic() - last_poll < POLL_FRESHNESS_SECONDS
        )
        ready = database_ok and polling_ok
        return JSONResponse(
            status_code=200 if ready else 503,
            content={
                "status": "ok" if ready else "unhealthy",
                "database": "ok" if database_ok else "unavailable",
                "telegram_poller": "receiving" if polling_ok else "unavailable",
            },
        )
