import unittest
import uuid
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.revenue import Revenue
from app.services.sub2api_revenue_sync import (
    Sub2APIRevenueCandidate,
    normalize_sub2api_revenue,
    sync_sub2api_revenues_for_instance,
)


class Sub2APIRevenueNormalizeTests(unittest.TestCase):
    def test_normalizes_common_order_payload(self):
        candidate = normalize_sub2api_revenue(
            {
                "id": 12345,
                "out_trade_no": "sub2_20260711DBAejiji",
                "user_email": "buyer@example.com",
                "amount": "19.90",
                "currency": "USDT",
                "paid_at": "2026-07-16T08:30:00Z",
                "status": "paid",
                "payment_method": "stripe",
            }
        )

        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.remote_order_no, "sub2_20260711DBAejiji")
        self.assertEqual(candidate.customer, "buyer@example.com")
        self.assertEqual(candidate.amount, Decimal("19.90"))
        self.assertEqual(candidate.currency, "USDT")
        self.assertEqual(candidate.revenue_date, date(2026, 7, 16))
        self.assertTrue(candidate.received)
        self.assertEqual(candidate.payment_method, "stripe")

    def test_skips_payload_without_order_or_amount(self):
        self.assertIsNone(normalize_sub2api_revenue({"amount": "10"}))
        self.assertIsNone(normalize_sub2api_revenue({"id": "order-1"}))

    def test_skips_unpaid_or_voided_orders(self):
        self.assertIsNone(
            normalize_sub2api_revenue(
                {
                    "out_trade_no": "voided-order",
                    "pay_amount": 10,
                    "status": "VOIDED",
                }
            )
        )
        self.assertIsNone(
            normalize_sub2api_revenue(
                {
                    "out_trade_no": "pending-order",
                    "pay_amount": 10,
                    "status": "PENDING",
                }
            )
        )


class Sub2APIRevenueSyncTests(unittest.TestCase):
    def test_creates_and_updates_revenue_by_remote_order(self):
        instance = SimpleNamespace(id=uuid.uuid4(), name="Main", base_url="https://sub2api.example")
        existing = Revenue(
            id=uuid.uuid4(),
            revenue_no=f"SUB2API-{instance.id}-remote-a",
            source="sub2api_recharge",
            customer="old@example.com",
            amount=Decimal("5"),
            currency="USD",
            revenue_date=date(2026, 7, 15),
            related_order_no=f"{instance.id}:remote-a",
            received=False,
        )
        db = MagicMock()
        db.scalars.return_value.all.return_value = [existing]
        added: list[Revenue] = []
        db.add.side_effect = added.append

        candidates = [
            Sub2APIRevenueCandidate(
                remote_order_no="remote-a",
                source="sub2api_recharge",
                customer="new@example.com",
                amount=Decimal("12.34"),
                currency="USD",
                payment_method="stripe",
                revenue_date=date(2026, 7, 16),
                received=True,
                raw_payload={"id": "remote-a"},
            ),
            Sub2APIRevenueCandidate(
                remote_order_no="remote-b",
                source="sub2api_recharge",
                customer="other@example.com",
                amount=Decimal("7.89"),
                currency="USD",
                payment_method=None,
                revenue_date=date(2026, 7, 16),
                received=True,
                raw_payload={"id": "remote-b"},
            ),
        ]

        with patch(
            "app.services.sub2api_revenue_sync.fetch_sub2api_revenue_candidates",
            return_value=candidates,
        ):
            result = sync_sub2api_revenues_for_instance(db, instance)

        self.assertEqual(result.created_count, 1)
        self.assertEqual(result.updated_count, 1)
        self.assertEqual(result.skipped_count, 0)
        self.assertEqual(existing.amount, Decimal("12.34"))
        self.assertEqual(existing.customer, "new@example.com")
        self.assertTrue(existing.received)
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0].related_order_no, f"{instance.id}:remote-b")
        self.assertEqual(added[0].revenue_no, f"SUB2API-{instance.id}-remote-b")


if __name__ == "__main__":
    unittest.main()
