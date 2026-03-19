"""
Mission Planner Component (D1_TRUSTED).

Компонент реализует протокол `sdk.base_component.BaseComponent`:
- сообщения маршрутизируются по полю `action`
- request/response идёт через `reply_to` + `correlation_id`
"""

from __future__ import annotations

import math
import os
import time
from typing import Any, Dict
from uuid import uuid4

from broker.system_bus import SystemBus
from sdk.base_component import BaseComponent
from sdk.event_emitter import emit_event
from systems.operator.src.topics import ComponentTopics, MissionPlannerActions


class MissionPlanner(BaseComponent):
    def __init__(self, component_id: str, bus: SystemBus):
        super().__init__(
            component_id=component_id,
            component_type="mission_planner",
            topic=ComponentTopics.get_mission_planner(),
            bus=bus,
            enable_tracing=True,
        )
        # Простое хранилище миссий для интеграционного сценария.
        self._missions: Dict[str, Dict[str, Any]] = {}

    def _register_handlers(self):
        self.register_handler(MissionPlannerActions.CREATE_MISSION, self._handle_create_mission)
        self.register_handler(MissionPlannerActions.VALIDATE_MISSION, self._handle_validate_mission)
        self.register_handler(MissionPlannerActions.REQUEST_UTM_APPROVAL, self._handle_request_utm_approval)
        self.register_handler(MissionPlannerActions.UPDATE_MISSION_STATUS, self._handle_update_mission_status)
        self.register_handler(MissionPlannerActions.GET_MISSION_DETAILS, self._handle_get_mission_details)
        self.register_handler(MissionPlannerActions.CALCULATE_ROUTE, self._handle_calculate_route)
        self.register_handler(MissionPlannerActions.CHECK_AIRSPACE, self._handle_check_airspace)

    async def _handle_create_mission(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {}) or {}
        order = payload.get("order", {}) or {}

        mission_id = payload.get("mission_id") or f"MISSION-{uuid4().hex[:8].upper()}"
        distance_km = self._derive_distance_km(order)
        payload_weight = float(order.get("payload_weight", 0) or 0)

        self._missions[mission_id] = {
            "mission_id": mission_id,
            "status": "draft",
            "distance": distance_km,
            "payload_weight": payload_weight,
            "order_id": order.get("id"),
            "updated_at": time.time(),
        }

        emit_event(
            self.bus,
            ComponentTopics.get_event_journal(),
            event_type="mission_created",
            severity="info",
            source_component=self.component_type,
            payload={"mission_id": mission_id, "order_id": order.get("id"), "distance": distance_km},
            trace_context=None,
        )

        return {"mission_id": mission_id, "status": "draft", "distance": distance_km}

    async def _handle_validate_mission(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {}) or {}
        mission_id = payload.get("mission_id")
        if not mission_id:
            return {"valid": False, "error": "mission_id is required"}

        # Упрощённая валидация для интеграционного сценария.
        emit_event(
            self.bus,
            ComponentTopics.get_event_journal(),
            event_type="mission_validated",
            severity="info",
            source_component=self.component_type,
            payload={"mission_id": mission_id},
            trace_context=None,
        )
        return {"valid": True, "validation_results": []}

    async def _handle_get_mission_details(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {}) or {}
        mission_id = payload.get("mission_id")
        if not mission_id:
            return {"error": "mission_id is required"}

        mission = self._missions.get(mission_id)
        if not mission:
            return {"error": f"Mission {mission_id} not found"}

        return {
            "mission_id": mission_id,
            "distance": mission.get("distance", 0.0),
            "payload_weight": mission.get("payload_weight", 0.0),
        }

    async def _handle_request_utm_approval(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {}) or {}
        mission_id = payload.get("mission_id")
        if not mission_id:
            return {"approved": False, "error": "mission_id is required"}

        approval_id = f"UTM-APPROVAL-{uuid4().hex[:8].upper()}"
        return {"approved": True, "approval_id": approval_id, "mission_id": mission_id}

    async def _handle_update_mission_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {}) or {}
        mission_id = payload.get("mission_id")
        status = payload.get("status")
        if not mission_id or not status:
            return {"error": "mission_id and status are required"}

        mission = self._missions.setdefault(mission_id, {"mission_id": mission_id})
        mission["status"] = status
        mission["updated_at"] = time.time()
        if payload.get("reason"):
            mission["reason"] = payload.get("reason")
        return {"updated": True, "mission_id": mission_id, "status": status}

    async def _handle_calculate_route(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = message.get("payload", {}) or {}
        order = payload.get("order", {}) or {}
        distance_km = self._derive_distance_km(order)
        return {"distance": distance_km, "waypoints_count": 2}

    async def _handle_check_airspace(self, message: Dict[str, Any]) -> Dict[str, Any]:
        # Заглушка: в текущем интеграционном стенде считаем пространство доступным.
        return {"allowed": True, "restrictions": []}

    def _derive_distance_km(self, order: Dict[str, Any]) -> float:
        if "distance" in order and order["distance"] is not None:
            try:
                return float(order["distance"])
            except (TypeError, ValueError):
                pass

        start = order.get("start_location") or order.get("pickup") or {}
        end = order.get("end_location") or order.get("dropoff") or {}
        try:
            lat1, lon1 = float(start["lat"]), float(start["lon"])
            lat2, lon2 = float(end["lat"]), float(end["lon"])
        except Exception:
            # Фоллбек на небольшой маршрут
            return float(os.getenv("DEFAULT_MISSION_DISTANCE_KM", "10.5"))

        return self._haversine_km(lat1, lon1, lat2, lon2)

    def _haversine_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)

        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return r * c
