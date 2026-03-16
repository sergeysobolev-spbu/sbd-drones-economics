"""
Fleet Manager - управление парком БАС

Компонент уровня D1_TRUSTED, отвечающий за отслеживание состояния БАС,
выбор оптимального дрона для миссии и контроль готовности к полёту.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from sdk.base_component import BaseComponent
from broker.system_bus import SystemBus
from systems.operator.src.topics import (
    ComponentTopics,
    FleetManagerActions,
    SecurityMonitorActions,
    SystemTopics
)
from systems.operator.src.developer_client import DeveloperClient, UASModel, UASCategory
from systems.operator.src.regulator_client import RegulatorClient


class UASStatus(Enum):
    """Статус БАС"""
    AVAILABLE = "available"
    RESERVED = "reserved"
    IN_MISSION = "in_mission"
    MAINTENANCE = "maintenance"
    CHARGING = "charging"
    ERROR = "error"


class UASType(Enum):
    """Тип БАС"""
    LIGHT_CARGO = "light_cargo"  # до 5 кг
    HEAVY_CARGO = "heavy_cargo"  # до 50 кг
    AGRO = "agro"  # агродрон
    INSPECTOR = "inspector"  # инспектор


@dataclass
class UAS:
    """Беспилотная авиационная система"""
    id: str
    type: UASType
    status: UASStatus
    battery_level: float  # 0.0 - 1.0
    location: Dict[str, float]  # lat, lon, alt
    max_payload: float  # кг
    max_range: float  # км
    certificate_status: str
    certificate_expiry: str
    last_maintenance: str
    flight_hours: float
    reserved_by: Optional[str] = None
    current_mission: Optional[str] = None


class FleetManager(BaseComponent):
    """
    Менеджер парка БАС - управляет всеми дронами эксплуатанта
    """
    
    def __init__(self, component_id: str, bus: SystemBus):
        self.logger = logging.getLogger(f"FleetManager.{component_id}")
        
        # Клиенты для взаимодействия с внешними системами
        self.regulator_client = RegulatorClient(bus)
        self.developer_client = DeveloperClient(bus, self.regulator_client)
        
        # Парк БАС
        self.fleet: Dict[str, UAS] = {}
        
        # Резервирования
        self.reservations: Dict[str, Dict[str, Any]] = {}
        
        # История покупок БАС
        self.purchase_history: List[Dict[str, Any]] = []
        
        super().__init__(
            component_id=component_id,
            component_type="fleet_manager",
            topic=ComponentTopics.FLEET_MANAGER,
            bus=bus
        )
        
        # Инициализируем парк из каталогов разработчиков
        self._init_fleet_from_catalogs()
        
        self.logger.info(f"Fleet Manager initialized with {len(self.fleet)} UAS")
    
    def _init_fleet_from_catalogs(self):
        """Инициализация парка БАС из каталогов разработчиков"""
        try:
            # Получаем топики систем от регулятора
            import asyncio
            loop = asyncio.get_event_loop()
            topics = loop.run_until_complete(self.regulator_client.get_system_topics())
            
            # Получаем каталоги от разработчиков
            catalogs = loop.run_until_complete(self.developer_client.get_all_catalogs())
            
            if not catalogs:
                self.logger.warning("No developer catalogs available, using default fleet")
                self._init_default_fleet()
                return
            
            # Формируем парк БАС на основе каталогов
            # Для прототипа покупаем по 2 БАС каждого типа
            uas_counter = 1
            
            for dev_id, catalog in catalogs.items():
                for model in catalog.models[:2]:  # Берём первые 2 модели от каждого разработчика
                    # Создаём БАС на основе модели
                    uas_id = f"UAS-{uas_counter:03d}"
                    
                    # Маппинг категорий
                    type_mapping = {
                        UASCategory.LIGHT_CARGO: UASType.LIGHT_CARGO,
                        UASCategory.HEAVY_CARGO: UASType.HEAVY_CARGO,
                        UASCategory.AGRO: UASType.AGRO,
                        UASCategory.INSPECTOR: UASType.INSPECTOR
                    }
                    
                    uas_type = type_mapping.get(model.category, UASType.LIGHT_CARGO)
                    
                    self.fleet[uas_id] = UAS(
                        id=uas_id,
                        type=uas_type,
                        status=UASStatus.AVAILABLE,
                        battery_level=1.0,
                        location={"lat": 55.7558, "lon": 37.6173, "alt": 0},
                        max_payload=model.specifications.get("max_payload_kg", 5.0),
                        max_range=model.specifications.get("max_range_km", 50.0),
                        certificate_status="valid" if model.certification else "invalid",
                        certificate_expiry=model.certification.get("valid_until", "2027-01-01") if model.certification else "2027-01-01",
                        last_maintenance=datetime.utcnow().isoformat(),
                        flight_hours=0.0
                    )
                    
                    # Записываем покупку
                    self.purchase_history.append({
                        "uas_id": uas_id,
                        "model_id": model.model_id,
                        "developer_id": dev_id,
                        "purchase_date": datetime.utcnow().isoformat(),
                        "price": model.price,
                        "model_name": model.name
                    })
                    
                    uas_counter += 1
                    
                    self.logger.info(f"Added UAS {uas_id} ({model.name}) to fleet")
            
        except Exception as e:
            self.logger.error(f"Failed to init fleet from catalogs: {e}")
            self._init_default_fleet()
    
    def _init_default_fleet(self):
        """Инициализация дефолтного парка БАС"""
        self.fleet = {
            "UAS-001": UAS(
                id="UAS-001",
                type=UASType.LIGHT_CARGO,
                status=UASStatus.AVAILABLE,
                battery_level=0.95,
                location={"lat": 55.7558, "lon": 37.6173, "alt": 0},
                max_payload=5.0,
                max_range=50.0,
                certificate_status="valid",
                certificate_expiry="2027-01-01T00:00:00Z",
                last_maintenance="2026-03-01T00:00:00Z",
                flight_hours=120.5
            ),
            "UAS-002": UAS(
                id="UAS-002",
                type=UASType.HEAVY_CARGO,
                status=UASStatus.AVAILABLE,
                battery_level=0.80,
                location={"lat": 55.7558, "lon": 37.6173, "alt": 0},
                max_payload=50.0,
                max_range=30.0,
                certificate_status="valid",
                certificate_expiry="2027-02-01T00:00:00Z",
                last_maintenance="2026-02-15T00:00:00Z",
                flight_hours=89.2
            ),
            "UAS-003": UAS(
                id="UAS-003",
                type=UASType.AGRO,
                status=UASStatus.MAINTENANCE,
                battery_level=0.60,
                location={"lat": 55.7558, "lon": 37.6173, "alt": 0},
                max_payload=20.0,
                max_range=40.0,
                certificate_status="valid",
                certificate_expiry="2026-12-01T00:00:00Z",
                last_maintenance="2026-03-10T00:00:00Z",
                flight_hours=200.8
            ),
            "UAS-004": UAS(
                id="UAS-004",
                type=UASType.INSPECTOR,
                status=UASStatus.AVAILABLE,
                battery_level=1.0,
                location={"lat": 55.7558, "lon": 37.6173, "alt": 0},
                max_payload=2.0,
                max_range=100.0,
                certificate_status="valid",
                certificate_expiry="2027-03-01T00:00:00Z",
                last_maintenance="2026-03-05T00:00:00Z",
                flight_hours=45.3
            )
        }
    
    def _register_handlers(self):
        """Регистрация обработчиков"""
        self.register_handler(FleetManagerActions.GET_UAS_LIST, self._handle_get_uas_list)
        self.register_handler(FleetManagerActions.GET_UAS_STATUS, self._handle_get_uas_status)
        self.register_handler(FleetManagerActions.FIND_AVAILABLE_UAS, self._handle_find_available_uas)
        self.register_handler(FleetManagerActions.RESERVE_UAS, self._handle_reserve_uas)
        self.register_handler(FleetManagerActions.RELEASE_UAS, self._handle_release_uas)
        self.register_handler(FleetManagerActions.UPDATE_UAS_STATUS, self._handle_update_uas_status)
        self.register_handler("GET_DEVELOPER_CATALOGS", self._handle_get_developer_catalogs)
        self.register_handler("PURCHASE_UAS", self._handle_purchase_uas)
        self.register_handler("GET_PURCHASE_HISTORY", self._handle_get_purchase_history)
    
    def _handle_get_uas_list(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Получение списка всех БАС"""
        uas_list = []
        for uas in self.fleet.values():
            uas_dict = asdict(uas)
            uas_dict["type"] = uas.type.value
            uas_dict["status"] = uas.status.value
            uas_list.append(uas_dict)
        
        return {
            "uas_list": uas_list,
            "total": len(uas_list),
            "available": len([u for u in self.fleet.values() if u.status == UASStatus.AVAILABLE])
        }
    
    def _handle_get_uas_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Получение статуса конкретного БАС"""
        payload = message.get("payload", {})
        uas_id = payload.get("uas_id")
        
        if not uas_id:
            return {"error": "uas_id is required"}
        
        uas = self.fleet.get(uas_id)
        if not uas:
            return {"error": f"UAS {uas_id} not found"}
        
        uas_dict = asdict(uas)
        uas_dict["type"] = uas.type.value
        uas_dict["status"] = uas.status.value
        
        # Добавляем информацию о готовности к полёту
        uas_dict["ready_for_flight"] = self._check_flight_readiness(uas)
        
        return uas_dict
    
    def _handle_find_available_uas(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Поиск доступных БАС для миссии"""
        payload = message.get("payload", {})
        requirements = payload.get("requirements", {})
        
        # Проверяем требования через монитор безопасности
        security_check = self._validate_with_security_monitor({
            "action": "find_uas",
            "sender": message.get("sender", "fleet_manager"),
            "requirements": requirements
        })
        
        if not security_check.get("allowed", True):
            return {
                "error": "Security check failed",
                "violations": security_check.get("violations", [])
            }
        
        # Фильтруем подходящие БАС
        suitable_uas = []
        
        required_type = requirements.get("type")
        min_payload = requirements.get("min_payload", 0)
        min_range = requirements.get("min_range", 0)
        min_battery = requirements.get("min_battery", 0.3)
        
        for uas in self.fleet.values():
            # Проверяем доступность
            if uas.status != UASStatus.AVAILABLE:
                continue
            
            # Проверяем тип
            if required_type and uas.type.value != required_type:
                continue
            
            # Проверяем характеристики
            if uas.max_payload < min_payload:
                continue
            
            if uas.max_range < min_range:
                continue
            
            if uas.battery_level < min_battery:
                continue
            
            # Проверяем сертификат
            if uas.certificate_status != "valid":
                continue
            
            # Проверяем готовность к полёту
            if not self._check_flight_readiness(uas):
                continue
            
            suitable_uas.append({
                "id": uas.id,
                "type": uas.type.value,
                "battery_level": uas.battery_level,
                "max_payload": uas.max_payload,
                "max_range": uas.max_range,
                "location": uas.location
            })
        
        # Сортируем по уровню заряда (оптимизация)
        suitable_uas.sort(key=lambda x: x["battery_level"], reverse=True)
        
        return {
            "suitable_uas": suitable_uas,
            "count": len(suitable_uas)
        }
    
    def _handle_reserve_uas(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Резервирование БАС для миссии"""
        payload = message.get("payload", {})
        uas_id = payload.get("uas_id")
        mission_id = payload.get("mission_id")
        duration = payload.get("duration", 3600)  # секунды
        
        if not all([uas_id, mission_id]):
            return {"error": "uas_id and mission_id are required"}
        
        uas = self.fleet.get(uas_id)
        if not uas:
            return {"error": f"UAS {uas_id} not found"}
        
        if uas.status != UASStatus.AVAILABLE:
            return {"error": f"UAS {uas_id} is not available (status: {uas.status.value})"}
        
        # Проверяем через монитор безопасности
        security_check = self._validate_with_security_monitor({
            "action": "reserve_uas",
            "sender": message.get("sender", "fleet_manager"),
            "uas_id": uas_id,
            "mission_id": mission_id
        }, {
            "uas": asdict(uas)
        })
        
        if not security_check.get("allowed", True):
            return {
                "error": "Security check failed",
                "violations": security_check.get("violations", [])
            }
        
        # Резервируем БАС
        uas.status = UASStatus.RESERVED
        uas.reserved_by = mission_id
        
        # Сохраняем информацию о резервировании
        self.reservations[uas_id] = {
            "mission_id": mission_id,
            "reserved_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(seconds=duration)).isoformat()
        }
        
        self.logger.info(f"UAS {uas_id} reserved for mission {mission_id}")
        
        return {
            "reserved": True,
            "uas_id": uas_id,
            "mission_id": mission_id,
            "expires_at": self.reservations[uas_id]["expires_at"]
        }
    
    def _handle_release_uas(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Освобождение БАС"""
        payload = message.get("payload", {})
        uas_id = payload.get("uas_id")
        
        if not uas_id:
            return {"error": "uas_id is required"}
        
        uas = self.fleet.get(uas_id)
        if not uas:
            return {"error": f"UAS {uas_id} not found"}
        
        # Освобождаем БАС
        previous_status = uas.status.value
        uas.status = UASStatus.AVAILABLE
        uas.reserved_by = None
        uas.current_mission = None
        
        # Удаляем резервирование
        if uas_id in self.reservations:
            del self.reservations[uas_id]
        
        self.logger.info(f"UAS {uas_id} released (was: {previous_status})")
        
        return {
            "released": True,
            "uas_id": uas_id,
            "previous_status": previous_status
        }
    
    def _handle_update_uas_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Обновление статуса БАС"""
        payload = message.get("payload", {})
        uas_id = payload.get("uas_id")
        updates = payload.get("updates", {})
        
        if not uas_id:
            return {"error": "uas_id is required"}
        
        uas = self.fleet.get(uas_id)
        if not uas:
            return {"error": f"UAS {uas_id} not found"}
        
        # Обновляем разрешённые поля
        allowed_updates = ["status", "battery_level", "location", "current_mission"]
        
        for field, value in updates.items():
            if field not in allowed_updates:
                continue
            
            if field == "status":
                try:
                    uas.status = UASStatus(value)
                except ValueError:
                    return {"error": f"Invalid status: {value}"}
            elif field == "battery_level":
                uas.battery_level = max(0.0, min(1.0, float(value)))
            elif field == "location":
                if isinstance(value, dict) and all(k in value for k in ["lat", "lon", "alt"]):
                    uas.location = value
            elif field == "current_mission":
                uas.current_mission = value
        
        self.logger.info(f"UAS {uas_id} updated: {updates}")
        
        return {
            "updated": True,
            "uas_id": uas_id,
            "updates": updates
        }
    
    def _check_flight_readiness(self, uas: UAS) -> bool:
        """Проверка готовности БАС к полёту"""
        # Проверяем статус
        if uas.status not in [UASStatus.AVAILABLE, UASStatus.RESERVED]:
            return False
        
        # Проверяем заряд батареи
        if uas.battery_level < 0.3:
            return False
        
        # Проверяем сертификат
        if uas.certificate_status != "valid":
            return False
        
        # Проверяем срок действия сертификата
        try:
            expiry = datetime.fromisoformat(uas.certificate_expiry.replace('Z', '+00:00'))
            if expiry < datetime.utcnow():
                return False
        except:
            return False
        
        # Проверяем необходимость обслуживания (каждые 50 часов)
        if uas.flight_hours % 50 > 45:  # Близко к порогу обслуживания
            return False
        
        return True
    
    def _validate_with_security_monitor(self, request: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Валидация запроса через монитор безопасности"""
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
    
    def get_fleet_statistics(self) -> Dict[str, Any]:
        """Получение статистики парка"""
        stats = {
            "total": len(self.fleet),
            "by_status": {},
            "by_type": {},
            "average_battery": 0,
            "certificates_expiring_soon": 0
        }
        
        total_battery = 0
        
        for uas in self.fleet.values():
            # По статусу
            status = uas.status.value
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            # По типу
            uas_type = uas.type.value
            stats["by_type"][uas_type] = stats["by_type"].get(uas_type, 0) + 1
            
            # Батарея
            total_battery += uas.battery_level
            
            # Сертификаты
            try:
                expiry = datetime.fromisoformat(uas.certificate_expiry.replace('Z', '+00:00'))
                if expiry < datetime.utcnow() + timedelta(days=30):
                    stats["certificates_expiring_soon"] += 1
            except:
                pass
        
        if stats["total"] > 0:
            stats["average_battery"] = total_battery / stats["total"]
        
        return stats
    
    def _handle_get_developer_catalogs(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Получение каталогов разработчиков БАС"""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            catalogs = loop.run_until_complete(self.developer_client.get_all_catalogs())
            
            # Преобразуем каталоги в сериализуемый формат
            result = {}
            for dev_id, catalog in catalogs.items():
                result[dev_id] = {
                    "developer_id": catalog.developer_id,
                    "developer_name": catalog.developer_name,
                    "models": [
                        {
                            "model_id": model.model_id,
                            "name": model.name,
                            "category": model.category.value,
                            "manufacturer": model.manufacturer,
                            "specifications": model.specifications,
                            "price": model.price,
                            "certification": model.certification,
                            "safety_features": model.safety_features,
                            "available_quantity": model.available_quantity,
                            "delivery_time_days": model.delivery_time_days
                        }
                        for model in catalog.models
                    ],
                    "updated_at": catalog.updated_at,
                    "contact_info": catalog.contact_info
                }
            
            return {
                "catalogs": result,
                "count": len(result)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get developer catalogs: {e}")
            return {"error": str(e)}
    
    def _handle_purchase_uas(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Покупка БАС у разработчика"""
        payload = message.get("payload", {})
        developer_id = payload.get("developer_id")
        model_id = payload.get("model_id")
        quantity = payload.get("quantity", 1)
        
        if not all([developer_id, model_id]):
            return {"error": "developer_id and model_id are required"}
        
        # Проверяем через монитор безопасности
        security_check = self._validate_with_security_monitor({
            "action": "purchase_uas",
            "sender": message.get("sender", "fleet_manager"),
            "developer_id": developer_id,
            "model_id": model_id,
            "quantity": quantity
        })
        
        if not security_check.get("allowed", True):
            return {
                "error": "Security check failed",
                "violations": security_check.get("violations", [])
            }
        
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Выполняем покупку
            purchase_result = loop.run_until_complete(
                self.developer_client.purchase_uas(developer_id, model_id, quantity)
            )
            
            if purchase_result.get("success"):
                # Добавляем БАС в парк
                for i in range(quantity):
                    uas_id = f"UAS-{len(self.fleet) + 1:03d}"
                    
                    # Получаем информацию о модели
                    catalog = self.developer_client.catalogs_cache.get(developer_id)
                    if catalog:
                        for model in catalog.models:
                            if model.model_id == model_id:
                                # Маппинг категорий
                                type_mapping = {
                                    UASCategory.LIGHT_CARGO: UASType.LIGHT_CARGO,
                                    UASCategory.HEAVY_CARGO: UASType.HEAVY_CARGO,
                                    UASCategory.AGRO: UASType.AGRO,
                                    UASCategory.INSPECTOR: UASType.INSPECTOR
                                }
                                
                                uas_type = type_mapping.get(model.category, UASType.LIGHT_CARGO)
                                
                                self.fleet[uas_id] = UAS(
                                    id=uas_id,
                                    type=uas_type,
                                    status=UASStatus.AVAILABLE,
                                    battery_level=1.0,
                                    location={"lat": 55.7558, "lon": 37.6173, "alt": 0},
                                    max_payload=model.specifications.get("max_payload_kg", 5.0),
                                    max_range=model.specifications.get("max_range_km", 50.0),
                                    certificate_status="valid" if model.certification else "invalid",
                                    certificate_expiry=model.certification.get("valid_until", "2027-01-01") if model.certification else "2027-01-01",
                                    last_maintenance=datetime.utcnow().isoformat(),
                                    flight_hours=0.0
                                )
                                
                                # Записываем покупку
                                self.purchase_history.append({
                                    "uas_id": uas_id,
                                    "model_id": model.model_id,
                                    "developer_id": developer_id,
                                    "purchase_date": datetime.utcnow().isoformat(),
                                    "price": model.price,
                                    "model_name": model.name,
                                    "order_id": purchase_result.get("order_id")
                                })
                                
                                self.logger.info(f"Purchased and added UAS {uas_id} ({model.name}) to fleet")
                                break
                
                return {
                    "success": True,
                    "order_id": purchase_result.get("order_id"),
                    "total_price": purchase_result.get("total_price"),
                    "delivery_days": purchase_result.get("delivery_days"),
                    "uas_added": quantity
                }
            else:
                return purchase_result
                
        except Exception as e:
            self.logger.error(f"Failed to purchase UAS: {e}")
            return {"error": str(e)}
    
    def _handle_get_purchase_history(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Получение истории покупок БАС"""
        payload = message.get("payload", {})
        developer_id = payload.get("developer_id")
        
        if developer_id:
            # Фильтруем по разработчику
            history = [p for p in self.purchase_history if p["developer_id"] == developer_id]
        else:
            history = self.purchase_history
        
        return {
            "purchase_history": history,
            "count": len(history),
            "total_spent": sum(p.get("price", 0) for p in history)
        }
