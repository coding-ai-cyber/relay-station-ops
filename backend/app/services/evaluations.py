from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.evaluation import AccountEvaluation, EvaluationBatch
from app.models.purchase import Purchase
from app.services.purchase_costs import sync_purchase_cost_item
from app.models.cost_item import CostItem


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def is_effective_evaluation(item: AccountEvaluation) -> bool:
    if item.is_banned or item.is_refunded:
        return False
    if item.can_login is False or item.has_risk_control is True:
        return False
    if item.target_model_available is False:
        return False
    if item.available_days is not None and item.available_days >= 7:
        return True
    return bool(item.can_login and item.target_model_available)


def recalculate_batch(db: Session, batch: EvaluationBatch) -> EvaluationBatch:
    evaluations = list(
        db.scalars(
            select(AccountEvaluation).where(AccountEvaluation.batch_id == batch.id)
        ).all()
    )

    batch.initial_pass_count = sum(1 for item in evaluations if item.can_login is True)
    batch.day7_available_count = sum(
        1 for item in evaluations if (item.available_days or 0) >= 7 and not item.is_banned
    )
    batch.day30_available_count = sum(
        1 for item in evaluations if (item.available_days or 0) >= 30 and not item.is_banned
    )
    batch.banned_count = sum(1 for item in evaluations if item.is_banned)
    batch.refund_count = sum(1 for item in evaluations if item.is_refunded)
    batch.effective_account_count = sum(1 for item in evaluations if is_effective_evaluation(item))

    if batch.purchase_quantity:
        batch.nominal_unit_price = quantize_money(
            Decimal(batch.purchase_total_price) / Decimal(batch.purchase_quantity)
        )
    else:
        batch.nominal_unit_price = None

    if batch.effective_account_count:
        batch.real_effective_unit_price = quantize_money(
            Decimal(batch.purchase_total_price) / Decimal(batch.effective_account_count)
        )
    else:
        batch.real_effective_unit_price = None

    batch.overall_score = calculate_batch_score(batch, evaluations)
    batch.conclusion = conclusion_from_batch(batch)
    return batch


def calculate_batch_score(
    batch: EvaluationBatch,
    evaluations: list[AccountEvaluation],
) -> Decimal:
    total = batch.purchase_quantity or len(evaluations)
    if total <= 0:
        return Decimal("0.00")

    available_rate = Decimal(batch.effective_account_count) / Decimal(total) * Decimal("100")
    stability = Decimal(batch.day7_available_count) / Decimal(total) * Decimal("100")
    if batch.day30_available_count:
        stability = max(
            stability,
            Decimal(batch.day30_available_count) / Decimal(total) * Decimal("100"),
        )

    avg_manual = _avg([item.manual_score for item in evaluations if item.manual_score is not None])
    avg_success = _avg(
        [
            item.request_success_rate
            for item in evaluations
            if item.request_success_rate is not None
        ]
    )

    if batch.nominal_unit_price and batch.real_effective_unit_price:
        price_ratio = Decimal(batch.nominal_unit_price) / Decimal(batch.real_effective_unit_price)
        cost_performance = min(price_ratio * Decimal("100"), Decimal("100"))
    else:
        cost_performance = Decimal("0")

    supply_stability = Decimal("100") if batch.purchase_quantity else Decimal("0")
    after_sales = Decimal("100") if batch.refund_count == 0 else Decimal("70")

    score = (
        available_rate * Decimal("0.30")
        + max(stability, avg_success) * Decimal("0.25")
        + cost_performance * Decimal("0.20")
        + after_sales * Decimal("0.10")
        + supply_stability * Decimal("0.10")
        + avg_manual * Decimal("0.05")
    )
    return score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def conclusion_from_batch(batch: EvaluationBatch) -> str:
    score = Decimal(batch.overall_score or 0)
    total = batch.purchase_quantity or 0
    day30_rate = (
        Decimal(batch.day30_available_count) / Decimal(total) * Decimal("100")
        if total
        else Decimal("0")
    )
    effective_rate = (
        Decimal(batch.effective_account_count) / Decimal(total) * Decimal("100")
        if total
        else Decimal("0")
    )

    if score >= 85 and (day30_rate >= 80 or effective_rate >= 80):
        return "recommended"
    if score >= 65 or effective_rate >= 50:
        return "cautious"
    if score >= 40 or effective_rate >= 20:
        return "not_recommended"
    return "blocked"


def finalize_batch(db: Session, batch: EvaluationBatch) -> EvaluationBatch:
    recalculate_batch(db, batch)

    if batch.purchase_id is None:
        return batch

    purchase = db.get(Purchase, batch.purchase_id)
    if purchase is None:
        return batch

    if batch.effective_account_count <= 0:
        purchase.include_real_cost = False
        purchase.cost_status = "invalid"
    elif batch.effective_account_count < batch.purchase_quantity:
        purchase.include_real_cost = True
        purchase.cost_status = "partial_valid"
    else:
        purchase.include_real_cost = True
        purchase.cost_status = "valid"

    cost_item = db.scalar(
        select(CostItem).where(
            CostItem.source_type == "purchase",
            CostItem.source_id == purchase.id,
        )
    )
    if cost_item is not None:
        sync_purchase_cost_item(cost_item, purchase)

    for item in db.scalars(
        select(AccountEvaluation).where(AccountEvaluation.batch_id == batch.id)
    ):
        account = db.get(Account, item.account_id)
        if account is None:
            continue
        if item.is_refunded:
            account.status = "refunded"
            account.participate_operation = False
            account.include_real_cost = False
        elif item.is_banned:
            account.status = "banned"
            account.participate_operation = False
            account.include_real_cost = False
        elif is_effective_evaluation(item):
            account.status = "available"
            account.participate_operation = True
            account.include_real_cost = True
            account.available_days = item.available_days
        else:
            account.status = "unavailable"
            account.participate_operation = False
            account.include_real_cost = False

    return batch


def _avg(values: list[Decimal | None]) -> Decimal:
    clean_values = [Decimal(value) for value in values if value is not None]
    if not clean_values:
        return Decimal("0")
    return sum(clean_values, Decimal("0")) / Decimal(len(clean_values))

