"""
Юнит-тесты для менеджера парка БАС
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

from systems.operator.src.fleet_manager import (
    FleetManager,
    UASStatus,
    UASType,
    UAS
)
from systems.operator.src.topics import FleetManagerActions


class TestFleetManager:
    """Тесты для менеджера парка"""
    
    @pytest.fixture
    def mock_bus(self):
        """Mock для SystemBus"""
        bus = Mock()
        bus.request = MagicMock()
        bus.publish = MagicMock()
        return bus
    
    @pytest.fixture
    def fleet_manager(self, mock_bus):
        """Создание экземпляра FleetManager"""
        return FleetManager("test-fleet", mock_bus)
    
    def test_initialization(self, fleet_manager):
        """Тест инициализации"""
        assert fleet_manager.component_id == "test-fleet"
        assert fleet_manager.component_type == "fleet_manager"
        assert len(fleet_manager.fleet) == 4  # 4 БАС в парке
        assert len(fleet_manager.reservations) == 0
    
    def test_fleet_initialization(self, fleet_manager):
        """Тест инициализации парка БАС"""
        # Проверяем UAS-001
        uas1 = fleet_manager.fleet.get("UAS-001")
        assert uas1 is not None
        assert uas1.type == UASType.LIGHT_CARGO
        assert uas1.status == UASStatus.AVAILABLE
        assert uas1.max_payload == 5.0
        assert uas1.battery_level == 0.95
        
        # Проверяем UAS-003 (в обслуживании)
        uas3 = fleet_manager.fleet.get("UAS-003")
        assert uas3 is not None
        assert uas3.status == UASStatus.MAINTENANCE
        assert uas3.type == UASType.AGRO
    
    def test_get_uas_list(self, fleet_manager):
        """Тест получения списка БАС"""
        message = {}
        result = fleet_manager._handle_get_uas_list(message)
        
        assert "uas_list" in result
        assert result["total"] == 4
        assert result["available"] == 3  # UAS-003 в обслуживании
        
        # Проверяем формат данных
        uas_list = result["uas_list"]
        assert len(uas_list) == 4
        assert all("id" in uas for uas in uas_list)
        assert all("type" in uas for uas in uas_list)
        assert all("status" in uas for uas in uas_list)
    
    def test_get_uas_status_success(self, fleet_manager):
        """Тест получения статуса конкретного БАС"""
        message = {
            "payload": {"uas_id": "UAS-001"}
        }
        
        result = fleet_manager._handle_get_uas_status(message)
        
        assert result["id"] == "UAS-001"
        assert result["type"] == "light_cargo"
        assert result["status"] == "available"
        assert result["ready_for_flight"] is True
    
    def test_get_uas_status_not_found(self, fleet_manager):
        """Тест получения статуса несуществующего БАС"""
        message = {
            "payload": {"uas_id": "UAS-999"}
        }
        
        result = fleet_manager._handle_get_uas_status(message)
        
        assert "error" in result
        assert "not found" in result["error"]
    
    def test_find_available_uas_success(self, fleet_manager, mock_bus):
        """Тест поиска подходящих БАС"""
        # Настраиваем mock для security monitor
        mock_bus.request.return_value = {
            "success": True,
            "payload": {"allowed": True}
        }
        
        message = {
            "payload": {
                "requirements": {
                    "type": "light_cargo",
                    "min_payload": 3.0,
                    "min_range": 40.0,
                    "min_battery": 0.8
                }
            }
        }
        
        result = fleet_manager._handle_find_available_uas(message)
        
        assert "suitable_uas" in result
        assert result["count"] == 1  # Только UAS-001 подходит
        assert result["suitable_uas"][0]["id"] == "UAS-001"
    
    def test_find_available_uas_no_matches(self, fleet_manager, mock_bus):
        """Тест поиска БАС без подходящих"""
        mock_bus.request.return_value = {
            "success": True,
            "payload": {"allowed": True}
        }
        
        message = {
            "payload": {
                "requirements": {
                    "min_payload": 100.0  # Слишком большой груз
                }
            }
        }
        
        result = fleet_manager._handle_find_available_uas(message)
        
        assert result["count"] == 0
        assert len(result["suitable_uas"]) == 0
    
    def test_find_available_uas_security_denied(self, fleet_manager, mock_bus):
        """Тест поиска БАС с отказом от security monitor"""
        mock_bus.request.return_value = {
            "success": True,
            "payload": {
                "allowed": False,
                "violations": [{"policy": "P1", "reason": "Unauthorized"}]
            }
        }
        
        message = {
            "payload": {"requirements": {}}
        }
        
        result = fleet_manager._handle_find_available_uas(message)
        
        assert "error" in result
        assert "Security check failed" in result["error"]
        assert "violations" in result
    
    def test_reserve_uas_success(self, fleet_manager, mock_bus):
        """Тест успешного резервирования БАС"""
        mock_bus.request.return_value = {
            "success": True,
            "payload": {"allowed": True}
        }
        
        message = {
            "payload": {
                "uas_id": "UAS-001",
                "mission_id": "MISSION-123",
                "duration": 3600
            }
        }
        
        result = fleet_manager._handle_reserve_uas(message)
        
        assert result["reserved"] is True
        assert result["uas_id"] == "UAS-001"
        assert result["mission_id"] == "MISSION-123"
        assert "expires_at" in result
        
        # Проверяем изменение статуса
        uas = fleet_manager.fleet["UAS-001"]
        assert uas.status == UASStatus.RESERVED
        assert uas.reserved_by == "MISSION-123"
        
        # Проверяем резервирование
        assert "UAS-001" in fleet_manager.reservations
    
    def test_reserve_uas_not_available(self, fleet_manager, mock_bus):
        """Тест резервирования недоступного БАС"""
        # Сначала резервируем БАС
        fleet_manager.fleet["UAS-001"].status = UASStatus.IN_MISSION
        
        message = {
            "payload": {
                "uas_id": "UAS-001",
                "mission_id": "MISSION-456"
            }
        }
        
        result = fleet_manager._handle_reserve_uas(message)
        
        assert "error" in result
        assert "not available" in result["error"]
    
    def test_release_uas_success(self, fleet_manager):
        """Тест освобождения БАС"""
        # Сначала резервируем БАС
        uas = fleet_manager.fleet["UAS-001"]
        uas.status = UASStatus.RESERVED
        uas.reserved_by = "MISSION-123"
        fleet_manager.reservations["UAS-001"] = {
            "mission_id": "MISSION-123",
            "reserved_at": datetime.utcnow().isoformat()
        }
        
        message = {
            "payload": {"uas_id": "UAS-001"}
        }
        
        result = fleet_manager._handle_release_uas(message)
        
        assert result["released"] is True
        assert result["uas_id"] == "UAS-001"
        assert result["previous_status"] == "reserved"
        
        # Проверяем изменение статуса
        assert uas.status == UASStatus.AVAILABLE
        assert uas.reserved_by is None
        assert "UAS-001" not in fleet_manager.reservations
    
    def test_update_uas_status_success(self, fleet_manager):
        """Тест обновления статуса БАС"""
        message = {
            "payload": {
                "uas_id": "UAS-001",
                "updates": {
                    "status": "in_mission",
                    "battery_level": 0.75,
                    "location": {"lat": 55.8, "lon": 37.7, "alt": 100},
                    "current_mission": "MISSION-123"
                }
            }
        }
        
        result = fleet_manager._handle_update_uas_status(message)
        
        assert result["updated"] is True
        
        # Проверяем обновления
        uas = fleet_manager.fleet["UAS-001"]
        assert uas.status == UASStatus.IN_MISSION
        assert uas.battery_level == 0.75
        assert uas.location["lat"] == 55.8
        assert uas.current_mission == "MISSION-123"
    
    def test_update_uas_status_invalid_field(self, fleet_manager):
        """Тест обновления с недопустимым полем"""
        message = {
            "payload": {
                "uas_id": "UAS-001",
                "updates": {
                    "certificate_status": "invalid"  # Не разрешено
                }
            }
        }
        
        result = fleet_manager._handle_update_uas_status(message)
        
        assert result["updated"] is True
        # Поле не должно измениться
        assert fleet_manager.fleet["UAS-001"].certificate_status == "valid"
    
    def test_check_flight_readiness_ready(self, fleet_manager):
        """Тест проверки готовности к полёту - готов"""
        uas = fleet_manager.fleet["UAS-001"]
        assert fleet_manager._check_flight_readiness(uas) is True
    
    def test_check_flight_readiness_low_battery(self, fleet_manager):
        """Тест проверки готовности к полёту - низкий заряд"""
        uas = fleet_manager.fleet["UAS-001"]
        uas.battery_level = 0.25
        assert fleet_manager._check_flight_readiness(uas) is False
    
    def test_check_flight_readiness_maintenance(self, fleet_manager):
        """Тест проверки готовности к полёту - в обслуживании"""
        uas = fleet_manager.fleet["UAS-003"]
        assert fleet_manager._check_flight_readiness(uas) is False
    
    def test_check_flight_readiness_expired_certificate(self, fleet_manager):
        """Тест проверки готовности к полёту - истёкший сертификат"""
        uas = fleet_manager.fleet["UAS-001"]
        uas.certificate_expiry = "2020-01-01T00:00:00Z"
        assert fleet_manager._check_flight_readiness(uas) is False
    
    def test_check_flight_readiness_needs_maintenance(self, fleet_manager):
        """Тест проверки готовности к полёту - требуется обслуживание"""
        uas = fleet_manager.fleet["UAS-001"]
        uas.flight_hours = 149.5  # Близко к 150 (кратно 50)
        assert fleet_manager._check_flight_readiness(uas) is False
    
    def test_get_fleet_statistics(self, fleet_manager):
        """Тест получения статистики парка"""
        stats = fleet_manager.get_fleet_statistics()
        
        assert stats["total"] == 4
        assert stats["by_status"]["available"] == 3
        assert stats["by_status"]["maintenance"] == 1
        assert stats["by_type"]["light_cargo"] == 1
        assert stats["by_type"]["heavy_cargo"] == 1
        assert stats["by_type"]["agro"] == 1
        assert stats["by_type"]["inspector"] == 1
        assert stats["average_battery"] > 0
        assert "certificates_expiring_soon" in stats
    
    def test_validate_with_security_monitor_success(self, fleet_manager, mock_bus):
        """Тест успешной валидации через security monitor"""
        mock_bus.request.return_value = {
            "success": True,
            "payload": {"allowed": True}
        }
        
        result = fleet_manager._validate_with_security_monitor(
            {"action": "test"},
            {"context": "test"}
        )
        
        assert result["allowed"] is True
        mock_bus.request.assert_called_once()
    
    def test_validate_with_security_monitor_timeout(self, fleet_manager, mock_bus):
        """Тест таймаута при валидации"""
        mock_bus.request.side_effect = Exception("Timeout")
        
        result = fleet_manager._validate_with_security_monitor(
            {"action": "test"},
            {}
        )
        
        assert result["allowed"] is False
        assert "error" in result