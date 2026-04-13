from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import User


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, user: User) -> User:
        self.db.add(user)
        return user

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: str) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def update_password_hash(self, user_id: str, password_hash: str) -> None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is not None:
            user.password_hash = password_hash

    async def get_first(self) -> User | None:
        result = await self.db.execute(select(User))
        return result.scalars().first()

    async def exists(self) -> bool:
        result = await self.db.execute(select(func.count()).select_from(User))
        count = result.scalar_one()
        return count > 0
