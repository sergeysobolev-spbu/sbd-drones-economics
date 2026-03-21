from __future__ import annotations

"""Сущность `DronePortEntity`: готовность, dispatch и разрешения на посадку."""

from typing import Any, Dict, List

from actions import (
    GET_AVAILABLE_UAS,
    PREPARE_DISPATCH,
    CHECK_DRONEPORT_READY,
    REQUEST_LANDING_PERMISSION,
    ASSIGN_UAS_TO_DRONEPORT,
)
from base_entity import BaseEntity


class DronePortEntity(BaseEntity):
    """
    Дронопорт:
    - список доступных БАС по task_type
    - dispatch (mission_id -> uas_id)
    - готовность к вылету
    - допуск на посадку и landing_coordinates
    """

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
        self._dispatch_state: Dict[str, str] = {}

    def _register_handlers(self) -> None:
        self.register_handler(GET_AVAILABLE_UAS, self._on_get_available_uas)
        self.register_handler(PREPARE_DISPATCH, self._on_prepare_dispatch)
        self.register_handler(CHECK_DRONEPORT_READY, self._on_check_ready)
        self.register_handler(REQUEST_LANDING_PERMISSION, self._on_landing_permission)
        self.register_handler(ASSIGN_UAS_TO_DRONEPORT, self._on_assign_uas)

    def _on_get_available_uas(self, msg: Dict[str, Any]) -> None:
        task_type = msg["payload"].get("task_type")
        park = self.world["dronports"][self.entity_id]["uas"]
        available: List[Dict[str, Any]] = [
            u for u in park if task_type in u.get("supported_task_types", [])
        ]
        self.send_response(request_msg=msg, payload={"status": "ok", "available_uas": available})

    def _on_prepare_dispatch(self, msg: Dict[str, Any]) -> None:
        mission_id = msg["payload"].get("mission_id")
        uas_id = msg["payload"].get("uas_id")
        self._dispatch_state[mission_id] = uas_id
        self.send_response(request_msg=msg, payload={"status": "ok", "dispatch_ready": True})

    def _on_check_ready(self, msg: Dict[str, Any]) -> None:
        mission_id = msg["payload"].get("mission_id")
        uas_id = msg["payload"].get("uas_id")
        takeoff_allowed = self._dispatch_state.get(mission_id) == uas_id
        self.send_response(
            request_msg=msg,
            payload={"status": "ok", "takeoff_allowed": takeoff_allowed},
        )

    def _on_landing_permission(self, msg: Dict[str, Any]) -> None:
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

    def _on_assign_uas(self, msg: Dict[str, Any]) -> None:
        uas_items = list(msg["payload"].get("uas_items", []))
        park = self.world["dronports"][self.entity_id]["uas"]
        park.extend(uas_items)
        self.send_response(
            request_msg=msg,
            payload={
                "status": "ok",
                "assigned_count": len(uas_items),
                "droneport_id": self.entity_id,
            },
        )
