"""Tests for XpubClient — mempool.space per-address backend for HD wallet queries."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

import hashlib as _hashlib

from backend.clients.xpub import (
    SATOSHI,
    DerivedAddressData,
    XpubClient,
    XpubSummary,
    XpubTransaction,
)

BASE_URL = "https://mempool.space/api"

# A valid account-level xpub key (BIP32 TV1 m/0H).
XPUB = "xpub68Gmy5EdvgibQVfPdqkBBCHxA5htiqg55crXYuXoQRKfDBFA1WEjWgP6LHhwBZeNK1VTsfTFUHCdrfp1bgwQ9xv5ski8PX9rL2dZXvgGDnw"

# Same key material with zpub/ypub version bytes


def _reversion(key, new_version_hex):
    _BASE58_CHARS = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    _BASE58_MAP = {c: i for i, c in enumerate(_BASE58_CHARS)}

    def decode(s):
        num = 0
        for ch in s:
            num = num * 58 + _BASE58_MAP[ch]
        leading = len(s) - len(s.lstrip("1"))
        byte_len = (num.bit_length() + 7) // 8 if num > 0 else 1
        return b"\x00" * leading + num.to_bytes(byte_len, "big")

    def encode(data):
        num = int.from_bytes(data, "big")
        result = []
        while num > 0:
            num, rem = divmod(num, 58)
            result.append(_BASE58_CHARS[rem])
        leading = len(data) - len(data.lstrip(b"\x00"))
        return "1" * leading + "".join(reversed(result))

    decoded = decode(key)
    payload = decoded[:-4]
    new_payload = bytes.fromhex(new_version_hex) + payload[4:]
    checksum = _hashlib.sha256(_hashlib.sha256(new_payload).digest()).digest()[:4]
    return encode(new_payload + checksum)


ZPUB = _reversion(XPUB, "04B24746")
YPUB = _reversion(XPUB, "049D7CB2")


def _addr_response(
    tx_count: int = 0,
    funded_sum: int = 0,
    spent_sum: int = 0,
) -> dict:
    """Build a minimal /address/{addr} API response."""
    return {
        "address": "placeholder",
        "chain_stats": {
            "funded_txo_sum": funded_sum,
            "spent_txo_sum": spent_sum,
            "tx_count": tx_count,
        },
        "mempool_stats": {
            "funded_txo_sum": 0,
            "spent_txo_sum": 0,
            "tx_count": 0,
        },
    }


def _tx_response(
    txid: str,
    block_time: int,
    block_height: int,
    vout_addr: str,
    vout_value: int,
    vin_addr: str = "",
    vin_value: int = 0,
    confirmed: bool = True,
) -> dict:
    """Build a minimal full tx object as returned by /address/{addr}/txs/chain."""
    tx: dict = {
        "txid": txid,
        "status": {
            "confirmed": confirmed,
            "block_height": block_height if confirmed else None,
            "block_time": block_time if confirmed else None,
        },
        "vout": [],
        "vin": [],
    }
    if vout_addr:
        tx["vout"].append({"value": vout_value, "scriptpubkey_address": vout_addr})
    if vin_addr:
        tx["vin"].append(
            {
                "prevout": {
                    "value": vin_value,
                    "scriptpubkey_address": vin_addr,
                }
            }
        )
    return tx


@pytest.fixture
def client():
    return XpubClient()


# ---------------------------------------------------------------------------
# SATOSHI constant is importable (used by refresh.py)
# ---------------------------------------------------------------------------


def test_satoshi_constant():
    assert SATOSHI == Decimal("100000000")


# ---------------------------------------------------------------------------
# XpubSummary / DerivedAddressData / XpubTransaction dataclasses
# ---------------------------------------------------------------------------


def test_xpub_summary_fields():
    derived = [DerivedAddressData(address="bc1qfoo", balance_sat=1000, n_tx=1)]
    summary = XpubSummary(
        balance_sat=1000,
        balance_btc=Decimal("0.00001"),
        n_tx=1,
        derived_addresses=derived,
    )
    assert summary.balance_sat == 1000
    assert summary.n_tx == 1
    assert summary.derived_addresses == derived


def test_xpub_transaction_fields():
    tx = XpubTransaction(tx_hash="abc", timestamp=1700000000, block_height=820000, amount_sat=50000)
    assert tx.tx_hash == "abc"
    assert tx.timestamp == 1700000000
    assert tx.amount_sat == 50000


# ---------------------------------------------------------------------------
# get_xpub_summary — uses _scan_active_addresses
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_xpub_summary_empty_wallet(client):
    """No active addresses → balance=0, n_tx=0, derived_addresses=[]."""
    # With GAP_LIMIT=20 addresses per chain side and all returning n_tx=0,
    # the scanner stops after one batch per chain.
    respx.get(url__regex=r"https://mempool\.space/api/address/").mock(
        return_value=httpx.Response(200, json=_addr_response(tx_count=0))
    )
    with patch("backend.clients.xpub.asyncio.sleep", new_callable=AsyncMock):
        summary = await client.get_xpub_summary(XPUB)

    assert isinstance(summary, XpubSummary)
    assert summary.balance_sat == 0
    assert summary.balance_btc == Decimal("0")
    assert summary.n_tx == 0
    assert summary.derived_addresses == []


@respx.mock
async def test_get_xpub_summary_with_active_addresses(client):
    """Active addresses (n_tx > 0) appear in derived_addresses; balance is summed."""
    call_count = 0

    def addr_side_effect(request):
        nonlocal call_count
        call_count += 1
        # First two addresses of chain=0 are active; rest unused
        if call_count <= 2:
            return httpx.Response(
                200, json=_addr_response(tx_count=1, funded_sum=50_000_000, spent_sum=0)
            )
        return httpx.Response(200, json=_addr_response(tx_count=0))

    respx.get(url__regex=r"https://mempool\.space/api/address/").mock(
        side_effect=addr_side_effect
    )
    with patch("backend.clients.xpub.asyncio.sleep", new_callable=AsyncMock):
        summary = await client.get_xpub_summary(XPUB)

    # 2 active addresses, each with 50_000_000 sat
    assert summary.balance_sat == 100_000_000
    assert summary.balance_btc == Decimal("1")
    assert summary.n_tx == 2
    assert len(summary.derived_addresses) == 2
    assert all(isinstance(a, DerivedAddressData) for a in summary.derived_addresses)
    assert all(a.balance_sat == 50_000_000 for a in summary.derived_addresses)


@respx.mock
async def test_get_xpub_summary_returns_xpub_summary_type(client):
    respx.get(url__regex=r"https://mempool\.space/api/address/").mock(
        return_value=httpx.Response(200, json=_addr_response())
    )
    with patch("backend.clients.xpub.asyncio.sleep", new_callable=AsyncMock):
        result = await client.get_xpub_summary(XPUB)
    assert isinstance(result, XpubSummary)


# ---------------------------------------------------------------------------
# _scan_active_addresses — gap limit behavior
# ---------------------------------------------------------------------------


@respx.mock
async def test_scan_stops_after_gap_limit(client):
    """After GAP_LIMIT consecutive unused addresses, scanning stops."""
    # Only the very first address is active; all others have n_tx=0
    first_call = True

    def side_effect(request):
        nonlocal first_call
        if first_call:
            first_call = False
            return httpx.Response(
                200, json=_addr_response(tx_count=1, funded_sum=10_000, spent_sum=0)
            )
        return httpx.Response(200, json=_addr_response(tx_count=0))

    respx.get(url__regex=r"https://mempool\.space/api/address/").mock(
        side_effect=side_effect
    )
    with patch("backend.clients.xpub.asyncio.sleep", new_callable=AsyncMock):
        active = await client._scan_active_addresses(XPUB)

    # Only 1 active address from chain=0; chain=1 scans GAP_LIMIT and finds nothing
    assert len(active) == 1
    assert active[0].n_tx == 1


@respx.mock
async def test_scan_scans_both_chains(client):
    """Both receive (chain=0) and change (chain=1) addresses are scanned."""
    # Count unique addresses scanned across both chains
    scanned_urls: list[str] = []

    def side_effect(request):
        url = str(request.url)
        scanned_urls.append(url)
        return httpx.Response(200, json=_addr_response(tx_count=0))

    respx.get(url__regex=r"https://mempool\.space/api/address/").mock(
        side_effect=side_effect
    )
    with patch("backend.clients.xpub.asyncio.sleep", new_callable=AsyncMock):
        await client._scan_active_addresses(XPUB)

    # Should query 2 * GAP_LIMIT addresses (one batch each for chain 0 and 1)
    assert len(scanned_urls) == 2 * client.GAP_LIMIT


# ---------------------------------------------------------------------------
# get_xpub_transactions_all — deduplication and net amount
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_xpub_transactions_all_empty(client):
    """No active addresses → empty transaction list."""
    respx.get(url__regex=r"https://mempool\.space/api/address/").mock(
        return_value=httpx.Response(200, json=_addr_response(tx_count=0))
    )
    with patch("backend.clients.xpub.asyncio.sleep", new_callable=AsyncMock):
        txs = await client.get_xpub_transactions_all(XPUB)
    assert txs == []


@respx.mock
async def test_get_xpub_transactions_all_deduplication(client):
    """A tx appearing in multiple addresses' histories is deduplicated."""
    # Derive the two addresses we'll use
    from backend.clients.hd_derive import derive_address_at

    addr0 = derive_address_at(XPUB, 0, 0)
    addr1 = derive_address_at(XPUB, 0, 1)

    shared_txid = "shared_tx_abc123"
    shared_tx = _tx_response(
        txid=shared_txid,
        block_time=1700000000,
        block_height=820000,
        vout_addr=addr0,
        vout_value=50_000_000,
    )
    # Add addr1 as second vout in shared tx
    shared_tx["vout"].append({"value": 30_000_000, "scriptpubkey_address": addr1})

    addr_call_count = 0
    txs_call_count = 0

    def addr_side_effect(request):
        nonlocal addr_call_count
        addr_call_count += 1
        url = str(request.url)
        if addr0 in url:
            return httpx.Response(
                200,
                json=_addr_response(tx_count=1, funded_sum=50_000_000, spent_sum=0),
            )
        elif addr1 in url:
            return httpx.Response(
                200,
                json=_addr_response(tx_count=1, funded_sum=30_000_000, spent_sum=0),
            )
        return httpx.Response(200, json=_addr_response(tx_count=0))

    def txs_side_effect(request):
        nonlocal txs_call_count
        txs_call_count += 1
        url = str(request.url)
        if addr0 in url or addr1 in url:
            return httpx.Response(200, json=[shared_tx])
        return httpx.Response(200, json=[])

    respx.get(url__regex=r"https://mempool\.space/api/address/[^/]+/txs").mock(
        side_effect=txs_side_effect
    )
    respx.get(url__regex=r"https://mempool\.space/api/address/[^/]+$").mock(
        side_effect=addr_side_effect
    )

    with patch("backend.clients.xpub.asyncio.sleep", new_callable=AsyncMock):
        txs = await client.get_xpub_transactions_all(XPUB)

    # The shared tx must appear exactly once
    assert len(txs) == 1
    assert txs[0].tx_hash == shared_txid
    # Net amount = 50M + 30M = 80M sat (both vouts go to wallet addresses)
    assert txs[0].amount_sat == 80_000_000


