"""
Integration tests for Fleet Manager component
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timedelta

from systems.operator.src.fleet_manager.src.fleet_manager import FleetManager
from systems.operator.src.fleet_manager.src.fleet_manager_core import UASStatus


class TestFleetManagerIntegration:
    """Интеграционные тесты компонента Fleet Manager"""

    @pytest.fixture
    def mock_bus(self):
        """Mock системной шины"""
        bus = Mock()
        bus.subscribe = AsyncMock()
        bus.publish = AsyncMock()
        bus.request = AsyncMock()
        return bus

    @pytest.fixture
    def mock_developer_client(self):
        """Mock клиента разработчика"""
        client = Mock()
        client.get_all_catalogs = AsyncMock(return_value={})
        client.purchase_uas = AsyncMock(return_value={"success": True})
        return client

    @pytest.fixture
    def mock_regulator_client(self):
        """Mock клиента регулятора"""
        client = Mock()
        client.get_system_topics = AsyncMock(return_value={})
        return client

    @pytest.fixture
    def fleet_manager(self, mock_bus, mock_developer_client, mock_regulator_client):
        """Создание экземпляра Fleet Manager"""
        config = {"developer_client": mock_developer_client, "regulator_client": mock_regulator_client}
        return FleetManager("test_fm", mock_bus, config)

    @pytest.mark.asyncio
    async def test_get_uas_list(self, fleet_manager):
        """Тест получения списка БАС"""
        # Добавляем тестовые БАС
        fleet_manager.core.add_uas(
            "UAS-001", {"certificate_valid": True, "certificate_expiry": "2027-01-01", "battery_level": 0.8}
        )

        # Вызываем обработчик
        message = {"action": "GET_UAS_LIST", "sender": "test"}
        result = fleet_manager._handle_get_uas_list(message)

        assert "uas_list" in result
        assert "total" in result
        assert "statistics" in result
        assert result["total"] >= 1

    @pytest.mark.asyncio
    async def test_find_available_uas(self, fleet_manager):
        """Тест поиска доступных БАС"""
        # Подготовка данных
        message = {
            "action": "FIND_AVAILABLE_UAS",
            "payload": {
                "requirements": {"type": "light_cargo", "min_payload": 3.0, "min_range": 20.0, "min_battery": 0.5}
            },
        }

        # Вызов обработчика
        result = fleet_manager._handle_find_available_uas(message)

        assert "suitable_uas" in result
        assert "count" in result
        assert isinstance(result["suitable_uas"], list)

    @pytest.mark.asyncio
    async def test_reserve_release_flow(self, fleet_manager):
        """Тест полного цикла резервирования и освобождения БАС"""
        # Добавляем БАС
        fleet_manager.core.add_uas(
            "UAS-001",
            {
                "certificate_valid": True,
                "certificate_expiry": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                "battery_level": 0.8,
            },
        )

        # Резервируем БАС
        reserve_msg = {
            "action": "RESERVE_UAS",
            "sender": "operator_01",
            "payload": {"uas_id": "UAS-001", "mission_id": "MISSION-123", "duration": 3600},
        }

        reserve_result = fleet_manager._handle_reserve_uas(reserve_msg)
        assert reserve_result["success"] is True
        assert reserve_result["uas_id"] == "UAS-001"

        # Проверяем статус
        status_msg = {"action": "GET_UAS_STATUS", "payload": {"uas_id": "UAS-001"}}

        status_result = fleet_manager._handle_get_uas_status(status_msg)
        assert status_result["status"] == UASStatus.RESERVED.value
        assert status_result["reserved_by"] == "MISSION-123"

        # Освобождаем БАС
        release_msg = {"action": "RELEASE_UAS", "sender": "operator_01", "payload": {"uas_id": "UAS-001"}}

        release_result = fleet_manager._handle_release_uas(release_msg)
        assert release_result["success"] is True

        # Проверяем финальный статус
        final_status = fleet_manager._handle_get_uas_status(status_msg)
        assert final_status["status"] == UASStatus.AVAILABLE.value
        assert final_status["reserved_by"] is None

    @pytest.mark.asyncio
    async def test_update_uas_status(self, fleet_manager):
        """Тест обновления статуса БАС"""
        # Добавляем БАС
        fleet_manager.core.add_uas(
            "UAS-001", {"certificate_valid": True, "certificate_expiry": "2027-01-01", "battery_level": 1.0}
        )

        # Обновляем статус
        update_msg = {
            "action": "UPDATE_UAS_STATUS",
            "payload": {"uas_id": "UAS-001", "updates": {"battery_level": 0.3, "status": "charging"}},
        }

        result = fleet_manager._handle_update_uas_status(update_msg)
        assert result["success"] is True

        # Проверяем обновления
        status = fleet_manager.core.get_uas_state("UAS-001")
        assert status["battery_level"] == 0.3
        assert status["status"] == UASStatus.CHARGING.value

    @pytest.mark.asyncio
    async def test_get_fleet_statistics(self, fleet_manager):
        """Тест получения статистики парка"""
        # Добавляем несколько БАС
        for i in range(3):
            fleet_manager.core.add_uas(
                f"UAS-00{i+1}",
                {"certificate_valid": True, "certificate_expiry": "2027-01-01", "battery_level": 0.5 + i * 0.2},
            )

        # Получаем статистику
        message = {"action": "GET_FLEET_STATISTICS"}
        result = fleet_manager._handle_get_fleet_statistics(message)

        assert "total" in result
        assert "by_status" in result
        assert "by_type" in result
        assert "average_battery" in result
        assert result["total"] >= 3

    @pytest.mark.asyncio
    async def test_health_check(self, fleet_manager):
        """Тест проверки здоровья компонента"""
        health = fleet_manager.get_health_status()

        assert "status" in health
        assert health["status"] in ["healthy", "degraded", "unhealthy"]
        assert "statistics" in health or "error" in health

    @pytest.mark.asyncio
    async def test_concurrent_reservations(self, fleet_manager):
        """Тест конкурентных резервирований"""
        # Добавляем БАС
        fleet_manager.core.add_uas(
            "UAS-001", {"certificate_valid": True, "certificate_expiry": "2027-01-01", "battery_level": 1.0}
        )

        # Создаём два конкурентных запроса
        reserve_msg1 = {
            "action": "RESERVE_UAS",
            "sender": "operator_01",
            "payload": {"uas_id": "UAS-001", "mission_id": "MISSION-001"},
        }

        reserve_msg2 = {
            "action": "RESERVE_UAS",
            "sender": "operator_02",
            "payload": {"uas_id": "UAS-001", "mission_id": "MISSION-002"},
        }

        # Первое резервирование должно успеть
        result1 = fleet_manager._handle_reserve_uas(reserve_msg1)
        assert result1["success"] is True

        # Второе должно провалиться
        result2 = fleet_manager._handle_reserve_uas(reserve_msg2)
        assert result2["success"] is False
        assert "suggestions" in result2

    @pytest.mark.asyncio
    async def test_purchase_history(self, fleet_manager):
        """Тест истории покупок"""
        # Инициализируем парк (создаст историю покупок)
        await fleet_manager.service.initialize_fleet()

        # Получаем историю
        message = {"action": "GET_PURCHASE_HISTORY", "payload": {}}
        result = fleet_manager._handle_get_purchase_history(message)

        assert "purchases" in result
        assert "count" in result
        assert "total_spent" in result
        assert "by_developer" in result

    @pytest.mark.asyncio
    async def test_error_handling(self, fleet_manager):
        """Тест обработки ошибок"""
        # Тест с несуществующим БАС
        message = {"action": "GET_UAS_STATUS", "payload": {"uas_id": "NON-EXISTENT"}}

        result = fleet_manager._handle_get_uas_status(message)
        assert "error" in result

        # Тест с отсутствующими параметрами
        message = {"action": "RESERVE_UAS", "payload": {}}

        result = fleet_manager._handle_reserve_uas(message)
        assert "error" in result
