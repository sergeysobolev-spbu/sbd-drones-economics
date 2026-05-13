"""Small HTTP backend used behind nginx for the prototype UI."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import unquote, urlparse

from gateway.bus_backend import BusApiContext, BusInvocationError
from shared.jwt_tokens import TokenError, create_access_token, verify_access_token
from shared.models import SecurityEvent
from shared.tcb import AuthorizationError
from shared.topics import Roles


def _json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    content_length = int(handler.headers.get("Content-Length", "0"))
    if content_length == 0:
        return {}
    body = handler.rfile.read(content_length).decode("utf-8")
    return json.loads(body)


def _bearer_principal(handler: BaseHTTPRequestHandler, ctx: Any) -> tuple[str, str]:
    """Из заголовка Authorization извлечь (username, role)."""
    auth = handler.headers.get("Authorization", "").strip()
    if not auth.lower().startswith("bearer "):
        raise AuthorizationError("missing bearer token")
    token = auth[7:].strip()
    if not token:
        raise AuthorizationError("empty bearer token")
    try:
        payload = verify_access_token(ctx.jwt_secret, token)
    except TokenError as exc:
        raise AuthorizationError(str(exc)) from exc
    username = str(payload.get("sub") or "").strip()
    role = str(payload.get("role") or "").strip()
    if not username or not role:
        raise AuthorizationError("invalid token payload")
    return username, role


def _http_status_for_login_bus_error(exc: BusInvocationError) -> int:
    """Ошибка входа по шине: отказ в авторизации — не 502; транспортные сбои оставляем для прокси-домена."""
    msg = str(exc).lower()
    transient = (
        msg == "security_monitor_request_timeout"
        or "timeout" in msg
        or msg == "invalid_monitor_payload"
        or msg == "missing_target_response"
        or "monitor_transport" in msg
    )
    return 502 if transient else 401


class ApiHandler(BaseHTTPRequestHandler):
    """JSON API для веб-интерфейса и интеграционных проверок."""

    context: Any

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        try:
            if path == "/health":
                self._send({"ok": True, "service": "uas_dev_company"})
                return
            if path == "/api/users":
                _, role = _bearer_principal(self, self.context)
                result = {"users": self.context.users.list_users(role)}
                self._audit_ok("/api/users")
                self._send(result)
                return
            if path == "/api/certificates":
                _, role = _bearer_principal(self, self.context)
                result = {"certificates": self.context.certification.list_certificates(role)}
                self._audit_ok("/api/certificates")
                self._send(result)
                return
            if path == "/api/drones":
                _, role = _bearer_principal(self, self.context)
                result = {"drones": self.context.registry.list_registered(role)}
                self._audit_ok("/api/drones")
                self._send(result)
                return
            self._send({"error": "not_found"}, status=404)
        except (AuthorizationError, PermissionError) as exc:
            self._send({"error": str(exc)}, status=401)
        except BusInvocationError as exc:
            self._audit_err(path, exc)
            self._send({"error": str(exc)}, status=502)
        except Exception as exc:
            self._audit_err(self.path, exc)
            self._send({"error": str(exc)}, status=400)

    def do_PATCH(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        try:
            if path.startswith("/api/users/"):
                username = unquote(path[len("/api/users/") :])
                _, role = _bearer_principal(self, self.context)
                body = _json_body(self)
                is_active = bool(body.get("is_active", True))
                result = self.context.users.set_user_active(role, username, is_active)
                self._audit_ok(path)
                self._send(result)
                return
            self._send({"error": "not_found"}, status=404)
        except (AuthorizationError, PermissionError) as exc:
            self._send({"error": str(exc)}, status=401)
        except BusInvocationError as exc:
            self._audit_err(path, exc)
            self._send({"error": str(exc)}, status=502)
        except Exception as exc:
            self._audit_err(self.path, exc)
            self._send({"error": str(exc)}, status=400)

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        try:
            if path.startswith("/api/users/"):
                username = unquote(path[len("/api/users/") :])
                _, role = _bearer_principal(self, self.context)
                result = self.context.users.delete_user(role, username)
                self._audit_ok(path)
                self._send(result)
                return
            self._send({"error": "not_found"}, status=404)
        except (AuthorizationError, PermissionError) as exc:
            self._send({"error": str(exc)}, status=401)
        except BusInvocationError as exc:
            self._audit_err(path, exc)
            self._send({"error": str(exc)}, status=502)
        except Exception as exc:
            self._audit_err(self.path, exc)
            self._send({"error": str(exc)}, status=400)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        payload = _json_body(self)
        try:
            if path == "/api/login":
                user = self.context.users.authenticate(
                    str(payload.get("username", "")).strip(),
                    str(payload.get("password", "")),
                )
                token = create_access_token(
                    self.context.jwt_secret,
                    user["username"],
                    user["role"],
                )
                self._audit_ok("/api/login")
                self._send({"access_token": token, "token_type": "Bearer"})
                return
            if path == "/api/bootstrap-admin":
                result = self.context.users.bootstrap_admin(payload["username"], payload["password"])
                self._audit_ok("/api/bootstrap-admin")
                self._send(result)
                return

            actor_name, actor_role = _bearer_principal(self, self.context)

            if path == "/api/users":
                result = self.context.users.create_user(
                    actor_role,
                    str(payload.get("username", "")).strip(),
                    str(payload.get("role", "")).strip(),
                    str(payload.get("password", "")),
                )
                self._audit_ok("/api/users")
                self._send(result)
                return
            if path == "/api/firmware":
                submitted_by = str(payload.get("submitted_by", actor_name)).strip() or actor_name
                result = self.context.firmware.submit(actor_role, submitted_by, payload)
                self._audit_ok("/api/firmware")
                self._send(result)
                return
            if path == "/api/certify":
                fid = str(payload.get("firmware_id", "")).strip()
                req_by = str(payload.get("requested_by", actor_name)).strip() or actor_name
                result = self.context.certification.certify(actor_role, req_by, fid)
                self._audit_ok("/api/certify")
                self._send(result)
                return
            if path == "/api/register-drone":
                result = self.context.registry.register(actor_role, payload)
                self._audit_ok("/api/register-drone")
                self._send(result)
                return
            if path == "/api/purchase":
                serial = str(payload.get("serial_number", "")).strip()
                buyer = str(payload.get("operator_username", actor_name)).strip() or actor_name
                result = self.context.purchase.purchase(actor_role, buyer, serial)
                self._audit_ok("/api/purchase")
                self._send(result)
                return

            self._send({"error": "not_found"}, status=404)
        except AuthorizationError as exc:
            if path == "/api/login":
                self._audit_err(path, exc)
                self._send({"error": str(exc)}, status=401)
            else:
                self._audit_err(path, exc)
                self._send({"error": str(exc)}, status=401)
        except BusInvocationError as exc:
            self._audit_err(path, exc)
            if path == "/api/login":
                st = _http_status_for_login_bus_error(exc)
            else:
                st = 502
            self._send({"error": str(exc)}, status=st)
        except Exception as exc:
            self._audit_err(path, exc)
            self._send({"error": str(exc)}, status=400)

    def _audit_ok(self, subject: str) -> None:
        try:
            self.context.audit.log(SecurityEvent("api_request", "info", "api_gateway", subject))
        except Exception:
            pass

    def _audit_err(self, subject: str, exc: Exception) -> None:
        try:
            self.context.audit.log(SecurityEvent("api_error", "warning", "api_gateway", subject, str(exc)))
        except Exception:
            pass

    def _send(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run() -> None:
    """Run the HTTP backend."""
    mode = os.environ.get("UAS_GATEWAY_BACKEND", "bus").strip().lower()
    if mode == "bus":
        ctx = BusApiContext()
        ctx.start()
        from shared.journal_bootstrap import emit_api_gateway_bus_started

        emit_api_gateway_bus_started(ctx.backend.bus)
        ApiHandler.context = ctx
    else:
        from gateway.sqlite_context import ApiContext
        from shared.journal_startup import emit_api_gateway_sqlite_started

        ctx = ApiContext()
        emit_api_gateway_sqlite_started(ctx.audit)
        ApiHandler.context = ctx
    port = int(os.environ.get("BACKEND_PORT", "8081"))
    server = ThreadingHTTPServer(("0.0.0.0", port), ApiHandler)
    print(f"uas_dev_company api ({mode}) listening on {port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
