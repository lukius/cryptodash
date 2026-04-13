import asyncio
from decimal import Decimal

from backend.clients.base import BaseClient

SATOSHI = Decimal("100000000")  # 1 BTC = 10^8 satoshis


class BitcoinClient(BaseClient):
    def __init__(self):
        super().__init__(base_url="https://mempool.space/api")

    async def get_balance(self, address: str) -> Decimal:
        """Returns confirmed balance in BTC."""
        data = await self._get_with_retry(f"/address/{address}")
        funded = data["chain_stats"]["funded_txo_sum"]
        spent = data["chain_stats"]["spent_txo_sum"]
        return Decimal(funded - spent) / SATOSHI

    async def get_transaction_summary(self, address: str) -> list[dict]:
        """
        Uses /txs/summary endpoint — returns signed net satoshi values per tx.
        Returns up to 5000 most recent transactions.
        Each entry: { "txid": str, "height": int, "value": int (signed satoshis), "time": int }
        """
        return await self._get(f"/address/{address}/txs/summary")

    async def get_transactions_paginated(
        self, address: str, after_txid: str | None = None
    ) -> list[dict]:
        """
        Full transaction objects via /txs/chain with pagination.
        Returns 25 txs per page, newest first.
        Pass after_txid for next page.
        """
        path = f"/address/{address}/txs/chain"
        if after_txid:
            path += f"/{after_txid}"
        return await self._get(path)

    async def get_all_transactions(self, address: str) -> list[dict]:
        """
        Fetches ALL transactions for an address using the summary endpoint
        when tx count <= 5000, falling back to paginated full tx fetching
        with UTXO parsing for addresses with more transactions.
        Returns list of: { "tx_hash": str, "amount_sat": int (signed), "block_height": int, "timestamp": int }
        """
        summary = await self.get_transaction_summary(address)

        addr_info = await self._get(f"/address/{address}")
        total_txs = addr_info["chain_stats"]["tx_count"]

        if len(summary) >= total_txs or total_txs <= 5000:
            return [
                {
                    "tx_hash": tx["txid"],
                    "amount_sat": tx["value"],
                    "block_height": tx["height"],
                    "timestamp": tx["time"],
                }
                for tx in summary
            ]

        return await self._fetch_all_with_utxo_parsing(address)

    async def _fetch_all_with_utxo_parsing(self, address: str) -> list[dict]:
        """Paginate through /txs/chain and parse vin/vout for net amounts."""
        all_txs = []
        after_txid = None
        address_lower = address.lower()

        while True:
            page = await self.get_transactions_paginated(address, after_txid)
            if not page:
                break

            for tx in page:
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
                net = inflow - outflow
                status = tx.get("status", {})
                all_txs.append(
                    {
                        "tx_hash": tx["txid"],
                        "amount_sat": net,
                        "block_height": status.get("block_height"),
                        "timestamp": status.get("block_time"),
                    }
                )

            if len(page) < 25:
                break
            after_txid = page[-1]["txid"]

            await asyncio.sleep(0.2)

        return all_txs
