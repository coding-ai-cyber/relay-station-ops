import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.enums import UserRole
from app.core.security import field_cipher
from app.db.session import get_db
from app.models.account import Account
from app.models.account_check import AccountCheckBatch, AccountCheckRecord
from app.models.account_item import AccountItem
from app.models.audit_log import AuditLog
from app.models.evaluation import AccountEvaluation
from app.models.sub2api_import import Sub2APIImportItem
from app.models.user import User
from app.schemas.account import (
    AccountBulkDeleteRequest,
    AccountBulkDeleteResult,
    AccountCheckBatchRead,
    AccountCheckRecordRead,
    AccountCreate,
    AccountItemRead,
    AccountRead,
    AccountSecretRead,
    AccountStatusUpdate,
    AccountUpdate,
    Sub2APIAutoCheckRequest,
    Sub2APICheckRequest,
)
from app.models.sub2api_instance import Sub2APIInstance
from app.services.account_credentials import prepare_raw_payload, redact_raw_payload
from app.services.sub2api_admin_adapter import run_admin_key_account_check
from app.services.sub2api_checker import run_sub2api_check

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

def to_account_read(account: Account) -> AccountRead:
    return AccountRead.model_validate(
        {
            **account.__dict__,
            "raw_payload": redact_raw_payload(account.raw_payload),
            "has_login_password": bool(account.login_password_encrypted),
            "has_sub2api_key": bool(account.sub2api_key_encrypted),
            "has_raw_credentials": bool(account.raw_credentials_encrypted),
        }
    )


def _get_account_or_404(db: Session, account_id: uuid.UUID) -> Account:
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    return account


def _delete_account_with_dependents(db: Session, account: Account) -> None:
    db.execute(delete(AccountEvaluation).where(AccountEvaluation.account_id == account.id))
    db.execute(delete(AccountCheckRecord).where(AccountCheckRecord.account_id == account.id))
    db.execute(delete(Sub2APIImportItem).where(Sub2APIImportItem.account_id == account.id))
    db.execute(delete(AccountItem).where(AccountItem.account_id == account.id))
    db.delete(account)


@router.get("", response_model=list[AccountRead])
def list_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    account_type: str | None = Query(default=None, alias="type"),
    status_filter: str | None = Query(default=None, alias="status"),
    supplier_id: uuid.UUID | None = None,
    purchase_id: uuid.UUID | None = None,
    sub2api_instance_id: uuid.UUID | None = None,
    participate_operation: bool | None = None,
    include_real_cost: bool | None = None,
    q: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AccountRead]:
    del current_user
    stmt = select(Account).order_by(Account.created_at.desc())

    if account_type:
        stmt = stmt.where(Account.account_type == account_type)
    if status_filter:
        stmt = stmt.where(Account.status == status_filter)
    if supplier_id:
        stmt = stmt.where(Account.supplier_id == supplier_id)
    if purchase_id:
        stmt = stmt.where(Account.purchase_id == purchase_id)
    if sub2api_instance_id:
        stmt = stmt.where(Account.sub2api_instance_id == sub2api_instance_id)
    if participate_operation is not None:
        stmt = stmt.where(Account.participate_operation == participate_operation)
    if include_real_cost is not None:
        stmt = stmt.where(Account.include_real_cost == include_real_cost)
    if q:
        stmt = stmt.where(Account.account_no.ilike(f"%{q}%"))

    return [to_account_read(item) for item in db.scalars(stmt.offset(offset).limit(limit)).all()]


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER, UserRole.TESTER)
    ),
) -> AccountRead:
    del current_user
    data = payload.model_dump(exclude={"login_password", "sub2api_key", "raw_payload"})
    raw_payload, raw_credentials_encrypted = prepare_raw_payload(payload.raw_payload)
    account = Account(
        **data,
        raw_payload=raw_payload,
        raw_credentials_encrypted=raw_credentials_encrypted,
        login_password_encrypted=field_cipher.encrypt(payload.login_password),
        sub2api_key_encrypted=field_cipher.encrypt(payload.sub2api_key),
    )
    db.add(account)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account number already exists",
        ) from exc

    db.refresh(account)
    return to_account_read(account)


@router.post("/bulk-import", response_model=list[AccountRead], status_code=status.HTTP_201_CREATED)
def bulk_import_accounts(
    payload: list[AccountCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER, UserRole.TESTER)
    ),
) -> list[AccountRead]:
    del current_user
    accounts: list[Account] = []

    for item in payload:
        data = item.model_dump(exclude={"login_password", "sub2api_key", "raw_payload"})
        raw_payload, raw_credentials_encrypted = prepare_raw_payload(item.raw_payload)
        accounts.append(
            Account(
                **data,
                raw_payload=raw_payload,
                raw_credentials_encrypted=raw_credentials_encrypted,
                login_password_encrypted=field_cipher.encrypt(item.login_password),
                sub2api_key_encrypted=field_cipher.encrypt(item.sub2api_key),
            )
        )

    db.add_all(accounts)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="One or more account numbers already exist",
        ) from exc

    for account in accounts:
        db.refresh(account)
    return [to_account_read(account) for account in accounts]


@router.post("/bulk-delete", response_model=AccountBulkDeleteResult)
def bulk_delete_accounts(
    payload: AccountBulkDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER, UserRole.TESTER)
    ),
) -> AccountBulkDeleteResult:
    del current_user
    accounts = list(
        db.scalars(select(Account).where(Account.id.in_(payload.account_ids))).all()
    )

    for account in accounts:
        _delete_account_with_dependents(db, account)

    db.commit()
    return AccountBulkDeleteResult(deleted_count=len(accounts))


