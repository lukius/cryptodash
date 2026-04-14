"""XpubClient — mempool.space per-address backend for HD wallet queries.

Replaces the blockchain.info multiaddr approach. Derives addresses locally
using hd_derive.py, then queries mempool.space per-address endpoints in
parallel (semaphore-limited).

Address types derived based on key prefix:
  zpub → bc1q... (P2WPKH, BIP84)
  ypub → 3...    (P2SH-P2WPKH, BIP49)
  xpub → 1...    (P2PKH, BIP44)
"""

import asyncio
from dataclasses import dataclass
from decimal import Decimal

from backend.clients.base import BaseClient
from backend.clients.hd_derive import derive_address_at

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
    GAP_LIMIT = 20
    _CONCURRENCY = 3

    def __init__(self):
        super().__init__(base_url="https://mempool.space/api", timeout=30.0)

    async def get_xpub_summary(self, key: str) -> XpubSummary:
        """Fetch aggregate balance and active derived address list.

        Parameters:
          key: the original xpub/ypub/zpub key (not normalized).
        Returns: XpubSummary with aggregate balance and list of DerivedAddressData.
        Raises: httpx.HTTPStatusError, httpx.RequestError on API failure.
        """
        active_addrs = await self._scan_active_addresses(key)
        balance_sat = sum(a.balance_sat for a in active_addrs)
        n_tx = sum(a.n_tx for a in active_addrs)
        return XpubSummary(
            balance_sat=balance_sat,
            balance_btc=Decimal(balance_sat) / SATOSHI,
            n_tx=n_tx,
            derived_addresses=[a for a in active_addrs if a.balance_sat > 0],
        )

    async def get_xpub_transactions_all(self, key: str) -> list[XpubTransaction]:
        """Fetch ALL confirmed transactions for the xpub.

        Derives active addresses, fetches tx history per address in parallel,
        deduplicates, computes net amount relative to the wallet address set.
        Returns list sorted oldest-first.
        """
        active_addrs = await self._scan_active_addresses(key)
        return await self._fetch_and_build_txs(active_addrs)

    async def get_xpub_transactions_since(
        self, key: str, after_timestamp: int
    ) -> list[XpubTransaction]:
        """Fetch confirmed transactions newer than after_timestamp.

        Used for incremental sync. Returns list sorted oldest-first.
        """
        active_addrs = await self._scan_active_addresses(key)
        all_txs = await self._fetch_and_build_txs(active_addrs, after_timestamp)
        return all_txs

    async def get_transactions_for_addresses(
        self, wallet_addrs: set[str]
    ) -> list[XpubTransaction]:
        """Fetch and build transactions for a pre-known set of wallet addresses.

        Skips the gap-limit scan. Used by history import after refresh has
        already discovered and stored the active address set in the DB.
        """
        stubs = [
            DerivedAddressData(address=addr, balance_sat=0, n_tx=1)
            for addr in wallet_addrs
        ]
        return await self._fetch_and_build_txs(stubs)

    async def _scan_active_addresses(self, key: str) -> list[DerivedAddressData]:
        """Discover all active derived addresses using the BIP44 gap limit.

        Scans both external (chain=0) and change (chain=1) chains.
        Stops when GAP_LIMIT consecutive unused addresses are encountered.
        Returns all addresses with n_tx > 0.
        """
        semaphore = asyncio.Semaphore(self._CONCURRENCY)
        active: list[DerivedAddressData] = []

        for chain in (0, 1):
            index = 0
            while True:
                # Derive a batch of GAP_LIMIT addresses
                batch_addrs = [
                    derive_address_at(key, chain, index + i)
                    for i in range(self.GAP_LIMIT)
                ]

                # Query all in parallel
                results = await asyncio.gather(
                    *[self._query_address(addr, semaphore) for addr in batch_addrs]
                )

                gap = 0
                for addr, info in zip(batch_addrs, results, strict=True):
                    tx_count = info["chain_stats"]["tx_count"]
                    if tx_count > 0:
                        funded = info["chain_stats"]["funded_txo_sum"]
                        spent = info["chain_stats"]["spent_txo_sum"]
                        active.append(
                            DerivedAddressData(
                                address=addr,
                                balance_sat=funded - spent,
                                n_tx=tx_count,
                            )
                        )
                        gap = 0
                    else:
                        gap += 1

                index += self.GAP_LIMIT

                # Stop if the entire batch was unused
                if gap >= self.GAP_LIMIT:
                    break

                await asyncio.sleep(0.1)

        return active

    async def _query_address(self, address: str, semaphore: asyncio.Semaphore) -> dict:
        """Query /address/{addr} with concurrency limiting."""
        async with semaphore:
            return await self._get_with_retry(f"/address/{address}")

    async def _fetch_and_build_txs(
        self,
        active_addrs: list[DerivedAddressData],
        after_timestamp: int | None = None,
    ) -> list[XpubTransaction]:
        """Fetch tx histories for active addresses, deduplicate, compute net amounts.

        Returns list sorted oldest-first.
        Only confirmed transactions are included.
        """
        if not active_addrs:
            return []

        wallet_addr_set = {a.address for a in active_addrs}

        # Fetch all raw tx dicts per address
        semaphore = asyncio.Semaphore(self._CONCURRENCY)

        async def fetch_for_addr(addr: str) -> list[dict]:
            async with semaphore:
                return await self._get_all_txs_for_address(addr, after_timestamp)

        pages = await asyncio.gather(*[fetch_for_addr(a.address) for a in active_addrs])

        # Deduplicate by txid
        seen: dict[str, dict] = {}
        for page in pages:
            for tx in page:
                txid = tx["txid"]
                if txid not in seen:
                    seen[txid] = tx

        # Build XpubTransaction list
        result: list[XpubTransaction] = []
        for tx in seen.values():
            status = tx.get("status", {})
            # Only confirmed txs
            if not status.get("confirmed", False):
                continue
            block_time: int | None = status.get("block_time")
            block_height: int | None = status.get("block_height")

            # Net amount relative to this wallet
            inflow = sum(
                vout["value"]
                for vout in tx.get("vout", [])
                if vout.get("scriptpubkey_address") in wallet_addr_set
            )
            outflow = sum(
                vin["prevout"]["value"]
                for vin in tx.get("vin", [])
                if vin.get("prevout")
                and vin["prevout"].get("scriptpubkey_address") in wallet_addr_set
            )
            net_sat = inflow - outflow

            result.append(
                XpubTransaction(
                    tx_hash=tx["txid"],
                    timestamp=block_time,
                    block_height=block_height,
                    amount_sat=net_sat,
                )
            )

        # Sort oldest-first by (timestamp, block_height)
        result.sort(
            key=lambda t: (
                t.timestamp if t.timestamp is not None else 0,
                t.block_height or 0,
            )
        )
        return result

    async def _get_all_txs_for_address(
        self,
        address: str,
        after_timestamp: int | None = None,
    ) -> list[dict]:
        """Paginate /address/{addr}/txs/chain (25 per page, newest-first).

        Only returns confirmed transactions.
        Stops when page is empty or < 25 items.
        Adds 0.1s sleep between pages to be polite.
        If after_timestamp is given, stops when block_time <= after_timestamp.
        """
        all_txs: list[dict] = []
        after_txid: str | None = None

        while True:
            path = f"/address/{address}/txs/chain"
            if after_txid:
                path += f"/{after_txid}"

            page: list = await self._get(path)

            if not page:
                break

            for tx in page:
                status = tx.get("status", {})
                if not status.get("confirmed", False):
                    continue
                block_time = status.get("block_time")
                if after_timestamp is not None and block_time is not None:
                    if block_time <= after_timestamp:
                        # Reached already-known transactions; stop this address
                        return all_txs
                all_txs.append(tx)

            if len(page) < 25:
                break

            after_txid = page[-1]["txid"]
            await asyncio.sleep(0.1)

        return all_txs
