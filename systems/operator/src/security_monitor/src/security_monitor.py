"""
Security Monitor Component - Основной компонент мониторинга безопасности

Объединяет функциональность Core (D0_CRITICAL) и Service (D2_OPERATIONAL)
для обеспечения комплексной защиты системы.
"""

from typing import Any, Dict
import asyncio
import logging

from sdk.base_component import BaseComponent
from broker.system_bus import SystemBus
from systems.operator.src.topics import ComponentTopics, SecurityMonitorActions, SystemTopics

from .security_monitor_core import SecurityMonitorCore
from .security_monitor_service import SecurityMonitorService


class SecurityMonitor(BaseComponent):
    """
    Компонент мониторинга безопасности

    Обеспечивает:
    - Проверку политик безопасности
    - Валидацию запросов
    - Аудит и логирование
    - Интеграцию с Регулятором
    """

    def __init__(self, component_id: str, bus: SystemBus):
        """
        Инициализация компонента

        Args:
            component_id: Уникальный идентификатор компонента
            bus: Системная шина
        """
        # Получаем топик компонента
        topic = ComponentTopics.get_security_monitor()

        super().__init__(
            component_id=component_id, component_type="security_monitor", topic=topic, bus=bus, enable_tracing=True
        )

        # Инициализируем подкомпоненты
        self.core = SecurityMonitorCore()
        self.service = SecurityMonitorService(self.core)

        # Настройка логирования
        self.logger = logging.getLogger(f"{self.__class__.__name__}.{component_id}")

        # Фоновые задачи
        self._background_tasks = []
        self._running = False

    def _register_handlers(self):
        """Регистрация обработчиков сообщений"""
        # Основные действия безопасности
        self.register_handler(SecurityMonitorActions.VALIDATE_REQUEST, self._handle_validate_request)
        self.register_handler(SecurityMonitorActions.CHECK_POLICY, self._handle_check_policy)
        self.register_handler(SecurityMonitorActions.LOG_VIOLATION, self._handle_log_violation)
        self.register_handler(SecurityMonitorActions.BLOCK_ACTION, self._handle_block_action)

        # Мониторинг и отчетность
        self.register_handler(SecurityMonitorActions.GET_SECURITY_STATUS, self._handle_get_security_status)
        self.register_handler(SecurityMonitorActions.AUDIT_OPERATION, self._handle_audit_operation)

        # Административные действия
        self.register_handler("get_audit_log", self._handle_get_audit_log)
        self.register_handler("get_metrics", self._handle_get_metrics)
        self.register_handler("get_security_report", self._handle_get_security_report)
        self.register_handler("export_audit", self._handle_export_audit)

    async def _handle_validate_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обработка запроса на валидацию

        Args:
            message: Сообщение с запросом

        Returns:
            Результат валидации
        """
        trace_context = self._extract_trace_context(message)

        try:
            # Валидируем НЕ вызов `validate_request`, а исходный запрос, пришедший в систему.
            payload = message.get("payload", {}) or {}
            original_request = payload.get("request", {}) or {}

            enriched_message = message.copy()
            sender_role = payload.get("sender_role", "unknown")
            enriched_message["target"] = payload.get("target_component", "operator_system")

            # Подменяем sender/action на исходные значения, чтобы политики применялись корректно.
            if original_request:
                enriched_message["sender"] = original_request.get("sender", enriched_message.get("sender", "unknown"))
                enriched_message["action"] = original_request.get("action", enriched_message.get("action", "unknown"))
                enriched_message["payload"] = original_request.get("payload", payload)

            # Если роль не передана явно, пытаемся вывести её из sender (демо-эвристика).
            if sender_role == "unknown":
                sender = str(enriched_message.get("sender", "") or "").lower()
                if sender.startswith("aggregator"):
                    sender_role = "aggregator"
                elif sender.startswith("operator"):
                    sender_role = "operator"
                elif any(k in sender for k in ("security", "fleet", "mission", "business")):
                    # Внутренние компоненты Эксплуатанта в демо считаем доверенными системными отправителями.
                    sender_role = "system"
                elif sender.startswith("shell") or sender.startswith("pytest"):
                    sender_role = "system"

            enriched_message["sender_role"] = sender_role

            # Обрабатываем через сервис
            result = await self.service.process_request(enriched_message)

            # Логируем результат
            self._log_with_trace(
                "info",
                f"Validation result: {result.get('allowed', False)}",
                trace_context,
                action=message.get("action"),
                allowed=result.get("allowed"),
                policy=result.get("policy"),
            )

            return result

        except Exception as e:
            self._log_with_trace("error", f"Error validating request: {e}", trace_context)
            return {"allowed": False, "error": str(e)}

    async def _handle_check_policy(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Проверка конкретной политики"""
        payload = message.get("payload", {})
        policy_id = payload.get("policy_id")

        if not policy_id:
            return {"error": "policy_id is required"}

        # Здесь была бы проверка конкретной политики
        # Для демонстрации возвращаем успех
        return {"policy_id": policy_id, "result": "allow", "details": f"Policy {policy_id} check passed"}

    async def _handle_log_violation(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Логирование нарушения безопасности"""
        payload = message.get("payload", {})

        # Создаем контекст для логирования
        trace_context = self._extract_trace_context(message)

        self._log_with_trace(
            "warning",
            f"Security violation logged: {payload.get('violation_type', 'unknown')}",
            trace_context,
            violation_type=payload.get("violation_type"),
            severity=payload.get("severity", "medium"),
            details=payload.get("details"),
        )

        return {"logged": True}

    async def _handle_block_action(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Блокировка действия"""
        payload = message.get("payload", {})
        action_to_block = payload.get("action")
        sender_to_block = payload.get("sender_id")

        # В реальной системе здесь была бы логика блокировки
        # Например, добавление в черный список

        return {"blocked": True, "action": action_to_block, "sender": sender_to_block}

    async def _handle_get_security_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Получение статуса безопасности"""
        metrics = self.service.get_metrics()
        violations_summary = self.core.get_violations_summary()

        return {
            "status": "operational",
            "metrics": metrics["summary"],
            "violations": violations_summary,
            "policies_loaded": len(self.core.policies),
            "audit_entries": len(self.service.audit_log),
        }

    async def _handle_audit_operation(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Аудит операции"""
        return {"audited": True, "entry_id": message.get("correlation_id")}

    async def _handle_get_audit_log(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Получение журнала аудита"""
        payload = message.get("payload", {})

        audit_log = self.service.get_audit_log(
            start_time=payload.get("start_time"),
            end_time=payload.get("end_time"),
            sender_id=payload.get("sender_id"),
            action=payload.get("action"),
        )

        return {"entries": audit_log, "count": len(audit_log)}

    async def _handle_get_metrics(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Получение метрик безопасности"""
        return self.service.get_metrics()

    async def _handle_get_security_report(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация отчета по безопасности"""
        return self.service.get_security_report()

    async def _handle_export_audit(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Экспорт журнала аудита"""
        payload = message.get("payload", {})
        filepath = payload.get("filepath", "/tmp/security_audit.json")

        try:
            self.service.export_audit_log(filepath)
            return {"exported": True, "filepath": filepath}
        except Exception as e:
            return {"exported": False, "error": str(e)}

    def start(self):
        """Запуск компонента"""
        super().start()
        self._running = True

        # Запускаем фоновые задачи
        self._start_background_tasks()

        # Отправляем уведомление о запуске
        self._notify_regulator_startup()

    def stop(self):
        """Остановка компонента"""
        self._running = False

        # Останавливаем фоновые задачи
        self._stop_background_tasks()

        # Отправляем уведомление об остановке
        self._notify_regulator_shutdown()

        super().stop()

    def _start_background_tasks(self):
        """Запуск фоновых задач"""
        # Периодическая очистка старых данных
        cleanup_task = asyncio.create_task(self._periodic_cleanup())
        self._background_tasks.append(cleanup_task)

        # Обработка очереди уведомлений
        notification_task = asyncio.create_task(self._process_notifications())
        self._background_tasks.append(notification_task)

    def _stop_background_tasks(self):
        """Остановка фоновых задач"""
        for task in self._background_tasks:
            task.cancel()
        self._background_tasks.clear()

    async def _periodic_cleanup(self):
        """Периодическая очистка старых данных"""
        while self._running:
            try:
                await asyncio.sleep(3600)  # Каждый час
                await self.service.cleanup_old_data()
                self.logger.info("Completed periodic cleanup")
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in periodic cleanup: {e}")

    async def _process_notifications(self):
        """Обработка очереди уведомлений"""
        while self._running:
            try:
                # Получаем уведомление из очереди
                notification = await asyncio.wait_for(self.service.notification_queue.get(), timeout=1.0)

                # Отправляем уведомление Регулятору
                await self._send_notification_to_regulator(notification)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error processing notification: {e}")

    async def _send_notification_to_regulator(self, notification: Dict[str, Any]):
        """Отправка уведомления Регулятору"""
        try:
            # Отправляем на топик Регулятора
            self.publish_event(topic=SystemTopics.REGULATOR, action="security_notification", payload=notification)

            self.logger.info(f"Sent security notification to Regulator: {notification['type']}")

        except Exception as e:
            self.logger.error(f"Failed to send notification to Regulator: {e}")

    def _notify_regulator_startup(self):
        """Уведомление Регулятора о запуске"""
        notification = {
            "type": "component_startup",
            "component_id": self.component_id,
            "component_type": self.component_type,
            "timestamp": asyncio.get_event_loop().time(),
        }

        self.publish_event(topic=SystemTopics.REGULATOR, action="component_status", payload=notification)

    def _notify_regulator_shutdown(self):
        """Уведомление Регулятора об остановке"""
        notification = {
            "type": "component_shutdown",
            "component_id": self.component_id,
            "component_type": self.component_type,
            "timestamp": asyncio.get_event_loop().time(),
        }

        self.publish_event(topic=SystemTopics.REGULATOR, action="component_status", payload=notification)
