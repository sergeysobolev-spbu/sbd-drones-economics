"""Обработчики сообщений purchase_service."""

from __future__ import annotations

from typing import Any, Callable

from shared.services import PurchaseService
from shared.storage import SQLiteStorage
from shared.topics import Actions
from shared.worker_deps import WorkerServiceDeps


def build_purchase_handlers(
    storage: SQLiteStorage,
    deps: WorkerServiceDeps,
) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
    purchase = PurchaseService(
        storage,
        regulator=deps.regulator,
        security_journal=deps.security_journal,
        operator_fleet=deps.operator_fleet,
        drone_port=deps.drone_port,
    )

    def purchase_drone(payload: dict[str, Any]) -> dict[str, Any]:
        return purchase.purchase(
            str(payload["actor_role"]),
            str(payload["operator_username"]),
            str(payload["serial_number"]),
        )

    return {Actions.PURCHASE_DRONE: purchase_drone}
