from __future__ import annotations

"""Сущность `DronePortEntity`: готовность, dispatch и разрешения на посадку."""

from typing import Any, Dict, List

from actions import (
    GET_AVAILABLE_UAS,
    PREPARE_DISPATCH,
    CHECK_DRONEPORT_READY,
    REQUEST_LANDING_PERMISSION,
)
from base_entity import BaseEntity


class DronePortEntity(BaseEntity):
    """
    Дронопорт:
    - отдаёт список доступных БАС по task_type
    - готовит dispatch (mission_id -> uas_id)
    - выдаёт подтверждение готовности на вылет
    - после миссии выдаёт допуск на посадку и landing_coordinates
    """

    def __init__(self, *, entity_id: str, inbox_queue: Any, broker_in_queue: Any, reply_queue: Any, reply_queue_name: str, world: Dict[str, Any]):
        super().__init__(
            entity_id=entity_id,
            inbox_queue=inbox_queue,
            broker_in_queue=broker_in_queue,
            reply_queue=reply_queue,
            reply_queue_name=reply_queue_name,
            world=world,
        )
        self._dispatch_state: Dict[str, str] = {}  # mission_id -> uas_id

    def handle_request(self, msg: Dict[str, Any]) -> None:
        action = msg.get("action")
        if action == GET_AVAILABLE_UAS:
            task_type = msg["payload"].get("task_type")
            park = self.world["dronports"][self.entity_id]["uas"]
            available: List[Dict[str, Any]] = [
                u for u in park if task_type in u.get("supported_task_types", [])
            ]
            self.send_response(request_msg=msg, payload={"status": "ok", "available_uas": available})
            return

        if action == PREPARE_DISPATCH:
            mission_id = msg["payload"].get("mission_id")
            uas_id = msg["payload"].get("uas_id")
            self._dispatch_state[mission_id] = uas_id
            self.send_response(request_msg=msg, payload={"status": "ok", "dispatch_ready": True})
            return

        if action == CHECK_DRONEPORT_READY:
            mission_id = msg["payload"].get("mission_id")
            uas_id = msg["payload"].get("uas_id")
            takeoff_allowed = self._dispatch_state.get(mission_id) == uas_id
            self.send_response(request_msg=msg, payload={"status": "ok", "takeoff_allowed": takeoff_allowed})
            return

        if action == REQUEST_LANDING_PERMISSION:
            landing_coordinates = msg["payload"].get("landing_coordinates")
            landing_allowed = landing_coordinates is not None
            self.send_response(
                request_msg=msg,
                payload={
                    "status": "ok",
                    "landing_allowed": landing_allowed,
                    "landing_coordinates": landing_coordinates,
                },
            )
            return

        self.send_response(request_msg=msg, payload={"status": "error", "error": "unknown_action"})

