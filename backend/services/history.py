import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.models.balance_snapshot import BalanceSnapshot
from backend.models.price_snapshot import PriceSnapshot
from backend.models.transaction import Transaction
from backend.models.wallet import Wallet
from backend.repositories.snapshot import (
    BalanceSnapshotRepository,
    PriceSnapshotRepository,
)
from backend.repositories.transaction import TransactionRepository

logger = logging.getLogger(__name__)

SATOSHI = Decimal("100000000")
SOMPI = Decimal("100000000")


@dataclass
class HistoryImportResult:
    partial: bool = False
    tx_count: int = 0
    message: str | None = None


class HistoryService:
    IMPORT_TIMEOUT = 300  # 5 minutes

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        btc_client,
        kas_client,
        coingecko_client,
        ws_manager,
    ) -> None:
        self._session_factory = session_factory
        self.btc_client = btc_client
        self.kas_client = kas_client
        self.coingecko_client = coingecko_client
        self.ws_manager = ws_manager

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def full_import(self, wallet: Wallet) -> HistoryImportResult:
        """One-time full transaction history import for a newly added wallet."""
        try:
            result = await asyncio.wait_for(
                self._do_full_import(wallet),
                timeout=self.IMPORT_TIMEOUT,
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(
                "History import timed out for %s. Partial data stored.", wallet.tag
            )
            msg = "Import timed out. Incremental syncs will pick up remaining data."
            await self.ws_manager.broadcast(
                "wallet:history:completed",
                {
                    "wallet_id": wallet.id,
                    "partial": True,
                    "message": msg,
                },
            )
            return HistoryImportResult(partial=True, message=msg)

    async def incremental_sync(self, wallet: Wallet) -> int:
        """Fetch only transactions newer than the most recent stored one.

        Uses stop-early per-network pagination — never re-fetches the full history.
        Returns: number of new transactions stored.
        """
        async with self._session_factory() as db:
            return await self._incremental_sync_with_db(db, wallet)

    async def fetch_price_history(self, network: str, days: int) -> int:
        """Fetch historical prices from CoinGecko and store as PriceSnapshots.
        Returns count of price snapshots created."""
        async with self._session_factory() as db:
            return await self._fetch_price_history_with_db(db, network, days)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _do_full_import(self, wallet: Wallet) -> HistoryImportResult:
        """The actual import logic, wrapped by wait_for in full_import."""
        async with self._session_factory() as db:
            result = await self._do_full_import_with_db(db, wallet)
            await db.commit()
            return result

    async def _do_full_import_with_db(
        self, db: AsyncSession, wallet: Wallet
    ) -> HistoryImportResult:
        """Session-scoped full import logic."""
        tx_repo = TransactionRepository(db)
        snap_repo = BalanceSnapshotRepository(db)

        await self.ws_manager.broadcast(
            "wallet:history:progress",
            {"wallet_id": wallet.id, "status": "started"},
        )

        # Fetch raw transactions from the appropriate client
        raw_txs = await self._fetch_raw_transactions(wallet)

        # Sort ascending by timestamp for correct running balance
        sorted_raw = sorted(raw_txs, key=lambda t: t["_timestamp"])

        # Build Transaction records, deduplicating by hash
        tx_records: list[Transaction] = []
        running_balance = Decimal("0")
        now = datetime.now(timezone.utc)

        for raw in sorted_raw:
            tx_hash = raw["_tx_hash"]
            already_exists = await tx_repo.exists_by_hash(wallet.id, tx_hash)
            if already_exists:
                # Still need to account for this tx in the running balance
                # to maintain correct balance_after for new txs that follow.
                stored = await tx_repo.get_by_wallet_and_hash(wallet.id, tx_hash)
                if stored is not None and stored.balance_after is not None:
                    running_balance = Decimal(stored.balance_after)
                continue

            amount = raw["_amount"]
            running_balance += amount
            tx = Transaction(
                id=str(uuid4()),
                wallet_id=wallet.id,
                tx_hash=tx_hash,
                amount=str(amount),
                balance_after=str(running_balance),
                block_height=raw.get("_block_height"),
                timestamp=raw["_timestamp_dt"],
                created_at=now,
            )
            tx_records.append(tx)

        # Batch-insert transactions
        await tx_repo.bulk_create(tx_records)

        # Compute daily end-of-day balances and store as BalanceSnapshot(source="historical").
        # Delete any pre-existing historical snapshots first to avoid duplicates on re-runs.
        await snap_repo.delete_historical_for_wallet(wallet.id)
        all_stored = await tx_repo.list_by_wallet(wallet.id)
        daily_snapshots = _compute_daily_snapshots(wallet.id, all_stored)
        await snap_repo.bulk_create(daily_snapshots)

        # Fetch historical prices (up to 365 days) — reuse the current session
        await self._fetch_price_history_with_db(db, wallet.network, 365)

        # Broadcast completion
        await self.ws_manager.broadcast(
            "wallet:history:completed",
            {"wallet_id": wallet.id, "partial": False},
        )

        return HistoryImportResult(partial=False, tx_count=len(tx_records))

    async def _fetch_price_history_with_db(
        self, db: AsyncSession, network: str, days: int
    ) -> int:
        """Fetch historical prices from CoinGecko and store as PriceSnapshots.
        Returns count of price snapshots created."""
        price_repo = PriceSnapshotRepository(db)
        price_data = await self.coingecko_client.get_price_history(network, days)
        snapshots = []
        for ts_ms, price_usd in price_data:
            snap = PriceSnapshot(
                id=str(uuid4()),
                coin=network,
                price_usd=str(price_usd),
                timestamp=datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc),
            )
            snapshots.append(snap)
        await price_repo.bulk_create(snapshots)
        return len(snapshots)

    async def _incremental_sync_with_db(self, db: AsyncSession, wallet: Wallet) -> int:
        """Session-scoped incremental sync logic."""
        tx_repo = TransactionRepository(db)
        snap_repo = BalanceSnapshotRepository(db)

        # Get the current balance from stored transactions
        current_balance = await tx_repo.compute_balance(wallet.id)
        if current_balance is None:
            current_balance = Decimal("0")

        # Fetch only new raw transactions using stop-early pagination
        if wallet.network == "BTC":
            new_raw = await self._incremental_sync_btc(wallet, tx_repo)
        elif wallet.network == "KAS":
            new_raw = await self._incremental_sync_kas(wallet, tx_repo)
        else:
            raise ValueError(f"Unsupported network: {wallet.network}")

        if not new_raw:
            return 0

        # Sort ascending so running balance is correct
        sorted_raw = sorted(new_raw, key=lambda t: t["_timestamp"])

        running_balance = current_balance
        now = datetime.now(timezone.utc)
        new_tx_records: list[Transaction] = []

        for raw in sorted_raw:
            amount = raw["_amount"]
            running_balance += amount
            tx = Transaction(
                id=str(uuid4()),
                wallet_id=wallet.id,
                tx_hash=raw["_tx_hash"],
                amount=str(amount),
                balance_after=str(running_balance),
                block_height=raw.get("_block_height"),
                timestamp=raw["_timestamp_dt"],
                created_at=now,
            )
            new_tx_records.append(tx)

        await tx_repo.bulk_create(new_tx_records)

        # Store a live balance snapshot
        snap = BalanceSnapshot(
            id=str(uuid4()),
            wallet_id=wallet.id,
            balance=str(running_balance),
            timestamp=datetime.now(timezone.utc),
            source="live",
        )
        await snap_repo.create(snap)
        await db.commit()

        return len(new_tx_records)

    async def _fetch_raw_transactions(self, wallet: Wallet) -> list[dict]:
        """Fetch all transactions from the appropriate client and normalize.

        Used for full_import only. Returns list of normalized dicts.
        """
        if wallet.network == "BTC":
            raw = await self.btc_client.get_all_transactions(wallet.address)
            return [_normalize_btc_tx(tx) for tx in raw]
        elif wallet.network == "KAS":
            raw = await self.kas_client.get_all_transactions(wallet.address)
            return [_normalize_kas_tx(tx) for tx in raw]
        else:
            raise ValueError(f"Unsupported network: {wallet.network}")

    async def _incremental_sync_btc(
        self, wallet: Wallet, tx_repo: TransactionRepository
    ) -> list[dict]:
        """Paginate BTC transactions newest-first, stopping when we hit a known txid.

        Uses get_transactions_paginated (25 per page, full tx objects) so we never
        re-fetch the full history — FR-026/FR-027 compliant.
        """
        new_txs: list[dict] = []
        after_txid: str | None = None
        address_lower = wallet.address.lower()

        while True:
            page = await self.btc_client.get_transactions_paginated(
                wallet.address, after_txid=after_txid
            )
            if not page:
                break

            stop = False
            for tx in page:
                txid = tx["txid"]
                if await tx_repo.exists_by_hash(wallet.id, txid):
                    stop = True
                    break

                # Parse net amount via vin/vout
                inflow = sum(
                    vout["value"]
                    for vout in tx.get("vout", [])
                    if vout.get("scriptpubkey_address", "").lower() == address_lower
                )
                outflow = sum(
                    vin["prevout"]["value"]
                    for vin in tx.get("vin", [])
                    if vin.get("prevout")
                    and vin["prevout"].get("scriptpubkey_address", "").lower()
                    == address_lower
                )
                net_sat = inflow - outflow
                status = tx.get("status", {})
                new_txs.append(
                    {
                        "_tx_hash": txid,
                        "_amount": Decimal(net_sat) / SATOSHI,
                        "_block_height": status.get("block_height"),
                        "_timestamp": status.get("block_time", 0),
                        "_timestamp_dt": datetime.fromtimestamp(
                            status.get("block_time", 0), tz=timezone.utc
                        ),
                    }
                )

            if stop or len(page) < 25:
                break
            after_txid = page[-1]["txid"]

        return new_txs

    async def _incremental_sync_kas(
        self, wallet: Wallet, tx_repo: TransactionRepository
    ) -> list[dict]:
        """Paginate KAS transactions newest-first, stopping when we hit a known txid.

        Uses get_transactions_page with cursor-based pagination.
        """
        new_txs: list[dict] = []
        cursor: int | None = None

        while True:
            page, next_cursor = await self.kas_client.get_transactions_page(
                wallet.address, before=cursor
            )
            if not page:
                break

            stop = False
            for tx in page:
                if not tx.get("is_accepted", False):
                    continue

                txid = tx["transaction_id"]
                if await tx_repo.exists_by_hash(wallet.id, txid):
                    stop = True
                    break

                inflow = sum(
                    int(out["amount"])
                    for out in (tx.get("outputs") or [])
                    if out.get("script_public_key_address") == wallet.address
                )
                outflow = sum(
                    int(inp["previous_outpoint_amount"])
                    for inp in (tx.get("inputs") or [])
                    if inp.get("previous_outpoint_address") == wallet.address
                )
                net_sompi = inflow - outflow
                timestamp_ms = tx.get("block_time", 0)
                timestamp_s = timestamp_ms / 1000
                new_txs.append(
                    {
                        "_tx_hash": txid,
                        "_amount": Decimal(net_sompi) / SOMPI,
                        "_block_height": None,
                        "_timestamp": timestamp_s,
                        "_timestamp_dt": datetime.fromtimestamp(
                            timestamp_s, tz=timezone.utc
                        ),
                    }
                )

            if stop or next_cursor is None:
                break
            cursor = next_cursor

        return new_txs


