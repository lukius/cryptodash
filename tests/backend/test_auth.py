"""Tests for the auth service, schemas, and router (T05)."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.dependencies import get_db
from backend.database import init_db
from backend.routers.auth import router as auth_router
import backend.services.auth as auth_module


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def fresh_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def auth_client(fresh_engine):
    """HTTP test client wired to the auth router with a fresh in-memory DB."""
    session_factory = async_sessionmaker(
        fresh_engine, class_=AsyncSession, expire_on_commit=False
    )
    await init_db(engine=fresh_engine, session_factory=session_factory)

    app = FastAPI()
    app.include_router(auth_router)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture(autouse=True)
def reset_auth_state():
    """Reset module-level rate limiting state before each test."""
    auth_module._failed_attempts = 0
    auth_module._lockout_until = None
    yield
    auth_module._failed_attempts = 0
    auth_module._lockout_until = None


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------


def test_setup_request_password_mismatch():
    from pydantic import ValidationError
    from backend.schemas.auth import SetupRequest

    with pytest.raises(ValidationError):
        SetupRequest(
            username="alice", password="password1", password_confirm="password2"
        )


def test_setup_request_password_too_short():
    from pydantic import ValidationError
    from backend.schemas.auth import SetupRequest

    with pytest.raises(ValidationError):
        SetupRequest(username="alice", password="short", password_confirm="short")


def test_setup_request_valid():
    from backend.schemas.auth import SetupRequest

    req = SetupRequest(
        username="alice", password="password1", password_confirm="password1"
    )
    assert req.username == "alice"
    assert req.password == "password1"


def test_login_request_defaults():
    from backend.schemas.auth import LoginRequest

    req = LoginRequest(username="alice", password="password1")
    assert req.remember_me is False


def test_auth_status_response_defaults():
    from backend.schemas.auth import AuthStatusResponse

    resp = AuthStatusResponse(account_exists=False, authenticated=False)
    assert resp.username is None


# ---------------------------------------------------------------------------
# Setup endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_setup_creates_account_returns_token(auth_client):
    resp = await auth_client.post(
        "/api/auth/setup",
        json={
            "username": "alice",
            "password": "password1",
            "password_confirm": "password1",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "token" in data
    assert "expires_at" in data
    assert len(data["token"]) > 0


@pytest.mark.asyncio
async def test_setup_returns_409_if_account_exists(auth_client):
    await auth_client.post(
        "/api/auth/setup",
        json={
            "username": "alice",
            "password": "password1",
            "password_confirm": "password1",
        },
    )
    resp = await auth_client.post(
        "/api/auth/setup",
        json={
            "username": "bob",
            "password": "password2",
            "password_confirm": "password2",
        },
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_setup_password_too_short_returns_422(auth_client):
    resp = await auth_client.post(
        "/api/auth/setup",
        json={"username": "alice", "password": "short", "password_confirm": "short"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_setup_password_mismatch_returns_422(auth_client):
    resp = await auth_client.post(
        "/api/auth/setup",
        json={
            "username": "alice",
            "password": "password1",
            "password_confirm": "different",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_setup_token_expires_in_7_days(auth_client):
    resp = await auth_client.post(
        "/api/auth/setup",
        json={
            "username": "alice",
            "password": "password1",
            "password_confirm": "password1",
        },
    )
    assert resp.status_code == 201
    expires_at = datetime.fromisoformat(resp.json()["expires_at"])
    now = datetime.now(timezone.utc)
    delta = expires_at - now
    assert timedelta(days=6, hours=23) < delta < timedelta(days=7, hours=1)


# ---------------------------------------------------------------------------
# Login endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_valid_credentials_returns_token(auth_client):
    await auth_client.post(
        "/api/auth/setup",
        json={
            "username": "alice",
            "password": "password1",
            "password_confirm": "password1",
        },
    )
    resp = await auth_client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "password1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert "expires_at" in data


@pytest.mark.asyncio
async def test_login_invalid_password_returns_401(auth_client):
    await auth_client.post(
        "/api/auth/setup",
        json={
            "username": "alice",
            "password": "password1",
            "password_confirm": "password1",
        },
    )
    resp = await auth_client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user_returns_401(auth_client):
    await auth_client.post(
        "/api/auth/setup",
        json={
            "username": "alice",
            "password": "password1",
            "password_confirm": "password1",
        },
    )
    resp = await auth_client.post(
        "/api/auth/login",
        json={"username": "nobody", "password": "password1"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_remember_me_sets_30_day_expiry(auth_client):
    await auth_client.post(
        "/api/auth/setup",
        json={
            "username": "alice",
            "password": "password1",
            "password_confirm": "password1",
        },
    )
    resp = await auth_client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "password1", "remember_me": True},
    )
    assert resp.status_code == 200
    expires_at = datetime.fromisoformat(resp.json()["expires_at"])
    now = datetime.now(timezone.utc)
    delta = expires_at - now
    assert timedelta(days=29, hours=23) < delta < timedelta(days=30, hours=1)


@pytest.mark.asyncio
async def test_login_default_sets_7_day_expiry(auth_client):
    await auth_client.post(
        "/api/auth/setup",
        json={
            "username": "alice",
            "password": "password1",
            "password_confirm": "password1",
        },
    )
    resp = await auth_client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "password1"},
    )
    assert resp.status_code == 200
    expires_at = datetime.fromisoformat(resp.json()["expires_at"])
    now = datetime.now(timezone.utc)
    delta = expires_at - now
    assert timedelta(days=6, hours=23) < delta < timedelta(days=7, hours=1)


@pytest.mark.asyncio
async def test_login_rate_limit_after_5_failures(auth_client):
    await auth_client.post(
        "/api/auth/setup",
        json={
            "username": "alice",
            "password": "password1",
            "password_confirm": "password1",
        },
    )
    for _ in range(4):
        resp = await auth_client.post(
            "/api/auth/login",
            json={"username": "alice", "password": "wrongpassword"},
        )
        assert resp.status_code == 401

    # 5th failure triggers lockout
    resp = await auth_client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "wrongpassword"},
    )
    assert resp.status_code == 429
    data = resp.json()
    # detail is {"message": ..., "retry_after": N}
    assert "retry_after" in data["detail"]
    assert data["detail"]["retry_after"] > 0


@pytest.mark.asyncio
async def test_login_during_lockout_returns_429(auth_client):
    await auth_client.post(
        "/api/auth/setup",
        json={
            "username": "alice",
            "password": "password1",
            "password_confirm": "password1",
        },
    )
    for _ in range(5):
        await auth_client.post(
            "/api/auth/login",
            json={"username": "alice", "password": "wrongpassword"},
        )

    # Subsequent attempt during lockout
    resp = await auth_client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "password1"},
    )
    assert resp.status_code == 429


@pytest.mark.asyncio
async def test_login_lockout_timer_not_extended_on_locked_attempt(auth_client):
    """A login attempt during lockout must NOT push _lockout_until further."""
    await auth_client.post(
        "/api/auth/setup",
        json={
            "username": "alice",
            "password": "password1",
            "password_confirm": "password1",
        },
    )
    # Trigger lockout
    for _ in range(5):
        await auth_client.post(
            "/api/auth/login",
            json={"username": "alice", "password": "wrongpassword"},
        )

    lockout_at = auth_module._lockout_until
    assert lockout_at is not None

    # Another attempt during lockout — timer must stay the same
    await auth_client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "wrongpassword"},
    )
    assert auth_module._lockout_until == lockout_at


@pytest.mark.asyncio
async def test_login_resets_lockout_counter_on_success(auth_client):
    await auth_client.post(
        "/api/auth/setup",
        json={
            "username": "alice",
            "password": "password1",
            "password_confirm": "password1",
        },
    )
    for _ in range(3):
        await auth_client.post(
            "/api/auth/login",
            json={"username": "alice", "password": "wrongpassword"},
        )

    resp = await auth_client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "password1"},
    )
    assert resp.status_code == 200
    assert auth_module._failed_attempts == 0
    assert auth_module._lockout_until is None


@pytest.mark.asyncio
async def test_login_lockout_retry_after_header(auth_client):
    """429 response includes Retry-After header."""
    await auth_client.post(
        "/api/auth/setup",
        json={
            "username": "alice",
            "password": "password1",
            "password_confirm": "password1",
        },
    )
    for _ in range(5):
        await auth_client.post(
            "/api/auth/login",
            json={"username": "alice", "password": "wrongpassword"},
        )
    resp = await auth_client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "wrongpassword"},
    )
    assert resp.status_code == 429
    assert "retry-after" in resp.headers


# ---------------------------------------------------------------------------
# Logout endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_logout_invalidates_session(auth_client):
    setup_resp = await auth_client.post(
        "/api/auth/setup",
        json={
            "username": "alice",
            "password": "password1",
            "password_confirm": "password1",
        },
    )
    token = setup_resp.json()["token"]

    resp = await auth_client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    # Token must be invalidated — a second request with it must return 401
    resp2 = await auth_client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_logout_without_token_returns_401(auth_client):
    resp = await auth_client.post("/api/auth/logout")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_with_invalid_token_returns_401(auth_client):
    resp = await auth_client.post(
        "/api/auth/logout",
        headers={"Authorization": "Bearer invalidtoken"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Session validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_expired_session_raises_invalid_session(fresh_engine):
    """validate_session raises InvalidSessionError for expired sessions."""
    from backend.core.exceptions import InvalidSessionError
    from backend.models.session import Session
    from backend.models.user import User
    from backend.services.auth import AuthService
    from backend.core.security import hash_password, generate_token

    session_factory = async_sessionmaker(
        fresh_engine, class_=AsyncSession, expire_on_commit=False
    )
    await init_db(engine=fresh_engine, session_factory=session_factory)

    async with session_factory() as db:
        now = datetime.now(timezone.utc)
        user = User(
            id=str(uuid4()),
            username="alice",
            password_hash=hash_password("password1"),
            created_at=now,
        )
        db.add(user)
        await db.flush()  # user must exist before session insert (FK)

        expired_session = Session(
            id=str(uuid4()),
            user_id=user.id,
            token=generate_token(),
            created_at=now - timedelta(days=10),
            expires_at=now - timedelta(days=3),
        )
        db.add(expired_session)
        await db.commit()

        service = AuthService(db)
        with pytest.raises(InvalidSessionError):
            await service.validate_session(expired_session.token)


@pytest.mark.asyncio
async def test_tampered_token_raises_invalid_session(fresh_engine):
    from backend.core.exceptions import InvalidSessionError
    from backend.services.auth import AuthService

    session_factory = async_sessionmaker(
        fresh_engine, class_=AsyncSession, expire_on_commit=False
    )
    await init_db(engine=fresh_engine, session_factory=session_factory)

    async with session_factory() as db:
        service = AuthService(db)
        with pytest.raises(InvalidSessionError):
            await service.validate_session("completelyfaketoken")


# ---------------------------------------------------------------------------
# Status endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_status_no_account(auth_client):
    resp = await auth_client.get("/api/auth/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["account_exists"] is False
    assert data["authenticated"] is False
    assert data["username"] is None


@pytest.mark.asyncio
async def test_status_account_exists_not_authenticated(auth_client):
    await auth_client.post(
        "/api/auth/setup",
        json={
            "username": "alice",
            "password": "password1",
            "password_confirm": "password1",
        },
    )
    resp = await auth_client.get("/api/auth/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["account_exists"] is True
    assert data["authenticated"] is False
    assert data["username"] is None


@pytest.mark.asyncio
async def test_status_authenticated_with_valid_token(auth_client):
    setup_resp = await auth_client.post(
        "/api/auth/setup",
        json={
            "username": "alice",
            "password": "password1",
            "password_confirm": "password1",
        },
    )
    token = setup_resp.json()["token"]

    resp = await auth_client.get(
        "/api/auth/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["account_exists"] is True
    assert data["authenticated"] is True
    assert data["username"] == "alice"


@pytest.mark.asyncio
async def test_status_invalid_token_not_authenticated(auth_client):
    await auth_client.post(
        "/api/auth/setup",
        json={
            "username": "alice",
            "password": "password1",
            "password_confirm": "password1",
        },
    )
    resp = await auth_client.get(
        "/api/auth/status",
        headers={"Authorization": "Bearer invalidtoken"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["account_exists"] is True
    assert data["authenticated"] is False


# ---------------------------------------------------------------------------
# Password reset (service layer)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reset_password_invalidates_all_sessions(fresh_engine):
    from backend.core.exceptions import InvalidSessionError
    from backend.services.auth import AuthService

    session_factory = async_sessionmaker(
        fresh_engine, class_=AsyncSession, expire_on_commit=False
    )
    await init_db(engine=fresh_engine, session_factory=session_factory)

    async with session_factory() as db:
        service = AuthService(db)
        _, session = await service.create_account("alice", "password1")
        token = session.token
        await db.commit()

    async with session_factory() as db:
        service = AuthService(db)
        await service.reset_password("newpassword1")
        await db.commit()

    async with session_factory() as db:
        service = AuthService(db)
        with pytest.raises(InvalidSessionError):
            await service.validate_session(token)


@pytest.mark.asyncio
async def test_reset_password_new_password_works(fresh_engine):
    from backend.services.auth import AuthService

    session_factory = async_sessionmaker(
        fresh_engine, class_=AsyncSession, expire_on_commit=False
    )
    await init_db(engine=fresh_engine, session_factory=session_factory)

    async with session_factory() as db:
        service = AuthService(db)
        await service.create_account("alice", "password1")
        await db.commit()

    async with session_factory() as db:
        service = AuthService(db)
        await service.reset_password("newpassword1")
        await db.commit()

    async with session_factory() as db:
        service = AuthService(db)
        session = await service.authenticate("alice", "newpassword1", False)
        assert session is not None


@pytest.mark.asyncio
async def test_reset_password_no_user_raises(fresh_engine):
    from backend.core.exceptions import AccountNotFoundError
    from backend.services.auth import AuthService

    session_factory = async_sessionmaker(
        fresh_engine, class_=AsyncSession, expire_on_commit=False
    )
    await init_db(engine=fresh_engine, session_factory=session_factory)

    async with session_factory() as db:
        service = AuthService(db)
        with pytest.raises(AccountNotFoundError):
            await service.reset_password("newpassword1")


# ---------------------------------------------------------------------------
# Multiple sessions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multiple_sessions_independent(auth_client):
    """Each session has its own token; logout only invalidates the current one."""
    await auth_client.post(
        "/api/auth/setup",
        json={
            "username": "alice",
            "password": "password1",
            "password_confirm": "password1",
        },
    )
    login1 = await auth_client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "password1"},
    )
    login2 = await auth_client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "password1"},
    )
    token1 = login1.json()["token"]
    token2 = login2.json()["token"]
    assert token1 != token2

    # Logout token1 — token2 must still be valid
    await auth_client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token1}"},
    )

    # Check token2 still authenticates
    resp = await auth_client.get(
        "/api/auth/status",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.json()["authenticated"] is True
