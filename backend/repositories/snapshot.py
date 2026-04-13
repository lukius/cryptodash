from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.balance_snapshot import BalanceSnapshot
from backend.models.price_snapshot import PriceSnapshot

_BULK_BATCH_SIZE = 500


class BalanceSnapshotRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, snapshot: BalanceSnapshot) -> None:
        self.db.add(snapshot)

    async def bulk_create(self, snapshots: list[BalanceSnapshot]) -> None:
        if not snapshots:
            return
        for i in range(0, len(snapshots), _BULK_BATCH_SIZE):
            batch = snapshots[i : i + _BULK_BATCH_SIZE]
            for snap in batch:
                self.db.add(snap)

    async def get_latest_for_wallet(self, wallet_id: str) -> BalanceSnapshot | None:
        result = await self.db.execute(
            select(BalanceSnapshot)
            .where(BalanceSnapshot.wallet_id == wallet_id)
            .order_by(BalanceSnapshot.timestamp.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_range(
        self, wallet_id: str, start: datetime, end: datetime
    ) -> list[BalanceSnapshot]:
        result = await self.db.execute(
            select(BalanceSnapshot)
            .where(
                BalanceSnapshot.wallet_id == wallet_id,
                BalanceSnapshot.timestamp >= start,
                BalanceSnapshot.timestamp <= end,
            )
            .order_by(BalanceSnapshot.timestamp.asc())
        )
        return list(result.scalars().all())

    async def get_nearest_before(
        self, wallet_id: str, target: datetime
    ) -> BalanceSnapshot | None:
        result = await self.db.execute(
            select(BalanceSnapshot)
            .where(
                BalanceSnapshot.wallet_id == wallet_id,
                BalanceSnapshot.timestamp <= target,
            )
            .order_by(BalanceSnapshot.timestamp.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def delete_historical_for_wallet(self, wallet_id: str) -> None:
        await self.db.execute(
            delete(BalanceSnapshot).where(
                BalanceSnapshot.wallet_id == wallet_id,
                BalanceSnapshot.source == "historical",
            )
        )


class PriceSnapshotRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, snapshot: PriceSnapshot) -> None:
        self.db.add(snapshot)

    async def bulk_create(self, snapshots: list[PriceSnapshot]) -> None:
        if not snapshots:
            return
        for i in range(0, len(snapshots), _BULK_BATCH_SIZE):
            batch = snapshots[i : i + _BULK_BATCH_SIZE]
            for snap in batch:
                self.db.add(snap)

    async def get_latest(self, coin: str) -> PriceSnapshot | None:
        result = await self.db.execute(
            select(PriceSnapshot)
            .where(PriceSnapshot.coin == coin)
            .order_by(PriceSnapshot.timestamp.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_range(
        self, coin: str, start: datetime, end: datetime
    ) -> list[PriceSnapshot]:
        result = await self.db.execute(
            select(PriceSnapshot)
            .where(
                PriceSnapshot.coin == coin,
                PriceSnapshot.timestamp >= start,
                PriceSnapshot.timestamp <= end,
            )
            .order_by(PriceSnapshot.timestamp.asc())
        )
        return list(result.scalars().all())

    async def get_nearest_before(
        self, coin: str, target: datetime
    ) -> PriceSnapshot | None:
        result = await self.db.execute(
            select(PriceSnapshot)
            .where(
                PriceSnapshot.coin == coin,
                PriceSnapshot.timestamp <= target,
            )
            .order_by(PriceSnapshot.timestamp.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
