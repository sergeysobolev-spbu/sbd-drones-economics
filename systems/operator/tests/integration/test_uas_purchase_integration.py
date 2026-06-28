"""
Интеграционные тесты для покупки БАС
"""

import pytest
import asyncio
import os
import tempfile
import yaml
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from broker.system_bus import SystemBus
from systems.operator.src.fleet_manager import FleetManager
from systems.operator.src.operator_clients import RegulatorClient, DeveloperClient
from systems.operator.src.topics import ComponentTopics, FleetManagerActions


class TestUASPurchaseIntegration:
    """Интеграционные тесты процесса покупки БАС"""

    @pytest.fixture
    def mock_bus(self):
        """Mock для SystemBus"""
        bus = Mock()
        bus.request = AsyncMock()
        bus.publish = AsyncMock()
        return bus

    @pytest.fixture
    def sample_catalog_data(self):
        """Пример каталога разработчиков"""
        return {
            "developers": [
                {
                    "developer_id": "aeronext-001",
                    "developer_name": "AeroNext Technologies",
                    "updated_at": "2024-03-15T10:00:00",
                    "contact_info": {"email": "sales@aeronext.ru", "phone": "+7-495-123-4567"},
                    "models": [
                        {
                            "model_id": "AN-CARGO-5",
                            "name": "AeroNext Cargo 5",
                            "category": "light_cargo",
                            "manufacturer": "AeroNext Technologies",
                            "specifications": {
                                "max_payload_kg": 5.0,
                                "max_range_km": 50.0,
                                "cruise_speed_kmh": 60.0,
                                "max_altitude_m": 500.0,
                                "battery_capacity_wh": 500.0,
                                "charging_time_min": 60.0,
                            },
                            "price": 1500000.0,
                            "certification": {
                                "type": "Type Certificate",
                                "number": "TC-2024-001",
                                "issued_by": "Росавиация",
                                "valid_until": "2029-01-01",
                            },
                            "safety_features": [
                                "Redundant flight controller",
                                "Parachute recovery system",
                                "Collision avoidance sensors",
                            ],
                            "available_quantity": 10,
                            "delivery_time_days": 14,
                        }
                    ],
                }
            ]
        }

    @pytest.fixture
    def setup_components(self, mock_bus, sample_catalog_data):
        """Настройка компонентов для тестов"""
        # Создаём временный YAML файл с каталогом
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(sample_catalog_data, f)
            catalog_path = f.name

        # Создаём клиенты
        regulator_client = RegulatorClient(mock_bus)
        developer_client = DeveloperClient(mock_bus, regulator_client)
        developer_client.yaml_catalog_path = catalog_path

        # Создаём Fleet Manager
        fleet_manager = FleetManager(
            "fleet-test",
            mock_bus,
            config={
                "developer_client": developer_client,
                "regulator_client": regulator_client,
            },
        )

        # Настраиваем mock для регулятора
        with patch.dict(
            os.environ,
            {
                "AGGREGATOR_ID": "agg-001",
                "DEVELOPERS_IDS": "aeronext-001",
                "INSURANCE_IDS": "ins-001",
                "UTM_ID": "utm-001",
            },
        ):
            yield {
                "fleet_manager": fleet_manager,
                "developer_client": developer_client,
                "regulator_client": regulator_client,
                "catalog_path": catalog_path,
            }

        # Удаляем временный файл
        os.unlink(catalog_path)

    def test_purchase_uas_full_flow(self, setup_components):
        """Тест полного процесса покупки БАС"""
        fleet_manager = setup_components["fleet_manager"]
        developer_client = setup_components["developer_client"]

        # 1. Получаем каталоги разработчиков
        catalogs = asyncio.run(developer_client.get_all_catalogs())
        assert len(catalogs) == 1
        assert "aeronext-001" in catalogs

        # 2. Ищем подходящие модели
        requirements = {"min_payload": 3.0, "min_range": 30.0, "category": "light_cargo"}

        suitable_models = developer_client.find_best_uas_for_requirements(requirements)
        assert len(suitable_models) == 1
        assert suitable_models[0].model_id == "AN-CARGO-5"

        # 3. Покупаем БАС через Fleet Manager
        purchase_request = {
            "action": FleetManagerActions.PURCHASE_UAS,
            "payload": {"developer_id": "aeronext-001", "model_id": "AN-CARGO-5", "quantity": 2},
        }

        result = fleet_manager._handle_purchase_uas(purchase_request)

        assert result["success"] is True
        assert result["order_id"] is not None
        assert result["quantity"] == 2
        assert result["total_price"] == 3000000.0  # 2 * 1500000
        assert result["delivery_time_days"] == 14

        # 4. Проверяем, что БАС добавлены в парк
        fleet_status = fleet_manager._handle_get_uas_list({})
        assert fleet_status["total_count"] == 2

        # Проверяем первый БАС
        uas_list = fleet_status["uas_list"]
        assert len(uas_list) == 2
        assert uas_list[0]["model_id"] == "AN-CARGO-5"
        assert uas_list[0]["status"] == "available"
        assert uas_list[0]["battery_level"] == 1.0

    def test_purchase_with_insufficient_quantity(self, setup_components):
        """Тест покупки при недостаточном количестве"""
        fleet_manager = setup_components["fleet_manager"]

        # Пытаемся купить больше, чем доступно
        purchase_request = {
            "action": FleetManagerActions.PURCHASE_UAS,
            "payload": {"developer_id": "aeronext-001", "model_id": "AN-CARGO-5", "quantity": 20},  # Доступно только 10
        }

        result = fleet_manager._handle_purchase_uas(purchase_request)

        assert result["success"] is False
        assert result["error"] == "Insufficient quantity available"
        assert result["available"] == 10

    def test_purchase_nonexistent_model(self, setup_components):
        """Тест покупки несуществующей модели"""
        fleet_manager = setup_components["fleet_manager"]

        purchase_request = {
            "action": FleetManagerActions.PURCHASE_UAS,
            "payload": {"developer_id": "aeronext-001", "model_id": "NONEXISTENT-MODEL", "quantity": 1},
        }

        result = fleet_manager._handle_purchase_uas(purchase_request)

        assert result["success"] is False
        assert result["error"] == "Model not found"

    def test_find_available_uas_after_purchase(self, setup_components):
        """Тест поиска доступных БАС после покупки"""
        fleet_manager = setup_components["fleet_manager"]

        # Покупаем БАС
        purchase_request = {
            "action": FleetManagerActions.PURCHASE_UAS,
            "payload": {"developer_id": "aeronext-001", "model_id": "AN-CARGO-5", "quantity": 3},
        }

        fleet_manager._handle_purchase_uas(purchase_request)

        # Ищем доступные БАС по требованиям
        find_request = {
            "action": FleetManagerActions.FIND_AVAILABLE_UAS,
            "payload": {"requirements": {"min_payload": 4.0, "min_range": 40.0, "min_battery": 0.8}},
        }

        result = fleet_manager._handle_find_available_uas(find_request)

        assert result["count"] == 3
        assert len(result["suitable_uas"]) == 3

        for uas in result["suitable_uas"]:
            assert uas["model_id"] == "AN-CARGO-5"
            assert uas["max_payload"] == 5.0
            assert uas["max_range"] == 50.0
            assert uas["battery_level"] >= 0.8

    def test_reserve_purchased_uas(self, setup_components):
        """Тест резервирования купленного БАС"""
        fleet_manager = setup_components["fleet_manager"]

        # Покупаем БАС
        purchase_request = {
            "action": FleetManagerActions.PURCHASE_UAS,
            "payload": {"developer_id": "aeronext-001", "model_id": "AN-CARGO-5", "quantity": 1},
        }

        purchase_result = fleet_manager._handle_purchase_uas(purchase_request)
        assert purchase_result["success"] is True

        # Получаем ID первого БАС
        fleet_status = fleet_manager._handle_get_uas_list({})
        uas_id = fleet_status["uas_list"][0]["id"]

        # Резервируем БАС
        reserve_request = {
            "action": FleetManagerActions.RESERVE_UAS,
            "payload": {"uas_id": uas_id, "mission_id": "MISSION-001", "duration": 3600},
        }

        result = fleet_manager._handle_reserve_uas(reserve_request)

        assert result["reserved"] is True
        assert result["uas_id"] == uas_id
        assert "expires_at" in result

        # Проверяем, что БАС теперь зарезервирован
        fleet_status = fleet_manager._handle_get_uas_list({})
        reserved_uas = next(u for u in fleet_status["uas_list"] if u["id"] == uas_id)
        assert reserved_uas["status"] == "reserved"
        assert reserved_uas["mission_id"] == "MISSION-001"

    def test_integration_with_multiple_developers(self, mock_bus):
        """Тест интеграции с несколькими разработчиками"""
        # Создаём каталог с несколькими разработчиками
        multi_catalog = {
            "developers": [
                {
                    "developer_id": "dev-001",
                    "developer_name": "Developer 1",
                    "models": [
                        {
                            "model_id": "M1",
                            "name": "Model 1",
                            "category": "light_cargo",
                            "manufacturer": "Developer 1",
                            "specifications": {"max_payload_kg": 5.0},
                            "price": 100000.0,
                            "certification": {"valid_until": "2029-01-01"},
                            "available_quantity": 5,
                            "delivery_time_days": 7,
                        }
                    ],
                },
                {
                    "developer_id": "dev-002",
                    "developer_name": "Developer 2",
                    "models": [
                        {
                            "model_id": "M2",
                            "name": "Model 2",
                            "category": "heavy_cargo",
                            "manufacturer": "Developer 2",
                            "specifications": {"max_payload_kg": 20.0},
                            "price": 200000.0,
                            "certification": {"valid_until": "2029-01-01"},
                            "available_quantity": 3,
                            "delivery_time_days": 14,
                        }
                    ],
                },
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(multi_catalog, f)
            catalog_path = f.name

        try:
            regulator_client = RegulatorClient(mock_bus)
            developer_client = DeveloperClient(mock_bus, regulator_client)
            developer_client.yaml_catalog_path = catalog_path

            # Получаем все каталоги
            catalogs = asyncio.run(developer_client.get_all_catalogs())
            assert len(catalogs) == 2

            # Ищем тяжёлые БАС
            heavy_models = developer_client.find_best_uas_for_requirements({"category": "heavy_cargo"})
            assert len(heavy_models) == 1
            assert heavy_models[0].model_id == "M2"

            # Ищем лёгкие БАС
            light_models = developer_client.find_best_uas_for_requirements({"category": "light_cargo"})
            assert len(light_models) == 1
            assert light_models[0].model_id == "M1"

        finally:
            os.unlink(catalog_path)
