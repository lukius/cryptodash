from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.config import config


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    f"sqlite+aiosqlite:///{config.db_path}",
    echo=False,
    connect_args={"timeout": 30},
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db(
    engine: AsyncEngine | None = None,
    session_factory: async_sessionmaker | None = None,
) -> None:
    """Enable WAL mode, foreign keys, create all tables, and seed defaults."""
    import backend.models  # noqa: F401 — ensure all models are registered on Base.metadata
    from backend.repositories.config import ConfigRepository

    _engine = engine or globals()["engine"]
    _session_factory = session_factory or globals()["async_session"]

    async with _engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Base.metadata.create_all)

    async with _session_factory() as session:
        config_repo = ConfigRepository(session)
        await config_repo.set_default("refresh_interval_minutes", "15")
        await session.commit()
