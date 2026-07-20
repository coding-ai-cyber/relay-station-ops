from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.services.shop_monitor_scheduler import (
    start_shop_monitor_scheduler,
    stop_shop_monitor_scheduler,
)
from app.services.revenue_sync_scheduler import (
    start_revenue_sync_scheduler,
    stop_revenue_sync_scheduler,
)
from app.services.account_check_scheduler import (
    start_account_check_scheduler,
    stop_account_check_scheduler,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    sync_task = start_shop_monitor_scheduler() if settings.shop_monitor_auto_sync_enabled else None
    revenue_sync_task = (
        start_revenue_sync_scheduler()
        if settings.sub2api_revenue_auto_sync_enabled
        else None
    )
    account_check_task = (
        start_account_check_scheduler()
        if settings.sub2api_account_check_auto_enabled
        else None
    )
    try:
        yield
    finally:
        await stop_shop_monitor_scheduler(sync_task)
        await stop_revenue_sync_scheduler(revenue_sync_task)
        await stop_account_check_scheduler(account_check_task)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(api_router)
    return app


app = create_app()
