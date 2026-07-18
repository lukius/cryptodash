"""One-time data repair tasks, run at app startup and guarded by config flags.

The app applies schema via ``Base.metadata.create_all`` rather than Alembic, so
data repairs live here to guarantee they run on every deployment path.
"""

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.models.wallet import Wallet
from backend.repositories.config import ConfigRepository
from backend.repositories.transaction import TransactionRepository

logger = logging.getLogger(__name__)

# Bump the suffix to force a re-run on all deployments (e.g. if the canonical
# transaction ordering ever changes again).
BALANCE_RECOMPUTE_FLAG = "maintenance:balance_recompute_v1"


async def recompute_transaction_balances(
    session_factory: async_sessionmaker[AsyncSession],
) -> int:
    """Recompute Transaction.balance_after for every wallet in the canonical
    (timestamp, block_height, tx_hash) order.

    Repairs rows written before the ordering became deterministic, where
    same-timestamp transactions could carry running balances inconsistent with
    the display order. Runs once; subsequent calls are no-ops.
    Returns the number of rows updated.
    """
    async with session_factory() as db:
        config_repo = ConfigRepository(db)
        if await config_repo.get(BALANCE_RECOMPUTE_FLAG) is not None:
            return 0

        tx_repo = TransactionRepository(db)
        wallet_ids = (await db.execute(select(Wallet.id))).scalars().all()

        updated = 0
        for wallet_id in wallet_ids:
            transactions = await tx_repo.list_by_wallet(wallet_id)
            running = Decimal("0")
            for tx in transactions:
                running += Decimal(tx.amount)
                if tx.balance_after is None or Decimal(tx.balance_after) != running:
                    tx.balance_after = str(running)
                    updated += 1

        await config_repo.set(BALANCE_RECOMPUTE_FLAG, "done")
        await db.commit()

    if updated:
        logger.info("Recomputed balance_after for %d transaction(s)", updated)
    return updated
