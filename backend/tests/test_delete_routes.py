import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.api.routes import (
    accounts,
    cost_items,
    evaluations,
    operations_platforms,
    proxy_pools,
    purchases,
    revenues,
    servers,
    sub2api_instances,
    suppliers,
    users,
)


class DeleteRouteRegistrationTests(unittest.TestCase):
    def test_mutable_resources_register_delete_routes(self):
        expected_routes = [
            (accounts.router, "/api/accounts/{account_id}"),
            (cost_items.router, "/api/cost-items/{cost_item_id}"),
            (evaluations.router, "/api/evaluation-batches/{batch_id}"),
            (operations_platforms.router, "/api/operations-platforms/{platform_id}"),
            (proxy_pools.router, "/api/proxy-pools/{proxy_pool_id}"),
            (purchases.router, "/api/purchases/{purchase_id}"),
            (revenues.router, "/api/revenues/{revenue_id}"),
            (servers.router, "/api/servers/{server_id}"),
            (sub2api_instances.router, "/api/sub2api-instances/{instance_id}"),
            (suppliers.router, "/api/suppliers/{supplier_id}"),
            (users.router, "/api/users/{user_id}"),
        ]

        for router, path in expected_routes:
            with self.subTest(path=path):
                self.assertTrue(
                    any(
                        route.path == path and "DELETE" in route.methods
                        for route in router.routes
                    )
                )

    def test_accounts_register_bulk_delete_route(self):
        self.assertTrue(
            any(
                route.path == "/api/accounts/bulk-delete" and "POST" in route.methods
                for route in accounts.router.routes
            )
        )

    def test_account_delete_removes_dependents_before_account(self):
        account_id = uuid.uuid4()
        account = SimpleNamespace(id=account_id)
        db = MagicMock()

        accounts._delete_account_with_dependents(db, account)

        executed_sql = [str(call.args[0]) for call in db.execute.call_args_list]
        self.assertTrue(any("account_evaluations" in statement for statement in executed_sql))
        self.assertTrue(any("account_check_records" in statement for statement in executed_sql))
        self.assertTrue(any("sub2api_import_items" in statement for statement in executed_sql))
        self.assertTrue(any("account_items" in statement for statement in executed_sql))
        db.delete.assert_called_once_with(account)

    def test_operations_platforms_register_reveal_secret_route(self):
        self.assertTrue(
            any(
                route.path == "/api/operations-platforms/{platform_id}/reveal-secret"
                and "POST" in route.methods
                for route in operations_platforms.router.routes
            )
        )


if __name__ == "__main__":
    unittest.main()
