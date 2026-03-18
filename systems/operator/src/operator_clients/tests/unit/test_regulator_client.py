"""
Unit-тесты для RegulatorClient.

Примечание: файл перенесён из системного уровня `systems/operator/tests/unit`,
чтобы в `systems/operator/tests` оставались только интеграционные/сквозные тесты уровня системы.
"""

import os
import pytest
from unittest.mock import Mock, AsyncMock, patch

from systems.operator.src.operator_clients import RegulatorClient, SystemTopicInfo
from systems.operator.src.topics import SystemTopics


class TestRegulatorClient:
    """Тесты для клиента Регулятора"""

    @pytest.fixture
    def mock_bus(self):
        """Mock для SystemBus"""
        bus = Mock()
        bus.request = AsyncMock()
        return bus

    @pytest.fixture
    def client(self, mock_bus):
        """Создание клиента для тестов"""
        return RegulatorClient(mock_bus)

    def test_init(self, mock_bus):
        """Тест инициализации клиента"""
        client = RegulatorClient(mock_bus)
        assert client.bus == mock_bus
        assert client.topics_cache == {}
        assert client.cache_updated_at is None
        assert client.use_env_topics is True

    @pytest.mark.asyncio
    async def test_get_system_topics_from_env(self, client):
        """Тест получения топиков из переменных окружения"""
        with patch.dict(
            os.environ,
            {
                "AGGREGATOR_ID": "agg-test-001",
                "DEVELOPERS_IDS": "dev-test-001,dev-test-002",
                "INSURANCE_IDS": "ins-test-001",
                "UTM_ID": "utm-test-001",
            },
        ):
            topics = await client.get_system_topics()

            assert len(topics) == 5  # 1 aggregator + 2 developers + 1 insurer + 1 utm
            assert "aggregator" in topics
            assert topics["aggregator"].system_id == "agg-test-001"
            assert topics["aggregator"].topic == SystemTopics.get_aggregator("agg-test-001")
            assert topics["aggregator"].system_type == "aggregator"
            assert topics["aggregator"].active is True

    @pytest.mark.asyncio
    async def test_get_system_topics_from_regulator(self, client, mock_bus):
        """Тест получения топиков от Регулятора"""
        client.use_env_topics = False

        mock_response = {
            "success": True,
            "payload": {
                "topics": {
                    "aggregator": {
                        "system_id": "agg-001",
                        "system_type": "aggregator",
                        "topic": SystemTopics.get_aggregator("agg-001"),
                        "active": True,
                        "registered_at": "2024-01-01T00:00:00",
                    }
                }
            },
        }
        mock_bus.request.return_value = mock_response

        topics = await client.get_system_topics()

        assert len(topics) == 1
        assert "aggregator" in topics
        assert topics["aggregator"].system_id == "agg-001"

        mock_bus.request.assert_called_once()
        call_args = mock_bus.request.call_args
        assert call_args[0][0] == SystemTopics.REGULATOR
        assert call_args[0][1]["action"] == "get_system_topics"

    def test_get_topic_for_system(self, client):
        """Тест получения топика для типа системы"""
        client.topics_cache = {
            "agg": SystemTopicInfo(
                system_id="agg-001",
                system_type="aggregator",
                topic=SystemTopics.get_aggregator("agg-001"),
                active=True,
                registered_at="2024-01-01",
            ),
            "dev": SystemTopicInfo(
                system_id="dev-001",
                system_type="developer",
                topic=SystemTopics.get_developer("dev-001"),
                active=True,
                registered_at="2024-01-01",
            ),
        }

        topic = client.get_topic_for_system("aggregator")
        assert topic == SystemTopics.get_aggregator("agg-001")

        topic = client.get_topic_for_system("developer")
        assert topic == SystemTopics.get_developer("dev-001")

        topic = client.get_topic_for_system("unknown")
        assert topic is None
