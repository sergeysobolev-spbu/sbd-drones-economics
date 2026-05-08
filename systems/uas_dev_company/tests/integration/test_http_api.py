"""HTTP API: логин Bearer и защищённые маршруты."""

from __future__ import annotations

import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

import pytest

from gateway.server import ApiHandler
from gateway.sqlite_context import ApiContext


@pytest.fixture()
def http_api(tmp_path, monkeypatch):
    """Короткоживущий ThreadingHTTPServer с изолированной SQLite (monolith-файл)."""
    monkeypatch.setenv("UAS_SQLITE_MONOLITH_PATH", str(tmp_path / "http.sqlite3"))
    ApiHandler.context = ApiContext()
    server = ThreadingHTTPServer(("127.0.0.1", 0), ApiHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "127.0.0.1", port
    finally:
        server.shutdown()
        thread.join(timeout=2)


def _post(host: str, port: int, path: str, body: dict | None = None, headers: dict | None = None):
    conn = HTTPConnection(host, port, timeout=30)
    data = json.dumps(body or {}).encode("utf-8")
    hdrs = {"Content-Type": "application/json; charset=utf-8"}
    if headers:
        hdrs.update(headers)
    conn.request("POST", path, body=data, headers=hdrs)
    resp = conn.getresponse()
    raw = resp.read()
    conn.close()
    return resp.status, json.loads(raw.decode("utf-8")) if raw else {}


def _get(host: str, port: int, path: str, headers: dict | None = None):
    conn = HTTPConnection(host, port, timeout=30)
    conn.request("GET", path, headers=headers or {})
    resp = conn.getresponse()
    raw = resp.read()
    conn.close()
    return resp.status, json.loads(raw.decode("utf-8")) if raw else {}


def _patch(host: str, port: int, path: str, body: dict, headers: dict):
    conn = HTTPConnection(host, port, timeout=30)
    data = json.dumps(body).encode("utf-8")
    hdrs = {**headers, "Content-Type": "application/json; charset=utf-8"}
    conn.request("PATCH", path, body=data, headers=hdrs)
    resp = conn.getresponse()
    raw = resp.read()
    conn.close()
    return resp.status, json.loads(raw.decode("utf-8")) if raw else {}


def _delete(host: str, port: int, path: str, headers: dict):
    conn = HTTPConnection(host, port, timeout=30)
    conn.request("DELETE", path, headers=headers)
    resp = conn.getresponse()
    raw = resp.read()
    conn.close()
    return resp.status, json.loads(raw.decode("utf-8")) if raw else {}


def test_bootstrap_login_and_users_list(http_api):
    host, port = http_api
    status, boot = _post(host, port, "/api/bootstrap-admin", {"username": "root", "password": "pw"})
    assert status == 200
    assert boot["username"] == "root"

    status, login = _post(host, port, "/api/login", {"username": "root", "password": "pw"})
    assert status == 200
    token = login["access_token"]
    hdr = {"Authorization": f"Bearer {token}"}

    status, created = _post(
        host,
        port,
        "/api/users",
        {"username": "dev", "role": "разработчик", "password": "d"},
        headers=hdr,
    )
    assert status == 200
    assert created["role"] == "разработчик"

    status, users = _get(host, port, "/api/users", hdr)
    assert status == 200
    names = {u["username"] for u in users["users"]}
    assert names == {"dev", "root"}


def test_block_and_delete_user(http_api):
    host, port = http_api
    _post(host, port, "/api/bootstrap-admin", {"username": "a", "password": "p"})
    _, login = _post(host, port, "/api/login", {"username": "a", "password": "p"})
    token = login["access_token"]
    hdr = {"Authorization": f"Bearer {token}"}
    _post(host, port, "/api/users", {"username": "x", "role": "эксплуатант", "password": "q"}, headers=hdr)

    status_patch, _ = _patch(host, port, "/api/users/x", {"is_active": False}, hdr)
    assert status_patch == 200

    status_del, body = _delete(host, port, "/api/users/x", hdr)
    assert status_del == 200
    assert body["deleted"] is True


def test_wrong_login_returns_401(http_api):
    host, port = http_api
    _post(host, port, "/api/bootstrap-admin", {"username": "root", "password": "pw"})
    status, body = _post(host, port, "/api/login", {"username": "root", "password": "wrong"})
    assert status == 401
    assert "error" in body


def test_post_login_certify_register_purchase_flow(http_api):
    """Все защищённые HTTP-методы после входа (sqlite-контекст шлюза)."""
    host, port = http_api
    _post(host, port, "/api/bootstrap-admin", {"username": "adm", "password": "adm-pw"})
    _, adm_login = _post(host, port, "/api/login", {"username": "adm", "password": "adm-pw"})
    adm_hdr = {"Authorization": f"Bearer {adm_login['access_token']}"}
    _post(
        host,
        port,
        "/api/users",
        {"username": "dev1", "role": "разработчик", "password": "d"},
        headers=adm_hdr,
    )
    _post(
        host,
        port,
        "/api/users",
        {"username": "op1", "role": "эксплуатант", "password": "o"},
        headers=adm_hdr,
    )

    _, dev_login = _post(host, port, "/api/login", {"username": "dev1", "password": "d"})
    dev_hdr = {"Authorization": f"Bearer {dev_login['access_token']}"}

    fw_body = {
        "firmware_id": "fw-http",
        "supplier": "team-a",
        "drone_type": "delivery",
        "version": "1.0",
        "firmware_hash": "sha256:ab",
        "security_goals": ["ЦБ-1", "ЦБ-2"],
        "authenticity_proof": "proof",
    }
    status, fw = _post(host, port, "/api/firmware", fw_body, headers=dev_hdr)
    assert status == 200
    assert fw.get("firmware_id") == "fw-http"

    status, cert = _post(
        host,
        port,
        "/api/certify",
        {"firmware_id": "fw-http", "requested_by": "dev1"},
        headers=dev_hdr,
    )
    assert status == 200
    assert "certificate_id" in cert

    status, certs = _get(host, port, "/api/certificates", dev_hdr)
    assert status == 200
    assert any(c.get("firmware_id") == "fw-http" for c in certs["certificates"])

    reg_body = {
        "serial_number": "SN-HTTP-1",
        "drone_type": "delivery",
        "firmware_id": "fw-http",
        "certificate_id": cert["certificate_id"],
        "security_goals": ["ЦБ-1"],
        "price": 1000,
    }
    status, reg = _post(host, port, "/api/register-drone", reg_body, headers=dev_hdr)
    assert status == 200
    assert reg.get("serial_number") == "SN-HTTP-1"

    status, drones_dev = _get(host, port, "/api/drones", dev_hdr)
    assert status == 200
    assert any(d.get("serial_number") == "SN-HTTP-1" for d in drones_dev["drones"])

    _, op_login = _post(host, port, "/api/login", {"username": "op1", "password": "o"})
    op_hdr = {"Authorization": f"Bearer {op_login['access_token']}"}
    status, drones_op = _get(host, port, "/api/drones", op_hdr)
    assert status == 200
    assert any(d.get("serial_number") == "SN-HTTP-1" for d in drones_op["drones"])

    status, purchase = _post(
        host,
        port,
        "/api/purchase",
        {"serial_number": "SN-HTTP-1"},
        headers=op_hdr,
    )
    assert status == 200
    assert purchase.get("purchased") is True
