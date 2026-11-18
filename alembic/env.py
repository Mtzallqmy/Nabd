import asyncio

from sqlalchemy import pool
from sqlalchemy.engine import Connection

from alembic import context
from app import models  # noqa: F401 - register ORM metadata
from app.config import settings
from app.database import Base, make_engine

target_metadata = Base.metadata
url = settings.database_dsn(migration=True)


def run_migrations_offline() -> None:
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    database = make_engine(url, poolclass=pool.NullPool)
    try:
        async with database.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await database.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
