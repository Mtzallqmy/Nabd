import asyncio
import os
import subprocess
import sys
from time import monotonic
from unittest.mock import AsyncMock

import pytest
from aiogram.methods import SendMessage
from aiogram.types import Update
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app import health, main
from app.config import Settings, settings
from app.database import make_engine


def migrate(url, revision):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", revision],
        env={**os.environ, "DATABASE_URL": url, "MIGRATION_DATABASE_URL": url},
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


def test_postgres_url_keeps_tls_and_hides_password():
    config = Settings(
        _env_file=None,
        database_url="postgresql://demo:p%40ss@localhost/nabd?sslmode=require&channel_binding=require",
    )
    url = config.database_dsn()
    assert url.drivername == "postgresql+psycopg"
    assert url.password == "p@ss"
    assert url.query["channel_binding"] == url.query["sslmode"] == "require"
    assert "p%40ss" not in repr(config)
    assert "p@ss" not in str(url)


@pytest.mark.parametrize("backend", ["sqlite", "postgresql"])
def test_upgrades_existing_projects(tmp_path, backend):
    url = (
        f"sqlite+aiosqlite:///{tmp_path / 'migration.db'}"
        if backend == "sqlite"
        else os.environ.get("NABD_TEST_POSTGRES_URL")
    )
    if url is None:
        pytest.skip("Set NABD_TEST_POSTGRES_URL to a dedicated empty database")
    migrate(url, "0001_create_projects")

    async def seed():
        engine = make_engine(make_url(url))
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO projects (owner, repository, registered_by, created_at) "
                    "VALUES ('Owner', 'Repo', 4095, CURRENT_TIMESTAMP)"
                )
            )
        await engine.dispose()

    asyncio.run(seed())
    migrate(url, "head")

    async def verify():
        engine = make_engine(make_url(url))
        async with engine.connect() as connection:
            assert await connection.scalar(text("SELECT id FROM telegram_users")) == 4095
            assert await connection.scalar(text("SELECT repository FROM projects")) == "Repo"
            assert await connection.scalar(text("SELECT count(*) FROM project_activity")) == 0
        await engine.dispose()

    asyncio.run(verify())


def test_fastapi_lifespan_and_health_with_simulated_poller(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'runtime.db'}"
    migrate(url, "head")
    database = make_engine(make_url(url))
    monkeypatch.setattr(main, "engine", database)
    monkeypatch.setattr(health, "engine", database)
    monkeypatch.setattr(settings, "bot_token", SecretStr("123456789:TEST_FAKE_TOKEN"))
    monkeypatch.setattr(settings, "telegram_admin_ids", "123456789")

    async def polling(*args, **kwargs):
        await asyncio.Future()

    monkeypatch.setattr(main.dispatcher, "start_polling", polling)
    with TestClient(main.app) as client:
        response = client.get("/healthz")
        assert response.status_code == 503
        assert response.json()["database"] == "ok"
        main.app.state.last_poll = monotonic()
        assert client.get("/healthz").status_code == 200
        main.app.state.last_poll -= health.POLL_FRESHNESS_SECONDS + 1
        assert client.get("/healthz").status_code == 503
    assert main.app.state.polling_task.done()


@pytest.mark.parametrize(
    "chat_type,user_id,allowed",
    [
        ("private", 42, True),
        ("private", 43, False),
        ("group", 42, False),
    ],
)
async def test_telegram_settings_dispatch(chat_type, user_id, allowed, monkeypatch):
    from aiogram import Bot

    monkeypatch.setattr(settings, "telegram_admin_ids", "42")
    bot = Bot("123456789:TEST_FAKE_TOKEN")
    call = AsyncMock()
    monkeypatch.setattr(bot.session, "make_request", call)
    update = Update.model_validate(
        {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "date": 1,
                "chat": {"id": user_id, "type": chat_type},
                "from": {"id": user_id, "is_bot": False, "first_name": "test"},
                "text": "/settings",
            },
        },
        context={"bot": bot},
    )
    # Clear the per-user rate limiter by using distinct update timings.
    clock = iter(range(10 if allowed else 100, 1000, 10))
    monkeypatch.setattr(main, "monotonic", lambda: next(clock))
    await main.dispatcher.feed_update(bot, update)
    request = call.await_args.args[1]
    assert isinstance(request, SendMessage)
    assert ("إعدادات نَبْض" in request.text) is allowed
    await bot.session.close()