# ------------------------------------------------------------------
# Pure helper functions
# ------------------------------------------------------------------


def _normalize_btc_tx(tx: dict) -> dict:
    """Convert a raw BTC tx dict (from get_all_transactions) to internal format."""
    timestamp_s = tx["timestamp"]
    dt = datetime.fromtimestamp(timestamp_s, tz=timezone.utc)
    return {
        "_tx_hash": tx["tx_hash"],
        "_amount": Decimal(tx["amount_sat"]) / SATOSHI,
        "_block_height": tx.get("block_height"),
        "_timestamp": timestamp_s,
        "_timestamp_dt": dt,
    }


def _normalize_kas_tx(tx: dict) -> dict:
    """Convert a raw Kaspa tx dict (from get_all_transactions) to internal format.

    Kaspa timestamps are in milliseconds.
    """
    timestamp_ms = tx["timestamp"]
    timestamp_s = timestamp_ms / 1000
    dt = datetime.fromtimestamp(timestamp_s, tz=timezone.utc)
    return {
        "_tx_hash": tx["tx_hash"],
        "_amount": Decimal(tx["amount_sompi"]) / SOMPI,
        "_block_height": None,
        "_timestamp": timestamp_s,
        "_timestamp_dt": dt,
    }


def _compute_daily_snapshots(
    wallet_id: str, transactions: list[Transaction]
) -> list[BalanceSnapshot]:
    """Group transactions by UTC calendar day and emit one BalanceSnapshot per day
    (the end-of-day balance after all that day's transactions).

    Skips any transaction where balance_after is None (defensive guard).
    """
    if not transactions:
        return []

    # Group by date, keeping last tx of the day (list is already sorted ASC)
    by_day: dict[tuple, Transaction] = {}
    for tx in transactions:
        if tx.balance_after is None:
            continue
        day_key = (tx.timestamp.year, tx.timestamp.month, tx.timestamp.day)
        by_day[day_key] = tx

    snapshots = []
    for (year, month, day), last_tx in sorted(by_day.items()):
        snap = BalanceSnapshot(
            id=str(uuid4()),
            wallet_id=wallet_id,
            balance=last_tx.balance_after,
            timestamp=datetime(year, month, day, 23, 59, 59, tzinfo=timezone.utc),
            source="historical",
        )
        snapshots.append(snap)
    return snapshots
