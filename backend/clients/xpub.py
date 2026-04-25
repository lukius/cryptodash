"""XpubClient — Trezor Blockbook backend for HD wallet queries.

Blockbook (the indexer Trezor Suite uses) returns aggregate balance, per-derived-address
balances, and full transaction history for an entire xpub/ypub/zpub in a single HTTP
call. This collapses an HD wallet refresh from 40+ per-address requests against an
Esplora-style endpoint down to one call, eliminating the rate-limit pressure that
plagued the previous mempool.space implementation.

zpub (BIP84/P2WPKH), ypub (BIP49/P2SH-P2WPKH), and xpub (BIP44/P2PKH) are all
accepted natively — Blockbook reads the SLIP-132 version prefix and derives the
correct script type server-side. No local key derivation is required.

Endpoints used (https://btc2.trezor.io/api/v2):
  GET /api                                            — node + indexer status (tip height)
  GET /xpub/{key}?details=tokenBalances&tokens=used   — balance + per-address breakdown
  GET /xpub/{key}?details=txs&tokens=used&pageSize=…  — paginated tx history
"""

import asyncio
import logging
from dataclasses import dataclass
from decimal import Decimal

from backend.clients.base import BaseClient

logger = logging.getLogger(__name__)

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
    n_tx: int  # total transaction count across all derived addresses
    derived_addresses: list[DerivedAddressData]  # active addresses with balance > 0


@dataclass
class XpubTransaction:
    tx_hash: str
    timestamp: (
        int | None
    )  # Unix epoch seconds (block confirmation time); None for unconfirmed
    block_height: int | None
    amount_sat: int  # signed net satoshi amount (positive = received, negative = sent)


class XpubClient(BaseClient):
    PAGE_SIZE = 1000  # Blockbook's documented maximum
    _PAGE_DELAY_SECONDS = 0.1

    def __init__(self):
        super().__init__(base_url="https://btc2.trezor.io/api/v2", timeout=30.0)

    async def get_tip_height(self) -> int:
        """Return the current Bitcoin chain tip block height. One API call."""
        data = await self._get_with_retry("/api")
        return int(data["blockbook"]["bestHeight"])

    async def get_xpub_summary(self, key: str) -> XpubSummary:
        """Fetch aggregate balance and active derived address list. One API call.

        Returns: XpubSummary with aggregate balance and a list of DerivedAddressData
        for each address with a positive balance.
        Raises: httpx.HTTPStatusError, httpx.RequestError on API failure.
        """
        data = await self._get_with_retry(
            f"/xpub/{key}",
            params={"details": "tokenBalances", "tokens": "used"},
        )
        balance_sat = int(data.get("balance", "0"))
        n_tx = int(data.get("addrTxCount", data.get("txs", 0)) or 0)

        derived: list[DerivedAddressData] = []
        for token in data.get("tokens") or []:
            if token.get("type") != "XPUBAddress":
                continue
            addr_balance = int(token.get("balance", "0") or "0")
            if addr_balance <= 0:
                continue
            derived.append(
                DerivedAddressData(
                    address=token["name"],
                    balance_sat=addr_balance,
                    n_tx=int(token.get("transfers", 0) or 0),
                )
            )

        return XpubSummary(
            balance_sat=balance_sat,
            balance_btc=Decimal(balance_sat) / SATOSHI,
            n_tx=n_tx,
            derived_addresses=derived,
        )

    async def get_xpub_transactions_all(self, key: str) -> list[XpubTransaction]:
        """Fetch ALL confirmed transactions for the xpub.

        Paginates Blockbook's tx response, deduplicates internally, and computes
        signed net amounts relative to the wallet's address set.
        Returns the list sorted oldest-first.
        """
        return await self._fetch_xpub_transactions(key, after_timestamp=None)

    async def get_xpub_transactions_since(
        self, key: str, after_timestamp: int
    ) -> list[XpubTransaction]:
        """Fetch confirmed transactions newer than ``after_timestamp``.

        Used for incremental sync. Pagination stops as soon as a page surfaces a
        block_time at or below ``after_timestamp``. Returns oldest-first.
        """
        return await self._fetch_xpub_transactions(key, after_timestamp=after_timestamp)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_xpub_transactions(
        self, key: str, after_timestamp: int | None
    ) -> list[XpubTransaction]:
        """Paginate /xpub/{key}?details=txs and build XpubTransaction list."""
        wallet_addr_set: set[str] = set()
        seen_txids: set[str] = set()
        results: list[XpubTransaction] = []
        page = 1
        stopped_early = False

        while not stopped_early:
            data = await self._get_with_retry(
                f"/xpub/{key}",
                params={
                    "details": "txs",
                    "tokens": "used",
                    "pageSize": self.PAGE_SIZE,
                    "page": page,
                },
            )

            if not wallet_addr_set:
                # Capture the address set from the first page response. Subsequent
                # pages return the same set, so we only need to read it once.
                wallet_addr_set = _extract_wallet_addresses(data)

            transactions = data.get("transactions") or []
            for tx in transactions:
                # Skip unconfirmed (no block_time) — only confirmed txs are
                # used for balance reconstruction.
                block_time = tx.get("blockTime")
                if not tx.get("confirmations") or block_time is None:
                    continue
                if after_timestamp is not None and block_time <= after_timestamp:
                    # Pagination is newest-first; once we cross the cutoff we
                    # have all the new txs we need.
                    stopped_early = True
                    continue

                txid = tx["txid"]
                if txid in seen_txids:
                    continue
                seen_txids.add(txid)

                results.append(
                    XpubTransaction(
                        tx_hash=txid,
                        timestamp=int(block_time),
                        block_height=tx.get("blockHeight"),
                        amount_sat=_compute_net_amount(tx, wallet_addr_set),
                    )
                )

            total_pages = int(data.get("totalPages", 0) or 0)
            if page >= total_pages or not transactions:
                break
            page += 1
            await asyncio.sleep(self._PAGE_DELAY_SECONDS)

        results.sort(
            key=lambda t: (
                t.timestamp if t.timestamp is not None else 0,
                t.block_height or 0,
            )
        )
        return results


def _extract_wallet_addresses(data: dict) -> set[str]:
    """Pull the set of derived (used) addresses from a Blockbook xpub response."""
    addrs: set[str] = set()
    for token in data.get("tokens") or []:
        if token.get("type") == "XPUBAddress" and token.get("name"):
            addrs.add(token["name"])
    return addrs


def _compute_net_amount(tx: dict, wallet_addr_set: set[str]) -> int:
    """Compute the signed net satoshi amount for a Blockbook tx vs. a wallet's
    address set.

    Positive => received, negative => sent. Uses ``addresses`` lists on each
    vin/vout (Blockbook supports multi-address scripts; an entry counts toward the
    wallet only if any of its addresses is in the set).
    """
    inflow = sum(
        int(vout.get("value", "0") or "0")
        for vout in tx.get("vout") or []
        if _entry_belongs_to_wallet(vout, wallet_addr_set)
    )
    outflow = sum(
        int(vin.get("value", "0") or "0")
        for vin in tx.get("vin") or []
        if _entry_belongs_to_wallet(vin, wallet_addr_set)
    )
    return inflow - outflow


def _entry_belongs_to_wallet(entry: dict, wallet_addr_set: set[str]) -> bool:
    """True if any of the entry's addresses is one of the wallet's derived addresses."""
    if not entry.get("isAddress", True):
        return False
    for addr in entry.get("addresses") or []:
        if addr in wallet_addr_set:
            return True
    return False
