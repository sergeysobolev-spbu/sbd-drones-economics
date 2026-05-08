"""Обработчики сообщений drone_registry."""

from __future__ import annotations

from typing import Any, Callable

from drone_registry.registry_service import DroneRegistryService
from shared.storage import SQLiteStorage
from shared.topics import Actions, ComponentTopics
from shared.worker_deps import WorkerServiceDeps


def build_drone_registry_handlers(
    storage: SQLiteStorage,
    deps: WorkerServiceDeps,
) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
    assert deps.monitor_proxy_call is not None

    def _cert_snap(cid: str, fid: str):
        r = deps.monitor_proxy_call(
            ComponentTopics.CERTIFICATION_SERVICE,
            Actions.GET_CERTIFICATE_SNAPSHOT,
            {"certificate_id": cid, "firmware_id": fid},
        )
        return r.get("snapshot")

    def _fw_row(fid: str):
        r = deps.monitor_proxy_call(
            ComponentTopics.FIRMWARE_INGESTION,
            Actions.GET_FIRMWARE_ROW,
            {"firmware_id": fid},
        )
        return r.get("row")

    reg = DroneRegistryService(
        storage,
        regulator=deps.regulator,
        security_journal=deps.security_journal,
        operator_fleet=deps.operator_fleet,
        certificate_snapshot=_cert_snap,
        firmware_row=_fw_row,
    )

    def register_drone(payload: dict[str, Any]) -> dict[str, Any]:
        inner = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        return reg.register(str(payload["actor_role"]), inner)

    def list_drones(payload: dict[str, Any]) -> dict[str, Any]:
        rows = reg.list_registered(str(payload["actor_role"]))
        return {"drones": rows}

    def get_drone_purchase_row(payload: dict[str, Any]) -> dict[str, Any]:
        sn = str(payload.get("serial_number") or "").strip()
        row = reg.get_drone_purchase_row(sn)
        return {"drone": row}

    def update_drone_purchase(payload: dict[str, Any]) -> dict[str, Any]:
        phase = str(payload.get("phase") or "purchase")
        sn = str(payload["serial_number"])
        if phase == "delivery":
            reg.update_drone_delivery(
                sn,
                delivery_status=str(payload.get("delivery_status") or ""),
                delivered_at=str(payload.get("delivered_at") or ""),
                physical_safety_responsibility=str(payload.get("physical_safety_responsibility") or ""),
            )
            return {"ok": True}
        reg.update_drone_after_purchase(
            sn,
            operator_username=str(payload["operator_username"]),
            dest=str(payload.get("dest") or ""),
            r_corr=str(payload["r_corr"]),
            regulator_mode=bool(payload.get("regulator_mode")),
            new_reg_version=int(payload.get("new_reg_version") or 1),
            updated_goals_json=payload.get("updated_goals_json"),
        )
        return {"ok": True}

    def apply_firmware_cert_decision(payload: dict[str, Any]) -> dict[str, Any]:
        return reg.apply_firmware_cert_decision(
            str(payload.get("firmware_id") or ""),
            dict(payload.get("decision") or {}),
        )

    return {
        Actions.REGISTER_DRONE: register_drone,
        Actions.LIST_REGISTERED_DRONES: list_drones,
        Actions.GET_DRONE_PURCHASE_ROW: get_drone_purchase_row,
        Actions.UPDATE_DRONE_PURCHASE: update_drone_purchase,
        Actions.APPLY_FIRMWARE_CERT_DECISION: apply_firmware_cert_decision,
    }
