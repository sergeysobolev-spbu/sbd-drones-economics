"""Разбор ответа security_monitor на proxy_request (общий для gateway и воркеров, Задача 23)."""

from __future__ import annotations

from typing import Any


class BusInvocationError(RuntimeError):
    """Raised when the monitor or a backend rejects a proxied RPC."""


def unwrap_monitor_proxy_result(raw: dict[str, Any] | None) -> dict[str, Any]:
    if raw is None:
        raise BusInvocationError("security_monitor_request_timeout")
    if not raw.get("success"):
        raise BusInvocationError(str(raw.get("error") or "monitor_transport_error"))
    mp = raw.get("payload")
    if not isinstance(mp, dict):
        raise BusInvocationError("invalid_monitor_payload")
    if mp.get("ok") is False:
        err = str(mp.get("error") or "policy_or_routing_error")
        raise BusInvocationError(err)
    target = mp.get("target_response")
    if not isinstance(target, dict):
        raise BusInvocationError("missing_target_response")
    if not target.get("success"):
        raise BusInvocationError(str(target.get("error") or "backend_error"))
    inner = target.get("payload")
    if not isinstance(inner, dict):
        return {}
    return inner


__all__ = ["BusInvocationError", "unwrap_monitor_proxy_result"]
