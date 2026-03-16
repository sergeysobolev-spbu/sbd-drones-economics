"""
Mission Planner - планировщик миссий

Компонент уровня D1_TRUSTED, отвечающий за планирование миссий,
взаимодействие с НУС и ОрВД для получения разрешений.
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from sdk.base_component import BaseComponent
from broker.system_bus import SystemBus
from systems.operator.src.topics import (
    ComponentTopics,
    MissionPlannerActions,
    FleetManagerActions,
    SecurityMonitorActions,
    SystemTopics
)


class MissionStatus(Enum):
    """Статус миссии"""
    DRAFT = "draft"
    PLANNED = "planned"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABORTED = "aborted"
    FAILED = "failed"


class MissionType(Enum):
    """Тип миссии"""
    CARGO_DELIVERY = "cargo_delivery"
    INSPECTION = "inspection"
    AGRO_SPRAYING = "agro_spraying"
    MONITORING = "monitoring"


@dataclass
class Waypoint:
    """Точка маршрута"""
    lat: float
    lon: float
    alt: float
    action: str = "fly_to"  # fly_to, hover, land, takeoff
    duration: int = 0  # секунды задержки


@dataclass
class Mission:
    """Миссия БАС"""
    id: str
    type: MissionType
    status: MissionStatus
    order_id: str
    uas_id: Optional[str]
    waypoints: List[Waypoint]
    start_time: str
    end_time: str
    payload_weight: float
    distance: float  # км
    created_at: str
    updated_at: str
    utm_approval: Optional[Dict[str, Any]] = None
    gcs_plan: Optional[Dict[str, Any]] = None


class MissionPlanner(BaseComponent):
    """
    Планировщик миссий - создаёт и управляет полётными заданиями
    """
    
    def __init__(self, component_id: str, bus: SystemBus):
        self.logger = logging.getLogger(f"MissionPlanner.{component_id}")
        
        # Активные миссии
        self.missions: Dict[str, Mission] = {}
        
        # Кеш маршрутов от НУС
        self.route_cache: Dict[str, Dict[str, Any]] = {}
        
        super().__init__(
            component_id=component_id,
            component_type="mission_planner",
            topic=ComponentTopics.MISSION_PLANNER,
            bus=bus
        )
        
        self.logger.info(f"Mission Planner {component_id} initialized")
    
    def _register_handlers(self):
        """Регистрация обработчиков"""
        self.register_handler(MissionPlannerActions.CREATE_MISSION, self._handle_create_mission)
        self.register_handler(MissionPlannerActions.VALIDATE_MISSION, self._handle_validate_mission)
        self.register_handler(MissionPlannerActions.REQUEST_UTM_APPROVAL, self._handle_request_utm_approval)
        self.register_handler(MissionPlannerActions.UPDATE_MISSION_STATUS, self._handle_update_mission_status)
        self.register_handler(MissionPlannerActions.GET_MISSION_DETAILS, self._handle_get_mission_details)
    
    def _handle_create_mission(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Создание новой миссии"""
        payload = message.get("payload", {})
        order = payload.get("order", {})
        
        if not order:
            return {"error": "Order details required"}
        
        # Проверяем через монитор безопасности
        security_check = self._validate_with_security_monitor({
            "action": "create_mission",
            "sender": message.get("sender", "mission_planner"),
            "order_id": order.get("id")
        }, {
            "order": order
        })
        
        if not security_check.get("allowed", True):
            return {
                "error": "Security check failed",
                "violations": security_check.get("violations", [])
            }
        
        # Определяем тип миссии
        mission_type = self._determine_mission_type(order)
        
        # Запрашиваем маршрут у НУС
        route_request = self._request_route_from_gcs(order)
        if not route_request.get("success"):
            return {
                "error": "Failed to get route from GCS",
                "details": route_request.get("error")
            }
        
        waypoints = self._convert_gcs_route_to_waypoints(route_request.get("route", []))
        
        # Создаём миссию
        mission = Mission(
            id=f"MISSION-{uuid.uuid4().hex[:8].upper()}",
            type=mission_type,
            status=MissionStatus.DRAFT,
            order_id=order.get("id"),
            uas_id=None,
            waypoints=waypoints,
            start_time=order.get("start_time", datetime.utcnow().isoformat()),
            end_time=order.get("end_time", (datetime.utcnow() + timedelta(hours=2)).isoformat()),
            payload_weight=order.get("payload_weight", 0),
            distance=self._calculate_distance(waypoints),
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            gcs_plan=route_request.get("route")
        )
        
        self.missions[mission.id] = mission
        
        self.logger.info(f"Created mission {mission.id} for order {order.get('id')}")
        
        return {
            "mission_id": mission.id,
            "status": mission.status.value,
            "waypoints_count": len(waypoints),
            "distance": mission.distance
        }
    
    def _handle_validate_mission(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация миссии"""
        payload = message.get("payload", {})
        mission_id = payload.get("mission_id")
        
        if not mission_id:
            return {"error": "mission_id is required"}
        
        mission = self.missions.get(mission_id)
        if not mission:
            return {"error": f"Mission {mission_id} not found"}
        
        validation_results = []
        
        # Проверка 1: Наличие точек маршрута
        if len(mission.waypoints) < 2:
            validation_results.append({
                "check": "waypoints",
                "passed": False,
                "reason": "Mission must have at least 2 waypoints"
            })
        else:
            validation_results.append({
                "check": "waypoints",
                "passed": True
            })
        
        # Проверка 2: Выбран БАС
        if not mission.uas_id:
            # Пытаемся найти подходящий БАС
            uas_requirements = {
                "min_payload": mission.payload_weight,
                "min_range": mission.distance * 1.2,  # 20% запас
                "min_battery": 0.8
            }
            
            available_uas = self._find_suitable_uas(uas_requirements)
            
            if available_uas.get("count", 0) == 0:
                validation_results.append({
                    "check": "uas_availability",
                    "passed": False,
                    "reason": "No suitable UAS available"
                })
            else:
                validation_results.append({
                    "check": "uas_availability",
                    "passed": True,
                    "available_uas": available_uas.get("suitable_uas", [])
                })
        else:
            validation_results.append({
                "check": "uas_assigned",
                "passed": True,
                "uas_id": mission.uas_id
            })
        
        # Проверка 3: Временное окно
        try:
            start = datetime.fromisoformat(mission.start_time.replace('Z', '+00:00'))
            end = datetime.fromisoformat(mission.end_time.replace('Z', '+00:00'))
            
            if end <= start:
                validation_results.append({
                    "check": "time_window",
                    "passed": False,
                    "reason": "End time must be after start time"
                })
            elif (end - start).total_seconds() < 1800:  # 30 минут минимум
                validation_results.append({
                    "check": "time_window",
                    "passed": False,
                    "reason": "Mission duration too short (min 30 minutes)"
                })
            else:
                validation_results.append({
                    "check": "time_window",
                    "passed": True,
                    "duration_minutes": (end - start).total_seconds() / 60
                })
        except Exception as e:
            validation_results.append({
                "check": "time_window",
                "passed": False,
                "reason": f"Invalid time format: {e}"
            })
        
        # Проверка 4: Безопасность маршрута
        safety_check = self._check_route_safety(mission.waypoints)
        validation_results.append(safety_check)
        
        # Общий результат
        all_passed = all(r.get("passed", False) for r in validation_results)
        
        if all_passed:
            mission.status = MissionStatus.PLANNED
            mission.updated_at = datetime.utcnow().isoformat()
        
        return {
            "valid": all_passed,
            "validation_results": validation_results,
            "mission_status": mission.status.value
        }
    
    def _handle_request_utm_approval(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Запрос разрешения от ОрВД"""
        payload = message.get("payload", {})
        mission_id = payload.get("mission_id")
        
        if not mission_id:
            return {"error": "mission_id is required"}
        
        mission = self.missions.get(mission_id)
        if not mission:
            return {"error": f"Mission {mission_id} not found"}
        
        if mission.status != MissionStatus.PLANNED:
            return {"error": f"Mission must be in PLANNED status, current: {mission.status.value}"}
        
        # Формируем запрос для ОрВД
        utm_request = {
            "mission_id": mission.id,
            "operator_id": "OPERATOR-001",
            "uas_id": mission.uas_id,
            "flight_plan": {
                "waypoints": [asdict(wp) for wp in mission.waypoints],
                "start_time": mission.start_time,
                "end_time": mission.end_time,
                "max_altitude": max(wp.alt for wp in mission.waypoints),
                "mission_type": mission.type.value
            }
        }
        
        # Отправляем запрос в ОрВД (симуляция)
        utm_response = self._simulate_utm_approval(utm_request)
        
        if utm_response.get("approved"):
            mission.utm_approval = utm_response
            mission.status = MissionStatus.APPROVED
            mission.updated_at = datetime.utcnow().isoformat()
            
            self.logger.info(f"Mission {mission_id} approved by UTM")
            
            return {
                "approved": True,
                "approval_id": utm_response.get("approval_id"),
                "valid_until": utm_response.get("valid_until"),
                "restrictions": utm_response.get("restrictions", [])
            }
        else:
            return {
                "approved": False,
                "reason": utm_response.get("reason", "Unknown"),
                "suggestions": utm_response.get("suggestions", [])
            }
    
    def _handle_update_mission_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Обновление статуса миссии"""
        payload = message.get("payload", {})
        mission_id = payload.get("mission_id")
        new_status = payload.get("status")
        reason = payload.get("reason", "")
        
        if not all([mission_id, new_status]):
            return {"error": "mission_id and status are required"}
        
        mission = self.missions.get(mission_id)
        if not mission:
            return {"error": f"Mission {mission_id} not found"}
        
        try:
            new_status_enum = MissionStatus(new_status)
        except ValueError:
            return {"error": f"Invalid status: {new_status}"}
        
        # Проверяем допустимость перехода
        allowed_transitions = {
            MissionStatus.DRAFT: [MissionStatus.PLANNED, MissionStatus.ABORTED],
            MissionStatus.PLANNED: [MissionStatus.APPROVED, MissionStatus.ABORTED],
            MissionStatus.APPROVED: [MissionStatus.IN_PROGRESS, MissionStatus.ABORTED],
            MissionStatus.IN_PROGRESS: [MissionStatus.COMPLETED, MissionStatus.FAILED, MissionStatus.ABORTED],
            MissionStatus.COMPLETED: [],
            MissionStatus.ABORTED: [],
            MissionStatus.FAILED: []
        }
        
        if new_status_enum not in allowed_transitions.get(mission.status, []):
            return {
                "error": f"Invalid status transition: {mission.status.value} -> {new_status}"
            }
        
        old_status = mission.status
        mission.status = new_status_enum
        mission.updated_at = datetime.utcnow().isoformat()
        
        self.logger.info(f"Mission {mission_id} status updated: {old_status.value} -> {new_status}")
        
        # Освобождаем БАС при завершении миссии
        if new_status_enum in [MissionStatus.COMPLETED, MissionStatus.FAILED, MissionStatus.ABORTED]:
            if mission.uas_id:
                self._release_uas(mission.uas_id)
        
        return {
            "updated": True,
            "mission_id": mission_id,
            "old_status": old_status.value,
            "new_status": new_status,
            "reason": reason
        }
    
    def _handle_get_mission_details(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Получение деталей миссии"""
        payload = message.get("payload", {})
        mission_id = payload.get("mission_id")
        
        if not mission_id:
            return {"error": "mission_id is required"}
        
        mission = self.missions.get(mission_id)
        if not mission:
            return {"error": f"Mission {mission_id} not found"}
        
        mission_dict = asdict(mission)
        mission_dict["type"] = mission.type.value
        mission_dict["status"] = mission.status.value
        
        # Добавляем расчётное время полёта
        mission_dict["estimated_flight_time"] = self._estimate_flight_time(mission)
        
        return mission_dict
    
    def _determine_mission_type(self, order: Dict[str, Any]) -> MissionType:
        """Определение типа миссии по заказу"""
        order_type = order.get("type", "").lower()
        
        if "cargo" in order_type or "delivery" in order_type:
            return MissionType.CARGO_DELIVERY
        elif "inspection" in order_type:
            return MissionType.INSPECTION
        elif "agro" in order_type or "spray" in order_type:
            return MissionType.AGRO_SPRAYING
        else:
            return MissionType.MONITORING
    
    def _request_route_from_gcs(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Запрос маршрута у НУС"""
        # В реальной системе здесь был бы запрос к НУС
        # Для прототипа генерируем простой маршрут
        
        start_point = order.get("start_location", {"lat": 55.7558, "lon": 37.6173})
        end_point = order.get("end_location", {"lat": 55.7600, "lon": 37.6200})
        
        route = [
            {"lat": start_point["lat"], "lon": start_point["lon"], "alt": 0, "action": "takeoff"},
            {"lat": start_point["lat"], "lon": start_point["lon"], "alt": 50, "action": "fly_to"},
            {"lat": end_point["lat"], "lon": end_point["lon"], "alt": 50, "action": "fly_to"},
            {"lat": end_point["lat"], "lon": end_point["lon"], "alt": 0, "action": "land"}
        ]
        
        return {
            "success": True,
            "route": route,
            "distance": self._calculate_distance_between_points(start_point, end_point)
        }
    
    def _convert_gcs_route_to_waypoints(self, gcs_route: List[Dict[str, Any]]) -> List[Waypoint]:
        """Конвертация маршрута НУС в точки маршрута"""
        waypoints = []
        
        for point in gcs_route:
            waypoint = Waypoint(
                lat=point.get("lat", 0),
                lon=point.get("lon", 0),
                alt=point.get("alt", 0),
                action=point.get("action", "fly_to"),
                duration=point.get("duration", 0)
            )
            waypoints.append(waypoint)
        
        return waypoints
    
    def _calculate_distance(self, waypoints: List[Waypoint]) -> float:
        """Расчёт общей дистанции маршрута"""
        if len(waypoints) < 2:
            return 0.0
        
        total_distance = 0.0
        
        for i in range(1, len(waypoints)):
            prev = waypoints[i-1]
            curr = waypoints[i]
            
            distance = self._calculate_distance_between_points(
                {"lat": prev.lat, "lon": prev.lon},
                {"lat": curr.lat, "lon": curr.lon}
            )
            total_distance += distance
        
        return round(total_distance, 2)
    
    def _calculate_distance_between_points(self, point1: Dict[str, float], point2: Dict[str, float]) -> float:
        """Расчёт расстояния между двумя точками (упрощённый)"""
        # Упрощённый расчёт для прототипа
        lat_diff = abs(point1["lat"] - point2["lat"])
        lon_diff = abs(point1["lon"] - point2["lon"])
        
        # Примерно 111 км на градус широты
        distance = ((lat_diff ** 2 + lon_diff ** 2) ** 0.5) * 111
        
        return distance
    
    def _find_suitable_uas(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Поиск подходящего БАС через Fleet Manager"""
        try:
            response = self.bus.request(
                ComponentTopics.FLEET_MANAGER,
                {
                    "action": FleetManagerActions.FIND_AVAILABLE_UAS,
                    "sender": self.component_id,
                    "payload": {
                        "requirements": requirements
                    }
                },
                timeout=5.0
            )
            
            if response and response.get("success"):
                return response.get("payload", {})
            
            return {"count": 0, "suitable_uas": []}
            
        except Exception as e:
            self.logger.error(f"Failed to find suitable UAS: {e}")
            return {"count": 0, "suitable_uas": []}
    
    def _check_route_safety(self, waypoints: List[Waypoint]) -> Dict[str, Any]:
        """Проверка безопасности маршрута"""
        # В реальной системе здесь была бы проверка на:
        # - Запретные зоны
        # - Препятствия
        # - Погодные условия
        # - Другие полёты
        
        max_altitude = max(wp.alt for wp in waypoints)
        
        if max_altitude > 120:  # Ограничение для БАС
            return {
                "check": "route_safety",
                "passed": False,
                "reason": f"Maximum altitude {max_altitude}m exceeds limit of 120m"
            }
        
        return {
            "check": "route_safety",
            "passed": True,
            "max_altitude": max_altitude
        }
    
    def _simulate_utm_approval(self, utm_request: Dict[str, Any]) -> Dict[str, Any]:
        """Симуляция ответа от ОрВД"""
        # В реальной системе здесь был бы запрос к ОрВД
        # Для прототипа возвращаем положительный ответ
        
        return {
            "approved": True,
            "approval_id": f"UTM-{uuid.uuid4().hex[:8].upper()}",
            "valid_until": (datetime.utcnow() + timedelta(hours=4)).isoformat(),
            "restrictions": [],
            "corridors": utm_request.get("flight_plan", {}).get("waypoints", [])
        }
    
    def _release_uas(self, uas_id: str):
        """Освобождение БАС через Fleet Manager"""
        try:
            self.bus.publish(
                ComponentTopics.FLEET_MANAGER,
                {
                    "action": FleetManagerActions.RELEASE_UAS,
                    "sender": self.component_id,
                    "payload": {
                        "uas_id": uas_id
                    }
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to release UAS {uas_id}: {e}")
    
    def _estimate_flight_time(self, mission: Mission) -> float:
        """Оценка времени полёта в минутах"""
        # Средняя скорость БАС: 50 км/ч
        average_speed = 50.0
        
        flight_time = (mission.distance / average_speed) * 60  # минуты
        
        # Добавляем время на взлёт/посадку и задержки
        for wp in mission.waypoints:
            if wp.action in ["takeoff", "land"]:
                flight_time += 2  # 2 минуты
            flight_time += wp.duration / 60  # секунды в минуты
        
        return round(flight_time, 1)
    
    def _validate_with_security_monitor(self, request: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Валидация через монитор безопасности"""
        try:
            response = self.bus.request(
                ComponentTopics.SECURITY_MONITOR,
                {
                    "action": SecurityMonitorActions.VALIDATE_REQUEST,
                    "sender": self.component_id,
                    "payload": {
                        "request": request,
                        "context": context or {}
                    }
                },
                timeout=5.0
            )
            
            if response and response.get("success"):
                return response.get("payload", {})
            
            return {"allowed": False, "error": "Security monitor not responding"}
            
        except Exception as e:
            self.logger.error(f"Security validation error: {e}")
            return {"allowed": False, "error": str(e)}