from __future__ import annotations

"""Сущность `SITLEntity`: заглушка симулятора."""

from typing import Any, Dict

from actions import SITL_SIMULATE
from base_entity import BaseEntity


class SITLEntity(BaseEntity):
    """СИТЛ: заглушка симуляции и телеметрии."""

    def handle_request(self, msg: Dict[str, Any]) -> None:
        if msg.get("action") != SITL_SIMULATE:
            self.send_response(request_msg=msg, payload={"status": "error", "error": "unknown_action"})
            return

        mission_id = msg["payload"].get("mission_id")
        self.send_response(
            request_msg=msg,
            payload={
                "status": "ok",
                "simulation_result": {"mission_id": mission_id, "telemetry": {"status": "simulated"}},
            },
        )