@respx.mock
async def test_get_xpub_transactions_all_sorted_oldest_first(client):
    """Returned transactions are sorted oldest-first."""
    from backend.clients.hd_derive import derive_address_at

    addr0 = derive_address_at(XPUB, 0, 0)

    tx1 = _tx_response(
        txid="tx1", block_time=1700001000, block_height=820001,
        vout_addr=addr0, vout_value=10_000_000,
    )
    tx2 = _tx_response(
        txid="tx2", block_time=1700000000, block_height=820000,
        vout_addr=addr0, vout_value=20_000_000,
    )

    def addr_side_effect(request):
        url = str(request.url)
        if addr0 in url:
            return httpx.Response(
                200,
                json=_addr_response(tx_count=2, funded_sum=30_000_000, spent_sum=0),
            )
        return httpx.Response(200, json=_addr_response(tx_count=0))

    def txs_side_effect(request):
        url = str(request.url)
        if addr0 in url:
            # API returns newest-first (tx1, then tx2)
            return httpx.Response(200, json=[tx1, tx2])
        return httpx.Response(200, json=[])

    respx.get(url__regex=r"https://mempool\.space/api/address/[^/]+/txs").mock(
        side_effect=txs_side_effect
    )
    respx.get(url__regex=r"https://mempool\.space/api/address/[^/]+$").mock(
        side_effect=addr_side_effect
    )

    with patch("backend.clients.xpub.asyncio.sleep", new_callable=AsyncMock):
        txs = await client.get_xpub_transactions_all(XPUB)

    assert len(txs) == 2
    # Sorted oldest-first
    assert txs[0].timestamp <= txs[1].timestamp
    assert txs[0].tx_hash == "tx2"  # older
    assert txs[1].tx_hash == "tx1"  # newer


