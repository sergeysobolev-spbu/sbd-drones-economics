from __future__ import annotations

"""Сущность `GCSEntity` (GCS): планирует миссию и формирует mission_details."""

from typing import Any, Dict

from actions import MISSION_PLANNING
from base_entity import BaseEntity


class GCSEntity(BaseEntity):
    """GCS: планирует миссию и подготавливает согласованные mission_details."""

    def _register_handlers(self) -> None:
        self.register_handler(MISSION_PLANNING, self._on_mission_planning)

    def _on_mission_planning(self, msg: Dict[str, Any]) -> None:
        order = msg["payload"]["order"]
        selected_uas = msg["payload"]["selected_uas"]
        order_security_goals = msg["payload"].get("order_security_goals", [])

        mission_id = f"mission-{msg['correlation_id'][:8]}"
        order_id = order["id"]
        start_droneport_id = selected_uas["droneport_id"]
        return_port = (
            order.get("return_port")
            or self.world.get("default_return_port")
            or start_droneport_id
        )
        landing_coordinates = self.world["landing_sites"][order_id][return_port]

        self.send_response(
            request_msg=msg,
            payload={
                "status": "ok",
                "mission_details": {
                    "mission_id": mission_id,
                    "order_id": order_id,
                    "uas_id": selected_uas["uas_id"],
                    "droneport_id": start_droneport_id,
                    "return_port": return_port,
                    "landing_site": return_port,
                    "landing_coordinates": landing_coordinates,
                },
                "mission_security_goals": list(order_security_goals),
            },
        )
