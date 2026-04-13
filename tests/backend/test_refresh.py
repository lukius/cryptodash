"""Tests for RefreshService (T09 ST7)."""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.database import init_db
from backend.models.user import User
from backend.models.wallet import Wallet


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def fresh_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(fresh_engine):
    factory = async_sessionmaker(
        fresh_engine, class_=AsyncSession, expire_on_commit=False
    )
    await init_db(engine=fresh_engine, session_factory=factory)
    return factory


@pytest_asyncio.fixture
async def db_session(session_factory):
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def test_user(session_factory):
    user = User(
        id=str(uuid4()),
        username="testuser",
        password_hash="x",
        created_at=datetime.now(timezone.utc),
    )
    async with session_factory() as db:
        db.add(user)
        await db.commit()
    return user


@pytest_asyncio.fixture
def btc_wallet(test_user):
    return Wallet(
        id=str(uuid4()),
        user_id=test_user.id,
        network="BTC",
        address="1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf",
        tag="BTC Wallet",
        created_at=datetime.now(timezone.utc),
    )


@pytest_asyncio.fixture
def kas_wallet(test_user):
    return Wallet(
        id=str(uuid4()),
        user_id=test_user.id,
        network="KAS",
        address="kaspa:" + "a" * 61,
        tag="KAS Wallet",
        created_at=datetime.now(timezone.utc),
    )


def make_mock_clients():
    btc_client = AsyncMock()
    btc_client.get_balance = AsyncMock(return_value=Decimal("0.5"))

    kas_client = AsyncMock()
    kas_client.get_balance = AsyncMock(return_value=Decimal("1000"))
    kas_client.get_price_usd = AsyncMock(return_value=Decimal("0.05"))

    coingecko_client = AsyncMock()
    coingecko_client.get_current_prices = AsyncMock(
        return_value={"BTC": Decimal("50000"), "KAS": Decimal("0.05")}
    )

    ws_manager = AsyncMock()
    ws_manager.broadcast = AsyncMock()

    history_service = AsyncMock()
    history_service.incremental_sync = AsyncMock(return_value=0)

    return btc_client, kas_client, coingecko_client, ws_manager, history_service


