"""
Юнит-тесты для RegulatorClient
"""
import os
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from systems.operator.src.regulator_client import RegulatorClient, SystemTopicInfo


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
        with patch.dict(os.environ, {
            'AGGREGATOR_ID': 'agg-test-001',
            'DEVELOPERS_IDS': 'dev-test-001,dev-test-002',
            'INSURANCE_IDS': 'ins-test-001',
            'UTM_ID': 'utm-test-001'
        }):
            topics = await client.get_system_topics()
            
            assert len(topics) == 5  # 1 aggregator + 2 developers + 1 insurance + 1 utm
            assert 'aggregator' in topics
            assert topics['aggregator'].system_id == 'agg-test-001'
            assert topics['aggregator'].topic == 'aggregator.agg-test-001'
            assert topics['aggregator'].system_type == 'aggregator'
            assert topics['aggregator'].active is True
    
    @pytest.mark.asyncio
    async def test_get_system_topics_from_regulator(self, client, mock_bus):
        """Тест получения топиков от Регулятора"""
        client.use_env_topics = False
        
        # Настраиваем mock ответ
        mock_response = {
            'success': True,
            'payload': {
                'topics': {
                    'aggregator': {
                        'system_id': 'agg-001',
                        'system_type': 'aggregator',
                        'topic': 'aggregator.agg-001',
                        'active': True,
                        'registered_at': '2024-01-01T00:00:00'
                    }
                }
            }
        }
        mock_bus.request.return_value = mock_response
        
        topics = await client.get_system_topics()
        
        assert len(topics) == 1
        assert 'aggregator' in topics
        assert topics['aggregator'].system_id == 'agg-001'
        
        # Проверяем, что был вызван request
        mock_bus.request.assert_called_once()
        call_args = mock_bus.request.call_args
        assert call_args[0][0] == 'regulator.system'
        assert call_args[0][1]['action'] == 'get_system_topics'
    
    @pytest.mark.asyncio
    async def test_get_system_topics_fallback_to_env(self, client, mock_bus):
        """Тест fallback на env при ошибке Регулятора"""
        client.use_env_topics = False
        
        # Настраиваем mock для ошибки
        mock_bus.request.side_effect = Exception("Connection error")
        
        topics = await client.get_system_topics()
        
        # Должен вернуть топики из env
        assert len(topics) > 0
        assert 'aggregator' in topics
    
    def test_get_topic_for_system(self, client):
        """Тест получения топика для типа системы"""
        # Заполняем кеш
        client.topics_cache = {
            'agg': SystemTopicInfo(
                system_id='agg-001',
                system_type='aggregator',
                topic='aggregator.agg-001',
                active=True,
                registered_at='2024-01-01'
            ),
            'dev': SystemTopicInfo(
                system_id='dev-001',
                system_type='developer',
                topic='developer.dev-001',
                active=True,
                registered_at='2024-01-01'
            )
        }
        
        topic = client.get_topic_for_system('aggregator')
        assert topic == 'aggregator.agg-001'
        
        topic = client.get_topic_for_system('developer')
        assert topic == 'developer.dev-001'
        
        topic = client.get_topic_for_system('unknown')
        assert topic is None
    
    def test_get_all_topics_by_type(self, client):
        """Тест получения всех топиков по типу"""
        # Заполняем кеш
        client.topics_cache = {
            'dev1': SystemTopicInfo(
                system_id='dev-001',
                system_type='developer',
                topic='developer.dev-001',
                active=True,
                registered_at='2024-01-01'
            ),
            'dev2': SystemTopicInfo(
                system_id='dev-002',
                system_type='developer',
                topic='developer.dev-002',
                active=True,
                registered_at='2024-01-01'
            ),
            'agg': SystemTopicInfo(
                system_id='agg-001',
                system_type='aggregator',
                topic='aggregator.agg-001',
                active=True,
                registered_at='2024-01-01'
            )
        }
        
        dev_topics = client.get_all_topics_by_type('developer')
        assert len(dev_topics) == 2
        assert 'developer.dev-001' in dev_topics
        assert 'developer.dev-002' in dev_topics
        
        agg_topics = client.get_all_topics_by_type('aggregator')
        assert len(agg_topics) == 1
        assert 'aggregator.agg-001' in agg_topics
    
    @pytest.mark.asyncio
    async def test_register_with_regulator_test_mode(self, client):
        """Тест регистрации в тестовом режиме"""
        client.use_env_topics = True
        
        operator_info = {
            'operator_id': 'op-001',
            'operator_name': 'Test Operator'
        }
        
        result = await client.register_with_regulator(operator_info)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_register_with_regulator_success(self, client, mock_bus):
        """Тест успешной регистрации"""
        client.use_env_topics = False
        
        mock_response = {
            'success': True,
            'payload': {
                'registered': True
            }
        }
        mock_bus.request.return_value = mock_response
        
        operator_info = {
            'operator_id': 'op-001',
            'operator_name': 'Test Operator'
        }
        
        result = await client.register_with_regulator(operator_info)
        assert result is True
        
        # Проверяем вызов
        mock_bus.request.assert_called_once()
        call_args = mock_bus.request.call_args
        assert call_args[0][0] == 'regulator.system'
        assert call_args[0][1]['action'] == 'register_operator'
        assert call_args[0][1]['payload'] == operator_info
    
    @pytest.mark.asyncio
    async def test_register_with_regulator_failure(self, client, mock_bus):
        """Тест неудачной регистрации"""
        client.use_env_topics = False
        
        mock_bus.request.side_effect = Exception("Connection error")
        
        operator_info = {
            'operator_id': 'op-001',
            'operator_name': 'Test Operator'
        }
        
        result = await client.register_with_regulator(operator_info)
        assert result is False