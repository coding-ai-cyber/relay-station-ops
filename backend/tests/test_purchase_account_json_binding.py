import unittest
import base64
import json
import uuid
from datetime import date
from decimal import Decimal

from app.core.security import field_cipher
from app.models.account import Account
from app.models.account_item import AccountItem
from app.models.purchase import Purchase
from app.services.account_credentials import decrypt_raw_credentials
from app.services.purchase_account_json import (
    bind_purchase_account_json,
    bind_json_items_to_accounts,
    extract_purchase_json_accounts,
)


def _jwt_with_payload(payload: dict) -> str:
    encoded_payload = base64.urlsafe_b64encode(
        json.dumps(payload).encode("utf-8")
    ).decode("ascii").rstrip("=")
    return f"header.{encoded_payload}.signature"


class PurchaseAccountJsonParsingTests(unittest.TestCase):
    def test_extracts_accounts_from_sub2api_root_object(self):
        payload = {"accounts": [{"name": "a"}, {"name": "b"}]}

        self.assertEqual(extract_purchase_json_accounts(payload), [{"name": "a"}, {"name": "b"}])

    def test_extracts_accounts_from_root_array(self):
        payload = [{"name": "a"}]

        self.assertEqual(extract_purchase_json_accounts(payload), [{"name": "a"}])

    def test_extracts_accounts_from_sub2api_nested_data_object(self):
        payload = {"data": {"accounts": [{"name": "a"}]}}

        self.assertEqual(extract_purchase_json_accounts(payload), [{"name": "a"}])

    def test_rejects_payload_without_accounts(self):
        with self.assertRaises(ValueError):
            extract_purchase_json_accounts({"items": []})

    def test_rejects_mixed_invalid_account_entries(self):
        with self.assertRaises(ValueError):
            extract_purchase_json_accounts([
                {"name": "a"},
                None,
                {"name": "c"},
            ])


