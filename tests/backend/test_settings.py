"""Tests for Settings Router (T09 ST9)."""

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.dependencies import get_db
from backend.database import init_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def fresh_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def settings_client(fresh_engine):
    """HTTP test client wired to auth + settings routers with fresh in-memory DB."""
    session_factory = async_sessionmaker(
        fresh_engine, class_=AsyncSession, expire_on_commit=False
    )
    await init_db(engine=fresh_engine, session_factory=session_factory)

    from backend.routers.auth import router as auth_router
    from backend.routers.settings import router as settings_router

    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(settings_router)

    # Wire mock scheduler and ws_manager on app.state
    mock_scheduler = AsyncMock()
    mock_scheduler.restart = AsyncMock()
    app.state.scheduler = mock_scheduler

    mock_ws = AsyncMock()
    mock_ws.broadcast = AsyncMock()
    app.state.ws_manager = mock_ws

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Attach the mocks so tests can inspect calls
        client.app = app
        yield client


@pytest_asyncio.fixture
async def auth_token(settings_client):
    resp = await settings_client.post(
        "/api/auth/setup",
        json={
            "username": "bob",
            "password": "password1",
            "password_confirm": "password1",
        },
    )
    assert resp.status_code == 201
    return resp.json()["token"]


@pytest_asyncio.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


