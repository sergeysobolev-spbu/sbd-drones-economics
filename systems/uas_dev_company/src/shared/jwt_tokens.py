"""Кодирование и проверка компактных JWT (HS256) только стандартной библиотекой."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
from typing import Any


class TokenError(ValueError):
    """Некорректный или истёкший токен."""


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(seg: str) -> bytes:
    pad = "=" * (-len(seg) % 4)
    try:
        return base64.urlsafe_b64decode(seg + pad)
    except (binascii.Error, ValueError) as exc:
        raise TokenError("invalid token encoding") from exc


def create_access_token(secret: str, username: str, role: str, ttl_seconds: int = 86400) -> str:
    """Выпустить Bearer-токен: payload содержит sub (логин) и role (русские идентификаторы ролей)."""
    if not secret:
        raise ValueError("JWT secret is empty")
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": username,
        "role": role,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    h = _b64encode(json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode())
    p = _b64encode(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode())
    signing_input = f"{h}.{p}".encode()
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    s = _b64encode(sig)
    return f"{h}.{p}.{s}"


def verify_access_token(secret: str, token: str) -> dict[str, Any]:
    """Проверить подпись и срок действия; вернуть payload как dict."""
    if not secret:
        raise ValueError("JWT secret is empty")
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise TokenError("token must have three segments")
    h_b64, p_b64, s_b64 = parts
    signing_input = f"{h_b64}.{p_b64}".encode()
    expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    try:
        actual_sig = _b64decode(s_b64)
    except TokenError:
        raise
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise TokenError("invalid signature")
    try:
        payload = json.loads(_b64decode(p_b64).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise TokenError("invalid payload") from exc
    exp = payload.get("exp")
    if exp is None or int(exp) < int(time.time()):
        raise TokenError("token expired")
    return payload
