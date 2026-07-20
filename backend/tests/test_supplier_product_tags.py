import unittest
import uuid
from datetime import UTC, datetime

from app.schemas.supplier import SupplierCreate, SupplierRead


class SupplierProductTagTests(unittest.TestCase):
    def test_supplier_create_accepts_preferred_product_tags(self):
        supplier = SupplierCreate(
            name="号商A",
            type="account",
            preferred_product_tags=["free", "K12", "plus"],
        )

        self.assertEqual(supplier.preferred_product_tags, ["free", "K12", "plus"])

    def test_supplier_read_exposes_preferred_product_tags(self):
        supplier = SupplierRead.model_validate(
            {
                "id": uuid.uuid4(),
                "name": "号商A",
                "type": "account",
                "preferred_product_tags": ["bugteam", "pro"],
                "contact_name": None,
                "purchase_url": None,
                "login_url": "https://pay.ldxp.cn/shop/ABC",
                "country_region": None,
                "continue_cooperation": True,
                "monitor_shop": True,
                "status": "normal",
                "remark": None,
                "has_login_account": False,
                "has_login_secret": False,
                "created_at": datetime(2026, 7, 17, tzinfo=UTC),
                "updated_at": datetime(2026, 7, 17, tzinfo=UTC),
            }
        )

        self.assertEqual(supplier.preferred_product_tags, ["bugteam", "pro"])


if __name__ == "__main__":
    unittest.main()
