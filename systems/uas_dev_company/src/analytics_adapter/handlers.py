"""Обработчики воркера analytics_adapter."""

from __future__ import annotations

from typing import Any, Callable

from analytics_adapter.service import analytics_adapter_service_from_env
from shared.storage import SQLiteStorage
from shared.topics import Actions
from shared.worker_deps import WorkerServiceDeps


def build_analytics_adapter_handlers(
    storage: SQLiteStorage,
    deps: WorkerServiceDeps,
) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
    svc = analytics_adapter_service_from_env(storage, deps.bus)

    def send_analytics(payload: dict[str, Any]) -> dict[str, Any]:
        ev = payload.get("event") if isinstance(payload.get("event"), dict) else {}
        svc.try_emit(ev)
        return {"ok": True}

    return {Actions.SEND_ANALYTICS: send_analytics}
