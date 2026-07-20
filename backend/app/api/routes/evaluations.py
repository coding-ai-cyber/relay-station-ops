import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.enums import UserRole
from app.db.session import get_db
from app.models.evaluation import AccountEvaluation, EvaluationBatch
from app.models.purchase import Purchase
from app.models.user import User
from app.schemas.evaluation import (
    AccountEvaluationCreate,
    AccountEvaluationRead,
    AccountEvaluationUpdate,
    EvaluationBatchCreate,
    EvaluationBatchRead,
    EvaluationBatchUpdate,
)
from app.services.evaluations import finalize_batch, recalculate_batch

router = APIRouter(prefix="/api/evaluation-batches", tags=["evaluation-batches"])
account_evaluation_router = APIRouter(
    prefix="/api/account-evaluations",
    tags=["account-evaluations"],
)


def _get_batch_or_404(db: Session, batch_id: uuid.UUID) -> EvaluationBatch:
    batch = db.get(EvaluationBatch, batch_id)
    if batch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation batch not found",
        )
    return batch


def _get_account_evaluation_or_404(
    db: Session,
    evaluation_id: uuid.UUID,
) -> AccountEvaluation:
    evaluation = db.get(AccountEvaluation, evaluation_id)
    if evaluation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account evaluation not found",
        )
    return evaluation


@router.get("", response_model=list[EvaluationBatchRead])
def list_evaluation_batches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    supplier_id: uuid.UUID | None = None,
    purchase_id: uuid.UUID | None = None,
    account_type: str | None = None,
    conclusion: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[EvaluationBatch]:
    del current_user
    stmt = select(EvaluationBatch).order_by(EvaluationBatch.created_at.desc())

    if supplier_id:
        stmt = stmt.where(EvaluationBatch.supplier_id == supplier_id)
    if purchase_id:
        stmt = stmt.where(EvaluationBatch.purchase_id == purchase_id)
    if account_type:
        stmt = stmt.where(EvaluationBatch.account_type == account_type)
    if conclusion:
        stmt = stmt.where(EvaluationBatch.conclusion == conclusion)

    return list(db.scalars(stmt.offset(offset).limit(limit)).all())


@router.post("", response_model=EvaluationBatchRead, status_code=status.HTTP_201_CREATED)
def create_evaluation_batch(
    payload: EvaluationBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER, UserRole.TESTER)
    ),
) -> EvaluationBatch:
    del current_user
    data = payload.model_dump()

    if payload.purchase_id:
        purchase = db.get(Purchase, payload.purchase_id)
        if purchase is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase not found",
            )
        if data.get("supplier_id") is None:
            data["supplier_id"] = purchase.supplier_id
        if not data.get("purchase_quantity"):
            data["purchase_quantity"] = int(purchase.quantity or 0)
        if not data.get("purchase_total_price"):
            data["purchase_total_price"] = purchase.total_price

    batch = EvaluationBatch(**data)
    recalculate_batch(db, batch)
    db.add(batch)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Evaluation batch number already exists",
        ) from exc

    db.refresh(batch)
    return batch


@router.get("/{batch_id}", response_model=EvaluationBatchRead)
def get_evaluation_batch(
    batch_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EvaluationBatch:
    del current_user
    return _get_batch_or_404(db, batch_id)


@router.patch("/{batch_id}", response_model=EvaluationBatchRead)
def update_evaluation_batch(
    batch_id: uuid.UUID,
    payload: EvaluationBatchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER, UserRole.TESTER)
    ),
) -> EvaluationBatch:
    del current_user
    batch = _get_batch_or_404(db, batch_id)

    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(batch, field_name, value)

    recalculate_batch(db, batch)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Evaluation batch number already exists",
        ) from exc

    db.refresh(batch)
    return batch


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evaluation_batch(
    batch_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER, UserRole.TESTER)
    ),
) -> None:
    del current_user
    batch = _get_batch_or_404(db, batch_id)

    for evaluation in db.scalars(
        select(AccountEvaluation).where(AccountEvaluation.batch_id == batch.id)
    ).all():
        db.delete(evaluation)

    db.delete(batch)
    db.commit()


@router.post("/{batch_id}/recalculate", response_model=EvaluationBatchRead)
def recalculate_evaluation_batch(
    batch_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER, UserRole.TESTER)
    ),
) -> EvaluationBatch:
    del current_user
    batch = _get_batch_or_404(db, batch_id)
    recalculate_batch(db, batch)
    db.commit()
    db.refresh(batch)
    return batch


@router.post("/{batch_id}/finalize", response_model=EvaluationBatchRead)
def finalize_evaluation_batch(
    batch_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER, UserRole.TESTER)
    ),
) -> EvaluationBatch:
    del current_user
    batch = _get_batch_or_404(db, batch_id)
    if batch.test_finished_at is None:
        batch.test_finished_at = datetime.now(UTC)
    finalize_batch(db, batch)
    db.commit()
    db.refresh(batch)
    return batch


@router.get("/{batch_id}/account-evaluations", response_model=list[AccountEvaluationRead])
def list_account_evaluations(
    batch_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AccountEvaluation]:
    del current_user
    _get_batch_or_404(db, batch_id)
    stmt = select(AccountEvaluation).where(AccountEvaluation.batch_id == batch_id)
    return list(db.scalars(stmt.order_by(AccountEvaluation.created_at.desc())).all())


@router.post(
    "/{batch_id}/account-evaluations",
    response_model=AccountEvaluationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_account_evaluation(
    batch_id: uuid.UUID,
    payload: AccountEvaluationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER, UserRole.TESTER)
    ),
) -> AccountEvaluation:
    del current_user
    batch = _get_batch_or_404(db, batch_id)
    evaluation = AccountEvaluation(batch_id=batch.id, **payload.model_dump())
    db.add(evaluation)
    db.flush()
    recalculate_batch(db, batch)
    db.commit()
    db.refresh(evaluation)
    return evaluation


@account_evaluation_router.patch("/{evaluation_id}", response_model=AccountEvaluationRead)
def update_account_evaluation(
    evaluation_id: uuid.UUID,
    payload: AccountEvaluationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER, UserRole.TESTER)
    ),
) -> AccountEvaluation:
    del current_user
    evaluation = _get_account_evaluation_or_404(db, evaluation_id)
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(evaluation, field_name, value)

    batch = _get_batch_or_404(db, evaluation.batch_id)
    recalculate_batch(db, batch)
    db.commit()
    db.refresh(evaluation)
    return evaluation
