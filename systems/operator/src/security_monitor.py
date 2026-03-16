"""
Монитор безопасности системы Эксплуатант

Критически важный компонент (D0_CRITICAL), обеспечивающий
соблюдение всех политик безопасности.
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from sdk.base_component import BaseComponent
from broker.system_bus import SystemBus
from systems.operator.src.topics import (
    ComponentTopics,
    SecurityMonitorActions,
    SystemTopics
)


class PolicyResult(Enum):
    """Результат проверки политики"""
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_ADDITIONAL_CHECK = "require_additional_check"


@dataclass
class PolicyViolation:
    """Нарушение политики безопасности"""
    policy_id: str
    policy_name: str
    timestamp: str
    sender: str
    action: str
    reason: str
    severity: str  # low, medium, high, critical


@dataclass
class SecurityPolicy:
    """Политика безопасности"""
    id: str
    name: str
    description: str
    rules: List[str]
    severity: str = "medium"


class SecurityMonitor(BaseComponent):
    """
    Монитор безопасности - контролирует все операции в системе
    и обеспечивает соблюдение политик безопасности.
    """
    
    def __init__(self, component_id: str, bus: SystemBus):
        self.logger = logging.getLogger(f"SecurityMonitor.{component_id}")
        
        # Политики безопасности
        self.policies = self._init_policies()
        
        # Журнал нарушений
        self.violations: List[PolicyViolation] = []
        
        # Кеш проверенных сертификатов
        self.certificate_cache: Dict[str, Dict[str, Any]] = {}
        
        # Статистика
        self.stats = {
            "total_requests": 0,
            "allowed_requests": 0,
            "denied_requests": 0,
            "violations": 0
        }
        
        super().__init__(
            component_id=component_id,
            component_type="security_monitor",
            topic=ComponentTopics.SECURITY_MONITOR,
            bus=bus
        )
        
        self.logger.info(f"Security Monitor {component_id} initialized with {len(self.policies)} policies")
    
    def _init_policies(self) -> Dict[str, SecurityPolicy]:
        """Инициализация политик безопасности"""
        return {
            "P1": SecurityPolicy(
                id="P1",
                name="Authorized Operators Only",
                description="Только авторизованные операторы могут отправлять команды",
                rules=[
                    "sender.role in ['operator', 'admin']",
                    "sender.authenticated == True",
                    "command.target in operator.fleet"
                ],
                severity="critical"
            ),
            "P2": SecurityPolicy(
                id="P2",
                name="Flight Plan Compliance",
                description="Миссия должна соответствовать утверждённому плану",
                rules=[
                    "mission.plan_approved_by == 'UTM'",
                    "mission.waypoints == approved_plan.waypoints",
                    "mission.time_window in approved_plan.time_window"
                ],
                severity="high"
            ),
            "P3": SecurityPolicy(
                id="P3",
                name="Profitability Check",
                description="Маржинальность не менее 10%",
                rules=[
                    "(order.price - mission.cost) / order.price >= 0.1",
                    "mission.insurance_valid == True"
                ],
                severity="medium"
            ),
            "P4": SecurityPolicy(
                id="P4",
                name="UAS Certification",
                description="Использование только сертифицированных БАС",
                rules=[
                    "uas.certificate_status == 'valid'",
                    "uas.certificate_expiry > current_time"
                ],
                severity="critical"
            ),
            "P5": SecurityPolicy(
                id="P5",
                name="Data Access Control",
                description="Доступ к данным только для авторизованных",
                rules=[
                    "requester.clearance_level >= data.classification_level",
                    "requester.need_to_know == True"
                ],
                severity="high"
            )
        }
    
    def _register_handlers(self):
        """Регистрация обработчиков"""
        self.register_handler(SecurityMonitorActions.VALIDATE_REQUEST, self._handle_validate_request)
        self.register_handler(SecurityMonitorActions.CHECK_POLICY, self._handle_check_policy)
        self.register_handler(SecurityMonitorActions.LOG_VIOLATION, self._handle_log_violation)
        self.register_handler(SecurityMonitorActions.GET_SECURITY_STATUS, self._handle_get_security_status)
    
    def _handle_validate_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация запроса на соответствие всем политикам"""
        self.stats["total_requests"] += 1
        
        payload = message.get("payload", {})
        request = payload.get("request", {})
        context = payload.get("context", {})
        
        self.logger.debug(f"Validating request: {request.get('action')} from {request.get('sender')}")
        
        # Проверяем все применимые политики
        violations = []
        applicable_policies = self._get_applicable_policies(request, context)
        
        for policy_id in applicable_policies:
            result, reason = self._check_policy(policy_id, request, context)
            
            if result == PolicyResult.DENY:
                violation = PolicyViolation(
                    policy_id=policy_id,
                    policy_name=self.policies[policy_id].name,
                    timestamp=datetime.utcnow().isoformat(),
                    sender=request.get("sender", "unknown"),
                    action=request.get("action", "unknown"),
                    reason=reason,
                    severity=self.policies[policy_id].severity
                )
                violations.append(violation)
                self._log_violation(violation)
        
        if violations:
            self.stats["denied_requests"] += 1
            return {
                "allowed": False,
                "violations": [asdict(v) for v in violations],
                "message": "Request denied due to policy violations"
            }
        
        self.stats["allowed_requests"] += 1
        return {
            "allowed": True,
            "message": "Request validated successfully"
        }
    
    def _handle_check_policy(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Проверка конкретной политики"""
        payload = message.get("payload", {})
        policy_id = payload.get("policy_id")
        request = payload.get("request", {})
        context = payload.get("context", {})
        
        if policy_id not in self.policies:
            return {
                "error": f"Unknown policy: {policy_id}",
                "result": PolicyResult.DENY.value
            }
        
        result, reason = self._check_policy(policy_id, request, context)
        
        return {
            "policy_id": policy_id,
            "result": result.value,
            "reason": reason
        }
    
    def _handle_log_violation(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Логирование нарушения политики"""
        payload = message.get("payload", {})
        
        violation = PolicyViolation(
            policy_id=payload.get("policy_id", "unknown"),
            policy_name=payload.get("policy_name", "unknown"),
            timestamp=datetime.utcnow().isoformat(),
            sender=payload.get("sender", "unknown"),
            action=payload.get("action", "unknown"),
            reason=payload.get("reason", ""),
            severity=payload.get("severity", "medium")
        )
        
        self._log_violation(violation)
        
        return {
            "logged": True,
            "violation_id": len(self.violations)
        }
    
    def _handle_get_security_status(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Получение статуса безопасности"""
        return {
            "stats": self.stats,
            "active_policies": len(self.policies),
            "recent_violations": [
                asdict(v) for v in self.violations[-10:]  # Последние 10 нарушений
            ],
            "certificate_cache_size": len(self.certificate_cache)
        }
    
    def _get_applicable_policies(self, request: Dict[str, Any], context: Dict[str, Any]) -> List[str]:
        """Определение применимых политик для запроса"""
        action = request.get("action", "")
        
        # Базовые политики применяются всегда
        applicable = ["P1", "P5"]
        
        # Политики для конкретных действий
        if "mission" in action.lower() or "flight" in action.lower():
            applicable.extend(["P2", "P4"])
        
        if "order" in action.lower() or "proposal" in action.lower():
            applicable.append("P3")
        
        if "uas" in action.lower() or "drone" in action.lower():
            applicable.append("P4")
        
        return applicable
    
    def _check_policy(self, policy_id: str, request: Dict[str, Any], context: Dict[str, Any]) -> Tuple[PolicyResult, str]:
        """Проверка конкретной политики"""
        policy = self.policies.get(policy_id)
        if not policy:
            return PolicyResult.DENY, f"Policy {policy_id} not found"
        
        # Здесь должна быть реальная проверка правил
        # Для прототипа используем упрощённую логику
        
        if policy_id == "P1":  # Проверка авторизации
            sender = request.get("sender", {})
            if isinstance(sender, str):
                # Если sender - строка, считаем что это ID компонента системы
                if sender.startswith("operator."):
                    return PolicyResult.ALLOW, "Internal component"
                return PolicyResult.DENY, "Unauthorized sender"
            
            role = sender.get("role", "")
            authenticated = sender.get("authenticated", False)
            
            if role in ["operator", "admin"] and authenticated:
                return PolicyResult.ALLOW, "Authorized operator"
            return PolicyResult.DENY, "Not an authorized operator"
        
        elif policy_id == "P2":  # Проверка плана полёта
            if "mission" not in context:
                return PolicyResult.ALLOW, "Not a mission request"
            
            mission = context.get("mission", {})
            if mission.get("plan_approved_by") == "UTM":
                return PolicyResult.ALLOW, "Mission approved by UTM"
            return PolicyResult.DENY, "Mission not approved by UTM"
        
        elif policy_id == "P3":  # Проверка маржинальности
            if "order" not in context:
                return PolicyResult.ALLOW, "Not an order request"
            
            order = context.get("order", {})
            price = order.get("price", 0)
            cost = order.get("cost", 0)
            
            if price > 0 and (price - cost) / price >= 0.1:
                return PolicyResult.ALLOW, "Profitability check passed"
            return PolicyResult.DENY, "Insufficient margin"
        
        elif policy_id == "P4":  # Проверка сертификации БАС
            if "uas" not in context:
                return PolicyResult.ALLOW, "Not a UAS request"
            
            uas = context.get("uas", {})
            uas_id = uas.get("id")
            
            # Проверяем кеш
            if uas_id in self.certificate_cache:
                cert = self.certificate_cache[uas_id]
                if cert.get("status") == "valid":
                    return PolicyResult.ALLOW, "Valid certificate (cached)"
                return PolicyResult.DENY, "Invalid certificate"
            
            # Здесь должен быть запрос к Регулятору
            # Для прототипа считаем все БАС сертифицированными
            return PolicyResult.REQUIRE_ADDITIONAL_CHECK, "Certificate check required"
        
        elif policy_id == "P5":  # Контроль доступа к данным
            requester = request.get("sender", {})
            if isinstance(requester, str):
                # Внутренние компоненты имеют доступ
                if requester.startswith("operator."):
                    return PolicyResult.ALLOW, "Internal component access"
            
            data_type = request.get("data_type", "")
            if data_type in ["public", "operational"]:
                return PolicyResult.ALLOW, "Public data access"
            return PolicyResult.DENY, "Insufficient clearance"
        
        return PolicyResult.ALLOW, "Policy check passed (default)"
    
    def _log_violation(self, violation: PolicyViolation):
        """Логирование нарушения"""
        self.violations.append(violation)
        self.stats["violations"] += 1
        
        # Логируем в зависимости от серьёзности
        log_msg = f"Policy violation: {violation.policy_name} - {violation.reason}"
        
        if violation.severity == "critical":
            self.logger.critical(log_msg)
        elif violation.severity == "high":
            self.logger.error(log_msg)
        elif violation.severity == "medium":
            self.logger.warning(log_msg)
        else:
            self.logger.info(log_msg)
        
        # Отправляем уведомление о критических нарушениях
        if violation.severity in ["critical", "high"]:
            self._notify_security_event(violation)
    
    def _notify_security_event(self, violation: PolicyViolation):
        """Уведомление о событии безопасности"""
        # Отправляем событие в систему мониторинга
        event = {
            "event_type": "security_violation",
            "severity": violation.severity,
            "violation": asdict(violation),
            "system": "operator",
            "component": self.component_id
        }
        
        # В реальной системе здесь был бы publish в топик событий безопасности
        self.logger.info(f"Security event notification: {event}")
    
    def validate_inter_component_flow(self, source: str, target: str, action: str) -> bool:
        """
        Проверка разрешённых потоков данных между компонентами
        согласно архитектуре безопасности
        """
        # Определяем домены компонентов
        component_domains = {
            "security_monitor": "D0_CRITICAL",
            "command_validator": "D0_CRITICAL",
            "fleet_manager": "D1_TRUSTED",
            "mission_planner": "D1_TRUSTED",
            "business_logic": "D2_OPERATIONAL",
            "order_manager": "D2_OPERATIONAL",
            "api_gateway": "D3_EXTERNAL"
        }
        
        # Правила потоков между доменами
        # D0 может обращаться ко всем
        # D1 может обращаться к D1, D2, D3
        # D2 может обращаться к D2, D3
        # D3 может обращаться только к D3
        # Обратные потоки запрещены (кроме ответов)
        
        source_domain = component_domains.get(source, "D3_EXTERNAL")
        target_domain = component_domains.get(target, "D3_EXTERNAL")
        
        allowed_flows = {
            "D0_CRITICAL": ["D0_CRITICAL", "D1_TRUSTED", "D2_OPERATIONAL", "D3_EXTERNAL"],
            "D1_TRUSTED": ["D1_TRUSTED", "D2_OPERATIONAL", "D3_EXTERNAL"],
            "D2_OPERATIONAL": ["D2_OPERATIONAL", "D3_EXTERNAL"],
            "D3_EXTERNAL": ["D3_EXTERNAL"]
        }
        
        if target_domain in allowed_flows.get(source_domain, []):
            return True
        
        # Проверяем, является ли это ответом
        if action.endswith("_response") or action == "reply":
            return True
        
        self.logger.warning(f"Blocked flow: {source}({source_domain}) -> {target}({target_domain})")
        return False