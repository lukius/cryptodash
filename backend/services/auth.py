from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import (
    AccountExistsError,
    AccountNotFoundError,
    InvalidCredentialsError,
    InvalidSessionError,
    RateLimitedError,
)
from backend.core.security import generate_token, hash_password, verify_password
from backend.models.session import Session
from backend.models.user import User
from backend.repositories.session import SessionRepository
from backend.repositories.user import UserRepository

# Module-level rate limiting state (resets on app restart — acceptable for single-user)
_failed_attempts: int = 0
_lockout_until: datetime | None = None

LOCKOUT_THRESHOLD = 5
LOCKOUT_DURATION = timedelta(seconds=30)


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.session_repo = SessionRepository(db)

    async def account_exists(self) -> bool:
        return await self.user_repo.exists()

    async def create_account(
        self, username: str, password: str
    ) -> tuple[User, Session]:
        if await self.user_repo.exists():
            raise AccountExistsError("An account already exists.")

        now = datetime.now(timezone.utc)
        user = User(
            id=str(uuid4()),
            username=username,
            password_hash=hash_password(password),
            created_at=now,
        )
        await self.user_repo.create(user)
        await self.db.flush()  # ensure user row exists before inserting session (FK)

        session = Session(
            id=str(uuid4()),
            user_id=user.id,
            token=generate_token(),
            created_at=now,
            expires_at=now + timedelta(days=7),
        )
        await self.session_repo.create(session)

        return user, session

    async def authenticate(
        self, username: str, password: str, remember_me: bool
    ) -> Session:
        global _failed_attempts, _lockout_until

        now = datetime.now(timezone.utc)

        if _lockout_until is not None and now < _lockout_until:
            remaining = int((_lockout_until - now).total_seconds())
            raise RateLimitedError(retry_after=remaining)

        user = await self.user_repo.get_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            _failed_attempts += 1
            if _failed_attempts >= LOCKOUT_THRESHOLD:
                _lockout_until = now + LOCKOUT_DURATION
                raise RateLimitedError(
                    retry_after=int(LOCKOUT_DURATION.total_seconds())
                )
            raise InvalidCredentialsError("Invalid username or password.")

        _failed_attempts = 0
        _lockout_until = None

        expiry_days = 30 if remember_me else 7
        session = Session(
            id=str(uuid4()),
            user_id=user.id,
            token=generate_token(),
            created_at=now,
            expires_at=now + timedelta(days=expiry_days),
        )
        await self.session_repo.create(session)
        return session

    async def validate_session(self, token: str) -> User:
        session = await self.session_repo.get_by_token(token)
        if session is None:
            raise InvalidSessionError("Session not found.")

        now = datetime.now(timezone.utc)
        expires_at = session.expires_at
        # Normalise to aware datetime if stored as naive UTC
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if now >= expires_at:
            raise InvalidSessionError("Session has expired.")

        user = await self.user_repo.get_by_id(session.user_id)
        if user is None:
            raise InvalidSessionError("User not found.")

        return user

    async def invalidate_session(self, token: str) -> None:
        await self.session_repo.delete_by_token(token)

    async def invalidate_all_sessions(self) -> None:
        await self.session_repo.delete_all()

    async def reset_password(self, new_password: str) -> None:
        user = await self.user_repo.get_first()
        if user is None:
            raise AccountNotFoundError("No user account found.")

        await self.user_repo.update_password_hash(user.id, hash_password(new_password))
        await self.invalidate_all_sessions()
