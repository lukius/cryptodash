import asyncio
from decimal import Decimal

from backend.clients.base import BaseClient

SOMPI = Decimal("100000000")  # 1 KAS = 10^8 sompi


class KaspaClient(BaseClient):
    def __init__(self):
        super().__init__(base_url="https://api.kaspa.org")

    async def get_balance(self, address: str) -> Decimal:
        """Returns balance in KAS."""
        data = await self._get_with_retry(f"/addresses/{address}/balance")
        return Decimal(str(data["balance"])) / SOMPI

    async def get_price_usd(self) -> Decimal:
        """Returns KAS/USD price from Kaspa's own API. Used as fallback."""
        data = await self._get("/info/price")
        return Decimal(str(data["price"]))

    async def get_transaction_count(self, address: str) -> int:
        data = await self._get(f"/addresses/{address}/transactions-count")
        return data["total"]

    async def get_transactions_page(
        self, address: str, limit: int = 500, before: int | None = None
    ) -> tuple[list[dict], int | None]:
        """
        Fetches a page of transactions using cursor-based pagination.
        Returns (transactions, next_before_cursor).
        next_before_cursor is None when no more pages.
        """
        params = {
            "limit": limit,
            "resolve_previous_outpoints": "light",
            "fields": "transaction_id,block_time,inputs,outputs,is_accepted",
        }
        if before is not None:
            params["before"] = before

        response = await self._client.get(
            f"/addresses/{address}/full-transactions-page",
            params=params,
        )
        response.raise_for_status()

        next_before = response.headers.get("X-Next-Page-Before")
        next_cursor = int(next_before) if next_before else None

        return response.json(), next_cursor

    async def get_all_transactions(self, address: str) -> list[dict]:
        """
        Fetches all transactions for a Kaspa address with UTXO-style parsing.
        Returns list of: { "tx_hash": str, "amount_sompi": int (signed), "timestamp": int }
        """
        all_txs = []
        cursor = None

        while True:
            page, next_cursor = await self.get_transactions_page(
                address, limit=500, before=cursor
            )
            if not page:
                break

            for tx in page:
                if not tx.get("is_accepted", False):
                    continue

                inflow = sum(
                    int(out["amount"])
                    for out in (tx.get("outputs") or [])
                    if out.get("script_public_key_address") == address
                )
                outflow = sum(
                    int(inp["previous_outpoint_amount"])
                    for inp in (tx.get("inputs") or [])
                    if inp.get("previous_outpoint_address") == address
                )
                net = inflow - outflow

                all_txs.append(
                    {
                        "tx_hash": tx["transaction_id"],
                        "amount_sompi": net,
                        "timestamp": tx.get("block_time"),
                    }
                )

            if next_cursor is None:
                break
            cursor = next_cursor

            await asyncio.sleep(0.2)

        return all_txs
