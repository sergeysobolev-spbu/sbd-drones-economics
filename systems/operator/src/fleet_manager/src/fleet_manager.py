"""
Fleet Manager Component - интеграция доверенного и недоверенного доменов
"""
import logging
from typing import Dict, Any, Optional
import asyncio

from sdk.base_component import BaseComponent
from broker.system_bus import SystemBus

from .fleet_manager_core import FleetManagerCore
from .fleet_manager_service import FleetManagerService


class FleetManager(BaseComponent):
    """
    Менеджер парка БАС - главный компонент.
    Интегрирует доверенный домен (core) и недоверенный домен (service).
    """
    
    def __init__(self, component_id: str, bus: SystemBus, config: Dict[str, Any] = None):
        """
        Инициализация компонента.
        
        Args:
            component_id: Идентификатор компонента
            bus: Системная шина
            config: Конфигурация компонента
        """
        self.logger = logging.getLogger(f"FleetManager.{component_id}")
        self.config = config or {}
        
        # Инициализация ядра (доверенный домен)
        self.core = FleetManagerCore()
        
        # Получаем клиенты из конфигурации или создаём заглушки
        developer_client = self.config.get("developer_client")
        regulator_client = self.config.get("regulator_client")
        
        # Инициализация сервиса (недоверенный домен)
        self.service = FleetManagerService(
            core=self.core,
            developer_client=developer_client,
            regulator_client=regulator_client
        )
        
        # Базовая инициализация компонента
        super().__init__(
            component_id=component_id,
            component_type="fleet_manager",
            topic=self.config.get("topic", "fleet_manager"),
            bus=bus
        )
        
        # Инициализация парка
        self._initialize_fleet()
        
        self.logger.info(f"Fleet Manager {component_id} initialized")
    
    def _initialize_fleet(self):
        """Инициализация парка БАС"""
        try:
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(self.service.initialize_fleet())
            self.logger.info(f"Fleet initialized: {result}")
        except Exception as e:
            self.logger.error(f"Failed to initialize fleet: {e}")
    
    def _register_handlers(self):
        """Регистрация обработчиков сообщений"""
        # Основные операции
        self.register_handler("GET_UAS_LIST", self._handle_get_uas_list)
        self.register_handler("GET_UAS_STATUS", self._handle_get_uas_status)
        self.register_handler("FIND_AVAILABLE_UAS", self._handle_find_available_uas)
        self.register_handler("RESERVE_UAS", self._handle_reserve_uas)
        self.register_handler("RELEASE_UAS", self._handle_release_uas)
        self.register_handler("UPDATE_UAS_STATUS", self._handle_update_uas_status)
        
        # Статистика и аналитика
        self.register_handler("GET_FLEET_STATISTICS", self._handle_get_fleet_statistics)
        
        # Работа с разработчиками
        self.register_handler("GET_DEVELOPER_CATALOGS", self._handle_get_developer_catalogs)
        self.register_handler("PURCHASE_UAS", self._handle_purchase_uas)
        self.register_handler("GET_PURCHASE_HISTORY", self._handle_get_purchase_history)
    
    def _handle_get_uas_list(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Получение списка всех БАС"""
        try:
            # Получаем статистику из сервиса
            stats = self.service.get_fleet_statistics()
            
            # Формируем список БАС
            uas_list = []
            for uas_id, uas_ext in self.service._fleet_extended.items():
                core_state = self.core.get_uas_state(uas_id)
                if core_state:
                    uas_info = {
                        "id": uas_id,
                        "type": uas_ext.type.value,
                        "status": core_state["status"],
                        "battery_level": core_state["battery_level"],
                        "location": uas_ext.location,
                        "max_payload": uas_ext.max_payload,
                        "max_range": uas_ext.max_range,
                        "certificate_valid": core_state["certificate_valid"],
                        "certificate_expiry": core_state["certificate_expiry"],
                        "reserved_by": core_state["reserved_by"]
                    }
                    uas_list.append(uas_info)
            
            return {
                "uas_list": uas_list,
                "total": len(uas_list),
                "statistics": stats
            }
        except Exception as e:
            self.logger.error(f"Error getting UAS list: {e}")
            return {"error": str(e)}
    
    def _handle_get_uas_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Получение статуса конкретного БАС"""
        payload = message.get("payload", {})
        uas_id = payload.get("uas_id")
        
        if not uas_id:
            return {"error": "uas_id is required"}
        
        try:
            # Получаем состояние из ядра
            core_state = self.core.get_uas_state(uas_id)
            if not core_state:
                return {"error": f"UAS {uas_id} not found"}
            
            # Получаем расширенную информацию
            uas_ext = self.service._fleet_extended.get(uas_id)
            if not uas_ext:
                return {"error": f"Extended info for UAS {uas_id} not found"}
            
            # Объединяем информацию
            result = {
                **core_state,
                "type": uas_ext.type.value,
                "location": uas_ext.location,
                "max_payload": uas_ext.max_payload,
                "max_range": uas_ext.max_range,
                "last_maintenance": uas_ext.last_maintenance,
                "flight_hours": uas_ext.flight_hours,
                "maintenance_due": self.service._is_maintenance_due(uas_ext)
            }
            
            return result
        except Exception as e:
            self.logger.error(f"Error getting UAS status: {e}")
            return {"error": str(e)}
    
    def _handle_find_available_uas(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Поиск доступных БАС для миссии"""
        payload = message.get("payload", {})
        requirements = payload.get("requirements", {})
        
        try:
            # Используем сервис для поиска с оптимизацией
            loop = asyncio.get_event_loop()
            suitable_uas = loop.run_until_complete(
                self.service.find_suitable_uas(requirements)
            )
            
            return {
                "suitable_uas": suitable_uas,
                "count": len(suitable_uas)
            }
        except Exception as e:
            self.logger.error(f"Error finding available UAS: {e}")
            return {"error": str(e)}
    
    def _handle_reserve_uas(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Резервирование БАС для миссии"""
        payload = message.get("payload", {})
        uas_id = payload.get("uas_id")
        mission_id = payload.get("mission_id")
        duration = payload.get("duration", 3600)
        
        if not all([uas_id, mission_id]):
            return {"error": "uas_id and mission_id are required"}
        
        try:
            # Используем сервис для резервирования с валидацией
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(
                self.service.reserve_uas_with_validation(
                    uas_id=uas_id,
                    mission_id=mission_id,
                    operator_id=message.get("sender", "system"),
                    duration=duration
                )
            )
            
            return result
        except Exception as e:
            self.logger.error(f"Error reserving UAS: {e}")
            return {"error": str(e)}
    
    def _handle_release_uas(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Освобождение БАС"""
        payload = message.get("payload", {})
        uas_id = payload.get("uas_id")
        
        if not uas_id:
            return {"error": "uas_id is required"}
        
        try:
            # Используем сервис для освобождения с очисткой
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(
                self.service.release_uas_with_cleanup(
                    uas_id=uas_id,
                    operator_id=message.get("sender", "system")
                )
            )
            
            return result
        except Exception as e:
            self.logger.error(f"Error releasing UAS: {e}")
            return {"error": str(e)}
    
    def _handle_update_uas_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Обновление статуса БАС"""
        payload = message.get("payload", {})
        uas_id = payload.get("uas_id")
        updates = payload.get("updates", {})
        
        if not uas_id:
            return {"error": "uas_id is required"}
        
        try:
            # Обновляем состояние в ядре
            success, reason = self.core.update_uas_state(uas_id, updates)
            
            if success:
                # Логируем в сервисе
                self.service._operation_history.append({
                    "type": "update_status",
                    "uas_id": uas_id,
                    "updates": updates,
                    "timestamp": self._get_timestamp(),
                    "success": True
                })
                
                return {
                    "success": True,
                    "uas_id": uas_id,
                    "updates": updates
                }
            else:
                return {
                    "success": False,
                    "uas_id": uas_id,
                    "reason": reason
                }
        except Exception as e:
            self.logger.error(f"Error updating UAS status: {e}")
            return {"error": str(e)}
    
    def _handle_get_fleet_statistics(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Получение статистики парка"""
        try:
            stats = self.service.get_fleet_statistics()
            return stats
        except Exception as e:
            self.logger.error(f"Error getting fleet statistics: {e}")
            return {"error": str(e)}
    
    def _handle_get_developer_catalogs(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Получение каталогов разработчиков БАС"""
        try:
            if not self.service.developer_client:
                return {"error": "Developer client not configured"}
            
            loop = asyncio.get_event_loop()
            catalogs = loop.run_until_complete(
                self.service.developer_client.get_all_catalogs()
            )
            
            # Преобразуем в сериализуемый формат
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
                            "specifications": model.specifications,
                            "price": model.price,
                            "certification": model.certification,
                            "available_quantity": model.available_quantity
                        }
                        for model in catalog.models
                    ],
                    "updated_at": catalog.updated_at
                }
            
            return {
                "catalogs": result,
                "count": len(result)
            }
        except Exception as e:
            self.logger.error(f"Error getting developer catalogs: {e}")
            return {"error": str(e)}
    
    def _handle_purchase_uas(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Покупка БАС у разработчика"""
        payload = message.get("payload", {})
        developer_id = payload.get("developer_id")
        model_id = payload.get("model_id")
        quantity = payload.get("quantity", 1)
        
        if not all([developer_id, model_id]):
            return {"error": "developer_id and model_id are required"}
        
        try:
            if not self.service.developer_client:
                return {"error": "Developer client not configured"}
            
            # Выполняем покупку через клиент разработчика
            loop = asyncio.get_event_loop()
            purchase_result = loop.run_until_complete(
                self.service.developer_client.purchase_uas(
                    developer_id, model_id, quantity
                )
            )
            
            if purchase_result.get("success"):
                # Добавляем БАС в парк
                # Здесь должна быть логика добавления купленных БАС
                self.logger.info(f"Successfully purchased {quantity} UAS from {developer_id}")
            
            return purchase_result
        except Exception as e:
            self.logger.error(f"Error purchasing UAS: {e}")
            return {"error": str(e)}
    
    def _handle_get_purchase_history(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Получение истории покупок БАС"""
        payload = message.get("payload", {})
        developer_id = payload.get("developer_id")
        
        try:
            history = self.service.get_purchase_history(developer_id)
            return history
        except Exception as e:
            self.logger.error(f"Error getting purchase history: {e}")
            return {"error": str(e)}
    
    def _get_timestamp(self) -> str:
        """Получение текущей временной метки"""
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    def get_health_status(self) -> Dict[str, Any]:
        """Получение статуса здоровья компонента"""
        try:
            stats = self.service.get_fleet_statistics()
            
            # Проверяем критичные показатели
            health_issues = []
            
            if stats.get("certificates_expiring_soon", 0) > 0:
                health_issues.append("Certificates expiring soon")
            
            if stats.get("maintenance_required", 0) > stats["total"] * 0.3:
                health_issues.append("Many UAS require maintenance")
            
            if stats.get("average_battery", 1.0) < 0.3:
                health_issues.append("Low average battery level")
            
            return {
                "status": "degraded" if health_issues else "healthy",
                "issues": health_issues,
                "statistics": stats
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }