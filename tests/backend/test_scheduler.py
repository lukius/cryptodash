import asyncio
import unittest.mock
from unittest.mock import AsyncMock

import pytest

from backend.core.scheduler import Scheduler


def make_scheduler(refresh_mock=None, interval=None):
    if refresh_mock is None:
        refresh_mock = AsyncMock()
        refresh_mock.run_full_refresh = AsyncMock()
    config_repo = AsyncMock()
    config_repo.get_int = AsyncMock(return_value=interval)
    return Scheduler(refresh_mock, config_repo), refresh_mock


@pytest.mark.asyncio
async def test_start_with_none_interval_does_not_start_loop():
    """start() with no interval in config should not create a task."""
    scheduler, _ = make_scheduler(interval=None)
    await scheduler.start()
    assert scheduler._task is None


@pytest.mark.asyncio
async def test_start_with_interval_creates_task():
    """start() with an interval should create a running asyncio task."""
    scheduler, _ = make_scheduler(interval=60)
    await scheduler.start()
    assert scheduler._task is not None
    assert not scheduler._task.done()
    await scheduler.stop()


@pytest.mark.asyncio
async def test_stop_cancels_task():
    """stop() should cancel the running loop task."""
    scheduler, _ = make_scheduler(interval=60)
    await scheduler.start()
    task = scheduler._task
    assert not task.done()
    await scheduler.stop()
    assert scheduler._task is None
    assert task.done()


@pytest.mark.asyncio
async def test_restart_with_none_stops_loop():
    """restart(None) should cancel the current loop and not start a new one."""
    scheduler, _ = make_scheduler(interval=60)
    await scheduler.start()
    assert scheduler._task is not None
    await scheduler.restart(None)
    assert scheduler._task is None


@pytest.mark.asyncio
async def test_restart_with_interval_replaces_loop():
    """restart(N) should cancel old loop and start a new one."""
    scheduler, _ = make_scheduler(interval=60)
    await scheduler.start()
    old_task = scheduler._task
    await scheduler.restart(30)
    assert scheduler._task is not None
    assert scheduler._task is not old_task
    await scheduler.stop()


@pytest.mark.asyncio
async def test_loop_calls_refresh_and_survives_error():
    """The loop should catch exceptions from run_full_refresh and keep running."""
    refresh_mock = AsyncMock()
    refresh_mock.run_full_refresh = AsyncMock(side_effect=RuntimeError("boom"))
    scheduler, _ = make_scheduler(refresh_mock)

    original_sleep = asyncio.sleep
    call_count = 0

    async def fast_sleep(seconds):
        nonlocal call_count
        call_count += 1
        if call_count >= 3:
            raise asyncio.CancelledError()
        await original_sleep(0)

    with unittest.mock.patch("asyncio.sleep", side_effect=fast_sleep):
        task = asyncio.create_task(scheduler._loop(0.001))
        try:
            await asyncio.wait_for(task, timeout=5.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass

    # Despite the error, run_full_refresh was called at least twice
    assert refresh_mock.run_full_refresh.call_count >= 2


@pytest.mark.asyncio
async def test_loop_calls_refresh_on_interval():
    """The loop should call run_full_refresh after each sleep interval."""
    refresh_mock = AsyncMock()
    refresh_mock.run_full_refresh = AsyncMock()
    scheduler, _ = make_scheduler(refresh_mock)

    original_sleep = asyncio.sleep
    call_count = 0

    async def fast_sleep(seconds):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.CancelledError()
        await original_sleep(0)

    with unittest.mock.patch("asyncio.sleep", side_effect=fast_sleep):
        task = asyncio.create_task(scheduler._loop(0.001))
        try:
            await asyncio.wait_for(task, timeout=5.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass

    assert refresh_mock.run_full_refresh.call_count >= 1


@pytest.mark.asyncio
async def test_stop_when_no_task_is_noop():
    """stop() with no running task should not raise."""
    scheduler, _ = make_scheduler()
    assert scheduler._task is None
    await scheduler.stop()  # should not raise
    assert scheduler._task is None
