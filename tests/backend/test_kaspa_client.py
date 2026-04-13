"""Tests for KaspaClient (api.kaspa.org)."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from backend.clients.kaspa import KaspaClient, SOMPI


BASE_URL = "https://api.kaspa.org"


@pytest.fixture
def client():
    return KaspaClient()


# ---------------------------------------------------------------------------
# get_balance
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_balance_sompi_conversion(client):
    """balance_sompi / SOMPI = KAS."""
    address = "kaspa:qtest"
    respx.get(f"{BASE_URL}/addresses/{address}/balance").mock(
        return_value=httpx.Response(200, json={"balance": 100_000_000})
    )

    balance = await client.get_balance(address)

    assert balance == Decimal("1.0")
    assert isinstance(balance, Decimal)


@respx.mock
async def test_get_balance_fractional(client):
    address = "kaspa:qtest"
    respx.get(f"{BASE_URL}/addresses/{address}/balance").mock(
        return_value=httpx.Response(200, json={"balance": 123_456_789})
    )

    balance = await client.get_balance(address)

    assert balance == Decimal("123456789") / SOMPI


# ---------------------------------------------------------------------------
# get_price_usd
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_price_usd(client):
    respx.get(f"{BASE_URL}/info/price").mock(
        return_value=httpx.Response(200, json={"price": 0.03251085})
    )

    price = await client.get_price_usd()

    assert isinstance(price, Decimal)
    assert price == Decimal("0.03251085")


# ---------------------------------------------------------------------------
# get_transaction_count
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_transaction_count(client):
    address = "kaspa:qtest"
    respx.get(f"{BASE_URL}/addresses/{address}/transactions-count").mock(
        return_value=httpx.Response(200, json={"total": 42})
    )

    count = await client.get_transaction_count(address)

    assert count == 42


# ---------------------------------------------------------------------------
# get_transactions_page
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_transactions_page_returns_cursor(client):
    address = "kaspa:qtest"
    page_data = [{"transaction_id": "tx1", "is_accepted": True}]
    respx.get(f"{BASE_URL}/addresses/{address}/full-transactions-page").mock(
        return_value=httpx.Response(
            200,
            json=page_data,
            headers={"X-Next-Page-Before": "1700000000000"},
        )
    )

    txs, next_cursor = await client.get_transactions_page(address)

    assert txs == page_data
    assert next_cursor == 1700000000000


@respx.mock
async def test_get_transactions_page_no_cursor_when_exhausted(client):
    address = "kaspa:qtest"
    page_data = [{"transaction_id": "txLast", "is_accepted": True}]
    respx.get(f"{BASE_URL}/addresses/{address}/full-transactions-page").mock(
        return_value=httpx.Response(200, json=page_data)
    )

    txs, next_cursor = await client.get_transactions_page(address)

    assert txs == page_data
    assert next_cursor is None


# ---------------------------------------------------------------------------
# get_all_transactions — pagination and filtering
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_all_transactions_happy_path(client):
    """Single page of accepted transactions are parsed correctly."""
    address = "kaspa:qhappy"
    page_data = [
        {
            "transaction_id": "txA",
            "block_time": 1700000000,
            "is_accepted": True,
            "outputs": [
                {"script_public_key_address": address, "amount": "500000000"},
                {"script_public_key_address": "kaspa:other", "amount": "100000000"},
            ],
            "inputs": [],
        }
    ]
    respx.get(f"{BASE_URL}/addresses/{address}/full-transactions-page").mock(
        return_value=httpx.Response(200, json=page_data)
    )

    txs = await client.get_all_transactions(address)

    assert len(txs) == 1
    assert txs[0]["tx_hash"] == "txA"
    assert txs[0]["amount_sompi"] == 500_000_000
    assert txs[0]["timestamp"] == 1700000000


@respx.mock
async def test_get_all_transactions_rejected_tx_skipped(client):
    """Transactions with is_accepted=false are excluded."""
    address = "kaspa:qtest"
    page_data = [
        {
            "transaction_id": "txGood",
            "block_time": 1000,
            "is_accepted": True,
            "outputs": [{"script_public_key_address": address, "amount": "200000000"}],
            "inputs": [],
        },
        {
            "transaction_id": "txBad",
            "block_time": 1001,
            "is_accepted": False,
            "outputs": [{"script_public_key_address": address, "amount": "999999999"}],
            "inputs": [],
        },
    ]
    respx.get(f"{BASE_URL}/addresses/{address}/full-transactions-page").mock(
        return_value=httpx.Response(200, json=page_data)
    )

    txs = await client.get_all_transactions(address)

    assert len(txs) == 1
    assert txs[0]["tx_hash"] == "txGood"


@respx.mock
async def test_get_all_transactions_cursor_pagination(client):
    """Cursor pagination fetches multiple pages and stops when cursor is None."""
    address = "kaspa:qpaged"
    page1 = [
        {
            "transaction_id": "txPage1",
            "block_time": 1000,
            "is_accepted": True,
            "outputs": [{"script_public_key_address": address, "amount": "100"}],
            "inputs": [],
        }
    ]
    page2 = [
        {
            "transaction_id": "txPage2",
            "block_time": 900,
            "is_accepted": True,
            "outputs": [{"script_public_key_address": address, "amount": "200"}],
            "inputs": [],
        }
    ]

    call_count = 0

    def side_effect(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(
                200,
                json=page1,
                headers={"X-Next-Page-Before": "900"},
            )
        return httpx.Response(200, json=page2)

    respx.get(f"{BASE_URL}/addresses/{address}/full-transactions-page").mock(
        side_effect=side_effect
    )

    with patch("backend.clients.kaspa.asyncio.sleep", new_callable=AsyncMock):
        txs = await client.get_all_transactions(address)

    assert len(txs) == 2
    assert call_count == 2
    assert txs[0]["tx_hash"] == "txPage1"
    assert txs[1]["tx_hash"] == "txPage2"


@respx.mock
async def test_get_all_transactions_cursor_exhaustion_halts(client):
    """Pagination stops when next_cursor is None (no X-Next-Page-Before header)."""
    address = "kaspa:qtest"
    page_data = [
        {
            "transaction_id": "txOnly",
            "block_time": 500,
            "is_accepted": True,
            "outputs": [{"script_public_key_address": address, "amount": "50"}],
            "inputs": [],
        }
    ]
    respx.get(f"{BASE_URL}/addresses/{address}/full-transactions-page").mock(
        return_value=httpx.Response(200, json=page_data)
    )

    txs = await client.get_all_transactions(address)

    # Only one call was made (no next cursor)
    assert len(txs) == 1


@respx.mock
async def test_get_all_transactions_net_amount_signed(client):
    """Net amount is inflow - outflow and can be negative (spend)."""
    address = "kaspa:qtest"
    page_data = [
        {
            "transaction_id": "txSpend",
            "block_time": 2000,
            "is_accepted": True,
            "outputs": [
                {"script_public_key_address": "kaspa:other", "amount": "300"},
            ],
            "inputs": [
                {
                    "previous_outpoint_address": address,
                    "previous_outpoint_amount": "500",
                }
            ],
        }
    ]
    respx.get(f"{BASE_URL}/addresses/{address}/full-transactions-page").mock(
        return_value=httpx.Response(200, json=page_data)
    )

    txs = await client.get_all_transactions(address)

    assert len(txs) == 1
    # inflow=0, outflow=500, net=-500
    assert txs[0]["amount_sompi"] == -500
