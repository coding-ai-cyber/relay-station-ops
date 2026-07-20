import json
import os

from app.db.session import SessionLocal
from app.schemas.account import Sub2APICheckRequest
from app.services.sub2api_checker import run_sub2api_check


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "y", "on"}


def main() -> None:
    endpoint_url = os.getenv("SUB2API_CHECK_URL")
    if not endpoint_url:
        raise SystemExit("SUB2API_CHECK_URL is required")

    request_body_text = os.getenv("SUB2API_CHECK_BODY")
    request_body = json.loads(request_body_text) if request_body_text else None

    payload = Sub2APICheckRequest(
        endpoint_url=endpoint_url,
        method=os.getenv("SUB2API_CHECK_METHOD", "GET"),
        auth_header_name=os.getenv("SUB2API_CHECK_AUTH_HEADER_NAME") or None,
        auth_header_value=os.getenv("SUB2API_CHECK_AUTH_HEADER_VALUE") or None,
        account_type=os.getenv("SUB2API_CHECK_ACCOUNT_TYPE") or None,
        import_batch_no=os.getenv("SUB2API_CHECK_IMPORT_BATCH_NO") or None,
        include_only_operation=_bool_env("SUB2API_CHECK_ONLY_OPERATION", True),
        request_body=request_body,
        timeout_seconds=int(os.getenv("SUB2API_CHECK_TIMEOUT_SECONDS", "15")),
        remark=os.getenv("SUB2API_CHECK_REMARK") or "scheduled check",
    )

    db = SessionLocal()
    try:
        batch = run_sub2api_check(db, payload, checked_by=None)
        print(
            f"{batch.batch_no} done: total={batch.total_count}, "
            f"alive={batch.alive_count}, abnormal={batch.abnormal_count}, "
            f"401={batch.status_401_count}, 403={batch.status_403_count}, 429={batch.status_429_count}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
