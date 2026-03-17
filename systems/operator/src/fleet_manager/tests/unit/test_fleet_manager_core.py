"""
Unit tests for FleetManagerCore - доверенный домен
"""
import pytest
from datetime import datetime, timedelta

from systems.operator.src.fleet_manager.src.fleet_manager_core import (
    FleetManagerCore, UASStatus, UASState
)


class TestFleetManagerCore:
    """Тесты для ядра менеджера парка"""
    
    @pytest.fixture
    def core(self):
        """Создание экземпляра ядра"""
        return FleetManagerCore()
    
    @pytest.fixture
    def sample_uas_state(self):
        """Пример состояния БАС"""
        return {
            "certificate_valid": True,
            "certificate_expiry": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "battery_level": 0.8
        }
    
    def test_add_uas_success(self, core, sample_uas_state):
        """Тест успешного добавления БАС"""
        success, reason = core.add_uas("UAS-001", sample_uas_state)
        
        assert success is True
        assert reason == "OK"
        assert "UAS-001" in core._fleet_state
    
    def test_add_uas_duplicate(self, core, sample_uas_state):
        """Тест добавления дубликата БАС"""
        core.add_uas("UAS-001", sample_uas_state)
        success, reason = core.add_uas("UAS-001", sample_uas_state)
        
        assert success is False
        assert reason == "UAS_ALREADY_EXISTS"
    
    def test_authorize_uas_operation_not_found(self, core):
        """Тест авторизации операции для несуществующего БАС"""
        authorized, reason = core.authorize_uas_operation(
            "UAS-999", "reserve", "operator_01"
        )
        
        assert authorized is False
        assert reason == "UAS_NOT_FOUND"
    
    def test_authorize_uas_operation_invalid_certificate(self, core):
        """Тест авторизации с недействительным сертификатом"""
        core.add_uas("UAS-001", {
            "certificate_valid": False,
            "certificate_expiry": "2027-01-01",
            "battery_level": 1.0
        })
        
        authorized, reason = core.authorize_uas_operation(
            "UAS-001", "reserve", "operator_01"
        )
        
        assert authorized is False
        assert reason == "CERTIFICATE_INVALID"
    
    def test_authorize_uas_operation_expired_certificate(self, core):
        """Тест авторизации с истекшим сертификатом"""
        core.add_uas("UAS-001", {
            "certificate_valid": True,
            "certificate_expiry": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "battery_level": 1.0
        })
        
        authorized, reason = core.authorize_uas_operation(
            "UAS-001", "reserve", "operator_01"
        )
        
        assert authorized is False
        assert reason == "CERTIFICATE_EXPIRED"
    
    def test_authorize_reserve_operation_success(self, core, sample_uas_state):
        """Тест успешной авторизации резервирования"""
        core.add_uas("UAS-001", sample_uas_state)
        
        authorized, reason = core.authorize_uas_operation(
            "UAS-001", "reserve", "operator_01"
        )
        
        assert authorized is True
        assert reason == "OK"
    
    def test_authorize_reserve_operation_not_available(self, core, sample_uas_state):
        """Тест авторизации резервирования недоступного БАС"""
        core.add_uas("UAS-001", sample_uas_state)
        core._fleet_state["UAS-001"].status = UASStatus.IN_MISSION
        
        authorized, reason = core.authorize_uas_operation(
            "UAS-001", "reserve", "operator_01"
        )
        
        assert authorized is False
        assert reason == "UAS_NOT_AVAILABLE"
    
    def test_authorize_mission_operation_low_battery(self, core):
        """Тест авторизации миссии с низким зарядом"""
        core.add_uas("UAS-001", {
            "certificate_valid": True,
            "certificate_expiry": "2027-01-01",
            "battery_level": 0.2
        })
        core._fleet_state["UAS-001"].status = UASStatus.RESERVED
        
        authorized, reason = core.authorize_uas_operation(
            "UAS-001", "mission", "operator_01"
        )
        
        assert authorized is False
        assert reason == "BATTERY_TOO_LOW"
    
    def test_reserve_uas_success(self, core, sample_uas_state):
        """Тест успешного резервирования БАС"""
        core.add_uas("UAS-001", sample_uas_state)
        
        success, reason = core.reserve_uas("UAS-001", "MISSION-123", "operator_01")
        
        assert success is True
        assert reason == "OK"
        assert core._fleet_state["UAS-001"].status == UASStatus.RESERVED
        assert core._fleet_state["UAS-001"].reserved_by == "MISSION-123"
    
    def test_reserve_uas_race_condition(self, core, sample_uas_state):
        """Тест защиты от race condition при резервировании"""
        core.add_uas("UAS-001", sample_uas_state)
        core._fleet_state["UAS-001"].status = UASStatus.RESERVED
        
        success, reason = core.reserve_uas("UAS-001", "MISSION-456", "operator_02")
        
        assert success is False
        assert reason == "RACE_CONDITION_UAS_ALREADY_RESERVED"
    
    def test_release_uas_success(self, core, sample_uas_state):
        """Тест успешного освобождения БАС"""
        core.add_uas("UAS-001", sample_uas_state)
        core.reserve_uas("UAS-001", "MISSION-123", "operator_01")
        
        success, reason = core.release_uas("UAS-001", "operator_01")
        
        assert success is True
        assert reason == "OK"
        assert core._fleet_state["UAS-001"].status == UASStatus.AVAILABLE
        assert core._fleet_state["UAS-001"].reserved_by is None
    
    def test_release_uas_unauthorized(self, core, sample_uas_state):
        """Тест неавторизованного освобождения БАС"""
        core.add_uas("UAS-001", sample_uas_state)
        core._fleet_state["UAS-001"].reserved_by = "operator_01"
        
        success, reason = core.release_uas("UAS-001", "operator_02")
        
        assert success is False
        assert reason == "NOT_AUTHORIZED_TO_RELEASE"
    
    def test_update_uas_state_success(self, core, sample_uas_state):
        """Тест успешного обновления состояния БАС"""
        core.add_uas("UAS-001", sample_uas_state)
        
        updates = {
            "status": "maintenance",
            "battery_level": 0.5,
            "certificate_valid": False
        }
        
        success, reason = core.update_uas_state("UAS-001", updates)
        
        assert success is True
        assert reason == "OK"
        assert core._fleet_state["UAS-001"].status == UASStatus.MAINTENANCE
        assert core._fleet_state["UAS-001"].battery_level == 0.5
        assert core._fleet_state["UAS-001"].certificate_valid is False
    
    def test_update_uas_state_invalid_status(self, core, sample_uas_state):
        """Тест обновления с недопустимым статусом"""
        core.add_uas("UAS-001", sample_uas_state)
        
        success, reason = core.update_uas_state("UAS-001", {"status": "invalid"})
        
        assert success is False
        assert reason == "INVALID_STATUS"
    
    def test_update_uas_state_invalid_battery(self, core, sample_uas_state):
        """Тест обновления с недопустимым уровнем батареи"""
        core.add_uas("UAS-001", sample_uas_state)
        
        success, reason = core.update_uas_state("UAS-001", {"battery_level": 1.5})
        
        assert success is False
        assert reason == "INVALID_BATTERY_LEVEL"
    
    def test_get_uas_state_success(self, core, sample_uas_state):
        """Тест получения состояния БАС"""
        core.add_uas("UAS-001", sample_uas_state)
        
        state = core.get_uas_state("UAS-001")
        
        assert state is not None
        assert state["id"] == "UAS-001"
        assert state["status"] == UASStatus.AVAILABLE.value
        assert state["battery_level"] == 0.8
        assert state["certificate_valid"] is True
    
    def test_get_uas_state_not_found(self, core):
        """Тест получения состояния несуществующего БАС"""
        state = core.get_uas_state("UAS-999")
        
        assert state is None
    
    def test_is_certificate_valid(self, core):
        """Тест проверки срока действия сертификата"""
        # Действительный сертификат
        future_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
        assert core._is_certificate_valid(future_date) is True
        
        # Истекший сертификат
        past_date = (datetime.utcnow() - timedelta(days=1)).isoformat()
        assert core._is_certificate_valid(past_date) is False
        
        # Некорректная дата
        assert core._is_certificate_valid("invalid-date") is False
    
    def test_minimal_code_size(self, core):
        """Тест минимального размера кода в доверенном домене"""
        import inspect
        import sys
        
        # Получаем исходный код класса
        source = inspect.getsource(FleetManagerCore)
        lines = source.split('\n')
        
        # Фильтруем пустые строки и комментарии
        code_lines = [
            line for line in lines 
            if line.strip() and not line.strip().startswith('#')
        ]
        
        # Проверяем, что код минимален (< 300 строк)
        assert len(code_lines) < 300, f"TCB too large: {len(code_lines)} lines"