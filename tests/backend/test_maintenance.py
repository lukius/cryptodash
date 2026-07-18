"""Tests for the one-time balance_after recompute repair task."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.database import init_db
from backend.models.transaction import Transaction
from backend.models.user import User
from backend.models.wallet import Wallet
from backend.repositories.transaction import TransactionRepository
from backend.services.maintenance import (
    BALANCE_RECOMPUTE_FLAG,
    recompute_transaction_balances,
)


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


def _tx(
    wallet_id: str,
    tx_hash: str,
    amount: str,
    balance_after: str,
    block_height: int,
    timestamp: datetime,
) -> Transaction:
    return Transaction(
        id=str(uuid4()),
        wallet_id=wallet_id,
        tx_hash=tx_hash,
        amount=amount,
        balance_after=balance_after,
        block_height=block_height,
        timestamp=timestamp,
        created_at=datetime.now(timezone.utc),
    )


async def _seed_wallet_with_inconsistent_balances(session_factory) -> str:
    """Recreate the observed bug: two same-timestamp txs whose stored
    balance_after chain contradicts the deterministic (tx_hash) tie order."""
    async with session_factory() as db:
        user = User(
            id=str(uuid4()),
            username="alice",
            password_hash="$2b$12$hash",
            created_at=datetime.now(timezone.utc),
        )
        db.add(user)
        await db.flush()
        wallet = Wallet(
            id=str(uuid4()),
            user_id=user.id,
            network="BTC",
            address="zpub" + "a" * 40,
            tag="tresha",
            created_at=datetime.now(timezone.utc),
        )
        db.add(wallet)
        await db.flush()

        shared = datetime(2025, 4, 5, 18, 36, 14, tzinfo=timezone.utc)
        # Stored compute order was bbb-first: bbb got 0.33..., aaa got 0.39...
        # Deterministic order is aaa-first, so these are inconsistent.
        db.add(
            _tx(
                wallet.id,
                "bbb",
                "0.33032118",
                "0.33032118",
                891092,
                shared,
            )
        )
        db.add(
            _tx(
                wallet.id,
                "aaa",
                "0.05717685",
                "0.38749803",
                891092,
                shared,
            )
        )
        db.add(
            _tx(
                wallet.id,
                "ccc",
                "0.17891197",
                "0.56641000",
                891093,
                datetime(2025, 4, 5, 18, 38, 18, tzinfo=timezone.utc),
            )
        )
        await db.commit()
        return wallet.id


@pytest.mark.asyncio
async def test_recompute_fixes_inconsistent_balance_after(session_factory):
    wallet_id = await _seed_wallet_with_inconsistent_balances(session_factory)

    updated = await recompute_transaction_balances(session_factory)
    assert updated == 2  # aaa and bbb corrected; ccc unchanged

    async with session_factory() as db:
        stored = await TransactionRepository(db).list_by_wallet(wallet_id)

    by_hash = {tx.tx_hash: Decimal(tx.balance_after) for tx in stored}
    assert by_hash["aaa"] == Decimal("0.05717685")
    assert by_hash["bbb"] == Decimal("0.38749803")
    assert by_hash["ccc"] == Decimal("0.56641000")
    # The displayed (ascending) order now matches the running-balance chain
    balances = [Decimal(tx.balance_after) for tx in stored]
    amounts = [Decimal(tx.amount) for tx in stored]
    running = Decimal("0")
    for amount, balance in zip(amounts, balances):
        running += amount
        assert balance == running


@pytest.mark.asyncio
async def test_recompute_runs_only_once(session_factory):
    wallet_id = await _seed_wallet_with_inconsistent_balances(session_factory)

    first = await recompute_transaction_balances(session_factory)
    assert first == 2

    # Corrupt a row again — the guarded task must NOT touch it a second time
    async with session_factory() as db:
        stored = await TransactionRepository(db).list_by_wallet(wallet_id)
        stored[0].balance_after = "999"
        await db.commit()

    second = await recompute_transaction_balances(session_factory)
    assert second == 0

    async with session_factory() as db:
        stored = await TransactionRepository(db).list_by_wallet(wallet_id)
    assert stored[0].balance_after == "999"


@pytest.mark.asyncio
async def test_recompute_sets_flag(session_factory):
    await _seed_wallet_with_inconsistent_balances(session_factory)
    await recompute_transaction_balances(session_factory)

    from backend.repositories.config import ConfigRepository

    async with session_factory() as db:
        flag = await ConfigRepository(db).get(BALANCE_RECOMPUTE_FLAG)
    assert flag is not None
