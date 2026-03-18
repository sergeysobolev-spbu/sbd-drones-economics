"""
BusinessLogic - компонент бизнес-логики системы Эксплуатант

Обеспечивает экономическую эффективность операций через
проверку маржинальности и управление коммерческими предложениями
"""

import logging
from datetime import datetime
from typing import Any, Dict

from sdk.base_component import BaseComponent
from broker.system_bus import SystemBus
from systems.operator.src.topics import (
    ComponentTopics,
    BusinessLogicActions,
    SecurityMonitorActions,
    FleetManagerActions,
)

from .business_logic_core import BusinessLogicCore
from .business_logic_service import BusinessLogicService


class BusinessLogic(BaseComponent):
    """
    Компонент бизнес-логики

    Интегрирует критическое ядро (D0) и сервисный слой (D2)
    для обеспечения экономической безопасности операций
    """

    def __init__(self, component_id: str, bus: SystemBus):
        self.logger = logging.getLogger(f"BusinessLogic.{component_id}")

        # Инициализация ядра и сервиса
        self.core = BusinessLogicCore()
        self.service = BusinessLogicService(self.core)

        # Базовая инициализация компонента
        super().__init__(
            component_id=component_id, component_type="business_logic", topic=ComponentTopics.BUSINESS_LOGIC, bus=bus
        )

        self.logger.info(f"Business Logic {component_id} initialized")

    def _register_handlers(self):
        """Регистрация обработчиков сообщений"""
        # Основные действия
        self.register_handler(BusinessLogicActions.CALCULATE_COST, self._handle_calculate_cost)
        self.register_handler(BusinessLogicActions.CHECK_PROFITABILITY, self._handle_check_profitability)
        self.register_handler(BusinessLogicActions.CREATE_PROPOSAL, self._handle_create_proposal)
        self.register_handler(BusinessLogicActions.PROCESS_ORDER, self._handle_process_order)
        self.register_handler(BusinessLogicActions.GET_STATISTICS, self._handle_get_statistics)

    async def _handle_calculate_cost(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка запроса на расчет стоимости"""
        try:
            payload = message.get("payload", {})
            mission_data = payload.get("mission_data", {})

            # Проверка через Security Monitor
            security_check = await self._check_with_security_monitor(
                action="calculate_cost", request=payload, context={"mission_data": mission_data}
            )

            if not security_check.get("allowed", False):
                return {"error": "Security check failed", "violations": security_check.get("violations", [])}

            # Расчет стоимости
            cost_breakdown = self.service.calculate_mission_cost(mission_data)

            return {
                "cost_breakdown": {
                    "uas_cost": cost_breakdown.uas_cost,
                    "operator_cost": cost_breakdown.operator_cost,
                    "insurance_cost": cost_breakdown.insurance_cost,
                    "total": cost_breakdown.total,
                },
                "total_cost": cost_breakdown.total,
            }

        except Exception as e:
            self.logger.error(f"Error calculating cost: {e}")
            return {"error": str(e)}

    async def _handle_check_profitability(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка проверки маржинальности"""
        try:
            payload = message.get("payload", {})
            price = payload.get("price", 0)
            cost = payload.get("cost", 0)

            # Используем core для критической проверки
            margin_check = self.core.validate_margin(price, cost)

            # Проверка через Security Monitor
            security_check = await self._check_with_security_monitor(
                action="check_profitability",
                request=payload,
                context={"price": price, "cost": cost, "margin_percent": margin_check.margin_percent},
            )

            if not security_check.get("allowed", False):
                return {
                    "profitable": False,
                    "reason": "Security policy violation",
                    "violations": security_check.get("violations", []),
                }

            result = {
                "profitable": margin_check.is_valid,
                "margin_percent": margin_check.margin_percent,
                "min_margin_percent": margin_check.min_required,
            }

            if not margin_check.is_valid:
                result["reason"] = margin_check.reason
                result["suggested_price"] = self.core.calculate_min_price(cost)

            return result

        except Exception as e:
            self.logger.error(f"Error checking profitability: {e}")
            return {"error": str(e)}

    async def _handle_create_proposal(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка создания коммерческого предложения"""
        try:
            payload = message.get("payload", {})
            order_data = payload.get("order_data", {})

            # Проверка через Security Monitor
            security_check = await self._check_with_security_monitor(
                action="create_proposal", request=payload, context={"order_data": order_data}
            )

            if not security_check.get("allowed", False):
                return {"error": "Security check failed", "violations": security_check.get("violations", [])}

            # Создание предложения
            result = self.service.create_proposal(order_data)

            if "error" in result:
                return result

            # Логирование для аудита
            self.logger.info(
                f"Created proposal {result['proposal']['id']} " f"with margin {result['proposal']['margin_percent']}%"
            )

            return result

        except Exception as e:
            self.logger.error(f"Error creating proposal: {e}")
            return {"error": str(e)}

    async def _handle_process_order(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка заказа"""
        try:
            payload = message.get("payload", {})

            # Проверка через Security Monitor
            security_check = await self._check_with_security_monitor(
                action="process_order", request=payload, context={"order_data": payload}
            )

            if not security_check.get("allowed", False):
                return {"error": "Security check failed", "violations": security_check.get("violations", [])}

            # Обработка заказа
            result = self.service.process_order(payload)

            if "error" not in result:
                # Уведомляем Fleet Manager о необходимости резервирования БАС
                await self._notify_fleet_manager(payload)

            return result

        except Exception as e:
            self.logger.error(f"Error processing order: {e}")
            return {"error": str(e)}

    async def _handle_get_statistics(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Получение статистики"""
        try:
            stats = self.service.get_statistics()
            limits = self.core.get_economic_limits()

            return {"statistics": stats, "economic_limits": limits}

        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {"error": str(e)}

    async def _check_with_security_monitor(
        self, action: str, request: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Проверка операции через Security Monitor"""
        try:
            security_request = self.create_message_with_trace(
                action=SecurityMonitorActions.VALIDATE_REQUEST,
                payload={"request": {"action": action, "sender": self.component_id, **request}, "context": context},
            )

            response = await self.bus.request(ComponentTopics.SECURITY_MONITOR, security_request, timeout=5.0)

            if response and response.get("success"):
                return response.get("payload", {})

            return {"allowed": False, "error": "Security monitor not responding"}

        except Exception as e:
            self.logger.error(f"Security validation error: {e}")
            return {"allowed": False, "error": str(e)}

    async def _notify_fleet_manager(self, order_data: Dict[str, Any]) -> None:
        """Уведомить Fleet Manager о новом заказе"""
        try:
            notification = self.create_message_with_trace(
                action=FleetManagerActions.RESERVE_UAS,
                payload={"order_id": order_data.get("order_id"), "mission_data": order_data.get("mission_data", {})},
            )

            await self.bus.publish(ComponentTopics.FLEET_MANAGER, notification)

        except Exception as e:
            self.logger.error(f"Failed to notify fleet manager: {e}")

    def get_component_status(self) -> Dict[str, Any]:
        """Получить статус компонента"""
        return {
            "component_id": self.component_id,
            "component_type": self.component_type,
            "status": "running",
            "economic_limits": self.core.get_economic_limits(),
            "statistics": self.service.get_statistics(),
            "timestamp": datetime.utcnow().isoformat(),
        }
