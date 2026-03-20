from __future__ import annotations

"""Сущность `AgroDroneEntity` (Агро-дрон): исполняет миссию и запрашивает landing."""

from typing import Any, Dict

from actions import (
    AGRO_MISSION_RECEIVED,
    REQUEST_TAKEOFF_PERMISSION,
    CHECK_DRONEPORT_READY,
    SITL_SIMULATE,
    REQUEST_LANDING_PERMISSION,
)
from base_entity import BaseEntity


class AgroDroneEntity(BaseEntity):
    """Агро-дрон: выполняет миссию после разрешений и проверок Дронопорта."""

    def handle_request(self, msg: Dict[str, Any]) -> None:
        if msg.get("action") != AGRO_MISSION_RECEIVED:
            self.send_response(request_msg=msg, payload={"status": "error", "error": "unknown_action"})
            return

        payload = msg["payload"]
        mission_details = payload["mission_details"]
        mission_id = mission_details["mission_id"]
        uas_id = payload["uas_id"]
        starting_droneport_id = payload["droneport_id"]
        insurance_payment_id = payload.get("insurance_payment_id")
        scenario = payload.get("scenario")

        # 1) ОрВД -> дрон: разрешение на вылет
        takeoff = self.rpc_send_wait(
            receiver="atm",
            action=REQUEST_TAKEOFF_PERMISSION,
            payload={
                "mission_id": mission_id,
                "uas_id": uas_id,
                "insurance_payment_id": insurance_payment_id,
            },
            timeout_s=30.0,
            expected_sender="atm",
        )
        if not takeoff.get("approved"):
            self.send_response(request_msg=msg, payload={"status": "error", "error": "takeoff_permission_denied"})
            return

        # 2) Дрон перед вылетом проверяет готовность выбранного Дронопорта (release конкретной БАС)
        ready = self.rpc_send_wait(
            receiver=starting_droneport_id,
            action=CHECK_DRONEPORT_READY,
            payload={"mission_id": mission_id, "uas_id": uas_id},
            timeout_s=30.0,
            expected_sender=starting_droneport_id,
        )
        if not ready.get("takeoff_allowed"):
            self.send_response(request_msg=msg, payload={"status": "error", "error": "droneport_not_ready"})
            return

        # 3) SITL (опционально)
        _ = self.rpc_send_wait(
            receiver="sitl",
            action=SITL_SIMULATE,
            payload={"mission_id": mission_id, "scenario": scenario},
            timeout_s=30.0,
            expected_sender="sitl",
        )

        # 4) После миссии дрон возвращается на return_port из согласованной миссии
        return_port = mission_details["return_port"]
        landing_coordinates = mission_details["landing_coordinates"]

        landing = self.rpc_send_wait(
            receiver=return_port,
            action=REQUEST_LANDING_PERMISSION,
            payload={
                "mission_id": mission_id,
                "uas_id": uas_id,
                "landing_coordinates": landing_coordinates,
            },
            timeout_s=30.0,
            expected_sender=return_port,
        )

        if not landing.get("landing_allowed"):
            self.send_response(request_msg=msg, payload={"status": "error", "error": "landing_denied"})
            return

        self.send_response(
            request_msg=msg,
            payload={
                "status": "ok",
                "landing_coordinates": landing.get("landing_coordinates"),
                "mission_id": mission_id,
                "uas_id": uas_id,
            },
        )

