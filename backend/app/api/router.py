from fastapi import APIRouter

from app.api.routes.accounts import router as accounts_router
from app.api.routes.audit_logs import router as audit_logs_router
from app.api.routes.auth import router as auth_router
from app.api.routes.cost_items import router as cost_items_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.evaluations import (
    account_evaluation_router,
    router as evaluation_batches_router,
)
from app.api.routes.files import router as files_router
from app.api.routes.health import router as health_router
from app.api.routes.operations_platforms import router as operations_platforms_router
from app.api.routes.purchases import router as purchases_router
from app.api.routes.proxy_pools import router as proxy_pools_router
from app.api.routes.reports import router as reports_router
from app.api.routes.revenues import router as revenues_router
from app.api.routes.servers import router as servers_router
from app.api.routes.shop_monitors import router as shop_monitors_router
from app.api.routes.suppliers import router as suppliers_router
from app.api.routes.sub2api_instances import router as sub2api_instances_router
from app.api.routes.sub2api_imports import router as sub2api_imports_router
from app.api.routes.system_maintenance import router as system_maintenance_router
from app.api.routes.users import router as users_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(suppliers_router)
api_router.include_router(purchases_router)
api_router.include_router(cost_items_router)
api_router.include_router(revenues_router)
api_router.include_router(files_router)
api_router.include_router(sub2api_instances_router)
api_router.include_router(operations_platforms_router)
api_router.include_router(sub2api_imports_router)
api_router.include_router(accounts_router)
api_router.include_router(servers_router)
api_router.include_router(proxy_pools_router)
api_router.include_router(shop_monitors_router)
api_router.include_router(evaluation_batches_router)
api_router.include_router(account_evaluation_router)
api_router.include_router(dashboard_router)
api_router.include_router(reports_router)
api_router.include_router(audit_logs_router)
api_router.include_router(system_maintenance_router)
