"""
Fleet Manager Service - некритичные функции управления парком БАС
Недоверенный домен D2_OPERATIONAL - вся вспомогательная логика
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from .fleet_manager_core import FleetManagerCore, UASStatus


class UASType(Enum):
    """Тип БАС"""
    LIGHT_CARGO = "light_cargo"  # до 5 кг
    HEAVY_CARGO = "heavy_cargo"  # до 50 кг
    AGRO = "agro"  # агродрон
    INSPECTOR = "inspector"  # инспектор


@dataclass
class UASExtended:
    """Расширенная информация о БАС для бизнес-логики"""
    id: str
    type: UASType
    location: Dict[str, float]  # lat, lon, alt
    max_payload: float  # кг
    max_range: float  # км
    last_maintenance: str
    flight_hours: float
    model_id: Optional[str] = None
    developer_id: Optional[str] = None


class FleetManagerService:
    """
    Сервисный слой менеджера парка.
    Содержит всю некритичную логику: оптимизация, аналитика, интеграции.
    """
    
    def __init__(self, core: FleetManagerCore, developer_client: Any, regulator_client: Any):
        """
        Инициализация сервиса.
        
        Args:
            core: Ядро менеджера парка (доверенный домен)
            developer_client: Клиент для работы с разработчиками
            regulator_client: Клиент для работы с регулятором
        """
        self.core = core
        self.developer_client = developer_client
        self.regulator_client = regulator_client
        self.logger = logging.getLogger(__name__)
        
        # Расширенная информация о БАС
        self._fleet_extended: Dict[str, UASExtended] = {}
        
        # История операций
        self._operation_history: List[Dict[str, Any]] = []
        
        # Кэш резервирований
        self._reservations: Dict[str, Dict[str, Any]] = {}
        
        # История покупок
        self._purchase_history: List[Dict[str, Any]] = []
        
        # Метрики
        self._metrics = {
            "total_operations": 0,
            "successful_reservations": 0,
            "failed_reservations": 0,
            "total_flight_hours": 0.0,
            "maintenance_alerts": 0
        }
    
    async def initialize_fleet(self) -> Dict[str, Any]:
        """Инициализация парка БАС из каталогов разработчиков"""
        try:
            # Получаем топики систем от регулятора
            topics = await self.regulator_client.get_system_topics()
            
            # Получаем каталоги от разработчиков
            catalogs = await self.developer_client.get_all_catalogs()
            
            if not catalogs:
                self.logger.warning("No developer catalogs available, using default fleet")
                self._init_default_fleet()
                return {"initialized": True, "source": "default", "count": len(self._fleet_extended)}

            # Каталоги есть, но парк не наполняем автоматически:
            # добавление БАС происходит через явную операцию PURCHASE_UAS.
            return {"initialized": True, "source": "catalogs", "count": len(self._fleet_extended), "developers": len(catalogs)}
            
        except Exception as e:
            self.logger.error(f"Failed to init fleet from catalogs: {e}")
            self._init_default_fleet()
            return {"initialized": True, "source": "default", "count": len(self._fleet_extended), "error": str(e)}
    
    def _init_default_fleet(self):
        """Инициализация дефолтного парка БАС"""
        default_uas = [
            ("UAS-001", UASType.LIGHT_CARGO, 5.0, 50.0),
            ("UAS-002", UASType.HEAVY_CARGO, 50.0, 30.0),
            ("UAS-003", UASType.AGRO, 20.0, 40.0),
            ("UAS-004", UASType.INSPECTOR, 2.0, 100.0)
        ]
        
        for uas_id, uas_type, payload, range_km in default_uas:
            # Добавляем в ядро
            self.core.add_uas(uas_id, {
                "certificate_valid": True,
                "certificate_expiry": "2027-01-01T00:00:00Z",
                "battery_level": 0.8 + (ord(uas_id[-1]) % 3) * 0.1
            })
            
            # Добавляем расширенную информацию
            self._fleet_extended[uas_id] = UASExtended(
                id=uas_id,
                type=uas_type,
                location={"lat": 55.7558, "lon": 37.6173, "alt": 0},
                max_payload=payload,
                max_range=range_km,
                last_maintenance="2026-03-01T00:00:00Z",
                flight_hours=50.0 + (ord(uas_id[-1]) % 5) * 30
            )
    
    async def find_suitable_uas(self, requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Поиск подходящих БАС для миссии с оптимизацией.
        
        Args:
            requirements: Требования к БАС
            
        Returns:
            Список подходящих БАС с рейтингом
        """
        suitable_uas = []
        
        required_type = requirements.get("type")
        min_payload = requirements.get("min_payload", 0)
        min_range = requirements.get("min_range", 0)
        min_battery = requirements.get("min_battery", 0.3)
        
        for uas_id, uas_ext in self._fleet_extended.items():
            # Получаем состояние из ядра
            core_state = self.core.get_uas_state(uas_id)
            if not core_state:
                continue
            
            # Проверяем доступность
            if core_state["status"] != UASStatus.AVAILABLE.value:
                continue
            
            # Проверяем сертификат
            if not core_state["certificate_valid"]:
                continue
            
            # Проверяем тип
            if required_type and uas_ext.type.value != required_type:
                continue
            
            # Проверяем характеристики
            if uas_ext.max_payload < min_payload:
                continue
            
            if uas_ext.max_range < min_range:
                continue
            
            if core_state["battery_level"] < min_battery:
                continue
            
            # Рассчитываем рейтинг пригодности
            suitability_score = self._calculate_suitability_score(
                uas_ext, core_state, requirements
            )
            
            suitable_uas.append({
                "id": uas_id,
                "type": uas_ext.type.value,
                "model_id": uas_ext.model_id,
                "battery_level": core_state["battery_level"],
                "max_payload": uas_ext.max_payload,
                "max_range": uas_ext.max_range,
                "location": uas_ext.location,
                "suitability_score": suitability_score,
                "maintenance_due": self._is_maintenance_due(uas_ext)
            })
        
        # Сортируем по рейтингу пригодности
        suitable_uas.sort(key=lambda x: x["suitability_score"], reverse=True)
        
        # Логируем результат поиска
        self._log_search_result(requirements, suitable_uas)
        
        return suitable_uas
    
    async def reserve_uas_with_validation(
        self, 
        uas_id: str, 
        mission_id: str, 
        operator_id: str,
        duration: int = 3600
    ) -> Dict[str, Any]:
        """
        Резервирование БАС с полной валидацией и логированием.
        
        Args:
            uas_id: Идентификатор БАС
            mission_id: Идентификатор миссии
            operator_id: Идентификатор оператора
            duration: Длительность резервирования в секундах
            
        Returns:
            Результат резервирования с деталями
        """
        start_time = datetime.utcnow()
        
        # Вызываем критичную функцию резервирования
        success, reason = self.core.reserve_uas(uas_id, mission_id, operator_id)
        
        # Обновляем метрики
        self._metrics["total_operations"] += 1
        if success:
            self._metrics["successful_reservations"] += 1
        else:
            self._metrics["failed_reservations"] += 1
        
        # Логируем операцию
        operation = {
            "type": "reserve",
            "uas_id": uas_id,
            "mission_id": mission_id,
            "operator_id": operator_id,
            "timestamp": start_time.isoformat(),
            "success": success,
            "reason": reason,
            "duration_ms": (datetime.utcnow() - start_time).total_seconds() * 1000
        }
        self._operation_history.append(operation)
        
        if success:
            # Сохраняем информацию о резервировании
            self._reservations[uas_id] = {
                "mission_id": mission_id,
                "operator_id": operator_id,
                "reserved_at": start_time.isoformat(),
                "expires_at": (start_time + timedelta(seconds=duration)).isoformat()
            }
            
            self.logger.info(f"UAS {uas_id} reserved for mission {mission_id}")
            
            return {
                "success": True,
                "uas_id": uas_id,
                "mission_id": mission_id,
                "reservation": self._reservations[uas_id]
            }
        else:
            self.logger.warning(f"Failed to reserve UAS {uas_id}: {reason}")
            
            return {
                "success": False,
                "uas_id": uas_id,
                "reason": reason,
                "suggestions": self._get_reservation_suggestions(uas_id, reason)
            }
    
    async def release_uas_with_cleanup(
        self, 
        uas_id: str, 
        operator_id: str
    ) -> Dict[str, Any]:
        """
        Освобождение БАС с очисткой данных.
        
        Args:
            uas_id: Идентификатор БАС
            operator_id: Идентификатор оператора
            
        Returns:
            Результат освобождения
        """
        # Сохраняем информацию о резервировании до освобождения
        reservation_info = self._reservations.get(uas_id, {})
        
        # Вызываем критичную функцию освобождения
        success, reason = self.core.release_uas(uas_id, operator_id)
        
        if success:
            # Очищаем данные о резервировании
            if uas_id in self._reservations:
                del self._reservations[uas_id]
            
            # Логируем операцию
            self._operation_history.append({
                "type": "release",
                "uas_id": uas_id,
                "operator_id": operator_id,
                "timestamp": datetime.utcnow().isoformat(),
                "success": True,
                "previous_reservation": reservation_info
            })
            
            self.logger.info(f"UAS {uas_id} released by {operator_id}")
            
            return {
                "success": True,
                "uas_id": uas_id,
                "released_from": reservation_info.get("mission_id")
            }
        else:
            self.logger.warning(f"Failed to release UAS {uas_id}: {reason}")
            
            return {
                "success": False,
                "uas_id": uas_id,
                "reason": reason
            }
    
    def get_fleet_statistics(self) -> Dict[str, Any]:
        """Получение расширенной статистики парка"""
        stats = {
            "total": len(self._fleet_extended),
            "by_status": {},
            "by_type": {},
            "average_battery": 0,
            "average_flight_hours": 0,
            "maintenance_required": 0,
            "certificates_expiring_soon": 0,
            "operational_metrics": self._metrics
        }
        
        total_battery = 0
        total_flight_hours = 0
        
        for uas_id, uas_ext in self._fleet_extended.items():
            # Получаем состояние из ядра
            core_state = self.core.get_uas_state(uas_id)
            if not core_state:
                continue
            
            # По статусу
            status = core_state["status"]
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            # По типу
            uas_type = uas_ext.type.value
            stats["by_type"][uas_type] = stats["by_type"].get(uas_type, 0) + 1
            
            # Батарея
            total_battery += core_state["battery_level"]
            
            # Часы полёта
            total_flight_hours += uas_ext.flight_hours
            
            # Обслуживание
            if self._is_maintenance_due(uas_ext):
                stats["maintenance_required"] += 1
            
            # Сертификаты
            try:
                expiry = datetime.fromisoformat(core_state["certificate_expiry"].replace('Z', '+00:00'))
                if expiry < datetime.utcnow() + timedelta(days=30):
                    stats["certificates_expiring_soon"] += 1
            except:
                pass
        
        if stats["total"] > 0:
            stats["average_battery"] = total_battery / stats["total"]
            stats["average_flight_hours"] = total_flight_hours / stats["total"]
        
        return stats
    
    def get_purchase_history(self, developer_id: Optional[str] = None) -> Dict[str, Any]:
        """Получение истории покупок БАС"""
        if developer_id:
            history = [p for p in self._purchase_history if p["developer_id"] == developer_id]
        else:
            history = self._purchase_history
        
        return {
            "purchases": history,
            "count": len(history),
            "total_spent": sum(p.get("price", 0) for p in history),
            "by_developer": self._group_purchases_by_developer(history)
        }
    
    def _calculate_suitability_score(
        self, 
        uas: UASExtended, 
        state: Dict[str, Any], 
        requirements: Dict[str, Any]
    ) -> float:
        """Расчёт рейтинга пригодности БАС для миссии"""
        score = 100.0
        
        # Штраф за низкий заряд
        battery_level = state["battery_level"]
        if battery_level < 0.5:
            score -= (0.5 - battery_level) * 50
        
        # Штраф за избыточные характеристики
        if requirements.get("min_payload"):
            excess_payload = uas.max_payload - requirements["min_payload"]
            if excess_payload > 20:
                score -= excess_payload * 0.5
        
        # Штраф за приближающееся обслуживание
        if self._is_maintenance_due(uas):
            score -= 20
        
        # Бонус за близость к месту миссии
        if "location" in requirements:
            distance = self._calculate_distance(uas.location, requirements["location"])
            if distance < 10:
                score += 10
            elif distance > 50:
                score -= 10
        
        return max(0, min(100, score))
    
    def _is_maintenance_due(self, uas: UASExtended) -> bool:
        """Проверка необходимости обслуживания"""
        # Каждые 50 часов полёта
        if uas.flight_hours % 50 > 45:
            return True
        
        # Каждые 30 дней
        try:
            last_maintenance = datetime.fromisoformat(uas.last_maintenance.replace('Z', '+00:00'))
            if datetime.utcnow() - last_maintenance > timedelta(days=30):
                return True
        except:
            return True
        
        return False
    
    def _calculate_distance(self, loc1: Dict[str, float], loc2: Dict[str, float]) -> float:
        """Простой расчёт расстояния между точками (км)"""
        # Упрощённая формула для демо
        lat_diff = abs(loc1["lat"] - loc2["lat"])
        lon_diff = abs(loc1["lon"] - loc2["lon"])
        return (lat_diff ** 2 + lon_diff ** 2) ** 0.5 * 111  # примерно км
    
    def _map_category_to_type(self, category: Any) -> UASType:
        """Маппинг категорий из каталога в типы БАС"""
        mapping = {
            "LIGHT_CARGO": UASType.LIGHT_CARGO,
            "HEAVY_CARGO": UASType.HEAVY_CARGO,
            "AGRO": UASType.AGRO,
            "INSPECTOR": UASType.INSPECTOR
        }
        return mapping.get(str(category).split('.')[-1], UASType.LIGHT_CARGO)
    
    def _log_search_result(self, requirements: Dict[str, Any], results: List[Dict[str, Any]]):
        """Логирование результатов поиска"""
        self.logger.info(
            f"UAS search completed: requirements={requirements}, "
            f"found={len(results)}, "
            f"best_score={results[0]['suitability_score'] if results else 0}"
        )
    
    def _get_reservation_suggestions(self, uas_id: str, reason: str) -> List[str]:
        """Получение рекомендаций при неудачном резервировании"""
        suggestions = []
        
        if reason == "UAS_NOT_AVAILABLE":
            suggestions.append("Try another UAS or wait for release")
            suggestions.append("Check fleet statistics for available units")
        elif reason == "CERTIFICATE_EXPIRED":
            suggestions.append("UAS requires certificate renewal")
            suggestions.append("Contact maintenance team")
        elif reason == "BATTERY_TOO_LOW":
            suggestions.append("UAS needs charging")
            suggestions.append("Expected charge time: 2 hours")
        
        return suggestions
    
    def _group_purchases_by_developer(self, purchases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Группировка покупок по разработчикам"""
        by_developer = {}
        
        for purchase in purchases:
            dev_id = purchase["developer_id"]
            if dev_id not in by_developer:
                by_developer[dev_id] = {
                    "count": 0,
                    "total_spent": 0,
                    "models": set()
                }
            
            by_developer[dev_id]["count"] += 1
            by_developer[dev_id]["total_spent"] += purchase.get("price", 0)
            by_developer[dev_id]["models"].add(purchase["model_id"])
        
        # Конвертируем sets в lists для сериализации
        for dev_data in by_developer.values():
            dev_data["models"] = list(dev_data["models"])
        
        return by_developer