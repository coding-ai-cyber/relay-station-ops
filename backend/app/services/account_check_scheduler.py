import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.sub2api_instance import Sub2APIInstance
from app.services.sub2api_admin_adapter import run_admin_key_account_check

logger = logging.getLogger(__name__)

CheckOnce = Callable[[], None | Awaitable[None]]
Sleep = Callable[[float], Awaitable[None]]


async def _maybe_await(value: None | Awaitable[None]) -> None:
    if inspect.isawaitable(value):
        await value


async def run_account_check_scheduler(
    *,
    check_once: CheckOnce,
    sleep: Sleep = asyncio.sleep,
    interval_seconds: float = 600,
    iterations: int | None = None,
) -> None:
    count = 0
    while True:
        await _maybe_await(check_once())
        count += 1
        if iterations is not None and count >= iterations:
            return
        await sleep(interval_seconds)


def check_once_with_session(session_factory: sessionmaker[Session] = SessionLocal) -> None:
    with session_factory() as db:
        instances = db.scalars(
            select(Sub2APIInstance).where(Sub2APIInstance.is_active.is_(True))
        ).all()
        batches = [
            run_admin_key_account_check(
                db=db,
                instance=instance,
                checked_by=None,
                include_only_operation=settings.sub2api_account_check_only_operation,
                timeout_seconds=15,
                remark="scheduled account check",
            )
            for instance in instances
        ]
    logger.info("Sub2API account auto check completed for %s instances", len(batches))


async def check_once_with_session_in_thread() -> None:
    await asyncio.to_thread(check_once_with_session)


def start_account_check_scheduler() -> asyncio.Task[None]:
    return asyncio.create_task(
        run_account_check_scheduler(
            check_once=check_once_with_session_in_thread,
            interval_seconds=settings.sub2api_account_check_interval_seconds,
        )
    )


async def stop_account_check_scheduler(task: asyncio.Task[None] | None) -> None:
    if task is None:
        return
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
