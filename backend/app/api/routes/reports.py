import uuid
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.cost_item import CostItem
from app.models.evaluation import EvaluationBatch
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.dashboard import (
    AccountTypeProfitRow,
    AIPricingRecommendationRow,
    MonthlyProfitRow,
    PurchaseBatchProfitRow,
    SupplierMultiplierRow,
    SupplierRankingRow,
)
from app.services.metrics import cost_sums, month_bounds, revenue_sum

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _iter_months(start_year: int, start_month: int, end_year: int, end_month: int):
    year = start_year
    month = start_month
    while (year, month) <= (end_year, end_month):
        yield year, month
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1


@router.get("/monthly-profit", response_model=list[MonthlyProfitRow])
def monthly_profit_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    start_year: int = Query(default_factory=lambda: date.today().year, ge=2000, le=2100),
    start_month: int = Query(default=1, ge=1, le=12),
    end_year: int = Query(default_factory=lambda: date.today().year, ge=2000, le=2100),
    end_month: int = Query(default_factory=lambda: date.today().month, ge=1, le=12),
) -> list[MonthlyProfitRow]:
    del current_user
    rows: list[MonthlyProfitRow] = []

    for year, month in _iter_months(start_year, start_month, end_year, end_month):
        start, end = month_bounds(year, month)
        revenue = revenue_sum(db, start, end)
        all_cost, real_cost = cost_sums(db, start, end)
        rows.append(
            MonthlyProfitRow(
                month=f"{year:04d}-{month:02d}",
                revenue=revenue,
                all_cost=all_cost,
                real_cost=real_cost,
                profit=revenue - all_cost,
                real_profit=revenue - real_cost,
                test_loss=all_cost - real_cost,
            )
        )

    return rows


@router.get("/supplier-ranking", response_model=list[SupplierRankingRow])
def supplier_ranking_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[SupplierRankingRow]:
    del current_user

    cost_rows = db.execute(
        select(
            Supplier.id,
            Supplier.name,
            func.count(CostItem.id),
            func.coalesce(
                func.sum(CostItem.amount).filter(CostItem.include_all_cost.is_(True)),
                0,
            ),
            func.coalesce(
                func.sum(CostItem.amount).filter(CostItem.include_real_cost.is_(True)),
                0,
            ),
        )
        .join(CostItem, CostItem.supplier_id == Supplier.id, isouter=True)
        .group_by(Supplier.id, Supplier.name)
        .order_by(
            func.coalesce(
                func.sum(CostItem.amount).filter(CostItem.include_all_cost.is_(True)),
                0,
            ).desc()
        )
        .limit(limit)
    ).all()

    score_rows = dict(
        db.execute(
            select(EvaluationBatch.supplier_id, func.avg(EvaluationBatch.overall_score))
            .where(EvaluationBatch.supplier_id.is_not(None))
            .group_by(EvaluationBatch.supplier_id)
        ).all()
    )

    return [
        SupplierRankingRow(
            supplier_id=str(row[0]) if row[0] else None,
            supplier_name=row[1],
            purchase_count=int(row[2] or 0),
            all_cost=float(row[3] or 0),
            real_cost=float(row[4] or 0),
            test_loss=float(row[3] or 0) - float(row[4] or 0),
            avg_score=float(score_rows.get(row[0])) if score_rows.get(row[0]) is not None else None,
        )
        for row in cost_rows
    ]


