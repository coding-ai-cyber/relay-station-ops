import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.enums import UserRole
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User
from app.models.account_check import AccountCheckBatch
from app.models.audit_log import AuditLog
from app.models.purchase import Purchase
from app.schemas.auth import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


def _get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.get("", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    q: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[User]:
    del current_user
    stmt = select(User).order_by(User.created_at.desc())

    if q:
        stmt = stmt.where(User.username.ilike(f"%{q}%"))
    if role:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)

    return list(db.scalars(stmt.offset(offset).limit(limit)).all())


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> User:
    del current_user
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=payload.is_active,
    )
    db.add(user)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        ) from exc

    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> User:
    user = _get_user_or_404(db, user_id)
    data = payload.model_dump(exclude_unset=True)

    if current_user.id == user.id and data.get("is_active") is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate current user",
        )

    if "password" in data:
        user.password_hash = hash_password(data.pop("password"))

    for field_name, value in data.items():
        setattr(user, field_name, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        ) from exc

    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> None:
    user = _get_user_or_404(db, user_id)
    if current_user.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete current user",
        )

    for purchase in db.scalars(select(Purchase).where(Purchase.purchaser_id == user.id)).all():
        purchase.purchaser_id = None
    for batch in db.scalars(
        select(AccountCheckBatch).where(AccountCheckBatch.checked_by == user.id)
    ).all():
        batch.checked_by = None
    for audit_log in db.scalars(select(AuditLog).where(AuditLog.user_id == user.id)).all():
        audit_log.user_id = None

    db.delete(user)
    db.commit()