@router.post("/sub2api-checks", response_model=AccountCheckBatchRead)
def create_sub2api_check(
    payload: Sub2APICheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER, UserRole.TESTER)
    ),
) -> AccountCheckBatchRead:
    batch = run_sub2api_check(db, payload, current_user.id)
    return AccountCheckBatchRead.model_validate(batch)


@router.post("/sub2api-checks/auto", response_model=AccountCheckBatchRead)
def create_auto_sub2api_check(
    payload: Sub2APIAutoCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER, UserRole.TESTER)
    ),
) -> AccountCheckBatchRead:
    instance = db.get(Sub2APIInstance, payload.instance_id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sub2API instance not found")
    batch = run_admin_key_account_check(
        db=db,
        instance=instance,
        checked_by=current_user.id,
        account_type=payload.account_type,
        import_batch_no=payload.import_batch_no,
        purchase_id=payload.purchase_id,
        include_only_operation=payload.include_only_operation,
        timeout_seconds=payload.timeout_seconds,
        remark=payload.remark,
    )
    return AccountCheckBatchRead.model_validate(batch)


@router.get("/sub2api-checks", response_model=list[AccountCheckBatchRead])
def list_sub2api_checks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AccountCheckBatchRead]:
    del current_user
    stmt = select(AccountCheckBatch).order_by(AccountCheckBatch.created_at.desc())
    return [
        AccountCheckBatchRead.model_validate(item)
        for item in db.scalars(stmt.offset(offset).limit(limit)).all()
    ]


@router.get("/sub2api-checks/{batch_id}/records", response_model=list[AccountCheckRecordRead])
def list_sub2api_check_records(
    batch_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=500),
) -> list[AccountCheckRecordRead]:
    del current_user
    stmt = (
        select(AccountCheckRecord)
        .where(AccountCheckRecord.batch_id == batch_id)
        .order_by(AccountCheckRecord.checked_at.desc())
    )
    return [
        AccountCheckRecordRead.model_validate(item)
        for item in db.scalars(stmt.offset(offset).limit(limit)).all()
    ]


@router.get("/{account_id}", response_model=AccountRead)
def get_account(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccountRead:
    del current_user
    account = _get_account_or_404(db, account_id)
    return to_account_read(account)


@router.get("/{account_id}/items", response_model=list[AccountItemRead])
def list_account_items(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AccountItem]:
    del current_user
    _get_account_or_404(db, account_id)
    return list(
        db.scalars(
            select(AccountItem)
            .where(AccountItem.account_id == account_id)
            .order_by(AccountItem.item_index.asc(), AccountItem.created_at.asc())
        ).all()
    )


@router.patch("/{account_id}", response_model=AccountRead)
def update_account(
    account_id: uuid.UUID,
    payload: AccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER, UserRole.TESTER)
    ),
) -> AccountRead:
    del current_user
    account = _get_account_or_404(db, account_id)
    data = payload.model_dump(exclude_unset=True)

    if "login_password" in data:
        account.login_password_encrypted = field_cipher.encrypt(data.pop("login_password"))
    if "sub2api_key" in data:
        account.sub2api_key_encrypted = field_cipher.encrypt(data.pop("sub2api_key"))
    if "raw_payload" in data:
        account.raw_payload, account.raw_credentials_encrypted = prepare_raw_payload(
            data.pop("raw_payload"),
            existing_encrypted=account.raw_credentials_encrypted,
        )

    for field_name, value in data.items():
        setattr(account, field_name, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account number already exists",
        ) from exc

    db.refresh(account)
    return to_account_read(account)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER, UserRole.TESTER)
    ),
) -> None:
    del current_user
    account = _get_account_or_404(db, account_id)
    _delete_account_with_dependents(db, account)
    db.commit()


@router.post("/{account_id}/mark-status", response_model=AccountRead)
def mark_account_status(
    account_id: uuid.UUID,
    payload: AccountStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER, UserRole.TESTER)
    ),
) -> AccountRead:
    del current_user
    account = _get_account_or_404(db, account_id)

    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, field_name, value)

    db.commit()
    db.refresh(account)
    return to_account_read(account)


@router.post("/{account_id}/reveal-secret", response_model=AccountSecretRead)
def reveal_account_secret(
    account_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER, UserRole.TESTER)
    ),
) -> AccountSecretRead:
    account = _get_account_or_404(db, account_id)

    audit_log = AuditLog(
        user_id=current_user.id,
        action="reveal_account_secret",
        resource_type="account",
        resource_id=account.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        detail={"account_no": account.account_no},
    )
    db.add(audit_log)
    db.commit()

    return AccountSecretRead(
        id=account.id,
        login_account=account.login_account,
        login_password=field_cipher.decrypt(account.login_password_encrypted),
        authorized_email=account.authorized_email,
        sub2api_account_id=account.sub2api_account_id,
        sub2api_key=field_cipher.decrypt(account.sub2api_key_encrypted),
    )




@router.get("/{account_id}/check-records", response_model=list[AccountCheckRecordRead])
def list_account_check_records(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=300),
) -> list[AccountCheckRecordRead]:
    del current_user
    _get_account_or_404(db, account_id)
    stmt = (
        select(AccountCheckRecord)
        .where(AccountCheckRecord.account_id == account_id)
        .order_by(AccountCheckRecord.checked_at.desc())
    )
    return [
        AccountCheckRecordRead.model_validate(item)
        for item in db.scalars(stmt.offset(offset).limit(limit)).all()
    ]
