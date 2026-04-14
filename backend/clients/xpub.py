"""XpubClient — blockchain.info multiaddr endpoint for HD wallet queries."""

import asyncio
from dataclasses import dataclass
from decimal import Decimal

from backend.clients.base import BaseClient

SATOSHI = Decimal("100000000")  # 1 BTC = 10^8 satoshis


@dataclass
class DerivedAddressData:
    address: str
    balance_sat: int  # confirmed balance in satoshis
    n_tx: int  # number of on-chain transactions


@dataclass
class XpubSummary:
    balance_sat: int  # aggregate confirmed balance in satoshis
    balance_btc: Decimal  # = balance_sat / SATOSHI
    n_tx: int  # total transaction count
    derived_addresses: list[DerivedAddressData]  # ALL active addresses


@dataclass
class XpubTransaction:
    tx_hash: str
    timestamp: (
        int | None
    )  # Unix epoch seconds (block confirmation time); None for unconfirmed
    block_height: int | None
    amount_sat: int  # signed net satoshi amount (positive = received, negative = sent)


class XpubClient(BaseClient):
    _TX_PAGE_SIZE = 50

    def __init__(self):
        super().__init__(base_url="https://blockchain.info", timeout=30.0)

    async def get_xpub_summary(self, xpub_normalized: str) -> XpubSummary:
        """
        Fetches aggregate balance and the full active derived address list.
        The 'addresses' array in the multiaddr response is complete in a single
        call (not paginated by n/offset).

        Parameters:
          xpub_normalized: an xpub-format key (convert ypub/zpub first).
        Returns: XpubSummary with aggregate balance and list of DerivedAddressData.
        Raises: httpx.HTTPStatusError, httpx.RequestError on API failure.
        """
        data = await self._get_with_retry(
            "/multiaddr",
            params={"active": xpub_normalized, "n": 1, "offset": 0},
        )
        wallet = data.get("wallet", {})
        balance_sat = wallet.get("final_balance", 0)
        n_tx = data.get("info", {}).get("n_tx", 0)

        derived = []
        for addr in data.get("addresses", []):
            if addr.get("n_tx", 0) > 0:  # FR-H13: active addresses only
                derived.append(
                    DerivedAddressData(
                        address=addr["address"],
                        balance_sat=addr.get("final_balance", 0),
                        n_tx=addr.get("n_tx", 0),
                    )
                )

        return XpubSummary(
            balance_sat=balance_sat,
            balance_btc=Decimal(balance_sat) / SATOSHI,
            n_tx=n_tx,
            derived_addresses=derived,
        )

    async def get_xpub_transactions_all(
        self, xpub_normalized: str
    ) -> list[XpubTransaction]:
        """
        Fetches ALL transactions for the xpub by paginating through the
        multiaddr endpoint with offset=0, 50, 100, ... until the txs array
        is empty or we've retrieved all n_tx transactions.
        Returns list of XpubTransaction sorted oldest-first.
        Adds a 0.2s sleep between pages to respect rate limits.
        """
        # First call: determine total tx count
        first_page = await self._get_with_retry(
            "/multiaddr",
            params={"active": xpub_normalized, "n": self._TX_PAGE_SIZE, "offset": 0},
        )
        total = first_page.get("info", {}).get("n_tx", 0)
        all_txs = self._parse_txs(first_page.get("txs", []))

        offset = self._TX_PAGE_SIZE
        while offset < total:
            await asyncio.sleep(0.2)
            page = await self._get_with_retry(
                "/multiaddr",
                params={
                    "active": xpub_normalized,
                    "n": self._TX_PAGE_SIZE,
                    "offset": offset,
                },
            )
            txs = self._parse_txs(page.get("txs", []))
            if not txs:
                break
            all_txs.extend(txs)
            offset += self._TX_PAGE_SIZE

        # Sort oldest-first for history replay
        all_txs.sort(
            key=lambda t: (
                t.timestamp if t.timestamp is not None else 0,
                t.block_height or 0,
            )
        )
        return all_txs

    async def get_xpub_transactions_since(
        self, xpub_normalized: str, after_timestamp: int
    ) -> list[XpubTransaction]:
        """
        Fetches transactions newer than after_timestamp (Unix epoch seconds).
        Paginates until we encounter a transaction at or before after_timestamp.
        Used for incremental sync.
        Returns list sorted oldest-first.
        """
        new_txs = []
        offset = 0
        while True:
            page = await self._get_with_retry(
                "/multiaddr",
                params={
                    "active": xpub_normalized,
                    "n": self._TX_PAGE_SIZE,
                    "offset": offset,
                },
            )
            txs = self._parse_txs(page.get("txs", []))
            if not txs:
                break
            for tx in txs:
                if (tx.timestamp if tx.timestamp is not None else 0) > after_timestamp:
                    new_txs.append(tx)
                else:
                    # Reached already-known transactions (API returns newest first)
                    new_txs.sort(
                        key=lambda t: (t.timestamp if t.timestamp is not None else 0)
                    )
                    return new_txs
            offset += self._TX_PAGE_SIZE
            await asyncio.sleep(0.2)

        new_txs.sort(key=lambda t: (t.timestamp if t.timestamp is not None else 0))
        return new_txs

    def _parse_txs(self, raw_txs: list[dict]) -> list[XpubTransaction]:
        """Parse raw multiaddr transaction objects into XpubTransaction.

        Unconfirmed transactions have time=None in the API response; their
        timestamp is preserved as None so callers can detect and skip them
        during history replay.
        """
        result = []
        for tx in raw_txs:
            raw_time = tx.get("time")
            # Unconfirmed transactions have time=None — preserve None so
            # the service layer can skip them during balance reconstruction.
            timestamp: int | None = raw_time if raw_time is not None else None
            result.append(
                XpubTransaction(
                    tx_hash=tx.get("hash", ""),
                    timestamp=timestamp,
                    block_height=tx.get("block_height"),
                    amount_sat=tx.get("result", 0),
                )
            )
        return result
