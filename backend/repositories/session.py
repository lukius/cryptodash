from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.session import Session


class SessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, session: Session) -> Session:
        self.db.add(session)
        return session

    async def get_by_token(self, token: str) -> Session | None:
        result = await self.db.execute(select(Session).where(Session.token == token))
        return result.scalar_one_or_none()

    async def delete_by_token(self, token: str) -> None:
        await self.db.execute(delete(Session).where(Session.token == token))

    async def delete_all_for_user(self, user_id: str) -> None:
        await self.db.execute(delete(Session).where(Session.user_id == user_id))

    async def delete_all(self) -> None:
        await self.db.execute(delete(Session))

    async def delete_expired(self, before: datetime) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Session).where(Session.expires_at < before)
        )
        count = result.scalar_one()
        await self.db.execute(delete(Session).where(Session.expires_at < before))
        return count
