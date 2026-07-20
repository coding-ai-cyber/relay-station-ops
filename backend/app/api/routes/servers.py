import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.enums import UserRole
from app.core.security import field_cipher
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.purchase import Purchase
from app.models.server import Server
from app.models.user import User
from app.schemas.purchase import PurchaseRead
from app.schemas.server import ServerCreate, ServerRead, ServerRenewRequest, ServerSecretRead, ServerUpdate
from app.api.routes.purchases import generate_purchase_no
from app.services.purchase_costs import make_purchase_cost_item

router = APIRouter(prefix="/api/servers", tags=["servers"])


def _to_server_read(server: Server) -> ServerRead:
    return ServerRead.model_validate(
        {
            **server.__dict__,
            "has_ssh_secret": bool(server.ssh_secret_encrypted),
        }
    )


def _get_server_or_404(db: Session, server_id: uuid.UUID) -> Server:
    server = db.get(Server, server_id)
    if server is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found",
        )
    return server


def build_server_renewal_purchase(
    *,
    server: Server,
    payload: ServerRenewRequest,
    purchaser_id: uuid.UUID,
    purchase_no: str | None = None,
) -> Purchase:
    purchased_at = payload.purchased_at.date() if hasattr(payload.purchased_at, "date") else payload.purchased_at
    remark_parts = [
        f"Renewal for server {server.id}",
        payload.remark,
    ]
    return Purchase(
        purchase_no=purchase_no or generate_purchase_no(today=purchased_at),
        purchase_type="server",
        supplier_id=server.supplier_id,
        product_name=f"续费：{server.name}",
        product_type="renewal",
        quantity=Decimal("1"),
        unit_price=payload.amount,
        total_price=payload.amount,
        currency=payload.currency,
        payment_method=payload.payment_method,
        purchased_at=purchased_at,
        purchaser_id=purchaser_id,
        include_all_cost=True,
        include_real_cost=payload.include_real_cost,
        cost_status=payload.cost_status,
        remark="；".join(part for part in remark_parts if part),
    )


@router.get("", response_model=list[ServerRead])
def list_servers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status_filter: str | None = Query(default=None, alias="status"),
    supplier_id: uuid.UUID | None = None,
    purchase_id: uuid.UUID | None = None,
    include_real_cost: bool | None = None,
    q: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ServerRead]:
    del current_user
    stmt = select(Server).order_by(Server.created_at.desc())

    if status_filter:
        stmt = stmt.where(Server.status == status_filter)
    if supplier_id:
        stmt = stmt.where(Server.supplier_id == supplier_id)
    if purchase_id:
        stmt = stmt.where(Server.purchase_id == purchase_id)
    if include_real_cost is not None:
        stmt = stmt.where(Server.include_real_cost == include_real_cost)
    if q:
        stmt = stmt.where(Server.name.ilike(f"%{q}%"))

    return [_to_server_read(item) for item in db.scalars(stmt.offset(offset).limit(limit)).all()]


@router.post("", response_model=ServerRead, status_code=status.HTTP_201_CREATED)
def create_server(
    payload: ServerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER)
    ),
) -> ServerRead:
    del current_user
    data = payload.model_dump(exclude={"ssh_secret"})
    server = Server(
        **data,
        ssh_secret_encrypted=field_cipher.encrypt(payload.ssh_secret),
    )
    db.add(server)
    db.commit()
    db.refresh(server)
    return _to_server_read(server)


@router.get("/{server_id}", response_model=ServerRead)
def get_server(
    server_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ServerRead:
    del current_user
    return _to_server_read(_get_server_or_404(db, server_id))


@router.patch("/{server_id}", response_model=ServerRead)
def update_server(
    server_id: uuid.UUID,
    payload: ServerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER)
    ),
) -> ServerRead:
    del current_user
    server = _get_server_or_404(db, server_id)
    data = payload.model_dump(exclude_unset=True)

    if "ssh_secret" in data:
        server.ssh_secret_encrypted = field_cipher.encrypt(data.pop("ssh_secret"))

    for field_name, value in data.items():
        setattr(server, field_name, value)

    db.commit()
    db.refresh(server)
    return _to_server_read(server)


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_server(
    server_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER)
    ),
) -> None:
    del current_user
    server = _get_server_or_404(db, server_id)
    db.delete(server)
    db.commit()


@router.post("/{server_id}/renew", response_model=PurchaseRead, status_code=status.HTTP_201_CREATED)
def renew_server(
    server_id: uuid.UUID,
    payload: ServerRenewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.FINANCE, UserRole.PURCHASER)
    ),
) -> Purchase:
    server = _get_server_or_404(db, server_id)
    purchase = build_server_renewal_purchase(
        server=server,
        payload=payload,
        purchaser_id=current_user.id,
    )
    server.expired_at = payload.new_expired_at
    server.monthly_cost = payload.amount
    server.include_real_cost = payload.include_real_cost
    db.add(purchase)
    db.flush()
    db.add(make_purchase_cost_item(purchase))
    db.commit()
    db.refresh(purchase)
    return purchase


@router.post("/{server_id}/reveal-secret", response_model=ServerSecretRead)
def reveal_server_secret(
    server_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PURCHASER)
    ),
) -> ServerSecretRead:
    server = _get_server_or_404(db, server_id)

    audit_log = AuditLog(
        user_id=current_user.id,
        action="reveal_server_secret",
        resource_type="server",
        resource_id=server.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        detail={"server_name": server.name, "login_host": server.login_host},
    )
    db.add(audit_log)
    db.commit()

    return ServerSecretRead(
        id=server.id,
        login_host=server.login_host,
        ssh_username=server.ssh_username,
        ssh_secret=field_cipher.decrypt(server.ssh_secret_encrypted),
    )
