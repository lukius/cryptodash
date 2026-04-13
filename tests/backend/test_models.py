"""Tests for SQLAlchemy ORM models (T02)."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from backend.models import (
    BalanceSnapshot,
    Configuration,
    PriceSnapshot,
    Session,
    Transaction,
    User,
    Wallet,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid4())


# ---------------------------------------------------------------------------
# Helpers to build model instances
# ---------------------------------------------------------------------------


def make_user(username: str = "alice") -> User:
    return User(
        id=_uuid(),
        username=username,
        password_hash="$2b$12$hashedvalue",
        created_at=_now(),
    )


def make_wallet(user_id: str, network: str = "BTC", address: str = "addr1") -> Wallet:
    return Wallet(
        id=_uuid(),
        user_id=user_id,
        network=network,
        address=address,
        tag="my wallet",
        created_at=_now(),
    )


def make_transaction(wallet_id: str, tx_hash: str = "abc123") -> Transaction:
    return Transaction(
        id=_uuid(),
        wallet_id=wallet_id,
        tx_hash=tx_hash,
        amount="0.001",
        balance_after="1.001",
        block_height=800000,
        timestamp=_now(),
        created_at=_now(),
    )


def make_balance_snapshot(wallet_id: str) -> BalanceSnapshot:
    return BalanceSnapshot(
        id=_uuid(),
        wallet_id=wallet_id,
        balance="1.001",
        timestamp=_now(),
        source="live",
    )


# ---------------------------------------------------------------------------
# User model
# ---------------------------------------------------------------------------


async def test_user_create_and_query(db_session):
    user = make_user("bob")
    db_session.add(user)
    await db_session.flush()

    result = await db_session.get(User, user.id)
    assert result is not None
    assert result.username == "bob"
    assert result.password_hash == "$2b$12$hashedvalue"
    assert isinstance(result.created_at, datetime)


async def test_user_username_unique_constraint(db_session):
    user1 = make_user("carol")
    user2 = make_user("carol")  # same username
    db_session.add(user1)
    await db_session.flush()

    db_session.add(user2)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_user_username_required(db_session):
    user = User(id=_uuid(), password_hash="hash", created_at=_now())
    db_session.add(user)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_user_password_hash_required(db_session):
    user = User(id=_uuid(), username="dave", created_at=_now())
    db_session.add(user)
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ---------------------------------------------------------------------------
# Session model
# ---------------------------------------------------------------------------


async def test_session_create_and_query(db_session):
    user = make_user("eve")
    db_session.add(user)
    await db_session.flush()

    session = Session(
        id=_uuid(),
        user_id=user.id,
        token="tok_" + _uuid(),
        created_at=_now(),
        expires_at=_now(),
    )
    db_session.add(session)
    await db_session.flush()

    result = await db_session.get(Session, session.id)
    assert result is not None
    assert result.user_id == user.id
    assert result.token == session.token


async def test_session_token_unique_constraint(db_session):
    user = make_user("frank")
    db_session.add(user)
    await db_session.flush()

    token = "shared_token_xyz"
    s1 = Session(
        id=_uuid(), user_id=user.id, token=token, created_at=_now(), expires_at=_now()
    )
    s2 = Session(
        id=_uuid(), user_id=user.id, token=token, created_at=_now(), expires_at=_now()
    )

    db_session.add(s1)
    await db_session.flush()

    db_session.add(s2)
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ---------------------------------------------------------------------------
# Wallet model
# ---------------------------------------------------------------------------


async def test_wallet_create_and_query(db_session):
    user = make_user("grace")
    db_session.add(user)
    await db_session.flush()

    wallet = make_wallet(user.id, "BTC", "bc1qtest")
    db_session.add(wallet)
    await db_session.flush()

    result = await db_session.get(Wallet, wallet.id)
    assert result is not None
    assert result.network == "BTC"
    assert result.address == "bc1qtest"
    assert result.tag == "my wallet"


async def test_wallet_unique_constraint_user_network_address(db_session):
    user = make_user("heidi")
    db_session.add(user)
    await db_session.flush()

    w1 = make_wallet(user.id, "BTC", "same_address")
    w2 = make_wallet(user.id, "BTC", "same_address")

    db_session.add(w1)
    await db_session.flush()

    db_session.add(w2)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_wallet_same_address_different_network_allowed(db_session):
    user = make_user("ivan")
    db_session.add(user)
    await db_session.flush()

    w1 = make_wallet(user.id, "BTC", "shared_addr")
    w2 = make_wallet(user.id, "KAS", "shared_addr")
    w2.tag = "kas wallet"

    db_session.add(w1)
    db_session.add(w2)
    await db_session.flush()  # should not raise


async def test_wallet_cascade_delete_transactions(db_session):
    user = make_user("judy")
    db_session.add(user)
    await db_session.flush()

    wallet = make_wallet(user.id)
    db_session.add(wallet)
    await db_session.flush()

    tx = make_transaction(wallet.id)
    db_session.add(tx)
    await db_session.flush()

    tx_id = tx.id
    await db_session.delete(wallet)
    await db_session.flush()

    result = await db_session.get(Transaction, tx_id)
    assert result is None, "Transaction should be deleted when wallet is deleted"


async def test_wallet_cascade_delete_balance_snapshots(db_session):
    user = make_user("ken")
    db_session.add(user)
    await db_session.flush()

    wallet = make_wallet(user.id)
    db_session.add(wallet)
    await db_session.flush()

    snap = make_balance_snapshot(wallet.id)
    db_session.add(snap)
    await db_session.flush()

    snap_id = snap.id
    await db_session.delete(wallet)
    await db_session.flush()

    result = await db_session.get(BalanceSnapshot, snap_id)
    assert result is None, "BalanceSnapshot should be deleted when wallet is deleted"


async def test_wallet_cascade_delete_all_children(db_session):
    user = make_user("lena")
    db_session.add(user)
    await db_session.flush()

    wallet = make_wallet(user.id)
    db_session.add(wallet)
    await db_session.flush()

    tx = make_transaction(wallet.id)
    snap = make_balance_snapshot(wallet.id)
    db_session.add(tx)
    db_session.add(snap)
    await db_session.flush()

    tx_id = tx.id
    snap_id = snap.id

    await db_session.delete(wallet)
    await db_session.flush()

    assert (
        await db_session.get(Transaction, tx_id) is None
    ), "Transaction should be deleted when wallet is deleted"
    assert (
        await db_session.get(BalanceSnapshot, snap_id) is None
    ), "BalanceSnapshot should be deleted when wallet is deleted"


# ---------------------------------------------------------------------------
# Transaction model
# ---------------------------------------------------------------------------


async def test_transaction_create_and_query(db_session):
    user = make_user("lisa")
    db_session.add(user)
    await db_session.flush()

    wallet = make_wallet(user.id)
    db_session.add(wallet)
    await db_session.flush()

    tx = make_transaction(wallet.id, "deadbeef")
    db_session.add(tx)
    await db_session.flush()

    result = await db_session.get(Transaction, tx.id)
    assert result is not None
    assert result.tx_hash == "deadbeef"
    assert result.amount == "0.001"
    assert result.balance_after == "1.001"
    assert result.block_height == 800000


async def test_transaction_nullable_fields(db_session):
    user = make_user("mike")
    db_session.add(user)
    await db_session.flush()

    wallet = make_wallet(user.id)
    db_session.add(wallet)
    await db_session.flush()

    tx = Transaction(
        id=_uuid(),
        wallet_id=wallet.id,
        tx_hash="nulltest",
        amount="-0.5",
        balance_after=None,  # nullable
        block_height=None,  # nullable
        timestamp=_now(),
        created_at=_now(),
    )
    db_session.add(tx)
    await db_session.flush()

    result = await db_session.get(Transaction, tx.id)
    assert result.balance_after is None
    assert result.block_height is None


async def test_transaction_unique_constraint_wallet_tx_hash(db_session):
    user = make_user("nina")
    db_session.add(user)
    await db_session.flush()

    wallet = make_wallet(user.id)
    db_session.add(wallet)
    await db_session.flush()

    tx1 = make_transaction(wallet.id, "samehash")
    tx2 = make_transaction(wallet.id, "samehash")

    db_session.add(tx1)
    await db_session.flush()

    db_session.add(tx2)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_transaction_same_hash_different_wallet_allowed(db_session):
    user = make_user("oscar")
    db_session.add(user)
    await db_session.flush()

    w1 = make_wallet(user.id, "BTC", "addr_w1")
    w2 = make_wallet(user.id, "KAS", "addr_w2")
    w2.tag = "second wallet"
    db_session.add(w1)
    db_session.add(w2)
    await db_session.flush()

    tx1 = make_transaction(w1.id, "sharedhash")
    tx2 = make_transaction(w2.id, "sharedhash")
    db_session.add(tx1)
    db_session.add(tx2)
    await db_session.flush()  # should not raise


# ---------------------------------------------------------------------------
# BalanceSnapshot model
# ---------------------------------------------------------------------------


async def test_balance_snapshot_create_and_query(db_session):
    user = make_user("pat")
    db_session.add(user)
    await db_session.flush()

    wallet = make_wallet(user.id)
    db_session.add(wallet)
    await db_session.flush()

    snap = make_balance_snapshot(wallet.id)
    db_session.add(snap)
    await db_session.flush()

    result = await db_session.get(BalanceSnapshot, snap.id)
    assert result is not None
    assert result.balance == "1.001"
    assert result.source == "live"


async def test_balance_snapshot_source_required(db_session):
    user = make_user("quinn")
    db_session.add(user)
    await db_session.flush()

    wallet = make_wallet(user.id)
    db_session.add(wallet)
    await db_session.flush()

    snap = BalanceSnapshot(
        id=_uuid(),
        wallet_id=wallet.id,
        balance="1.0",
        timestamp=_now(),
        source=None,  # required field
    )
    db_session.add(snap)
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ---------------------------------------------------------------------------
# PriceSnapshot model
# ---------------------------------------------------------------------------


async def test_price_snapshot_create_and_query(db_session):
    snap = PriceSnapshot(
        id=_uuid(),
        coin="BTC",
        price_usd="65000.50",
        timestamp=_now(),
    )
    db_session.add(snap)
    await db_session.flush()

    result = await db_session.get(PriceSnapshot, snap.id)
    assert result is not None
    assert result.coin == "BTC"
    assert result.price_usd == "65000.50"


async def test_price_snapshot_coin_required(db_session):
    snap = PriceSnapshot(
        id=_uuid(),
        coin=None,  # required
        price_usd="100.0",
        timestamp=_now(),
    )
    db_session.add(snap)
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ---------------------------------------------------------------------------
# Configuration model
# ---------------------------------------------------------------------------


async def test_configuration_create_and_query(db_session):
    cfg = Configuration(
        key="theme",
        value="dark",
        updated_at=_now(),
    )
    db_session.add(cfg)
    await db_session.flush()

    result = await db_session.get(Configuration, "theme")
    assert result is not None
    assert result.value == "dark"


async def test_configuration_key_is_primary_key(db_session):
    cfg1 = Configuration(key="same_key", value="val1", updated_at=_now())

    db_session.add(cfg1)
    await db_session.flush()
    db_session.expunge(cfg1)  # remove from identity map so the DB constraint is hit

    cfg2 = Configuration(key="same_key", value="val2", updated_at=_now())
    db_session.add(cfg2)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_configuration_value_required(db_session):
    cfg = Configuration(key="some_key", value=None, updated_at=_now())
    db_session.add(cfg)
    with pytest.raises(IntegrityError):
        await db_session.flush()
