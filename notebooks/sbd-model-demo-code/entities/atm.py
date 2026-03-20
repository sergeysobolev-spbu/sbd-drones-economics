from __future__ import annotations

"""Сущность `ATMEntity` (ОрВД БАС): согласует миссию и разрешает вылет."""

from typing import Any, Dict, Set

from actions import VALIDATE_MISSION, REQUEST_TAKEOFF_PERMISSION
from base_entity import BaseEntity


class ATMEntity(BaseEntity):
    """ОрВД БАС (ATM): согласует миссии и выдаёт разрешение на вылет."""

    def __init__(self, *, entity_id: str, inbox_queue: Any, broker_in_queue: Any, reply_queue: Any, reply_queue_name: str, world: Dict[str, Any]):
        super().__init__(
            entity_id=entity_id,
            inbox_queue=inbox_queue,
            broker_in_queue=broker_in_queue,
            reply_queue=reply_queue,
            reply_queue_name=reply_queue_name,
            world=world,
        )
        self._approved_missions: Set[str] = set()

    def handle_request(self, msg: Dict[str, Any]) -> None:
        action = msg.get("action")

        if action == VALIDATE_MISSION:
            mission_details = msg["payload"]["mission_details"]
            mission_id = mission_details["mission_id"]
            self._approved_missions.add(mission_id)
            self.send_response(request_msg=msg, payload={"status": "ok", "approved": True, "mission_id": mission_id})
            return

        if action == REQUEST_TAKEOFF_PERMISSION:
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
            return

        self.send_response(request_msg=msg, payload={"status": "error", "error": "unknown_action"})

