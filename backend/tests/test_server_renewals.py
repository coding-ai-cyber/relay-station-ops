import unittest
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from app.api.routes.servers import build_server_renewal_purchase
from app.models.server import Server
from app.schemas.server import ServerRenewRequest


class ServerRenewalTests(unittest.TestCase):
    def test_builds_renewal_purchase_from_server_and_payload(self):
        server_id = uuid.uuid4()
        supplier_id = uuid.uuid4()
        purchaser_id = uuid.uuid4()
        expires_at = datetime(2026, 9, 16, tzinfo=UTC)
        server = Server(
            id=server_id,
            name="sub2api-main-01",
            supplier_id=supplier_id,
            usage="sub2api_main",
            include_real_cost=True,
        )
        payload = ServerRenewRequest(
            amount=Decimal("88.50"),
            currency="CNY",
            payment_method="alipay",
            purchased_at=date(2026, 8, 16),
            new_expired_at=expires_at,
            include_real_cost=True,
            cost_status="valid",
            remark="renew one month",
        )

        purchase = build_server_renewal_purchase(
            server=server,
            payload=payload,
            purchaser_id=purchaser_id,
            purchase_no="PO-20260816-RENEW1",
        )

        self.assertEqual(purchase.purchase_no, "PO-20260816-RENEW1")
        self.assertEqual(purchase.purchase_type, "server")
        self.assertEqual(purchase.supplier_id, supplier_id)
        self.assertEqual(purchase.product_name, "续费：sub2api-main-01")
        self.assertEqual(purchase.product_type, "renewal")
        self.assertEqual(purchase.quantity, Decimal("1"))
        self.assertEqual(purchase.unit_price, Decimal("88.50"))
        self.assertEqual(purchase.total_price, Decimal("88.50"))
        self.assertEqual(purchase.currency, "CNY")
        self.assertEqual(purchase.payment_method, "alipay")
        self.assertEqual(purchase.purchased_at, date(2026, 8, 16))
        self.assertEqual(purchase.purchaser_id, purchaser_id)
        self.assertTrue(purchase.include_all_cost)
        self.assertTrue(purchase.include_real_cost)
        self.assertEqual(purchase.cost_status, "valid")
        self.assertIn(str(server_id), purchase.remark)


if __name__ == "__main__":
    unittest.main()