@respx.mock
async def test_get_xpub_transactions_all_skips_unconfirmed(client):
    """Unconfirmed transactions (confirmed=False) are excluded."""
    from backend.clients.hd_derive import derive_address_at

    addr0 = derive_address_at(XPUB, 0, 0)

    confirmed_tx = _tx_response(
        txid="confirmed", block_time=1700000000, block_height=820000,
        vout_addr=addr0, vout_value=10_000_000, confirmed=True,
    )
    unconfirmed_tx = _tx_response(
        txid="unconfirmed", block_time=0, block_height=0,
        vout_addr=addr0, vout_value=5_000_000, confirmed=False,
    )

    def addr_side_effect(request):
        url = str(request.url)
        if addr0 in url:
            return httpx.Response(
                200,
                json=_addr_response(tx_count=2, funded_sum=15_000_000, spent_sum=0),
            )
        return httpx.Response(200, json=_addr_response(tx_count=0))

    def txs_side_effect(request):
        url = str(request.url)
        if addr0 in url:
            return httpx.Response(200, json=[confirmed_tx, unconfirmed_tx])
        return httpx.Response(200, json=[])

    respx.get(url__regex=r"https://mempool\.space/api/address/[^/]+/txs").mock(
        side_effect=txs_side_effect
    )
    respx.get(url__regex=r"https://mempool\.space/api/address/[^/]+$").mock(
        side_effect=addr_side_effect
    )

    with patch("backend.clients.xpub.asyncio.sleep", new_callable=AsyncMock):
        txs = await client.get_xpub_transactions_all(XPUB)

    # Only the confirmed tx returned
    assert len(txs) == 1
    assert txs[0].tx_hash == "confirmed"
    assert txs[0].timestamp == 1700000000


