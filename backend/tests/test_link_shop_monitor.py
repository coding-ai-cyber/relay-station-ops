import unittest
from unittest.mock import MagicMock, patch

import httpx

from app.schemas.supplier import SupplierCreate
from app.services.link_shop_monitor import (
    LinkShopClient,
    apply_standard_categories,
    normalize_link_shop_product,
    parse_link_shop_token,
    parse_shop_reference,
)


class LinkShopMonitorTests(unittest.TestCase):
    def test_parses_token_from_link_shop_url(self):
        self.assertEqual(
            parse_link_shop_token("https://pay.ldxp.cn/shop/DD6LGP2Z"),
            "DD6LGP2Z",
        )

    def test_parses_token_with_category_path(self):
        self.assertEqual(
            parse_link_shop_token("https://pay.ldxp.cn/shop/DD6LGP2Z/some-category"),
            "DD6LGP2Z",
        )

    def test_accepts_raw_token(self):
        self.assertEqual(parse_link_shop_token("DD6LGP2Z"), "DD6LGP2Z")

    def test_rejects_non_link_shop_url(self):
        with self.assertRaises(ValueError):
            parse_link_shop_token("https://example.com/shop/DD6LGP2Z")

    def test_parses_link_shop_reference(self):
        platform, token = parse_shop_reference("https://pay.ldxp.cn/shop/DD6LGP2Z")

        self.assertEqual(platform.platform, "link_shop")
        self.assertEqual(platform.base_url, "https://pay.ldxp.cn")
        self.assertEqual(token, "DD6LGP2Z")

    def test_parses_catfk_shop_reference(self):
        platform, token = parse_shop_reference("https://catfk.com/shop/666666")

        self.assertEqual(platform.platform, "catfk")
        self.assertEqual(platform.base_url, "https://catfk.com")
        self.assertEqual(token, "666666")

    def test_rejects_unsupported_shop_reference_host(self):
        with self.assertRaises(ValueError):
            parse_shop_reference("https://example.com/shop/666666")

    def test_normalizes_product_stock_and_price(self):
        product = normalize_link_shop_product(
            {
                "name": "ChatGPT Plus",
                "goods_key": "r5z74o",
                "price": 99,
                "market_price": 120,
                "extend": {"stock_count": 676},
            },
            shop_token="DD6LGP2Z",
            goods_type="card",
            category={"id": 149148, "name": "ChatGPT Plus"},
        )

        self.assertEqual(product["external_product_id"], "r5z74o")
        self.assertEqual(product["name"], "ChatGPT Plus")
        self.assertEqual(product["price"], "99")
        self.assertEqual(product["market_price"], "120")
        self.assertEqual(product["stock_count"], 676)
        self.assertFalse(product["is_out_of_stock"])
        self.assertEqual(product["category_name"], "ChatGPT Plus")
        self.assertEqual(product["standard_category_key"], "chatgpt plus")
        self.assertEqual(product["standard_category_name"], "ChatGPT Plus")
        self.assertEqual(product["category_duplicate_status"], "unique")

    def test_normalizes_out_of_stock_product(self):
        product = normalize_link_shop_product(
            {
                "name": "K12 account",
                "goods_key": "u2o4oo",
                "price": 0.9,
                "extend": {"stock_count": 0},
            },
            shop_token="DD6LGP2Z",
            goods_type="card",
            category=None,
        )

        self.assertEqual(product["stock_count"], 0)
        self.assertTrue(product["is_out_of_stock"])
        self.assertIsNone(product["standard_category_key"])
        self.assertEqual(product["standard_category_name"], "未分类")
        self.assertEqual(product["category_duplicate_status"], "unique")

    def test_applies_standard_categories_to_case_duplicate_names(self):
        products = [
            normalize_link_shop_product(
                {"name": "K12 one", "goods_key": "one", "price": 1, "extend": {"stock_count": 1}},
                shop_token="DD6LGP2Z",
                goods_type="card",
                category={"id": 145340, "name": "K12"},
            ),
            normalize_link_shop_product(
                {"name": "K12 two", "goods_key": "two", "price": 2, "extend": {"stock_count": 1}},
                shop_token="DD6LGP2Z",
                goods_type="card",
                category={"id": 149688, "name": " k12 "},
            ),
        ]

        apply_standard_categories(products)

        self.assertEqual(products[0]["standard_category_key"], "k12")
        self.assertEqual(products[0]["standard_category_name"], "K12")
        self.assertEqual(products[0]["category_duplicate_status"], "unique")
        self.assertEqual(products[1]["standard_category_key"], "k12")
        self.assertEqual(products[1]["standard_category_name"], "K12")
        self.assertEqual(products[1]["category_duplicate_status"], "auto_merged")

    def test_normalizes_catfk_product_payload(self):
        product = normalize_link_shop_product(
            {
                "goods_key": "wjg5br",
                "name": "谷歌k12 team",
                "price": 1.46,
                "market_price": 0,
                "category": {"id": 4998, "name": "日抛json"},
                "extend": {"stock_count": 5},
            },
            shop_token="666666",
            goods_type="card",
            category={"id": 4998, "name": "日抛json"},
        )

        self.assertEqual(product["external_product_id"], "wjg5br")
        self.assertEqual(product["shop_token"], "666666")
        self.assertEqual(product["name"], "谷歌k12 team")
        self.assertEqual(product["price"], "1.46")
        self.assertEqual(product["market_price"], "0")
        self.assertEqual(product["stock_count"], 5)
        self.assertFalse(product["is_out_of_stock"])

    def test_supplier_create_accepts_purchase_url(self):
        supplier = SupplierCreate(
            name="bug team",
            type="account",
            purchase_url="https://pay.ldxp.cn/shop/DD6LGP2Z",
        )

        self.assertEqual(supplier.purchase_url, "https://pay.ldxp.cn/shop/DD6LGP2Z")

    def test_get_goods_uses_normal_page_size_by_default(self):
        client = LinkShopClient()
        captured_payloads = []

        def fake_post(path, payload):
            captured_payloads.append(payload)
            return {"list": []}

        client._post = fake_post

        client.get_goods("DD6LGP2Z", "card", 149148)

        self.assertEqual(captured_payloads[0]["pageSize"], 50)

    def test_post_retries_transient_server_error(self):
        request = httpx.Request("POST", "https://pay.ldxp.cn/shopApi/Shop/categoryList")
        server_error = httpx.Response(500, request=request, text="server error")
        success = httpx.Response(
            200,
            request=request,
            json={"code": 1, "msg": "success", "data": []},
        )
        http_client = MagicMock()
        http_client.post.side_effect = [server_error, success]
        http_client.__enter__.return_value = http_client
        http_client.__exit__.return_value = None

        with patch("app.services.link_shop_monitor.httpx.Client", return_value=http_client):
            result = LinkShopClient().get_categories("DD6LGP2Z", "card")

        self.assertEqual(result, [])
        self.assertEqual(http_client.post.call_count, 2)

    def test_post_reports_link_shop_block_page_as_readable_error(self):
        request = httpx.Request("POST", "https://pay.ldxp.cn/shopApi/Shop/goodsList")
        response = httpx.Response(
            403,
            request=request,
            text="<html><title>403 禁止访问</title><div>访问受限 - 检测到高风险异常访问行为</div></html>",
            headers={"content-type": "text/html"},
        )
        http_client = MagicMock()
        http_client.post.return_value = response
        http_client.__enter__.return_value = http_client
        http_client.__exit__.return_value = None

        with patch("app.services.link_shop_monitor.httpx.Client", return_value=http_client):
            with self.assertRaisesRegex(ValueError, "访问受限.*高风险异常访问行为"):
                LinkShopClient().get_goods("DD6LGP2Z", "card", 149148)


if __name__ == "__main__":
    unittest.main()
