import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.shop_monitor_sync import sync_enabled_shop_monitors

logger = logging.getLogger(__name__)

SyncOnce = Callable[[], None | Awaitable[None]]
Sleep = Callable[[float], Awaitable[None]]


async def _maybe_await(value: None | Awaitable[None]) -> None:
    if inspect.isawaitable(value):
        await value


async def run_shop_monitor_scheduler(
    *,
    sync_once: SyncOnce,
    sleep: Sleep = asyncio.sleep,
    interval_seconds: float = 300,
    iterations: int | None = None,
) -> None:
    count = 0
    while True:
        await _maybe_await(sync_once())
        count += 1
        if iterations is not None and count >= iterations:
            return
        await sleep(interval_seconds)


async def run_shop_monitor_scheduler_once_for_test(
    *,
    sync_once: SyncOnce,
    sleep: Sleep,
    interval_seconds: float,
    iterations: int,
) -> None:
    await run_shop_monitor_scheduler(
        sync_once=sync_once,
        sleep=sleep,
        interval_seconds=interval_seconds,
        iterations=iterations,
    )


def sync_once_with_session(session_factory: sessionmaker[Session] = SessionLocal) -> None:
    with session_factory() as db:
        results = sync_enabled_shop_monitors(db)
    failed = [result for result in results if result.status != "success"]
    if failed:
        logger.warning("Shop monitor auto sync completed with %s failures", len(failed))
    else:
        logger.info("Shop monitor auto sync completed for %s shops", len(results))


async def sync_once_with_session_in_thread() -> None:
    await asyncio.to_thread(sync_once_with_session)


def start_shop_monitor_scheduler() -> asyncio.Task[None]:
    return asyncio.create_task(
        run_shop_monitor_scheduler(
            sync_once=sync_once_with_session_in_thread,
            interval_seconds=settings.shop_monitor_sync_interval_seconds,
        )
    )


async def stop_shop_monitor_scheduler(task: asyncio.Task[None] | None) -> None:
    if task is None:
        return
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
