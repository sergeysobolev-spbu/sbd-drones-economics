"""
Юнит-тесты для монитора безопасности
"""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from systems.operator.src.security_monitor import (
    SecurityMonitor,
    PolicyResult,
    PolicyViolation,
    SecurityPolicy
)
from systems.operator.src.topics import SecurityMonitorActions


class TestSecurityMonitor:
    """Тесты для монитора безопасности"""
    
    @pytest.fixture
    def mock_bus(self):
        """Mock для SystemBus"""
        bus = Mock()
        bus.request = MagicMock()
        bus.publish = MagicMock()
        return bus
    
    @pytest.fixture
    def security_monitor(self, mock_bus):
        """Создание экземпляра SecurityMonitor"""
        return SecurityMonitor("test-monitor", mock_bus)
    
    def test_initialization(self, security_monitor):
        """Тест инициализации"""
        assert security_monitor.component_id == "test-monitor"
        assert security_monitor.component_type == "security_monitor"
        assert len(security_monitor.policies) == 5  # P1-P5
        assert len(security_monitor.violations) == 0
        assert security_monitor.stats["total_requests"] == 0
    
    def test_policy_initialization(self, security_monitor):
        """Тест инициализации политик"""
        # Проверяем политику P1
        p1 = security_monitor.policies.get("P1")
        assert p1 is not None
        assert p1.name == "Authorized Operators Only"
        assert p1.severity == "critical"
        assert len(p1.rules) == 3
        
        # Проверяем политику P3
        p3 = security_monitor.policies.get("P3")
        assert p3 is not None
        assert p3.name == "Profitability Check"
        assert p3.severity == "medium"
    
    def test_validate_request_allowed(self, security_monitor):
        """Тест успешной валидации запроса"""
        message = {
            "payload": {
                "request": {
                    "action": "test_action",
                    "sender": {"role": "operator", "authenticated": True}
                },
                "context": {}
            }
        }
        
        result = security_monitor._handle_validate_request(message)
        
        assert result["allowed"] is True
        assert "message" in result
        assert security_monitor.stats["total_requests"] == 1
        assert security_monitor.stats["allowed_requests"] == 1
        assert security_monitor.stats["denied_requests"] == 0
    
    def test_validate_request_denied(self, security_monitor):
        """Тест отклонения запроса"""
        message = {
            "payload": {
                "request": {
                    "action": "test_action",
                    "sender": {"role": "guest", "authenticated": False}
                },
                "context": {}
            }
        }
        
        result = security_monitor._handle_validate_request(message)
        
        assert result["allowed"] is False
        assert "violations" in result
        assert len(result["violations"]) > 0
        assert security_monitor.stats["total_requests"] == 1
        assert security_monitor.stats["allowed_requests"] == 0
        assert security_monitor.stats["denied_requests"] == 1
    
    def test_check_policy_p1_authorized(self, security_monitor):
        """Тест проверки политики P1 - авторизованный оператор"""
        request = {
            "sender": {"role": "operator", "authenticated": True}
        }
        
        result, reason = security_monitor._check_policy("P1", request, {})
        
        assert result == PolicyResult.ALLOW
        assert reason == "Authorized operator"
    
    def test_check_policy_p1_unauthorized(self, security_monitor):
        """Тест проверки политики P1 - неавторизованный пользователь"""
        request = {
            "sender": {"role": "guest", "authenticated": False}
        }
        
        result, reason = security_monitor._check_policy("P1", request, {})
        
        assert result == PolicyResult.DENY
        assert reason == "Not an authorized operator"
    
    def test_check_policy_p1_internal_component(self, security_monitor):
        """Тест проверки политики P1 - внутренний компонент"""
        request = {
            "sender": "operator.fleet_manager"
        }
        
        result, reason = security_monitor._check_policy("P1", request, {})
        
        assert result == PolicyResult.ALLOW
        assert reason == "Internal component"
    
    def test_check_policy_p3_profitable(self, security_monitor):
        """Тест проверки политики P3 - достаточная маржа"""
        request = {}
        context = {
            "order": {
                "price": 1000,
                "cost": 800
            }
        }
        
        result, reason = security_monitor._check_policy("P3", request, context)
        
        assert result == PolicyResult.ALLOW
        assert reason == "Profitability check passed"
    
    def test_check_policy_p3_unprofitable(self, security_monitor):
        """Тест проверки политики P3 - недостаточная маржа"""
        request = {}
        context = {
            "order": {
                "price": 1000,
                "cost": 950
            }
        }
        
        result, reason = security_monitor._check_policy("P3", request, context)
        
        assert result == PolicyResult.DENY
        assert reason == "Insufficient margin"
    
    def test_check_policy_p4_valid_certificate(self, security_monitor):
        """Тест проверки политики P4 - действующий сертификат"""
        request = {}
        context = {
            "uas": {
                "id": "UAS-001"
            }
        }
        
        # Добавляем сертификат в кеш
        security_monitor.certificate_cache["UAS-001"] = {
            "status": "valid",
            "expiry": "2027-01-01"
        }
        
        result, reason = security_monitor._check_policy("P4", request, context)
        
        assert result == PolicyResult.ALLOW
        assert reason == "Valid certificate (cached)"
    
    def test_check_policy_p4_invalid_certificate(self, security_monitor):
        """Тест проверки политики P4 - недействительный сертификат"""
        request = {}
        context = {
            "uas": {
                "id": "UAS-002"
            }
        }
        
        # Добавляем недействительный сертификат в кеш
        security_monitor.certificate_cache["UAS-002"] = {
            "status": "expired",
            "expiry": "2025-01-01"
        }
        
        result, reason = security_monitor._check_policy("P4", request, context)
        
        assert result == PolicyResult.DENY
        assert reason == "Invalid certificate"
    
    def test_get_applicable_policies(self, security_monitor):
        """Тест определения применимых политик"""
        # Базовый запрос
        request = {"action": "test"}
        policies = security_monitor._get_applicable_policies(request, {})
        assert "P1" in policies
        assert "P5" in policies
        
        # Запрос связанный с миссией
        request = {"action": "start_mission"}
        policies = security_monitor._get_applicable_policies(request, {})
        assert "P2" in policies
        assert "P4" in policies
        
        # Запрос связанный с заказом
        request = {"action": "accept_order"}
        policies = security_monitor._get_applicable_policies(request, {})
        assert "P3" in policies
    
    def test_log_violation(self, security_monitor):
        """Тест логирования нарушения"""
        violation = PolicyViolation(
            policy_id="P1",
            policy_name="Test Policy",
            timestamp=datetime.utcnow().isoformat(),
            sender="test_sender",
            action="test_action",
            reason="Test reason",
            severity="high"
        )
        
        security_monitor._log_violation(violation)
        
        assert len(security_monitor.violations) == 1
        assert security_monitor.stats["violations"] == 1
        assert security_monitor.violations[0] == violation
    
    def test_handle_log_violation(self, security_monitor):
        """Тест обработчика логирования нарушения"""
        message = {
            "payload": {
                "policy_id": "P1",
                "policy_name": "Test Policy",
                "sender": "test_sender",
                "action": "test_action",
                "reason": "Test reason",
                "severity": "medium"
            }
        }
        
        result = security_monitor._handle_log_violation(message)
        
        assert result["logged"] is True
        assert "violation_id" in result
        assert len(security_monitor.violations) == 1
    
    def test_get_security_status(self, security_monitor):
        """Тест получения статуса безопасности"""
        # Добавляем некоторые данные
        security_monitor.stats["total_requests"] = 10
        security_monitor.stats["allowed_requests"] = 8
        security_monitor.stats["denied_requests"] = 2
        
        message = {}
        result = security_monitor._handle_get_security_status(message)
        
        assert result["stats"]["total_requests"] == 10
        assert result["stats"]["allowed_requests"] == 8
        assert result["stats"]["denied_requests"] == 2
        assert result["active_policies"] == 5
        assert "recent_violations" in result
        assert result["certificate_cache_size"] == 0
    
    def test_validate_inter_component_flow_allowed(self, security_monitor):
        """Тест проверки разрешённых потоков между компонентами"""
        # D0 -> D1 (разрешено)
        assert security_monitor.validate_inter_component_flow(
            "security_monitor", "fleet_manager", "get_status"
        ) is True
        
        # D1 -> D2 (разрешено)
        assert security_monitor.validate_inter_component_flow(
            "fleet_manager", "business_logic", "calculate_cost"
        ) is True
        
        # D2 -> D3 (разрешено)
        assert security_monitor.validate_inter_component_flow(
            "business_logic", "api_gateway", "send_response"
        ) is True
    
    def test_validate_inter_component_flow_denied(self, security_monitor):
        """Тест проверки запрещённых потоков между компонентами"""
        # D3 -> D1 (запрещено)
        assert security_monitor.validate_inter_component_flow(
            "api_gateway", "fleet_manager", "direct_command"
        ) is False
        
        # D2 -> D0 (запрещено)
        assert security_monitor.validate_inter_component_flow(
            "business_logic", "security_monitor", "modify_policy"
        ) is False
    
    def test_validate_inter_component_flow_response(self, security_monitor):
        """Тест проверки ответных потоков"""
        # Ответ всегда разрешён
        assert security_monitor.validate_inter_component_flow(
            "api_gateway", "security_monitor", "validate_response"
        ) is True
        
        assert security_monitor.validate_inter_component_flow(
            "business_logic", "fleet_manager", "reply"
        ) is True