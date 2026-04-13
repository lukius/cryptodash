from decimal import Decimal

from backend.clients.base import BaseClient

COIN_IDS = {"BTC": "bitcoin", "KAS": "kaspa"}


class CoinGeckoClient(BaseClient):
    MAX_HISTORY_DAYS = 365  # Free tier hard limit

    def __init__(self):
        super().__init__(base_url="https://api.coingecko.com/api/v3", timeout=30.0)

    async def get_current_prices(self) -> dict[str, Decimal]:
        """
        Returns current USD prices for BTC and KAS in a single API call.
        Returns: { "BTC": Decimal("71681"), "KAS": Decimal("0.03251085") }
        """
        data = await self._get_with_retry(
            "/simple/price",
            params={
                "ids": "bitcoin,kaspa",
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_last_updated_at": "true",
            },
        )
        result = {}
        for network, coin_id in COIN_IDS.items():
            if coin_id in data and "usd" in data[coin_id]:
                result[network] = Decimal(str(data[coin_id]["usd"]))
        return result

    async def get_price_history(
        self, network: str, days: int
    ) -> list[tuple[int, Decimal]]:
        """
        Returns daily historical prices as [(timestamp_ms, price_usd), ...].
        Max 365 days on free tier.
        """
        days = min(days, self.MAX_HISTORY_DAYS)
        coin_id = COIN_IDS[network]
        data = await self._get(
            f"/coins/{coin_id}/market_chart",
            params={
                "vs_currency": "usd",
                "days": days,
                "interval": "daily",
            },
        )
        return [
            (int(point[0]), Decimal(str(point[1]))) for point in data.get("prices", [])
        ]

    async def get_price_at_date_range(
        self, network: str, from_ts: int, to_ts: int
    ) -> list[tuple[int, Decimal]]:
        """
        Returns prices in a Unix timestamp range (seconds).
        Returns: [(timestamp_ms, price_usd), ...]
        """
        coin_id = COIN_IDS[network]
        data = await self._get(
            f"/coins/{coin_id}/market_chart/range",
            params={
                "vs_currency": "usd",
                "from": from_ts,
                "to": to_ts,
            },
        )
        return [
            (int(point[0]), Decimal(str(point[1]))) for point in data.get("prices", [])
        ]
