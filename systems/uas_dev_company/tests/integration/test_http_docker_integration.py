"""HTTP-проверки поднятого docker-compose (режим bus): задаётся UAS_HTTP_INTEGRATION_BASE."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

import pytest

BASE = os.environ.get("UAS_HTTP_INTEGRATION_BASE", "").rstrip("/")

requires_live_stack = pytest.mark.skipif(not BASE, reason="UAS_HTTP_INTEGRATION_BASE не задан (см. make test-all-docker)")


def _request(
    method: str,
    path: str,
    body: dict | None = None,
    headers: dict | None = None,
    timeout: float = 60.0,
) -> tuple[int, dict]:
    url = f"{BASE}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req_headers = dict(headers or {})
    if body is not None:
        req_headers.setdefault("Content-Type", "application/json; charset=utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"error": raw}
        return e.code, payload


@requires_live_stack
def test_live_health_ok():
    status, data = _request("GET", "/health", timeout=15.0)
    assert status == 200
    assert data.get("ok") is True


@requires_live_stack
def test_live_wrong_login_fails_under_one_minute():
    """Неверные учётные данные не должны ждать общий длинный таймаут шлюза."""
    t0 = time.monotonic()
    status, data = _request(
        "POST",
        "/api/login",
        {"username": "__no_such_user__", "password": "x"},
        timeout=90.0,
    )
    elapsed = time.monotonic() - t0
    assert status == 401
    assert "error" in data
    assert elapsed < 60.0, f"ожидался быстрый 401, заняло {elapsed:.1f}s"


@requires_live_stack
def test_live_gateway_roundtrip_with_admin():
    """Логин и чтение /api/users через nginx → gateway → монитор → user_management."""
    user = os.environ.get("E2E_ADMIN_USER", "e2e-admin")
    password = os.environ.get("E2E_ADMIN_PASSWORD", "e2e-admin-pass")
    _request("POST", "/api/bootstrap-admin", {"username": user, "password": password}, timeout=30.0)
    status, login = _request("POST", "/api/login", {"username": user, "password": password}, timeout=30.0)
    assert status == 200, f"логин администратора: {login}"
    token = login["access_token"]
    status_u, users = _request(
        "GET",
        "/api/users",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    assert status_u == 200
    assert "users" in users
    names = {u["username"] for u in users["users"]}
    assert user in names
