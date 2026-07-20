from app.models.cost_item import CostItem
from app.models.purchase import Purchase


def cost_type_from_purchase_type(purchase_type: str) -> str:
    mapping = {
        "account": "account",
        "server": "server",
        "proxy": "proxy",
        "domain": "domain",
        "software": "software",
    }
    return mapping.get(purchase_type, "other")


def make_purchase_cost_item(purchase: Purchase) -> CostItem:
    return CostItem(
        cost_no=f"COST-{purchase.purchase_no}",
        cost_type=cost_type_from_purchase_type(purchase.purchase_type),
        source_type="purchase",
        source_id=purchase.id,
        supplier_id=purchase.supplier_id,
        product_name=purchase.product_name,
        amount=purchase.total_price,
        currency=purchase.currency,
        cost_date=purchase.purchased_at,
        include_all_cost=purchase.include_all_cost,
        include_real_cost=purchase.include_real_cost,
        one_time=True,
        recurring=False,
        remark=f"Generated from purchase {purchase.purchase_no}",
    )


def sync_purchase_cost_item(cost_item: CostItem, purchase: Purchase) -> None:
    cost_item.cost_type = cost_type_from_purchase_type(purchase.purchase_type)
    cost_item.supplier_id = purchase.supplier_id
    cost_item.product_name = purchase.product_name
    cost_item.amount = purchase.total_price
    cost_item.currency = purchase.currency
    cost_item.cost_date = purchase.purchased_at
    cost_item.include_all_cost = purchase.include_all_cost
    cost_item.include_real_cost = purchase.include_real_cost
    cost_item.remark = f"Generated from purchase {purchase.purchase_no}"
