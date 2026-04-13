import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)


class BaseClient:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(timeout, connect=10.0),
            headers={"User-Agent": "CryptoDash/1.0"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str, params: dict | None = None) -> dict | list:
        response = await self._client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    async def _get_with_retry(
        self, path: str, params: dict | None = None
    ) -> dict | list:
        """Single retry on transient failure.

        - HTTP 429: wait Retry-After seconds (or 60s default), retry once.
        - HTTP 5xx / 4xx: raise immediately — no retry.
        - RequestError (timeout, network): wait 10s, retry once.
        """
        try:
            response = await self._client.get(path, params=params)
            if response.status_code == 429:
                wait = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limited on {path}. Waiting {wait}s before retry.")
                await asyncio.sleep(wait)
                response = await self._client.get(path, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError:
            raise
        except httpx.RequestError as e:
            logger.warning(f"Request error for {path}: {e}. Retrying in 10s.")
            await asyncio.sleep(10)
            response = await self._client.get(path, params=params)
            response.raise_for_status()
            return response.json()
