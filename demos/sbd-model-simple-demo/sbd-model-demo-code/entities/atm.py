from __future__ import annotations

"""Сущность `ATMEntity` (ОрВД БАС): согласует миссию и разрешает вылет."""

from typing import Any, Dict, Set

from actions import VALIDATE_MISSION, REQUEST_TAKEOFF_PERMISSION
from base_entity import BaseEntity


class ATMEntity(BaseEntity):
    """ОрВД БАС (ATM): согласует миссии и выдаёт разрешение на вылет."""

    def __init__(
        self,
        *,
        entity_id: str,
        inbox_queue: Any,
        broker_in_queue: Any,
        reply_queue: Any,
        reply_queue_name: str,
        world: Dict[str, Any],
    ) -> None:
        super().__init__(
            entity_id=entity_id,
            inbox_queue=inbox_queue,
            broker_in_queue=broker_in_queue,
            reply_queue=reply_queue,
            reply_queue_name=reply_queue_name,
            world=world,
        )
        self._approved_missions: Set[str] = set()

    def _register_handlers(self) -> None:
        self.register_handler(VALIDATE_MISSION, self._on_validate_mission)
        self.register_handler(REQUEST_TAKEOFF_PERMISSION, self._on_takeoff_permission)

    def _on_validate_mission(self, msg: Dict[str, Any]) -> None:
        mission_details = msg["payload"]["mission_details"]
        mission_id = mission_details["mission_id"]
        self._approved_missions.add(mission_id)
        self.send_response(
            request_msg=msg,
            payload={"status": "ok", "approved": True, "mission_id": mission_id},
        )

    def _on_takeoff_permission(self, msg: Dict[str, Any]) -> None:
        mission_id = msg["payload"].get("mission_id")
        approved = mission_id in self._approved_missions
        self.send_response(
            request_msg=msg,
            payload={
                "status": "ok",
                "approved": approved,
                "takeoff_allowed": approved,
                "mission_id": mission_id,
            },
        )
