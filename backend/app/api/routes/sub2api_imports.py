import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.enums import UserRole
from app.db.session import get_db
from app.models.account import Account
from app.models.audit_log import AuditLog
from app.models.sub2api_import import Sub2APIImportBatch, Sub2APIImportItem
from app.models.sub2api_instance import Sub2APIInstance
from app.models.user import User
from app.schemas.sub2api_import import (
    Sub2APIImportBatchRead,
    Sub2APIImportCreate,
    Sub2APIImportItemRead,
)
from app.services.sub2api_importer import recover_stale_import_batch, run_sub2api_import

router = APIRouter(prefix="/api/sub2api-imports", tags=["sub2api-imports"])


def _batch_or_404(db: Session, batch_id: uuid.UUID) -> Sub2APIImportBatch:
    batch = db.get(Sub2APIImportBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import batch not found")
    return batch


def _batch_read(db: Session, batch: Sub2APIImportBatch) -> Sub2APIImportBatchRead:
    instance = db.get(Sub2APIInstance, batch.instance_id)
    return Sub2APIImportBatchRead.model_validate(
        {**batch.__dict__, "instance_name": instance.name if instance else None}
    )


def _accounts_in_order(db: Session, account_ids: list[uuid.UUID]) -> list[Account]:
    accounts = list(db.scalars(select(Account).where(Account.id.in_(account_ids))).all())
    by_id = {account.id: account for account in accounts}
    missing = [str(account_id) for account_id in account_ids if account_id not in by_id]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Accounts not found", "account_ids": missing},
        )
    return [by_id[account_id] for account_id in account_ids]


def _resolve_import_accounts(db: Session, payload: Sub2APIImportCreate) -> list[Account]:
    if payload.purchase_id:
        accounts = list(
            db.scalars(
                select(Account)
                .where(
                    Account.purchase_id == payload.purchase_id,
                    Account.raw_credentials_encrypted.is_not(None),
                )
                .order_by(Account.account_no.asc())
            ).all()
        )
        if not accounts:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No bound accounts available for this purchase",
            )
        return accounts
    if payload.select_all:
        accounts = list(
            db.scalars(select(Account).order_by(Account.created_at.desc())).all()
        )
        if not accounts:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No accounts available to import",
            )
        return accounts
    return _accounts_in_order(db, list(dict.fromkeys(payload.account_ids)))


def _prepare_retry_source(db: Session, source_batch: Sub2APIImportBatch) -> None:
    try:
        db.refresh(source_batch, with_for_update={"nowait": True})
    except OperationalError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Import batch is still running",
        ) from exc

    if source_batch.status == "running":
        if not recover_stale_import_batch(source_batch):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Import batch is still running",
            )
        db.commit()

    existing_retry = db.scalar(
        select(Sub2APIImportBatch).where(
            Sub2APIImportBatch.retry_of_batch_id == source_batch.id
        )
    )
    if existing_retry is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A retry batch already exists for this import",
        )


def _add_audit_log(
    db: Session,
    request: Request,
    user: User,
    batch: Sub2APIImportBatch,
    action: str,
    proxy_id: int | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user.id,
            action=action,
            resource_type="sub2api_import_batch",
            resource_id=batch.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            detail={
                "batch_no": batch.batch_no,
                "instance_id": str(batch.instance_id),
                "group_ids": batch.group_ids,
                "duplicate_policy": batch.duplicate_policy,
                "total_count": batch.total_count,
                "success_count": batch.success_count,
                "failed_count": batch.failed_count,
                "skipped_count": batch.skipped_count,
                "proxy_id": proxy_id,
            },
        )
    )
    db.commit()


@router.post("", response_model=Sub2APIImportBatchRead, status_code=status.HTTP_201_CREATED)
def create_sub2api_import(
    payload: Sub2APIImportCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PURCHASER)),
) -> Sub2APIImportBatchRead:
    instance = db.get(Sub2APIInstance, payload.instance_id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sub2API instance not found")
    if not instance.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Sub2API instance is inactive")
    accounts = _resolve_import_accounts(db, payload)
    batch = run_sub2api_import(
        db=db,
        instance=instance,
        accounts=accounts,
        group_ids=list(dict.fromkeys(payload.group_ids)),
        duplicate_policy=payload.duplicate_policy,
        created_by=current_user.id,
        remark=payload.remark,
        proxy_id=payload.proxy_id,
    )
    _add_audit_log(db, request, current_user, batch, "sub2api_import_accounts", payload.proxy_id)
    return _batch_read(db, batch)


@router.get("", response_model=list[Sub2APIImportBatchRead])
def list_sub2api_imports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Sub2APIImportBatchRead]:
    del current_user
    stmt = select(Sub2APIImportBatch).order_by(Sub2APIImportBatch.created_at.desc()).limit(50)
    return [_batch_read(db, batch) for batch in db.scalars(stmt).all()]


@router.get("/{batch_id}/items", response_model=list[Sub2APIImportItemRead])
def list_sub2api_import_items(
    batch_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Sub2APIImportItemRead]:
    del current_user
    _batch_or_404(db, batch_id)
    rows = db.execute(
        select(Sub2APIImportItem, Account)
        .join(Account, Account.id == Sub2APIImportItem.account_id)
        .where(Sub2APIImportItem.batch_id == batch_id)
        .order_by(Sub2APIImportItem.created_at.asc())
    ).all()
    return [
        Sub2APIImportItemRead.model_validate(
            {
                **item.__dict__,
                "account_no": account.account_no,
                "account_type": account.account_type,
            }
        )
        for item, account in rows
    ]


@router.post("/{batch_id}/retry", response_model=Sub2APIImportBatchRead, status_code=status.HTTP_201_CREATED)
def retry_sub2api_import(
    batch_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PURCHASER)),
) -> Sub2APIImportBatchRead:
    source_batch = _batch_or_404(db, batch_id)
    _prepare_retry_source(db, source_batch)
    failed_account_ids = list(
        db.scalars(
            select(Sub2APIImportItem.account_id).where(
                Sub2APIImportItem.batch_id == batch_id,
                Sub2APIImportItem.status == "failed",
            )
        ).all()
    )
    if not failed_account_ids:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No failed accounts to retry")
    instance = db.get(Sub2APIInstance, source_batch.instance_id)
    if instance is None or not instance.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Sub2API instance is unavailable")
    accounts = _accounts_in_order(db, failed_account_ids)
    try:
        batch = run_sub2api_import(
            db=db,
            instance=instance,
            accounts=accounts,
            group_ids=source_batch.group_ids,
            duplicate_policy=source_batch.duplicate_policy,
            created_by=current_user.id,
            remark=f"重试批次 {source_batch.batch_no}",
            retry_of_batch_id=source_batch.id,
        )
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A retry batch already exists for this import",
        ) from exc
    _add_audit_log(db, request, current_user, batch, "retry_sub2api_import_accounts")
    return _batch_read(db, batch)
