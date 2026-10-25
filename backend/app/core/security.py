"""Password hashing, access tokens and pickup-code hashing.

* Passwords: bcrypt (salted, adaptive cost). Plaintext is never stored.
* Access tokens: short-lived signed JWT (HS256). The user is re-loaded from the
  database on every request, so deactivating an account takes effect immediately.
* Pickup codes: random 6-digit codes. Only an HMAC-SHA256 of (salt + code) keyed
  with SECRET_KEY is stored, so a database leak does not reveal usable codes.
"""
import hashlib
import hmac
import secrets
from datetime import timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError
from app.core.time import utcnow


def hash_password(password: str) -> str:
    rounds = get_settings().bcrypt_rounds
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=rounds)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def create_access_token(user_id: int, role: str) -> tuple[str, int]:
    settings = get_settings()
    expires_in = settings.access_token_expire_minutes * 60
    now = utcnow()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str) -> int:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise AuthenticationError("Invalid or expired access token") from exc


def generate_pickup_code() -> str:
    """Cryptographically random 6-digit code (000000-999999)."""
    return f"{secrets.randbelow(1_000_000):06d}"


def generate_salt() -> str:
    return secrets.token_hex(16)


def hash_pickup_code(code: str, salt: str) -> str:
    key = get_settings().secret_key.encode()
    return hmac.new(key, f"{salt}:{code}".encode(), hashlib.sha256).hexdigest()


def pickup_code_matches(code: str, salt: str, expected_hash: str) -> bool:
    return hmac.compare_digest(hash_pickup_code(code, salt), expected_hash)


def generate_reset_token() -> tuple[str, str]:
    """Cryptographically secure 32-byte URL-safe password reset token and its sha256 hash."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)


def hash_token(token: str) -> str:
    """SHA-256 hash of an opaque token for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_refresh_token() -> tuple[str, str]:
    """Cryptographically secure 48-byte URL-safe refresh token and its sha256 hash."""
    raw = secrets.token_urlsafe(48)
    return raw, hash_token(raw)

