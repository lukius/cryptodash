"""Tests for XpubClient (blockchain.info multiaddr endpoint)."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from backend.clients.xpub import (
    XpubClient,
    XpubSummary,
    XpubTransaction,
    DerivedAddressData,
)

BASE_URL = "https://blockchain.info"
MULTIADDR_PATH = f"{BASE_URL}/multiaddr"
XPUB = "xpub6CUGRUonZSQ4TWtTMmzXdrXDtypWKiKrhko4egpiMZbpiaQL2jkwSB1icqYh2cfDfVxdx4df189oijk3e1xt3t4"


def _multiaddr_response(
    balance_sat: int = 100_000_000,
    n_tx: int = 2,
    addresses: list | None = None,
    txs: list | None = None,
) -> dict:
    """Build a minimal multiaddr response."""
    if addresses is None:
        addresses = [
            {
                "address": "bc1qaddr1",
                "final_balance": 60_000_000,
                "n_tx": 1,
                "total_received": 60_000_000,
                "total_sent": 0,
            },
            {
                "address": "bc1qaddr2",
                "final_balance": 40_000_000,
                "n_tx": 1,
                "total_received": 40_000_000,
                "total_sent": 0,
            },
        ]
    if txs is None:
        txs = [
            {
                "hash": "txhash2",
                "time": 1700001000,
                "block_height": 820001,
                "result": -50_000,
            },
            {
                "hash": "txhash1",
                "time": 1700000000,
                "block_height": 820000,
                "result": 100_000_000,
            },
        ]
    return {
        "wallet": {"final_balance": balance_sat, "n_tx": n_tx},
        "addresses": addresses,
        "txs": txs,
        "info": {"n_tx": n_tx, "n_unredeemed": 1},
    }


@pytest.fixture
def client():
    return XpubClient()


# ---------------------------------------------------------------------------
# get_xpub_summary
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_xpub_summary_parses_response(client):
    """Mock multiaddr response → correct XpubSummary."""
    respx.get(MULTIADDR_PATH).mock(
        return_value=httpx.Response(200, json=_multiaddr_response())
    )

    summary = await client.get_xpub_summary(XPUB)

    assert isinstance(summary, XpubSummary)
    assert summary.balance_sat == 100_000_000
    assert summary.balance_btc == Decimal("1.0")
    assert summary.n_tx == 2
    assert len(summary.derived_addresses) == 2

    addr1 = summary.derived_addresses[0]
    assert isinstance(addr1, DerivedAddressData)
    assert addr1.address == "bc1qaddr1"
    assert addr1.balance_sat == 60_000_000
    assert addr1.n_tx == 1

    addr2 = summary.derived_addresses[1]
    assert addr2.address == "bc1qaddr2"
    assert addr2.balance_sat == 40_000_000


@respx.mock
async def test_get_xpub_summary_empty_addresses(client):
    """addresses: [] → derived_addresses = [], balance_sat = 0."""
    respx.get(MULTIADDR_PATH).mock(
        return_value=httpx.Response(
            200,
            json=_multiaddr_response(balance_sat=0, n_tx=0, addresses=[], txs=[]),
        )
    )

    summary = await client.get_xpub_summary(XPUB)

    assert summary.derived_addresses == []
    assert summary.balance_sat == 0
    assert summary.balance_btc == Decimal("0")
    assert summary.n_tx == 0


@respx.mock
async def test_get_xpub_summary_uses_n1_param(client):
    """get_xpub_summary passes n=1 to minimise the txs array."""
    captured_params = {}

    def capture(request):
        captured_params.update(dict(request.url.params))
        return httpx.Response(200, json=_multiaddr_response())

    respx.get(MULTIADDR_PATH).mock(side_effect=capture)

    await client.get_xpub_summary(XPUB)

    assert captured_params.get("n") == "1"
    assert captured_params.get("offset") == "0"
    assert captured_params.get("active") == XPUB


# ---------------------------------------------------------------------------
# get_xpub_transactions_all
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_xpub_transactions_all_single_page(client):
    """n_tx ≤ 50 → single request, result sorted oldest-first."""
    respx.get(MULTIADDR_PATH).mock(
        return_value=httpx.Response(200, json=_multiaddr_response(n_tx=2))
    )

    txs = await client.get_xpub_transactions_all(XPUB)

    assert len(txs) == 2
    assert isinstance(txs[0], XpubTransaction)
    # Should be sorted oldest-first
    assert txs[0].timestamp <= txs[1].timestamp
    assert txs[0].tx_hash == "txhash1"
    assert txs[1].tx_hash == "txhash2"
    assert txs[0].amount_sat == 100_000_000
    assert txs[1].amount_sat == -50_000


@respx.mock
async def test_get_xpub_transactions_all_multi_page(client):
    """n_tx = 125 → 3 requests (offsets 0, 50, 100)."""
    call_params = []

    def make_page(offset: int, count: int):
        """Generate `count` dummy transactions starting at a given offset."""
        return [
            {
                "hash": f"tx_{offset + i}",
                "time": 1700000000 + offset + i,
                "block_height": 820000 + offset + i,
                "result": 1000,
            }
            for i in range(count)
        ]

    def side_effect(request):
        params = dict(request.url.params)
        call_params.append(params)
        offset = int(params.get("offset", 0))
        n = int(params.get("n", 50))
        if offset == 0:
            count = n  # full page
        elif offset == 50:
            count = n  # full page
        else:
            count = 25  # last page (offset=100, only 25 remain)
        return httpx.Response(
            200,
            json={
                "wallet": {"final_balance": 125_000, "n_tx": 125},
                "addresses": [],
                "txs": make_page(offset, count),
                "info": {"n_tx": 125, "n_unredeemed": 0},
            },
        )

    respx.get(MULTIADDR_PATH).mock(side_effect=side_effect)

    with patch(
        "backend.clients.xpub.asyncio.sleep", new_callable=AsyncMock
    ) as mock_sleep:
        txs = await client.get_xpub_transactions_all(XPUB)

    assert len(txs) == 125
    assert len(call_params) == 3
    offsets = [int(p["offset"]) for p in call_params]
    assert offsets == [0, 50, 100]
    # Sorted oldest-first: timestamp increases
    timestamps = [t.timestamp for t in txs]
    assert timestamps == sorted(timestamps)
    # Sleep called between pages (between page 2 and 3, once after first page)
    assert mock_sleep.call_count == 2
    mock_sleep.assert_called_with(0.2)


@respx.mock
async def test_get_xpub_transactions_all_stops_on_empty_page(client):
    """Pagination stops if API returns empty txs before n_tx is reached."""
    call_count = 0

    def side_effect(request):
        nonlocal call_count
        call_count += 1
        offset = int(dict(request.url.params).get("offset", 0))
        txs = (
            [
                {
                    "hash": f"tx_{offset + i}",
                    "time": 1700000000 + offset + i,
                    "block_height": 820000,
                    "result": 1000,
                }
                for i in range(50)
            ]
            if offset == 0
            else []
        )
        return httpx.Response(
            200,
            json={
                "wallet": {"final_balance": 0, "n_tx": 200},
                "addresses": [],
                "txs": txs,
                "info": {"n_tx": 200, "n_unredeemed": 0},
            },
        )

    respx.get(MULTIADDR_PATH).mock(side_effect=side_effect)

    with patch("backend.clients.xpub.asyncio.sleep", new_callable=AsyncMock):
        txs = await client.get_xpub_transactions_all(XPUB)

    # Two requests made (offset 0, offset 50 → empty → stop)
    assert call_count == 2
    assert len(txs) == 50


# ---------------------------------------------------------------------------
# get_xpub_transactions_since
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_xpub_transactions_since(client):
    """Stop pagination when tx.timestamp ≤ after_timestamp; result sorted oldest-first."""
    after_ts = 1700001000

    # Page has: newest tx (1700002000), then one at boundary (1700001000) → stop
    txs_page = [
        {"hash": "txnew2", "time": 1700002000, "block_height": 820002, "result": 500},
        {"hash": "txnew1", "time": 1700001500, "block_height": 820001, "result": 300},
        {"hash": "txold", "time": 1700001000, "block_height": 820000, "result": 100},
    ]

    call_count = 0

    def side_effect(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(
            200,
            json={
                "wallet": {"final_balance": 0, "n_tx": 10},
                "addresses": [],
                "txs": txs_page,
                "info": {"n_tx": 10},
            },
        )

    respx.get(MULTIADDR_PATH).mock(side_effect=side_effect)

    txs = await client.get_xpub_transactions_since(XPUB, after_ts)

    # Only txs strictly newer than after_ts
    assert len(txs) == 2
    assert call_count == 1
    # Sorted oldest-first
    assert txs[0].tx_hash == "txnew1"
    assert txs[1].tx_hash == "txnew2"


@respx.mock
async def test_get_xpub_transactions_since_all_new(client):
    """If all txs on all pages are new, fetches all pages."""
    call_count = 0
    after_ts = 1699999999

    def side_effect(request):
        nonlocal call_count
        call_count += 1
        offset = int(dict(request.url.params).get("offset", 0))
        if offset == 0:
            txs = [
                {
                    "hash": f"tx_p1_{i}",
                    "time": 1700001000 + i,
                    "block_height": 820000,
                    "result": 1000,
                }
                for i in range(50)
            ]
        elif offset == 50:
            txs = [
                {
                    "hash": f"tx_p2_{i}",
                    "time": 1700000001 + i,
                    "block_height": 820001,
                    "result": 1000,
                }
                for i in range(3)
            ]
        else:
            txs = []
        return httpx.Response(
            200,
            json={
                "wallet": {"final_balance": 0, "n_tx": 53},
                "addresses": [],
                "txs": txs,
                "info": {"n_tx": 53},
            },
        )

    respx.get(MULTIADDR_PATH).mock(side_effect=side_effect)

    with patch("backend.clients.xpub.asyncio.sleep", new_callable=AsyncMock):
        txs = await client.get_xpub_transactions_since(XPUB, after_ts)

    # All 53 transactions are newer than after_ts
    assert len(txs) == 53
    assert call_count == 3


# ---------------------------------------------------------------------------
# Unconfirmed transaction (time=None)
# ---------------------------------------------------------------------------


@respx.mock
async def test_xpub_client_unconfirmed_tx(client):
    """tx with time=None → XpubTransaction.timestamp is preserved as None.

    The service layer uses timestamp=None to detect and skip unconfirmed
    transactions during history replay.
    """
    unconfirmed_tx = {
        "hash": "txunconfirmed",
        "time": None,
        "block_height": None,
        "result": 10_000,
    }
    confirmed_tx = {
        "hash": "txconfirmed",
        "time": 1700000000,
        "block_height": 820000,
        "result": 50_000,
    }

    respx.get(MULTIADDR_PATH).mock(
        return_value=httpx.Response(
            200,
            json={
                "wallet": {"final_balance": 60_000, "n_tx": 2},
                "addresses": [],
                "txs": [unconfirmed_tx, confirmed_tx],
                "info": {"n_tx": 2},
            },
        )
    )

    txs = await client.get_xpub_transactions_all(XPUB)

    assert len(txs) == 2
    # Unconfirmed tx is present but with timestamp=None
    unconfirmed = next(t for t in txs if t.tx_hash == "txunconfirmed")
    assert unconfirmed.timestamp is None
    assert unconfirmed.block_height is None
    # The confirmed tx has its proper timestamp
    confirmed = next(t for t in txs if t.tx_hash == "txconfirmed")
    assert confirmed.timestamp == 1700000000
    assert confirmed.block_height == 820000


# ---------------------------------------------------------------------------
# info.n_tx = 0 → no extra requests
# ---------------------------------------------------------------------------


@respx.mock
async def test_xpub_client_zero_n_tx(client):
    """info.n_tx=0 → returns [], no extra requests made."""
    call_count = 0

    def side_effect(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(
            200,
            json={
                "wallet": {"final_balance": 0, "n_tx": 0},
                "addresses": [],
                "txs": [],
                "info": {"n_tx": 0},
            },
        )

    respx.get(MULTIADDR_PATH).mock(side_effect=side_effect)

    txs = await client.get_xpub_transactions_all(XPUB)

    assert txs == []
    assert call_count == 1  # Only the first request, no pagination


# ---------------------------------------------------------------------------
# Rate limit (429) — inherited BaseClient retry
# ---------------------------------------------------------------------------


@respx.mock
async def test_xpub_client_rate_limit_handling(client):
    """429 → waits Retry-After, retries once, returns successfully."""
    call_count = 0

    def side_effect(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(429, headers={"Retry-After": "5"})
        return httpx.Response(200, json=_multiaddr_response())

    respx.get(MULTIADDR_PATH).mock(side_effect=side_effect)

    with patch(
        "backend.clients.base.asyncio.sleep", new_callable=AsyncMock
    ) as mock_sleep:
        summary = await client.get_xpub_summary(XPUB)

    assert call_count == 2
    mock_sleep.assert_called_once_with(5)
    assert summary.balance_sat == 100_000_000


# ---------------------------------------------------------------------------
# FR-H13: n_tx > 0 filter — only active addresses returned
# ---------------------------------------------------------------------------


@respx.mock
async def test_xpub_summary_filters_zero_tx_addresses(client):
    """Addresses with n_tx=0 must be excluded from derived_addresses (FR-H13)."""
    addresses = [
        {
            "address": "bc1qactive",
            "final_balance": 50_000_000,
            "n_tx": 3,
            "total_received": 50_000_000,
            "total_sent": 0,
        },
        {
            "address": "bc1qinactive",
            "final_balance": 0,
            "n_tx": 0,
            "total_received": 0,
            "total_sent": 0,
        },
    ]
    respx.get(MULTIADDR_PATH).mock(
        return_value=httpx.Response(
            200,
            json=_multiaddr_response(
                balance_sat=50_000_000, n_tx=3, addresses=addresses
            ),
        )
    )

    summary = await client.get_xpub_summary(XPUB)

    assert len(summary.derived_addresses) == 1
    assert summary.derived_addresses[0].address == "bc1qactive"
    assert summary.derived_addresses[0].n_tx == 3


@respx.mock
async def test_xpub_summary_xpub_string_not_included_as_address(client):
    """The xpub key string echoed back by blockchain.info with n_tx=0 must be excluded (FR-H13)."""
    addresses = [
        {
            "address": XPUB,  # blockchain.info quirk: xpub echoed as an address entry
            "final_balance": 0,
            "n_tx": 0,
            "total_received": 0,
            "total_sent": 0,
        },
        {
            "address": "bc1qrealaddr",
            "final_balance": 10_000_000,
            "n_tx": 1,
            "total_received": 10_000_000,
            "total_sent": 0,
        },
    ]
    respx.get(MULTIADDR_PATH).mock(
        return_value=httpx.Response(
            200,
            json=_multiaddr_response(
                balance_sat=10_000_000, n_tx=1, addresses=addresses
            ),
        )
    )

    summary = await client.get_xpub_summary(XPUB)

    assert len(summary.derived_addresses) == 1
    assert summary.derived_addresses[0].address == "bc1qrealaddr"
    # The xpub string itself must not appear in derived_addresses
    assert not any(a.address == XPUB for a in summary.derived_addresses)


# ---------------------------------------------------------------------------
# HTTP 5xx — raises on first failure (no retry from 5xx in BaseClient)
# ---------------------------------------------------------------------------


@respx.mock
async def test_xpub_client_server_error(client):
    """500 → raises HTTPStatusError immediately (no retry for 5xx)."""
    call_count = 0

    def side_effect(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(500)

    respx.get(MULTIADDR_PATH).mock(side_effect=side_effect)

    with pytest.raises(httpx.HTTPStatusError):
        await client.get_xpub_summary(XPUB)

    assert call_count == 1
