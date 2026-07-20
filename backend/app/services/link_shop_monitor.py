from decimal import Decimal
from dataclasses import dataclass
import re
import time
from typing import Any
from urllib.parse import urlparse

import httpx

LINK_SHOP_HOST = "pay.ldxp.cn"
LINK_SHOP_BASE_URL = "https://pay.ldxp.cn"
CATFK_HOST = "catfk.com"
CATFK_BASE_URL = "https://catfk.com"
GOODS_TYPES = ("card", "article", "resource", "equity")


@dataclass(frozen=True)
class ShopPlatformConfig:
    platform: str
    host: str
    base_url: str


SHOP_PLATFORMS = {
    LINK_SHOP_HOST: ShopPlatformConfig(
        platform="link_shop",
        host=LINK_SHOP_HOST,
        base_url=LINK_SHOP_BASE_URL,
    ),
    CATFK_HOST: ShopPlatformConfig(
        platform="catfk",
        host=CATFK_HOST,
        base_url=CATFK_BASE_URL,
    ),
}

SHOP_PLATFORMS_BY_NAME = {config.platform: config for config in SHOP_PLATFORMS.values()}


def parse_shop_reference(url_or_token: str) -> tuple[ShopPlatformConfig, str]:
    value = url_or_token.strip()
    if not value:
        raise ValueError("Shop URL or token is required")

    if "://" not in value:
        return SHOP_PLATFORMS_BY_NAME["link_shop"], value.strip("/")

    parsed = urlparse(value)
    platform = SHOP_PLATFORMS.get(parsed.netloc)
    if platform is None:
        raise ValueError("Only pay.ldxp.cn and catfk.com shop URLs are supported")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or parts[0] != "shop":
        raise ValueError("Shop URL must look like https://{host}/shop/{token}")
    return platform, parts[1]


def parse_link_shop_token(url_or_token: str) -> str:
    value = url_or_token.strip()
    if not value:
        raise ValueError("Shop URL or token is required")

    if "://" not in value:
        return value.strip("/")

    parsed = urlparse(value)
    if parsed.netloc != LINK_SHOP_HOST:
        raise ValueError("Only pay.ldxp.cn shop URLs are supported")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or parts[0] != "shop":
        raise ValueError("Link shop URL must look like https://pay.ldxp.cn/shop/{token}")
    return parts[1]


def _decimal_string(value: object) -> str | None:
    if value is None:
        return None
    return str(Decimal(str(value)))


def _standard_category_key(category_name: object) -> str | None:
    if category_name is None:
        return None
    key = str(category_name).strip().lower()
    return key or None


def apply_standard_categories(products: list[dict[str, Any]]) -> None:
    standard_names: dict[str, str] = {}
    standard_raw_ids: dict[str, set[str | None]] = {}
    for product in products:
        key = _standard_category_key(product.get("category_name"))
        if key is None:
            product["standard_category_key"] = None
            product["standard_category_name"] = "未分类"
            product["category_duplicate_status"] = "unique"
            continue

        raw_category_id = product.get("category_id")
        raw_id = str(raw_category_id) if raw_category_id is not None else None
        if key not in standard_names:
            standard_names[key] = str(product.get("category_name")).strip()
            standard_raw_ids[key] = set()

        product["standard_category_key"] = key
        product["standard_category_name"] = standard_names[key]
        product["category_duplicate_status"] = (
            "auto_merged" if standard_raw_ids[key] and raw_id not in standard_raw_ids[key] else "unique"
        )
        standard_raw_ids[key].add(raw_id)


def normalize_link_shop_product(
    raw: dict[str, Any],
    shop_token: str,
    goods_type: str,
    category: dict[str, Any] | None,
) -> dict[str, Any]:
    stock_count = int((raw.get("extend") or {}).get("stock_count") or 0)
    category = category or {}
    product = {
        "external_product_id": str(raw.get("goods_key") or ""),
        "shop_token": shop_token,
        "goods_type": goods_type,
        "category_id": str(category.get("id")) if category.get("id") is not None else None,
        "category_name": category.get("name"),
        "name": raw.get("name") or "",
        "price": _decimal_string(raw.get("price")) or "0",
        "market_price": _decimal_string(raw.get("market_price")),
        "stock_count": stock_count,
        "is_out_of_stock": stock_count <= 0,
        "raw_payload": raw,
    }
    apply_standard_categories([product])
    return product


