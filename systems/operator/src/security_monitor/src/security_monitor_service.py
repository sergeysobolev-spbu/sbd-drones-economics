"""
Security Monitor Service - Операционный домен D2_OPERATIONAL

Сервисный компонент для обработки некритичной логики:
- Аудит и логирование
- Статистика и метрики
- Интеграция с внешними системами
- Управление конфигурацией
"""

from typing import Dict, Any, List, Optional, DefaultDict
from collections import defaultdict
from datetime import datetime
import asyncio
import json
import os
from dataclasses import dataclass, asdict

from .security_monitor_core import SecurityMonitorCore, SecurityContext, PolicyResult, PolicyViolation


@dataclass
class AuditEntry:
    """Запись аудита"""

    timestamp: float
    trace_id: str
    sender_id: str
    action: str
    target: str
    result: str
    details: Optional[Dict[str, Any]] = None
    violation: Optional[PolicyViolation] = None


@dataclass
class SecurityMetrics:
    """Метрики безопасности"""

    total_requests: int = 0
    allowed_requests: int = 0
    denied_requests: int = 0
    audited_requests: int = 0
    violations_by_policy: Dict[str, int] = None
    violations_by_severity: Dict[str, int] = None
    request_rate: float = 0.0  # запросов в секунду

    def __post_init__(self):
        if self.violations_by_policy is None:
            self.violations_by_policy = {}
        if self.violations_by_severity is None:
            self.violations_by_severity = {}


