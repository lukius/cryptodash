import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.database import init_db


@pytest_asyncio.fixture
async def db_engine():
    """Provide a fresh in-memory async SQLite engine per test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Provide an async database session backed by the in-memory engine."""
    session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    await init_db(engine=db_engine, session_factory=session_factory)

    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def test_client(db_engine):
    """Provide an async HTTP test client with the in-memory database wired in."""
    from fastapi import FastAPI
    from backend.core.dependencies import get_db

    session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    await init_db(engine=db_engine, session_factory=session_factory)

    # Import the real app factory once it exists (T10); stub for now
    try:
        from backend.app import create_app

        app = create_app()
    except ImportError:
        app = FastAPI()

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
