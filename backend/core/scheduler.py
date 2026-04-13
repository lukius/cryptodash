import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self, refresh_service: Any, config_repo: Any) -> None:
        self._refresh_service = refresh_service
        self._config_repo = config_repo
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Read interval from config and start the loop. Called at app startup."""
        interval_minutes = await self._config_repo.get_int("refresh_interval_minutes")
        if interval_minutes is not None:
            self._task = asyncio.create_task(self._loop(interval_minutes))

    async def restart(self, interval_minutes: int | None) -> None:
        """Cancel current loop (if any) and start a new one with the given interval.
        If interval_minutes is None, the scheduler is disabled (no auto-refresh)."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

        if interval_minutes is not None:
            self._task = asyncio.create_task(self._loop(interval_minutes))

    async def stop(self) -> None:
        """Cancel the loop. Called at app shutdown."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    async def _loop(self, interval_minutes: int) -> None:
        """Main scheduler loop. Runs until cancelled."""
        logger.info(f"Scheduler started with interval={interval_minutes}m")
        while True:
            await asyncio.sleep(interval_minutes * 60)
            logger.info("Scheduled refresh starting")
            try:
                result = await self._refresh_service.run_full_refresh()
                logger.info(
                    f"Scheduled refresh completed: "
                    f"{result.success_count} ok, {result.failure_count} failed"
                )
            except Exception as e:
                logger.error(f"Scheduled refresh failed: {e}")
