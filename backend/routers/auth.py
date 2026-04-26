from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import bearer_scheme, get_auth_token, get_db
from backend.utils import utc_isoformat
from backend.core.exceptions import (
    AccountExistsError,
    InvalidCredentialsError,
    InvalidSessionError,
    RateLimitedError,
)
from backend.schemas.auth import (
    AuthStatusResponse,
    LoginRequest,
    LoginResponse,
    SetupRequest,
)
from backend.services.auth import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/status")
async def get_auth_status(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> AuthStatusResponse:
    service = AuthService(db)
    account_exists = await service.account_exists()

    if credentials is not None:
        try:
            user = await service.validate_session(credentials.credentials)
            return AuthStatusResponse(
                account_exists=account_exists,
                authenticated=True,
                username=user.username,
            )
        except InvalidSessionError:
            pass

    return AuthStatusResponse(account_exists=account_exists, authenticated=False)


@router.post("/setup", status_code=status.HTTP_201_CREATED)
async def setup_account(
    body: SetupRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    service = AuthService(db)
    try:
        _user, session = await service.create_account(body.username, body.password)
    except AccountExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account already exists.",
        )
    await db.commit()
    return LoginResponse(token=session.token, expires_at=utc_isoformat(session.expires_at))


@router.post("/login")
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    service = AuthService(db)
    try:
        session = await service.authenticate(
            body.username, body.password, body.remember_me
        )
    except RateLimitedError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"message": str(exc), "retry_after": exc.retry_after},
            headers={"Retry-After": str(exc.retry_after)},
        )
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )
    await db.commit()
    return LoginResponse(token=session.token, expires_at=utc_isoformat(session.expires_at))


@router.post("/logout")
async def logout(
    token: str = Depends(get_auth_token),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = AuthService(db)
    try:
        await service.validate_session(token)
    except InvalidSessionError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session.",
        )
    await service.invalidate_session(token)
    await db.commit()
    return {"ok": True}
