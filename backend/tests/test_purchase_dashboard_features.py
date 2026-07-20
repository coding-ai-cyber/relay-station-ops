import re
import unittest
import uuid
from datetime import UTC, date
from datetime import datetime, timezone
from decimal import Decimal

from app.api.routes.dashboard import resolve_dashboard_period
from app.api.routes.purchases import _make_account_assets_from_purchase, generate_purchase_no
from app.models.account import Account
from app.models.purchase import Purchase
from app.schemas.purchase import PurchaseCreate
from app.schemas.purchase import PurchaseRead


class PurchaseNumberTests(unittest.TestCase):
    def test_blank_purchase_number_is_treated_as_missing(self):
        payload = PurchaseCreate(
            purchase_no="",
            purchase_type="account",
            product_name="OpenAI free accounts",
            purchased_at=date(2026, 7, 14),
        )

        self.assertIsNone(payload.purchase_no)

    def test_generates_purchase_number_with_current_date_prefix(self):
        purchase_no = generate_purchase_no(today=date(2026, 7, 14))

        self.assertRegex(purchase_no, r"^PO-20260714-[A-Z0-9]{6}$")

    def test_generates_uppercase_random_suffix(self):
        numbers = {generate_purchase_no(today=date(2026, 7, 14)) for _ in range(20)}

        self.assertTrue(all(re.match(r"^PO-20260714-[A-Z0-9]{6}$", item) for item in numbers))
        self.assertGreater(len(numbers), 1)


class PurchaseAssetStatusTests(unittest.TestCase):
    def test_read_model_marks_purchase_with_generated_assets(self):
        sub2api_instance_id = uuid.uuid4()
        purchase = Purchase(
            id=uuid.uuid4(),
            purchase_no="PO-20260714-ASSET1",
            purchase_type="account",
            product_name="OpenAI account batch",
            quantity=Decimal("2"),
            unit_price=Decimal("10"),
            total_price=Decimal("20"),
            currency="CNY",
            purchased_at=date(2026, 7, 14),
            include_all_cost=True,
            include_real_cost=False,
            cost_status="testing",
            created_at=datetime(2026, 7, 14, tzinfo=timezone.utc),
            updated_at=datetime(2026, 7, 14, tzinfo=timezone.utc),
        )
        purchase.accounts = [
            Account(
                account_no="PO-20260714-ASSET1-A001",
                account_type="openai",
                raw_credentials_encrypted="encrypted-a",
                sub2api_instance_id=sub2api_instance_id,
                status="available",
            ),
            Account(
                account_no="PO-20260714-ASSET1-A002",
                account_type="openai",
                raw_credentials_encrypted="encrypted-b",
                status="api_401",
                first_abnormal_at=datetime(2026, 7, 14, tzinfo=timezone.utc),
            ),
            Account(
                account_no="PO-20260714-ASSET1-A003",
                account_type="openai",
                status="pending_test",
            ),
        ]

        read_model = PurchaseRead.model_validate(purchase)

        self.assertTrue(read_model.asset_generated)
        self.assertEqual(read_model.generated_asset_count, 3)
        self.assertEqual(read_model.bound_account_count, 2)
        self.assertEqual(read_model.imported_account_count, 1)
        self.assertEqual(read_model.abnormal_account_count, 1)

    def test_account_purchase_generates_single_asset_record_for_large_quantity(self):
        purchase_id = uuid.uuid4()
        purchase = Purchase(
            id=purchase_id,
            purchase_no="PO-20260715-B3CWWP",
            purchase_type="account",
            product_name="100 account JSON bundle",
            product_type="openai",
            quantity=Decimal("100"),
            unit_price=Decimal("0.60"),
            total_price=Decimal("60.00"),
            currency="CNY",
            purchased_at=date(2026, 7, 15),
            include_all_cost=True,
            include_real_cost=True,
            cost_status="valid",
        )

        accounts = _make_account_assets_from_purchase(purchase)

        self.assertEqual(len(accounts), 1)
        account = accounts[0]
        self.assertEqual(account.account_no, "PO-20260715-B3CWWP-A001")
        self.assertEqual(account.purchase_id, purchase_id)
        self.assertEqual(account.account_type, "openai")
        self.assertEqual(account.cost_unit_price, Decimal("0.60"))
        self.assertEqual(account.raw_payload["source"], "purchase_asset_generation")
        self.assertEqual(account.raw_payload["purchase_quantity"], "100")
        self.assertEqual(account.raw_payload["asset_index"], 1)

    def test_account_purchase_generated_asset_uses_expiry_date(self):
        expires_at = datetime(2026, 8, 16, tzinfo=UTC)
        purchase = Purchase(
            id=uuid.uuid4(),
            purchase_no="PO-20260716-EXPIRY",
            purchase_type="account",
            product_name="expiring account bundle",
            product_type="openai",
            quantity=Decimal("10"),
            unit_price=Decimal("1"),
            total_price=Decimal("10"),
            currency="CNY",
            purchased_at=date(2026, 7, 16),
            include_all_cost=True,
            include_real_cost=True,
            cost_status="valid",
        )

        accounts = _make_account_assets_from_purchase(purchase, expired_at=expires_at)

        self.assertEqual(accounts[0].expired_at, expires_at)

    def test_account_purchase_rejects_fractional_quantity_for_assets(self):
        purchase = Purchase(
            id=uuid.uuid4(),
            purchase_no="PO-20260715-FRACTN",
            purchase_type="account",
            product_name="fractional bundle",
            quantity=Decimal("1.5"),
            unit_price=Decimal("1"),
            total_price=Decimal("1.5"),
            currency="CNY",
            purchased_at=date(2026, 7, 15),
            include_all_cost=True,
            include_real_cost=True,
            cost_status="valid",
        )

        with self.assertRaises(ValueError):
            _make_account_assets_from_purchase(purchase)


class DashboardPeriodTests(unittest.TestCase):
    def test_uses_inclusive_custom_date_range_when_provided(self):
        start, end = resolve_dashboard_period(
            year=2026,
            month=7,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )

        self.assertEqual(start, date(2026, 1, 1))
        self.assertEqual(end, date(2026, 4, 1))

    def test_falls_back_to_month_bounds_without_custom_range(self):
        start, end = resolve_dashboard_period(year=2026, month=7)

        self.assertEqual(start, date(2026, 7, 1))
        self.assertEqual(end, date(2026, 8, 1))


if __name__ == "__main__":
    unittest.main()
