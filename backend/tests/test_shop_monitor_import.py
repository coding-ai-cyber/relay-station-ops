import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.api.routes.shop_monitors import collect_supplier_shop_monitor_imports
from app.api.routes.suppliers import sync_supplier_shop_monitor
from app.models.shop_monitor import ShopMonitor


def supplier(
    *,
    name: str,
    supplier_type: str = "account",
    login_url: str | None = None,
    monitor_shop: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        name=name,
        type=supplier_type,
        login_url=login_url,
        monitor_shop=monitor_shop,
    )


class ShopMonitorImportTests(unittest.TestCase):
    def test_collects_only_opted_in_account_suppliers_with_supported_login_urls(self):
        link_supplier = supplier(
            name="Link Shop",
            login_url="https://pay.ldxp.cn/shop/DD6LGP2Z",
            monitor_shop=True,
        )
        catfk_supplier = supplier(
            name="Yunmao",
            login_url="https://catfk.com/shop/666666",
            monitor_shop=True,
        )
        suppliers = [
            link_supplier,
            catfk_supplier,
            supplier(name="Telegram", login_url=None, monitor_shop=True),
            supplier(name="Not opted in", login_url="https://catfk.com/shop/123456"),
            supplier(
                name="Server vendor",
                supplier_type="server",
                login_url="https://catfk.com/shop/999999",
                monitor_shop=True,
            ),
            supplier(name="Unsupported", login_url="https://example.com/shop/abc", monitor_shop=True),
        ]

        payloads, skipped_count = collect_supplier_shop_monitor_imports(
            suppliers,
            existing_refs=set(),
        )

        self.assertEqual(skipped_count, 4)
        self.assertEqual(
            [
                (payload["name"], payload["platform"], payload["shop_token"], payload["shop_url"])
                for payload in payloads
            ],
            [
                ("Link Shop", "link_shop", "DD6LGP2Z", "https://pay.ldxp.cn/shop/DD6LGP2Z"),
                ("Yunmao", "catfk", "666666", "https://catfk.com/shop/666666"),
            ],
        )
        self.assertEqual(payloads[0]["supplier_id"], link_supplier.id)
        self.assertEqual(payloads[1]["supplier_id"], catfk_supplier.id)

    def test_skips_existing_platform_token_pairs(self):
        suppliers = [
            supplier(name="Yunmao", login_url="https://catfk.com/shop/666666", monitor_shop=True),
        ]

        payloads, skipped_count = collect_supplier_shop_monitor_imports(
            suppliers,
            existing_refs={("catfk", "666666")},
        )

        self.assertEqual(payloads, [])
        self.assertEqual(skipped_count, 1)

    def test_supplier_monitor_creates_shop_monitor_when_enabled(self):
        db = MagicMock()
        db.scalar.return_value = None
        watched_supplier = supplier(
            name="Link Shop",
            login_url="https://pay.ldxp.cn/shop/DD6LGP2Z",
            monitor_shop=True,
        )

        sync_supplier_shop_monitor(db, watched_supplier)

        db.add.assert_called_once()
        monitor = db.add.call_args.args[0]
        self.assertIsInstance(monitor, ShopMonitor)
        self.assertEqual(monitor.supplier_id, watched_supplier.id)
        self.assertEqual(monitor.name, "Link Shop")
        self.assertEqual(monitor.platform, "link_shop")
        self.assertEqual(monitor.shop_token, "DD6LGP2Z")
        self.assertTrue(monitor.enabled)

    def test_supplier_monitor_reactivates_existing_shop_monitor(self):
        existing = ShopMonitor(
            name="Old name",
            shop_url="https://pay.ldxp.cn/shop/DD6LGP2Z",
            shop_token="DD6LGP2Z",
            platform="link_shop",
            enabled=False,
        )
        db = MagicMock()
        db.scalar.return_value = existing
        watched_supplier = supplier(
            name="New supplier name",
            login_url="https://pay.ldxp.cn/shop/DD6LGP2Z",
            monitor_shop=True,
        )

        sync_supplier_shop_monitor(db, watched_supplier)

        db.add.assert_not_called()
        self.assertEqual(existing.supplier_id, watched_supplier.id)
        self.assertEqual(existing.name, "New supplier name")
        self.assertTrue(existing.enabled)


if __name__ == "__main__":
    unittest.main()
