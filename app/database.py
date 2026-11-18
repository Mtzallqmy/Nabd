from sqlalchemy import event
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


def make_engine(url: URL, **kwargs):
    if url.drivername == "postgresql+psycopg":
        kwargs.setdefault("connect_args", {"connect_timeout": 5, "prepare_threshold": None})
    database = create_async_engine(url, **kwargs)
    if url.drivername == "sqlite+aiosqlite":

        @event.listens_for(database.sync_engine, "connect")
        def enable_foreign_keys(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return database


engine = make_engine(settings.database_dsn(), pool_pre_ping=True)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
