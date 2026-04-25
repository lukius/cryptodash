"""Tests for BitcoinClient (Mempool.space)."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from backend.clients.bitcoin import BitcoinClient


BASE_URL = "https://mempool.space/api"


@pytest.fixture
def client():
    return BitcoinClient()


# ---------------------------------------------------------------------------
# get_balance
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_balance_satoshi_conversion(client):
    """funded_txo_sum - spent_txo_sum, divided by SATOSHI."""
    address = "bc1qtest"
    respx.get(f"{BASE_URL}/address/{address}").mock(
        return_value=httpx.Response(
            200,
            json={
                "chain_stats": {
                    "funded_txo_sum": 150_000_000,
                    "spent_txo_sum": 50_000_000,
                    "tx_count": 2,
                },
                "mempool_stats": {},
            },
        )
    )

    balance = await client.get_balance(address)

    assert balance == Decimal("1.0")
    assert isinstance(balance, Decimal)


@respx.mock
async def test_get_balance_zero(client):
    address = "bc1qempty"
    respx.get(f"{BASE_URL}/address/{address}").mock(
        return_value=httpx.Response(
            200,
            json={
                "chain_stats": {
                    "funded_txo_sum": 0,
                    "spent_txo_sum": 0,
                    "tx_count": 0,
                },
            },
        )
    )

    balance = await client.get_balance(address)

    assert balance == Decimal("0")


# ---------------------------------------------------------------------------
# get_all_transactions — summary path
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_all_transactions_summary_path(client):
    """Uses summary path when total_txs <= 5000."""
    address = "bc1qtest"
    summary_data = [
        {"txid": "txabc", "height": 800000, "value": 100_000_000, "time": 1700000000},
        {"txid": "txdef", "height": 800001, "value": -50_000_000, "time": 1700001000},
    ]
    addr_info = {
        "chain_stats": {
            "funded_txo_sum": 150_000_000,
            "spent_txo_sum": 50_000_000,
            "tx_count": 2,
        },
    }

    respx.get(f"{BASE_URL}/address/{address}/txs/summary").mock(
        return_value=httpx.Response(200, json=summary_data)
    )
    respx.get(f"{BASE_URL}/address/{address}").mock(
        return_value=httpx.Response(200, json=addr_info)
    )

    txs = await client.get_all_transactions(address)

    assert len(txs) == 2
    assert txs[0]["tx_hash"] == "txabc"
    assert txs[0]["amount_sat"] == 100_000_000
    assert txs[0]["block_height"] == 800000
    assert txs[0]["timestamp"] == 1700000000
    assert txs[1]["tx_hash"] == "txdef"
    assert txs[1]["amount_sat"] == -50_000_000


@respx.mock
async def test_get_all_transactions_summary_covers_all(client):
    """summary covers all when len(summary) >= total_txs."""
    address = "bc1qtest"
    summary_data = [
        {"txid": "tx1", "height": 100, "value": 10_000, "time": 1000},
    ]
    addr_info = {
        "chain_stats": {
            "funded_txo_sum": 10_000,
            "spent_txo_sum": 0,
            "tx_count": 1,
        },
    }

    respx.get(f"{BASE_URL}/address/{address}/txs/summary").mock(
        return_value=httpx.Response(200, json=summary_data)
    )
    respx.get(f"{BASE_URL}/address/{address}").mock(
        return_value=httpx.Response(200, json=addr_info)
    )

    txs = await client.get_all_transactions(address)

    assert len(txs) == 1
    assert txs[0]["tx_hash"] == "tx1"


# ---------------------------------------------------------------------------
# get_all_transactions — UTXO fallback
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_all_transactions_fallback_to_utxo_parsing(client):
    """Falls back to UTXO parsing when total_txs > summary count (>5000)."""
    address = "bc1qlarge"

    # Summary only returns 2 entries but total is 6000
    summary_data = [
        {"txid": "txA", "height": 100, "value": 1000, "time": 1000},
        {"txid": "txB", "height": 101, "value": -500, "time": 1001},
    ]
    addr_info = {
        "chain_stats": {
            "funded_txo_sum": 1000,
            "spent_txo_sum": 500,
            "tx_count": 6000,
        },
    }

    # Single page of full transactions (< 25 items means last page)
    full_tx_page = [
        {
            "txid": "txFull1",
            "status": {"block_height": 200, "block_time": 2000},
            "vout": [
                {"scriptpubkey_address": address, "value": 2000},
                {"scriptpubkey_address": "other", "value": 500},
            ],
            "vin": [
                {
                    "prevout": {
                        "scriptpubkey_address": "other",
                        "value": 2500,
                    }
                }
            ],
        }
    ]

    respx.get(f"{BASE_URL}/address/{address}/txs/summary").mock(
        return_value=httpx.Response(200, json=summary_data)
    )
    respx.get(f"{BASE_URL}/address/{address}").mock(
        return_value=httpx.Response(200, json=addr_info)
    )
    respx.get(f"{BASE_URL}/address/{address}/txs/chain").mock(
        return_value=httpx.Response(200, json=full_tx_page)
    )

    txs = await client.get_all_transactions(address)

    assert len(txs) == 1
    assert txs[0]["tx_hash"] == "txFull1"
    # inflow=2000, outflow=0 (other address), net=2000
    assert txs[0]["amount_sat"] == 2000
    assert txs[0]["block_height"] == 200
    assert txs[0]["timestamp"] == 2000


# ---------------------------------------------------------------------------
# coinbase transaction (no prevout)
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_all_transactions_coinbase_tx(client):
    """Coinbase tx has no prevout on vin; inflow only."""
    address = "bc1qlarge"
    summary_data = []
    addr_info = {
        "chain_stats": {
            "funded_txo_sum": 625_000_000,
            "spent_txo_sum": 0,
            "tx_count": 6001,
        },
    }
    coinbase_tx = {
        "txid": "txCoinbase",
        "status": {"block_height": 1, "block_time": 500},
        "vout": [{"scriptpubkey_address": address, "value": 625_000_000}],
        "vin": [{"is_coinbase": True}],  # No prevout
    }

    respx.get(f"{BASE_URL}/address/{address}/txs/summary").mock(
        return_value=httpx.Response(200, json=summary_data)
    )
    respx.get(f"{BASE_URL}/address/{address}").mock(
        return_value=httpx.Response(200, json=addr_info)
    )
    respx.get(f"{BASE_URL}/address/{address}/txs/chain").mock(
        return_value=httpx.Response(200, json=[coinbase_tx])
    )

    txs = await client.get_all_transactions(address)

    assert len(txs) == 1
    # inflow = 625_000_000, outflow = 0 (coinbase vin has no prevout)
    assert txs[0]["amount_sat"] == 625_000_000


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_with_retry_succeeds_on_second_attempt(client):
    """_get_with_retry makes exactly two HTTP calls when first fails."""
    address = "bc1qtest"
    call_count = 0

    def side_effect(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.ConnectError("Network error")
        return httpx.Response(
            200,
            json={
                "chain_stats": {
                    "funded_txo_sum": 100_000_000,
                    "spent_txo_sum": 0,
                    "tx_count": 1,
                }
            },
        )

    respx.get(f"{BASE_URL}/address/{address}").mock(side_effect=side_effect)

    with patch(
        "backend.clients.base.asyncio.sleep", new_callable=AsyncMock
    ) as mock_sleep:
        balance = await client.get_balance(address)

    assert balance == Decimal("1.0")
    assert call_count == 2
    mock_sleep.assert_called_once_with(10)


@respx.mock
async def test_get_with_retry_on_429_uses_retry_after(client):
    """HTTP 429 triggers retry; waits Retry-After seconds."""
    address = "bc1qtest"
    call_count = 0

    def side_effect(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(429, headers={"Retry-After": "30"})
        return httpx.Response(
            200,
            json={
                "chain_stats": {
                    "funded_txo_sum": 100_000_000,
                    "spent_txo_sum": 0,
                    "tx_count": 1,
                }
            },
        )

    respx.get(f"{BASE_URL}/address/{address}").mock(side_effect=side_effect)

    with patch(
        "backend.clients.base.asyncio.sleep", new_callable=AsyncMock
    ) as mock_sleep:
        balance = await client.get_balance(address)

    assert balance == Decimal("1.0")
    assert call_count == 2
    mock_sleep.assert_called_once_with(30)


@respx.mock
async def test_get_with_retry_on_429_defaults_10s_when_no_header(client):
    """HTTP 429 without Retry-After header defaults to 10s wait."""
    address = "bc1qtest"
    call_count = 0

    def side_effect(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(429)
        return httpx.Response(
            200,
            json={
                "chain_stats": {
                    "funded_txo_sum": 50_000_000,
                    "spent_txo_sum": 0,
                    "tx_count": 1,
                }
            },
        )

    respx.get(f"{BASE_URL}/address/{address}").mock(side_effect=side_effect)

    with patch(
        "backend.clients.base.asyncio.sleep", new_callable=AsyncMock
    ) as mock_sleep:
        balance = await client.get_balance(address)

    assert balance == Decimal("0.5")
    assert call_count == 2
    mock_sleep.assert_called_once_with(10)


@respx.mock
async def test_get_with_retry_raises_on_persistent_5xx(client):
    """HTTP 5xx is retried once; if it persists the error propagates."""
    address = "bc1qtest"
    call_count = 0

    def side_effect(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(500)

    respx.get(f"{BASE_URL}/address/{address}").mock(side_effect=side_effect)

    with patch("backend.clients.base.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_balance(address)

    assert call_count == 2


# ---------------------------------------------------------------------------
# get_transactions_paginated
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_transactions_paginated_without_cursor(client):
    address = "bc1qtest"
    page_data = [{"txid": "txFirst"}]
    respx.get(f"{BASE_URL}/address/{address}/txs/chain").mock(
        return_value=httpx.Response(200, json=page_data)
    )

    result = await client.get_transactions_paginated(address)

    assert result == page_data


@respx.mock
async def test_get_transactions_paginated_with_cursor(client):
    address = "bc1qtest"
    after_txid = "txPrev"
    page_data = [{"txid": "txSecond"}]
    respx.get(f"{BASE_URL}/address/{address}/txs/chain/{after_txid}").mock(
        return_value=httpx.Response(200, json=page_data)
    )

    result = await client.get_transactions_paginated(address, after_txid=after_txid)

    assert result == page_data
