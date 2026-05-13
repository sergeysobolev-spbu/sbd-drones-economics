"""Политика хранения учётных данных (PBKDF2), без доступа к БД."""

from __future__ import annotations

import hashlib
import hmac
import secrets


def hash_password(password: str, *, salt: str | None = None) -> str:
    """Hash a password with PBKDF2-HMAC-SHA256."""
    if not password:
        raise ValueError("password is required")
    salt_value = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt_value.encode(), 120_000)
    return f"pbkdf2_sha256${salt_value}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Return True if password matches the stored password hash."""
    try:
        algorithm, salt, expected = password_hash.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    actual = hash_password(password, salt=salt)
    return hmac.compare_digest(actual, password_hash)
