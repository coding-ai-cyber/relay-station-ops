import unittest
import uuid
import inspect
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import ANY, MagicMock, patch

from fastapi import HTTPException
from sqlalchemy.exc import OperationalError

from app.api.routes.sub2api_imports import _prepare_retry_source, _resolve_import_accounts
from app.api.routes.sub2api_instances import router as instance_router
from app.schemas.sub2api_import import Sub2APIImportCreate


class ResolveImportAccountsTests(unittest.TestCase):
    def test_accepts_purchase_scope_without_account_ids(self):
        payload = Sub2APIImportCreate(
            instance_id=uuid.uuid4(),
            purchase_id=uuid.uuid4(),
            group_ids=[1],
        )

        self.assertIsNotNone(payload.purchase_id)
        self.assertEqual(payload.account_ids, [])
        self.assertFalse(payload.select_all)

    def test_select_all_queries_accounts_on_the_server(self):
        expected = [SimpleNamespace(id=uuid.uuid4()), SimpleNamespace(id=uuid.uuid4())]
        db = MagicMock()
        db.scalars.return_value.all.return_value = expected
        payload = Sub2APIImportCreate(
            instance_id=uuid.uuid4(),
            select_all=True,
            group_ids=[1],
        )

        result = _resolve_import_accounts(db, payload)

        self.assertEqual(result, expected)
        db.scalars.assert_called_once()

    def test_selected_scope_deduplicates_ids_before_loading(self):
        account_id = uuid.uuid4()
        payload = Sub2APIImportCreate(
            instance_id=uuid.uuid4(),
            account_ids=[account_id, account_id],
            group_ids=[1],
        )

        with patch(
            "app.api.routes.sub2api_imports._accounts_in_order",
            return_value=[SimpleNamespace(id=account_id)],
        ) as loader:
            result = _resolve_import_accounts(MagicMock(), payload)

        self.assertEqual([item.id for item in result], [account_id])
        loader.assert_called_once_with(ANY, [account_id])

    def test_purchase_scope_queries_only_bound_accounts_from_purchase(self):
        purchase_id = uuid.uuid4()
        expected = [SimpleNamespace(id=uuid.uuid4())]
        db = MagicMock()
        db.scalars.return_value.all.return_value = expected
        payload = Sub2APIImportCreate(
            instance_id=uuid.uuid4(),
            purchase_id=purchase_id,
            group_ids=[1],
        )

        result = _resolve_import_accounts(db, payload)

        self.assertEqual(result, expected)
        statement = str(db.scalars.call_args.args[0])
        self.assertIn("accounts.purchase_id", statement)
        self.assertIn("accounts.raw_credentials_encrypted IS NOT NULL", statement)
        self.assertEqual(db.scalars.call_args.args[0].compile().params["purchase_id_1"], purchase_id)

    def test_purchase_scope_rejects_when_no_bound_accounts_are_available(self):
        db = MagicMock()
        db.scalars.return_value.all.return_value = []
        payload = Sub2APIImportCreate(
            instance_id=uuid.uuid4(),
            purchase_id=uuid.uuid4(),
            group_ids=[1],
        )

        with self.assertRaises(HTTPException) as raised:
            _resolve_import_accounts(db, payload)

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail, "No bound accounts available for this purchase")


class PrepareRetrySourceTests(unittest.TestCase):
    def test_rejects_recent_running_batch(self):
        source = SimpleNamespace(
            id=uuid.uuid4(),
            status="running",
            started_at=datetime.now(UTC) - timedelta(minutes=5),
            items=[],
        )

        with self.assertRaises(HTTPException) as raised:
            _prepare_retry_source(MagicMock(), source)

        self.assertEqual(raised.exception.status_code, 409)

    def test_recovers_stale_batch_before_retry(self):
        pending = SimpleNamespace(status="pending", error_message=None)
        source = SimpleNamespace(
            id=uuid.uuid4(),
            status="running",
            started_at=datetime.now(UTC) - timedelta(minutes=20),
            items=[pending],
            success_count=0,
            failed_count=0,
            skipped_count=0,
            finished_at=None,
        )
        db = MagicMock()
        db.scalar.return_value = None

        _prepare_retry_source(db, source)

        self.assertEqual(source.status, "failed")
        self.assertEqual(pending.status, "failed")
        db.commit.assert_called_once()

    def test_rejects_batch_that_already_has_a_direct_retry(self):
        source = SimpleNamespace(
            id=uuid.uuid4(),
            status="failed",
            started_at=datetime.now(UTC) - timedelta(minutes=20),
            items=[],
        )
        db = MagicMock()
        db.scalar.return_value = SimpleNamespace(batch_no="S2IMP-existing")

        with self.assertRaises(HTTPException) as raised:
            _prepare_retry_source(db, source)

        self.assertEqual(raised.exception.status_code, 409)

    def test_rejects_retry_when_active_import_holds_the_batch_lock(self):
        source = SimpleNamespace(
            id=uuid.uuid4(),
            status="failed",
            started_at=datetime.now(UTC) - timedelta(minutes=20),
            items=[],
        )
        db = MagicMock()
        db.scalar.return_value = None
        db.refresh.side_effect = OperationalError("SELECT", {}, RuntimeError("locked"))

        with self.assertRaises(HTTPException) as raised:
            _prepare_retry_source(db, source)

        self.assertEqual(raised.exception.status_code, 409)
        self.assertIn("running", raised.exception.detail)
        db.rollback.assert_called_once()


class Sub2APIInstancePermissionTests(unittest.TestCase):
    def test_only_admin_can_create_or_update_instances(self):
        protected_routes = [
            route
            for route in instance_router.routes
            if (route.path, next(iter(route.methods)))
            in {
                ("/api/sub2api-instances", "POST"),
                ("/api/sub2api-instances/{instance_id}", "PATCH"),
            }
        ]

        self.assertEqual(len(protected_routes), 2)
        for route in protected_routes:
            role_dependency = next(
                dependency
                for dependency in route.dependant.dependencies
                if dependency.name == "current_user"
            )
            allowed_roles = inspect.getclosurevars(role_dependency.call).nonlocals["allowed_roles"]
            self.assertEqual(allowed_roles, {"admin"})


if __name__ == "__main__":
    unittest.main()