class LinkShopClient:
    def __init__(
        self,
        platform: str = "link_shop",
        timeout: float = 20.0,
        max_retries: int = 1,
        retry_delay_seconds: float = 0.2,
    ) -> None:
        if platform not in SHOP_PLATFORMS_BY_NAME:
            raise ValueError(f"Unsupported shop platform: {platform}")
        self.base_url = SHOP_PLATFORMS_BY_NAME[platform].base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

    def _format_http_error(
        self,
        path: str,
        payload: dict[str, Any],
        response: httpx.Response,
    ) -> str:
        labels = {
            "/shopApi/Shop/info": "店铺信息接口",
            "/shopApi/Shop/categoryList": "分类接口",
            "/shopApi/Shop/goodsList": "商品接口",
        }
        context_parts = [f"接口 {path}"]
        for key in ("token", "goods_type", "category_id"):
            if payload.get(key) is not None:
                context_parts.append(f"{key}={payload[key]}")
        context = "，".join(context_parts)

        body = response.text or ""
        body_text = re.sub(r"<[^>]+>", " ", body)
        body_text = re.sub(r"\s+", " ", body_text).strip()
        if response.status_code == 403 and "访问受限" in body_text:
            return f"Link Shop {labels.get(path, '接口')}访问受限：{body_text}（HTTP 403，{context}）"
        if response.status_code >= 500:
            detail = f"：{body_text[:200]}" if body_text else ""
            return (
                f"Link Shop {labels.get(path, '接口')}暂时异常"
                f"（HTTP {response.status_code}，{context}）{detail}"
            )
        return f"Link Shop {labels.get(path, '接口')}请求失败（HTTP {response.status_code}，{context}）"

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Visitorid": "sub2api-ops-monitor",
        }
        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(base_url=self.base_url, timeout=self.timeout, headers=headers) as client:
                    response = client.post(path, json=payload)
                    response.raise_for_status()
                    data = response.json()
                break
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                if status_code >= 500 and attempt < self.max_retries:
                    time.sleep(self.retry_delay_seconds)
                    continue
                raise ValueError(self._format_http_error(path, payload, exc.response)) from exc
            except httpx.TimeoutException as exc:
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay_seconds)
                    continue
                raise ValueError(f"Link Shop 接口请求超时（接口 {path}）") from exc
        if data.get("code") != 1:
            raise ValueError(str(data.get("msg") or "Link shop request failed"))
        return data.get("data")

    def get_shop_info(self, token: str) -> dict[str, Any]:
        return self._post("/shopApi/Shop/info", {"token": token})

    def get_categories(
        self,
        token: str,
        goods_type: str,
        category_key: str | None = None,
    ) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"token": token, "goods_type": goods_type}
        if category_key:
            payload["category_key"] = category_key
        return list(self._post("/shopApi/Shop/categoryList", payload) or [])

    def get_goods(
        self,
        token: str,
        goods_type: str,
        category_id: int | str,
        current: int = 1,
        page_size: int = 50,
    ) -> list[dict[str, Any]]:
        products: list[dict[str, Any]] = []
        page = current
        while True:
            data = self._post(
                "/shopApi/Shop/goodsList",
                {
                    "token": token,
                    "keywords": "",
                    "category_id": category_id,
                    "goods_type": goods_type,
                    "current": page,
                    "pageSize": page_size,
                },
            )
            page_products = list((data or {}).get("list") or [])
            products.extend(page_products)
            if len(page_products) < page_size:
                break
            page += 1
        return products

    def fetch_products(self, token: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        shop_info = self.get_shop_info(token)
        products: list[dict[str, Any]] = []
        goods_types = shop_info.get("goods_type_sort") or GOODS_TYPES

        for goods_type in goods_types:
            categories = self.get_categories(token, str(goods_type))
            for category in categories:
                category_id = category.get("id")
                if category_id is None:
                    continue
                for raw in self.get_goods(token, str(goods_type), category_id):
                    products.append(
                        normalize_link_shop_product(raw, token, str(goods_type), category)
                    )

        apply_standard_categories(products)
        return shop_info, products