@router.get("/supplier-multiplier", response_model=list[SupplierMultiplierRow])
def supplier_multiplier_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    target_margin: float = Query(default=35, ge=0, le=80),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[SupplierMultiplierRow]:
    del current_user

    rows = db.execute(
        select(
            Supplier.id,
            Supplier.name,
            func.count(EvaluationBatch.id),
            func.coalesce(func.sum(EvaluationBatch.purchase_quantity), 0),
            func.coalesce(func.sum(EvaluationBatch.effective_account_count), 0),
            func.coalesce(func.sum(EvaluationBatch.purchase_total_price), 0),
            func.coalesce(func.avg(EvaluationBatch.overall_score), 0),
        )
        .join(EvaluationBatch, EvaluationBatch.supplier_id == Supplier.id)
        .where(EvaluationBatch.purchase_quantity > 0)
        .group_by(Supplier.id, Supplier.name)
        .order_by(func.coalesce(func.avg(EvaluationBatch.overall_score), 0).desc())
        .limit(limit)
    ).all()

    result: list[SupplierMultiplierRow] = []
    for row in rows:
        supplier_id, supplier_name, batch_count, purchase_quantity, effective_count, total_price, avg_score = row
        purchase_quantity_decimal = Decimal(purchase_quantity or 0)
        effective_count_decimal = Decimal(effective_count or 0)
        total_price_decimal = Decimal(total_price or 0)
        avg_score_decimal = Decimal(avg_score or 0)

        if purchase_quantity_decimal <= 0 or effective_count_decimal <= 0:
            continue

        effective_rate = effective_count_decimal / purchase_quantity_decimal * Decimal("100")
        real_effective_unit_cost = total_price_decimal / effective_count_decimal
        stability_level = _stability_level(int(batch_count), effective_rate, avg_score_decimal)
        multiplier_parts = _recommended_multiplier_parts(
            target_margin=Decimal(str(target_margin)),
            effective_rate=effective_rate,
            avg_score=avg_score_decimal,
            stability_level=stability_level,
        )
        multiplier = sum(multiplier_parts.values(), Decimal("0"))
        suggested_sale_price = real_effective_unit_cost * multiplier

        result.append(
            SupplierMultiplierRow(
                supplier_id=str(supplier_id),
                supplier_name=supplier_name,
                batch_count=int(batch_count or 0),
                purchase_quantity=int(purchase_quantity or 0),
                effective_account_count=int(effective_count or 0),
                effective_rate=float(_q2(effective_rate)),
                avg_score=float(_q2(avg_score_decimal)),
                real_effective_unit_cost=float(_q4(real_effective_unit_cost)),
                target_margin=target_margin,
                base_multiplier=float(_q2(multiplier_parts["base_multiplier"])),
                risk_buffer=float(_q2(multiplier_parts["risk_buffer"])),
                loss_buffer=float(_q2(multiplier_parts["loss_buffer"])),
                score_buffer=float(_q2(multiplier_parts["score_buffer"])),
                recommended_multiplier=float(_q2(multiplier)),
                suggested_sale_price=float(_q4(suggested_sale_price)),
                stability_level=stability_level,
                reason=_multiplier_reason(stability_level, effective_rate, avg_score_decimal),
            )
        )

    return result


@router.get("/account-type-profit", response_model=list[AccountTypeProfitRow])
def account_type_profit_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[AccountTypeProfitRow]:
    del current_user

    batches = db.scalars(
        select(EvaluationBatch)
        .where(EvaluationBatch.purchase_quantity > 0)
        .order_by(EvaluationBatch.created_at.desc())
    ).all()

    grouped: dict[str, dict[str, Decimal | int | list[Decimal]]] = {}
    for batch in batches:
        account_type = batch.account_type
        purchase_quantity = int(batch.purchase_quantity or 0)
        effective_count = int(batch.effective_account_count or 0)
        total_price = Decimal(batch.purchase_total_price or 0)
        nominal_unit_price = total_price / Decimal(purchase_quantity) if purchase_quantity else Decimal("0")
        test_loss = nominal_unit_price * Decimal(max(purchase_quantity - effective_count, 0))

        item = grouped.setdefault(
            account_type,
            {
                "batch_count": 0,
                "purchase_quantity": 0,
                "effective_account_count": 0,
                "all_cost": Decimal("0"),
                "test_loss": Decimal("0"),
                "scores": [],
            },
        )
        item["batch_count"] = int(item["batch_count"]) + 1
        item["purchase_quantity"] = int(item["purchase_quantity"]) + purchase_quantity
        item["effective_account_count"] = int(item["effective_account_count"]) + effective_count
        item["all_cost"] = Decimal(item["all_cost"]) + total_price
        item["test_loss"] = Decimal(item["test_loss"]) + test_loss
        if batch.overall_score is not None:
            scores = item["scores"]
            assert isinstance(scores, list)
            scores.append(Decimal(batch.overall_score))

    result: list[AccountTypeProfitRow] = []
    for account_type, item in grouped.items():
        purchase_quantity = int(item["purchase_quantity"])
        effective_count = int(item["effective_account_count"])
        all_cost = Decimal(item["all_cost"])
        test_loss = Decimal(item["test_loss"])
        effective_cost = all_cost - test_loss
        scores = item["scores"]
        assert isinstance(scores, list)
        effective_rate = (
            Decimal(effective_count) / Decimal(purchase_quantity) * Decimal("100")
            if purchase_quantity
            else Decimal("0")
        )
        real_effective_unit_cost = (
            all_cost / Decimal(effective_count)
            if effective_count
            else None
        )
        avg_score = sum(scores, Decimal("0")) / Decimal(len(scores)) if scores else None

        result.append(
            AccountTypeProfitRow(
                account_type=account_type,
                batch_count=int(item["batch_count"]),
                purchase_quantity=purchase_quantity,
                effective_account_count=effective_count,
                effective_rate=float(_q2(effective_rate)),
                all_cost=float(_q4(all_cost)),
                effective_cost=float(_q4(effective_cost)),
                test_loss=float(_q4(test_loss)),
                real_effective_unit_cost=float(_q4(real_effective_unit_cost)) if real_effective_unit_cost is not None else None,
                avg_score=float(_q2(avg_score)) if avg_score is not None else None,
            )
        )

    return sorted(result, key=lambda row: (row.real_effective_unit_cost is None, row.real_effective_unit_cost or 0))[:limit]


