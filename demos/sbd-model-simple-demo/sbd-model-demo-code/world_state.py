from __future__ import annotations

"""YAML-снимок «мира» демо: загрузка, сохранение, сброс, слияние после онбординга."""

from pathlib import Path
from typing import Any, Dict, List

import yaml


def build_world() -> Dict[str, Any]:
    """Начальное состояние всех сущностей (как тестовые данные)."""
    return {
        "aggregator_constants": {"agro": ["SG_ID_CONSTR_010"]},
        "operator_ids": ["operator_1", "operator_2"],
        "system_security_goals": {
            "operator_1": ["SG_ID_AUTH_001", "SG_ID_SAF_002", "SG_ID_CONSTR_010"],
            "operator_2": ["SG_ID_AUTH_001", "SG_ID_SAF_002"],
        },
        "operators": {
            "operator_1": {
                "system_security_goals": ["SG_ID_AUTH_001", "SG_ID_SAF_002", "SG_ID_CONSTR_010"]
            },
            "operator_2": {"system_security_goals": ["SG_ID_AUTH_001", "SG_ID_SAF_002"]},
        },
        "default_return_port": "droneport_B",
        "dronports": {
            "droneport_A": {
                "uas": [
                    {
                        "uas_id": "uas_A_01",
                        "model_id": "agro-model-1",
                        "supported_task_types": ["agro"],
                        "base_cost": 9000.0,
                    }
                ]
            },
            "droneport_B": {
                "uas": [
                    {
                        "uas_id": "uas_B_11",
                        "model_id": "agro-model-3",
                        "supported_task_types": ["agro"],
                        "base_cost": 9500.0,
                    }
                ]
            },
        },
        "landing_sites": {
            "ORDER-DEMO-001": {
                "droneport_A": [55.75, 37.61],
                "droneport_B": [55.76, 37.62],
            }
        },
        "registration_counters": {},
        "uas_registry": {},
        "firmware_certificates": [],
    }


def save_world_state(path: str | Path, world: Dict[str, Any]) -> None:
    """Атомарная запись YAML."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            world,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )
    tmp.replace(path)


def load_world_state(path: str | Path) -> Dict[str, Any]:
    """Загрузка мира из YAML; при отсутствии файла — дефолт."""
    path = Path(path)
    if not path.is_file():
        return build_world()
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        return build_world()
    return data


def reset_context(path: str | Path) -> Dict[str, Any]:
    """Сброс хранилища к начальному миру и запись на диск."""
    world = build_world()
    save_world_state(path, world)
    return world


def sync_registration_counters(world: Dict[str, Any]) -> None:
    """Восстанавливает registration_counters из идентификаторов UAS-* в uas_registry."""
    counters: Dict[str, int] = world.setdefault("registration_counters", {})
    registry = world.get("uas_registry", {})
    for uas_id in registry:
        parts = uas_id.split("-")
        if len(parts) != 4 or parts[0] != "UAS":
            continue
        uas_type, vendor, num_s = parts[1], parts[2], parts[3]
        try:
            num = int(num_s)
        except ValueError:
            continue
        key = f"{uas_type}:{vendor}"
        counters[key] = max(counters.get(key, 0), num)


def merge_onboarding_into_world(world: Dict[str, Any], artifacts: Dict[str, Any]) -> None:
    """
    Вносит в мир результаты сценария онбординга (из ответов оркестратора).

    artifacts ожидает ключи: firmware_cert, standalone_registration (опц.),
    purchase (опц.: registered_uas_ids, droneport_id, uas_items, imeis).
    """
    world.setdefault("firmware_certificates", []).append(artifacts["firmware_cert"])

    standalone = artifacts.get("standalone_registration") or {}
    if standalone.get("registered_uas_id"):
        uid = standalone["registered_uas_id"]
        world.setdefault("uas_registry", {})[uid] = {
            "imei": standalone.get("imei"),
            "uas_type": standalone.get("uas_type"),
            "vendor_code": standalone.get("vendor_code"),
            "firmware_version": standalone.get("firmware_version"),
        }

    purchase = artifacts.get("purchase") or {}
    if purchase.get("registered_uas_ids"):
        dp_id = purchase["droneport_id"]
        uas_items: List[Dict[str, Any]] = list(purchase.get("uas_items", []))
        imeis: List[str] = list(purchase.get("imeis", []))
        world.setdefault("dronports", {}).setdefault(dp_id, {}).setdefault("uas", [])
        # Избегаем дублирования по uas_id
        existing = {u["uas_id"] for u in world["dronports"][dp_id]["uas"]}
        for item in uas_items:
            if item.get("uas_id") not in existing:
                world["dronports"][dp_id]["uas"].append(item)
                existing.add(item["uas_id"])
        reg = world.setdefault("uas_registry", {})
        for i, uid in enumerate(purchase["registered_uas_ids"]):
            imei = imeis[i] if i < len(imeis) else None
            reg.setdefault(
                uid,
                {
                    "imei": imei,
                    "uas_type": purchase.get("uas_type"),
                    "vendor_code": purchase.get("vendor_code"),
                    "firmware_version": purchase.get("firmware_version"),
                },
            )

    sync_registration_counters(world)
