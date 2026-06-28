from __future__ import annotations

"""Сущность `SITLEntity`: заглушка симулятора."""

from typing import Any, Dict

from actions import SITL_SIMULATE
from base_entity import BaseEntity


class SITLEntity(BaseEntity):
    """СИТЛ: заглушка симуляции и телеметрии."""

    def _register_handlers(self) -> None:
        self.register_handler(SITL_SIMULATE, self._on_sitl_simulate)

    def _on_sitl_simulate(self, msg: Dict[str, Any]) -> None:
        mission_id = msg["payload"].get("mission_id")
        self.send_response(
            request_msg=msg,
            payload={
                "status": "ok",
                "simulation_result": {"mission_id": mission_id, "telemetry": {"status": "simulated"}},
            },
        )