class PurchaseAccountJsonBindingTests(unittest.TestCase):
    def test_binds_credentials_and_email_to_existing_assets(self):
        purchase = Purchase(
            id=uuid.uuid4(),
            purchase_no="PO-20260716-K12",
            purchase_type="account",
            product_name="K12",
            quantity=Decimal("2"),
            unit_price=Decimal("1"),
            total_price=Decimal("2"),
            currency="USDT",
            purchased_at=date(2026, 7, 16),
            include_all_cost=True,
            include_real_cost=True,
            cost_status="testing",
        )
        accounts = [
            Account(id=uuid.uuid4(), account_no="PO-20260716-K12-A001", purchase_id=purchase.id, account_type="k12"),
            Account(id=uuid.uuid4(), account_no="PO-20260716-K12-A002", purchase_id=purchase.id, account_type="k12"),
        ]
        json_accounts = [
            {
                "name": "remote-a",
                "platform": "openai",
                "type": "oauth",
                "credentials": {
                    "access_token": "token-a",
                    "email": "a@example.com",
                    "plan_type": "plus",
                    "account_id": "remote-a-id",
                },
            }
        ]

        result = bind_json_items_to_accounts(
            purchase=purchase,
            accounts=accounts,
            json_accounts=json_accounts,
            import_batch_no="JSON-202607160001",
            file_id=None,
            overwrite_existing=False,
            remark="sample",
        )

        self.assertEqual(result.bound_count, 1)
        self.assertEqual(result.skipped_count, 0)
        self.assertEqual(accounts[0].login_account, "a@example.com")
        self.assertEqual(accounts[0].authorized_email, "a@example.com")
        self.assertEqual(accounts[0].sub2api_account_id, "remote-a-id")
        self.assertEqual(accounts[0].account_type, "openai")
        self.assertEqual(accounts[0].plan_type, "plus")
        self.assertEqual(accounts[0].raw_payload["credentials"], "[REDACTED]")
        self.assertEqual(decrypt_raw_credentials(accounts[0].raw_credentials_encrypted)["access_token"], "token-a")
        self.assertIsNone(accounts[1].login_account)

    def test_does_not_overwrite_existing_credentials_by_default(self):
        purchase = Purchase(id=uuid.uuid4(), purchase_no="PO-1", purchase_type="account")
        account = Account(
            id=uuid.uuid4(),
            account_no="PO-1-A001",
            purchase_id=purchase.id,
            account_type="openai",
            raw_credentials_encrypted=field_cipher.encrypt('{"access_token":"old"}'),
        )

        result = bind_json_items_to_accounts(
            purchase=purchase,
            accounts=[account],
            json_accounts=[{"credentials": {"access_token": "new", "email": "new@example.com"}}],
            import_batch_no="JSON-1",
            file_id=None,
            overwrite_existing=False,
            remark=None,
        )

        self.assertEqual(result.bound_count, 0)
        self.assertEqual(result.skipped_count, 1)
        self.assertEqual(decrypt_raw_credentials(account.raw_credentials_encrypted)["access_token"], "old")

    def test_rejects_json_exceeding_unbound_capacity_without_mutating_assets(self):
        purchase = Purchase(id=uuid.uuid4(), purchase_no="PO-2", purchase_type="account")
        accounts = [
            Account(
                id=uuid.uuid4(),
                account_no="PO-2-A001",
                purchase_id=purchase.id,
                account_type="openai",
                raw_payload={"source": "purchase_asset_generation"},
            ),
            Account(
                id=uuid.uuid4(),
                account_no="PO-2-A002",
                purchase_id=purchase.id,
                account_type="openai",
                raw_credentials_encrypted=field_cipher.encrypt('{"access_token":"old"}'),
            ),
            Account(
                id=uuid.uuid4(),
                account_no="PO-2-A003",
                purchase_id=purchase.id,
                account_type="openai",
                raw_payload={"source": "purchase_asset_generation"},
            ),
        ]
        initial_values = [
            (
                account.raw_payload,
                account.raw_credentials_encrypted,
                account.login_account,
                account.authorized_email,
                account.sub2api_account_id,
                account.account_type,
                account.plan_type,
                account.import_file_id,
                account.import_batch_no,
                account.remark,
            )
            for account in accounts
        ]

        with self.assertRaises(ValueError):
            bind_json_items_to_accounts(
                purchase=purchase,
                accounts=accounts,
                json_accounts=[
                    {"credentials": {"access_token": "new-a"}},
                    {"credentials": {"access_token": "new-b"}},
                    {"credentials": {"access_token": "new-c"}},
                ],
                import_batch_no="JSON-2",
                file_id=None,
                overwrite_existing=False,
                remark=None,
            )

        self.assertEqual(
            [
                (
                    account.raw_payload,
                    account.raw_credentials_encrypted,
                    account.login_account,
                    account.authorized_email,
                    account.sub2api_account_id,
                    account.account_type,
                    account.plan_type,
                    account.import_file_id,
                    account.import_batch_no,
                    account.remark,
                )
                for account in accounts
            ],
            initial_values,
        )

    def test_rejects_json_count_above_total_account_assets(self):
        purchase = Purchase(id=uuid.uuid4(), purchase_no="PO-3", purchase_type="account")
        account = Account(id=uuid.uuid4(), account_no="PO-3-A001", purchase_id=purchase.id, account_type="openai")

        with self.assertRaises(ValueError):
            bind_json_items_to_accounts(
                purchase=purchase,
                accounts=[account],
                json_accounts=[{"credentials": {"access_token": "a"}}, {"credentials": {"access_token": "b"}}],
                import_batch_no="JSON-3",
                file_id=None,
                overwrite_existing=False,
                remark=None,
            )

    def test_overwrite_binds_all_assets_in_account_number_order(self):
        purchase = Purchase(id=uuid.uuid4(), purchase_no="PO-4", purchase_type="account")
        first = Account(
            id=uuid.uuid4(),
            account_no="PO-4-A001",
            purchase_id=purchase.id,
            account_type="openai",
            raw_credentials_encrypted=field_cipher.encrypt('{"access_token":"old-first"}'),
        )
        second = Account(
            id=uuid.uuid4(),
            account_no="PO-4-A002",
            purchase_id=purchase.id,
            account_type="openai",
            raw_credentials_encrypted=field_cipher.encrypt('{"access_token":"old-second"}'),
        )

        result = bind_json_items_to_accounts(
            purchase=purchase,
            accounts=[second, first],
            json_accounts=[
                {"credentials": {"access_token": "new-first"}},
                {"credentials": {"access_token": "new-second"}},
            ],
            import_batch_no="JSON-4",
            file_id=None,
            overwrite_existing=True,
            remark=None,
        )

        self.assertEqual(result.bound_count, 2)
        self.assertEqual(decrypt_raw_credentials(first.raw_credentials_encrypted)["access_token"], "new-first")
        self.assertEqual(decrypt_raw_credentials(second.raw_credentials_encrypted)["access_token"], "new-second")

    def test_prefers_credentials_email_and_account_id_over_fallback_fields(self):
        purchase = Purchase(id=uuid.uuid4(), purchase_no="PO-5", purchase_type="account")
        account = Account(id=uuid.uuid4(), account_no="PO-5-A001", purchase_id=purchase.id, account_type="openai")

        bind_json_items_to_accounts(
            purchase=purchase,
            accounts=[account],
            json_accounts=[
                {
                    "email": "top-level@example.com",
                    "account": "top-level-account@example.com",
                    "username": "top-level-username@example.com",
                    "id": "top-level-id",
                    "account_id": "top-level-account-id",
                    "credentials": {
                        "access_token": "token",
                        "email": "credential@example.com",
                        "account_id": "credential-account-id",
                        "chatgpt_account_id": "credential-chatgpt-account-id",
                    },
                }
            ],
            import_batch_no="JSON-5",
            file_id=None,
            overwrite_existing=False,
            remark=None,
        )

        self.assertEqual(account.login_account, "credential@example.com")
        self.assertEqual(account.authorized_email, "credential@example.com")
        self.assertEqual(account.sub2api_account_id, "credential-account-id")

    def test_extracts_email_from_openai_access_token_profile_claim(self):
        purchase = Purchase(id=uuid.uuid4(), purchase_no="PO-6", purchase_type="account")
        account = Account(id=uuid.uuid4(), account_no="PO-6-A001", purchase_id=purchase.id, account_type="openai")
        access_token = _jwt_with_payload({
            "https://api.openai.com/profile": {
                "email": "jwt-profile@example.com",
            },
        })

        bind_json_items_to_accounts(
            purchase=purchase,
            accounts=[account],
            json_accounts=[{"credentials": {"access_token": access_token}}],
            import_batch_no="JSON-6",
            file_id=None,
            overwrite_existing=False,
            remark=None,
        )

        self.assertEqual(account.login_account, "jwt-profile@example.com")
        self.assertEqual(account.authorized_email, "jwt-profile@example.com")

    def test_skips_items_without_importable_credentials(self):
        purchase = Purchase(id=uuid.uuid4(), purchase_no="PO-6", purchase_type="account")
        account = Account(id=uuid.uuid4(), account_no="PO-6-A001", purchase_id=purchase.id, account_type="openai")

        result = bind_json_items_to_accounts(
            purchase=purchase,
            accounts=[account],
            json_accounts=[{"email": "no-token@example.com", "platform": "openai"}],
            import_batch_no="JSON-6",
            file_id=None,
            overwrite_existing=False,
            remark=None,
        )

        self.assertEqual(result.bound_count, 0)
        self.assertEqual(result.skipped_count, 1)
        self.assertIsNone(account.raw_credentials_encrypted)
        self.assertIsNone(account.import_batch_no)
        self.assertEqual(result.items[0].status, "skipped")

    def test_batch_asset_creates_one_detail_per_json_account(self):
        purchase = Purchase(id=uuid.uuid4(), purchase_no="PO-7", purchase_type="account")
        account = Account(id=uuid.uuid4(), account_no="PO-7-A001", purchase_id=purchase.id, account_type="openai")
        account_items: list[AccountItem] = []

        result = bind_json_items_to_accounts(
            purchase=purchase,
            accounts=[account],
            account_items=account_items,
            json_accounts=[
                {
                    "platform": "openai",
                    "credentials": {
                        "access_token": "token-a",
                        "email": "a@example.com",
                        "account_id": "remote-a",
                        "plan_type": "plus",
                    },
                },
                {
                    "platform": "claude",
                    "credentials": {
                        "access_token": "token-b",
                        "email": "b@example.com",
                        "account_id": "remote-b",
                    },
                },
            ],
            import_batch_no="JSON-7",
            file_id=None,
            overwrite_existing=False,
            remark="detail import",
        )

        self.assertEqual(result.bound_count, 2)
        self.assertEqual(result.skipped_count, 0)
        self.assertEqual([item.item_no for item in account_items], ["PO-7-A001-D001", "PO-7-A001-D002"])
        self.assertEqual([item.email for item in account_items], ["a@example.com", "b@example.com"])
        self.assertEqual([item.platform for item in account_items], ["openai", "claude"])
        self.assertEqual([item.remote_account_id for item in account_items], ["remote-a", "remote-b"])
        self.assertEqual(account_items[0].plan_type, "plus")
        self.assertEqual(account_items[0].raw_payload["credentials"], "[REDACTED]")
        self.assertEqual(decrypt_raw_credentials(account_items[0].raw_credentials_encrypted)["access_token"], "token-a")
        self.assertEqual(account.login_account, "a@example.com")
        self.assertEqual(account.raw_payload["detail_count"], 2)

    def test_json_detail_does_not_override_main_account_type_or_plan(self):
        purchase = Purchase(id=uuid.uuid4(), purchase_no="PO-8", purchase_type="account")
        account = Account(
            id=uuid.uuid4(),
            account_no="PO-8-A001",
            purchase_id=purchase.id,
            account_type="plus",
            plan_type="plus",
        )
        account_items: list[AccountItem] = []

        bind_json_items_to_accounts(
            purchase=purchase,
            accounts=[account],
            account_items=account_items,
            json_accounts=[
                {
                    "platform": "openai",
                    "credentials": {
                        "access_token": "token-a",
                        "email": "a@example.com",
                        "plan_type": "free",
                    },
                }
            ],
            import_batch_no="JSON-8",
            file_id=None,
            overwrite_existing=False,
            remark=None,
        )

        self.assertEqual(account.account_type, "plus")
        self.assertEqual(account.plan_type, "plus")
        self.assertEqual(account_items[0].plan_type, "free")

    def test_manual_type_selection_overrides_json_platform_and_plan(self):
        purchase = Purchase(id=uuid.uuid4(), purchase_no="PO-9", purchase_type="account")
        account = Account(
            id=uuid.uuid4(),
            account_no="PO-9-A001",
            purchase_id=purchase.id,
            account_type="other",
        )
        account_items: list[AccountItem] = []

        bind_json_items_to_accounts(
            purchase=purchase,
            accounts=[account],
            account_items=account_items,
            json_accounts=[
                {
                    "platform": "claude",
                    "credentials": {
                        "access_token": "token-a",
                        "email": "a@example.com",
                        "plan_type": "free",
                    },
                }
            ],
            import_batch_no="JSON-9",
            file_id=None,
            overwrite_existing=False,
            remark=None,
            account_type="OpenAI",
            plan_type="plus",
        )

        self.assertEqual(account.account_type, "OpenAI")
        self.assertEqual(account.plan_type, "plus")
        self.assertEqual(account_items[0].platform, "OpenAI")
        self.assertEqual(account_items[0].plan_type, "plus")


