"""Tests for wallet management — service and router (T07 ST6)."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.dependencies import get_db
from backend.database import init_db
from backend.routers.auth import router as auth_router
from backend.routers.wallets import router as wallets_router

# ---------------------------------------------------------------------------
# Valid address fixtures
# ---------------------------------------------------------------------------

VALID_BTC = "1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf"
VALID_BTC_2 = "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"
VALID_BC1Q = "bc1q" + "a" * 38  # 42 chars
VALID_KAS = "kaspa:" + "a" * 61


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def fresh_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def wallet_client(fresh_engine):
    """HTTP test client wired to auth + wallets routers with fresh in-memory DB."""
    session_factory = async_sessionmaker(
        fresh_engine, class_=AsyncSession, expire_on_commit=False
    )
    await init_db(engine=fresh_engine, session_factory=session_factory)

    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(wallets_router)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest_asyncio.fixture
async def auth_token(wallet_client):
    """Create an account and return a bearer token."""
    resp = await wallet_client.post(
        "/api/auth/setup",
        json={
            "username": "alice",
            "password": "password1",
            "password_confirm": "password1",
        },
    )
    assert resp.status_code == 201
    return resp.json()["token"]


@pytest_asyncio.fixture
async def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def add_wallet(client, headers, network, address, tag=None):
    payload = {"network": network, "address": address}
    if tag is not None:
        payload["tag"] = tag
    return await client.post("/api/wallets/", json=payload, headers=headers)


# ---------------------------------------------------------------------------
# Auth requirements — all endpoints must return 401 without token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_wallets_requires_auth(wallet_client):
    resp = await wallet_client.get("/api/wallets/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_add_wallet_requires_auth(wallet_client):
    resp = await wallet_client.post(
        "/api/wallets/",
        json={"network": "BTC", "address": VALID_BTC},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_patch_wallet_requires_auth(wallet_client):
    resp = await wallet_client.patch(
        "/api/wallets/some-id",
        json={"tag": "New Tag"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_wallet_requires_auth(wallet_client):
    resp = await wallet_client.delete("/api/wallets/some-id")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_retry_history_requires_auth(wallet_client):
    resp = await wallet_client.post("/api/wallets/some-id/retry-history")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET / — list wallets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_wallets_empty(wallet_client, auth_headers):
    resp = await wallet_client.get("/api/wallets/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["wallets"] == []
    assert data["count"] == 0
    assert data["limit"] == 50


@pytest.mark.asyncio
async def test_list_wallets_returns_added_wallet(wallet_client, auth_headers):
    await add_wallet(wallet_client, auth_headers, "BTC", VALID_BTC, "My Wallet")
    resp = await wallet_client.get("/api/wallets/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    w = data["wallets"][0]
    assert w["network"] == "BTC"
    assert w["address"] == VALID_BTC
    assert w["tag"] == "My Wallet"
    assert "id" in w
    assert "created_at" in w
    assert "history_status" in w


# ---------------------------------------------------------------------------
# POST / — add wallet
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_btc_wallet_success(wallet_client, auth_headers):
    resp = await add_wallet(wallet_client, auth_headers, "BTC", VALID_BTC, "BTC Cold")
    assert resp.status_code == 201
    data = resp.json()
    assert data["network"] == "BTC"
    assert data["address"] == VALID_BTC
    assert data["tag"] == "BTC Cold"
    assert data["balance"] is None
    assert data["balance_usd"] is None
    assert data["history_status"] == "pending"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_add_kas_wallet_success(wallet_client, auth_headers):
    resp = await add_wallet(wallet_client, auth_headers, "KAS", VALID_KAS, "KAS Wallet")
    assert resp.status_code == 201
    data = resp.json()
    assert data["network"] == "KAS"
    assert data["address"] == VALID_KAS
    assert data["tag"] == "KAS Wallet"


@pytest.mark.asyncio
async def test_add_wallet_response_shape(wallet_client, auth_headers):
    resp = await add_wallet(wallet_client, auth_headers, "BTC", VALID_BTC)
    assert resp.status_code == 201
    data = resp.json()
    for field in (
        "id",
        "network",
        "address",
        "tag",
        "balance",
        "balance_usd",
        "created_at",
        "last_updated",
        "warning",
        "history_status",
    ):
        assert field in data


# ---------------------------------------------------------------------------
# POST / — invalid address → 400
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_wallet_invalid_btc_address(wallet_client, auth_headers):
    resp = await add_wallet(wallet_client, auth_headers, "BTC", "notanaddress")
    assert resp.status_code == 400
    assert "Invalid Bitcoin address format." in resp.json()["detail"]


@pytest.mark.asyncio
async def test_add_wallet_invalid_kas_address(wallet_client, auth_headers):
    resp = await add_wallet(wallet_client, auth_headers, "KAS", "notanaddress")
    assert resp.status_code == 400
    assert "Invalid Kaspa address format." in resp.json()["detail"]


@pytest.mark.asyncio
async def test_add_wallet_empty_address_rejected_by_pydantic(
    wallet_client, auth_headers
):
    resp = await wallet_client.post(
        "/api/wallets/",
        json={"network": "BTC", "address": ""},
        headers=auth_headers,
    )
    # WalletCreate.address has min_length=1 → 422 from Pydantic
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST / — whitespace/newline stripping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_wallet_address_whitespace_stripped(wallet_client, auth_headers):
    resp = await add_wallet(wallet_client, auth_headers, "BTC", f"  {VALID_BTC}  ")
    assert resp.status_code == 201
    assert resp.json()["address"] == VALID_BTC


@pytest.mark.asyncio
async def test_add_wallet_address_newlines_stripped(wallet_client, auth_headers):
    addr_with_newline = VALID_BTC[:10] + "\n" + VALID_BTC[10:]
    resp = await add_wallet(wallet_client, auth_headers, "BTC", addr_with_newline)
    assert resp.status_code == 201
    assert resp.json()["address"] == VALID_BTC


# ---------------------------------------------------------------------------
# POST / — duplicate address → 400
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_wallet_duplicate_address(wallet_client, auth_headers):
    await add_wallet(wallet_client, auth_headers, "BTC", VALID_BTC)
    resp = await add_wallet(wallet_client, auth_headers, "BTC", VALID_BTC)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "This wallet address is already being tracked."


@pytest.mark.asyncio
async def test_add_wallet_btc_duplicate_case_insensitive(wallet_client, auth_headers):
    # Add bc1q address in lowercase
    resp1 = await add_wallet(wallet_client, auth_headers, "BTC", VALID_BC1Q)
    assert resp1.status_code == 201
    # Attempt uppercase variant — should be caught as duplicate
    resp2 = await add_wallet(wallet_client, auth_headers, "BTC", VALID_BC1Q.upper())
    assert resp2.status_code == 400
    assert resp2.json()["detail"] == "This wallet address is already being tracked."


# ---------------------------------------------------------------------------
# POST / — tag validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_wallet_long_tag_rejected(wallet_client, auth_headers):
    resp = await add_wallet(wallet_client, auth_headers, "BTC", VALID_BTC, "x" * 51)
    assert resp.status_code == 400
    assert "Tag must be 50 characters or fewer." in resp.json()["detail"]


@pytest.mark.asyncio
async def test_add_wallet_tag_exactly_50_accepted(wallet_client, auth_headers):
    resp = await add_wallet(wallet_client, auth_headers, "BTC", VALID_BTC, "x" * 50)
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_add_wallet_duplicate_tag_rejected(wallet_client, auth_headers):
    await add_wallet(wallet_client, auth_headers, "BTC", VALID_BTC, "My Tag")
    resp = await add_wallet(wallet_client, auth_headers, "KAS", VALID_KAS, "My Tag")
    assert resp.status_code == 400
    assert "A wallet with this tag already exists." in resp.json()["detail"]


@pytest.mark.asyncio
async def test_add_wallet_no_tag_generates_default(wallet_client, auth_headers):
    resp = await add_wallet(wallet_client, auth_headers, "BTC", VALID_BTC)
    assert resp.status_code == 201
    assert resp.json()["tag"] == "BTC Wallet #1"


@pytest.mark.asyncio
async def test_add_wallet_no_tag_increments_counter(wallet_client, auth_headers):
    resp1 = await add_wallet(wallet_client, auth_headers, "BTC", VALID_BTC)
    resp2 = await add_wallet(wallet_client, auth_headers, "BTC", VALID_BTC_2)
    assert resp1.json()["tag"] == "BTC Wallet #1"
    assert resp2.json()["tag"] == "BTC Wallet #2"


@pytest.mark.asyncio
async def test_add_kas_wallet_no_tag_generates_kas_default(wallet_client, auth_headers):
    resp = await add_wallet(wallet_client, auth_headers, "KAS", VALID_KAS)
    assert resp.status_code == 201
    assert resp.json()["tag"] == "KAS Wallet #1"


@pytest.mark.asyncio
async def test_add_wallet_empty_tag_generates_default(wallet_client, auth_headers):
    resp = await wallet_client.post(
        "/api/wallets/",
        json={"network": "BTC", "address": VALID_BTC, "tag": ""},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["tag"] == "BTC Wallet #1"


@pytest.mark.asyncio
async def test_add_wallet_whitespace_only_tag_generates_default(
    wallet_client, auth_headers
):
    resp = await wallet_client.post(
        "/api/wallets/",
        json={"network": "BTC", "address": VALID_BTC, "tag": "   "},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["tag"] == "BTC Wallet #1"


# ---------------------------------------------------------------------------
# POST / — wallet limit → 409
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_wallet_limit_51st_returns_409(wallet_client, auth_headers):
    """Adding 51 wallets: the 51st must return 409."""
    # Use KAS addresses — they use exact-match duplicate detection (not case-insensitive)
    # "kaspa:" + 61 lowercase bech32 chars; vary the last two digits numerically
    bech32_digits = "023456789"  # digits only (no letters), no case ambiguity
    for i in range(50):
        # Encode i as two-digit bech32 (base 9), fill rest with 'a'
        d1 = bech32_digits[i // len(bech32_digits)]
        d2 = bech32_digits[i % len(bech32_digits)]
        addr = "kaspa:" + "a" * 59 + d1 + d2
        resp = await add_wallet(wallet_client, auth_headers, "KAS", addr, f"Wallet {i}")
        assert resp.status_code == 201, f"Failed at wallet {i}: {resp.json()}"

    # 51st wallet should be rejected
    resp = await add_wallet(wallet_client, auth_headers, "KAS", VALID_KAS, "Overflow")
    assert resp.status_code == 409
    assert "Wallet limit reached (50)" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# PATCH /{wallet_id} — update tag
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_tag_success(wallet_client, auth_headers):
    create_resp = await add_wallet(
        wallet_client, auth_headers, "BTC", VALID_BTC, "Old Tag"
    )
    wallet_id = create_resp.json()["id"]

    resp = await wallet_client.patch(
        f"/api/wallets/{wallet_id}",
        json={"tag": "New Tag"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["tag"] == "New Tag"


@pytest.mark.asyncio
async def test_patch_tag_not_found(wallet_client, auth_headers):
    resp = await wallet_client.patch(
        "/api/wallets/nonexistent-id",
        json={"tag": "Whatever"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_tag_duplicate_rejected(wallet_client, auth_headers):
    await add_wallet(wallet_client, auth_headers, "BTC", VALID_BTC, "Tag A")
    r2 = await add_wallet(wallet_client, auth_headers, "BTC", VALID_BTC_2, "Tag B")
    wallet_id = r2.json()["id"]

    resp = await wallet_client.patch(
        f"/api/wallets/{wallet_id}",
        json={"tag": "Tag A"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "A wallet with this tag already exists." in resp.json()["detail"]


@pytest.mark.asyncio
async def test_patch_tag_same_name_allowed(wallet_client, auth_headers):
    """A wallet can be PATCH'd with its own existing tag (no duplicate conflict)."""
    r = await add_wallet(wallet_client, auth_headers, "BTC", VALID_BTC, "My Tag")
    wallet_id = r.json()["id"]

    resp = await wallet_client.patch(
        f"/api/wallets/{wallet_id}",
        json={"tag": "My Tag"},
        headers=auth_headers,
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# DELETE /{wallet_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_wallet_success(wallet_client, auth_headers):
    r = await add_wallet(wallet_client, auth_headers, "BTC", VALID_BTC, "To Delete")
    wallet_id = r.json()["id"]

    resp = await wallet_client.delete(
        f"/api/wallets/{wallet_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_wallet_then_list_empty(wallet_client, auth_headers):
    r = await add_wallet(wallet_client, auth_headers, "BTC", VALID_BTC, "Solo")
    wallet_id = r.json()["id"]

    await wallet_client.delete(f"/api/wallets/{wallet_id}", headers=auth_headers)

    list_resp = await wallet_client.get("/api/wallets/", headers=auth_headers)
    assert list_resp.json()["wallets"] == []
    assert list_resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_delete_wallet_not_found(wallet_client, auth_headers):
    resp = await wallet_client.delete(
        "/api/wallets/nonexistent-id",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_wallet_cascades_snapshots(
    wallet_client, auth_headers, fresh_engine
):
    """After deleting a wallet, its balance snapshots are gone too."""
    from datetime import datetime, timezone

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from backend.models.balance_snapshot import BalanceSnapshot

    r = await add_wallet(wallet_client, auth_headers, "BTC", VALID_BTC, "Cascade Test")
    wallet_id = r.json()["id"]

    # Insert a snapshot directly via DB
    session_factory = async_sessionmaker(
        fresh_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as db:
        snap = BalanceSnapshot(
            id="snap-1",
            wallet_id=wallet_id,
            balance="0.5",  # balance column is String(40)
            timestamp=datetime.now(timezone.utc),
            source="api",
        )
        db.add(snap)
        await db.commit()

    # Delete wallet via API
    await wallet_client.delete(f"/api/wallets/{wallet_id}", headers=auth_headers)

    # Verify snapshot is gone
    async with session_factory() as db:
        result = await db.execute(
            select(BalanceSnapshot).where(BalanceSnapshot.wallet_id == wallet_id)
        )
        assert result.scalar_one_or_none() is None


# ---------------------------------------------------------------------------
# POST /{wallet_id}/retry-history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_history_success(wallet_client, auth_headers):
    r = await add_wallet(wallet_client, auth_headers, "BTC", VALID_BTC, "Retry Me")
    wallet_id = r.json()["id"]

    resp = await wallet_client.post(
        f"/api/wallets/{wallet_id}/retry-history",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "message": "History import started."}


@pytest.mark.asyncio
async def test_retry_history_not_found(wallet_client, auth_headers):
    resp = await wallet_client.post(
        "/api/wallets/nonexistent-id/retry-history",
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# IDOR — cross-user wallet access must return 404 (service layer)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_idor_update_tag_other_user_wallet_returns_not_found(fresh_engine):
    """User B cannot update a wallet owned by User A — service raises WalletNotFoundError."""
    from datetime import datetime, timezone
    from uuid import uuid4 as _uuid4

    from sqlalchemy.ext.asyncio import async_sessionmaker

    from backend.core.exceptions import WalletNotFoundError
    from backend.models.user import User
    from backend.models.wallet import Wallet
    from backend.services.wallet import WalletService

    session_factory = async_sessionmaker(
        fresh_engine, class_=AsyncSession, expire_on_commit=False
    )
    from backend.database import init_db

    await init_db(engine=fresh_engine, session_factory=session_factory)

    async with session_factory() as db:
        now = datetime.now(timezone.utc)
        user_a = User(
            id=str(_uuid4()), username="userA", password_hash="x", created_at=now
        )
        user_b = User(
            id=str(_uuid4()), username="userB", password_hash="x", created_at=now
        )
        db.add(user_a)
        db.add(user_b)
        await db.flush()

        wallet_a = Wallet(
            id=str(_uuid4()),
            user_id=user_a.id,
            network="BTC",
            address=VALID_BTC,
            tag="User A Wallet",
            created_at=now,
        )
        db.add(wallet_a)
        await db.commit()

    async with session_factory() as db:
        # User B attempts to update User A's wallet tag
        service = WalletService(db=db, user=user_b)
        import pytest as _pytest

        with _pytest.raises(WalletNotFoundError):
            await service.update_tag(wallet_a.id, "Hijacked")


@pytest.mark.asyncio
async def test_idor_remove_wallet_other_user_returns_not_found(fresh_engine):
    """User B cannot delete a wallet owned by User A — service raises WalletNotFoundError."""
    from datetime import datetime, timezone
    from uuid import uuid4 as _uuid4

    from sqlalchemy.ext.asyncio import async_sessionmaker

    from backend.core.exceptions import WalletNotFoundError
    from backend.models.user import User
    from backend.models.wallet import Wallet
    from backend.services.wallet import WalletService

    session_factory = async_sessionmaker(
        fresh_engine, class_=AsyncSession, expire_on_commit=False
    )
    from backend.database import init_db

    await init_db(engine=fresh_engine, session_factory=session_factory)

    async with session_factory() as db:
        now = datetime.now(timezone.utc)
        user_a = User(
            id=str(_uuid4()), username="userA2", password_hash="x", created_at=now
        )
        user_b = User(
            id=str(_uuid4()), username="userB2", password_hash="x", created_at=now
        )
        db.add(user_a)
        db.add(user_b)
        await db.flush()

        wallet_a = Wallet(
            id=str(_uuid4()),
            user_id=user_a.id,
            network="BTC",
            address=VALID_BTC,
            tag="User A Wallet",
            created_at=now,
        )
        db.add(wallet_a)
        await db.commit()

    async with session_factory() as db:
        # User B attempts to delete User A's wallet
        service = WalletService(db=db, user=user_b)
        import pytest as _pytest

        with _pytest.raises(WalletNotFoundError):
            await service.remove_wallet(wallet_a.id)
