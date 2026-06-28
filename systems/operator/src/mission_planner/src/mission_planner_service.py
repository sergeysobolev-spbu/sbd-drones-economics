"""
Mission Planner Service - Операционный домен D2_OPERATIONAL

Сервисный компонент для обработки некритичной логики:
- Управление миссиями
- Интеграция с другими компонентами
- Хранение и поиск планов
- Оптимизация маршрутов
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import os
from collections import defaultdict

from .mission_planner_core import (
    MissionPlannerCore,
    FlightPlan,
    Waypoint,
    MissionStatus,
    ValidationResult,
)


@dataclass
class Mission:
    """Полная информация о миссии"""

    mission_id: str
    name: str
    description: str
    operator_id: str
    uas_id: str
    flight_plan: FlightPlan
    status: MissionStatus
    created_at: float
    updated_at: float
    approved_by: Optional[str] = None
    approved_at: Optional[float] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    abort_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class MissionTemplate:
    """Шаблон миссии для повторного использования"""

    template_id: str
    name: str
    description: str
    waypoints: List[Waypoint]
    emergency_points: List[Waypoint]
    typical_duration: float
    created_by: str
    created_at: float
    usage_count: int = 0


@dataclass
class WeatherConditions:
    """Погодные условия"""

    wind_speed: float  # м/с
    wind_direction: float  # градусы
    visibility: float  # метры
    temperature: float  # Цельсий
    precipitation: bool
    timestamp: float


class MissionPlannerService:
    """
    Сервисный компонент планировщика миссий

    Обрабатывает некритичную логику:
    - Управление жизненным циклом миссий
    - Хранение и поиск
    - Интеграция с Fleet Manager
    - Оптимизация маршрутов
    - Работа с шаблонами
    """

    def __init__(self, core: MissionPlannerCore):
        """
        Инициализация сервиса

        Args:
            core: Ядро планировщика миссий
        """
        self.core = core
        self.missions: Dict[str, Mission] = {}
        self.templates: Dict[str, MissionTemplate] = {}
        self.mission_history: List[Mission] = []

        # Конфигурация
        self.max_concurrent_missions = int(os.environ.get("MAX_CONCURRENT_MISSIONS", "10"))
        self.mission_retention_days = int(os.environ.get("MISSION_RETENTION_DAYS", "90"))
        self.enable_route_optimization = os.environ.get("ENABLE_ROUTE_OPTIMIZATION", "true").lower() == "true"

        # Кеш погодных условий
        self.weather_cache: Optional[WeatherConditions] = None
        self.weather_cache_ttl = 300  # 5 минут

    async def create_mission(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создание новой миссии

        Args:
            request: Запрос на создание миссии

        Returns:
            Результат создания
        """
        try:
            # Извлекаем данные
            mission_id = request.get("mission_id", self._generate_mission_id())
            name = request.get("name", f"Mission {mission_id}")
            description = request.get("description", "")
            operator_id = request.get("operator_id")
            uas_id = request.get("uas_id")
            waypoints_data = request.get("waypoints", [])
            emergency_points_data = request.get("emergency_points", [])
            takeoff_time = request.get("takeoff_time", datetime.now().timestamp())

            # Проверка обязательных полей
            if not operator_id or not uas_id or not waypoints_data:
                return {"success": False, "error": "Missing required fields: operator_id, uas_id, waypoints"}

            # Проверка лимита активных миссий
            active_count = self.core.get_active_missions_count()
            if active_count >= self.max_concurrent_missions:
                return {
                    "success": False,
                    "error": f"Maximum concurrent missions limit reached: {self.max_concurrent_missions}",
                }

            # Создаем waypoints
            waypoints = [self._create_waypoint(wp) for wp in waypoints_data]
            emergency_points = [self._create_waypoint(ep) for ep in emergency_points_data]

            # Расчет параметров полета
            flight_params = self.core.calculate_flight_parameters(waypoints)

            # Создаем план полета
            flight_plan = FlightPlan(
                mission_id=mission_id,
                uas_id=uas_id,
                waypoints=waypoints,
                takeoff_time=takeoff_time,
                estimated_duration=flight_params["estimated_duration"],
                max_altitude=flight_params["max_altitude"],
                total_distance=flight_params["total_distance"],
                emergency_landing_points=emergency_points,
            )

            # Валидация плана
            validation_result, issues = self.core.validate_flight_plan(flight_plan)

            if validation_result == ValidationResult.INVALID:
                return {
                    "success": False,
                    "error": "Flight plan validation failed",
                    "validation_issues": [asdict(issue) for issue in issues],
                }

            # Оптимизация маршрута если включена
            if self.enable_route_optimization and validation_result == ValidationResult.VALID:
                flight_plan = await self._optimize_route(flight_plan)

            # Создаем миссию
            mission = Mission(
                mission_id=mission_id,
                name=name,
                description=description,
                operator_id=operator_id,
                uas_id=uas_id,
                flight_plan=flight_plan,
                status=(
                    MissionStatus.DRAFT if validation_result == ValidationResult.WARNING else MissionStatus.VALIDATED
                ),
                created_at=datetime.now().timestamp(),
                updated_at=datetime.now().timestamp(),
                metadata=request.get("metadata", {}),
            )

            # Сохраняем миссию
            self.missions[mission_id] = mission

            return {
                "success": True,
                "mission_id": mission_id,
                "status": mission.status.value,
                "validation_result": validation_result.value,
                "validation_issues": [asdict(issue) for issue in issues] if issues else [],
                "flight_parameters": flight_params,
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to create mission: {str(e)}"}

    async def update_mission(self, mission_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Обновление миссии"""
        if mission_id not in self.missions:
            return {"success": False, "error": f"Mission {mission_id} not found"}

        mission = self.missions[mission_id]

        # Проверка статуса - нельзя изменять активные миссии
        if mission.status in [MissionStatus.ACTIVE, MissionStatus.COMPLETED]:
            return {"success": False, "error": f"Cannot update mission in status {mission.status.value}"}

        # Обновляем поля
        if "name" in updates:
            mission.name = updates["name"]
        if "description" in updates:
            mission.description = updates["description"]

        # Обновление плана полета
        if "waypoints" in updates or "emergency_points" in updates:
            # Пересоздаем план полета
            waypoints = [
                self._create_waypoint(wp) for wp in updates.get("waypoints", [])
            ] or mission.flight_plan.waypoints
            emergency_points = [
                self._create_waypoint(ep) for ep in updates.get("emergency_points", [])
            ] or mission.flight_plan.emergency_landing_points

            flight_params = self.core.calculate_flight_parameters(waypoints)

            new_plan = FlightPlan(
                mission_id=mission_id,
                uas_id=mission.uas_id,
                waypoints=waypoints,
                takeoff_time=updates.get("takeoff_time", mission.flight_plan.takeoff_time),
                estimated_duration=flight_params["estimated_duration"],
                max_altitude=flight_params["max_altitude"],
                total_distance=flight_params["total_distance"],
                emergency_landing_points=emergency_points,
            )

            # Валидация нового плана
            validation_result, issues = self.core.validate_flight_plan(new_plan)

            if validation_result == ValidationResult.INVALID:
                return {
                    "success": False,
                    "error": "Updated flight plan validation failed",
                    "validation_issues": [asdict(issue) for issue in issues],
                }

            mission.flight_plan = new_plan
            mission.status = (
                MissionStatus.DRAFT if validation_result == ValidationResult.WARNING else MissionStatus.VALIDATED
            )

        mission.updated_at = datetime.now().timestamp()

        return {"success": True, "mission_id": mission_id, "status": mission.status.value}

    async def approve_mission(self, mission_id: str, approver_id: str) -> Dict[str, Any]:
        """Утверждение миссии"""
        if mission_id not in self.missions:
            return {"success": False, "error": f"Mission {mission_id} not found"}

        mission = self.missions[mission_id]

        if mission.status != MissionStatus.VALIDATED:
            return {
                "success": False,
                "error": f"Mission must be validated before approval, current status: {mission.status.value}",
            }

        # Проверка погодных условий
        weather_ok, weather_msg = await self._check_weather_conditions()
        if not weather_ok:
            return {"success": False, "error": f"Weather conditions unsuitable: {weather_msg}"}

        mission.status = MissionStatus.APPROVED
        mission.approved_by = approver_id
        mission.approved_at = datetime.now().timestamp()
        mission.updated_at = datetime.now().timestamp()

        return {"success": True, "mission_id": mission_id, "status": mission.status.value, "approved_by": approver_id}

    async def start_mission(self, mission_id: str) -> Dict[str, Any]:
        """Запуск миссии"""
        if mission_id not in self.missions:
            return {"success": False, "error": f"Mission {mission_id} not found"}

        mission = self.missions[mission_id]

        if mission.status != MissionStatus.APPROVED:
            return {
                "success": False,
                "error": f"Mission must be approved before start, current status: {mission.status.value}",
            }

        # Финальная проверка перед запуском
        validation_result, issues = self.core.validate_flight_plan(mission.flight_plan)
        if validation_result == ValidationResult.INVALID:
            return {
                "success": False,
                "error": "Pre-flight validation failed",
                "validation_issues": [asdict(issue) for issue in issues],
            }

        # Регистрируем активную миссию в ядре
        self.core.register_active_mission(mission.flight_plan)

        mission.status = MissionStatus.ACTIVE
        mission.started_at = datetime.now().timestamp()
        mission.updated_at = datetime.now().timestamp()

        return {
            "success": True,
            "mission_id": mission_id,
            "status": mission.status.value,
            "started_at": mission.started_at,
        }

    async def complete_mission(self, mission_id: str, completion_data: Dict[str, Any]) -> Dict[str, Any]:
        """Завершение миссии"""
        if mission_id not in self.missions:
            return {"success": False, "error": f"Mission {mission_id} not found"}

        mission = self.missions[mission_id]

        if mission.status != MissionStatus.ACTIVE:
            return {"success": False, "error": f"Mission is not active, current status: {mission.status.value}"}

        # Удаляем из активных миссий
        self.core.unregister_mission(mission_id)

        mission.status = MissionStatus.COMPLETED
        mission.completed_at = datetime.now().timestamp()
        mission.updated_at = datetime.now().timestamp()

        # Сохраняем данные о выполнении
        if "actual_duration" in completion_data:
            mission.metadata["actual_duration"] = completion_data["actual_duration"]
        if "actual_distance" in completion_data:
            mission.metadata["actual_distance"] = completion_data["actual_distance"]

        # Добавляем в историю
        self.mission_history.append(mission)

        return {
            "success": True,
            "mission_id": mission_id,
            "status": mission.status.value,
            "completed_at": mission.completed_at,
        }

    async def abort_mission(self, mission_id: str, reason: str) -> Dict[str, Any]:
        """Прерывание миссии"""
        if mission_id not in self.missions:
            return {"success": False, "error": f"Mission {mission_id} not found"}

        mission = self.missions[mission_id]

        if mission.status != MissionStatus.ACTIVE:
            return {
                "success": False,
                "error": f"Can only abort active missions, current status: {mission.status.value}",
            }

        # Удаляем из активных миссий
        self.core.unregister_mission(mission_id)

        mission.status = MissionStatus.ABORTED
        mission.abort_reason = reason
        mission.updated_at = datetime.now().timestamp()

        # Добавляем в историю
        self.mission_history.append(mission)

        return {"success": True, "mission_id": mission_id, "status": mission.status.value, "abort_reason": reason}

    def get_mission(self, mission_id: str) -> Optional[Dict[str, Any]]:
        """Получение информации о миссии"""
        if mission_id not in self.missions:
            return None

        mission = self.missions[mission_id]
        return self._mission_to_dict(mission)

    def list_missions(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Получение списка миссий с фильтрацией"""
        missions = list(self.missions.values())

        if filters:
            if "status" in filters:
                status = MissionStatus(filters["status"])
                missions = [m for m in missions if m.status == status]

            if "operator_id" in filters:
                missions = [m for m in missions if m.operator_id == filters["operator_id"]]

            if "uas_id" in filters:
                missions = [m for m in missions if m.uas_id == filters["uas_id"]]

            if "date_from" in filters:
                date_from = filters["date_from"]
                missions = [m for m in missions if m.created_at >= date_from]

            if "date_to" in filters:
                date_to = filters["date_to"]
                missions = [m for m in missions if m.created_at <= date_to]

        return [self._mission_to_dict(m) for m in missions]

    async def create_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создание шаблона миссии"""
        template_id = template_data.get("template_id", self._generate_template_id())

        waypoints = [self._create_waypoint(wp) for wp in template_data.get("waypoints", [])]
        emergency_points = [self._create_waypoint(ep) for ep in template_data.get("emergency_points", [])]

        template = MissionTemplate(
            template_id=template_id,
            name=template_data["name"],
            description=template_data.get("description", ""),
            waypoints=waypoints,
            emergency_points=emergency_points,
            typical_duration=template_data.get("typical_duration", 0),
            created_by=template_data["created_by"],
            created_at=datetime.now().timestamp(),
        )

        self.templates[template_id] = template

        return {"success": True, "template_id": template_id}

    async def create_mission_from_template(self, template_id: str, mission_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создание миссии из шаблона"""
        if template_id not in self.templates:
            return {"success": False, "error": f"Template {template_id} not found"}

        template = self.templates[template_id]

        # Подготавливаем данные для создания миссии
        request = {
            "name": mission_data.get("name", f"{template.name} - Copy"),
            "description": mission_data.get("description", template.description),
            "operator_id": mission_data["operator_id"],
            "uas_id": mission_data["uas_id"],
            "waypoints": [asdict(wp) for wp in template.waypoints],
            "emergency_points": [asdict(ep) for ep in template.emergency_points],
            "takeoff_time": mission_data.get("takeoff_time", datetime.now().timestamp()),
            "metadata": {"from_template": template_id, **mission_data.get("metadata", {})},
        }

        # Увеличиваем счетчик использования
        template.usage_count += 1

        return await self.create_mission(request)

    async def _optimize_route(self, flight_plan: FlightPlan) -> FlightPlan:
        """Оптимизация маршрута"""
        # Простая оптимизация - сглаживание траектории
        # В реальной системе здесь был бы более сложный алгоритм

        optimized_waypoints = []
        waypoints = flight_plan.waypoints

        for i, wp in enumerate(waypoints):
            if i == 0 or i == len(waypoints) - 1:
                # Сохраняем первую и последнюю точки
                optimized_waypoints.append(wp)
            else:
                # Проверяем, можно ли пропустить точку
                prev_wp = waypoints[i - 1]
                next_wp = waypoints[i + 1]

                # Если точки на одной линии и нет специального действия
                if not wp.action and self._are_collinear(prev_wp, wp, next_wp):
                    continue  # Пропускаем точку
                else:
                    optimized_waypoints.append(wp)

        flight_plan.waypoints = optimized_waypoints
        return flight_plan

    def _are_collinear(self, p1: Waypoint, p2: Waypoint, p3: Waypoint, tolerance: float = 0.01) -> bool:
        """Проверка, лежат ли три точки на одной линии"""
        # Упрощенная проверка через площадь треугольника
        area = abs(
            (p2.latitude - p1.latitude) * (p3.longitude - p1.longitude)
            - (p3.latitude - p1.latitude) * (p2.longitude - p1.longitude)
        )
        return area < tolerance

    async def _check_weather_conditions(self) -> Tuple[bool, Optional[str]]:
        """Проверка погодных условий"""
        # Получаем актуальные данные о погоде
        weather = await self._get_weather_conditions()

        if not weather:
            return True, None  # Если нет данных, разрешаем полет

        constraints = self.core.safety_constraints

        if weather.wind_speed > constraints.max_wind_speed:
            return False, f"Wind speed {weather.wind_speed}m/s exceeds limit {constraints.max_wind_speed}m/s"

        if weather.visibility < constraints.min_visibility:
            return False, f"Visibility {weather.visibility}m below minimum {constraints.min_visibility}m"

        if weather.precipitation:
            return False, "Precipitation detected"

        return True, None

    async def _get_weather_conditions(self) -> Optional[WeatherConditions]:
        """Получение погодных условий"""
        # Проверяем кеш
        if self.weather_cache:
            age = datetime.now().timestamp() - self.weather_cache.timestamp
            if age < self.weather_cache_ttl:
                return self.weather_cache

        # В реальной системе здесь был бы запрос к погодному сервису
        # Для демонстрации возвращаем фиктивные данные
        self.weather_cache = WeatherConditions(
            wind_speed=5.0,
            wind_direction=180.0,
            visibility=5000.0,
            temperature=20.0,
            precipitation=False,
            timestamp=datetime.now().timestamp(),
        )

        return self.weather_cache

    def _create_waypoint(self, data: Dict[str, Any]) -> Waypoint:
        """Создание waypoint из словаря"""
        return Waypoint(
            latitude=data["latitude"],
            longitude=data["longitude"],
            altitude=data["altitude"],
            speed=data.get("speed", 10.0),
            action=data.get("action"),
            duration=data.get("duration"),
        )

    def _mission_to_dict(self, mission: Mission) -> Dict[str, Any]:
        """Преобразование миссии в словарь"""
        result = asdict(mission)
        result["status"] = mission.status.value
        result["flight_plan"]["waypoints"] = [asdict(wp) for wp in mission.flight_plan.waypoints]
        result["flight_plan"]["emergency_landing_points"] = [
            asdict(ep) for ep in mission.flight_plan.emergency_landing_points
        ]
        return result

    def _generate_mission_id(self) -> str:
        """Генерация ID миссии"""
        timestamp = int(datetime.now().timestamp() * 1000)
        return f"mission-{timestamp}"

    def _generate_template_id(self) -> str:
        """Генерация ID шаблона"""
        timestamp = int(datetime.now().timestamp() * 1000)
        return f"template-{timestamp}"

    async def cleanup_old_missions(self):
        """Очистка старых миссий"""
        cutoff_time = datetime.now().timestamp() - (self.mission_retention_days * 86400)

        # Удаляем завершенные миссии старше cutoff_time
        missions_to_remove = []
        for mission_id, mission in self.missions.items():
            if mission.status in [MissionStatus.COMPLETED, MissionStatus.ABORTED, MissionStatus.FAILED]:
                if mission.updated_at < cutoff_time:
                    missions_to_remove.append(mission_id)

        for mission_id in missions_to_remove:
            del self.missions[mission_id]

        # Очищаем историю
        self.mission_history = [m for m in self.mission_history if m.updated_at >= cutoff_time]

    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики по миссиям"""
        total_missions = len(self.missions) + len(self.mission_history)

        status_counts = defaultdict(int)
        for mission in self.missions.values():
            status_counts[mission.status.value] += 1

        # Статистика по истории
        completed_count = sum(1 for m in self.mission_history if m.status == MissionStatus.COMPLETED)
        aborted_count = sum(1 for m in self.mission_history if m.status == MissionStatus.ABORTED)

        # Средняя продолжительность
        durations = []
        for mission in self.mission_history:
            if mission.status == MissionStatus.COMPLETED and mission.started_at and mission.completed_at:
                durations.append(mission.completed_at - mission.started_at)

        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            "total_missions": total_missions,
            "active_missions": self.core.get_active_missions_count(),
            "status_distribution": dict(status_counts),
            "completed_missions": completed_count,
            "aborted_missions": aborted_count,
            "average_duration_seconds": avg_duration,
            "templates_count": len(self.templates),
        }
