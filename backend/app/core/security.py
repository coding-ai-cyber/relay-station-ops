import base64
import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, jwt

from app.core.config import settings


class FieldCipher:
    def __init__(self, raw_key: str) -> None:
        self._aesgcm = AESGCM(self._normalize_key(raw_key))

    def encrypt(self, value: str | None) -> str | None:
        if value is None:
            return None

        nonce = os.urandom(12)
        ciphertext = self._aesgcm.encrypt(nonce, value.encode("utf-8"), None)
        payload = {
            "v": 1,
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        }
        return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")

    def decrypt(self, value: str | None) -> str | None:
        if value is None:
            return None

        payload: dict[str, Any] = json.loads(base64.b64decode(value).decode("utf-8"))
        nonce = base64.b64decode(payload["nonce"])
        ciphertext = base64.b64decode(payload["ciphertext"])
        plaintext = self._aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")

    @staticmethod
    def _normalize_key(raw_key: str) -> bytes:
        try:
            decoded = base64.b64decode(raw_key, validate=True)
            if len(decoded) in {16, 24, 32}:
                return decoded
        except Exception:
            pass
        return hashlib.sha256(raw_key.encode("utf-8")).digest()


field_cipher = FieldCipher(settings.app_field_encryption_key)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(UTC) + (
        expires_delta
        or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.app_secret_key, algorithm="HS256")


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.app_secret_key, algorithms=["HS256"])
    except JWTError as exc:
        raise ValueError("Invalid access token") from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise ValueError("Invalid access token subject")
    return subject
