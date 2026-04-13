from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.configuration import Configuration


class ConfigRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def set_default(self, key: str, value: str) -> None:
        """Insert the key/value only if the key does not already exist."""
        result = await self.db.execute(
            select(Configuration).where(Configuration.key == key)
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            self.db.add(
                Configuration(
                    key=key, value=value, updated_at=datetime.now(timezone.utc)
                )
            )

    async def get(self, key: str) -> str | None:
        result = await self.db.execute(
            select(Configuration).where(Configuration.key == key)
        )
        row = result.scalar_one_or_none()
        return row.value if row is not None else None

    async def set(self, key: str, value: str) -> None:
        result = await self.db.execute(
            select(Configuration).where(Configuration.key == key)
        )
        row = result.scalar_one_or_none()
        if row is None:
            self.db.add(
                Configuration(
                    key=key, value=value, updated_at=datetime.now(timezone.utc)
                )
            )
        else:
            row.value = value
            row.updated_at = datetime.now(timezone.utc)

    async def get_int(self, key: str) -> int | None:
        value = await self.get(key)
        if value is None:
            return None
        return int(value)