# ---------------------------------------------------------------------------
# get_xpub_transactions_since
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_xpub_transactions_since_filters_by_timestamp(client):
    """Only transactions with timestamp > after_timestamp are returned."""
    from backend.clients.hd_derive import derive_address_at

    addr0 = derive_address_at(XPUB, 0, 0)
    after_ts = 1700000000

    old_tx = _tx_response(
        txid="old", block_time=1700000000, block_height=820000,
        vout_addr=addr0, vout_value=10_000_000,
    )
    new_tx = _tx_response(
        txid="new", block_time=1700001000, block_height=820001,
        vout_addr=addr0, vout_value=5_000_000,
    )

    def addr_side_effect(request):
        url = str(request.url)
        if addr0 in url:
            return httpx.Response(
                200,
                json=_addr_response(tx_count=2, funded_sum=15_000_000, spent_sum=0),
            )
        return httpx.Response(200, json=_addr_response(tx_count=0))

    def txs_side_effect(request):
        url = str(request.url)
        if addr0 in url:
            # API returns newest first
            return httpx.Response(200, json=[new_tx, old_tx])
        return httpx.Response(200, json=[])

    respx.get(url__regex=r"https://mempool\.space/api/address/[^/]+/txs").mock(
        side_effect=txs_side_effect
    )
    respx.get(url__regex=r"https://mempool\.space/api/address/[^/]+$").mock(
        side_effect=addr_side_effect
    )

    with patch("backend.clients.xpub.asyncio.sleep", new_callable=AsyncMock):
        txs = await client.get_xpub_transactions_since(XPUB, after_ts)

    # Only the new tx (timestamp > after_ts)
    assert len(txs) == 1
    assert txs[0].tx_hash == "new"
    assert txs[0].timestamp == 1700001000


