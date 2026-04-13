"""Tests for CoinGeckoClient."""

from decimal import Decimal

import httpx
import pytest
import respx

from backend.clients.coingecko import CoinGeckoClient


BASE_URL = "https://api.coingecko.com/api/v3"


@pytest.fixture
def client():
    return CoinGeckoClient()


# ---------------------------------------------------------------------------
# get_current_prices
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_current_prices_parses_btc_and_kas(client):
    """Returns BTC and KAS prices as Decimals."""
    respx.get(f"{BASE_URL}/simple/price").mock(
        return_value=httpx.Response(
            200,
            json={
                "bitcoin": {
                    "usd": 71681.0,
                    "usd_24h_change": 1.5,
                    "last_updated_at": 1700000000,
                },
                "kaspa": {
                    "usd": 0.03251085,
                    "usd_24h_change": -0.5,
                    "last_updated_at": 1700000000,
                },
            },
        )
    )

    prices = await client.get_current_prices()

    assert "BTC" in prices
    assert "KAS" in prices
    assert prices["BTC"] == Decimal("71681.0")
    assert prices["KAS"] == Decimal("0.03251085")
    assert isinstance(prices["BTC"], Decimal)
    assert isinstance(prices["KAS"], Decimal)


@respx.mock
async def test_get_current_prices_zero_is_returned_as_is(client):
    """Price=0 is returned without error; caller (PriceService) handles zero guard."""
    respx.get(f"{BASE_URL}/simple/price").mock(
        return_value=httpx.Response(
            200,
            json={
                "bitcoin": {"usd": 0, "usd_24h_change": 0},
                "kaspa": {"usd": 0, "usd_24h_change": 0},
            },
        )
    )

    prices = await client.get_current_prices()

    assert prices["BTC"] == Decimal("0")
    assert prices["KAS"] == Decimal("0")


@respx.mock
async def test_get_current_prices_missing_coin_excluded(client):
    """If a coin is absent from response, it's not included in result."""
    respx.get(f"{BASE_URL}/simple/price").mock(
        return_value=httpx.Response(
            200,
            json={
                "bitcoin": {"usd": 65000.0},
                # kaspa absent
            },
        )
    )

    prices = await client.get_current_prices()

    assert "BTC" in prices
    assert "KAS" not in prices


# ---------------------------------------------------------------------------
# get_price_history
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_price_history_returns_tuples(client):
    """Returns list of (timestamp_ms, price) tuples."""
    respx.get(f"{BASE_URL}/coins/bitcoin/market_chart").mock(
        return_value=httpx.Response(
            200,
            json={
                "prices": [
                    [1700000000000, 71000.5],
                    [1700086400000, 71500.0],
                ],
            },
        )
    )

    history = await client.get_price_history("BTC", 7)

    assert len(history) == 2
    assert history[0] == (1700000000000, Decimal("71000.5"))
    assert history[1] == (1700086400000, Decimal("71500.0"))
    assert isinstance(history[0][1], Decimal)


@respx.mock
async def test_get_price_history_respects_max_days_cap(client):
    """days > MAX_HISTORY_DAYS (365) is capped to 365."""
    route = respx.get(f"{BASE_URL}/coins/bitcoin/market_chart").mock(
        return_value=httpx.Response(200, json={"prices": []})
    )

    await client.get_price_history("BTC", 1000)

    request = route.calls.last.request
    assert request.url.params["days"] == "365"


@respx.mock
async def test_get_price_history_kas(client):
    """Works for KAS using 'kaspa' coin_id."""
    respx.get(f"{BASE_URL}/coins/kaspa/market_chart").mock(
        return_value=httpx.Response(200, json={"prices": [[1700000000000, 0.032]]})
    )

    history = await client.get_price_history("KAS", 30)

    assert len(history) == 1
    assert history[0][1] == Decimal("0.032")


# ---------------------------------------------------------------------------
# get_price_at_date_range
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_price_at_date_range(client):
    """Returns prices in range as (timestamp_ms, price) tuples."""
    respx.get(f"{BASE_URL}/coins/bitcoin/market_chart/range").mock(
        return_value=httpx.Response(
            200,
            json={
                "prices": [
                    [1699000000000, 69000.0],
                    [1699086400000, 70000.0],
                ]
            },
        )
    )

    result = await client.get_price_at_date_range("BTC", 1699000000, 1699100000)

    assert len(result) == 2
    assert result[0] == (1699000000000, Decimal("69000.0"))
    assert result[1] == (1699086400000, Decimal("70000.0"))
