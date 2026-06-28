"""
Unit-тесты для DeveloperClient.

Примечание: файл перенесён из системного уровня `systems/operator/tests/unit`,
чтобы в `systems/operator/tests` оставались только интеграционные/сквозные тесты уровня системы.
"""

import os
import pytest
import tempfile
import yaml
from unittest.mock import Mock, AsyncMock

from systems.operator.src.operator_clients import DeveloperClient, UASModel, UASCategory, DeveloperCatalog


class TestDeveloperClient:
    """Тесты для клиента Разработчиков БАС"""

    @pytest.fixture
    def mock_bus(self):
        """Mock для SystemBus"""
        bus = Mock()
        bus.request = AsyncMock()
        return bus

    @pytest.fixture
    def mock_regulator_client(self):
        """Mock для RegulatorClient"""
        client = Mock()
        client.get_all_topics_by_type = Mock(return_value=["developer.dev-001", "developer.dev-002"])
        client.get_topic_for_system = Mock(return_value="developer.dev-001")
        return client

    @pytest.fixture
    def client(self, mock_bus, mock_regulator_client):
        """Создание клиента для тестов"""
        return DeveloperClient(mock_bus, mock_regulator_client)

    @pytest.fixture
    def sample_catalog_data(self):
        """Пример данных каталога"""
        return {
            "developers": [
                {
                    "developer_id": "dev-001",
                    "developer_name": "Test Developer",
                    "updated_at": "2024-01-01T00:00:00",
                    "contact_info": {"email": "test@dev.com", "phone": "+7-123-456-7890"},
                    "models": [
                        {
                            "model_id": "TEST-001",
                            "name": "Test Drone",
                            "category": "light_cargo",
                            "manufacturer": "Test Developer",
                            "specifications": {"max_payload_kg": 5.0, "max_range_km": 50.0},
                            "price": 100000.0,
                            "certification": {
                                "type": "Type Certificate",
                                "number": "TC-TEST-001",
                                "issued_by": "Regulator",
                                "valid_until": "2029-01-01",
                            },
                            "safety_features": ["Feature 1", "Feature 2"],
                            "available_quantity": 10,
                            "delivery_time_days": 14,
                        }
                    ],
                }
            ]
        }

    def test_init(self, mock_bus, mock_regulator_client):
        """Тест инициализации клиента"""
        client = DeveloperClient(mock_bus, mock_regulator_client)
        assert client.bus == mock_bus
        assert client.regulator_client == mock_regulator_client
        assert client.catalogs_cache == {}
        assert client.use_yaml_catalog is True

    @pytest.mark.asyncio
    async def test_get_all_catalogs_from_yaml(self, client, sample_catalog_data):
        """Тест получения каталогов из YAML"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(sample_catalog_data, f)
            temp_path = f.name

        try:
            client.yaml_catalog_path = temp_path
            catalogs = await client.get_all_catalogs()

            assert len(catalogs) == 1
            assert "dev-001" in catalogs

            catalog = catalogs["dev-001"]
            assert catalog.developer_id == "dev-001"
            assert catalog.developer_name == "Test Developer"
            assert len(catalog.models) == 1

            model = catalog.models[0]
            assert model.model_id == "TEST-001"
            assert model.name == "Test Drone"
            assert model.category == UASCategory.LIGHT_CARGO
            assert model.price == 100000.0
        finally:
            os.unlink(temp_path)

    def test_parse_catalog(self, client):
        """Тест парсинга данных каталога"""
        data = {
            "developer_id": "dev-test",
            "developer_name": "Test Dev",
            "updated_at": "2024-01-01",
            "contact_info": {"email": "test@test.com"},
            "models": [
                {
                    "model_id": "M-001",
                    "name": "Model 1",
                    "category": "agro",
                    "manufacturer": "Test",
                    "specifications": {},
                    "price": 50000.0,
                    "certification": {},
                    "safety_features": ["SF1"],
                    "available_quantity": 3,
                    "delivery_time_days": 7,
                }
            ],
        }

        catalog = client._parse_catalog(data)

        assert catalog is not None
        assert catalog.developer_id == "dev-test"
        assert len(catalog.models) == 1
        assert catalog.models[0].category == UASCategory.AGRO

    @pytest.mark.asyncio
    async def test_purchase_uas_success(self, client):
        """Тест успешной покупки БАС"""
        client.catalogs_cache = {
            "dev-001": DeveloperCatalog(
                developer_id="dev-001",
                developer_name="Test Dev",
                models=[
                    UASModel(
                        model_id="M-001",
                        name="Test Model",
                        category=UASCategory.LIGHT_CARGO,
                        manufacturer="Test",
                        specifications={},
                        price=100000.0,
                        certification={},
                        available_quantity=5,
                    )
                ],
                updated_at="2024-01-01",
                contact_info={},
            )
        }

        result = await client.purchase_uas("dev-001", "M-001", 2)

        assert result["success"] is True
        assert "order_id" in result
        assert result["quantity"] == 2
        assert result["total_price"] == 200000.0
