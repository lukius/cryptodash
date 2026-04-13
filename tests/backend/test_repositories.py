"""Tests for the repository layer (T03)."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from backend.models import (
    BalanceSnapshot,
    PriceSnapshot,
    Session,
    Transaction,
    User,
    Wallet,
)
from backend.repositories import (
    BalanceSnapshotRepository,
    ConfigRepository,
    PriceSnapshotRepository,
    SessionRepository,
    TransactionRepository,
    UserRepository,
    WalletRepository,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid4())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_user(username: str = "alice") -> User:
    return User(
        id=_uuid(),
        username=username,
        password_hash="$2b$12$hashedvalue",
        created_at=_now(),
    )


def make_wallet(
    user_id: str,
    network: str = "BTC",
    address: str = "addr1",
    tag: str = "my wallet",
) -> Wallet:
    return Wallet(
        id=_uuid(),
        user_id=user_id,
        network=network,
        address=address,
        tag=tag,
        created_at=_now(),
    )


def make_transaction(
    wallet_id: str,
    tx_hash: str = "abc123",
    amount: str = "0.001",
    timestamp: datetime | None = None,
    block_height: int | None = 800000,
) -> Transaction:
    return Transaction(
        id=_uuid(),
        wallet_id=wallet_id,
        tx_hash=tx_hash,
        amount=amount,
        balance_after=None,
        block_height=block_height,
        timestamp=timestamp or _now(),
        created_at=_now(),
    )


def make_balance_snapshot(
    wallet_id: str,
    balance: str = "1.001",
    timestamp: datetime | None = None,
    source: str = "live",
) -> BalanceSnapshot:
    return BalanceSnapshot(
        id=_uuid(),
        wallet_id=wallet_id,
        balance=balance,
        timestamp=timestamp or _now(),
        source=source,
    )


def make_price_snapshot(
    coin: str = "BTC",
    price_usd: str = "65000.50",
    timestamp: datetime | None = None,
) -> PriceSnapshot:
    return PriceSnapshot(
        id=_uuid(),
        coin=coin,
        price_usd=price_usd,
        timestamp=timestamp or _now(),
    )


# ---------------------------------------------------------------------------
# UserRepository
# ---------------------------------------------------------------------------


async def test_user_create(db_session):
    repo = UserRepository(db_session)
    user = make_user("bob")
    created = await repo.create(user)
    await db_session.flush()

    assert created.id == user.id
    assert created.username == "bob"


async def test_user_get_by_username(db_session):
    repo = UserRepository(db_session)
    user = make_user("carol")
    await repo.create(user)
    await db_session.flush()

    result = await repo.get_by_username("carol")
    assert result is not None
    assert result.id == user.id


async def test_user_get_by_username_not_found(db_session):
    repo = UserRepository(db_session)
    result = await repo.get_by_username("nobody")
    assert result is None


async def test_user_get_by_id(db_session):
    repo = UserRepository(db_session)
    user = make_user("dave")
    await repo.create(user)
    await db_session.flush()

    result = await repo.get_by_id(user.id)
    assert result is not None
    assert result.username == "dave"


async def test_user_get_by_id_not_found(db_session):
    repo = UserRepository(db_session)
    result = await repo.get_by_id(_uuid())
    assert result is None


async def test_user_exists_false_when_empty(db_session):
    repo = UserRepository(db_session)
    assert await repo.exists() is False


async def test_user_exists_true_when_user_present(db_session):
    repo = UserRepository(db_session)
    user = make_user("eve")
    await repo.create(user)
    await db_session.flush()

    assert await repo.exists() is True


async def test_user_update_password_hash(db_session):
    repo = UserRepository(db_session)
    user = make_user("frank")
    await repo.create(user)
    await db_session.flush()

    await repo.update_password_hash(user.id, "new_hash_xyz")
    await db_session.flush()

    updated = await repo.get_by_id(user.id)
    assert updated.password_hash == "new_hash_xyz"


async def test_user_get_first_returns_user(db_session):
    repo = UserRepository(db_session)
    user = make_user("greta")
    await repo.create(user)
    await db_session.flush()

    result = await repo.get_first()
    assert result is not None
    assert result.id == user.id


async def test_user_get_first_returns_none_when_empty(db_session):
    repo = UserRepository(db_session)
    result = await repo.get_first()
    assert result is None


# ---------------------------------------------------------------------------
# SessionRepository
# ---------------------------------------------------------------------------


async def test_session_create(db_session):
    user = make_user("grace")
    db_session.add(user)
    await db_session.flush()

    repo = SessionRepository(db_session)
    session = Session(
        id=_uuid(),
        user_id=user.id,
        token="tok_abc",
        created_at=_now(),
        expires_at=_now() + timedelta(hours=1),
    )
    created = await repo.create(session)
    await db_session.flush()

    assert created.token == "tok_abc"


async def test_session_get_by_token(db_session):
    user = make_user("heidi")
    db_session.add(user)
    await db_session.flush()

    repo = SessionRepository(db_session)
    token = "tok_" + _uuid()
    session = Session(
        id=_uuid(),
        user_id=user.id,
        token=token,
        created_at=_now(),
        expires_at=_now() + timedelta(hours=1),
    )
    await repo.create(session)
    await db_session.flush()

    result = await repo.get_by_token(token)
    assert result is not None
    assert result.user_id == user.id


async def test_session_get_by_token_not_found(db_session):
    repo = SessionRepository(db_session)
    result = await repo.get_by_token("nonexistent_token")
    assert result is None


async def test_session_delete_by_token(db_session):
    user = make_user("ivan")
    db_session.add(user)
    await db_session.flush()

    repo = SessionRepository(db_session)
    token = "tok_del_" + _uuid()
    session = Session(
        id=_uuid(),
        user_id=user.id,
        token=token,
        created_at=_now(),
        expires_at=_now() + timedelta(hours=1),
    )
    await repo.create(session)
    await db_session.flush()

    await repo.delete_by_token(token)
    await db_session.flush()

    result = await repo.get_by_token(token)
    assert result is None


async def test_session_delete_all_for_user(db_session):
    user = make_user("judy")
    db_session.add(user)
    await db_session.flush()

    repo = SessionRepository(db_session)
    tokens = []
    for i in range(3):
        tok = f"tok_{i}_{_uuid()}"
        tokens.append(tok)
        s = Session(
            id=_uuid(),
            user_id=user.id,
            token=tok,
            created_at=_now(),
            expires_at=_now() + timedelta(hours=1),
        )
        await repo.create(s)
    await db_session.flush()

    await repo.delete_all_for_user(user.id)
    await db_session.flush()

    for tok in tokens:
        assert await repo.get_by_token(tok) is None


async def test_session_delete_expired(db_session):
    user = make_user("ken")
    db_session.add(user)
    await db_session.flush()

    repo = SessionRepository(db_session)
    expired_token = "tok_expired_" + _uuid()
    active_token = "tok_active_" + _uuid()

    expired = Session(
        id=_uuid(),
        user_id=user.id,
        token=expired_token,
        created_at=_now() - timedelta(hours=2),
        expires_at=_now() - timedelta(hours=1),  # already expired
    )
    active = Session(
        id=_uuid(),
        user_id=user.id,
        token=active_token,
        created_at=_now(),
        expires_at=_now() + timedelta(hours=1),
    )
    await repo.create(expired)
    await repo.create(active)
    await db_session.flush()

    cutoff = _now()
    count = await repo.delete_expired(before=cutoff)
    await db_session.flush()

    assert count == 1
    assert await repo.get_by_token(expired_token) is None
    assert await repo.get_by_token(active_token) is not None


async def test_session_delete_all(db_session):
    user = make_user("lars")
    db_session.add(user)
    await db_session.flush()

    repo = SessionRepository(db_session)
    tokens = []
    for i in range(3):
        tok = f"tok_all_{i}_{_uuid()}"
        tokens.append(tok)
        s = Session(
            id=_uuid(),
            user_id=user.id,
            token=tok,
            created_at=_now(),
            expires_at=_now() + timedelta(hours=1),
        )
        await repo.create(s)
    await db_session.flush()

    await repo.delete_all()
    await db_session.flush()

    for tok in tokens:
        assert await repo.get_by_token(tok) is None


# ---------------------------------------------------------------------------
# WalletRepository
# ---------------------------------------------------------------------------


async def test_wallet_create(db_session):
    user = make_user("lena")
    db_session.add(user)
    await db_session.flush()

    repo = WalletRepository(db_session)
    wallet = make_wallet(user.id, "BTC", "bc1qtest")
    created = await repo.create(wallet)
    await db_session.flush()

    assert created.id == wallet.id
    assert created.address == "bc1qtest"


async def test_wallet_get_by_id(db_session):
    user = make_user("lisa")
    db_session.add(user)
    await db_session.flush()

    repo = WalletRepository(db_session)
    wallet = make_wallet(user.id)
    await repo.create(wallet)
    await db_session.flush()

    result = await repo.get_by_id(wallet.id, user.id)
    assert result is not None
    assert result.id == wallet.id


async def test_wallet_get_by_id_not_found(db_session):
    repo = WalletRepository(db_session)
    result = await repo.get_by_id(_uuid(), _uuid())
    assert result is None


async def test_wallet_get_by_id_wrong_user_returns_none(db_session):
    user = make_user("lisa2")
    other_user = make_user("eve2")
    db_session.add(user)
    db_session.add(other_user)
    await db_session.flush()

    repo = WalletRepository(db_session)
    wallet = make_wallet(user.id)
    await repo.create(wallet)
    await db_session.flush()

    # Querying with the wrong user_id must return None (IDOR prevention)
    result = await repo.get_by_id(wallet.id, other_user.id)
    assert result is None


async def test_wallet_list_all(db_session):
    user = make_user("mike")
    db_session.add(user)
    await db_session.flush()

    repo = WalletRepository(db_session)
    w1 = make_wallet(user.id, "BTC", "addr1", "Wallet 1")
    w2 = make_wallet(user.id, "KAS", "addr2", "Wallet 2")
    await repo.create(w1)
    await repo.create(w2)
    await db_session.flush()

    wallets = await repo.list_all(user.id)
    assert len(wallets) == 2


async def test_wallet_list_all_empty(db_session):
    repo = WalletRepository(db_session)
    wallets = await repo.list_all(_uuid())
    assert wallets == []


async def test_wallet_get_all_returns_all_users_wallets(db_session):
    user_a = make_user("get_all_a")
    user_b = make_user("get_all_b")
    db_session.add(user_a)
    db_session.add(user_b)
    await db_session.flush()

    repo = WalletRepository(db_session)
    w1 = make_wallet(user_a.id, "BTC", "addr_ga1", "Wallet A1")
    w2 = make_wallet(user_b.id, "KAS", "addr_ga2", "Wallet B1")
    await repo.create(w1)
    await repo.create(w2)
    await db_session.flush()

    wallets = await repo.get_all()
    wallet_ids = {w.id for w in wallets}
    assert w1.id in wallet_ids
    assert w2.id in wallet_ids


async def test_wallet_get_all_empty(db_session):
    repo = WalletRepository(db_session)
    wallets = await repo.get_all()
    assert wallets == []


async def test_wallet_count_by_user(db_session):
    user = make_user("nina")
    db_session.add(user)
    await db_session.flush()

    repo = WalletRepository(db_session)
    w1 = make_wallet(user.id, "BTC", "addr1", "Wallet 1")
    w2 = make_wallet(user.id, "KAS", "addr2", "Wallet 2")
    await repo.create(w1)
    await repo.create(w2)
    await db_session.flush()

    count = await repo.count_by_user(user.id)
    assert count == 2


async def test_wallet_update_tag(db_session):
    user = make_user("oscar")
    db_session.add(user)
    await db_session.flush()

    repo = WalletRepository(db_session)
    wallet = make_wallet(user.id, tag="old tag")
    await repo.create(wallet)
    await db_session.flush()

    await repo.update_tag(wallet.id, "new tag")
    await db_session.flush()

    updated = await repo.get_by_id(wallet.id, user.id)
    assert updated.tag == "new tag"


async def test_wallet_delete(db_session):
    user = make_user("pat")
    db_session.add(user)
    await db_session.flush()

    repo = WalletRepository(db_session)
    wallet = make_wallet(user.id)
    await repo.create(wallet)
    await db_session.flush()

    await repo.delete(wallet.id)
    await db_session.flush()

    result = await repo.get_by_id(wallet.id, user.id)
    assert result is None


async def test_wallet_exists_by_address(db_session):
    user = make_user("quinn")
    db_session.add(user)
    await db_session.flush()

    repo = WalletRepository(db_session)
    wallet = make_wallet(user.id, "BTC", "BC1QADDRESS")
    await repo.create(wallet)
    await db_session.flush()

    assert await repo.exists_by_address(user.id, "BTC", "BC1QADDRESS") is True
    assert (
        await repo.exists_by_address(user.id, "BTC", "bc1qaddress") is True
    )  # case-insensitive
    assert await repo.exists_by_address(user.id, "KAS", "BC1QADDRESS") is False
    assert await repo.exists_by_address(user.id, "BTC", "other_address") is False


async def test_wallet_exists_by_address_false_when_none(db_session):
    repo = WalletRepository(db_session)
    assert await repo.exists_by_address(_uuid(), "BTC", "someaddr") is False


async def test_wallet_tag_exists(db_session):
    user = make_user("ruth")
    db_session.add(user)
    await db_session.flush()

    repo = WalletRepository(db_session)
    wallet = make_wallet(user.id, tag="My BTC Wallet")
    await repo.create(wallet)
    await db_session.flush()

    assert await repo.tag_exists(user.id, "My BTC Wallet") is True
    assert await repo.tag_exists(user.id, "my btc wallet") is True  # case-insensitive
    assert await repo.tag_exists(user.id, "MY BTC WALLET") is True
    assert await repo.tag_exists(user.id, "Other Tag") is False


async def test_wallet_tag_exists_exclude(db_session):
    user = make_user("sam")
    db_session.add(user)
    await db_session.flush()

    repo = WalletRepository(db_session)
    wallet = make_wallet(user.id, tag="Existing Tag")
    await repo.create(wallet)
    await db_session.flush()

    # Excluding the wallet that owns the tag should return False
    assert (
        await repo.tag_exists(user.id, "Existing Tag", exclude_wallet_id=wallet.id)
        is False
    )
    # Without exclusion should return True
    assert await repo.tag_exists(user.id, "Existing Tag") is True


# ---------------------------------------------------------------------------
# TransactionRepository
# ---------------------------------------------------------------------------


async def test_transaction_bulk_create(db_session):
    user = make_user("tina")
    db_session.add(user)
    await db_session.flush()

    wallet = make_wallet(user.id)
    db_session.add(wallet)
    await db_session.flush()

    repo = TransactionRepository(db_session)
    txs = [
        make_transaction(wallet.id, f"hash_{i}", amount=f"0.00{i + 1}")
        for i in range(5)
    ]
    await repo.bulk_create(txs)
    await db_session.flush()

    listed = await repo.list_by_wallet(wallet.id)
    assert len(listed) == 5


async def test_transaction_bulk_create_deduplication(db_session):
    user = make_user("uma")
    db_session.add(user)
    await db_session.flush()

    wallet = make_wallet(user.id)
    db_session.add(wallet)
    await db_session.flush()

    repo = TransactionRepository(db_session)
    txs = [make_transaction(wallet.id, "same_hash", amount="0.001")]
    await repo.bulk_create(txs)
    await db_session.flush()

    # Insert the same hash again — should not raise and should not duplicate
    duplicate_txs = [make_transaction(wallet.id, "same_hash", amount="0.002")]
    await repo.bulk_create(duplicate_txs)
    await db_session.flush()

    listed = await repo.list_by_wallet(wallet.id)
    assert len(listed) == 1


async def test_transaction_list_by_wallet_ordered_by_timestamp(db_session):
    user = make_user("vera")
    db_session.add(user)
    await db_session.flush()

    wallet = make_wallet(user.id)
    db_session.add(wallet)
    await db_session.flush()

    repo = TransactionRepository(db_session)
    base_time = _now()
    txs = [
        make_transaction(
            wallet.id, f"hash_{i}", timestamp=base_time + timedelta(minutes=i)
        )
        for i in range(3)
    ]
    # Insert in reverse order
    await repo.bulk_create(list(reversed(txs)))
    await db_session.flush()

    listed = await repo.list_by_wallet(wallet.id)
    assert len(listed) == 3
    assert listed[0].timestamp <= listed[1].timestamp <= listed[2].timestamp


async def test_transaction_list_by_wallet_in_range(db_session):
    user = make_user("wendy")
    db_session.add(user)
    await db_session.flush()

    wallet = make_wallet(user.id)
    db_session.add(wallet)
    await db_session.flush()

    repo = TransactionRepository(db_session)
    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    txs = [
        make_transaction(wallet.id, f"hash_{i}", timestamp=base + timedelta(hours=i))
        for i in range(5)
    ]
    await repo.bulk_create(txs)
    await db_session.flush()

    start = base + timedelta(hours=1)
    end = base + timedelta(hours=3)
    result = await repo.list_by_wallet_in_range(wallet.id, start, end)
    # Should include hours 1, 2, 3
    assert len(result) == 3


async def test_transaction_get_latest_for_wallet(db_session):
    user = make_user("xena")
    db_session.add(user)
    await db_session.flush()

    wallet = make_wallet(user.id)
    db_session.add(wallet)
    await db_session.flush()

    repo = TransactionRepository(db_session)
    base_time = _now()
    txs = [
        make_transaction(
            wallet.id,
            f"hash_{i}",
            block_height=800000 + i,
            timestamp=base_time + timedelta(minutes=i),
        )
        for i in range(3)
    ]
    await repo.bulk_create(txs)
    await db_session.flush()

    latest = await repo.get_latest_for_wallet(wallet.id)
    assert latest is not None
    assert latest.block_height == 800002


async def test_transaction_get_latest_for_wallet_none(db_session):
    repo = TransactionRepository(db_session)
    result = await repo.get_latest_for_wallet(_uuid())
    assert result is None


async def test_transaction_exists_by_hash(db_session):
    user = make_user("yvonne")
    db_session.add(user)
    await db_session.flush()

    wallet = make_wallet(user.id)
    db_session.add(wallet)
    await db_session.flush()

    repo = TransactionRepository(db_session)
    tx = make_transaction(wallet.id, "existing_hash")
    await repo.bulk_create([tx])
    await db_session.flush()

    assert await repo.exists_by_hash(wallet.id, "existing_hash") is True
    assert await repo.exists_by_hash(wallet.id, "nonexistent_hash") is False


async def test_transaction_compute_balance(db_session):
    user = make_user("zara")
    db_session.add(user)
    await db_session.flush()

    wallet = make_wallet(user.id)
    db_session.add(wallet)
    await db_session.flush()

    repo = TransactionRepository(db_session)
    txs = [
        make_transaction(wallet.id, "hash_1", amount="1.5"),
        make_transaction(wallet.id, "hash_2", amount="-0.3"),
        make_transaction(wallet.id, "hash_3", amount="0.2"),
    ]
    await repo.bulk_create(txs)
    await db_session.flush()

    balance = await repo.compute_balance(wallet.id)
    assert balance == Decimal("1.4")


async def test_transaction_compute_balance_none_when_empty(db_session):
    repo = TransactionRepository(db_session)
    balance = await repo.compute_balance(_uuid())
    assert balance is None


async def test_transaction_get_by_wallet_and_hash(db_session):
    user = make_user("amy")
    db_session.add(user)
    await db_session.flush()

    wallet = make_wallet(user.id)
    db_session.add(wallet)
    await db_session.flush()

    repo = TransactionRepository(db_session)
    tx = make_transaction(wallet.id, "findme_hash")
    await repo.bulk_create([tx])
    await db_session.flush()

    result = await repo.get_by_wallet_and_hash(wallet.id, "findme_hash")
    assert result is not None
    assert result.tx_hash == "findme_hash"

    result_none = await repo.get_by_wallet_and_hash(wallet.id, "nothere")
    assert result_none is None


# ---------------------------------------------------------------------------
# BalanceSnapshotRepository
# ---------------------------------------------------------------------------


async def test_balance_snapshot_create(db_session):
    user = make_user("bella")
    db_session.add(user)
    await db_session.flush()

    wallet = make_wallet(user.id)
    db_session.add(wallet)
    await db_session.flush()

    repo = BalanceSnapshotRepository(db_session)
    snap = make_balance_snapshot(wallet.id, balance="2.5")
    await repo.create(snap)
    await db_session.flush()

    result = await db_session.get(BalanceSnapshot, snap.id)
    assert result is not None
    assert result.balance == "2.5"


async def test_balance_snapshot_bulk_create(db_session):
    user = make_user("bianca")
    db_session.add(user)
    await db_session.flush()

    wallet = make_wallet(user.id)
    db_session.add(wallet)
    await db_session.flush()

    repo = BalanceSnapshotRepository(db_session)
    base = _now()
    snaps = [
        make_balance_snapshot(
            wallet.id, balance=f"{i}.0", timestamp=base + timedelta(hours=i)
        )
        for i in range(3)
    ]
    await repo.bulk_create(snaps)
    await db_session.flush()

    latest = await repo.get_latest_for_wallet(wallet.id)
    assert latest is not None
    assert latest.balance == "2.0"


async def test_balance_snapshot_get_latest_for_wallet(db_session):
    user = make_user("chloe")
    db_session.add(user)
    await db_session.flush()

    wallet = make_wallet(user.id)
    db_session.add(wallet)
    await db_session.flush()

    repo = BalanceSnapshotRepository(db_session)
    base = _now()
    snaps = [
        make_balance_snapshot(
            wallet.id, balance=f"{i}.0", timestamp=base + timedelta(hours=i)
        )
        for i in range(3)
    ]
    for s in snaps:
        await repo.create(s)
    await db_session.flush()

    latest = await repo.get_latest_for_wallet(wallet.id)
    assert latest is not None
    assert latest.balance == "2.0"


async def test_balance_snapshot_get_latest_for_wallet_none(db_session):
    repo = BalanceSnapshotRepository(db_session)
    result = await repo.get_latest_for_wallet(_uuid())
    assert result is None


async def test_balance_snapshot_get_range(db_session):
    user = make_user("diana")
    db_session.add(user)
    await db_session.flush()

    wallet = make_wallet(user.id)
    db_session.add(wallet)
    await db_session.flush()

    repo = BalanceSnapshotRepository(db_session)
    base = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    snaps = [
        make_balance_snapshot(wallet.id, timestamp=base + timedelta(hours=i))
        for i in range(5)
    ]
    for s in snaps:
        await repo.create(s)
    await db_session.flush()

    start = base + timedelta(hours=1)
    end = base + timedelta(hours=3)
    result = await repo.get_range(wallet.id, start, end)
    assert len(result) == 3


async def test_balance_snapshot_get_nearest_before(db_session):
    user = make_user("emma")
    db_session.add(user)
    await db_session.flush()

    wallet = make_wallet(user.id)
    db_session.add(wallet)
    await db_session.flush()

    repo = BalanceSnapshotRepository(db_session)
    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    # Snapshots at base-1h (balance "1.0"), base-2h ("2.0"), base-3h ("3.0")
    snaps = [
        make_balance_snapshot(
            wallet.id, balance=f"{i}.0", timestamp=base - timedelta(hours=i)
        )
        for i in range(1, 4)
    ]
    for s in snaps:
        await repo.create(s)
    await db_session.flush()

    # target = base - 1.5h: the latest snapshot at or before target is base-2h ("2.0")
    target = base - timedelta(hours=1, minutes=30)
    result = await repo.get_nearest_before(wallet.id, target)
    assert result is not None
    assert result.balance == "2.0"


async def test_balance_snapshot_get_nearest_before_excludes_after(db_session):
    user = make_user("fiona")
    db_session.add(user)
    await db_session.flush()

    wallet = make_wallet(user.id)
    db_session.add(wallet)
    await db_session.flush()

    repo = BalanceSnapshotRepository(db_session)
    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    # Only a snapshot AFTER the target
    snap = make_balance_snapshot(
        wallet.id, balance="5.0", timestamp=base + timedelta(hours=1)
    )
    await repo.create(snap)
    await db_session.flush()

    # target is before all snapshots — should return None
    result = await repo.get_nearest_before(wallet.id, base)
    assert result is None


# ---------------------------------------------------------------------------
# PriceSnapshotRepository
# ---------------------------------------------------------------------------


async def test_price_snapshot_create(db_session):
    repo = PriceSnapshotRepository(db_session)
    snap = make_price_snapshot("BTC", "65000.00")
    await repo.create(snap)
    await db_session.flush()

    result = await db_session.get(PriceSnapshot, snap.id)
    assert result is not None
    assert result.price_usd == "65000.00"


async def test_price_snapshot_bulk_create(db_session):
    repo = PriceSnapshotRepository(db_session)
    snaps = [make_price_snapshot("BTC", f"{60000 + i}.00") for i in range(5)]
    await repo.bulk_create(snaps)
    await db_session.flush()

    latest = await repo.get_latest("BTC")
    assert latest is not None


async def test_price_snapshot_get_latest(db_session):
    repo = PriceSnapshotRepository(db_session)
    base = _now()
    snaps = [
        make_price_snapshot(
            "BTC", f"{60000 + i}.00", timestamp=base + timedelta(hours=i)
        )
        for i in range(3)
    ]
    await repo.bulk_create(snaps)
    await db_session.flush()

    latest = await repo.get_latest("BTC")
    assert latest is not None
    assert latest.price_usd == "60002.00"


async def test_price_snapshot_get_latest_none(db_session):
    repo = PriceSnapshotRepository(db_session)
    result = await repo.get_latest("XYZ")
    assert result is None


async def test_price_snapshot_get_range(db_session):
    repo = PriceSnapshotRepository(db_session)
    base = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    snaps = [
        make_price_snapshot("KAS", "0.10", timestamp=base + timedelta(hours=i))
        for i in range(5)
    ]
    await repo.bulk_create(snaps)
    await db_session.flush()

    start = base + timedelta(hours=1)
    end = base + timedelta(hours=3)
    result = await repo.get_range("KAS", start, end)
    assert len(result) == 3


async def test_price_snapshot_get_nearest_before(db_session):
    repo = PriceSnapshotRepository(db_session)
    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    # Snapshots at base-1h ($60100), base-2h ($60200), base-3h ($60300)
    snaps = [
        make_price_snapshot(
            "BTC",
            f"{60000 + i * 100}.00",
            timestamp=base - timedelta(hours=i),
        )
        for i in range(1, 4)
    ]
    await repo.bulk_create(snaps)
    await db_session.flush()

    # target = base - 1.5h: the latest snapshot at or before target is base-2h ($60200)
    target = base - timedelta(hours=1, minutes=30)
    result = await repo.get_nearest_before("BTC", target)
    assert result is not None
    assert result.price_usd == "60200.00"


async def test_price_snapshot_get_nearest_before_excludes_after(db_session):
    repo = PriceSnapshotRepository(db_session)
    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    snap = make_price_snapshot("BTC", "60000.00", timestamp=base + timedelta(hours=1))
    await repo.bulk_create([snap])
    await db_session.flush()

    # target is before all snapshots — should return None
    result = await repo.get_nearest_before("BTC", base)
    assert result is None


async def test_price_snapshot_get_nearest_before_none(db_session):
    repo = PriceSnapshotRepository(db_session)
    result = await repo.get_nearest_before("XYZ", _now())
    assert result is None


# ---------------------------------------------------------------------------
# ConfigRepository
# ---------------------------------------------------------------------------


async def test_config_set_and_get(db_session):
    repo = ConfigRepository(db_session)
    await repo.set("theme", "dark")
    await db_session.flush()

    value = await repo.get("theme")
    assert value == "dark"


async def test_config_get_returns_none_when_missing(db_session):
    repo = ConfigRepository(db_session)
    result = await repo.get("nonexistent_key")
    assert result is None


async def test_config_set_overwrites(db_session):
    repo = ConfigRepository(db_session)
    await repo.set("color", "red")
    await db_session.flush()

    await repo.set("color", "blue")
    await db_session.flush()

    value = await repo.get("color")
    assert value == "blue"


async def test_config_set_default_only_sets_once(db_session):
    repo = ConfigRepository(db_session)
    await repo.set_default("interval", "15")
    await db_session.flush()

    await repo.set_default("interval", "30")
    await db_session.flush()

    value = await repo.get("interval")
    assert value == "15"  # not overwritten


async def test_config_set_default_sets_when_missing(db_session):
    repo = ConfigRepository(db_session)
    await repo.set_default("new_key", "initial")
    await db_session.flush()

    value = await repo.get("new_key")
    assert value == "initial"


async def test_config_get_int(db_session):
    repo = ConfigRepository(db_session)
    await repo.set("max_wallets", "10")
    await db_session.flush()

    value = await repo.get_int("max_wallets")
    assert value == 10


async def test_config_get_int_returns_none_when_missing(db_session):
    repo = ConfigRepository(db_session)
    result = await repo.get_int("missing_key")
    assert result is None