# ---------------------------------------------------------------------------
# Auth enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_settings_requires_auth(settings_client):
    resp = await settings_client.get("/api/settings/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_put_settings_requires_auth(settings_client):
    resp = await settings_client.put(
        "/api/settings/", json={"refresh_interval_minutes": 15}
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET / — default value
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_default_interval(settings_client, auth_headers):
    """Default refresh interval should be 15 minutes."""
    resp = await settings_client.get("/api/settings/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "refresh_interval_minutes" in data
    assert data["refresh_interval_minutes"] == 15


@pytest.mark.asyncio
async def test_get_default_timezone(settings_client, auth_headers):
    """Default preferred timezone should be UTC."""
    resp = await settings_client.get("/api/settings/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["preferred_timezone"] == "UTC"


# ---------------------------------------------------------------------------
# PUT / — valid intervals
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_to_5_minutes(settings_client, auth_headers):
    resp = await settings_client.put(
        "/api/settings/", json={"refresh_interval_minutes": 5}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["refresh_interval_minutes"] == 5


@pytest.mark.asyncio
async def test_update_to_15_minutes(settings_client, auth_headers):
    resp = await settings_client.put(
        "/api/settings/", json={"refresh_interval_minutes": 15}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["refresh_interval_minutes"] == 15


@pytest.mark.asyncio
async def test_update_to_30_minutes(settings_client, auth_headers):
    resp = await settings_client.put(
        "/api/settings/", json={"refresh_interval_minutes": 30}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["refresh_interval_minutes"] == 30


@pytest.mark.asyncio
async def test_update_to_60_minutes(settings_client, auth_headers):
    resp = await settings_client.put(
        "/api/settings/", json={"refresh_interval_minutes": 60}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["refresh_interval_minutes"] == 60


@pytest.mark.asyncio
async def test_update_to_null_disables(settings_client, auth_headers):
    resp = await settings_client.put(
        "/api/settings/", json={"refresh_interval_minutes": None}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["refresh_interval_minutes"] is None


# ---------------------------------------------------------------------------
# PUT / — invalid interval → 422
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_invalid_7_minutes_rejected(settings_client, auth_headers):
    resp = await settings_client.put(
        "/api/settings/", json={"refresh_interval_minutes": 7}, headers=auth_headers
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_invalid_999_minutes_rejected(settings_client, auth_headers):
    resp = await settings_client.put(
        "/api/settings/", json={"refresh_interval_minutes": 999}, headers=auth_headers
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_invalid_0_minutes_rejected(settings_client, auth_headers):
    resp = await settings_client.put(
        "/api/settings/", json={"refresh_interval_minutes": 0}, headers=auth_headers
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Persistence — GET after PUT returns new value
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_persists_across_get(settings_client, auth_headers):
    await settings_client.put(
        "/api/settings/", json={"refresh_interval_minutes": 30}, headers=auth_headers
    )
    resp = await settings_client.get("/api/settings/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["refresh_interval_minutes"] == 30


# ---------------------------------------------------------------------------
# Scheduler restart triggered on PUT
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_triggers_scheduler_restart(settings_client, auth_headers):
    resp = await settings_client.put(
        "/api/settings/", json={"refresh_interval_minutes": 60}, headers=auth_headers
    )
    assert resp.status_code == 200
    settings_client.app.state.scheduler.restart.assert_awaited_once_with(60)


@pytest.mark.asyncio
async def test_update_broadcasts_settings_updated(settings_client, auth_headers):
    await settings_client.put(
        "/api/settings/", json={"refresh_interval_minutes": 15}, headers=auth_headers
    )
    settings_client.app.state.ws_manager.broadcast.assert_awaited_once()
    call_args = settings_client.app.state.ws_manager.broadcast.call_args
    assert call_args.args[0] == "settings:updated"


@pytest.mark.asyncio
async def test_update_null_broadcasts_null_value_not_string(
    settings_client, auth_headers
):
    """Broadcast payload value should be null (not the string 'None')."""
    await settings_client.put(
        "/api/settings/", json={"refresh_interval_minutes": None}, headers=auth_headers
    )
    call_args = settings_client.app.state.ws_manager.broadcast.call_args
    payload = call_args.args[1]
    assert payload["value"] is None, f"Expected None but got {payload['value']!r}"


# ---------------------------------------------------------------------------
# Timezone — GET default, PUT valid, persistence, invalid, independence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_timezone(settings_client, auth_headers):
    resp = await settings_client.put(
        "/api/settings/",
        json={"preferred_timezone": "America/New_York"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["preferred_timezone"] == "America/New_York"


@pytest.mark.asyncio
async def test_update_timezone_persists_across_get(settings_client, auth_headers):
    await settings_client.put(
        "/api/settings/",
        json={"preferred_timezone": "Asia/Tokyo"},
        headers=auth_headers,
    )
    resp = await settings_client.get("/api/settings/", headers=auth_headers)
    assert resp.json()["preferred_timezone"] == "Asia/Tokyo"


@pytest.mark.asyncio
async def test_update_blank_timezone_rejected(settings_client, auth_headers):
    resp = await settings_client.put(
        "/api/settings/", json={"preferred_timezone": ""}, headers=auth_headers
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_too_long_timezone_rejected(settings_client, auth_headers):
    resp = await settings_client.put(
        "/api/settings/", json={"preferred_timezone": "A" * 65}, headers=auth_headers
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_timezone_only_update_does_not_restart_scheduler(
    settings_client, auth_headers
):
    """A TZ-only PUT should not trigger a scheduler restart."""
    await settings_client.put(
        "/api/settings/",
        json={"preferred_timezone": "Europe/London"},
        headers=auth_headers,
    )
    settings_client.app.state.scheduler.restart.assert_not_called()


@pytest.mark.asyncio
async def test_interval_update_does_not_reset_timezone(settings_client, auth_headers):
    """Updating interval only should leave the stored timezone untouched."""
    await settings_client.put(
        "/api/settings/",
        json={"preferred_timezone": "Europe/Paris"},
        headers=auth_headers,
    )
    await settings_client.put(
        "/api/settings/",
        json={"refresh_interval_minutes": 30},
        headers=auth_headers,
    )
    resp = await settings_client.get("/api/settings/", headers=auth_headers)
    assert resp.json()["preferred_timezone"] == "Europe/Paris"


@pytest.mark.asyncio
async def test_timezone_update_does_not_reset_interval(settings_client, auth_headers):
    """Updating timezone only should leave the stored interval untouched."""
    await settings_client.put(
        "/api/settings/",
        json={"refresh_interval_minutes": 5},
        headers=auth_headers,
    )
    await settings_client.put(
        "/api/settings/",
        json={"preferred_timezone": "Asia/Singapore"},
        headers=auth_headers,
    )
    resp = await settings_client.get("/api/settings/", headers=auth_headers)
    assert resp.json()["refresh_interval_minutes"] == 5
