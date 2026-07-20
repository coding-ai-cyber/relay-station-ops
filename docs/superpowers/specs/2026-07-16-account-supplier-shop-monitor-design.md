# Account Supplier Shop Monitor Design

## Goal

Simplify account supplier shop URLs and support product monitoring for both Link Shop (`pay.ldxp.cn`) and CatFK/Yunmao (`catfk.com`) shop links.

## Supplier URL UX

For account suppliers, the supplier form uses one URL field: `login_url`, labeled as the supplier login/shop address. The previous separate purchase shop URL is no longer shown in the form. This avoids entering the same shop link twice.

Some account suppliers come from Telegram, WeChat, or other non-shop sources. To prevent noisy monitor entries, suppliers gain an explicit `monitor_shop` switch. Only suppliers with `monitor_shop = true` and a supported `login_url` are imported into shop monitoring.

## Monitoring Platforms

The shop monitor backend detects platform by URL host:

- `pay.ldxp.cn/shop/{token}` maps to platform `link_shop`.
- `catfk.com/shop/{token}` maps to platform `catfk`.

Both platforms use the same public API shape under `/shopApi/Shop/info`, `/categoryList`, and `/goodsList`, with `token`, `goods_type`, `category_id`, `current`, and `pageSize` parameters. The existing product normalization can be reused for CatFK because product fields include `goods_key`, `name`, `price`, `market_price`, `category`, and `extend.stock_count`.

## Data Model

`suppliers` gains `monitor_shop boolean not null default false`.

`shop_monitors` should identify a store by `(platform, shop_token)` rather than global `shop_token` alone, so different platforms can safely use the same token value.

Existing `purchase_url` data remains in the database for compatibility, but the supplier UI no longer edits it for this workflow.

## Backend Behavior

Creating a shop monitor parses the URL, stores `platform`, `shop_url`, and `shop_token`, and rejects unsupported hosts.

Importing from suppliers reads account suppliers where `monitor_shop` is true and `login_url` is present. Unsupported URLs are skipped. Existing monitors for the same `(platform, shop_token)` are skipped.

Sync chooses the client base URL from `monitor.platform` and otherwise keeps the current upsert behavior.

## Frontend Behavior

The supplier modal shows:

- Supplier name
- Type
- Status
- Continue cooperation
- Login/shop address
- Enable shop monitoring
- Credentials fields

The monitoring switch should be visible only for account suppliers or harmlessly disabled/hidden for other supplier types.

The shop monitor page copy should describe general shop monitoring rather than only Link Shop. Manual monitor creation accepts either supported shop URL.

## Tests

Backend tests cover:

- Parsing Link Shop URLs.
- Parsing CatFK URLs.
- Rejecting unsupported hosts.
- Normalizing CatFK product payloads.
- Import-from-suppliers behavior only includes opted-in account suppliers with supported login URLs.

Frontend verification uses the existing build to catch TypeScript and JSX regressions.