class PurchaseAccountJsonAutoAssetTests(unittest.TestCase):
    def test_binding_json_auto_creates_account_asset_when_missing(self):
        class FakeScalarResult:
            def __init__(self, values):
                self.values = values

            def all(self):
                return self.values

        class FakeSession:
            def __init__(self):
                self.accounts: list[Account] = []
                self.account_items: list[AccountItem] = []

            def scalars(self, statement):
                statement_text = str(statement)
                if "account_items" in statement_text:
                    return FakeScalarResult(self.account_items)
                return FakeScalarResult(self.accounts)

            def add_all(self, values):
                for value in values:
                    if isinstance(value, Account):
                        self.accounts.append(value)
                    elif isinstance(value, AccountItem):
                        self.account_items.append(value)

            def delete(self, value):
                self.account_items.remove(value)

            def flush(self):
                return None

            def commit(self):
                return None

        purchase = Purchase(
            id=uuid.uuid4(),
            purchase_no="PO-20260717-K3PFJ3",
            purchase_type="account",
            product_name="plus",
            product_type="openai",
            quantity=Decimal("2"),
            unit_price=Decimal("1"),
            total_price=Decimal("2"),
            currency="CNY",
            purchased_at=date(2026, 7, 17),
            include_all_cost=True,
            include_real_cost=True,
            cost_status="testing",
        )
        db = FakeSession()

        result = bind_purchase_account_json(
            db=db,
            purchase=purchase,
            payload={"accounts": [{"credentials": {"access_token": "token", "email": "a@example.com"}}]},
            file_id=None,
            overwrite_existing=False,
            remark=None,
        )

        self.assertEqual(result.bound_count, 1)
        self.assertEqual(len(db.accounts), 1)
        self.assertEqual(len(db.account_items), 1)
        self.assertEqual(db.accounts[0].account_no, "PO-20260717-K3PFJ3-A001")

    def test_overwrite_rejects_non_importable_json_before_deleting_existing_details(self):
        class FakeScalarResult:
            def __init__(self, values):
                self.values = values

            def all(self):
                return self.values

        class FakeSession:
            def __init__(self, account: Account, item: AccountItem):
                self.accounts = [account]
                self.account_items = [item]
                self.deleted: list[AccountItem] = []

            def scalars(self, statement):
                statement_text = str(statement)
                if "account_items" in statement_text:
                    return FakeScalarResult(self.account_items)
                return FakeScalarResult(self.accounts)

            def add_all(self, values):
                for value in values:
                    if isinstance(value, AccountItem):
                        self.account_items.append(value)

            def delete(self, value):
                self.deleted.append(value)
                self.account_items.remove(value)

            def flush(self):
                return None

            def commit(self):
                return None

        purchase = Purchase(
            id=uuid.uuid4(),
            purchase_no="PO-20260717-K3PFJ3",
            purchase_type="account",
            product_name="plus",
            product_type="openai",
            quantity=Decimal("1"),
            unit_price=Decimal("1"),
            total_price=Decimal("1"),
            currency="CNY",
            purchased_at=date(2026, 7, 17),
            include_all_cost=True,
            include_real_cost=True,
            cost_status="testing",
        )
        account = Account(
            id=uuid.uuid4(),
            account_no="PO-20260717-K3PFJ3-A001",
            purchase_id=purchase.id,
            account_type="openai",
        )
        item = AccountItem(
            account_id=account.id,
            purchase_id=purchase.id,
            item_no="PO-20260717-K3PFJ3-A001-D001",
            item_index=1,
            status="bound",
            raw_credentials_encrypted=field_cipher.encrypt('{"access_token":"old"}'),
        )
        db = FakeSession(account, item)

        with self.assertRaisesRegex(ValueError, "without importable credentials"):
            bind_purchase_account_json(
                db=db,
                purchase=purchase,
                payload={"accounts": [{"credentials": "[REDACTED]"}]},
                file_id=None,
                overwrite_existing=True,
                remark=None,
            )

        self.assertEqual(db.account_items, [item])
        self.assertEqual(db.deleted, [])


if __name__ == "__main__":
    unittest.main()