@router.get("/ai-pricing-recommendations", response_model=list[AIPricingRecommendationRow])
def ai_pricing_recommendations_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    target_margin: float = Query(default=35, ge=0, le=80),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[AIPricingRecommendationRow]:
    account_type_rows = account_type_profit_report(
        db=db,
        current_user=current_user,
        limit=limit,
    )
    return build_ai_pricing_recommendations(account_type_rows, target_margin=target_margin)


def build_ai_pricing_recommendations(
    rows: list[AccountTypeProfitRow],
    *,
    target_margin: float,
) -> list[AIPricingRecommendationRow]:
    result: list[AIPricingRecommendationRow] = []
    for row in rows:
        if row.real_effective_unit_cost is None or row.effective_account_count <= 0:
            continue

        effective_rate = Decimal(str(row.effective_rate))
        avg_score = Decimal(str(row.avg_score if row.avg_score is not None else 70))
        risk_level = _stability_level(row.batch_count, effective_rate, avg_score)
        multiplier_parts = _recommended_multiplier_parts(
            target_margin=Decimal(str(target_margin)),
            effective_rate=effective_rate,
            avg_score=avg_score,
            stability_level=risk_level,
        )
        multiplier = sum(multiplier_parts.values(), Decimal("0"))
        display_multiplier = _q2(multiplier)
        real_unit_cost = Decimal(str(row.real_effective_unit_cost))
        suggested_sale_price = real_unit_cost * display_multiplier
        projected_revenue = suggested_sale_price * Decimal(row.effective_account_count)
        projected_profit = projected_revenue - Decimal(str(row.all_cost))
        projected_margin = (
            projected_profit / projected_revenue * Decimal("100")
            if projected_revenue > 0
            else Decimal("0")
        )

        result.append(
            AIPricingRecommendationRow(
                account_type=row.account_type,
                batch_count=row.batch_count,
                purchase_quantity=row.purchase_quantity,
                effective_account_count=row.effective_account_count,
                effective_rate=float(_q2(effective_rate)),
                real_effective_unit_cost=float(_q4(real_unit_cost)),
                target_margin=target_margin,
                recommended_multiplier=float(display_multiplier),
                suggested_sale_price=float(_q2(suggested_sale_price)),
                projected_revenue=float(_q2(projected_revenue)),
                projected_profit=float(_q2(projected_profit)),
                projected_margin=float(_q2(projected_margin)),
                risk_level=risk_level,
                reason=_ai_recommendation_reason(
                    risk_level,
                    effective_rate,
                    avg_score,
                    row.test_loss,
                ),
            )
        )

    return sorted(result, key=lambda item: item.projected_profit, reverse=True)


