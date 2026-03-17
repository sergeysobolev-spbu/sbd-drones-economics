"""
Unit тесты для SecurityMonitorCore
"""
import pytest
from unittest.mock import Mock, patch
import time

from systems.operator.src.security_monitor.src.security_monitor_core import (
    SecurityMonitorCore, SecurityContext, PolicyResult, PolicyViolation
)


class TestSecurityMonitorCore:
    """Тесты для ядра монитора безопасности"""
    
    @pytest.fixture
    def core(self):
        """Создание экземпляра SecurityMonitorCore"""
        return SecurityMonitorCore()
    
    @pytest.fixture
    def valid_context(self):
        """Валидный контекст безопасности"""
        return SecurityContext(
            sender_id="operator-001",
            sender_role="operator",
            action="get_fleet_status",
            target_component="fleet_manager",
            payload_hash="abc123",
            timestamp=time.time(),
            trace_id="trace-123"
        )
    
    def test_init(self, core):
        """Тест инициализации"""
        assert core.policies is not None
        assert len(core.policies) > 0
        assert core.violations_log == []
        assert "fleet_manager" in core.trusted_components
    
    def test_load_security_policies(self, core):
        """Тест загрузки политик безопасности"""
        policies = core._load_security_policies()
        
        # Проверяем наличие всех политик
        assert "P1" in policies
        assert "P2" in policies
        assert "P3" in policies
        assert "P4" in policies
        
        # Проверяем структуру политик
        assert policies["P1"]["name"] == "Контроль источника команд"
        assert "critical_actions" in policies["P2"]
        assert "rate_limits" in policies["P4"]
    
    def test_validate_request_allowed(self, core, valid_context):
        """Тест успешной валидации запроса"""
        result, violation = core.validate_request(valid_context)
        
        assert result == PolicyResult.ALLOW
        assert violation is None
    
    def test_validate_request_unauthorized_sender(self, core):
        """Тест отклонения неавторизованного отправителя"""
        context = SecurityContext(
            sender_id="unknown-001",
            sender_role="unknown",
            action="start_mission",
            target_component="mission_planner",
            payload_hash="xyz789",
            timestamp=time.time()
        )
        
        result, violation = core.validate_request(context)
        
        assert result == PolicyResult.DENY
        assert violation is not None
        assert violation.policy_id == "P1"
        assert violation.violation_type == "unauthorized_sender"
    
    def test_validate_request_critical_action_denied(self, core):
        """Тест отклонения критического действия для не-админа"""
        context = SecurityContext(
            sender_id="operator-001",
            sender_role="operator",
            action="emergency_landing",  # Критическое действие
            target_component="mission_planner",
            payload_hash="def456",
            timestamp=time.time()
        )
        
        result, violation = core.validate_request(context)
        
        assert result == PolicyResult.DENY
        assert violation is not None
        assert violation.policy_id == "P2"
        assert violation.violation_type == "critical_action_denied"
    
    def test_validate_request_critical_action_allowed_for_admin(self, core):
        """Тест разрешения критического действия для админа"""
        context = SecurityContext(
            sender_id="admin-001",
            sender_role="admin",
            action="emergency_landing",
            target_component="mission_planner",
            payload_hash="ghi789",
            timestamp=time.time()
        )
        
        result, violation = core.validate_request(context)
        
        assert result == PolicyResult.ALLOW
        assert violation is None
    
    def test_validate_request_untrusted_component(self, core):
        """Тест взаимодействия с недоверенным компонентом"""
        context = SecurityContext(
            sender_id="operator-001",
            sender_role="operator",
            action="get_status",
            target_component="unknown_component",
            payload_hash="jkl012",
            timestamp=time.time()
        )
        
        result, violation = core.validate_request(context)
        
        assert result == PolicyResult.AUDIT  # Разрешаем, но логируем
        assert violation is not None
        assert violation.policy_id == "P3"
        assert violation.violation_type == "untrusted_component"
    
    def test_check_sender_authorization(self, core):
        """Тест проверки авторизации отправителя"""
        valid_context = SecurityContext(
            sender_id="op-001",
            sender_role="operator",
            action="test",
            target_component="test",
            payload_hash="test",
            timestamp=time.time()
        )
        
        invalid_context = SecurityContext(
            sender_id="guest-001",
            sender_role="guest",
            action="test",
            target_component="test",
            payload_hash="test",
            timestamp=time.time()
        )
        
        assert core._check_sender_authorization(valid_context) is True
        assert core._check_sender_authorization(invalid_context) is False
    
    def test_is_critical_action(self, core):
        """Тест определения критических действий"""
        assert core._is_critical_action("start_mission") is True
        assert core._is_critical_action("abort_mission") is True
        assert core._is_critical_action("get_status") is False
        assert core._is_critical_action("list_uas") is False
    
    def test_check_rate_limit_within_limit(self, core):
        """Тест проверки rate limit - в пределах лимита"""
        current_time = time.time()
        request_history = [current_time - 30, current_time - 20, current_time - 10]
        
        allowed, msg = core.check_rate_limit("sender-001", "get_status", request_history)
        
        assert allowed is True
        assert msg is None
    
    def test_check_rate_limit_exceeded(self, core):
        """Тест проверки rate limit - превышен лимит"""
        current_time = time.time()
        # 101 запрос за последнюю минуту
        request_history = [current_time - i for i in range(101)]
        
        allowed, msg = core.check_rate_limit("sender-001", "get_status", request_history)
        
        assert allowed is False
        assert "Rate limit exceeded" in msg
        assert "101/100" in msg
    
    def test_check_rate_limit_critical_action(self, core):
        """Тест проверки rate limit для критических действий"""
        current_time = time.time()
        # 11 запросов за последнюю минуту
        request_history = [current_time - i*5 for i in range(11)]
        
        allowed, msg = core.check_rate_limit("sender-001", "start_mission", request_history)
        
        assert allowed is False
        assert "11/10" in msg
    
    def test_calculate_payload_hash(self, core):
        """Тест вычисления хеша полезной нагрузки"""
        payload1 = {"action": "test", "data": "value"}
        payload2 = {"data": "value", "action": "test"}  # Другой порядок
        payload3 = {"action": "test", "data": "other"}
        
        hash1 = core.calculate_payload_hash(payload1)
        hash2 = core.calculate_payload_hash(payload2)
        hash3 = core.calculate_payload_hash(payload3)
        
        # Хеши должны быть одинаковыми для одинаковых данных
        assert hash1 == hash2
        # Хеши должны отличаться для разных данных
        assert hash1 != hash3
        # Хеш должен быть строкой определенной длины
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA256
    
    def test_log_violation(self, core):
        """Тест логирования нарушений"""
        violation = PolicyViolation(
            policy_id="P1",
            policy_name="Test Policy",
            violation_type="test_violation",
            details="Test details",
            severity="high",
            timestamp=time.time()
        )
        
        initial_count = len(core.violations_log)
        core._log_violation(violation)
        
        assert len(core.violations_log) == initial_count + 1
        assert core.violations_log[-1] == violation
    
    def test_get_violations_summary_empty(self, core):
        """Тест получения сводки по нарушениям - пустой лог"""
        summary = core.get_violations_summary()
        
        assert summary["total_violations"] == 0
        assert summary["by_severity"] == {}
        assert summary["by_policy"] == {}
    
    def test_get_violations_summary_with_violations(self, core):
        """Тест получения сводки по нарушениям - с нарушениями"""
        # Добавляем несколько нарушений
        violations = [
            PolicyViolation("P1", "Policy 1", "type1", "details1", "high", time.time()),
            PolicyViolation("P1", "Policy 1", "type1", "details2", "high", time.time()),
            PolicyViolation("P2", "Policy 2", "type2", "details3", "critical", time.time()),
            PolicyViolation("P3", "Policy 3", "type3", "details4", "medium", time.time()),
        ]
        
        for v in violations:
            core._log_violation(v)
        
        summary = core.get_violations_summary()
        
        assert summary["total_violations"] == 4
        assert summary["by_severity"]["high"] == 2
        assert summary["by_severity"]["critical"] == 1
        assert summary["by_severity"]["medium"] == 1
        assert summary["by_policy"]["P1"]["count"] == 2
        assert summary["by_policy"]["P2"]["count"] == 1
        assert len(summary["recent_violations"]) == 4
    
    def test_validate_critical_action_admin_only(self, core):
        """Тест валидации критических действий - только для админов"""
        admin_context = SecurityContext(
            sender_id="admin-001",
            sender_role="admin",
            action="test",
            target_component="test",
            payload_hash="test",
            timestamp=time.time()
        )
        
        operator_context = SecurityContext(
            sender_id="op-001",
            sender_role="operator",
            action="test",
            target_component="test",
            payload_hash="test",
            timestamp=time.time()
        )
        
        assert core._validate_critical_action(admin_context) is True
        assert core._validate_critical_action(operator_context) is False