import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.models.balance_snapshot import BalanceSnapshot
from backend.models.price_snapshot import PriceSnapshot
from backend.models.wallet import Wallet
from backend.repositories.snapshot import (
    BalanceSnapshotRepository,
    PriceSnapshotRepository,
)
from backend.repositories.wallet import WalletRepository

logger = logging.getLogger(__name__)

_MAX_CONCURRENT = 5


@dataclass
class RefreshResult:
    success_count: int = 0
    failure_count: int = 0
    skipped: bool = False
    errors: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class RefreshService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        btc_client,
        kas_client,
        coingecko_client,
        ws_manager,
        history_service,
    ) -> None:
        self._session_factory = session_factory
        self.btc_client = btc_client
        self.kas_client = kas_client
        self.coingecko_client = coingecko_client
        self.ws_manager = ws_manager
        self.history_service = history_service
        self._lock = asyncio.Lock()

    async def run_full_refresh(self) -> RefreshResult:
        """Fetches balances for ALL wallets and prices for BTC+KAS.

        Precondition: acquires _lock non-blocking; if already locked, returns immediately
        with skipped=True.
        Postcondition: new snapshots stored and committed; WebSocket event broadcast.
        """
        acquired = self._lock.locked() is False and await self._try_acquire()
        if not acquired:
            logger.info("Refresh skipped — previous cycle still running")
            return RefreshResult(skipped=True)

        try:
            await self.ws_manager.broadcast("refresh:started", {})

            async with self._session_factory() as db:
                await self._fetch_prices(db)

                wallet_repo = WalletRepository(db)
                wallets = await wallet_repo.get_all()

                wallet_results = await self._fetch_all_wallets(db, wallets)

                await db.commit()

            success_count = sum(1 for r in wallet_results if r["success"])
            failure_count = sum(1 for r in wallet_results if not r["success"])
            errors = [
                r["error"] for r in wallet_results if not r["success"] and r["error"]
            ]

            refresh_result = RefreshResult(
                success_count=success_count,
                failure_count=failure_count,
                skipped=False,
                errors=errors,
                timestamp=datetime.now(timezone.utc),
            )

            await self.ws_manager.broadcast(
                "refresh:completed",
                {
                    "success_count": success_count,
                    "failure_count": failure_count,
                    "timestamp": refresh_result.timestamp.isoformat(),
                },
            )

            return refresh_result
        finally:
            self._lock.release()

    async def refresh_single_wallet(self, wallet: Wallet) -> BalanceSnapshot | None:
        """Fetches balance for one wallet. Used for initial fetch after adding.

        Does NOT acquire _lock (runs independently).
        Returns: BalanceSnapshot or None on failure.
        """
        try:
            balance = await self._get_balance(wallet)
            snap = BalanceSnapshot(
                id=str(uuid4()),
                wallet_id=wallet.id,
                balance=str(balance),
                timestamp=datetime.now(timezone.utc),
                source="live",
            )
            async with self._session_factory() as db:
                snap_repo = BalanceSnapshotRepository(db)
                await snap_repo.create(snap)
                await db.commit()
            return snap
        except Exception as exc:
            logger.warning("Balance fetch failed for %s: %s", wallet.tag, exc)
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _try_acquire(self) -> bool:
        """Attempt a non-blocking lock acquire. Returns True if acquired."""
        if self._lock.locked():
            return False
        await self._lock.acquire()
        return True

    async def _fetch_prices(self, db: AsyncSession) -> dict[str, Decimal]:
        """Fetch current prices and store as PriceSnapshots. Returns price map."""
        prices: dict[str, Decimal] = {}
        price_repo = PriceSnapshotRepository(db)
        now = datetime.now(timezone.utc)

        try:
            prices = await self.coingecko_client.get_current_prices()
        except Exception as exc:
            logger.warning(
                "CoinGecko price fetch failed: %s. Trying KAS fallback.", exc
            )
            try:
                kas_price = await self.kas_client.get_price_usd()
                if kas_price and kas_price > Decimal("0"):
                    prices["KAS"] = kas_price
            except Exception as fallback_exc:
                logger.warning("KAS price fallback also failed: %s", fallback_exc)

        # Store non-zero prices
        for coin, price in prices.items():
            if price and price > Decimal("0"):
                snap = PriceSnapshot(
                    id=str(uuid4()),
                    coin=coin,
                    price_usd=str(price),
                    timestamp=now,
                )
                await price_repo.create(snap)

        return prices

    async def _fetch_all_wallets(
        self, db: AsyncSession, wallets: list[Wallet]
    ) -> list[dict]:
        """Fetch balances for all wallets in parallel (up to _MAX_CONCURRENT at once)."""
        semaphore = asyncio.Semaphore(_MAX_CONCURRENT)

        async def fetch_one(wallet: Wallet) -> dict:
            async with semaphore:
                try:
                    balance = await self._get_balance(wallet)
                    snap = BalanceSnapshot(
                        id=str(uuid4()),
                        wallet_id=wallet.id,
                        balance=str(balance),
                        timestamp=datetime.now(timezone.utc),
                        source="live",
                    )
                    snap_repo = BalanceSnapshotRepository(db)
                    await snap_repo.create(snap)

                    try:
                        await self.history_service.incremental_sync(wallet)
                    except Exception as sync_exc:
                        logger.warning(
                            "Incremental sync failed for %s: %s", wallet.tag, sync_exc
                        )

                    return {"wallet_id": wallet.id, "success": True, "error": None}
                except Exception as exc:
                    logger.warning("Balance fetch failed for %s: %s", wallet.tag, exc)
                    return {
                        "wallet_id": wallet.id,
                        "success": False,
                        "error": str(exc),
                    }

        return list(await asyncio.gather(*[fetch_one(w) for w in wallets]))

    async def _get_balance(self, wallet: Wallet) -> Decimal:
        """Get balance from the appropriate client based on network."""
        if wallet.network == "BTC":
            return await self.btc_client.get_balance(wallet.address)
        elif wallet.network == "KAS":
            return await self.kas_client.get_balance(wallet.address)
        else:
            raise ValueError(f"Unsupported network: {wallet.network}")
