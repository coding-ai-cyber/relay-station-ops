import unittest
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.account import Account
from app.models.account_item import AccountItem
from app.services.sub2api_admin_adapter import (
    Sub2APIProbe,
    _account_lookup_keys,
    _check_targets_for_accounts,
    _select_accounts,
    run_admin_key_account_check,
)


class AccountLookupKeyTests(unittest.TestCase):
    def test_uses_only_instance_bound_remote_id(self):
        account = SimpleNamespace(
            sub2api_account_id="global-id-from-another-instance",
            account_no="ACC-001",
            login_account=None,
            authorized_email=None,
            bind_email=None,
            name=None,
        )

        without_binding = _account_lookup_keys(account, known_remote_id=None)
        with_binding = _account_lookup_keys(account, known_remote_id="instance-id")

        self.assertNotIn("global-id-from-another-instance", without_binding)
        self.assertIn("instance-id", with_binding)
        self.assertIn("acc-001", without_binding)


class AutoCheckPurchaseScopeTests(unittest.TestCase):
    def test_select_accounts_filters_by_purchase_id(self):
        purchase_id = uuid.uuid4()
        instance_id = uuid.uuid4()
        db = MagicMock()
        db.scalars.return_value.all.return_value = []

        _select_accounts(
            db=db,
            instance_id=instance_id,
            account_type=None,
            import_batch_no=None,
            purchase_id=purchase_id,
            include_only_operation=False,
        )

        statement = db.scalars.call_args.args[0]
        self.assertIn("accounts.purchase_id", str(statement))
        self.assertEqual(statement.compile().params["purchase_id_1"], purchase_id)

    def test_auto_check_records_purchase_scope_in_request_config(self):
        purchase_id = uuid.uuid4()
        instance = SimpleNamespace(
            id=uuid.uuid4(),
            name="Test instance",
            base_url="https://sub2api.example",
            last_probe_at=None,
            last_probe_status=None,
            last_probe_message=None,
            detected_accounts_path=None,
        )
        db = MagicMock()

        with (
            patch(
                "app.services.sub2api_admin_adapter.probe_sub2api_instance",
                return_value=Sub2APIProbe(False, "auth_failed", "Unauthorized"),
            ),
            patch("app.services.sub2api_admin_adapter._select_accounts", return_value=[]),
            patch("app.services.sub2api_admin_adapter._instance_remote_ids", return_value={}),
        ):
            batch = run_admin_key_account_check(
                db=db,
                instance=instance,
                checked_by=uuid.uuid4(),
                purchase_id=purchase_id,
            )

        self.assertEqual(batch.request_config["purchase_id"], str(purchase_id))

    def test_successful_check_redacts_remote_credentials_in_raw_response(self):
        account = Account(
            id=uuid.uuid4(),
            account_no="ACC-RED-A",
            account_type="openai",
            sub2api_instance_id=uuid.uuid4(),
            login_account="redacted@example.com",
            created_at=datetime(2026, 7, 16, tzinfo=UTC),
        )
        instance = SimpleNamespace(
            id=account.sub2api_instance_id,
            name="Test instance",
            base_url="https://sub2api.example",
            last_probe_at=None,
            last_probe_status=None,
            last_probe_message=None,
            detected_accounts_path=None,
        )
        db = MagicMock()
        records = []

        def add(item):
            if item.__class__.__name__ == "AccountCheckBatch":
                item.id = uuid.uuid4()
                item.alive_count = 0
                item.abnormal_count = 0
                item.status_401_count = 0
            records.append(item)

        db.add.side_effect = add

        with (
            patch(
                "app.services.sub2api_admin_adapter.probe_sub2api_instance",
                return_value=Sub2APIProbe(
                    True,
                    "ok",
                    "ok",
                    accounts_path="/api/v1/admin/accounts",
                    payload={
                        "data": {
                            "items": [
                                {
                                    "id": "remote-red-a",
                                    "name": "ACC-RED-A",
                                    "status": "active",
                                    "credentials": {"access_token": "plain-token"},
                                }
                            ]
                        }
                    },
                ),
            ),
            patch("app.services.sub2api_admin_adapter._select_accounts", return_value=[account]),
            patch("app.services.sub2api_admin_adapter._instance_remote_ids", return_value={}),
        ):
            run_admin_key_account_check(
                db=db,
                instance=instance,
                checked_by=uuid.uuid4(),
            )

        check_records = [item for item in records if item.__class__.__name__ == "AccountCheckRecord"]
        self.assertEqual(check_records[0].raw_response["credentials"], "[REDACTED]")

    def test_expands_account_details_into_check_targets(self):
        account = Account(
            id=uuid.uuid4(),
            account_no="PO-1-A001",
            account_type="openai",
            sub2api_instance_id=uuid.uuid4(),
            created_at=datetime(2026, 7, 16, tzinfo=UTC),
        )
        first = AccountItem(
            id=uuid.uuid4(),
            account_id=account.id,
            item_no="PO-1-A001-D001",
            item_index=1,
            email="first@example.com",
            platform="openai",
            remote_account_id="101",
        )
        second = AccountItem(
            id=uuid.uuid4(),
            account_id=account.id,
            item_no="PO-1-A001-D002",
            item_index=2,
            email="second@example.com",
            platform="openai",
            remote_account_id="102",
        )
        account.items = [second, first]

        targets = _check_targets_for_accounts([account])

        self.assertEqual([target.display_no for target in targets], ["PO-1-A001-D001", "PO-1-A001-D002"])
        self.assertEqual(targets[0].lookup_account.login_account, "first@example.com")
        self.assertEqual(targets[0].known_remote_id, "101")

    def test_auto_check_counts_account_details_individually(self):
        account = Account(
            id=uuid.uuid4(),
            account_no="PO-2-A001",
            account_type="openai",
            sub2api_instance_id=uuid.uuid4(),
            created_at=datetime(2026, 7, 16, tzinfo=UTC),
        )
        account.items = [
            AccountItem(
                id=uuid.uuid4(),
                account_id=account.id,
                item_no="PO-2-A001-D001",
                item_index=1,
                email="first@example.com",
                platform="openai",
            ),
            AccountItem(
                id=uuid.uuid4(),
                account_id=account.id,
                item_no="PO-2-A001-D002",
                item_index=2,
                email="second@example.com",
                platform="openai",
            ),
        ]
        instance = SimpleNamespace(
            id=account.sub2api_instance_id,
            name="Test instance",
            base_url="https://sub2api.example",
            last_probe_at=None,
            last_probe_status=None,
            last_probe_message=None,
            detected_accounts_path=None,
        )
        db = MagicMock()
        records = []

        def add(item):
            if item.__class__.__name__ == "AccountCheckBatch":
                item.id = uuid.uuid4()
                item.alive_count = 0
                item.abnormal_count = 0
                item.status_401_count = 0
            records.append(item)

        db.add.side_effect = add

        with (
            patch(
                "app.services.sub2api_admin_adapter.probe_sub2api_instance",
                return_value=Sub2APIProbe(
                    True,
                    "ok",
                    "ok",
                    accounts_path="/api/v1/admin/accounts",
                    payload={
                        "data": {
                            "items": [
                                {"id": "201", "name": "first@example.com", "status": "active"},
                                {"id": "202", "name": "second@example.com", "status": "active"},
                            ]
                        }
                    },
                ),
            ),
            patch("app.services.sub2api_admin_adapter._select_accounts", return_value=[account]),
            patch("app.services.sub2api_admin_adapter._instance_remote_ids", return_value={}),
        ):
            batch = run_admin_key_account_check(
                db=db,
                instance=instance,
                checked_by=uuid.uuid4(),
            )

        check_records = [item for item in records if item.__class__.__name__ == "AccountCheckRecord"]
        self.assertEqual(batch.total_count, 2)
        self.assertEqual(batch.alive_count, 2)
        self.assertEqual(len(check_records), 2)
        self.assertEqual([record.remark for record in check_records], ["PO-2-A001-D001", "PO-2-A001-D002"])
        self.assertEqual([item.status for item in account.items], ["available", "available"])
        self.assertTrue(all(item.last_checked_at is not None for item in account.items))
        self.assertTrue(all(item.last_seen_alive_at is not None for item in account.items))
        self.assertEqual([item.last_sub2api_status_code for item in account.items], [200, 200])

    def test_auto_check_maps_remote_rate_limit_to_detail_status(self):
        account = Account(
            id=uuid.uuid4(),
            account_no="PO-3-A001",
            account_type="openai",
            sub2api_instance_id=uuid.uuid4(),
            created_at=datetime(2026, 7, 16, tzinfo=UTC),
        )
        account.items = [
            AccountItem(
                id=uuid.uuid4(),
                account_id=account.id,
                item_no="PO-3-A001-D001",
                item_index=1,
                email="limited@example.com",
                platform="openai",
            )
        ]
        instance = SimpleNamespace(
            id=account.sub2api_instance_id,
            name="Test instance",
            base_url="https://sub2api.example",
            last_probe_at=None,
            last_probe_status=None,
            last_probe_message=None,
            detected_accounts_path=None,
        )
        db = MagicMock()
        records = []

        def add(item):
            if item.__class__.__name__ == "AccountCheckBatch":
                item.id = uuid.uuid4()
                item.alive_count = 0
                item.abnormal_count = 0
                item.status_401_count = 0
                item.status_429_count = 0
            records.append(item)

        db.add.side_effect = add

        with (
            patch(
                "app.services.sub2api_admin_adapter.probe_sub2api_instance",
                return_value=Sub2APIProbe(
                    True,
                    "ok",
                    "ok",
                    accounts_path="/api/v1/admin/accounts",
                    payload={
                        "data": {
                            "items": [
                                {
                                    "id": "301",
                                    "name": "limited@example.com",
                                    "status": "active",
                                    "schedulable": False,
                                    "rate_limit_reset_at": "2026-07-17T18:00:00+08:00",
                                }
                            ]
                        }
                    },
                ),
            ),
            patch("app.services.sub2api_admin_adapter._select_accounts", return_value=[account]),
            patch("app.services.sub2api_admin_adapter._instance_remote_ids", return_value={}),
        ):
            batch = run_admin_key_account_check(
                db=db,
                instance=instance,
                checked_by=uuid.uuid4(),
            )

        check_record = next(item for item in records if item.__class__.__name__ == "AccountCheckRecord")
        self.assertEqual(batch.abnormal_count, 1)
        self.assertEqual(batch.status_429_count, 1)
        self.assertEqual(account.items[0].status, "rate_limited")
        self.assertEqual(account.items[0].last_sub2api_error_code, "rate_limited")
        self.assertIn("2026-07-17T18:00:00+08:00", account.items[0].last_sub2api_message)
        self.assertEqual(check_record.sub2api_status, "active")
        self.assertFalse(check_record.is_alive)

    def test_failed_probe_redacts_raw_response_payload(self):
        account = Account(
            id=uuid.uuid4(),
            account_no="ACC-RED-B",
            account_type="openai",
            sub2api_instance_id=uuid.uuid4(),
            created_at=datetime(2026, 7, 16, tzinfo=UTC),
        )
        instance = SimpleNamespace(
            id=account.sub2api_instance_id,
            name="Test instance",
            base_url="https://sub2api.example",
            last_probe_at=None,
            last_probe_status=None,
            last_probe_message=None,
            detected_accounts_path=None,
        )
        db = MagicMock()
        records = []

        def add(item):
            if item.__class__.__name__ == "AccountCheckBatch":
                item.id = uuid.uuid4()
                item.alive_count = 0
                item.abnormal_count = 0
                item.status_401_count = 0
            records.append(item)

        db.add.side_effect = add

        with (
            patch(
                "app.services.sub2api_admin_adapter.probe_sub2api_instance",
                return_value=Sub2APIProbe(
                    False,
                    "auth_failed",
                    "Unauthorized",
                    payload={"credentials": {"api_key": "plain-key"}},
                ),
            ),
            patch("app.services.sub2api_admin_adapter._select_accounts", return_value=[account]),
            patch("app.services.sub2api_admin_adapter._instance_remote_ids", return_value={}),
        ):
            run_admin_key_account_check(
                db=db,
                instance=instance,
                checked_by=uuid.uuid4(),
            )

        check_records = [item for item in records if item.__class__.__name__ == "AccountCheckRecord"]
        self.assertEqual(check_records[0].raw_response["credentials"], "[REDACTED]")


if __name__ == "__main__":
    unittest.main()
