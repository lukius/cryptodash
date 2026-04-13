"""Tests for BaseClient retry and error-propagation behavior."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from backend.clients.bitcoin import BitcoinClient

# Use BitcoinClient as a concrete BaseClient — all retry logic lives in BaseClient.
BASE_URL = "https://mempool.space/api"
ADDRESS = "bc1qtest"
ADDRESS_PATH = f"{BASE_URL}/address/{ADDRESS}"

SUCCESS_RESPONSE = httpx.Response(
    200,
    json={
        "chain_stats": {
            "funded_txo_sum": 100_000_000,
            "spent_txo_sum": 0,
            "tx_count": 1,
        }
    },
)


@pytest.fixture
def client():
    return BitcoinClient()


# ---------------------------------------------------------------------------
# test_request_timeout — httpx.ReadTimeout propagates after retry
# ---------------------------------------------------------------------------


@respx.mock
async def test_request_timeout(client):
    """ReadTimeout on both attempts raises to the caller after one retry."""
    call_count = 0

    def side_effect(request):
        nonlocal call_count
        call_count += 1
        raise httpx.ReadTimeout("timed out", request=request)

    respx.get(ADDRESS_PATH).mock(side_effect=side_effect)

    with patch(
        "backend.clients.base.asyncio.sleep", new_callable=AsyncMock
    ) as mock_sleep:
        with pytest.raises(httpx.ReadTimeout):
            await client.get_balance(ADDRESS)

    assert call_count == 2
    mock_sleep.assert_called_once_with(10)


# ---------------------------------------------------------------------------
# test_network_unreachable — httpx.ConnectError propagates after retry
# ---------------------------------------------------------------------------


@respx.mock
async def test_network_unreachable(client):
    """ConnectError on both attempts raises to the caller after one retry."""
    call_count = 0

    def side_effect(request):
        nonlocal call_count
        call_count += 1
        raise httpx.ConnectError("network unreachable")

    respx.get(ADDRESS_PATH).mock(side_effect=side_effect)

    with patch(
        "backend.clients.base.asyncio.sleep", new_callable=AsyncMock
    ) as mock_sleep:
        with pytest.raises(httpx.ConnectError):
            await client.get_balance(ADDRESS)

    assert call_count == 2
    mock_sleep.assert_called_once_with(10)


# ---------------------------------------------------------------------------
# Confirm 5xx is not retried (BaseClient perspective)
# ---------------------------------------------------------------------------


@respx.mock
async def test_server_error_no_retry(client):
    """HTTP 5xx raises immediately without retry — no sleep, single call."""
    call_count = 0

    def side_effect(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(503)

    respx.get(ADDRESS_PATH).mock(side_effect=side_effect)

    with patch(
        "backend.clients.base.asyncio.sleep", new_callable=AsyncMock
    ) as mock_sleep:
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_balance(ADDRESS)

    assert call_count == 1
    mock_sleep.assert_not_called()