@respx.mock
async def test_get_xpub_transactions_since_sorted_oldest_first(client):
    """Results from get_xpub_transactions_since are sorted oldest-first."""
    from backend.clients.hd_derive import derive_address_at

    addr0 = derive_address_at(XPUB, 0, 0)
    after_ts = 1699000000

    tx_a = _tx_response(
        txid="newer", block_time=1700002000, block_height=820002,
        vout_addr=addr0, vout_value=5_000_000,
    )
    tx_b = _tx_response(
        txid="older", block_time=1700001000, block_height=820001,
        vout_addr=addr0, vout_value=10_000_000,
    )

    def addr_side_effect(request):
        url = str(request.url)
        if addr0 in url:
            return httpx.Response(
                200,
                json=_addr_response(tx_count=2, funded_sum=15_000_000, spent_sum=0),
            )
        return httpx.Response(200, json=_addr_response(tx_count=0))

    def txs_side_effect(request):
        url = str(request.url)
        if addr0 in url:
            return httpx.Response(200, json=[tx_a, tx_b])
        return httpx.Response(200, json=[])

    respx.get(url__regex=r"https://mempool\.space/api/address/[^/]+/txs").mock(
        side_effect=txs_side_effect
    )
    respx.get(url__regex=r"https://mempool\.space/api/address/[^/]+$").mock(
        side_effect=addr_side_effect
    )

    with patch("backend.clients.xpub.asyncio.sleep", new_callable=AsyncMock):
        txs = await client.get_xpub_transactions_since(XPUB, after_ts)

    assert len(txs) == 2
    assert txs[0].timestamp <= txs[1].timestamp
    assert txs[0].tx_hash == "older"
    assert txs[1].tx_hash == "newer"


# ---------------------------------------------------------------------------
# Net amount computation
# ---------------------------------------------------------------------------


@respx.mock
async def test_net_amount_incoming(client):
    """tx with vout to wallet address → positive net amount."""
    from backend.clients.hd_derive import derive_address_at

    addr0 = derive_address_at(XPUB, 0, 0)

    tx = _tx_response(
        txid="incoming", block_time=1700000000, block_height=820000,
        vout_addr=addr0, vout_value=100_000_000,
    )

    def addr_side_effect(request):
        url = str(request.url)
        if addr0 in url:
            return httpx.Response(
                200,
                json=_addr_response(tx_count=1, funded_sum=100_000_000, spent_sum=0),
            )
        return httpx.Response(200, json=_addr_response(tx_count=0))

    def txs_side_effect(request):
        url = str(request.url)
        if addr0 in url:
            return httpx.Response(200, json=[tx])
        return httpx.Response(200, json=[])

    respx.get(url__regex=r"https://mempool\.space/api/address/[^/]+/txs").mock(
        side_effect=txs_side_effect
    )
    respx.get(url__regex=r"https://mempool\.space/api/address/[^/]+$").mock(
        side_effect=addr_side_effect
    )

    with patch("backend.clients.xpub.asyncio.sleep", new_callable=AsyncMock):
        txs = await client.get_xpub_transactions_all(XPUB)

    assert len(txs) == 1
    assert txs[0].amount_sat == 100_000_000


@respx.mock
async def test_net_amount_outgoing(client):
    """tx with vin from wallet address → negative net amount."""
    from backend.clients.hd_derive import derive_address_at

    addr0 = derive_address_at(XPUB, 0, 0)

    tx = {
        "txid": "outgoing",
        "status": {"confirmed": True, "block_height": 820000, "block_time": 1700000000},
        "vout": [{"value": 50_000_000, "scriptpubkey_address": "external_addr"}],
        "vin": [
            {
                "prevout": {
                    "value": 100_000_000,
                    "scriptpubkey_address": addr0,
                }
            }
        ],
    }

    def addr_side_effect(request):
        url = str(request.url)
        if addr0 in url:
            return httpx.Response(
                200,
                json=_addr_response(tx_count=1, funded_sum=100_000_000, spent_sum=100_000_000),
            )
        return httpx.Response(200, json=_addr_response(tx_count=0))

    def txs_side_effect(request):
        url = str(request.url)
        if addr0 in url:
            return httpx.Response(200, json=[tx])
        return httpx.Response(200, json=[])

    respx.get(url__regex=r"https://mempool\.space/api/address/[^/]+/txs").mock(
        side_effect=txs_side_effect
    )
    respx.get(url__regex=r"https://mempool\.space/api/address/[^/]+$").mock(
        side_effect=addr_side_effect
    )

    with patch("backend.clients.xpub.asyncio.sleep", new_callable=AsyncMock):
        txs = await client.get_xpub_transactions_all(XPUB)

    assert len(txs) == 1
    assert txs[0].amount_sat == -100_000_000


