"""
Интеграционные тесты для системы Эксплуатант
"""
import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from broker.kafka.kafka_system_bus import KafkaSystemBus
from systems.operator.src.operator_system import OperatorSystem
from systems.operator.src.security_monitor import SecurityMonitor
from systems.operator.src.fleet_manager import FleetManager
from systems.operator.src.mission_planner import MissionPlanner
from systems.operator.src.business_logic import BusinessLogic
from systems.operator.src.topics import (
    SystemTopics,
    ComponentTopics,
    OperatorActions
)


class TestOperatorSystemIntegration:
    """Интеграционные тесты системы Эксплуатант"""
    
    @pytest.fixture
    def mock_kafka_config(self):
        """Mock конфигурация для Kafka"""
        return {
            "bootstrap_servers": "localhost:9092",
            "group_id": "test-operator-system"
        }
    
    @pytest.fixture
    async def system_bus(self, mock_kafka_config):
        """Создание системной шины"""
        # Используем mock вместо реального Kafka для тестов
        bus = Mock(spec=KafkaSystemBus)
        bus.subscribe = MagicMock()
        bus.publish = MagicMock()
        bus.request = MagicMock()
        bus.start = MagicMock()
        bus.stop = MagicMock()
        return bus
    
    @pytest.fixture
    async def operator_components(self, system_bus):
        """Создание всех компонентов системы"""
        components = {
            "security_monitor": SecurityMonitor("security-01", system_bus),
            "fleet_manager": FleetManager("fleet-01", system_bus),
            "mission_planner": MissionPlanner("planner-01", system_bus),
            "business_logic": BusinessLogic("business-01", system_bus),
            "operator_system": OperatorSystem("operator-01", system_bus)
        }
        
        # Настраиваем mock для внутренних запросов
        def mock_request(topic, message, timeout=None):
            # Симулируем ответы от компонентов
            if topic == ComponentTopics.SECURITY_MONITOR:
                return {"success": True, "payload": {"allowed": True}}
            elif topic == ComponentTopics.FLEET_MANAGER:
                if message["action"] == "find_available_uas":
                    return {
                        "success": True,
                        "payload": {
                            "count": 1,
                            "suitable_uas": [{
                                "id": "UAS-001",
                                "type": "light_cargo",
                                "battery_level": 0.95
                            }]
                        }
                    }
                elif message["action"] == "reserve_uas":
                    return {
                        "success": True,
                        "payload": {
                            "reserved": True,
                            "uas_id": "UAS-001",
                            "expires_at": "2026-03-16T20:00:00Z"
                        }
                    }
            elif topic == ComponentTopics.MISSION_PLANNER:
                if message["action"] == "create_mission":
                    return {
                        "success": True,
                        "payload": {
                            "mission_id": "MISSION-TEST-001",
                            "status": "draft",
                            "waypoints_count": 4,
                            "distance": 10.5
                        }
                    }
                elif message["action"] == "validate_mission":
                    return {
                        "success": True,
                        "payload": {
                            "valid": True,
                            "validation_results": []
                        }
                    }
                elif message["action"] == "get_mission_details":
                    return {
                        "success": True,
                        "payload": {
                            "id": "MISSION-TEST-001",
                            "type": "cargo_delivery",
                            "status": "planned",
                            "distance": 10.5,
                            "payload_weight": 3.0,
                            "estimated_flight_time": 25.0
                        }
                    }
                elif message["action"] == "request_utm_approval":
                    return {
                        "success": True,
                        "payload": {
                            "approved": True,
                            "approval_id": "UTM-APPROVAL-001",
                            "valid_until": "2026-03-16T22:00:00Z"
                        }
                    }
            elif topic == ComponentTopics.BUSINESS_LOGIC:
                if message["action"] == "request_insurance_quote":
                    return {
                        "success": True,
                        "payload": {
                            "quote_id": "INS-001",
                            "premium": 150.0,
                            "rate": 2.5
                        }
                    }
                elif message["action"] == "create_proposal":
                    return {
                        "success": True,
                        "payload": {
                            "proposal_id": "PROP-001",
                            "price": 2500.0,
                            "margin_percent": 15.5,
                            "delivery_time": "2026-03-16T18:00:00Z"
                        }
                    }
            
            return {"success": False, "error": "Unknown request"}
        
        system_bus.request.side_effect = mock_request
        
        return components
    
    @pytest.mark.asyncio
    async def test_full_order_flow(self, operator_components, system_bus):
        """Тест полного цикла обработки заказа"""
        operator = operator_components["operator_system"]
        
        # 1. Получение заказа
        order_message = {
            "sender": "aggregator",
            "payload": {
                "order": {
                    "id": "ORDER-TEST-001",
                    "type": "cargo_delivery",
                    "start_location": {"lat": 55.7558, "lon": 37.6173},
                    "end_location": {"lat": 55.7600, "lon": 37.6200},
                    "payload_weight": 3.0,
                    "payload_value": 5000.0,
                    "start_time": "2026-03-16T17:00:00Z",
                    "end_time": "2026-03-16T19:00:00Z"
                }
            }
        }
        
        result = operator._handle_receive_order(order_message)
        
        assert "error" not in result
        assert result["order_id"] == "ORDER-TEST-001"
        assert result["status"] == "received"
        assert "proposal" in result
        assert result["proposal"]["proposal_id"] == "PROP-001"
        assert result["proposal"]["price"] == 2500.0
        
        # 2. Принятие заказа
        accept_message = {
            "payload": {
                "order_id": "ORDER-TEST-001"
            }
        }
        
        accept_result = operator._handle_accept_order(accept_message)
        
        assert accept_result["accepted"] is True
        assert accept_result["uas_id"] == "UAS-001"
        assert accept_result["utm_approval_id"] == "UTM-APPROVAL-001"
        
        # 3. Запуск миссии
        start_message = {
            "payload": {
                "mission_id": accept_result["mission_id"]
            }
        }
        
        start_result = operator._handle_start_mission(start_message)
        
        assert start_result["started"] is True
        
        # 4. Завершение миссии
        complete_message = {
            "payload": {
                "mission_id": accept_result["mission_id"],
                "success": True
            }
        }
        
        complete_result = operator._handle_complete_mission(complete_message)
        
        assert complete_result["completed"] is True
        assert complete_result["success"] is True
        
        # Проверяем статистику
        stats = operator.get_system_statistics()
        assert stats["system_stats"]["orders_received"] == 1
        assert stats["system_stats"]["orders_accepted"] == 1
        assert stats["system_stats"]["missions_completed"] == 1
    
    @pytest.mark.asyncio
    async def test_security_policy_enforcement(self, operator_components, system_bus):
        """Тест применения политик безопасности"""
        operator = operator_components["operator_system"]
        security_monitor = operator_components["security_monitor"]
        
        # Настраиваем security monitor для отклонения запроса
        def mock_security_request(topic, message, timeout=None):
            if topic == ComponentTopics.SECURITY_MONITOR:
                return {
                    "success": True,
                    "payload": {
                        "allowed": False,
                        "violations": [{
                            "policy_id": "P1",
                            "policy_name": "Authorized Operators Only",
                            "reason": "Unauthorized sender",
                            "severity": "critical"
                        }]
                    }
                }
            return {"success": False}
        
        system_bus.request.side_effect = mock_security_request
        
        # Попытка получить заказ от неавторизованного отправителя
        order_message = {
            "sender": "unknown_sender",
            "payload": {
                "order": {
                    "id": "ORDER-HACK-001",
                    "type": "cargo_delivery"
                }
            }
        }
        
        result = operator._handle_receive_order(order_message)
        
        assert "error" in result
        assert "Security check failed" in result["error"]
        assert len(result["violations"]) == 1
        assert result["violations"][0]["policy_id"] == "P1"
    
    @pytest.mark.asyncio
    async def test_no_suitable_uas_scenario(self, operator_components, system_bus):
        """Тест сценария отсутствия подходящих БАС"""
        operator = operator_components["operator_system"]
        
        # Настраиваем mock для возврата пустого списка БАС
        def mock_no_uas_request(topic, message, timeout=None):
            if topic == ComponentTopics.SECURITY_MONITOR:
                return {"success": True, "payload": {"allowed": True}}
            elif topic == ComponentTopics.FLEET_MANAGER:
                if message["action"] == "find_available_uas":
                    return {
                        "success": True,
                        "payload": {
                            "count": 0,
                            "suitable_uas": []
                        }
                    }
            elif topic == ComponentTopics.MISSION_PLANNER:
                if message["action"] == "create_mission":
                    return {
                        "success": True,
                        "payload": {
                            "mission_id": "MISSION-TEST-002",
                            "status": "draft",
                            "distance": 100.0  # Большая дистанция
                        }
                    }
                elif message["action"] == "validate_mission":
                    return {
                        "success": True,
                        "payload": {"valid": True}
                    }
                elif message["action"] == "get_mission_details":
                    return {
                        "success": True,
                        "payload": {
                            "distance": 100.0,
                            "payload_weight": 50.0  # Тяжёлый груз
                        }
                    }
            return {"success": False}
        
        system_bus.request.side_effect = mock_no_uas_request
        
        order_message = {
            "payload": {
                "order": {
                    "id": "ORDER-HEAVY-001",
                    "payload_weight": 50.0,
                    "distance": 100.0
                }
            }
        }
        
        result = operator._handle_receive_order(order_message)
        
        assert "error" in result
        assert "No suitable UAS available" in result["error"]
    
    @pytest.mark.asyncio
    async def test_utm_denial_scenario(self, operator_components, system_bus):
        """Тест сценария отказа ОрВД"""
        operator = operator_components["operator_system"]
        
        # Сначала создаём заказ
        order_message = {
            "payload": {
                "order": {
                    "id": "ORDER-UTM-001",
                    "type": "cargo_delivery"
                }
            }
        }
        
        operator._handle_receive_order(order_message)
        
        # Настраиваем mock для отказа UTM
        def mock_utm_denial(topic, message, timeout=None):
            if topic == ComponentTopics.MISSION_PLANNER:
                if message["action"] == "request_utm_approval":
                    return {
                        "success": True,
                        "payload": {
                            "approved": False,
                            "reason": "Airspace restricted",
                            "suggestions": ["Try different route", "Delay mission"]
                        }
                    }
            elif topic == ComponentTopics.FLEET_MANAGER:
                if message["action"] == "reserve_uas":
                    return {
                        "success": True,
                        "payload": {"reserved": True}
                    }
                elif message["action"] == "release_uas":
                    return {
                        "success": True,
                        "payload": {"released": True}
                    }
            return {"success": True, "payload": {}}
        
        system_bus.request.side_effect = mock_utm_denial
        
        # Пытаемся принять заказ
        accept_message = {
            "payload": {
                "order_id": "ORDER-UTM-001"
            }
        }
        
        result = operator._handle_accept_order(accept_message)
        
        assert "error" in result
        assert "UTM approval denied" in result["error"]
        assert result["details"]["reason"] == "Airspace restricted"
    
    @pytest.mark.asyncio
    async def test_component_communication(self, operator_components):
        """Тест взаимодействия между компонентами"""
        security_monitor = operator_components["security_monitor"]
        fleet_manager = operator_components["fleet_manager"]
        
        # Тест проверки потоков данных между компонентами
        assert security_monitor.validate_inter_component_flow(
            "fleet_manager", "business_logic", "calculate_cost"
        ) is True
        
        assert security_monitor.validate_inter_component_flow(
            "business_logic", "security_monitor", "modify_policy"
        ) is False
    
    @pytest.mark.asyncio
    async def test_incident_reporting(self, operator_components, system_bus):
        """Тест отчёта об инцидентах"""
        operator = operator_components["operator_system"]
        
        incident_message = {
            "sender": "uas_controller",
            "payload": {
                "incident": {
                    "type": "emergency_landing",
                    "description": "Battery critical, emergency landing performed",
                    "severity": "high",
                    "location": {"lat": 55.76, "lon": 37.62},
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        }
        
        result = operator._handle_report_incident(incident_message)
        
        assert result["reported"] is True
        assert "incident_id" in result