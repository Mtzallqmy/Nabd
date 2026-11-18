import pytest_asyncio
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker

from app import models  # noqa: F401 - register ORM metadata
from app.database import Base, make_engine


@pytest_asyncio.fixture
async def test_engine():
    engine = make_engine(make_url("sqlite+aiosqlite:///:memory:"))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session