def make_refresh_service(
    session_factory,
    btc_client,
    kas_client,
    coingecko_client,
    ws_manager,
    history_service,
):
    from backend.services.refresh import RefreshService

    return RefreshService(
        session_factory=session_factory,
        btc_client=btc_client,
        kas_client=kas_client,
        coingecko_client=coingecko_client,
        ws_manager=ws_manager,
        history_service=history_service,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_refresh_fetches_balances_and_prices(
    session_factory, db_session, btc_wallet, kas_wallet
):
    """Full refresh should fetch balances for all wallets and store snapshots."""
    db_session.add(btc_wallet)
    db_session.add(kas_wallet)
    await db_session.commit()

    btc_client, kas_client, coingecko_client, ws_manager, history_service = (
        make_mock_clients()
    )
    service = make_refresh_service(
        session_factory,
        btc_client,
        kas_client,
        coingecko_client,
        ws_manager,
        history_service,
    )

    result = await service.run_full_refresh()

    assert result.skipped is False
    assert result.success_count == 2
    assert result.failure_count == 0
    assert result.errors == []

    btc_client.get_balance.assert_awaited_once()
    kas_client.get_balance.assert_awaited_once()
    coingecko_client.get_current_prices.assert_awaited_once()


@pytest.mark.asyncio
async def test_full_refresh_stores_balance_snapshots(
    session_factory, db_session, btc_wallet
):
    """Full refresh should store a BalanceSnapshot for the wallet."""
    from sqlalchemy import select

    from backend.models.balance_snapshot import BalanceSnapshot

    db_session.add(btc_wallet)
    await db_session.commit()

    btc_client, kas_client, coingecko_client, ws_manager, history_service = (
        make_mock_clients()
    )
    service = make_refresh_service(
        session_factory,
        btc_client,
        kas_client,
        coingecko_client,
        ws_manager,
        history_service,
    )

    await service.run_full_refresh()

    # Query via a fresh session (service committed its own session)
    async with session_factory() as s:
        result = await s.execute(
            select(BalanceSnapshot).where(BalanceSnapshot.wallet_id == btc_wallet.id)
        )
        snapshots = result.scalars().all()

    assert len(snapshots) >= 1
    assert snapshots[-1].source == "live"
    assert Decimal(snapshots[-1].balance) == Decimal("0.5")


@pytest.mark.asyncio
async def test_full_refresh_partial_failure(
    session_factory, db_session, btc_wallet, kas_wallet
):
    """One wallet failing should not abort others — partial success."""
    db_session.add(btc_wallet)
    db_session.add(kas_wallet)
    await db_session.commit()

    btc_client, kas_client, coingecko_client, ws_manager, history_service = (
        make_mock_clients()
    )
    # Make BTC balance fetch fail
    btc_client.get_balance = AsyncMock(side_effect=Exception("BTC API down"))

    service = make_refresh_service(
        session_factory,
        btc_client,
        kas_client,
        coingecko_client,
        ws_manager,
        history_service,
    )
    result = await service.run_full_refresh()

    assert result.skipped is False
    assert result.success_count == 1
    assert result.failure_count == 1
    assert len(result.errors) == 1


@pytest.mark.asyncio
async def test_concurrent_refresh_skipped(session_factory):
    """A second run_full_refresh call while the first is running must return skipped=True."""
    btc_client, kas_client, coingecko_client, ws_manager, history_service = (
        make_mock_clients()
    )

    service = make_refresh_service(
        session_factory,
        btc_client,
        kas_client,
        coingecko_client,
        ws_manager,
        history_service,
    )

    # Manually acquire the lock to simulate a running refresh
    await service._lock.acquire()
    try:
        result = await service.run_full_refresh()
        assert result.skipped is True
        assert result.success_count == 0
        assert result.failure_count == 0
    finally:
        service._lock.release()


@pytest.mark.asyncio
async def test_concurrent_refresh_truly_skipped(
    session_factory, db_session, btc_wallet
):
    """Two concurrent run_full_refresh calls: one completes, the other returns skipped=True."""
    db_session.add(btc_wallet)
    await db_session.commit()

    btc_client, kas_client, coingecko_client, ws_manager, history_service = (
        make_mock_clients()
    )
    service = make_refresh_service(
        session_factory,
        btc_client,
        kas_client,
        coingecko_client,
        ws_manager,
        history_service,
    )

    results = await asyncio.gather(
        service.run_full_refresh(),
        service.run_full_refresh(),
    )

    skipped = [r for r in results if r.skipped]
    not_skipped = [r for r in results if not r.skipped]
    assert len(skipped) == 1, "Exactly one refresh should be skipped"
    assert len(not_skipped) == 1, "Exactly one refresh should complete"


@pytest.mark.asyncio
async def test_refresh_price_fallback_to_kaspa(session_factory, db_session, kas_wallet):
    """When CoinGecko fails, KAS price should fall back to kas_client.get_price_usd()."""
    from sqlalchemy import select

    from backend.models.price_snapshot import PriceSnapshot

    db_session.add(kas_wallet)
    await db_session.commit()

    btc_client, kas_client, coingecko_client, ws_manager, history_service = (
        make_mock_clients()
    )
    coingecko_client.get_current_prices = AsyncMock(
        side_effect=Exception("CoinGecko down")
    )
    kas_client.get_price_usd = AsyncMock(return_value=Decimal("0.07"))

    service = make_refresh_service(
        session_factory,
        btc_client,
        kas_client,
        coingecko_client,
        ws_manager,
        history_service,
    )
    result = await service.run_full_refresh()

    assert result.skipped is False
    # KAS fallback price should have been used
    kas_client.get_price_usd.assert_awaited_once()

    async with session_factory() as s:
        price_result = await s.execute(
            select(PriceSnapshot)
            .where(PriceSnapshot.coin == "KAS")
            .order_by(PriceSnapshot.timestamp.desc())
        )
        kas_snapshots = price_result.scalars().all()

    assert len(kas_snapshots) >= 1
    assert Decimal(kas_snapshots[0].price_usd) == Decimal("0.07")


@pytest.mark.asyncio
async def test_refresh_zero_price_discarded(session_factory):
    """A price of 0 from CoinGecko should be discarded (not stored)."""
    from sqlalchemy import select

    from backend.models.price_snapshot import PriceSnapshot

    btc_client, kas_client, coingecko_client, ws_manager, history_service = (
        make_mock_clients()
    )
    # Return 0 for BTC (should be discarded)
    coingecko_client.get_current_prices = AsyncMock(
        return_value={"BTC": Decimal("0"), "KAS": Decimal("0.05")}
    )

    service = make_refresh_service(
        session_factory,
        btc_client,
        kas_client,
        coingecko_client,
        ws_manager,
        history_service,
    )
    await service.run_full_refresh()

    async with session_factory() as s:
        result = await s.execute(
            select(PriceSnapshot).where(PriceSnapshot.coin == "BTC")
        )
        btc_snapshots = result.scalars().all()

    # Zero price should not be stored
    assert all(Decimal(s.price_usd) != Decimal("0") for s in btc_snapshots)


@pytest.mark.asyncio
async def test_refresh_broadcasts_events(session_factory):
    """Full refresh should broadcast refresh:started and refresh:completed events."""
    btc_client, kas_client, coingecko_client, ws_manager, history_service = (
        make_mock_clients()
    )

    service = make_refresh_service(
        session_factory,
        btc_client,
        kas_client,
        coingecko_client,
        ws_manager,
        history_service,
    )
    await service.run_full_refresh()

    broadcast_calls = ws_manager.broadcast.call_args_list
    events = [call.args[0] for call in broadcast_calls]
    assert "refresh:started" in events
    assert "refresh:completed" in events


@pytest.mark.asyncio
async def test_refresh_single_wallet_no_lock(session_factory, db_session, btc_wallet):
    """refresh_single_wallet should not acquire the lock and should return a BalanceSnapshot."""
    db_session.add(btc_wallet)
    await db_session.commit()

    btc_client, kas_client, coingecko_client, ws_manager, history_service = (
        make_mock_clients()
    )
    service = make_refresh_service(
        session_factory,
        btc_client,
        kas_client,
        coingecko_client,
        ws_manager,
        history_service,
    )

    # Verify it works even when the lock is already held
    await service._lock.acquire()
    try:
        snapshot = await service.refresh_single_wallet(btc_wallet)
        assert snapshot is not None
        assert Decimal(snapshot.balance) == Decimal("0.5")
    finally:
        service._lock.release()


@pytest.mark.asyncio
async def test_refresh_single_wallet_failure_returns_none(
    session_factory, db_session, btc_wallet
):
    """refresh_single_wallet should return None on failure."""
    db_session.add(btc_wallet)
    await db_session.commit()

    btc_client, kas_client, coingecko_client, ws_manager, history_service = (
        make_mock_clients()
    )
    btc_client.get_balance = AsyncMock(side_effect=Exception("API error"))

    service = make_refresh_service(
        session_factory,
        btc_client,
        kas_client,
        coingecko_client,
        ws_manager,
        history_service,
    )
    snapshot = await service.refresh_single_wallet(btc_wallet)
    assert snapshot is None
