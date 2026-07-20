import json
from typing import Any

from app.core.security import field_cipher

SENSITIVE_RAW_KEYS = {
    "access_token",
    "api_key",
    "authorization",
    "client_secret",
    "credentials",
    "key",
    "login_password",
    "password",
    "refresh_token",
    "secret",
    "service_account",
    "service_account_json",
    "session_token",
    "setup_token",
    "sub2api_key",
    "token",
}

FLAT_CREDENTIAL_ALIASES = {
    "access_token": "access_token",
    "api_key": "api_key",
    "client_secret": "client_secret",
    "key": "api_key",
    "refresh_token": "refresh_token",
    "service_account": "service_account",
    "service_account_json": "service_account_json",
    "session_token": "session_token",
    "setup_token": "setup_token",
    "sub2api_key": "api_key",
    "token": "token",
}


def redact_raw_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]"
            if str(key).lower() in SENSITIVE_RAW_KEYS
            else redact_raw_payload(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_raw_payload(item) for item in value]
    return value


def _is_redacted(value: Any) -> bool:
    return isinstance(value, str) and (value == "[REDACTED]" or "***" in value)


def _is_usable_credential_value(value: Any) -> bool:
    if value is None or _is_redacted(value):
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (dict, list)):
        return bool(value)
    return True


def prepare_raw_payload(
    raw_payload: dict | None,
    existing_encrypted: str | None = None,
) -> tuple[dict | None, str | None]:
    if not isinstance(raw_payload, dict):
        return raw_payload, None
    credentials_present = "credentials" in raw_payload
    credentials = raw_payload.get("credentials")
    extracted_credentials = {
        target_key: raw_payload[source_key]
        for source_key, target_key in FLAT_CREDENTIAL_ALIASES.items()
        if source_key in raw_payload
        and _is_usable_credential_value(raw_payload[source_key])
    }
    if isinstance(credentials, dict):
        extracted_credentials.update(credentials)

    encrypted = existing_encrypted if not credentials_present or _is_redacted(credentials) else None
    if extracted_credentials:
        encrypted = field_cipher.encrypt(
            json.dumps(extracted_credentials, ensure_ascii=False)
        )
    return redact_raw_payload(raw_payload), encrypted


def decrypt_raw_credentials(encrypted: str | None) -> dict[str, Any] | None:
    plaintext = field_cipher.decrypt(encrypted)
    if not plaintext:
        return None
    parsed = json.loads(plaintext)
    return parsed if isinstance(parsed, dict) else None
