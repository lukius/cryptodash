from typing import AsyncGenerator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import async_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


bearer_scheme = HTTPBearer(auto_error=False)


async def get_auth_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return credentials.credentials


async def get_current_user(
    token: str = Depends(get_auth_token),
    db: AsyncSession = Depends(get_db),
):
    from backend.core.exceptions import InvalidSessionError
    from backend.services.auth import AuthService

    service = AuthService(db)
    try:
        return await service.validate_session(token)
    except InvalidSessionError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )


async def get_refresh_service(request: Request):
    return request.app.state.refresh_service


async def get_ws_manager(request: Request):
    return request.app.state.ws_manager


async def get_scheduler(request: Request):
    return request.app.state.scheduler
