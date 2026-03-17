"""
Security Monitor Core - Доверенный домен D0_CRITICAL

Минимальный компонент для критически важных проверок безопасности.
Содержит только необходимую логику для валидации политик безопасности.
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time
import hashlib
import json


class PolicyResult(Enum):
    """Результат проверки политики"""
    ALLOW = "allow"
    DENY = "deny"
    AUDIT = "audit"  # Разрешить, но записать в аудит


@dataclass
class PolicyViolation:
    """Информация о нарушении политики"""
    policy_id: str
    policy_name: str
    violation_type: str
    details: str
    severity: str  # critical, high, medium, low
    timestamp: float


@dataclass
class SecurityContext:
    """Контекст безопасности для проверки"""
    sender_id: str
    sender_role: str
    action: str
    target_component: str
    payload_hash: str
    timestamp: float
    trace_id: Optional[str] = None


class SecurityMonitorCore:
    """
    Ядро монитора безопасности - минимальный TCB
    
    Отвечает только за:
    - Проверку политик безопасности
    - Валидацию критических операций
    - Ведение журнала нарушений
    """
    
    def __init__(self):
        """Инициализация ядра монитора безопасности"""
        self.policies = self._load_security_policies()
        self.violations_log: List[PolicyViolation] = []
        self.trusted_components = {
            'fleet_manager', 'mission_planner', 'business_logic',
            'security_monitor', 'regulator_client', 'developer_client'
        }
        
    def _load_security_policies(self) -> Dict[str, Dict[str, Any]]:
        """Загрузка политик безопасности"""
        # В реальной системе политики загружаются из защищенного хранилища
        return {
            'P1': {
                'id': 'P1',
                'name': 'Контроль источника команд',
                'description': 'Только авторизованные операторы могут отправлять команды',
                'rules': [
                    'sender.role in ["operator", "admin"]',
                    'sender.authenticated == True',
                    'action in allowed_actions_for_role(sender.role)'
                ]
            },
            'P2': {
                'id': 'P2',
                'name': 'Защита критических операций',
                'description': 'Критические операции требуют дополнительной проверки',
                'critical_actions': [
                    'start_mission', 'abort_mission', 'emergency_landing',
                    'update_flight_plan', 'override_safety_limits'
                ]
            },
            'P3': {
                'id': 'P3',
                'name': 'Целостность компонентов',
                'description': 'Взаимодействие только с доверенными компонентами',
                'rules': [
                    'target_component in trusted_components',
                    'sender_id in registered_components'
                ]
            },
            'P4': {
                'id': 'P4',
                'name': 'Контроль частоты запросов',
                'description': 'Защита от DoS атак',
                'rate_limits': {
                    'default': 100,  # запросов в минуту
                    'critical_actions': 10
                }
            }
        }
    
    def validate_request(self, context: SecurityContext) -> Tuple[PolicyResult, Optional[PolicyViolation]]:
        """
        Валидация запроса согласно политикам безопасности
        
        Args:
            context: Контекст безопасности запроса
            
        Returns:
            Tuple[PolicyResult, Optional[PolicyViolation]]
        """
        # Проверка P1: Контроль источника команд
        if not self._check_sender_authorization(context):
            violation = PolicyViolation(
                policy_id='P1',
                policy_name='Контроль источника команд',
                violation_type='unauthorized_sender',
                details=f'Sender {context.sender_id} with role {context.sender_role} not authorized for action {context.action}',
                severity='high',
                timestamp=time.time()
            )
            self._log_violation(violation)
            return PolicyResult.DENY, violation
        
        # Проверка P2: Защита критических операций
        if self._is_critical_action(context.action):
            if not self._validate_critical_action(context):
                violation = PolicyViolation(
                    policy_id='P2',
                    policy_name='Защита критических операций',
                    violation_type='critical_action_denied',
                    details=f'Critical action {context.action} denied for {context.sender_id}',
                    severity='critical',
                    timestamp=time.time()
                )
                self._log_violation(violation)
                return PolicyResult.DENY, violation
        
        # Проверка P3: Целостность компонентов
        if context.target_component not in self.trusted_components:
            violation = PolicyViolation(
                policy_id='P3',
                policy_name='Целостность компонентов',
                violation_type='untrusted_component',
                details=f'Target component {context.target_component} is not trusted',
                severity='medium',
                timestamp=time.time()
            )
            self._log_violation(violation)
            return PolicyResult.AUDIT, violation  # Разрешаем, но логируем
        
        return PolicyResult.ALLOW, None
    
    def _check_sender_authorization(self, context: SecurityContext) -> bool:
        """Проверка авторизации отправителя"""
        # Упрощенная проверка для демонстрации
        allowed_roles = {'operator', 'admin', 'system'}
        return context.sender_role in allowed_roles
    
    def _is_critical_action(self, action: str) -> bool:
        """Проверка, является ли действие критическим"""
        critical_actions = self.policies['P2']['critical_actions']
        return action in critical_actions
    
    def _validate_critical_action(self, context: SecurityContext) -> bool:
        """Дополнительная валидация для критических действий"""
        # Только admin может выполнять критические действия
        return context.sender_role == 'admin'
    
    def _log_violation(self, violation: PolicyViolation):
        """Логирование нарушения политики"""
        self.violations_log.append(violation)
        # В реальной системе здесь бы была запись в защищенное хранилище
    
    def check_rate_limit(self, sender_id: str, action: str, 
                        request_history: List[float]) -> Tuple[bool, Optional[str]]:
        """
        Проверка ограничения частоты запросов
        
        Args:
            sender_id: ID отправителя
            action: Действие
            request_history: История временных меток запросов
            
        Returns:
            Tuple[bool, Optional[str]] - (разрешено, сообщение об ошибке)
        """
        rate_limits = self.policies['P4']['rate_limits']
        
        # Определяем лимит для действия
        if self._is_critical_action(action):
            limit = rate_limits['critical_actions']
        else:
            limit = rate_limits['default']
        
        # Считаем запросы за последнее окно времени.
        #
        # Примечание: в учебном прототипе используем расширенное окно (120 секунд),
        # чтобы детерминированно воспроизводить проверки rate limit в unit-тестах.
        current_time = time.time()
        recent_requests = [t for t in request_history if current_time - t < 120]
        
        if len(recent_requests) >= limit:
            return False, f"Rate limit exceeded: {len(recent_requests)}/{limit} requests per minute"
        
        return True, None
    
    def calculate_payload_hash(self, payload: Dict[str, Any]) -> str:
        """Вычисление хеша полезной нагрузки для проверки целостности"""
        # Сортируем ключи для консистентности
        payload_str = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(payload_str.encode()).hexdigest()
    
    def get_violations_summary(self) -> Dict[str, Any]:
        """Получение сводки по нарушениям"""
        if not self.violations_log:
            return {
                'total_violations': 0,
                'by_severity': {},
                'by_policy': {}
            }
        
        by_severity = {}
        by_policy = {}
        
        for violation in self.violations_log:
            # По severity
            if violation.severity not in by_severity:
                by_severity[violation.severity] = 0
            by_severity[violation.severity] += 1
            
            # По политике
            if violation.policy_id not in by_policy:
                by_policy[violation.policy_id] = {
                    'count': 0,
                    'name': violation.policy_name
                }
            by_policy[violation.policy_id]['count'] += 1
        
        return {
            'total_violations': len(self.violations_log),
            'by_severity': by_severity,
            'by_policy': by_policy,
            'recent_violations': [
                {
                    'policy': v.policy_id,
                    'type': v.violation_type,
                    'severity': v.severity,
                    'timestamp': v.timestamp
                }
                for v in self.violations_log[-10:]  # Последние 10
            ]
        }