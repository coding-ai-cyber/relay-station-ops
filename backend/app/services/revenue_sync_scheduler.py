import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.sub2api_revenue_sync import sync_sub2api_revenues

logger = logging.getLogger(__name__)

SyncOnce = Callable[[], None | Awaitable[None]]
Sleep = Callable[[float], Awaitable[None]]


async def _maybe_await(value: None | Awaitable[None]) -> None:
    if inspect.isawaitable(value):
        await value


async def run_revenue_sync_scheduler(
    *,
    sync_once: SyncOnce,
    sleep: Sleep = asyncio.sleep,
    interval_seconds: float = 600,
    iterations: int | None = None,
) -> None:
    count = 0
    while True:
        await _maybe_await(sync_once())
        count += 1
        if iterations is not None and count >= iterations:
            return
        await sleep(interval_seconds)


def sync_once_with_session(session_factory: sessionmaker[Session] = SessionLocal) -> None:
    with session_factory() as db:
        results = sync_sub2api_revenues(db)
    failed = [result for result in results if result.status != "success"]
    logger.info(
        "Sub2API revenue sync completed for %s instances, %s failures",
        len(results),
        len(failed),
    )


async def sync_once_with_session_in_thread() -> None:
    await asyncio.to_thread(sync_once_with_session)


def start_revenue_sync_scheduler() -> asyncio.Task[None]:
    return asyncio.create_task(
        run_revenue_sync_scheduler(
            sync_once=sync_once_with_session_in_thread,
            interval_seconds=settings.sub2api_revenue_sync_interval_seconds,
        )
    )


async def stop_revenue_sync_scheduler(task: asyncio.Task[None] | None) -> None:
    if task is None:
        return
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
