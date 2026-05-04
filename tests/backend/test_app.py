"""Tests for the application factory (T10)."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from unittest.mock import AsyncMock

from backend.app import create_app
from backend.core.dependencies import get_db
from backend.database import init_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def app_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def app_client(app_engine):
    """Provide a test HTTP client backed by an in-memory DB via the real app factory.

    app.state is populated with stubs so endpoints that use it don't crash.
    This is intentionally not running lifespan (which would hit external APIs).
    """
    session_factory = async_sessionmaker(
        app_engine, class_=AsyncSession, expire_on_commit=False
    )
    await init_db(engine=app_engine, session_factory=session_factory)

    app = create_app()

    # Stub app.state for endpoints that read from it
    mock_ws_manager = AsyncMock()
    mock_ws_manager.broadcast = AsyncMock()
    mock_scheduler = AsyncMock()
    mock_scheduler.restart = AsyncMock()
    mock_refresh_service = AsyncMock()
    mock_history_service = AsyncMock()

    app.state.ws_manager = mock_ws_manager
    app.state.scheduler = mock_scheduler
    app.state.refresh_service = mock_refresh_service
    app.state.history_service = mock_history_service

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


async def _create_account_and_get_token(client: AsyncClient) -> str:
    """Helper: set up an account and return its session token."""
    resp = await client.post(
        "/api/auth/setup",
        json={
            "username": "testuser",
            "password": "testpassword123",
            "password_confirm": "testpassword123",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


# ---------------------------------------------------------------------------
# ST1: create_app() smoke
# ---------------------------------------------------------------------------


def test_app_creates_without_error():
    """create_app() must return a FastAPI instance without raising."""
    from fastapi import FastAPI

    app = create_app()
    assert isinstance(app, FastAPI)


def test_app_has_title():
    app = create_app()
    assert app.title == "CryptoDash"


def test_app_has_routes():
    """App must expose at least some routes."""
    app = create_app()
    assert len(app.routes) > 0


# ---------------------------------------------------------------------------
# ST2: Router mounts — verify each router is reachable
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auth_status_returns_200(app_client):
    """GET /api/auth/status must return 200 — no auth required."""
    response = await app_client.get("/api/auth/status")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_wallets_requires_auth(app_client):
    """GET /api/wallets/ must return 401 without a token (router mounted)."""
    response = await app_client.get("/api/wallets/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_requires_auth(app_client):
    """GET /api/dashboard/summary must return 401 without a token."""
    response = await app_client.get("/api/dashboard/summary")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_settings_requires_auth(app_client):
    """GET /api/settings/ must return 401 without a token (router mounted)."""
    response = await app_client.get("/api/settings/")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# ST3: HTTP status codes for error conditions
# These exercise both global exception handlers and router-level HTTPExceptions.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_credentials_returns_401(app_client):
    """POST /api/auth/login with wrong credentials must return 401."""
    await _create_account_and_get_token(app_client)
    response = await app_client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_account_exists_returns_409(app_client):
    """POST /api/auth/setup when account already exists must return 409."""
    await _create_account_and_get_token(app_client)
    response = await app_client.post(
        "/api/auth/setup",
        json={
            "username": "testuser2",
            "password": "anotherpassword",
            "password_confirm": "anotherpassword",
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_wallet_not_found_returns_404(app_client):
    """PATCH /api/wallets/<nonexistent-id> with auth must return 404."""
    token = await _create_account_and_get_token(app_client)
    response = await app_client.patch(
        "/api/wallets/nonexistent-id",
        json={"tag": "new tag"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_address_validation_error_returns_400(app_client):
    """POST /api/wallets/ with invalid address must return 400."""
    token = await _create_account_and_get_token(app_client)
    response = await app_client.post(
        "/api/wallets/",
        json={"network": "BTC", "address": "not-a-valid-address", "tag": "my btc"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_rate_limited_returns_429_with_retry_after(app_client):
    """After 5 failed logins the 6th must return 429 with Retry-After header."""
    await _create_account_and_get_token(app_client)
    for _ in range(5):
        await app_client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "wrong"},
        )
    response = await app_client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "wrong"},
    )
    assert response.status_code == 429
    assert "retry-after" in response.headers


@pytest.mark.asyncio
async def test_duplicate_wallet_returns_400(app_client):
    """Adding the same wallet address twice must return 400."""
    from unittest.mock import patch, AsyncMock as AMock

    token = await _create_account_and_get_token(app_client)
    address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf"

    # Add once — patch _fetch_initial_data so background task doesn't hit real clients
    with patch.object(
        __import__("backend.services.wallet", fromlist=["WalletService"]).WalletService,
        "_fetch_initial_data",
        new=AMock(return_value=None),
    ):
        resp = await app_client.post(
            "/api/wallets/",
            json={"network": "BTC", "address": address, "tag": "first"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 201

    # Add again — duplicate
    response = await app_client.post(
        "/api/wallets/",
        json={"network": "BTC", "address": address, "tag": "second"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_tag_validation_error_returns_400(app_client):
    """Adding two wallets with the same tag must return 400 on the second."""
    from unittest.mock import patch, AsyncMock as AMock

    token = await _create_account_and_get_token(app_client)

    wallet_svc = __import__(
        "backend.services.wallet", fromlist=["WalletService"]
    ).WalletService
    with patch.object(wallet_svc, "_fetch_initial_data", new=AMock(return_value=None)):
        resp = await app_client.post(
            "/api/wallets/",
            json={
                "network": "BTC",
                "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf",
                "tag": "my wallet",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 201

    response = await app_client.post(
        "/api/wallets/",
        json={
            "network": "KAS",
            "address": "kaspa:" + "a" * 61,
            "tag": "my wallet",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_invalid_session_returns_401(app_client):
    """A tampered/invalid token must return 401 on protected endpoints."""
    response = await app_client.get(
        "/api/wallets/",
        headers={"Authorization": "Bearer totally-invalid-token"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# ST4: No crash when frontend/dist is missing
# ---------------------------------------------------------------------------


def test_app_creates_without_frontend_dist(monkeypatch):
    """create_app() must not crash if frontend/dist/ does not exist."""
    import os

    real_isdir = os.path.isdir

    def mock_isdir(path):
        if "frontend" in str(path) and "dist" in str(path):
            return False
        return real_isdir(path)

    monkeypatch.setattr(os.path, "isdir", mock_isdir)

    from fastapi import FastAPI

    app = create_app()
    assert isinstance(app, FastAPI)


# ---------------------------------------------------------------------------
# ST5: SPA fallback for client-side routes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_spa_fallback_serves_index_for_client_routes(app_client):
    """Refreshing on a frontend route (e.g. /wallet/<id>) must return the SPA
    index.html so the router can take over, not a JSON 404."""
    response = await app_client.get("/wallet/abc-123")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '<div id="app">' in response.text or "id=app" in response.text


@pytest.mark.asyncio
async def test_spa_fallback_does_not_swallow_unknown_api_routes(app_client):
    """Unknown /api/* paths must still return a JSON 404 — not the SPA
    index.html — so client API errors stay machine-readable."""
    response = await app_client.get("/api/this-endpoint-does-not-exist")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": "Not Found"}