# ---------------------------------------------------------------------------
# _get_all_txs_for_address — pagination (25 per page)
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_all_txs_for_address_paginates(client):
    """Fetches multiple pages when first page has 25 items."""
    from backend.clients.hd_derive import derive_address_at

    addr = derive_address_at(XPUB, 0, 0)
    call_count = 0
    last_txid_seen = None

    def make_page(n, start_time):
        return [
            {
                "txid": f"tx_{start_time + i}",
                "status": {
                    "confirmed": True,
                    "block_height": 820000 + start_time + i,
                    "block_time": start_time + i,
                },
                "vout": [{"value": 1000, "scriptpubkey_address": addr}],
                "vin": [],
            }
            for i in range(n)
        ]

    def txs_side_effect(request):
        nonlocal call_count, last_txid_seen
        call_count += 1
        url = str(request.url)
        if "/txs/chain/" in url:
            # Second page: 10 items (partial page)
            return httpx.Response(200, json=make_page(10, 100))
        else:
            # First page: 25 items (full page — triggers next page fetch)
            return httpx.Response(200, json=make_page(25, 0))

    respx.get(url__regex=r"https://mempool\.space/api/address/[^/]+/txs").mock(
        side_effect=txs_side_effect
    )

    with patch("backend.clients.xpub.asyncio.sleep", new_callable=AsyncMock):
        result = await client._get_all_txs_for_address(addr)

    # Two pages fetched: 25 + 10 = 35 confirmed txs
    assert len(result) == 35
    assert call_count == 2


