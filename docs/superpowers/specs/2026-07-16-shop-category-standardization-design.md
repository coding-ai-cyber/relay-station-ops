# Shop Category Standardization Design

## Goal

Remove duplicate-looking category choices in shop monitor filters while preserving the original category data returned by supplier shop APIs.

## Design

Shop product snapshots keep the raw category fields (`category_id`, `category_name`) unchanged. Synchronization also writes standard category fields derived from the raw name:

- `standard_category_key`: normalized comparison key, currently lowercased trimmed whitespace.
- `standard_category_name`: display name for the merged category, preserving a readable canonical label.
- `category_duplicate_status`: `unique` for first category in a normalized group and `auto_merged` for later category ids/names in the same group.

Only exact normalization matches are auto-merged. For example, `K12`, `k12`, and ` K12 ` share `standard_category_key = "k12"`. Semantically different names such as `Chat GPT`, `ChatGPT Plus`, and `Chatgpt官方直充` remain separate.

## Data Flow

`LinkShopClient.fetch_products()` gathers all products and category payloads. Before returning them, it assigns standard category metadata across the fetched batch. `sync_monitor()` persists both raw and standard fields. The API response exposes the standard fields. The frontend category dropdown and filtering use standard fields, while the product table still displays the raw category name.

## Testing

Backend tests cover category metadata for a single product and duplicate category normalization across a product batch. Frontend build verifies TypeScript wiring and rendering.
