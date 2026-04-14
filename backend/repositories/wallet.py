from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.wallet import Wallet


class WalletRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, wallet: Wallet) -> Wallet:
        self.db.add(wallet)
        return wallet

    async def get_by_id(self, wallet_id: str, user_id: str) -> Wallet | None:
        result = await self.db.execute(
            select(Wallet).where(Wallet.id == wallet_id, Wallet.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self, user_id: str) -> list[Wallet]:
        result = await self.db.execute(select(Wallet).where(Wallet.user_id == user_id))
        return list(result.scalars().all())

    async def get_all(self) -> list[Wallet]:
        """Return all wallets across all users. Used for system-level operations (e.g. refresh)."""
        result = await self.db.execute(select(Wallet))
        return list(result.scalars().all())

    async def count_by_user(self, user_id: str) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Wallet).where(Wallet.user_id == user_id)
        )
        return result.scalar_one()

    async def update_tag(self, wallet_id: str, tag: str) -> None:
        result = await self.db.execute(select(Wallet).where(Wallet.id == wallet_id))
        wallet = result.scalar_one_or_none()
        if wallet is not None:
            wallet.tag = tag

    async def delete(self, wallet_id: str) -> None:
        result = await self.db.execute(select(Wallet).where(Wallet.id == wallet_id))
        wallet = result.scalar_one_or_none()
        if wallet is not None:
            await self.db.delete(wallet)

    async def exists_by_address(
        self, user_id: str, network: str, normalized_address: str
    ) -> bool:
        result = await self.db.execute(
            select(func.count())
            .select_from(Wallet)
            .where(
                Wallet.user_id == user_id,
                Wallet.network == network,
                func.lower(Wallet.address) == normalized_address.lower(),
            )
        )
        return result.scalar_one() > 0

    async def exists_by_address_exact(
        self, user_id: str, network: str, address: str
    ) -> bool:
        """Case-sensitive exact-match duplicate check.

        Used for HD wallet keys (FR-H06: comparison is exact-match, case-sensitive).
        Individual BTC addresses use the case-insensitive `exists_by_address` instead.
        """
        result = await self.db.execute(
            select(func.count())
            .select_from(Wallet)
            .where(
                Wallet.user_id == user_id,
                Wallet.network == network,
                Wallet.address == address,
            )
        )
        return result.scalar_one() > 0

    async def tag_exists(
        self,
        user_id: str,
        tag: str,
        exclude_wallet_id: str | None = None,
    ) -> bool:
        stmt = (
            select(func.count())
            .select_from(Wallet)
            .where(
                Wallet.user_id == user_id,
                func.lower(Wallet.tag) == tag.lower(),
            )
        )
        if exclude_wallet_id is not None:
            stmt = stmt.where(Wallet.id != exclude_wallet_id)
        result = await self.db.execute(stmt)
        return result.scalar_one() > 0