@respx.mock
async def test_get_all_txs_for_address_stops_on_empty_page(client):
    """Stops pagination when page is empty."""
    from backend.clients.hd_derive import derive_address_at

    addr = derive_address_at(XPUB, 0, 0)
    call_count = 0

    def txs_side_effect(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(200, json=[
                {
                    "txid": f"tx_{i}",
                    "status": {"confirmed": True, "block_height": 820000 + i, "block_time": 1700000000 + i},
                    "vout": [{"value": 1000, "scriptpubkey_address": addr}],
                    "vin": [],
                }
                for i in range(25)
            ])
        return httpx.Response(200, json=[])

    respx.get(url__regex=r"https://mempool\.space/api/address/[^/]+/txs").mock(
        side_effect=txs_side_effect
    )

    with patch("backend.clients.xpub.asyncio.sleep", new_callable=AsyncMock):
        result = await client._get_all_txs_for_address(addr)

    assert len(result) == 25
    assert call_count == 2


# ---------------------------------------------------------------------------
# zpub key type — address format
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_xpub_summary_zpub_derives_bech32_addresses(client):
    """get_xpub_summary with a zpub key correctly scans bc1q... addresses."""
    scanned_addresses: list[str] = []

    def addr_side_effect(request):
        url = str(request.url)
        # Extract the address portion from the URL
        addr = url.split("/address/")[1].split("/")[0]
        scanned_addresses.append(addr)
        return httpx.Response(200, json=_addr_response(tx_count=0))

    respx.get(url__regex=r"https://mempool\.space/api/address/").mock(
        side_effect=addr_side_effect
    )

    with patch("backend.clients.xpub.asyncio.sleep", new_callable=AsyncMock):
        await client.get_xpub_summary(ZPUB)

    # All scanned addresses must be bech32 (bc1q...) for zpub
    for addr in scanned_addresses:
        assert addr.startswith("bc1q"), (
            f"zpub should derive bc1q addresses, got: {addr!r}"
        )


# ---------------------------------------------------------------------------
# HTTP 5xx — raises
# ---------------------------------------------------------------------------


@respx.mock
async def test_xpub_client_server_error_on_address_scan(client):
    """500 from mempool.space /address endpoint → raises HTTPStatusError."""
    respx.get(url__regex=r"https://mempool\.space/api/address/").mock(
        return_value=httpx.Response(500)
    )

    with patch("backend.clients.xpub.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_xpub_summary(XPUB)


# ---------------------------------------------------------------------------
# get_transactions_for_addresses — skip gap-limit scan
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_transactions_for_addresses_skips_scan(client):
    """get_transactions_for_addresses uses the supplied address set, not gap scan."""
    from backend.clients.hd_derive import derive_address_at

    addr0 = derive_address_at(XPUB, 0, 0)
    scan_called = False

    tx = _tx_response(
        txid="tx_foo",
        block_time=1700000000,
        block_height=820000,
        vout_addr=addr0,
        vout_value=10_000_000,
    )

    original_scan = client._scan_active_addresses

    async def spy_scan(*a, **kw):
        nonlocal scan_called
        scan_called = True
        return await original_scan(*a, **kw)

    client._scan_active_addresses = spy_scan

    def txs_side_effect(request):
        url = str(request.url)
        if addr0 in url:
            return httpx.Response(200, json=[tx])
        return httpx.Response(200, json=[])

    respx.get(url__regex=r"https://mempool\.space/api/address/[^/]+/txs").mock(
        side_effect=txs_side_effect
    )

    with patch("backend.clients.xpub.asyncio.sleep", new_callable=AsyncMock):
        txs = await client.get_transactions_for_addresses({addr0})

    assert not scan_called, "_scan_active_addresses should NOT be called"
    assert len(txs) == 1
    assert txs[0].tx_hash == "tx_foo"
    assert txs[0].amount_sat == 10_000_000


@respx.mock
async def test_get_transactions_for_addresses_uses_full_addr_set_for_net(client):
    """Net amount is computed across all supplied addresses (change + receive)."""
    from backend.clients.hd_derive import derive_address_at

    receive_addr = derive_address_at(XPUB, 0, 0)
    change_addr = derive_address_at(XPUB, 1, 0)

    # A send tx: 100k sat from receive_addr, 60k change to change_addr, rest to external
    spend_tx = {
        "txid": "spend_tx",
        "status": {"confirmed": True, "block_height": 820000, "block_time": 1700000000},
        "vout": [
            {"value": 60_000, "scriptpubkey_address": change_addr},
            {"value": 30_000, "scriptpubkey_address": "external"},
        ],
        "vin": [
            {"prevout": {"value": 100_000, "scriptpubkey_address": receive_addr}}
        ],
    }

    def txs_side_effect(request):
        url = str(request.url)
        if receive_addr in url or change_addr in url:
            return httpx.Response(200, json=[spend_tx])
        return httpx.Response(200, json=[])

    respx.get(url__regex=r"https://mempool\.space/api/address/[^/]+/txs").mock(
        side_effect=txs_side_effect
    )

    with patch("backend.clients.xpub.asyncio.sleep", new_callable=AsyncMock):
        txs = await client.get_transactions_for_addresses({receive_addr, change_addr})

    # Deduplicated to 1 tx; net = +60k (change received) - 100k (sent) = -40k
    assert len(txs) == 1
    assert txs[0].amount_sat == -40_000


# ---------------------------------------------------------------------------
# Zero-balance address filtering in get_xpub_summary.derived_addresses
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_xpub_summary_excludes_zero_balance_from_derived(client):
    """derived_addresses only contains addresses with balance_sat > 0."""
    from backend.clients.hd_derive import derive_address_at

    addr0 = derive_address_at(XPUB, 0, 0)  # has balance
    addr1 = derive_address_at(XPUB, 0, 1)  # fully spent, balance = 0

    call_count = 0

    def addr_side_effect(request):
        nonlocal call_count
        call_count += 1
        url = str(request.url)
        if addr0 in url:
            # Active with positive balance
            return httpx.Response(
                200,
                json=_addr_response(tx_count=1, funded_sum=50_000_000, spent_sum=0),
            )
        if addr1 in url:
            # Active but fully spent
            return httpx.Response(
                200,
                json=_addr_response(tx_count=2, funded_sum=30_000_000, spent_sum=30_000_000),
            )
        return httpx.Response(200, json=_addr_response(tx_count=0))

    respx.get(url__regex=r"https://mempool\.space/api/address/").mock(
        side_effect=addr_side_effect
    )

    with patch("backend.clients.xpub.asyncio.sleep", new_callable=AsyncMock):
        summary = await client.get_xpub_summary(XPUB)

    # Total balance: only addr0 contributes
    assert summary.balance_sat == 50_000_000
    # derived_addresses: only addr0 (balance > 0); addr1 excluded despite n_tx=2
    assert len(summary.derived_addresses) == 1
    assert summary.derived_addresses[0].address == addr0
    assert summary.derived_addresses[0].balance_sat == 50_000_000
