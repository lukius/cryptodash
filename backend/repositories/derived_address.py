from datetime import datetime
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.derived_address import DerivedAddress

_MAX_DERIVED_ADDRESSES = 200


class DerivedAddressRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def replace_all(
        self,
        wallet_id: str,
        addresses: list[dict],
        updated_at: datetime,
    ) -> int:
        """Atomically replaces all derived addresses for a wallet.

        'addresses' is a list of dicts with keys:
            "address"     — str, the derived Bitcoin address
            "balance_btc" — Decimal, balance in BTC (stored as string)
            "balance_sat" — int, balance in satoshis (used for sorting)

        Only the top 200 by balance_sat are stored (FR-H15).
        Returns the total count before capping.
        """
        total = len(addresses)

        top = sorted(addresses, key=lambda x: x["balance_sat"], reverse=True)[
            :_MAX_DERIVED_ADDRESSES
        ]

        await self.db.execute(
            delete(DerivedAddress).where(DerivedAddress.wallet_id == wallet_id)
        )

        for entry in top:
            row = DerivedAddress(
                id=str(uuid4()),
                wallet_id=wallet_id,
                address=entry["address"],
                current_balance_native=str(entry["balance_btc"]),
                balance_sat=entry["balance_sat"],
                last_updated_at=updated_at,
            )
            self.db.add(row)

        return total

    async def get_by_wallet(self, wallet_id: str) -> list[DerivedAddress]:
        """Returns derived addresses for a wallet ordered by balance_sat descending."""
        result = await self.db.execute(
            select(DerivedAddress)
            .where(DerivedAddress.wallet_id == wallet_id)
            .order_by(DerivedAddress.balance_sat.desc())
        )
        return list(result.scalars().all())