@router.get("/purchase-batch-profit", response_model=list[PurchaseBatchProfitRow])
def purchase_batch_profit_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    account_type: str | None = None,
    supplier_id: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[PurchaseBatchProfitRow]:
    del current_user

    stmt = (
        select(EvaluationBatch, Supplier.name)
        .join(Supplier, EvaluationBatch.supplier_id == Supplier.id, isouter=True)
        .where(EvaluationBatch.purchase_quantity > 0)
        .order_by(EvaluationBatch.created_at.desc())
        .limit(limit)
    )
    if account_type:
        stmt = stmt.where(EvaluationBatch.account_type == account_type)
    if supplier_id:
        stmt = stmt.where(EvaluationBatch.supplier_id == supplier_id)

    result: list[PurchaseBatchProfitRow] = []
    for batch, supplier_name in db.execute(stmt).all():
        purchase_quantity = int(batch.purchase_quantity or 0)
        effective_count = int(batch.effective_account_count or 0)
        total_price = Decimal(batch.purchase_total_price or 0)
        nominal_unit_price = total_price / Decimal(purchase_quantity) if purchase_quantity else None
        real_effective_unit_price = (
            total_price / Decimal(effective_count)
            if effective_count
            else None
        )
        effective_rate = (
            Decimal(effective_count) / Decimal(purchase_quantity) * Decimal("100")
            if purchase_quantity
            else Decimal("0")
        )
        test_loss = (
            nominal_unit_price * Decimal(max(purchase_quantity - effective_count, 0))
            if nominal_unit_price is not None
            else Decimal("0")
        )

        result.append(
            PurchaseBatchProfitRow(
                batch_id=str(batch.id),
                batch_no=batch.batch_no,
                supplier_id=str(batch.supplier_id) if batch.supplier_id else None,
                supplier_name=supplier_name,
                account_type=batch.account_type,
                purchase_quantity=purchase_quantity,
                effective_account_count=effective_count,
                effective_rate=float(_q2(effective_rate)),
                purchase_total_price=float(_q4(total_price)),
                nominal_unit_price=float(_q4(nominal_unit_price)) if nominal_unit_price is not None else None,
                real_effective_unit_price=float(_q4(real_effective_unit_price)) if real_effective_unit_price is not None else None,
                test_loss=float(_q4(test_loss)),
                overall_score=float(_q2(Decimal(batch.overall_score))) if batch.overall_score is not None else None,
                conclusion=batch.conclusion,
            )
        )

    return result


def _recommended_multiplier_parts(
    target_margin: Decimal,
    effective_rate: Decimal,
    avg_score: Decimal,
    stability_level: str,
) -> dict[str, Decimal]:
    margin_ratio = target_margin / Decimal("100")
    base_multiplier = Decimal("1") / (Decimal("1") - margin_ratio)
    risk_buffer = {
        "stable": Decimal("0.10"),
        "observing": Decimal("0.25"),
        "high_risk": Decimal("0.50"),
    }[stability_level]
    loss_buffer = min((Decimal("100") - effective_rate) / Decimal("100") * Decimal("0.50"), Decimal("0.50"))
    score_buffer = max(Decimal("0"), (Decimal("85") - avg_score) / Decimal("100") * Decimal("0.50"))
    return {
        "base_multiplier": base_multiplier,
        "risk_buffer": risk_buffer,
        "loss_buffer": loss_buffer,
        "score_buffer": score_buffer,
    }


def _stability_level(batch_count: int, effective_rate: Decimal, avg_score: Decimal) -> str:
    if batch_count >= 2 and effective_rate >= 80 and avg_score >= 85:
        return "stable"
    if effective_rate >= 50 and avg_score >= 65:
        return "observing"
    return "high_risk"


def _multiplier_reason(stability_level: str, effective_rate: Decimal, avg_score: Decimal) -> str:
    label = {
        "stable": "长期稳定",
        "observing": "观察中",
        "high_risk": "高风险",
    }[stability_level]
    return f"{label}；有效率 {float(_q2(effective_rate))}%；平均评分 {float(_q2(avg_score))}"


def _ai_recommendation_reason(
    risk_level: str,
    effective_rate: Decimal,
    avg_score: Decimal,
    test_loss: float,
) -> str:
    label = {
        "stable": "稳定",
        "observing": "观察中",
        "high_risk": "高风险",
    }[risk_level]
    return (
        f"{label}；有效率 {float(_q2(effective_rate))}%；"
        f"平均评分 {float(_q2(avg_score))}；测试损耗 ¥{float(_q2(Decimal(str(test_loss))))}"
    )


def _q2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _q4(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
