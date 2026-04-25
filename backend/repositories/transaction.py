from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.transaction import Transaction

_BULK_BATCH_SIZE = 500


class TransactionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_wallet_and_hash(
        self, wallet_id: str, tx_hash: str
    ) -> Transaction | None:
        result = await self.db.execute(
            select(Transaction).where(
                Transaction.wallet_id == wallet_id,
                Transaction.tx_hash == tx_hash,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_wallet(self, wallet_id: str) -> list[Transaction]:
        result = await self.db.execute(
            select(Transaction)
            .where(Transaction.wallet_id == wallet_id)
            .order_by(Transaction.timestamp.asc())
        )
        return list(result.scalars().all())

    async def list_by_wallet_paginated(
        self, wallet_id: str, limit: int, offset: int
    ) -> tuple[list[Transaction], int]:
        count_result = await self.db.execute(
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.wallet_id == wallet_id)
        )
        total = count_result.scalar_one()
        result = await self.db.execute(
            select(Transaction)
            .where(Transaction.wallet_id == wallet_id)
            .order_by(Transaction.timestamp.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    async def list_by_wallet_in_range(
        self, wallet_id: str, start: datetime, end: datetime
    ) -> list[Transaction]:
        result = await self.db.execute(
            select(Transaction)
            .where(
                Transaction.wallet_id == wallet_id,
                Transaction.timestamp >= start,
                Transaction.timestamp <= end,
            )
            .order_by(Transaction.timestamp.asc())
        )
        return list(result.scalars().all())

    async def bulk_create(self, transactions: list[Transaction]) -> None:
        if not transactions:
            return
        for i in range(0, len(transactions), _BULK_BATCH_SIZE):
            batch = transactions[i : i + _BULK_BATCH_SIZE]
            rows = [
                {
                    "id": tx.id,
                    "wallet_id": tx.wallet_id,
                    "tx_hash": tx.tx_hash,
                    "amount": tx.amount,
                    "balance_after": tx.balance_after,
                    "block_height": tx.block_height,
                    "timestamp": tx.timestamp,
                    "created_at": tx.created_at,
                }
                for tx in batch
            ]
            stmt = sqlite_insert(Transaction).values(rows).prefix_with("OR IGNORE")
            await self.db.execute(stmt)

    async def get_latest_for_wallet(self, wallet_id: str) -> Transaction | None:
        result = await self.db.execute(
            select(Transaction)
            .where(Transaction.wallet_id == wallet_id)
            .order_by(
                Transaction.block_height.desc().nullslast(),
                Transaction.timestamp.desc(),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def exists_by_hash(self, wallet_id: str, tx_hash: str) -> bool:
        result = await self.db.execute(
            select(func.count())
            .select_from(Transaction)
            .where(
                Transaction.wallet_id == wallet_id,
                Transaction.tx_hash == tx_hash,
            )
        )
        return result.scalar_one() > 0

    async def compute_balance(self, wallet_id: str) -> Decimal | None:
        # amount is stored as a string; sum in Python using Decimal for precision
        result = await self.db.execute(
            select(Transaction.amount).where(Transaction.wallet_id == wallet_id)
        )
        amounts = result.scalars().all()
        if not amounts:
            return None
        return sum((Decimal(a) for a in amounts), Decimal("0"))