class SecurityMonitorService:
    """
    Сервисный компонент монитора безопасности

    Обрабатывает некритичную логику:
    - Ведение аудита
    - Сбор метрик
    - Уведомления о нарушениях
    - Интеграция с Регулятором
    """

    def __init__(self, core: SecurityMonitorCore):
        """
        Инициализация сервиса

        Args:
            core: Ядро монитора безопасности
        """
        self.core = core
        self.audit_log: List[AuditEntry] = []
        self.request_history: DefaultDict[str, List[float]] = defaultdict(list)
        self.metrics = SecurityMetrics()
        self.notification_queue: asyncio.Queue = asyncio.Queue()

        # Конфигурация
        self.audit_retention_days = int(os.environ.get("AUDIT_RETENTION_DAYS", "30"))
        self.metrics_window_minutes = int(os.environ.get("METRICS_WINDOW_MINUTES", "5"))
        self.enable_notifications = os.environ.get("ENABLE_NOTIFICATIONS", "true").lower() == "true"

    async def process_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обработка запроса с проверкой безопасности

        Args:
            message: Входящее сообщение

        Returns:
            Результат проверки
        """
        # Извлекаем контекст безопасности
        context = self._extract_security_context(message)

        # Проверяем rate limit
        sender_id = context.sender_id
        self.request_history[sender_id].append(context.timestamp)

        rate_ok, rate_msg = self.core.check_rate_limit(sender_id, context.action, self.request_history[sender_id])

        if not rate_ok:
            # Rate limit превышен
            violation = PolicyViolation(
                policy_id="P4",
                policy_name="Контроль частоты запросов",
                violation_type="rate_limit_exceeded",
                details=rate_msg,
                severity="medium",
                timestamp=context.timestamp,
            )

            await self._handle_violation(context, PolicyResult.DENY, violation)

            return {"allowed": False, "reason": "rate_limit_exceeded", "details": rate_msg, "policy": "P4"}

        # Основная проверка политик
        result, violation = self.core.validate_request(context)

        # Обновляем метрики
        self._update_metrics(result, violation)

        # Создаем запись аудита
        audit_entry = AuditEntry(
            timestamp=context.timestamp,
            trace_id=context.trace_id or "no-trace",
            sender_id=context.sender_id,
            action=context.action,
            target=context.target_component,
            result=result.value,
            details={"sender_role": context.sender_role},
            violation=violation,
        )

        self.audit_log.append(audit_entry)

        # Обрабатываем результат
        if result == PolicyResult.DENY:
            await self._handle_violation(context, result, violation)
            return {
                "allowed": False,
                "reason": violation.violation_type,
                "details": violation.details,
                "policy": violation.policy_id,
            }
        elif result == PolicyResult.AUDIT:
            # Разрешаем, но отправляем уведомление
            if self.enable_notifications:
                await self._send_notification(context, violation, "warning")
            return {"allowed": True, "audited": True, "warning": violation.details if violation else None}
        else:  # ALLOW
            return {"allowed": True, "audited": False}

    def _extract_security_context(self, message: Dict[str, Any]) -> SecurityContext:
        """Извлечение контекста безопасности из сообщения"""
        payload = message.get("payload", {})

        return SecurityContext(
            sender_id=message.get("sender", "unknown"),
            sender_role=message.get("sender_role", "unknown"),
            action=message.get("action", "unknown"),
            target_component=message.get("target", "unknown"),
            payload_hash=self.core.calculate_payload_hash(payload),
            timestamp=message.get("timestamp", datetime.now().timestamp()),
            trace_id=message.get("trace_id"),
        )

    def _update_metrics(self, result: PolicyResult, violation: Optional[PolicyViolation]):
        """Обновление метрик"""
        self.metrics.total_requests += 1

        if result == PolicyResult.ALLOW:
            self.metrics.allowed_requests += 1
        elif result == PolicyResult.DENY:
            self.metrics.denied_requests += 1
        elif result == PolicyResult.AUDIT:
            self.metrics.audited_requests += 1

        if violation:
            # По политике
            policy_id = violation.policy_id
            if policy_id not in self.metrics.violations_by_policy:
                self.metrics.violations_by_policy[policy_id] = 0
            self.metrics.violations_by_policy[policy_id] += 1

            # По severity
            severity = violation.severity
            if severity not in self.metrics.violations_by_severity:
                self.metrics.violations_by_severity[severity] = 0
            self.metrics.violations_by_severity[severity] += 1

    async def _handle_violation(self, context: SecurityContext, result: PolicyResult, violation: PolicyViolation):
        """Обработка нарушения политики"""
        # Отправляем уведомление
        if self.enable_notifications:
            severity = "critical" if result == PolicyResult.DENY else "warning"
            await self._send_notification(context, violation, severity)

        # Логируем в системный журнал
        # В реальной системе здесь была бы интеграция с SIEM

    async def _send_notification(self, context: SecurityContext, violation: PolicyViolation, severity: str):
        """Отправка уведомления о нарушении"""
        notification = {
            "type": "security_violation",
            "severity": severity,
            "timestamp": datetime.now().isoformat(),
            "trace_id": context.trace_id,
            "violation": {
                "policy_id": violation.policy_id,
                "policy_name": violation.policy_name,
                "type": violation.violation_type,
                "details": violation.details,
            },
            "context": {"sender_id": context.sender_id, "action": context.action, "target": context.target_component},
        }

        await self.notification_queue.put(notification)

    def get_audit_log(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        sender_id: Optional[str] = None,
        action: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Получение записей аудита с фильтрацией

        Args:
            start_time: Начало периода
            end_time: Конец периода
            sender_id: Фильтр по отправителю
            action: Фильтр по действию

        Returns:
            Список записей аудита
        """
        filtered_entries = self.audit_log

        if start_time:
            filtered_entries = [e for e in filtered_entries if e.timestamp >= start_time]

        if end_time:
            filtered_entries = [e for e in filtered_entries if e.timestamp <= end_time]

        if sender_id:
            filtered_entries = [e for e in filtered_entries if e.sender_id == sender_id]

        if action:
            filtered_entries = [e for e in filtered_entries if e.action == action]

        # Конвертируем в словари
        return [self._audit_entry_to_dict(e) for e in filtered_entries]

    def _audit_entry_to_dict(self, entry: AuditEntry) -> Dict[str, Any]:
        """Преобразование записи аудита в словарь"""
        result = asdict(entry)

        # Преобразуем violation если есть
        if entry.violation:
            result["violation"] = asdict(entry.violation)

        # Добавляем читаемую дату
        result["datetime"] = datetime.fromtimestamp(entry.timestamp).isoformat()

        return result

    def get_metrics(self) -> Dict[str, Any]:
        """Получение текущих метрик"""
        # Вычисляем rate
        window_start = datetime.now().timestamp() - (self.metrics_window_minutes * 60)
        recent_requests = sum(len([t for t in times if t >= window_start]) for times in self.request_history.values())

        self.metrics.request_rate = recent_requests / (self.metrics_window_minutes * 60)

        return {
            "summary": {
                "total_requests": self.metrics.total_requests,
                "allowed": self.metrics.allowed_requests,
                "denied": self.metrics.denied_requests,
                "audited": self.metrics.audited_requests,
                "request_rate": round(self.metrics.request_rate, 2),
            },
            "violations": {
                "by_policy": self.metrics.violations_by_policy,
                "by_severity": self.metrics.violations_by_severity,
            },
            "core_violations": self.core.get_violations_summary(),
        }

    async def cleanup_old_data(self):
        """Очистка старых данных"""
        cutoff_time = datetime.now().timestamp() - (self.audit_retention_days * 86400)

        # Очищаем аудит
        self.audit_log = [e for e in self.audit_log if e.timestamp >= cutoff_time]

        # Очищаем историю запросов
        for sender_id in list(self.request_history.keys()):
            self.request_history[sender_id] = [t for t in self.request_history[sender_id] if t >= cutoff_time]

            # Удаляем пустые записи
            if not self.request_history[sender_id]:
                del self.request_history[sender_id]

    def export_audit_log(self, filepath: str):
        """Экспорт журнала аудита в файл"""
        audit_data = self.get_audit_log()

        with open(filepath, "w") as f:
            json.dump(audit_data, f, indent=2)

    def get_security_report(self) -> Dict[str, Any]:
        """Генерация отчета по безопасности"""
        metrics = self.get_metrics()

        # Анализируем тренды
        total = metrics["summary"]["total_requests"]
        if total > 0:
            deny_rate = metrics["summary"]["denied"] / total * 100
            audit_rate = metrics["summary"]["audited"] / total * 100
        else:
            deny_rate = audit_rate = 0

        return {
            "generated_at": datetime.now().isoformat(),
            "period": f"last {self.audit_retention_days} days",
            "metrics": metrics,
            "analysis": {
                "deny_rate_percent": round(deny_rate, 2),
                "audit_rate_percent": round(audit_rate, 2),
                "top_violated_policies": self._get_top_violated_policies(),
                "high_risk_senders": self._get_high_risk_senders(),
            },
            "recommendations": self._generate_recommendations(metrics),
        }

    def _get_top_violated_policies(self, limit: int = 3) -> List[Dict[str, Any]]:
        """Получение наиболее нарушаемых политик"""
        violations = self.metrics.violations_by_policy

        sorted_policies = sorted(violations.items(), key=lambda x: x[1], reverse=True)[:limit]

        return [{"policy_id": policy_id, "violations": count} for policy_id, count in sorted_policies]

    def _get_high_risk_senders(self, threshold: int = 5) -> List[str]:
        """Получение отправителей с большим количеством нарушений"""
        sender_violations = defaultdict(int)

        for entry in self.audit_log:
            if entry.violation:
                sender_violations[entry.sender_id] += 1

        return [sender_id for sender_id, count in sender_violations.items() if count >= threshold]

    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Генерация рекомендаций по безопасности"""
        recommendations = []

        # Проверяем rate limit нарушения
        p4_violations = metrics["violations"]["by_policy"].get("P4", 0)
        if p4_violations > 10:
            recommendations.append(
                "Высокое количество нарушений rate limit. "
                "Рекомендуется пересмотреть лимиты или усилить защиту от DDoS."
            )

        # Проверяем критические нарушения
        critical_violations = metrics["violations"]["by_severity"].get("critical", 0)
        if critical_violations > 0:
            recommendations.append(
                f"Обнаружено {critical_violations} критических нарушений. " "Требуется немедленное расследование."
            )

        # Проверяем общий уровень отказов
        total = metrics["summary"]["total_requests"]
        if total > 0 and metrics["summary"]["denied"] / total > 0.1:
            recommendations.append("Более 10% запросов отклонено. " "Возможны проблемы с авторизацией или атака.")

        if not recommendations:
            recommendations.append("Система функционирует в пределах нормы.")

        return recommendations
